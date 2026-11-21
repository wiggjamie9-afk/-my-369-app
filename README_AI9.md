# AI9 looping memory - Stage 1

- `ai9/agent.py`   recall before every answer, save after important things
- `ai9/memory.py`  Memory(who, what, when, source, recall_count); LocalBackend + HindsightBackend (one shared bank)
- `ai9/safety.py`  refuses passwords/keys; strips phone numbers and labelled caller names
- `ai9/dna.py`     locked DNA (`ai9/dna/DNA.md`), hash-checked at every startup; CODEOWNERS = Jamie
- `ai9/recall_test.py`  10 facts, fresh process, scored

Run: `python -m unittest discover -s tests -t .` and `python -m ai9.recall_test`.
After Jamie edits DNA.md: `python -m ai9.dna lock`.

Status: HindsightBackend is unverified (no key yet). Recall test so far = local backend, no real model.
