"""Trend input. OFFLINE import only: Jamie/Kimi supply trends (hand-curated or from an allowed API).
No scraping here - platform terms differ and must be checked before any automated collector is added."""
from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class Trend:
    name: str          # e.g. "POV storytime format"
    source: str        # where it was seen
    velocity: float    # 0-10 how fast it is rising (human/API judgement)
    note: str = ""


def load_trends(path: str) -> list[Trend]:
    with open(path) as f:
        return [Trend(**d) for d in json.load(f)]


def rank_trends(trends: list[Trend], k: int = 3) -> list[Trend]:
    return sorted(trends, key=lambda t: -t.velocity)[:k]
