"""Stage 2: the seven rings. Each ring is a plain function over a backend that
exposes all()/add()/delete()/commit() (LocalBackend today; Hindsight needs list
and delete calls added before these run against the cloud bank).

Every ring is idempotent and skips DNA (is_dna) memories.
Pluggable AI parts (summarizer, contradicts, checker) default to cheap rules so
the rings run and test offline; swap in model calls for real use.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Callable

from .memory import Memory, _tokens, now_iso
from .safety import Refused, sanitize


def _jac(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def _live(backend):
    return [m for m in backend.all() if m.status == "active" and not m.is_dna]


# ---- 7. Checker twin ------------------------------------------------------
Checker = Callable[[Memory], tuple[bool, str]]


def rule_checker(m: Memory) -> tuple[bool, str]:
    """Offline stand-in. Real use: make_llm_checker with a DIFFERENT model."""
    if len(m.what.split()) < 3:
        return False, "too short to be a fact"
    if m.what.strip().endswith("?"):
        return False, "a question, not a fact"
    return True, "ok"


def make_llm_checker(review: Callable[[str], str], checker_model: str, agent_model: str) -> Checker:
    """review(prompt)->'YES'/'NO: reason' from a different provider/model."""
    if checker_model == agent_model:
        raise ValueError("checker twin must be a DIFFERENT model from the agent")

    def check(m: Memory) -> tuple[bool, str]:
        out = review("Is this a true, durable, non-sensitive business fact worth remembering? "
                     f"Reply YES or NO: reason.\n\n{m.what}").strip()
        return out.upper().startswith("YES"), out
    return check


# ---- 1. Save (every few minutes) -----------------------------------------
def ring_save(queue: list[Memory], backend, checker: Checker = rule_checker) -> dict:
    """Drain pending saves: safety filter -> checker twin -> commit."""
    stats = {"saved": 0, "rejected": 0}
    pending, queue[:] = list(queue), []
    for m in pending:
        try:
            m.what = sanitize(m.what)
        except Refused:
            stats["rejected"] += 1
            continue
        ok, _ = checker(m)
        if ok:
            backend.add(m); stats["saved"] += 1
        else:
            stats["rejected"] += 1
    return stats


# ---- 2. Rollup (every few hours) -----------------------------------------
def _clean(note: str) -> str:
    n = re.sub(r"(?i)^\s*(please\s+)?(remember|note)( that)?[:,]?\s*", "", note).strip()
    return (n[:1].upper() + n[1:]).rstrip(".") + "." if n else n


def ring_rollup(backend, summarize: Callable[[list[str]], list[str]] | None = None) -> dict:
    """Raw notes -> clean facts. Raw notes are kept (status=rolled), not deleted."""
    raw = [m for m in _live(backend) if m.source != "rollup"]
    n = 0
    for m in raw:
        facts = summarize([m.what]) if summarize else [_clean(m.what)]
        for f in facts:
            if f:
                backend.add(Memory(who=m.who, what=f, source="rollup", when=m.when))
        m.status = "rolled"; n += 1
    backend.commit()
    return {"rolled": n}


# ---- 3. Dedupe ------------------------------------------------------------
def ring_dedupe(backend, threshold: float = 0.8) -> dict:
    items = sorted(_live(backend), key=lambda m: m.when)
    gone = set(); merged = 0
    for i, a in enumerate(items):
        if a.id in gone:
            continue
        for b in items[i + 1:]:
            if b.id not in gone and _jac(_tokens(a.what), _tokens(b.what)) >= threshold:
                a.recall_count += b.recall_count          # keep the older, absorb the newer
                gone.add(b.id); backend.delete(b.id); merged += 1
    backend.commit()
    return {"merged": merged}


# ---- 4. Fade (never DNA) --------------------------------------------------
def ring_fade(backend, decay: float = 0.9, floor: float = 0.05) -> dict:
    """Unused since last pass: score *= decay. Used: score recovers."""
    faded = 0
    for m in backend.all():
        if m.is_dna:
            continue
        if m.recall_count == m.fade_seen:
            m.score = max(floor, m.score * decay); faded += 1
        else:
            m.score = min(1.0, m.score + 0.1)
        m.fade_seen = m.recall_count
    backend.commit()
    return {"faded": faded}


# ---- 5. Link --------------------------------------------------------------
def ring_link(backend, threshold: float = 0.3) -> dict:
    items = _live(backend)
    parent = {m.id: m.id for m in items}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if _jac(_tokens(a.what), _tokens(b.what)) >= threshold:
                parent[find(a.id)] = find(b.id)
    for m in items:
        m.cluster = find(m.id)
    backend.commit()
    return {"clusters": len({m.cluster for m in items})}


# ---- 6. Conflict: flag, keep dates, newest true fact wins -----------------
_NUM = re.compile(r"\d+(?:\.\d+)?")
_NEG = re.compile(r"(?i)\b(not|never|no longer|don't|doesn't|cannot|can't)\b")


def default_contradicts(a: Memory, b: Memory) -> bool:
    """Same topic (token overlap) but different numbers, or flipped negation."""
    if _jac(_tokens(a.what), _tokens(b.what)) < 0.35:
        return False
    if set(_NUM.findall(a.what)) != set(_NUM.findall(b.what)):
        return True
    return bool(_NEG.search(a.what)) != bool(_NEG.search(b.what))


def ring_conflict(backend, contradicts: Callable[[Memory, Memory], bool] = default_contradicts) -> dict:
    """Older side is marked superseded (kept, with its date, for audit); newest wins."""
    items = sorted(_live(backend), key=lambda m: m.when)
    flagged = []
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a.status == "active" and b.status == "active" and contradicts(a, b):
                a.status = "superseded"
                a.what += f" [superseded {now_iso()[:10]} by newer fact dated {b.when[:10]}]"
                flagged.append((a.id, b.id))
                break
    backend.commit()
    return {"conflicts": len(flagged), "pairs": flagged}


RINGS = ["save", "rollup", "dedupe", "fade", "link", "conflict"]
