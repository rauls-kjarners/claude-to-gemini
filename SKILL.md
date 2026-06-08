---
name: claude-to-agy
description: Offloads heavy, token-intensive reasoning and search tasks to Antigravity CLI (agy) via MCP. MANDATORY delegation for grep, git diff, git log, large files, multi-file analysis.
---

# Skill: claude-to-agy

This workspace is equipped with a custom MCP bridge that connects Claude to the local `agy` CLI. It enables Claude to safely delegate massive reasoning tasks, huge file reads, and web searches without exhausting its own context window.

## The routing gate — consume vs. operate

Before any read, search, or analysis, decide which mode you're in:

- **Operate-on** — you're about to edit, refactor, or implement in this code. Keep it in your own context, regardless of size. You cannot edit well from someone else's summary.
- **Consume-and-discard** — you want a verdict, not the bytes (audits, searches, reviews, history, external research). This is a candidate for offloading to agy.

This gate scopes every delegation rule below — size thresholds and the grep/git defaults apply to _consume-and-discard_ only. **Never delegate a file you're about to operate on.** And if a review is likely to lead straight into editing the same file, read it locally once rather than delegate-then-read (otherwise you fetch it twice).

## Terminal Command Delegation - MANDATORY

**BEFORE** running ANY of these commands in a terminal, you MUST use `delegate_to_agy` instead:

- `grep` / `git diff` / `git log` — delegate by default, because output size is unpredictable before you run it.
  **Exception:** when you can bound it small and need it inline — `git log -n 5`, `git diff --stat`, a `git diff` of the single file you just touched — run it directly.

**NEVER** run unbounded versions of these commands directly. No exceptions.

## When to Use `delegate_to_agy`

You should automatically use this tool whenever you encounter:

1. **Large files:** Analyzing log files, database dumps, or any file >200 lines. When in doubt, delegate.
2. **Massive context:** Trying to process more than 3 files at once.
3. **Heavy search tools:** Needing to perform `git log`, `git diff`, or `grep`.
4. **Web/external knowledge:** Web searches and documentation lookups.
5. **Adversarial review / plan critique:** Always delegate.

## How to Delegate

- **Always pass `cwd`** with your current working directory (absolute path) so agy knows where the project is.
- Formulate a clear, detailed `prompt` explaining exactly what needs to be found, analyzed, or searched.
- Optionally pass relevant file paths in the `files` array.
- Await the text response and use the summary/data provided by agy to fulfill the user's request.

## Configuration

The bridge supports environment variables for tuning:

- `AGY_CONNECT_TIMEOUT` - subprocess start timeout in seconds (default: `60`)
- `AGY_TOTAL_TIMEOUT` - total execution timeout in seconds (default: `600`)

## Setup Instructions (for users)

If the tool is not already active in your Claude Code environment, run the following command to register it:

```bash
cd ~/.claude-to-agy && uv sync
claude mcp add -s user claude-to-agy ~/.claude-to-agy/.venv/bin/python ~/.claude-to-agy/src/claude_to_agy/bridge.py
```

## Subagent Enforcement (Hooks)

Subagents do **not** read skill/CLAUDE.md rules and will run `grep`, `git diff`, etc. directly. Add the following PreToolUse hook to `~/.claude/settings.json` to block banned commands for **all** agents:

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
