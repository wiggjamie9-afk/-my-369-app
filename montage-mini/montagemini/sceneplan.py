"""Stage 2 — scene planning.

Turns script beats into timed scenes. Each scene gets a duration proportional
to its narration length (so longer lines stay on screen longer), plus
word-level caption timings for TikTok-style synced captions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from .script import Script


WORDS_PER_SECOND = 2.6  # comfortable narration pace
MIN_SCENE_S = 2.5
MAX_SCENE_S = 8.0


@dataclass
class Word:
    text: str
    start: float  # seconds, relative to scene start
    end: float


@dataclass
class Scene:
    index: int
    headline: str
    narration: str
    start: float  # seconds, absolute
    duration: float
    words: List[Word] = field(default_factory=list)


def plan_scenes(script: Script, target_duration_s: int) -> List[Scene]:
    beats = script.beats
    # Raw per-beat duration from word count.
    raws = []
    for b in beats:
        wc = max(1, len(b.narration.split()))
        raws.append(min(MAX_SCENE_S, max(MIN_SCENE_S, wc / WORDS_PER_SECOND + 0.8)))

    # Scale the whole thing toward the requested target duration so the video
    # lands close to what the user asked for.
    total = sum(raws) or 1.0
    scale = target_duration_s / total
    durations = [max(MIN_SCENE_S, r * scale) for r in raws]

    scenes: List[Scene] = []
    clock = 0.0
    for i, (b, dur) in enumerate(zip(beats, durations)):
        words = _time_words(b.narration, dur)
        scenes.append(
            Scene(
                index=i,
                headline=b.headline,
                narration=b.narration,
                start=round(clock, 3),
                duration=round(dur, 3),
                words=words,
            )
        )
        clock += dur
    return scenes


def _time_words(narration: str, dur: float) -> List[Word]:
    tokens = narration.split()
    if not tokens:
        return []
    # Leave a small lead-in and tail so captions don't slam the scene edges.
    lead, tail = 0.25, 0.35
    span = max(0.1, dur - lead - tail)
    # Weight each word's slice by its length so long words linger a touch.
    weights = [max(1, len(t)) for t in tokens]
    wsum = sum(weights)
    words: List[Word] = []
    t = lead
    for tok, w in zip(tokens, weights):
        slice_s = span * (w / wsum)
        words.append(Word(text=tok, start=round(t, 3), end=round(t + slice_s, 3)))
        t += slice_s
    return words


def total_duration(scenes: List[Scene]) -> float:
    if not scenes:
        return 0.0
    last = scenes[-1]
    return round(last.start + last.duration, 3)
