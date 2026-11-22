"""Compliance lint. Blocks fake testimonials and unverified claims BEFORE any spend.

Why: fake / AI-generated testimonials are banned under the FTC's review rule, and an
AI presenter saying "I tried this and loved it" is a testimonial nobody had. Rule:
presenters DEMONSTRATE or EXPLAIN; they never claim personal experience. Real quotes
are allowed only if listed in brief.verified_quotes. This is a safety net, NOT legal
advice - have a lawyer review before publishing paid ads.
"""
from __future__ import annotations

import re

EXPERIENCE = re.compile(
    r"(?i)\b(i|we)\s+(have\s+)?(used|tried|bought|tested|switched|lost|gained|love[d]?|loved|swear)\b"
    r"|\bchanged my (life|skin|body|mind)\b|\bworked for me\b|\bmy (skin|results?|journey)\b|\bafter (using|trying)\b")
HARD_CLAIM = re.compile(r"(?i)(\d+\s?%|#1|\b(?:guarantee[d]?|cure[sd]?|clinically|proven|doctor|best in)\b)")


def lint(text: str, brief) -> list[str]:
    problems = []
    quoted = any(q.lower() in text.lower() for q in brief.verified_quotes)
    if EXPERIENCE.search(text) and not quoted:
        problems.append("first-person experience claim (fake testimonial risk)")
    for m in HARD_CLAIM.finditer(text):
        if not any(m.group(0).lower() in c.lower() for c in brief.verified_claims):
            problems.append(f"unverified claim: '{m.group(0)}'")
    for w in brief.banned_words:
        if w.lower() in text.lower():
            problems.append(f"banned word: '{w}'")
    return problems
