"""Claude-to-Antigravity MCP Bridge.

An MCP server that delegates tasks to the Antigravity CLI (agy)
with configurable timeouts.
"""

import asyncio
import os

from fastmcp import FastMCP

CONNECT_TIMEOUT = int(os.environ.get("AGY_CONNECT_TIMEOUT", "60"))
TOTAL_TIMEOUT = int(os.environ.get("AGY_TOTAL_TIMEOUT", "1200"))

mcp = FastMCP("claude-to-agy")


def build_files_context(files: list[str] | None) -> str:
    """Build a context string from a list of file paths."""
    if not files:
        return ""

    file_list = "\n".join(f"- {f}" for f in files)

    return f"""Context files:
{file_list}

"""


@mcp.tool()
async def delegate_to_agy(prompt: str, cwd: str, files: list[str] | None = None) -> str:
    """Delegate complex reasoning or deep search to Antigravity CLI.

    Args:
        prompt: The detailed prompt/instructions for Antigravity CLI.
        cwd: The working directory of the project (absolute path).
        files: Optional list of absolute file paths to include as context.
    """
    full_prompt = build_files_context(files) + prompt
    cmd = ["agy", "--dangerously-skip-permissions", "--add-dir", cwd, "-p", full_prompt]

    try:
        process = await asyncio.wait_for(
            asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            ),
            timeout=CONNECT_TIMEOUT,
        )
    except asyncio.TimeoutError:
        raise RuntimeError(f"Connect timeout ({CONNECT_TIMEOUT}s) exceeded.") from None
    except OSError as error:
        raise RuntimeError(f"Failed to start agy: {error}") from error

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(),
            timeout=TOTAL_TIMEOUT,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise RuntimeError(f"Total timeout ({TOTAL_TIMEOUT}s) exceeded.") from None

    stdout = stdout_bytes.decode("utf-8", errors="replace")
    stderr = stderr_bytes.decode("utf-8", errors="replace")

    if process.returncode != 0:
        raise RuntimeError(
            f"Process exited with code {process.returncode}. Stderr: {stderr}"
        )

    return stdout


def main() -> None:  # pragma: no cover
    """Entry point for the claude-to-agy console script."""
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
