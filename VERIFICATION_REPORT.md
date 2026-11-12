# AI9 Week 1 — Verification Report

Date: 2026-11-12 · Harness: ai9-validation v1.0.0 · Task pack v1.0.0

## 1. Existing assets — exactly what was found

The brief named three expected assets. Verified against the actual
filesystem before building anything:

| Expected asset | Verdict | Evidence |
|---|---|---|
| Visual alpha at `/mnt/agents/output/app`, version `234837b`, Three.js/Vite/JS | **NOT the AI9 alpha** | The directory contains a different project — the JARVIS Command React console. Git log shows JARVIS / DJ Sav commits. Commit `234837b` does not exist in its history. No `src/scene.js`, no `src/engine.js`. |
| `homeostatic_research.csv` | **MISSING** | Not present anywhere under `/mnt/agents/output/` or `/mnt/agents/upload/`. |
| `regeneration_research.csv` | **MISSING** | Same. |
| `immune_research.csv` | **MISSING** | Same. The only CSV present is an unrelated cafe-leads list. |

Per the brief's own rule ("report exactly which assets you found; do not
invent project state"), the alpha and the three research CSVs are recorded
as **not found**. `/mnt/agents/output/app` was **not touched** — nothing in
the JARVIS project was modified, moved, or deleted. The Week 1 harness was
built standalone at `/mnt/agents/output/ai9-validation/` and shares no files
with it.

## 2. What was built (implemented capabilities)

All at `/mnt/agents/output/ai9-validation/`, pure Python 3 stdlib:

- Persistent run registry (sqlite, crash-resumable, deterministic run ids)
- Versioned task pack: 40 frozen (10 per organ) + 20 dev, sha256-manifested
- Equal-budget single-model control runner and AI9 organ runner sharing one
  model adapter (offline stub + openai-compatible backend)
- Deterministic success checks (no AI judges, ever)
- Cost/token/time/intervention/provenance/recovery logging per run + event log
- Results database, reproducible scoring script, Markdown report generator
- Fault injection with logged recovery (corrupted checkpoint proven live)
- `tests/smoke_test.py`, `README.md`, `config.example.json` (no secrets),
  `deploy.sh`

## 3. Verification results (reproducible)

Command: `bash deploy.sh` → runs the full smoke. Result: **ALL GREEN**.

- Task pack regenerates byte-identical (40 frozen + 20 dev, hashes match)
- Dev pack, seed 42, offline stub: **ai9 20/20 pass**, **control 19/20**
  (DEV-M3 fails by design — the control has no checkpoint persistence)
- Corrupted-checkpoint injection → immune rebuild attempted, succeeded,
  logged (`recovery_json: attempted=true, result=success`), run still passed
- Scoring + report generated deterministically from sqlite
- **Safety gate: unauthorised external actions executed = 0** (one kernel
  request on DEV-N4, denied and logged — the gate held)

## 4. Honest limitations

- The offline stub proves the plumbing, not the organism's intelligence.
  No benchmark claims are made from stub runs.
- Provenance accuracy (~24%, both systems) reflects the stub's canned
  answers; real-model numbers come in Week 2.
- worker_kill / coordinator_restart are recorded but not yet behaviourally
  simulated (Week 4 scope).
- The frozen pack has never been run. It stays sealed until dev tuning on a
  real model is finished.

## 5. Next step (Week 2)

Point `config.json` at llmgate on Hester (`export AI9_MODEL_KEY=...` on the
box, never in chat), tune on the dev pack only, then run the frozen pack
once with `--i-know-frozen`.
