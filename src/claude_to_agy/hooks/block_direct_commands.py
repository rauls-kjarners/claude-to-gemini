#!/usr/bin/env python3
"""PreToolUse hook: blocks grep, git diff, git log from running directly.

Claude Code hooks run for ALL agents (main + subagents), so this enforces
delegation even when subagents ignore CLAUDE.md instructions.

Usage in ~/.claude/settings.json or .claude/settings.json:

  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "claude-agy-hook",
            "onError": "block"
          }
        ]
      }
    ]
  }
"""

import json
import os
import sys
import textwrap

BANNED_PATTERNS = [
    "grep ",
    "grep\t",
    "grep -",
    "git diff",
    "git log",
]


def main() -> int:
    raw = os.environ.get("CLAUDE_TOOL_INPUT", "{}")
    try:
        cmd = json.loads(raw).get("command", "")
    except (json.JSONDecodeError, AttributeError, TypeError):
        cmd = ""

    if any(pattern in cmd for pattern in BANNED_PATTERNS):
        message = textwrap.dedent(f"""
            =======================================================
            BLOCKED: Direct command execution
            =======================================================
            Claude Code tried to run: {cmd}

            grep/git diff/git log cannot be run directly.
            If you are a subagent, return control to the parent agent
            and instruct it to retry this task using delegate_to_agy.
            =======================================================
        """).strip()
        print(message, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
