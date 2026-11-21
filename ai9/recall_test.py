"""Stage 1 recall test (rule 6).

Phase 1 ("tell")  : a session is told 10 facts.
Phase 2 ("ask")   : a FRESH PROCESS (new session, no shared Python state) is
                    asked one question per fact and scored.

Run:   python -m ai9.recall_test            (local backend, offline plumbing check)
       python -m ai9.recall_test hindsight  (live; needs HINDSIGHT_* env vars)

Scoring uses the real answer path (recall -> context -> llm). With no model key
the llm is an "echo" that answers only from recalled context, so the score
measures whether recall surfaced the fact - NOT model quality. Set ANTHROPIC_API_KEY
and pass `--llm claude` for a real-model run (not wired yet; see README_AI9.md).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile

from .agent import AI9
from .memory import HindsightBackend, LocalBackend

# (statement told to AI9, question asked later, substring the answer must contain)
FACTS = [
    ("We open at 8am on weekdays.", "What time do we open on weekdays?", "8am"),
    ("Our main product is called Vitruvian Core.", "What is our main product called?", "Vitruvian Core"),
    ("The standard callout fee is 90 dollars.", "What is the standard callout fee?", "90"),
    ("Our office is in Leeds.", "Which city is our office in?", "Leeds"),
    ("We close at 5pm on Fridays.", "When do we close on Fridays?", "5pm"),
    ("Our accountant is called Priya Shah.", "Who is our accountant?", "Priya Shah"),
    ("Invoices are due within 14 days.", "How many days do invoices have to be paid within?", "14"),
    ("The warranty lasts 2 years.", "How long does the warranty last?", "2 years"),
    ("We never work on Sundays.", "Do we work on Sundays?", "never work on Sundays"),
    ("Our emergency line is staffed by Dan.", "Who staffs the emergency line?", "Dan"),
]


def echo_llm(system: str, user: str) -> str:
    """Answers only from recalled memories (no model): isolates the memory layer."""
    ctx = system.split("## Recalled memories\n", 1)[-1]
    return ctx if ctx.strip() != "(none)" else "I don't know."


def make_backend(kind: str, store: str):
    return HindsightBackend() if kind == "hindsight" else LocalBackend(store)


def main(argv: list[str]) -> int:
    if argv[:1] == ["--phase"]:
        phase, kind, store = argv[1], argv[2], argv[3]
        ai = AI9(make_backend(kind, store), echo_llm)
        if phase == "tell":
            for fact, _, _ in FACTS:
                ai.answer(fact)
            print(json.dumps({"saved": ai.log.count("save")}))
        else:
            right = sum(exp.lower() in ai.answer(q).lower() for _, q, exp in FACTS)
            print(json.dumps({"right": right, "total": len(FACTS)}))
        return 0

    kind = argv[0] if argv else "local"
    store = os.path.join(tempfile.mkdtemp(), "mem.json")
    for phase in ("tell", "ask"):      # separate processes = genuinely fresh session
        out = subprocess.run([sys.executable, "-m", "ai9.recall_test", "--phase", phase, kind, store],
                             capture_output=True, text=True)
        if out.returncode:
            print(out.stderr); return 1
        print(phase, out.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
