"""Brief -> hooks -> compliant scripts -> (cost-gated) videos -> AI-labelled outputs -> memory."""
from __future__ import annotations

import json
import os
import subprocess

from video.pipeline import make_video
from video.plan import plan_shots

from .compliance import lint
from .hooks import write_hooks

LABEL = "AI-generated"


def _has_drawtext() -> bool:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-filters"], capture_output=True, text=True)
    return "drawtext" in r.stdout


def _label(path: str) -> str:
    """Burn a visible 'AI-generated' label where possible; always return the final path."""
    if not _has_drawtext():
        return path
    out = path.replace(".mp4", ".labelled.mp4")
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-vf",
                        f"drawtext=text='{LABEL}':x=20:y=20:fontsize=28:fontcolor=white:box=1:boxcolor=black@0.5",
                        "-c:a", "copy", out], capture_output=True)
    return out if r.returncode == 0 else path


def build_script(brief, hook: str) -> str:
    facts = " ".join(c.rstrip(".") + "." for c in brief.verified_claims[:2])
    return " ".join(x for x in (hook, facts, brief.cta) if x)


def run_batch(brief, provider, out_dir: str, ai=None, n: int = 3, approved_budget: float = 0.0, llm=None,
              trends=None, captions: bool = False) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    hooks, rejected = write_hooks(brief, n, llm, trends)
    made, blocked = [], [{"hook": h, "why": p} for h, p in rejected]
    for i, hook in enumerate(hooks):
        script = build_script(brief, hook)
        problems = lint(script, brief)                   # lint the FULL script, not just the hook
        if problems:
            blocked.append({"hook": hook, "why": problems}); continue
        vid = f"{brief.brand}-{i:02d}".replace(" ", "_")
        path = os.path.join(out_dir, f"{vid}.mp4")
        info = make_video(script, path, provider, ai, vid, approved_budget)
        if captions:
            from video.captions import burn_captions
            path = burn_captions(path, plan_shots(script), path.replace(".mp4", ".cap.mp4"))
        final = _label(path)
        meta = {"id": vid, "hook": hook, "script": script, "file": final, "ai_generated": True, **info}
        with open(os.path.join(out_dir, f"{vid}.json"), "w") as f:      # disclosure sidecar
            json.dump(meta, f, indent=1)
        made.append(meta)
    return {"made": made, "blocked": blocked}


def record_result(ai, vid: str, hook: str, views: int, clicks: int, spend_usd: float) -> bool:
    """Close the loop: real performance becomes memory so the next batch learns from winners."""
    ctr = round(100 * clicks / views, 2) if views else 0.0
    return ai.save("jamie", f"Ad {vid} with hook '{hook}' got {ctr}% click rate on {views} views, spend {spend_usd} dollars.",
                   "ad-results")
