"""Carousel maker: turn slide copy (+ optional frames from your own footage) into a numbered PNG set,
a ZIP, and an optional slideshow video. Text is rendered with ffmpeg's libass (same engine as captions),
so there are no extra dependencies.

Typical uses: YouTube Community image posts (multi-image), Instagram/LinkedIn carousels, slideshow videos.
"""
import re
import subprocess
import uuid
import zipfile
import tempfile
from pathlib import Path

import engines as E

SIZES = {"1:1": (1080, 1080), "4:5": (1080, 1350), "9:16": (1080, 1920), "16:9": (1920, 1080)}
KINDS = ("cover", "text", "cta")
MAX_SLIDES = 10  # YouTube Community posts: up to 10 images per post (Google's help page may still say 5)


def _hex(c, default):
    c = (c or default).lstrip("#")
    return c if re.fullmatch(r"[0-9a-fA-F]{6}", c) else default.lstrip("#")


def _ass_col(c):  # RRGGBB -> &H00BBGGRR
    return f"&H00{c[4:6]}{c[2:4]}{c[0:2]}".upper()


def _esc(s):
    return str(s).replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def _size(text, big, mid, small, a=28, b=48):
    n = len(text)
    return big if n <= a else mid if n <= b else small


def build_ass(slide, idx, total, W, H, accent, handle, numbering):
    k = W / 1080
    kind = slide.get("kind", "text")
    title, body = (slide.get("title") or "").strip(), (slide.get("body") or "").strip()
    font = "Arial"
    mx = int(90 * k)
    acc = _ass_col(accent)
    st = lambda name, size, col="&H00FFFFFF", al=8, bold=1, outline=7: (  # noqa: E731
        f"Style: {name},{font},{int(size * k)},{col},{col},&H00000000,&H80000000,{bold},0,0,0,100,100,0,0,1,"
        f"{max(1, int(outline * k))},{max(1, int(2 * k))},{al},{mx},{mx},0,1")
    cover_sz = _size(title, 124, 98, 78)
    text_sz = 84 if len(body) <= 90 else 68 if len(body) <= 170 else 54
    lines = ["[Script Info]", "ScriptType: v4.00+", f"PlayResX: {W}", f"PlayResY: {H}", "WrapStyle: 0", "",
             "[V4+ Styles]",
             "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
             "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
             "MarginR, MarginV, Encoding",
             st("Big", cover_sz), st("Head", 66, acc), st("Body", text_sz, bold=0, outline=4),
             st("Cap", 78, al=2), st("Small", 34, "&H99FFFFFF", al=9, bold=1, outline=2),
             st("Handle", 36, acc, al=2, outline=2), st("Sub", 54, bold=0, outline=4), "",
             "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    ev = lambda style, text, x, y, an=8: lines.append(  # noqa: E731
        f"Dialogue: 0,0:00:00.00,0:00:10.00,{style},,0,0,0,,{{\\an{an}\\pos({int(x)},{int(y)})}}{_esc(text)}")
    cx = W / 2
    if kind == "cover":
        ev("Big", title.upper(), cx, H * 0.22)
        if body:
            ev("Sub", body, cx, H * 0.60)
    elif kind == "cta":
        ev("Big", (title or "Follow for more").upper(), cx, H * 0.30)
        if body:
            ev("Sub", body, cx, H * 0.58)
    elif slide.get("source"):  # frame slide: caption along the bottom
        ev("Cap", (title or body).upper(), cx, H * 0.88, 2)
        if title and body:
            ev("Sub", body, cx, H * 0.70, 8)
    else:  # text slide
        if title:
            ev("Head", title.upper(), cx, H * 0.14)
        ev("Body", body, cx, H * (0.30 if title else 0.22))
    if numbering:
        ev("Small", f"{idx}/{total}", W - 50 * k, 40 * k, 9)
    if handle:
        ev("Handle", handle, cx, H - 36 * k, 2)
    return "\n".join(lines) + "\n"


def _run(cmd, cwd):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("ffmpeg failed: " + r.stderr[-300:])


