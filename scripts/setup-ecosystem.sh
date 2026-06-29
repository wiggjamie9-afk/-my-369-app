#!/usr/bin/env bash
#
# setup-ecosystem.sh — one-shot installer for the AI-coding ecosystem.
#
# Run this on YOUR OWN machine (not in a remote/CI sandbox), because most of
# these tools wire themselves into your local editor / agent configuration.
#
#   bash scripts/setup-ecosystem.sh
#
# It is idempotent: re-running it just re-checks/updates each tool.
set -uo pipefail

bold()  { printf '\033[1m%s\033[0m\n' "$*"; }
ok()    { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn()  { printf '  \033[33m!\033[0m %s\n' "$*"; }
step()  { printf '\n\033[1m▶ %s\033[0m\n' "$*"; }
have()  { command -v "$1" >/dev/null 2>&1; }

bold "Installing the AI-coding ecosystem…"

# ── 1. code-review-graph (structural graph + MCP for your AI assistant) ───────
step "code-review-graph"
if have pipx; then
  pipx install code-review-graph || pipx upgrade code-review-graph
elif have pip3; then
  pip3 install --user --upgrade code-review-graph
else
  warn "No pip/pipx found — install Python 3.10+ first, then re-run."
fi
if have code-review-graph; then
  ok "installed: $(code-review-graph --version 2>/dev/null)"
  # Auto-detects Codex, Claude Code, Cursor, Windsurf, Zed, Continue, etc.
  # and writes the correct MCP config + hooks for each.
  code-review-graph install || warn "code-review-graph install reported an issue"
  # Build the graph for the current repo if we're inside one.
  if [ -d .git ]; then code-review-graph build || true; fi
fi

# ── 2. Open Code Review (Alibaba) — AI diff-review CLI (`ocr`) ────────────────
step "Open Code Review (ocr)"
if have npm; then
  npm install -g @alibaba-group/open-code-review && ok "installed: $(ocr version 2>/dev/null | head -1)"
  warn "Next: run 'ocr config provider' to set your LLM provider + API key."
else
  warn "No npm found — install Node 18+ first, then re-run."
fi

# ── 3. pre-commit (local quality hooks) ──────────────────────────────────────
step "pre-commit"
if have pipx; then
  pipx install pre-commit || pipx upgrade pre-commit
elif have pip3; then
  pip3 install --user --upgrade pre-commit
fi
if have pre-commit && [ -f .pre-commit-config.yaml ]; then
  pre-commit install && ok "git pre-commit hook installed"
fi

# ── 4. Manual steps (client-only; can't be scripted) ─────────────────────────
step "Manual steps (run these inside your agent/editor)"
cat <<'EOF'
  • Superpowers (Claude Code plugin):
      /plugin install superpowers@claude-plugins-official

  • Open Code Review as a Claude Code slash command (optional):
      /plugin marketplace add alibaba/open-code-review
      /plugin install open-code-review@open-code-review

  • Project MCP servers are committed in .mcp.json (code-review-graph,
    filesystem, playwright). Your agent picks them up automatically — approve
    them when prompted.

  • Restart your editor/agent so new MCP servers and plugins load.
EOF

bold "\nDone. Verify with:  code-review-graph status   &&   ocr llm test"
