"""Hook writer. Offline templates by default; pass llm(prompt)->list[str] for real model hooks."""
from __future__ import annotations

from .compliance import lint

TEMPLATES = [
    "Stop scrolling if {pain}.",
    "Nobody tells {audience} this about {pain}.",
    "Here is a simple way to get {outcome}.",
    "{product}: what it is and who it is for.",
    "POV: you want {outcome} and you are tired of {pain}.",
    "Three things to know before you pick a {product}.",
    "If you are {audience}, watch this.",
]


def write_hooks(brief, n: int = 5, llm=None) -> tuple[list[str], list[tuple[str, list[str]]]]:
    """Returns (clean_hooks, rejected[(hook, problems)])."""
    raw = llm(f"Write {n} short ad hooks for {brief.product}. Voice: {brief.voice}. "
              f"Audience: {brief.audience}. Never claim personal experience.") if llm else \
        [t.format(**vars(brief)) for t in TEMPLATES]
    clean, bad = [], []
    for h in raw[:max(n * 2, n)]:
        p = lint(h, brief)
        (bad.append((h, p)) if p else clean.append(h))
    return clean[:n], bad
