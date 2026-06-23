from unittest.mock import MagicMock, patch

import pytest

from claude_to_agy import bridge
from claude_to_agy.bridge import _run_pty, build_files_context, delegate_to_agy


def _fake_proc(reads: list[str], exitstatus: int = 0) -> MagicMock:
    """A fake PtyProcess: yields `reads`, then EOFError, then reports dead."""
    state = {"reads": list(reads), "alive": True}
    proc = MagicMock()
    proc.isalive.side_effect = lambda: state["alive"]

    def _read(_n: int) -> str:
        if state["reads"]:
            return state["reads"].pop(0)
        state["alive"] = False
        raise EOFError

    def _terminate(**_kwargs: object) -> None:
        state["alive"] = False

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
        def __init__(self, _t: float, fn: object) -> None:
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
