"""The orchestrator.

Runs the full pipeline and writes a project directory:

  projects/<slug>/
    final.html       # the playable video
    production.json  # the composed plan
    checkpoint.json  # brief + decision log + review report (resumable record)

There is no code "engine" driving creative choices — each stage is a small,
inspectable function, and every decision is appended to a decision log, in the
spirit of OpenMontage's auditable decision trail.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import List

from .brief import parse_brief
from .script import write_script
from .sceneplan import plan_scenes, total_duration
from .assets import build_assets
from .compose import build_production, render_html
from .review import review
from .styles import get_playbook


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (s or "untitled")[:48]


@dataclass
class Result:
    project_dir: str
    html_path: str
    production: dict
    review_report: dict
    decisions: List[dict] = field(default_factory=list)
    passed: bool = True


def run_pipeline(request: str, out_root: str = "projects") -> Result:
    decisions: List[dict] = []

    def log(stage: str, choice: str, why: str):
        decisions.append({"stage": stage, "choice": choice, "why": why})

    # Stage 0 — brief
    brief = parse_brief(request)
    log("brief", f"{brief.duration_s}s / {brief.profile} / {brief.tone}",
        "parsed from the request text")

    # Style selection
    pb = get_playbook(brief.tone)
    log("style", pb["name"], f"matched to tone '{brief.tone}'")

    # Stage 1 — script
    script = write_script(brief)
    log("script", f"{script.backend} backend, {len(script.beats)} beats",
        "LLM used when credentials present, else deterministic template")

    # Stage 2 — scene plan
    scenes = plan_scenes(script, brief.duration_s)
    log("scene_plan", f"{len(scenes)} scenes, {total_duration(scenes):.1f}s",
        "durations weighted by narration length, scaled to target")

    # Stage 3 — assets
    visuals = build_assets(scenes, brief.tone)
    log("assets", f"{len(visuals)} synthesized vector scenes",
        "computed gradients + motif from the style playbook (no image model)")

    # Stage 4 — compose
    production = build_production(brief, script, scenes, visuals)
    html = render_html(production)
    log("compose", "self-contained HTML player",
        "Remotion/FFmpeg unavailable offline; HTML video is the deliverable")

    # Stage 5 — review (gate)
    passed, report = review(scenes, brief.duration_s, brief.narration)
    log("review", "passed" if passed else "FAILED",
        "; ".join(report["findings"]) if report["findings"] else "all gates green")

    # Write project
    slug = _slug(script.title or brief.topic)
    project_dir = os.path.join(out_root, slug)
    os.makedirs(project_dir, exist_ok=True)
    html_path = os.path.join(project_dir, "final.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)
    with open(os.path.join(project_dir, "production.json"), "w", encoding="utf-8") as f:
        json.dump(production, f, indent=2, ensure_ascii=False)
    with open(os.path.join(project_dir, "checkpoint.json"), "w", encoding="utf-8") as f:
        json.dump(
            {
                "request": request,
                "brief": brief.to_dict(),
                "decisions": decisions,
                "review": report,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    return Result(
        project_dir=project_dir,
        html_path=html_path,
        production=production,
        review_report=report,
        decisions=decisions,
        passed=passed,
    )
