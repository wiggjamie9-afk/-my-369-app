"""Join clips with ffmpeg (concat demuxer; all clips share codec/size/fps)."""
import os
import subprocess
import tempfile


def stitch(clips: list[str], out: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as f:
        f.writelines(f"file '{os.path.abspath(c)}'\n" for c in clips)
        lst = f.name
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out], check=True)
    finally:
        os.unlink(lst)
    return out


def duration(path: str) -> float:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())
