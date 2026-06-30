"""Stage 1 — scriptwriting.

Produces a title plus an ordered list of scene beats (a headline + a line of
narration each). There are two backends:

  * llm   — if the `anthropic` package is importable AND credentials are
            available, Claude authors a grounded, factual script.
  * template — a deterministic narrative-arc scaffold that always works
            offline. It writes the *structure* of a good script (hook ->
            context -> points -> takeaway -> outro) with placeholder-grade
            prose, so the pipeline produces a complete video with zero deps.

The backend used is recorded in the decision log so the output is auditable.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Beat:
    headline: str
    narration: str


@dataclass
class Script:
    title: str
    beats: List[Beat]
    backend: str  # "llm" or "template"


def _scene_count(duration_s: int) -> int:
    # ~5.5s per scene reads comfortably with word-level captions.
    return max(3, min(round(duration_s / 5.5), 14))


# --------------------------------------------------------------------------- #
# Template backend (always available)
# --------------------------------------------------------------------------- #

_ARC = [
    ("hook", "{topic} is more than it first appears."),
    ("context", "To understand it, start with where it comes from and why it matters."),
    ("point", "The first thing to notice about {topic} is how the pieces fit together."),
    ("point", "It shapes the way we think, build, and decide — often quietly."),
    ("point", "Look closer and the details reveal a pattern worth following."),
    ("point", "Each part depends on the others, which is what makes it work."),
    ("turn", "But the real story of {topic} is what it lets us do next."),
    ("takeaway", "Understand this, and the rest starts to make sense."),
    ("outro", "{topic} — a small idea with a long reach."),
]


def _template_script(topic: str, n: int) -> Script:
    topic_title = topic.strip().rstrip(".")
    # Pick an evenly spaced subset of the arc to hit the target scene count,
    # always keeping the first (hook) and last (outro).
    chosen = [_ARC[0]]
    middle = _ARC[1:-1]
    if n > 2 and middle:
        step = max(1, len(middle) // (n - 2)) if n - 2 > 0 else 1
        for i in range(0, len(middle), step):
            if len(chosen) >= n - 1:
                break
            chosen.append(middle[i])
    chosen.append(_ARC[-1])

    headlines = {
        "hook": topic_title.upper(),
        "context": "ORIGINS",
        "point": "HOW IT WORKS",
        "turn": "WHY IT MATTERS",
        "takeaway": "THE TAKEAWAY",
        "outro": topic_title.upper(),
    }
    beats = []
    seen_point = 0
    for kind, line in chosen[:n]:
        hl = headlines.get(kind, topic_title.upper())
        if kind == "point":
            seen_point += 1
            hl = f"POINT {seen_point}"
        beats.append(Beat(headline=hl, narration=line.format(topic=topic_title)))
    return Script(title=topic_title, beats=beats, backend="template")


# --------------------------------------------------------------------------- #
# LLM backend (optional)
# --------------------------------------------------------------------------- #

_LLM_SYSTEM = (
    "You are a senior video scriptwriter. You write tight, factual, "
    "narration-ready scripts for short explainer videos. Each scene is one "
    "spoken sentence (12-22 words) plus a 1-4 word on-screen headline in "
    "Title Case. Be concrete and accurate; never invent statistics."
)

_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "title": {"type": "string"},
        "scenes": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "headline": {"type": "string"},
                    "narration": {"type": "string"},
                },
                "required": ["headline", "narration"],
            },
        },
    },
    "required": ["title", "scenes"],
}


def _llm_script(brief_raw: str, topic: str, tone: str, n: int) -> Optional[Script]:
    try:
        import anthropic
    except Exception:
        return None

    # Default to a current, capable Claude model; override with the env var.
    model = os.environ.get("MONTAGE_LLM_MODEL", "claude-sonnet-4-6")
    try:
        client = anthropic.Anthropic()
    except Exception:
        return None

    prompt = (
        f"Write the script for a short video.\n\n"
        f"Request: {brief_raw}\n"
        f"Topic: {topic}\n"
        f"Tone: {tone}\n"
        f"Exactly {n} scenes, in narrative order (hook -> body -> takeaway).\n"
        f"Return JSON matching the schema."
    )
    try:
        import json

        resp = client.messages.create(
            model=model,
            max_tokens=1500,
            system=_LLM_SYSTEM,
            output_config={"format": {"type": "json_schema", "schema": _SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        text = next(b.text for b in resp.content if b.type == "text")
        data = json.loads(text)
        beats = [
            Beat(headline=s["headline"].strip(), narration=s["narration"].strip())
            for s in data["scenes"]
            if s.get("narration")
        ]
        if not beats:
            return None
        return Script(
            title=data.get("title", topic).strip(),
            beats=beats[:n] if len(beats) >= n else beats,
            backend="llm",
        )
    except Exception:
        # Any failure (no creds, network, bad output) falls back silently to
        # the template backend at the call site.
        return None


def write_script(brief) -> Script:
    n = _scene_count(brief.duration_s)
    llm = _llm_script(brief.raw, brief.topic, brief.tone, n)
    if llm is not None:
        return llm
    return _template_script(brief.topic, n)
