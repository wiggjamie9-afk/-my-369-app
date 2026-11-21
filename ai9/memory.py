"""Memory model + backends.

Each memory stores: who, what, when, source, recall_count (Stage 1, rule 3).

Backends:
  LocalBackend      JSON file. Offline, used for tests and the plumbing check.
  HindsightBackend  Hindsight Cloud, ONE shared bank. UNVERIFIED against the
                    live API (no key available when written) - see class doc.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Protocol


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass
class Memory:
    who: str          # who the fact is about / who said it (never a caller name)
    what: str         # the fact itself
    source: str       # where it came from (e.g. "jamie-chat", "rollup")
    when: str = field(default_factory=now_iso)
    recall_count: int = 0
    score: float = 1.0  # used by Stage 2 "fade"
    id: str = ""
    status: str = "active"   # active | rolled | superseded (Stage 2)
    cluster: str = ""        # set by the link ring
    is_dna: bool = False     # DNA is never faded/merged/superseded
    fade_seen: int = 0       # recall_count at the last fade pass

    def __post_init__(self):
        if not self.id:
            self.id = hashlib.sha256(f"{self.who}|{self.what}".encode()).hexdigest()[:16]


class Backend(Protocol):
    def add(self, m: Memory) -> None: ...
    def search(self, query: str, k: int = 5) -> list[Memory]: ...


def _tokens(s: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9']+", s.lower()) if len(t) > 2}


class LocalBackend:
    def __init__(self, path: str):
        self.path = path
        self.items: dict[str, Memory] = {}
        if os.path.exists(path):
            with open(path) as f:
                self.items = {d["id"]: Memory(**d) for d in json.load(f)}

    def _flush(self):
        with open(self.path, "w") as f:
            json.dump([asdict(m) for m in self.items.values()], f, indent=1)

    def add(self, m: Memory) -> None:
        if m.id in self.items:       # same fact again: keep one copy
            return
        self.items[m.id] = m
        self._flush()

    def all(self) -> list[Memory]:
        return list(self.items.values())

    def delete(self, mid: str) -> None:
        self.items.pop(mid, None)

    def commit(self) -> None:
        self._flush()

    def search(self, query: str, k: int = 5) -> list[Memory]:
        q = _tokens(query)
        scored = []
        for m in self.items.values():
            if m.status != "active":
                continue
            overlap = len(q & _tokens(m.what + " " + m.who))
            if overlap:
                scored.append((overlap * m.score, m))
        scored.sort(key=lambda t: -t[0])
        hits = [m for _, m in scored[:k]]
        for m in hits:
            m.recall_count += 1
        if hits:
            self._flush()
        return hits


class HindsightBackend:
    """Hindsight Cloud, one shared bank.

    UNVERIFIED: endpoint paths follow Hindsight's documented REST shape
    (retain -> POST .../banks/{bank}/memories, recall -> POST
    .../banks/{bank}/memories/recall) but were written without a live key.
    Base URL, bank id and key come from env: HINDSIGHT_BASE_URL,
    HINDSIGHT_BANK_ID, HINDSIGHT_API_KEY. Fix paths here if the first live
    call returns 404 - nothing else in AI9 depends on them.

    Hindsight does not track our recall_count, so it is kept in a small
    sidecar file keyed by memory id.
    """

    def __init__(self, base_url=None, bank_id=None, api_key=None, counts_path="ai9_counts.json"):
        self.base = (base_url or os.environ.get("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")).rstrip("/")
        self.bank = bank_id or os.environ.get("HINDSIGHT_BANK_ID", "ai9-shared")
        self.key = api_key or os.environ["HINDSIGHT_API_KEY"]
        self.counts_path = counts_path
        self.counts = json.load(open(counts_path)) if os.path.exists(counts_path) else {}

    def _post(self, path: str, body: dict) -> dict:
        req = urllib.request.Request(
            f"{self.base}/v1/default/banks/{self.bank}{path}",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)

    def add(self, m: Memory) -> None:
        payload = json.dumps(asdict(m))
        self._post("/memories", {"items": [{"content": m.what, "context": payload, "timestamp": m.when}]})

    def search(self, query: str, k: int = 5) -> list[Memory]:
        res = self._post("/memories/recall", {"query": query, "max_tokens": 2000})
        out = []
        for r in (res.get("results") or [])[:k]:
            ctx = r.get("context")
            try:
                m = Memory(**json.loads(ctx))
            except Exception:
                m = Memory(who="unknown", what=r.get("text", ""), source="hindsight")
            m.recall_count = self.counts.get(m.id, m.recall_count) + 1
            self.counts[m.id] = m.recall_count
            out.append(m)
        json.dump(self.counts, open(self.counts_path, "w"))
        return out
