---
description: Reference and helper for working with Claude Squad (the `cs` multi-agent TUI)
---

# Claude Squad helper

Claude Squad is a terminal manager for multiple AI coding agents (Claude Code, Aider,
Codex, Amp). It is installed on this machine as the `cs` command. The full developer
guide lives in this repo's `CLAUDE.md` and `docs/claude-squad-developer-guide.md`.

When this command is invoked, help the user with whatever follows in `$ARGUMENTS`.
If no arguments are given, summarize the most useful commands below and ask what they
want to do.

## Quick reference

| Goal | Command |
| --- | --- |
| Start the TUI | `cs` |
| Auto-accept prompts (unattended) | `cs --autoyes` |
| Use a custom agent program | `cs --program "aider --model ollama_chat/gemma3:1b"` |
| Print version | `cs version` |
| Show config paths | `cs debug` |
| Reset all stored sessions | `cs reset` |
| Help | `cs --help` |

## In-app keys

- `n` new session · `N` new session with prompt · `D` kill session
- `↵/o` attach · `ctrl-q` detach · `s` commit & push · `c` checkout (commit + pause) · `r` resume
- `tab` switch preview/diff · `q` quit · `?` help

## Notes for this environment

- Requires a TTY — `cs` will not run inside a non-interactive script or CI shell
  (error: "could not open a new TTY"). Run it from an interactive terminal.
- Prerequisite `tmux` is present. `gh` (GitHub CLI) is **not** installed here, so the
  in-app `s` (commit & push to GitHub) action will not work until `gh` is available.
- Config dir: `~/.claude-squad/` · Logs: `/tmp/claudesquad.log`.
