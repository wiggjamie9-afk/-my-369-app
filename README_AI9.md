# AI9 looping memory - Stage 1

- `ai9/agent.py`   recall before every answer, save after important things
- `ai9/memory.py`  Memory(who, what, when, source, recall_count); LocalBackend + HindsightBackend (one shared bank)
- `ai9/safety.py`  refuses passwords/keys; strips phone numbers and labelled caller names
- `ai9/dna.py`     locked DNA (`ai9/dna/DNA.md`), hash-checked at every startup; CODEOWNERS = Jamie
- `ai9/recall_test.py`  10 facts, fresh process, scored

Run: `python -m unittest discover -s tests -t .` and `python -m ai9.recall_test`.
After Jamie edits DNA.md: `python -m ai9.dna lock`.

Status: HindsightBackend is unverified (no key yet). Recall test so far = local backend, no real model.

## Stage 2 (built offline, local store only)
`ai9/loops.py` seven rings, `ai9/jobs.py` runner, `ai9/schedule.cron` timings (not installed). Rings need list/delete on the backend, so Hindsight cannot run them yet.

## Stage 3 (harness only - NOT run)
`ai9/bench.py` + `bench/README.md`. Needs Jamie's 50 real questions and notes. `python -m ai9.bench estimate` first; `run` refuses without an approved budget. Tests use simulated models, so no real result exists.
