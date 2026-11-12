# AI9 Validation Harness — Week 1

The measurement rig for the AI9 four-organ artificial organism (Research,
Memory, Routines, Money). It answers one question with numbers, not vibes:
**does the organism beat a single model given the same brain and the same
budget — and can we prove it?**

Pure Python 3 standard library. No pip installs, no network, no keys needed
for the offline smoke. Runs on a Mac or any Linux box.

## What is built and working now (implemented)

- **Persistent run registry** — `results/results.db` (sqlite). Every run is
  registered before it starts, so a crash mid-batch leaves a `queued` row and
  a rerun resumes exactly where it stopped. Run ids are deterministic
  (`sha256(task|system|seed|repeat)`), so the same run is never double-counted.
- **Versioned benchmark task pack** — `taskpack/`. 65 tasks: **40 frozen**
  (10 per organ) + **25 dev** (20 generated + 5 hand-written TREND tasks). Every task file is sha256-manifested in
  `taskpack/pack.json`. Regenerating the pack must produce identical hashes or
  the harness refuses to treat results as comparable. `run_benchmark.py`
  now enforces this: it checks every task file against the manifest before
  running and stops if a file was changed, added or removed. Hand-written dev
  tasks are registered (never rewritten) by `python3 taskpack/gen.py`.
- **Live console** — `index.html` + `organism.py`. Reads `results/results.db`
  read-only and shows the organism against the control as runs land. See
  "The console" below.
- **Single-model control runner** — `ai9lab/control_runner.py`. One model,
  one call, whole task. This is the yardstick.
- **AI9 runner** — `ai9lab/ai9_runner.py`. The 5-stage local cycle
  (sense → model → decide → act/verify → learn) with checkpoints at each
  stage, a kernel permission gate, and packet-logged provenance. Same model
  adapter, same budget as the control.
- **Deterministic success checks** — `ai9lab/checks.py`. Every check is a
  mechanical rule (contains/regex/ranking order/citation counts/json fields/
  state files/refusal behaviour/external-action caps). No AI judges anything.
- **Cost / token / time / intervention / provenance / recovery logging** —
  every run row carries the lot, plus an event log per run
  (`results/run-*/events.json`).
- **Results database + reproducible scoring** — `ai9lab/score.py` computes
  the Week-1 metrics straight from sqlite: verified success rate, cost per
  success, interventions per success, provenance accuracy, recovery rate,
  duplicate-action rate, energy per success, duration/recovery medians + p95.
  Deterministic — same db in, same numbers out.
- **Report generator** — `ai9lab/report.py` renders the Markdown comparison
  table and safety snapshot from `scores.json`.
- **Fault injection** — `--inject corrupted_checkpoint | duplicate_packet |
  energy_depletion | worker_kill`. Corrupted checkpoints are rebuilt by the
  immune path and the recovery (attempted, result, seconds, cost) is logged.
  Worker-kill and coordinator-restart are recorded from Week 1; their full
  behavioural simulations land with the Week 4 build.
- **Offline stub adapter** — deterministic canned model for harness
  validation at $0. **Never used for benchmark claims** — it exists to prove
  the plumbing. Real runs go through the openai-compatible backend (e.g.
  llmgate on Hester).

## What is future architecture (not built yet)

- Live external actions (Week 1: `permitted_external_actions` is always `[]`;
  the kernel denies everything and the denial is logged).
- Behavioural worker-kill / coordinator-restart simulations (Week 4).
- The frozen 40-task pack has not been run against a real model yet — that
  is the Week 2 job, once, after dev tuning is done.

## The frozen law

- The **frozen** pack is run for measurement only. All tuning happens on the
  **dev** pack. Running frozen repeatedly while tuning voids the benchmark.
  `run_benchmark.py` demands `--i-know-frozen` for frozen runs.
- No AI calculates or alters scores. Scoring is sqlite + arithmetic.
- Raw successes and failures are preserved — nothing is deleted, ever.

## Layout

```
ai9-validation/
├── ai9lab/                 # the harness
│   ├── adapter.py          # shared model adapter (offline-stub / openai-compat)
│   ├── core.py             # run context, packets, checkpoints, injection, recovery
│   ├── control_runner.py   # single-model yardstick
│   ├── ai9_runner.py       # the organism: 5-stage cycle + kernel gate
│   ├── checks.py           # deterministic success checks
│   ├── db.py               # sqlite run registry (crash-resumable)
│   ├── score.py            # metrics, no AI
│   ├── report.py           # markdown report
│   └── run_benchmark.py    # CLI entry
├── taskpack/               # 40 frozen + 20 dev tasks + generators + manifest
├── tests/                  # smoke_test.py (end-to-end, $0), test_harness.py, test_organism.py
├── ai9.py                  # one entry point: smoke | dev | score | console | doctor
├── index.html              # the console page (single file, no libraries)
├── organism.py             # console back end: reads results.db read-only, serves the page
├── config.example.json     # model config template (no secrets)
├── deploy.sh               # one-command setup + smoke on any box
└── results/                # runs.db, per-run outputs, scores.json, report.md
```

