"""Testing loop: pick winners from real results and PROPOSE budget moves. Never spends.

Ranks by the Wilson lower bound of click rate, so 5 clicks on 20 views cannot beat
200 clicks on 5000 views. Ads under `min_views` are 'insufficient data', not losers.
There is deliberately no function here that spends money; a human acts on a proposal.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Result:
    vid: str
    hook: str
    views: int
    clicks: int
    spend_usd: float = 0.0


def wilson_lb(clicks: int, views: int, z: float = 1.96) -> float:
    if views <= 0:
        return 0.0
    p = clicks / views
    d = 1 + z * z / views
    c = p + z * z / (2 * views)
    a = z * math.sqrt((p * (1 - p) + z * z / (4 * views)) / views)
    return max(0.0, (c - a) / d)


def rank(results: list[Result], min_views: int = 500) -> dict:
    ok = [r for r in results if r.views >= min_views]
    return {"ranked": sorted(ok, key=lambda r: -wilson_lb(r.clicks, r.views)),
            "insufficient_data": [r.vid for r in results if r.views < min_views]}


@dataclass
class Proposal:
    moves: list[tuple[str, float]]          # (video id, USD to put behind it)
    total_usd: float
    status: str = "pending"                 # pending -> approved (by a human) ; never auto-executed
    approved_by: str = ""
    notes: list[str] = field(default_factory=list)

    def approve(self, by: str) -> None:
        if not by.strip():
            raise ValueError("a named human must approve")
        self.status, self.approved_by = "approved", by


def propose_budget(results: list[Result], total_usd: float, min_views: int = 500, top_n: int = 3) -> Proposal:
    r = rank(results, min_views)
    winners = r["ranked"][:top_n]
    if not winners:
        return Proposal([], 0.0, notes=["no ad has enough data yet; do not move budget"])
    w = [wilson_lb(x.clicks, x.views) for x in winners]
    tot = sum(w) or 1.0
    return Proposal([(x.vid, round(total_usd * wi / tot, 2)) for x, wi in zip(winners, w)], total_usd,
                    notes=[f"insufficient data: {', '.join(r['insufficient_data'])}"] if r["insufficient_data"] else [])
