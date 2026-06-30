"""Stage 3 — asset synthesis.

Instead of calling an image model, montage-mini *synthesizes* a vector visual
for every scene: a per-scene gradient (derived from the style playbook with a
deterministic hue rotation), a motif, and camera-motion parameters. This is
the zero-key analogue of "generate an image per scene" — the visuals are
computed, consistent with the playbook, and need no network.
"""

from __future__ import annotations

import colorsys
from typing import List

from .styles import get_playbook


def _hex_to_rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def _rgb_to_hex(rgb):
    return "#" + "".join(f"{int(round(max(0, min(1, c)) * 255)):02x}" for c in rgb)


def _rotate_hue(hex_color: str, degrees: float):
    r, g, b = _hex_to_rgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    h = (h + degrees / 360.0) % 1.0
    return _rgb_to_hex(colorsys.hls_to_rgb(h, l, s))


def build_assets(scenes, tone: str) -> List[dict]:
    """Attach a synthesized visual spec to each scene. Returns the visuals."""
    pb = get_playbook(tone)
    n = max(1, len(scenes))
    visuals = []
    for i, _scene in enumerate(scenes):
        # Walk the hue gradually across the production so scenes feel related
        # but distinct — a coherent "look", not a slideshow of random colors.
        shift = (i / n) * 40.0 - 20.0  # +/- 20 degrees across the piece
        bg0 = _rotate_hue(pb["bg"][0], shift)
        bg1 = _rotate_hue(pb["bg"][1], shift * 0.6)
        visuals.append(
            {
                "bg0": bg0,
                "bg1": bg1,
                "accent": pb["accent"],
                "accent2": pb["accent2"],
                "motif": pb["motif"],
                "motion": pb["motion"],
                # Deterministic per-scene motion params (browser doesn't need
                # randomness — we bake variety in here).
                "angle": (i * 47) % 360,
                "zoom_dir": 1 if i % 2 == 0 else -1,
                "pan_x": ((i * 31) % 7 - 3) / 10.0,
                "pan_y": ((i * 19) % 5 - 2) / 10.0,
                "seed": (i * 2654435761) % 100000,
            }
        )
    return visuals
