"""Brand brief: everything the factory may say, and may not say."""
from __future__ import annotations

import json
from dataclasses import dataclass, field


@dataclass
class Brief:
    brand: str
    product: str
    audience: str
    pain: str                                   # problem the audience has
    outcome: str                                # what they want
    cta: str = "Link in bio."
    voice: str = "friendly, direct, plain English"
    verified_claims: list[str] = field(default_factory=list)   # the ONLY factual claims allowed
    verified_quotes: list[str] = field(default_factory=list)   # real customer quotes WITH permission
    banned_words: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> "Brief":
        return cls(**json.load(open(path)))
