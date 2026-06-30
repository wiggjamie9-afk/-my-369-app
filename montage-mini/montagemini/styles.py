"""Visual style playbooks, keyed by tone.

Each playbook defines a palette, typography and motion profile that the asset
and compose stages apply consistently across every scene — the same idea as
OpenMontage's style system, shrunk to a dict.
"""

from __future__ import annotations

PLAYBOOKS = {
    "professional": {
        "name": "Clean Professional",
        "bg": ["#0e1726", "#16233a"],
        "accent": "#4ea1ff",
        "accent2": "#7ce0c3",
        "text": "#eaf1fb",
        "muted": "#8aa0bd",
        "font": "'Segoe UI', system-ui, -apple-system, sans-serif",
        "motion": "ken_burns",
        "motif": "grid",
        "vignette": 0.35,
    },
    "energetic": {
        "name": "Flat Motion Graphics",
        "bg": ["#1a0b2e", "#3a0ca3"],
        "accent": "#ff4d6d",
        "accent2": "#ffd166",
        "text": "#ffffff",
        "muted": "#c9b8e8",
        "font": "'Poppins', 'Segoe UI', system-ui, sans-serif",
        "motion": "pop",
        "motif": "burst",
        "vignette": 0.2,
    },
    "cinematic": {
        "name": "Cinematic",
        "bg": ["#05070d", "#101826"],
        "accent": "#dfb76c",
        "accent2": "#c44536",
        "text": "#f1e9da",
        "muted": "#8d8576",
        "font": "Georgia, 'Times New Roman', serif",
        "motion": "slow_push",
        "motif": "rays",
        "vignette": 0.55,
    },
    "elegiac": {
        "name": "Elegy",
        "bg": ["#0a0a0c", "#1c1a22"],
        "accent": "#c9a96a",
        "accent2": "#6c7a89",
        "text": "#e8e2d6",
        "muted": "#7a7468",
        "font": "Georgia, 'Times New Roman', serif",
        "motion": "drift",
        "motif": "embers",
        "vignette": 0.6,
    },
    "calm": {
        "name": "Ambient",
        "bg": ["#0c1f24", "#123a40"],
        "accent": "#7fd1c1",
        "accent2": "#a7d8ff",
        "text": "#eaf6f3",
        "muted": "#88a8a4",
        "font": "'Segoe UI', system-ui, sans-serif",
        "motion": "drift",
        "motif": "waves",
        "vignette": 0.4,
    },
}


def get_playbook(tone: str) -> dict:
    return PLAYBOOKS.get(tone, PLAYBOOKS["professional"])
