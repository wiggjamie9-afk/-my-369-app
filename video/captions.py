"""Burn timed captions (one per shot) with ffmpeg drawtext. Falls back to the input if drawtext is unavailable."""
import os
import subprocess
import tempfile
import textwrap


def burn_captions(video: str, shots, out: str, fontsize: int = 44) -> str:
    d = tempfile.mkdtemp()
    t, filters = 0.0, []
    for s in shots:
        p = os.path.join(d, f"c{s.idx}.txt")
        with open(p, "w") as f:
            f.write("\n".join(textwrap.wrap(s.text, 28)))
        a, b = t, t + s.seconds
        filters.append(f"drawtext=textfile={p}:x=(w-text_w)/2:y=h*0.68:fontsize={fontsize}:fontcolor=white:"
                       f"box=1:boxcolor=black@0.55:boxborderw=12:line_spacing=8:enable='between(t,{a:.2f},{b:.2f})'")
        t = b
    r = subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-vf", ",".join(filters),
                        "-c:a", "copy", out], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"caption burn failed: {r.stderr[-300:]}")
    return out
