"""Claude-to-Antigravity MCP Bridge.

An MCP server that delegates tasks to the Antigravity CLI (agy)
with configurable timeouts.
"""

import asyncio
import os
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

from fastmcp import FastMCP

# ponytail: Windows-only bridge. winpty wraps ConPTY; POSIX would need ptyprocess
# (not implemented — agy and this MCP only run on the Windows PC).
if sys.platform == "win32":
    from winpty import PtyProcess
else:  # pragma: no cover - bridge only runs on Windows
    PtyProcess = None

TOTAL_TIMEOUT = int(os.environ.get("AGY_TOTAL_TIMEOUT", "1200"))

mcp = FastMCP("claude-to-agy")

_executor = ThreadPoolExecutor(max_workers=4)
# Strip VT/ANSI control sequences the PTY injects (CSI/charset/OSC) + CRs.
_ANSI = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"  # CSI sequences
    r"|\x1b[()][AB0-2]"  # charset selection
    r"|\x1b\][^\x07]*(?:\x07|\x1b\\)"  # OSC sequences
    r"|\r"  # carriage returns
)


def build_files_context(files: list[str] | None) -> str:
    """Build a context string from a list of file paths."""
    if not files:
        return ""

    file_list = "\n".join(f"- {f}" for f in files)

    return f"""Context files:
{file_list}

"""


def _run_pty(cmd: list[str], cwd: str, total_timeout: int) -> str:
    """Spawn agy in a PTY so it thinks it's attached to a terminal (fixes #76).

    agy gates ALL output on isatty() and emits nothing down a plain pipe, so we
    give it a real Windows console. We read until the process dies (or a watchdog
    kills it on timeout), then strip the VT noise the PTY adds.
    """
    if PtyProcess is None:  # pragma: no cover - non-Windows guard
        raise RuntimeError("claude-to-agy requires Windows (pywinpty unavailable).")
    try:
        # ponytail: 220 cols wide so agy's output isn't hard-wrapped mid-line
        proc = PtyProcess.spawn(cmd, cwd=cwd, dimensions=(50, 220))
    except OSError as error:
        raise RuntimeError(f"Failed to start agy: {error}") from error

    timed_out = threading.Event()

    def _watchdog() -> None:
        timed_out.set()
        if proc.isalive():
            proc.terminate(force=True)  # unblocks the blocking read() -> EOFError

    timer = threading.Timer(total_timeout, _watchdog)
    timer.start()
    chunks: list[str] = []
    try:
        while proc.isalive():
            try:
                chunks.append(proc.read(4096))
            except EOFError:
                break
    finally:
        timer.cancel()
        if proc.isalive():
            proc.terminate(force=True)
        proc.close()  # release ConPTY/socket handles deterministically

    if timed_out.is_set():
        raise RuntimeError(f"Total timeout ({total_timeout}s) exceeded.")

    output = _ANSI.sub("", "".join(chunks))
    if proc.exitstatus:
        raise RuntimeError(
            f"agy exited with code {proc.exitstatus}. Output: {output.strip()}"
        )
    return output


@mcp.tool()
async def delegate_to_agy(prompt: str, cwd: str, files: list[str] | None = None) -> str:
    """Delegate complex reasoning or deep search to Antigravity CLI.

    Args:
        prompt: The detailed prompt/instructions for Antigravity CLI.
        cwd: The working directory of the project (absolute path).
        files: Optional list of absolute file paths to include as context.
    """
    full_prompt = build_files_context(files) + prompt
    cmd = [
        "agy",
        "--dangerously-skip-permissions",
        "--add-dir",
        cwd,
        # keep agy's own print-timeout aligned with ours so it doesn't self-abort
        # long reasoning tasks at its 5-minute default
        "--print-timeout",
        f"{TOTAL_TIMEOUT}s",
        "-p",
        full_prompt,
    ]
    loop = asyncio.get_running_loop()
    # outer wait_for is a backstop; the in-thread watchdog is the primary kill path
    return await asyncio.wait_for(
        loop.run_in_executor(_executor, _run_pty, cmd, cwd, TOTAL_TIMEOUT),
        timeout=TOTAL_TIMEOUT + 15,
    )


def main() -> None:  # pragma: no cover
    """Entry point for the claude-to-agy console script."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
