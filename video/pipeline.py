"""script -> plan (memory-informed) -> cost gate -> generate -> stitch -> remember."""
from __future__ import annotations

import os
import tempfile

from .plan import plan_shots
from .stitch import stitch


def make_video(script: str, out: str, provider, ai=None, title: str = "untitled", approved_budget: float = 0.0) -> dict:
    shots = plan_shots(script, ai)
    if not shots:
        raise ValueError("empty script")
    est = provider.estimate_cost(shots)
    if provider.paid and est > approved_budget:        # never spend without an approved number
        raise PermissionError(f"estimated ${est:.2f} exceeds approved budget ${approved_budget:.2f}")
    work = tempfile.mkdtemp()
    clips = [provider.generate(s, os.path.join(work, f"{s.idx:02d}.mp4")) for s in shots]
    stitch(clips, out)
    if ai is not None:
        ai.save("jamie", f"Video '{title}' made from {len(shots)} shots in the style recalled from memory.", "video-pipeline")
    return {"out": out, "shots": len(shots), "estimated_usd": est}


def rate(ai, title: str, liked: bool, why: str) -> bool:
    """Feedback loop: Jamie's reaction becomes a memory that shapes the next plan."""
    return ai.save("jamie", f"Jamie {'liked' if liked else 'disliked'} video '{title}': {why}", "video-feedback")
