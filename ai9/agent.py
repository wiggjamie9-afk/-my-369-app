"""AI9 core loop (Stage 1, rules 1-3).

  answer(q):  recall BEFORE answering, always.
  after the answer: save anything important (via safety filter).

`llm` is any callable (system:str, user:str) -> str, so the model is swappable.
`judge_important` decides what to save; default is a cheap heuristic and can be
replaced with an LLM call.
"""
from __future__ import annotations

import re
from typing import Callable

from . import dna
from .memory import Backend, Memory
from .safety import Refused, sanitize

LLM = Callable[[str, str], str]

_IMPORTANT = re.compile(r"(?i)\b(remember|note that|important|from now on|our |we (are|use|open|close|charge)|is (called|named)|costs?|price|deadline|always|never)\b|\d")


def default_important(text: str) -> bool:
    return bool(_IMPORTANT.search(text)) and not text.strip().endswith("?")


class AI9:
    def __init__(self, backend: Backend, llm: LLM, judge_important=default_important, k: int = 5, queue=None):
        self.dna = dna.load()               # refuses to start if tampered
        self.backend, self.llm, self.judge, self.k = backend, llm, judge_important, k
        self.queue = queue                  # Stage 2: if set, saves wait for the checker twin
        self.log: list[str] = []            # audit trail of recall/save calls

    def recall(self, query: str) -> list[Memory]:
        hits = self.backend.search(query, self.k)
        self.log.append(f"recall:{query[:40]}:{len(hits)}")
        return hits

    def save(self, who: str, what: str, source: str) -> bool:
        try:
            clean = sanitize(what)
        except Refused as e:
            self.log.append(f"refused:{e}")
            return False
        m = Memory(who=who, what=clean, source=source)
        (self.queue.append if self.queue is not None else self.backend.add)(m)
        self.log.append("save")
        return True

    def answer(self, user_text: str, who: str = "jamie", source: str = "chat") -> str:
        memories = self.recall(user_text)                      # rule 2: recall first
        ctx = "\n".join(f"- [{m.when[:10]}] {m.who}: {m.what}" for m in memories) or "(none)"
        system = f"{self.dna}\n\n## Recalled memories\n{ctx}"
        reply = self.llm(system, user_text)
        if self.judge(user_text):                              # rule 2: save after important
            self.save(who, user_text, source)
        return reply
