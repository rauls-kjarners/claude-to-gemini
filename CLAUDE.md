# Claude-to-Antigravity Delegation Rules

You are equipped with a custom MCP tool called `delegate_to_agy`. You **MUST** use this tool to offload heavy, token-intensive tasks to save your own context window.

## The routing gate - consume vs. operate

Before any read, search, or analysis, decide which mode you're in:

- **Operate-on** - you're about to edit, refactor, or implement in this code. Keep it in your own context, regardless of size. You cannot edit well from someone else's summary.
- **Consume-and-discard** - you want a verdict, not the bytes (audits, searches, reviews, history, external research). This is a candidate for offloading to agy.

This gate scopes every delegation rule below - size thresholds and the grep/git defaults apply to _consume-and-discard_ only. **Never delegate a file you're about to operate on.** And if a review is likely to lead straight into editing the same file, read it locally once rather than delegate-then-read (otherwise you fetch it twice).

## Terminal Command Delegation - MANDATORY

**BEFORE** running ANY of these commands in a terminal, you MUST use `delegate_to_agy` instead:

- `grep` / `git diff` / `git log` - delegate by default, because output size is unpredictable before you run it.
  **Exception:** when you can bound it small and need it inline - `git log -n 5`, `git diff --stat`, a `git diff` of the single file you just touched - run it directly.

**NEVER** run unbounded versions of these commands directly. No exceptions. This applies during ALL phases: planning, exploration, implementation, review.

## Delegation Thresholds - MANDATORY

Use `delegate_to_agy` when ANY of these conditions are met:

1. **File length >200 lines**: Any analysis, review, or reading of files exceeding 200 lines.
2. **Multi-file analysis (>3 files)**: Bug hunting, architecture review, or debugging spanning more than 3 files.
3. **Web/external knowledge**: Any query needing current information or documentation lookups.
4. **Adversarial review / plan critique**: Always delegate.

If you are unsure whether a file is large, delegate it anyway - Antigravity CLI handles the cost, not you.

## STOP & VERIFY

**You are violating these rules if**:

- You delegated a file you were about to **edit** and are now working from agy's summary. Operate-on stays in your context.
- You ran an **unbounded** `grep` / `git diff` / `git log` in-terminal instead of delegating. (Bounded ones like `-n 5` or `--stat` are fine).
- You read or held a large file in context to **audit or review** it instead of delegating.
- You answered a consume trigger from memory instead of verifying - code changes.

## Rationalization Table

| Excuse                                                             | Reality                                                                                                   |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------- |
| "I already know this code."                                        | Code changes. If you're verifying, delegate and check.                                                    |
| "The file is probably small."                                      | If you're consuming and unsure, delegate - don't guess.                                                   |
| "I can answer this directly."                                      | If it's a consume trigger and you're not editing, delegate. Your memory goes stale.                       |
| "It's faster if I just read it."                                   | For consume work, context-budget conservation outranks speed.                                             |
| "I only need a small part of the file."                            | _Consuming_ → delegate the whole file, let agy extract. _Editing_ → read it locally; you need the source. |
| "I'll just delegate this file I'm about to edit."                  | You'll edit from a summary, half-blind, and miss what it dropped. Operate-on stays local.                 |
| "I'll delegate the review, then read the file to make the change." | If the review leads straight to an edit, read it once locally. Don't fetch it twice.                      |

## How to Delegate

- Formulate a clear, detailed `prompt` explaining exactly what needs to be found, analyzed, or searched.
- **Always pass `cwd`** with your current working directory (absolute path) so agy knows where the project is.
- Call `delegate_to_agy` with your `prompt`, `cwd`, and any relevant file paths in the `files` array.
- Await the text response and use the summary/data provided by Antigravity CLI to fulfill the user's request.
