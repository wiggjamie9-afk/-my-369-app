"""Stage 0 — brief parsing.

Turn a plain-language request into a structured brief the rest of the
pipeline can plan against. Deliberately lightweight: a few regexes pull out
duration, aspect ratio and tone; the leftover text becomes the topic.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Optional


# Platform output profiles, mirroring OpenMontage's render profiles.
PROFILES = {
    "youtube": (1920, 1080, "16:9"),
    "landscape": (1920, 1080, "16:9"),
    "shorts": (1080, 1920, "9:16"),
    "reels": (1080, 1920, "9:16"),
    "tiktok": (1080, 1920, "9:16"),
    "vertical": (1080, 1920, "9:16"),
    "square": (1080, 1080, "1:1"),
    "feed": (1080, 1080, "1:1"),
    "cinematic": (2560, 1080, "21:9"),
}

# Tone keywords -> a canonical tone label used by the asset/style stages.
TONES = {
    "elegiac": ["elegiac", "elegy", "mournful", "somber", "melancholy"],
    "energetic": ["energetic", "upbeat", "punchy", "hype", "exciting", "fun"],
    "cinematic": ["cinematic", "epic", "dramatic", "trailer", "sweeping"],
    "calm": ["calm", "ambient", "dreamlike", "serene", "gentle", "meditative"],
    "professional": ["professional", "corporate", "clean", "explainer", "educational"],
}


@dataclass
class Brief:
    topic: str
    duration_s: int = 45
    profile: str = "youtube"
    width: int = 1920
    height: int = 1080
    aspect: str = "16:9"
    tone: str = "professional"
    narration: bool = True
    raw: str = ""
    key_points: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _match_duration(text: str) -> Optional[int]:
    # "45 second", "45-second", "1 minute", "90s", "1:30"
    m = re.search(r"(\d+)\s*[:m]\s*(\d{1,2})\s*(?:min|minute|s|sec)?", text)
    if m:  # mm:ss style
        return int(m.group(1)) * 60 + int(m.group(2))
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|\s)?\s*minute", text)
    if m:
        return int(round(float(m.group(1)) * 60))
    m = re.search(r"(\d+)\s*(?:-|\s)?\s*(?:second|sec|s)\b", text)
    if m:
        return int(m.group(1))
    return None


def _match_profile(text: str) -> Optional[str]:
    for key in PROFILES:
        if key in text:
            return key
    return None


def _match_tone(text: str) -> Optional[str]:
    for tone, words in TONES.items():
        if any(w in text for w in words):
            return tone
    return None


def parse_brief(request: str) -> Brief:
    """Parse a free-text request into a structured Brief."""
    low = request.lower()

    duration = _match_duration(low) or 45
    duration = max(8, min(duration, 180))  # keep it sane for an HTML player

    profile_key = _match_profile(low) or "youtube"
    w, h, aspect = PROFILES[profile_key]

    tone = _match_tone(low) or "professional"

    # Narration off if the user explicitly says "no narration".
    narration = not bool(re.search(r"\bno\s+narrat", low))

    # Topic: strip the directive scaffolding so the script stage gets a clean
    # subject. This is heuristic, not perfect — the LLM stage (if available)
    # re-reads the raw request anyway.
    topic = request.strip()
    topic = re.sub(
        r"^(make|create|produce|build|generate|cut|render)\s+(me\s+)?(a|an)?\s*",
        "",
        topic,
        flags=re.I,
    )
    # durations: "45 second", "45-second", "1 minute", "90s", "1:30"
    topic = re.sub(
        r"\b\d+\s*[:m]?\s*\d*\s*-?\s*(?:seconds?|secs?|s|minutes?|mins?)\b",
        "",
        topic,
        flags=re.I,
    )
    # format / platform words
    topic = re.sub(
        r"\b(animated|animation|explainer|video|montage|short|reel|reels|tiktok|"
        r"youtube|vertical|horizontal|landscape|square|feed|cinematic|trailer|"
        r"teaser|documentary)\b",
        "",
        topic,
        flags=re.I,
    )
    # directive words for narration / audio
    topic = re.sub(
        r"\b(?:no|with|without)?\s*(?:narration|voiceover|voice[- ]?over|"
        r"captions?|subtitles?|music|soundtrack)\b",
        "",
        topic,
        flags=re.I,
    )
    # strip tone keywords (they're captured separately)
    for words in TONES.values():
        for kw in words:
            topic = re.sub(rf"\b{re.escape(kw)}\b\s*(?:tone)?", " ", topic, flags=re.I)
    # only strip the connective "about" and leading filler, not every article
    topic = re.sub(r"\babout\b", " ", topic, flags=re.I)
    topic = topic.strip(" .,-")
    topic = re.sub(r"^(?:for|of|on)\s+(?:a|an|the)?\s*", "", topic, flags=re.I)
    topic = re.sub(r"^(?:a|an|the)\s+", "", topic, flags=re.I)
    topic = re.sub(r"\s{2,}", " ", topic).strip(" .,-")
    if not topic:
        topic = request.strip()

    return Brief(
        topic=topic,
        duration_s=duration,
        profile=profile_key,
        width=w,
        height=h,
        aspect=aspect,
        tone=tone,
        narration=narration,
        raw=request.strip(),
    )
