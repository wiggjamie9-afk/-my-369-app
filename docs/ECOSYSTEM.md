# AI-Coding Ecosystem

A map of the tools wired around this project, what each one does, and how to
install it. The fast path is the bootstrap script:

```bash
bash scripts/setup-ecosystem.sh
```

Run it **on your own machine** — most of these tools configure your local
editor/agent, which a remote or CI sandbox cannot do.

## The stack

| Tool | Role | Where it lives | Install |
|---|---|---|---|
| **ant-design-vue** | UI component library for the app itself | this repo (`package.json`) | `npm install` |
| **code-review-graph** | Tree-sitter structural graph; gives your AI assistant precise, minimal review context via MCP | your machine (MCP) + this repo (CI) | `pipx install code-review-graph && code-review-graph install` |
| **Open Code Review (`ocr`)** | Deterministic-engineering + agent diff reviewer | your machine (CLI) + this repo (CI) | `npm i -g @alibaba-group/open-code-review` |
| **Superpowers** | Claude Code plugin: brainstorm → spec → plan → TDD workflow | your Claude Code client | `/plugin install superpowers@claude-plugins-official` |

## Already wired into this repo

- **`npm install`** pulls in `ant-design-vue` for the app.
- **`.mcp.json`** — project-scoped MCP servers (`code-review-graph`,
  `filesystem`, `playwright`, `github`). Any agent that opens this repo offers
  them automatically — no per-machine setup.
  - The **`github`** server runs via Docker and reads a `GITHUB_PERSONAL_ACCESS_TOKEN`
    from your environment (nothing is committed). Requirements: Docker running,
    and `export GITHUB_PERSONAL_ACCESS_TOKEN=ghp_…` in your shell. Prefer the
    hosted server? Replace the entry with
    `{ "type": "http", "url": "https://api.githubcopilot.com/mcp/" }` and
    authenticate via OAuth in a client that supports it.
- **`.github/dependabot.yml`** — weekly dependency updates for npm (grouped
  minor/patch) and GitHub Actions.
- **`.github/workflows/code-review-graph.yml`** — risk-scored PR reviews in CI
  (local-first; only needs `GITHUB_TOKEN`).
- **`.github/workflows/open-code-review.yml`** — manual-trigger OCR review.
  Requires an `OCR_LLM_TOKEN` repo secret; flip its trigger to
  `on: pull_request` to gate every PR.
- **`.github/workflows/semgrep.yml`** — Semgrep SAST on every PR (OSS rulesets,
  no token needed).
- **`.pre-commit-config.yaml`** — local hooks (whitespace, EOF, YAML/JSON
  checks, prettier). Activated by `pre-commit install` (the bootstrap does it).

## What only you can do (client-side)

A remote sandbox can't write to your local editor config or install Claude Code
plugins (those are in-client slash commands), and it can't fetch the Superpowers
repo through a locked-down proxy. So the editor/agent wiring — Superpowers, and
`code-review-graph install`'s MCP setup — has to run in your own environment.
That's exactly what `scripts/setup-ecosystem.sh` automates, plus the two
slash-command steps it prints at the end.

## Verify

```bash
code-review-graph status      # graph built & MCP reachable
ocr llm test                  # OCR can reach your configured LLM
# In your agent: /mcp         # confirms the code-review-graph MCP server is live
```
