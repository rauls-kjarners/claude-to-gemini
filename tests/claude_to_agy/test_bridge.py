import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from claude_to_agy.bridge import build_files_context, delegate_to_agy


def test_build_files_context() -> None:
    assert build_files_context(None) == ""
    assert build_files_context([]) == ""
    expected = """Context files:
- /a/b.txt
- /c/d.txt

"""
    assert build_files_context(["/a/b.txt", "/c/d.txt"]) == expected


@pytest.mark.asyncio
async def test_delegate_to_agy_success() -> None:
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Success!", b""))
        mock_exec.return_value = mock_process

        result = await delegate_to_agy("test prompt", "/some/workspace")

        assert result == "Success!"
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]
        assert "agy" in args
        assert "test prompt" in args


@pytest.mark.asyncio
async def test_delegate_to_agy_failure() -> None:
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error occurred"))
        mock_exec.return_value = mock_process

        with pytest.raises(RuntimeError) as exc_info:
            await delegate_to_agy("test prompt", "/some/workspace")

        assert "Process exited with code 1" in str(exc_info.value)
        assert "Error occurred" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delegate_to_agy_connect_timeout() -> None:
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = asyncio.TimeoutError()

        with pytest.raises(RuntimeError) as exc_info:
            await delegate_to_agy("prompt", "/workspace")

        assert "Connect timeout" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delegate_to_agy_connect_exception() -> None:
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_exec.side_effect = OSError("System crash")

        with pytest.raises(RuntimeError) as exc_info:
            await delegate_to_agy("prompt", "/workspace")

        assert "Failed to start agy: System crash" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delegate_to_agy_communicate_timeout() -> None:
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()
        mock_exec.return_value = mock_process

        with pytest.raises(RuntimeError) as exc_info:
            await delegate_to_agy("prompt", "/workspace")

        assert "Total timeout" in str(exc_info.value)
        mock_process.kill.assert_called_once()
        mock_process.wait.assert_called_once()
