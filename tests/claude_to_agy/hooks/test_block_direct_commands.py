"""Tests for block-direct-commands.py hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

HOOK = (
    Path(__file__).parent / "../../../src/claude_to_agy/hooks/block_direct_commands.py"
).resolve()


def run_hook(command: str) -> int:
    env = {**os.environ, "CLAUDE_TOOL_INPUT": json.dumps({"command": command})}
    result = subprocess.run(
        [sys.executable, HOOK], env=env, check=False, capture_output=True
    )
    return result.returncode


def assert_blocked(cmd: str) -> None:
    assert run_hook(cmd) == 1, f"Expected BLOCKED: {cmd!r}"


def assert_allowed(cmd: str) -> None:
    assert run_hook(cmd) == 0, f"Expected ALLOWED: {cmd!r}"


def test_grep_space() -> None:
    assert_blocked("grep foo bar.txt")


def test_grep_flag() -> None:
    assert_blocked("grep -r 'pattern' .")


def test_grep_tab() -> None:
    assert_blocked("grep\t-i foo")


def test_git_diff() -> None:
    assert_blocked("git diff HEAD~1")


def test_git_diff_staged() -> None:
    assert_blocked("git diff --staged")


def test_git_log() -> None:
    assert_blocked("git log --oneline -10")


def test_egrep_blocked() -> None:
    assert_blocked("egrep foo bar")


def test_ls() -> None:
    assert_allowed("ls -la")


def test_find() -> None:
    assert_allowed("find . -name '*.py'")


def test_git_status() -> None:
    assert_allowed("git status")


def test_empty_command() -> None:
    assert_allowed("")


def test_invalid_json() -> None:
    # hook should not crash on bad input — exit 0 (allow)
    env = {**os.environ, "CLAUDE_TOOL_INPUT": "not-json"}
    result = subprocess.run(
        [sys.executable, HOOK], env=env, check=False, capture_output=True
    )
    assert result.returncode == 0