## Quick start

```bash
cd ai9-validation
cp config.example.json config.json     # offline stub = default, free
python3 ai9.py smoke                   # proves everything below in ~1 min
python3 ai9.py dev                     # dev pack, both systems, then score + report
python3 ai9.py console --lan           # live console; --lan lets a phone on the same network open it
python3 ai9.py doctor                  # checks page, database, task pack, scores, port
```

The smoke test works in `results-smoke/` and never touches `results/`, so it
is safe to run on a box that holds real benchmark results.

## The console

`python3 ai9.py console` serves `index.html` at `http://127.0.0.1:8369/` and
pushes an update to the open page whenever `results/results.db` changes.

- The database is opened **read-only**. The console never writes to it.
- Scoreboard pass/total is counted the way `score.py` counts it (verified
  successes over completed runs), one row per system and model. Dev and
  frozen are never blended.
- The "Organism vs control" table shows `results/scores.json` **as written by
  score.py**. The console recomputes none of it, and says so when the file is
  older than the runs.
- Organ lights read what the harness logs: sourced claims (SENSE), runs in
  progress or the last outcome (MODEL), external actions requested vs executed
  (DECIDE), verified runs, recoveries and task-pack integrity (VERIFY), runs
  logged and duplicate actions (LEARN).
- Runs made with the offline stub are labelled as such on the page.
- It serves only the page, `status.json` and a change feed, on this machine
  unless `--lan` is given. No keys are read, stored or shown.

## Running a benchmark

```bash
# dev pack, both systems (this is the tuning loop)
python3 -m ai9lab.run_benchmark --system ai9 --pack dev --repeat 1 --seed 42
python3 -m ai9lab.run_benchmark --system control --pack dev --repeat 1 --seed 42

# fault-injection demo
python3 -m ai9lab.run_benchmark --system ai9 --pack dev --seed 97 \
    --tasks DEV-M1 --inject corrupted_checkpoint

# score + report (reproducible, no AI)
python3 -m ai9lab.score --db results/results.db --out results/scores.json
python3 -m ai9lab.report --scores results/scores.json --out results/report.md

# the frozen pack — measurement only, when dev tuning is done
python3 -m ai9lab.run_benchmark --system ai9 --pack frozen --repeat 3 \
    --seed 42 --i-know-frozen
```

## Pointing it at a real model

`config.json`:

```json
{
  "model": {
    "backend": "openai-compatible",
    "model": "flint",
    "base_url": "http://<your-model-host>:4000/v1",
    "key_env": "AI9_MODEL_KEY",
    "price_per_m_in": 0.14,
    "price_per_m_out": 0.28,
    "timeout_sec": 120
  }
}
```

The key is read from the environment variable named in `key_env` — never
from the file, never printed:

```bash
export AI9_MODEL_KEY='...'   # loaded on the box, not in chat
```

Both runners use the identical adapter with identical per-task budgets
(`token_limit`, `cost_limit` from the task file), so control vs organism is
an equal-budget comparison by construction.

## Current measured state (dev pack, offline stub, seed 42)

| Metric | control | ai9 |
|---|---|---|
| verified success rate | 95.0% (19/20) | 100% (20/20) |
| recovery rate | n/a (no recovery machinery) | 100% (1/1 injected faults) |
| unauthorised external actions | 0 | 0 |
| duplicate action rate | 0% | 0% |

The one control failure (DEV-M3) is real signal, not a bug: the control has
no checkpoint persistence, so the resumption check fails. That is exactly
the kind of gap this harness exists to measure. Stub-era provenance accuracy
(~24% both systems) reflects the canned stub's terse answers, not a real
model's citation behaviour — expect it to move with a live backend.

## Working on this repo with an AI builder (Fable 5.2 / any hand)

This repo is the AI9 week-1 validation harness — the backend brain testbench.
Rules for any AI hand touching it:

1. NO KEYS. Configs reference key NAMES only (`key_env`). Never write key values, .env files, or real endpoints into this repo.
2. Pure Python 3 stdlib. No pip installs. Prove changes with `python3 tests/smoke_test.py` before committing.
3. Deterministic run ids (sha256 of task|system|seed|repeat) — never double-count runs; the registry resumes after crashes.
4. Thinking models: set `"thinking": true` in the config's model block — the runner then allows up to min(8000, token_limit) answer tokens (default path unchanged: min(3000, token_limit//2)).
5. The frozen pack is measurement-only. Never run it while tuning. Never touch frozen task files.
6. scores.json / report.md are generated by score.py / report.py — no AI writes or edits scores.
7. New tasks go in taskpack/dev/ following the existing JSON shape, with keyword checks in `checks`.
8. Backups: before replacing any file, keep a copy named <file>.bak-<change-id>.
