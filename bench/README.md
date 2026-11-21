# Stage 3 inputs (Jamie supplies - I will not invent "real" data)
- `questions.json`: exactly 50 `{"q": "...", "a": "known answer"}` written BEFORE any testing, from real data. Then `python -m ai9.bench lock`.
- `notes.jsonl`: the real notes to load, one `{"id","who","what","when"}` per line. Caller names/numbers get stripped on ingest.
- Run: `python -m ai9.bench estimate` -> approve the number -> `run --approved-budget N`.
