"""Script -> shot list, informed by AI9 memory (brand/style/likes/dislikes)."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Shot:
    idx: int
    text: str            # what is said / shown
    prompt: str          # prompt sent to the video generator
    seconds: float


def plan_shots(script: str, ai=None, max_shots: int = 12) -> list[Shot]:
    """Split on sentences; ~2.5 words/sec, clamped 2-6s. Style comes from memory."""
    style = ""
    if ai is not None:
        hits = ai.recall("video style brand look preferences likes dislikes")
        style = " ".join(m.what for m in hits)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", script.strip()) if s.strip()][:max_shots]
    return [Shot(i, s, f"{s} Style notes: {style}".strip() if style else s,
                 min(6.0, max(2.0, round(len(s.split()) / 2.5, 1)))) for i, s in enumerate(sents)]
