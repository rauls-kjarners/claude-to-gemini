import os
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from claude_to_agy import bridge
from claude_to_agy.bridge import _run_pty, build_files_context, delegate_to_agy


def _fake_proc(reads: list[str], exitstatus: int = 0) -> MagicMock:
    """A fake PtyProcess: yields `reads`, then EOFError, then reports dead."""
    reads_left: list[str] = list(reads)
    alive = [True]
    proc = MagicMock()
    proc.isalive.side_effect = lambda: alive[0]

    def _read(_n: int) -> str:
        if reads_left:
            return reads_left.pop(0)
        alive[0] = False
        raise EOFError

    def _terminate(**_kwargs: object) -> None:
        alive[0] = False

    proc.read.side_effect = _read
    proc.terminate.side_effect = _terminate
    proc.exitstatus = exitstatus
    return proc


def test_build_files_context() -> None:
    assert build_files_context(None) == ""
    assert build_files_context([]) == ""
    expected = """Context files:
- /a/b.txt
- /c/d.txt

"""
    assert build_files_context(["/a/b.txt", "/c/d.txt"]) == expected


def test_run_pty_strips_vt_and_returns_output() -> None:
    # OSC title (ESC-]...ST) + CSI seqs + \r — all present in real agy PTY output
    proc = _fake_proc(["\x1b]0;title\x1b\\\x1b[?7lhello\x1b[1t world\r\n\x1b[c"])
    with patch.object(bridge.PtyProcess, "spawn", return_value=proc) as spawn:
        result = _run_pty(["agy"], "/ws", 60)
    assert result == "hello world\n"  # OSC + CSI seqs + \r stripped
    spawn.assert_called_once()


def test_run_pty_raises_on_nonzero_exit() -> None:
    proc = _fake_proc(["boom"], exitstatus=1)
    with (
        patch.object(bridge.PtyProcess, "spawn", return_value=proc),
        pytest.raises(RuntimeError) as exc,
    ):
        _run_pty(["agy"], "/ws", 60)
    assert "agy exited with code 1" in str(exc.value)
    assert "boom" in str(exc.value)


def test_run_pty_spawn_failure() -> None:
    with (
        patch.object(bridge.PtyProcess, "spawn", side_effect=OSError("no agy")),
        pytest.raises(RuntimeError) as exc,
    ):
        _run_pty(["agy"], "/ws", 60)
    assert "Failed to start agy: no agy" in str(exc.value)


def test_run_pty_timeout() -> None:
    """Watchdog fires -> terminate -> Total timeout raised (deterministic stub)."""
    proc = _fake_proc(["partial output"])

    class _ImmediateTimer:
        def __init__(self, _t: float, fn: Callable[[], None]) -> None:
            self._fn = fn

        def start(self) -> None:
            self._fn()  # fire the watchdog before any read happens

        def cancel(self) -> None:
            pass

    with (
        patch.object(bridge.PtyProcess, "spawn", return_value=proc),
        patch.object(bridge.threading, "Timer", _ImmediateTimer),
        pytest.raises(RuntimeError) as exc,
    ):
        _run_pty(["agy"], "/ws", 1)
    assert "Total timeout (1s) exceeded" in str(exc.value)


@pytest.mark.asyncio
async def test_delegate_to_agy_success() -> None:
    proc = _fake_proc(["Success!\r\n"])
    with patch.object(bridge.PtyProcess, "spawn", return_value=proc) as spawn:
        result = await delegate_to_agy("test prompt", "/some/workspace")
    assert result == "Success!\n"
    cmd = spawn.call_args[0][0]
    assert cmd[0] == "agy"
    assert "-p" in cmd
    assert "--print-timeout" in cmd
    assert "test prompt" in cmd
    assert "/some/workspace" in cmd


@pytest.fixture
def deny_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real sensitive-repo dir that the guard is patched to deny."""
    root = tmp_path / "repo"
    root.mkdir()
    monkeypatch.setattr(bridge, "_DENY_CWD", (str(root),))
    return root


def test_guard_allows_cwd_not_in_deny_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(bridge, "_DENY_CWD", ())
    bridge._guard_cwd(str(tmp_path))  # empty deny list -> no raise


def test_guard_blocks_exact_deny_root(deny_root: Path) -> None:
    with pytest.raises(PermissionError):
        bridge._guard_cwd(str(deny_root))


def test_guard_blocks_subdir_of_deny_root(deny_root: Path) -> None:
    sub = deny_root / "kernel"
    sub.mkdir()
    with pytest.raises(PermissionError):
        bridge._guard_cwd(str(sub))


def test_guard_blocks_parent_traversal_into_deny_root(deny_root: Path) -> None:
    (deny_root / "x").mkdir()
    tricky = deny_root / "x" / ".."  # realpath collapses back into the deny root
    with pytest.raises(PermissionError):
        bridge._guard_cwd(str(tricky))


def test_guard_allows_sibling_with_shared_prefix(deny_root: Path) -> None:
    sibling = deny_root.parent / "repo-x"
    sibling.mkdir()
    bridge._guard_cwd(str(sibling))  # os.sep boundary -> not a child, no raise


@pytest.mark.skipif(os.name != "nt", reason="case-insensitive FS (win/mac)")
def test_guard_blocks_uppercase_variant(deny_root: Path) -> None:
    with pytest.raises(PermissionError):
        bridge._guard_cwd(str(deny_root).upper())


def test_parse_deny_cwd_splits_and_strips() -> None:
    # blank and whitespace-only segments must be dropped
    raw = f"C:\\a{os.pathsep} {os.pathsep}C:\\b{os.pathsep}"
    assert bridge._parse_deny_cwd(raw) == ("C:\\a", "C:\\b")
    assert bridge._parse_deny_cwd("") == ()


def test_strip_win_prefix_handles_unc_and_extended() -> None:
    assert bridge._strip_win_prefix("\\\\?\\C:\\x") == "C:\\x"
    assert bridge._strip_win_prefix("\\\\?\\UNC\\srv\\share") == "\\\\srv\\share"
    assert bridge._strip_win_prefix("C:\\plain") == "C:\\plain"


@pytest.mark.skipif(os.name != "nt", reason="extended-length path is Windows-only")
def test_guard_blocks_extended_length_prefix(deny_root: Path) -> None:
    extended = "\\\\?\\" + str(deny_root)  # \\?\ prefix must not bypass the guard
    with pytest.raises(PermissionError):
        bridge._guard_cwd(extended)
