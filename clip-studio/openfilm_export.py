"""Export a Clip Studio clip as an OpenFilm project (https://github.com/openfilm/openfilm, MIT, protocol 0.1 draft).

An OpenFilm film is a folder containing film.html. This writes one with:
  * the source video, trimmed with a #t=in,out fragment (no re-encode, no copy: assets/ links to your file)
  * the 9:16 / 1:1 / 4:5 / 16:9 canvas via the viewport meta tag
  * the reframe as a static or keyframed pan (CSS @keyframes using `translate`)
  * captions as a WebVTT <track kind="captions">

Written from the published spec; only documented elements/attributes are used because OpenFilm's reader is strict.
NOT carried over: hook title, watermark, progress bar, punch-in zoom, blurred-background layout, word highlight.
Open it with:  npx -y openfilm@latest open <folder>   (needs Node 22.2+ and ffmpeg)
"""
import os
import shlex
import shutil
from pathlib import Path


def _vtt_time(t):
    t = max(0.0, t)
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}.{ms % 1000:03d}"


def build_vtt(segments, t0, t1, upper=False):
    """One cue per caption line, on the film's own timeline (0 = start of the clip)."""
    lines = ["WEBVTT", ""]
    n = 0
    for seg in sorted(segments or [], key=lambda s: s["start"]):
        s, e = max(seg["start"], t0) - t0, min(seg["end"], t1) - t0
        text = " ".join(str(seg.get("text", "")).split())
        if e - s < 0.05 or not text:
            continue
        n += 1
        lines += [str(n), f"{_vtt_time(s)} --> {_vtt_time(e)}", (text.upper() if upper else text).replace("-->", "->"), ""]
    return "\n".join(lines), n


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


def build_film_html(src_rel, t0, t1, iw, ih, ow, oh, layout, keyframes, has_captions, lang="en"):
    dur = t1 - t0
    notes = []
    style_block = ""
    anim = ""
    if layout == "blur":  # contain: full frame centred (the blurred background is not carried over)
        s = min(ow / iw, oh / ih)
        vw, vh = iw * s, ih * s
        left, top = (ow - vw) / 2, (oh - vh) / 2
        notes.append("blurred background is not exported; the frame is centred on black")
    else:  # cover + pan
        s = max(oh / ih, ow / iw)
        vw, vh = iw * s, ih * s
        top = (oh - vh) / 2
        rel = sorted((float(k["t"]) - t0, float(k.get("x", 0.5))) for k in (keyframes or []))
        left_of = lambda cx: _clamp(ow / 2 - cx * vw, ow - vw, 0.0)  # noqa: E731
        if len(rel) >= 2 and max(x for _, x in rel) - min(x for _, x in rel) > 0.01:
            left = left_of(rel[0][1])
            frames = []
            for t, x in rel:
                pct = _clamp(t / dur * 100, 0, 100)
                frames.append(f"  {pct:.2f}% {{ translate: {left_of(x) - left:.1f}px 0; }}")
            style_block = "@keyframes pan {\n" + "\n".join(frames) + "\n}"
            anim = f"animation: pan {dur:.3f}s linear both;"
        else:
            left = left_of(rel[0][1] if rel else 0.5)
    css = f"left:{left:.1f}px;top:{top:.1f}px;width:{vw:.1f}px;height:{vh:.1f}px;{anim}"
    parts = ["<!doctype html>", "<html>", "<head>", f'<meta name="viewport" content="width={ow}, height={oh}">']
    if style_block:
        parts += ["<style>", style_block, "</style>"]
    parts += ["</head>", "<body>"]
    if has_captions:
        parts += ["<section>", f'  <track kind="captions" src="captions.vtt" srclang="{lang}" label="Captions">', "</section>"]
    parts += ["<section>", f'  <video src="{src_rel}#t={t0:.3f},{t1:.3f}" at="0" style="{css}"></video>', "</section>",
              "</body>", "</html>", ""]
    return "\n".join(parts), notes


def export_film(root, media_file, info, spec, formats):
    """Write <root>/<name>/film.html (+ assets/ link, captions.vtt). Returns a result dict."""
    import uuid
    media_file = Path(media_file)
    if info.get("audio_only"):
        raise ValueError("OpenFilm export needs a video source (audio-only files use the built-in visualizer export)")
    ow, oh = formats.get(spec.get("format", "9:16"), formats["9:16"])
    t0 = max(0.0, float(spec["start"]))
    t1 = min(float(spec["end"]), info["duration"])
    if t1 - t0 < 0.5:
        raise ValueError("clip is too short")
    name = f"{media_file.stem[:30]}_{int(t0)}-{int(t1)}_{uuid.uuid4().hex[:4]}"
    name = "".join(c if c.isalnum() or c in "._-" else "_" for c in name).strip("._") or "film"
    folder = Path(root) / name
    (folder / "assets").mkdir(parents=True)
    link = folder / "assets" / ("source" + media_file.suffix.lower())
    try:  # link, don't copy: sources can be many GB
        os.symlink(media_file.resolve(), link)
    except (OSError, NotImplementedError):
        shutil.copy2(media_file, link)  # e.g. Windows without symlink rights
    caps = spec.get("captions") or {}
    vtt, n = build_vtt(caps.get("segments"), t0, t1, bool(caps.get("upper"))) if caps.get("enabled", True) else ("", 0)
    if n:
        (folder / "captions.vtt").write_text(vtt, encoding="utf-8")
    html, notes = build_film_html("assets/" + link.name, t0, t1, info["width"], info["height"], ow, oh,
                                  spec.get("layout", "crop"), spec.get("keyframes"), n > 0)
    (folder / "film.html").write_text(html, encoding="utf-8")
    q = shlex.quote(str(folder))
    return {"folder": str(folder), "film": str(folder / "film.html"), "captions": n,
            "open_cmd": f"npx -y openfilm@latest open {q}",
            "render_cmd": f"cd {q} && npx -y openfilm@latest render",
            "notes": notes + ["hook title, watermark, progress bar and punch-in zoom are not exported"]}
