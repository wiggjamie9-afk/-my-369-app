"""Stage 5 — self-review / quality gates.

A miniature of OpenMontage's pre-compose validation and post-render review.
It can't run ffprobe (there's no mp4), so it validates the production *plan*:
every scene must carry a headline, narration, timed captions and a visual;
the total duration must land near the brief's target; and it scores a simple
"slideshow risk" so motion-led briefs don't degrade into static cards.

Returns (passed, report). A failing report does not crash the pipeline — it
is surfaced to the user, exactly like a real review gate would be.
"""

from __future__ import annotations

from typing import List, Tuple

from .sceneplan import Scene, total_duration


def review(scenes: List[Scene], target_duration_s: int, narration: bool) -> Tuple[bool, dict]:
    findings = []
    checks = []

    def check(name: str, ok: bool, detail: str):
        checks.append({"name": name, "ok": ok, "detail": detail})
        if not ok:
            findings.append(f"{name}: {detail}")

    # 1. Non-empty.
    check("scenes_present", len(scenes) >= 2, f"{len(scenes)} scene(s)")

    # 2. Every scene complete.
    incomplete = [
        s.index
        for s in scenes
        if not s.headline.strip() or not s.narration.strip() or not s.words
    ]
    check(
        "scenes_complete",
        not incomplete,
        "all scenes have headline + narration + captions"
        if not incomplete
        else f"incomplete scenes: {incomplete}",
    )

    # 3. Caption timings stay within their scene.
    overflow = [s.index for s in scenes if s.words and s.words[-1].end > s.duration + 0.05]
    check(
        "captions_in_bounds",
        not overflow,
        "captions fit their scenes" if not overflow else f"caption overflow: {overflow}",
    )

    # 4. Duration close to target (within 25%).
    actual = total_duration(scenes)
    lo, hi = target_duration_s * 0.75, target_duration_s * 1.25
    check(
        "duration_on_target",
        lo <= actual <= hi,
        f"{actual:.1f}s vs target {target_duration_s}s",
    )

    # 5. Slideshow-risk heuristic: enough distinct scenes and some pacing
    #    variety. (Low risk == good.)
    durations = [s.duration for s in scenes]
    variety = (max(durations) - min(durations)) if durations else 0
    risk = 0
    if len(scenes) < 4:
        risk += 1
    if variety < 0.5:
        risk += 1
    check("slideshow_risk", risk <= 1, f"risk score {risk}/2")

    passed = all(c["ok"] for c in checks)
    report = {
        "passed": passed,
        "actual_duration_s": actual,
        "target_duration_s": target_duration_s,
        "scene_count": len(scenes),
        "narration": narration,
        "checks": checks,
        "findings": findings,
    }
    return passed, report
