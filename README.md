# claude-to-agy

[![CI](https://github.com/rauls-kjarners/claude-to-agy/actions/workflows/ci.yml/badge.svg)](https://github.com/rauls-kjarners/claude-to-agy/actions/workflows/ci.yml)
[![codecov](https://codecov.io/github/rauls-kjarners/claude-to-agy/graph/badge.svg?token=QWY0HFQATX)](https://codecov.io/github/rauls-kjarners/claude-to-agy)

A lightweight MCP bridge that lets Claude Code delegate heavy tasks to the Antigravity CLI (agy) - saving context window and **tokens** for what matters.

## What It Does

Registers a `delegate_to_agy` MCP tool that Claude automatically uses when it encounters:

- **Large files** (>200 lines) - logs, dumps, generated code
- **Multi-file analysis** (>3 files at once)
- **Deep searches** - `git log`, `git diff`, `grep`
- **Web lookups** - documentation, external knowledge
- **Adversarial review / plan critique** - always delegated

Claude sends a prompt + file paths → the bridge runs `agy` CLI → returns the result.

## Requirements

- Python 3.10+
- [`agy` CLI](https://antigravity.google/docs/cli-getting-started) installed and authenticated
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Installation

```bash
# 1. Register the MCP server globally via uvx
claude mcp add -s user claude-to-agy uvx claude-to-agy

# 2. Download the delegation rules into your current project
curl -o CLAUDE.md https://raw.githubusercontent.com/rauls-kjarners/claude-to-agy/main/CLAUDE.md

# 3. (Optional) Add the PreToolUse hook to enforce delegation for subagents
```

Then merge the following into your `~/.claude/settings.json` (or per-project `.claude/settings.json`):

```json
{
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
}
```

That's it. Claude will now automatically delegate heavy tasks to Antigravity CLI in any project that has the `CLAUDE.md` file.

> **Tip:** To enable globally without copying `CLAUDE.md` per project, add the rules to `~/.claude/CLAUDE.md` instead.

### Why the Hook Matters

`CLAUDE.md` rules only apply to the **main** Claude agent. Subagents (spawned via `run_subagent` or similar) **do not** read `CLAUDE.md` and will run `grep -r`, `git diff`, etc. directly - wasting tokens and defeating the purpose of delegation.

The PreToolUse hook runs at the Claude Code platform level for **all** agents (main + sub), mechanically blocking banned commands before they execute.

### Using as a Skill

This project also includes a `SKILL.md` file, which is the standard format for reusable Claude Code skills. If your setup supports skills, you can use it instead of manually copying `CLAUDE.md`:

```bash
claude skill add https://raw.githubusercontent.com/rauls-kjarners/claude-to-agy/main/SKILL.md
```

> **Note:** You still need the MCP server registered (step 1 above). The skill provides the rules, MCP provides the tool.

## Configuration

All settings are optional environment variables:

| Variable              | Default | Description                       |
| --------------------- | ------- | --------------------------------- |
| `AGY_CONNECT_TIMEOUT` | `60`    | Seconds to start the agy process  |
| `AGY_TOTAL_TIMEOUT`   | `1200`  | Hard timeout for entire execution |

## How It Works

```
User → Claude Code → MCP bridge (FastMCP) → agy CLI → Gemini API
                   ←                      ←         ←
```

1. `CLAUDE.md` instructs Claude when to delegate
2. Claude calls `delegate_to_agy(prompt, cwd, files?)` via MCP
3. `bridge.py` prepends file paths to the prompt
4. Runs `agy --dangerously-skip-permissions --add-dir <cwd> -p "<prompt>"`
5. Returns the text output cleanly or raises an exception natively handled by [FastMCP](https://github.com/jlowin/fastmcp)

## Development

```bash
# Linting & Formatting
uv run ruff check .
uv run ruff format .

# Type Checking
uv run pyright

# Tests
uv run pytest

# Pre-commit Hooks (Run before committing)
uv run pre-commit install
```

## License

MIT
