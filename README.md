# claude-to-agy

[![CI](https://github.com/rauls-kjarners/claude-to-agy/actions/workflows/ci.yml/badge.svg)](https://github.com/rauls-kjarners/claude-to-agy/actions/workflows/ci.yml)
[![CodeQL](https://github.com/rauls-kjarners/claude-to-agy/actions/workflows/codeql.yml/badge.svg)](https://github.com/rauls-kjarners/claude-to-agy/actions/workflows/codeql.yml)
[![codecov](https://codecov.io/github/rauls-kjarners/claude-to-agy/graph/badge.svg?token=QWY0HFQATX)](https://codecov.io/github/rauls-kjarners/claude-to-agy)
[![PyPI version](https://badge.fury.io/py/claude-to-agy.svg)](https://badge.fury.io/py/claude-to-agy)
![Static Badge](https://img.shields.io/badge/OS-Windows-blue)

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

- Windows (agy is spawned in a Windows PTY via `pywinpty`)
- Python 3.10+
- [`agy` CLI](https://antigravity.google/docs/cli-getting-started) installed and authenticated
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)

## Installation

> **Note:** The command below uses [`uvx`](https://docs.astral.sh/uv/guides/scripts/#running-tools) to run the server without manual installation. If you don't have `uv` installed, you can substitute `uvx` with `npx -y` or `pipx run`.

```bash
# 1. Register the MCP server globally via uvx
claude mcp add -s user claude-to-agy uvx claude-to-agy

# 2. Download the delegation rules into your current project
curl -o CLAUDE.md https://raw.githubusercontent.com/rauls-kjarners/claude-to-agy/main/CLAUDE.md
```

That's it. Claude will now automatically delegate heavy tasks to Antigravity CLI in any project that has the `CLAUDE.md` file.

> **Tip:** To enable globally without copying `CLAUDE.md` per project, add the rules to `~/.claude/CLAUDE.md` instead.

### Using as a Skill

This project also includes a `SKILL.md` file, which is the standard format for reusable Claude Code skills. If your setup supports skills, you can use it instead of manually copying `CLAUDE.md`:

```bash
claude skill add https://raw.githubusercontent.com/rauls-kjarners/claude-to-agy/main/SKILL.md
```

> **Note:** You still need the MCP server registered (step 1 above). The skill provides the rules, MCP provides the tool.

## Configuration

All settings are optional environment variables:

| Variable            | Default | Description                                                  |
| ------------------- | ------- | ------------------------------------------------------------ |
| `AGY_TOTAL_TIMEOUT` | `1200`  | Hard timeout (s); also passed to agy as `--print-timeout`    |
| `AGY_DENY_CWD`      | _(empty)_ | `os.pathsep`-separated **absolute** paths. The bridge refuses to run agy in any of these directories (or a subdirectory). Empty = disabled. |

> **Security — the guard is opt-in.** agy is spawned with `--dangerously-skip-permissions`, so it can read/write/execute in the task `cwd` without confirming. Set `AGY_DENY_CWD` to your sensitive repos in the registration (`claude mcp add ... -e AGY_DENY_CWD="C:\path\to\repo"`) and the bridge refuses those directories. It is **off by default** so the bridge stays drop-in; enable it per machine.

## How It Works

```
User → Claude Code → MCP bridge (FastMCP) → agy CLI → Gemini API
                   ←                      ←         ←
```

1. `CLAUDE.md` instructs Claude when to delegate
2. Claude calls `delegate_to_agy(prompt, cwd, files?)` via MCP
3. `bridge.py` prepends file paths to the prompt
4. Spawns `agy --dangerously-skip-permissions --add-dir <cwd> --print-timeout <t>s -p "<prompt>"` inside a Windows PTY (agy emits nothing to a plain pipe — it gates output on `isatty()`)
5. Strips the PTY's VT/ANSI noise and returns clean text, or raises an exception natively handled by [FastMCP](https://github.com/jlowin/fastmcp)

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
