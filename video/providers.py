"""Clip generators. All share: estimate_cost(shots)->USD and generate(shot,out)->path.

SlateProvider   works NOW, free, local (ffmpeg colour slates) - proves the pipeline.
HostedProvider  TODO(Kimmy): a paid API (e.g. Higgsfield, which this workspace has connected as MCP).
OpenWeightsProvider  TODO(Kimmy): Wan / LTX / HunyuanVideo on a GPU machine (this container has no GPU).
"""
from __future__ import annotations

import hashlib
import subprocess

W, H, FPS = 1280, 720, 24


class SlateProvider:
    paid = False

    def estimate_cost(self, shots) -> float:
        return 0.0

    def generate(self, shot, out: str) -> str:
        h = hashlib.sha256(shot.prompt.encode()).hexdigest()[:6]
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error",
                        "-f", "lavfi", "-i", f"color=c=0x{h}:s={W}x{H}:d={shot.seconds}:r={FPS}",
                        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                        "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out], check=True)
        return out


class HostedProvider:
    paid = True
    usd_per_second = None   # TODO(Kimmy): fill from the provider's real price list

    def estimate_cost(self, shots) -> float:
        if self.usd_per_second is None:
            raise NotImplementedError("set usd_per_second from the provider's price list before use")
        return sum(s.seconds for s in shots) * self.usd_per_second

    def generate(self, shot, out: str) -> str:
        raise NotImplementedError("TODO(Kimmy): call the hosted video API, download the clip to `out`, normalise to 1280x720/24fps")


class OpenWeightsProvider:
    paid = False   # no per-clip fee, but needs GPU hours
    def estimate_cost(self, shots) -> float:
        return 0.0
    def generate(self, shot, out: str) -> str:
        raise NotImplementedError("TODO(Kimmy): run Wan/LTX/HunyuanVideo on a GPU box; check each model's licence first")