def build_carousel(job, spec, resolve, out_root, base_url):
    """spec: {format, slides:[{kind,title,body,source?,t?}], handle, accent, bg1, bg2, numbering, video?, seconds?, audio?}.
    resolve(name) -> Path of a file in the media bin (raises on unknown). Returns urls + folder."""
    slides = [s for s in (spec.get("slides") or []) if (s.get("title") or s.get("body") or s.get("source"))]
    if not slides:
        raise ValueError("add at least one slide")
    if len(slides) > MAX_SLIDES:
        raise ValueError(f"max {MAX_SLIDES} slides per post")
    W, H = SIZES.get(spec.get("format", "1:1"), SIZES["1:1"])
    accent, bg1, bg2 = _hex(spec.get("accent"), "#ff2e88"), _hex(spec.get("bg1"), "#2b0f4d"), _hex(spec.get("bg2"), "#05030a")
    handle = (spec.get("handle") or "").strip()
    name = f"carousel_{uuid.uuid4().hex[:6]}"
    folder = Path(out_root) / name
    folder.mkdir(parents=True)
    pngs = []
    with tempfile.TemporaryDirectory() as td:
        for i, s in enumerate(slides, 1):
            job.message, job.progress = f"Slide {i}/{len(slides)}", 0.05 + 0.7 * (i - 1) / len(slides)
            (Path(td) / "s.ass").write_text(build_ass(s, i, len(slides), W, H, accent, handle,
                                                      spec.get("numbering", True)), encoding="utf-8")
            out = folder / f"slide_{i:02d}.png"
            if s.get("source"):
                src = resolve(s["source"])
                cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{max(0.0, float(s.get('t', 0))):.2f}", "-i", str(src),
                       "-frames:v", "1", "-vf",
                       f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},eq=brightness=-0.3:saturation=1.15,"
                       f"vignette=PI/5,ass=s.ass", str(out)]
            else:
                cmd = ["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i",
                       f"gradients=s={W}x{H}:c0=0x{bg1}:c1=0x{bg2}:x0=0:y0=0:x1={W // 3}:y1={H}:speed=0.00001:d=1:r=1",
                       "-frames:v", "1", "-vf", "ass=s.ass", str(out)]
            _run(cmd, td)
            pngs.append(out)
    result = {"folder": str(folder), "slides": [f"{base_url}/{name}/{p.name}" for p in pngs]}
    video = None
    if spec.get("video"):
        job.message, job.progress = "Building slideshow video", 0.8
        sec = max(1.0, min(15.0, float(spec.get("seconds", 3))))
        video = folder / f"{name}.mp4"
        cmd = ["ffmpeg", "-y", "-v", "error", "-framerate", f"1/{sec}", "-i", str(folder / "slide_%02d.png")]
        if spec.get("audio"):
            cmd += ["-i", str(resolve(spec["audio"]))]
        cmd += ["-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30,format=yuv420p"] + E.encoder_args(E.pick_encoder())
        cmd += ["-pix_fmt", "yuv420p"] + (["-c:a", "aac", "-b:a", "192k", "-shortest"] if spec.get("audio") else []) + \
               ["-movflags", "+faststart", str(video)]
        try:
            _run(cmd, str(folder))
        except RuntimeError:  # hardware encoder hiccup: retry in software
            cmd = [c for c in cmd]
            i = cmd.index("-c:v")
            cmd[i:i + 2] = ["-c:v", "libx264"]
            _run(cmd, str(folder))
        result["video"] = f"{base_url}/{name}/{video.name}"
    zpath = folder / f"{name}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for p in pngs + ([video] if video else []):
            z.write(p, p.name)
    result["zip"] = f"{base_url}/{name}/{zpath.name}"
    return result


# --------------------------------------------------------------------------- slide copy drafting
def _clean(slides, n):
    out = []
    for s in slides:
        if not isinstance(s, dict):
            continue
        kind = s.get("kind") if s.get("kind") in KINDS else "text"
        out.append({"kind": kind, "title": str(s.get("title", ""))[:70].strip(), "body": str(s.get("body", ""))[:240].strip()})
    out = out[:n]
    if out:
        out[0]["kind"] = "cover"
        if len(out) > 1:
            out[-1]["kind"] = "cta"
    return out


def draft_slides(notes, n=7, model=None, topic=""):
    """Structure the creator's own notes into slides. Uses a local LLM when available; else splits the notes."""
    n = max(2, min(int(n), MAX_SLIDES))
    notes = (notes or "").strip()
    if not notes and not topic:
        raise ValueError("write some notes or a topic first")
    if model:
        prompt = (f"You write carousel slide copy (YouTube Community post / Instagram carousel). Topic: {topic or 'see notes'}.\n"
                  "Use ONLY the facts in the creator's notes below; never invent dates, features, prices or rumours. "
                  "Keep the creator's own opinion and voice. Short punchy lines.\n"
                  f'Reply with JSON only: {{"slides":[{{"kind":"cover|text|cta","title":"<=7 words","body":"<=28 words"}}]}} '
                  f"with exactly {n} slides: the first is the cover (title is the hook), the last is cta, the rest are text.\n\n"
                  f"Notes:\n{notes[:4000]}")
        try:
            got = _clean(E.chat_json(model, prompt).get("slides") or [], n)
            if len(got) >= 2:
                return {"slides": got, "engine": model}
        except (E.EngineError, AttributeError, TypeError, ValueError):
            pass
    lines = [ln.strip(" -*•\t") for ln in notes.splitlines() if ln.strip()]
    sl = [{"kind": "cover", "title": topic or (lines[0][:60] if lines else "Title"), "body": ""}]
    for ln in lines[: n - 2]:
        head, _, rest = ln.partition(":")
        sl.append({"kind": "text", "title": head[:40] if rest else "", "body": (rest or ln).strip()})
    sl.append({"kind": "cta", "title": "Follow for more", "body": "Which one surprised you? Tell me below."})
    return {"slides": _clean(sl, n), "engine": "template"}
