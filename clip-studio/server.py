#!/usr/bin/env python3
"""Clip Studio backend: VOD -> find highlights -> cut -> reframe 9:16 -> caption -> export.

Core needs only Python 3.9+ and ffmpeg/ffprobe on PATH (stdlib only).
Optional extras are auto-detected: yt-dlp (import), faster-whisper / openai-whisper /
whisper.cpp (transcripts), opencv (face tracking).
"""
import array
import importlib.util
import json
import math
import mimetypes
import os
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("CLIP_STUDIO_DATA", ROOT / "data")).resolve()
MEDIA, EXPORTS, CACHE = DATA / "media", DATA / "exports", DATA / "cache"
WEB = ROOT / "web"
for d in (MEDIA, EXPORTS, CACHE):
    d.mkdir(parents=True, exist_ok=True)

VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".flv", ".ts"}


# --------------------------------------------------------------------------- jobs
class Job:
    def __init__(self, kind):
        self.id = uuid.uuid4().hex[:10]
        self.kind = kind
        self.status = "running"
        self.progress = 0.0
        self.message = ""
        self.result = None
        self.error = None

    def to_dict(self):
        return {"id": self.id, "kind": self.kind, "status": self.status,
                "progress": round(self.progress, 3), "message": self.message,
                "result": self.result, "error": self.error}


JOBS = {}


def start_job(kind, fn, **kw):
    job = Job(kind)
    JOBS[job.id] = job

    def run():
        try:
            job.result = fn(job, **kw)
            job.progress, job.status = 1.0, "done"
        except Exception as e:  # surfaced to the UI
            job.error, job.status = str(e) or e.__class__.__name__, "error"

    threading.Thread(target=run, daemon=True).start()
    return job


# --------------------------------------------------------------------------- helpers
class ApiError(Exception):
    pass


def media_path(name):
    p = (MEDIA / name).resolve()
    if MEDIA not in p.parents or not p.is_file():
        raise ApiError(f"unknown media: {name}")
    return p


def safe_stem(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("._") or "clip"


_probe_cache = {}


def probe(path):
    path = Path(path)
    key = (str(path), path.stat().st_mtime_ns)
    if key in _probe_cache:
        return _probe_cache[key]
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True)
    if out.returncode:
        raise ApiError("ffprobe could not read that file")
    j = json.loads(out.stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), None)
    if not v:
        raise ApiError("no video stream")
    num, _, den = v.get("r_frame_rate", "30/1").partition("/")
    fps = float(num) / float(den or 1) if float(den or 1) else 30.0
    info = {"duration": float(j["format"].get("duration") or v.get("duration") or 0),
            "width": int(v["width"]), "height": int(v["height"]), "fps": round(fps, 3),
            "has_audio": any(s["codec_type"] == "audio" for s in j["streams"])}
    # honor rotation metadata (phone footage)
    rot = abs(int((v.get("tags") or {}).get("rotate", 0)))
    for sd in v.get("side_data_list", []) or []:
        rot = abs(int(sd.get("rotation", rot)))
    if rot in (90, 270):
        info["width"], info["height"] = info["height"], info["width"]
    _probe_cache[key] = info
    return info


def capabilities():
    whisper = None
    if importlib.util.find_spec("faster_whisper"):
        whisper = "faster-whisper"
    elif importlib.util.find_spec("whisper"):
        whisper = "openai-whisper"
    elif shutil.which("whisper-cli") and os.environ.get("WHISPER_CPP_MODEL"):
        whisper = "whisper.cpp"
    return {"ffmpeg": bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
            "yt_dlp": bool(shutil.which("yt-dlp") or importlib.util.find_spec("yt_dlp")),
            "whisper": whisper,
            "opencv": bool(importlib.util.find_spec("cv2"))}


# --------------------------------------------------------------------------- import
def do_import(job, url):
    if not re.match(r"^https?://", url):
        raise ApiError("URL must start with http(s)://")
    exe = shutil.which("yt-dlp")
    cmd = [exe] if exe else [sys.executable, "-m", "yt_dlp"]
    if not exe and not importlib.util.find_spec("yt_dlp"):
        raise ApiError("yt-dlp is not installed (pip install yt-dlp) - or just drop a file in the media bin")
    before = {p.name for p in MEDIA.iterdir()}
    cmd += ["--no-playlist", "--newline", "-f", "bv*[height<=1080]+ba/b", "--merge-output-format", "mp4",
            "-o", str(MEDIA / "%(title).80B [%(id)s].%(ext)s"), "--", url]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = []
    for line in p.stdout:
        tail = (tail + [line.strip()])[-6:]
        m = re.search(r"\[download\]\s+([\d.]+)%", line)
        if m:
            job.progress = float(m.group(1)) / 100 * 0.98
        job.message = line.strip()[:120]
    if p.wait():
        raise ApiError("yt-dlp failed: " + " | ".join(tail[-2:]))
    new = sorted({p.name for p in MEDIA.iterdir()} - before)
    return {"files": new}


# --------------------------------------------------------------------------- analysis
def audio_energy(path, duration, job, win=0.5, lo=0.0, hi=0.6):
    sr = 8000
    n = int(sr * win)
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(sr),
                          "-f", "s16le", "-"], stdout=subprocess.PIPE)
    db = []
    while True:
        buf = p.stdout.read(n * 2)
        if len(buf) < 2:
            break
        a = array.array("h")
        a.frombytes(buf[: len(buf) // 2 * 2])
        if sys.byteorder == "big":
            a.byteswap()
        rms = math.sqrt(sum(x * x for x in a) / len(a))
        db.append(20 * math.log10(rms + 1))
        if duration:
            job.progress = lo + (hi - lo) * min(1, len(db) * win / duration)
    p.wait()
    return db


def scene_cuts(path, duration, job, lo=0.6, hi=0.98, thresh=0.28):
    p = subprocess.Popen(
        ["ffmpeg", "-nostats", "-i", str(path), "-an", "-vf",
         f"fps=4,scale=160:-2,select='gt(scene,{thresh})',showinfo", "-f", "null", "-"],
        stderr=subprocess.PIPE, text=True)
    cuts = []
    for line in p.stderr:
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            cuts.append(round(float(m.group(1)), 2))
            if duration:
                job.progress = lo + (hi - lo) * min(1, cuts[-1] / duration)
    p.wait()
    return cuts


def analyze(job, name, clip_len=25.0, count=8):
    path = media_path(name)
    info = probe(path)
    dur = info["duration"]
    clip_len = max(5.0, min(float(clip_len), 90.0, dur or 90.0))
    job.message = "Scanning audio energy"
    win = 0.5
    db = audio_energy(path, dur, job, win) if info["has_audio"] else [0.0] * int(dur / win)
    job.message = "Detecting scene cuts"
    cuts = scene_cuts(path, dur, job)
    if not db:
        raise ApiError("could not read audio")
    med = statistics.median(db)
    sd = statistics.pstdev(db) or 1.0
    z = [(d - med) / sd for d in db]
    nwin = max(1, int(clip_len / win))
    cands = []
    for i in range(0, max(1, len(z) - nwin + 1), int(1 / win)):
        seg = z[i:i + nwin]
        t0, t1 = i * win, (i + nwin) * win
        nc = sum(1 for c in cuts if t0 <= c < t1)
        peak = max(seg)
        mean = sum(seg) / len(seg)
        score = 0.45 * peak + 0.9 * mean + 0.12 * nc
        cands.append((score, i, peak, mean, nc, seg.index(peak)))
    cands.sort(reverse=True)
    picked, clips = [], []
    for score, i, peak, mean, nc, pk in cands:
        t0, t1 = i * win, (i + nwin) * win
        if any(t0 < b and t1 > a for a, b in picked):
            continue
        picked.append((t0, t1))
        peak_t = (i + pk) * win
        start = max(0.0, min(max(0.0, dur - clip_len), peak_t - 0.4 * clip_len))
        reasons = []
        if peak > 2.0:
            reasons.append("loud moment")
        if mean > 0.8:
            reasons.append("sustained intensity")
        if nc >= max(3, clip_len / 6):
            reasons.append("fast cuts")
        clips.append({"start": round(start, 2), "end": round(min(dur, start + clip_len), 2),
                      "score": round(score, 2), "peak": round(peak_t, 2),
                      "reasons": reasons or ["energy"]})
        if len(clips) >= int(count):
            break
    return {"duration": dur, "window": win, "energy": [round(d, 1) for d in db], "cuts": cuts, "clips": clips}


# --------------------------------------------------------------------------- transcription
_models = {}


def extract_wav(path, start, end, out):
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(end - start), "-i", str(path),
                        "-vn", "-ac", "1", "-ar", "16000", str(out)], capture_output=True, text=True)
    if r.returncode:
        raise ApiError("audio extract failed: " + r.stderr[-200:])


def transcribe(job, name, start, end, model="base"):
    caps = capabilities()["whisper"]
    if not caps:
        raise ApiError("No transcription engine found. pip install faster-whisper  "
                       "(or openai-whisper, or set WHISPER_CPP_MODEL with whisper-cli on PATH)")
    path = media_path(name)
    start, end = float(start), float(end)
    segs = []
    with tempfile.TemporaryDirectory(dir=CACHE) as td:
        wav = Path(td) / "a.wav"
        job.message, job.progress = "Extracting audio", 0.05
        extract_wav(path, start, end, wav)
        job.message, job.progress = f"Transcribing ({caps})", 0.15
        if caps == "faster-whisper":
            from faster_whisper import WhisperModel
            m = _models.setdefault(("fw", model), WhisperModel(model, compute_type="int8"))
            it, _ = m.transcribe(str(wav), word_timestamps=True, vad_filter=True)
            for s in it:
                segs.append({"start": s.start + start, "end": s.end + start, "text": s.text.strip(),
                             "words": [{"start": w.start + start, "end": w.end + start, "word": w.word.strip()}
                                       for w in (s.words or [])]})
                job.progress = min(0.95, 0.15 + 0.8 * (s.end / max(1e-3, end - start)))
        elif caps == "openai-whisper":
            import whisper
            m = _models.setdefault(("ow", model), whisper.load_model(model))
            r = m.transcribe(str(wav), word_timestamps=True)
            for s in r["segments"]:
                segs.append({"start": s["start"] + start, "end": s["end"] + start, "text": s["text"].strip(),
                             "words": [{"start": w["start"] + start, "end": w["end"] + start,
                                        "word": w["word"].strip()} for w in s.get("words", [])]})
        else:  # whisper.cpp (segment-level only)
            of = Path(td) / "out"
            r = subprocess.run(["whisper-cli", "-m", os.environ["WHISPER_CPP_MODEL"], "-f", str(wav), "-oj",
                                "-of", str(of)], capture_output=True, text=True)
            if r.returncode:
                raise ApiError("whisper.cpp failed: " + r.stderr[-200:])
            for s in json.loads((of.with_suffix(".json")).read_text())["transcription"]:
                segs.append({"start": s["offsets"]["from"] / 1000 + start, "end": s["offsets"]["to"] / 1000 + start,
                             "text": s["text"].strip(), "words": []})
    return {"segments": [s for s in segs if s["text"]]}


# --------------------------------------------------------------------------- tracking
def track(job, name, start, end, fps=3):
    """Auto-reframe: returns keyframes {t, x(0..1 center)} (t = absolute source seconds).
    Uses OpenCV face detection when available, otherwise a pure-python motion centroid."""
    path = media_path(name)
    info = probe(path)
    start, end = float(start), min(float(end), info["duration"] or float(end))
    use_cv = importlib.util.find_spec("cv2") is not None
    W = 480 if use_cv else 192
    H = max(2, int(W * info["height"] / info["width"]) // 2 * 2)
    pix = "bgr24" if use_cv else "gray"
    bpp = 3 if use_cv else 1
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", str(start), "-t", str(end - start), "-i", str(path),
                          "-an", "-vf", f"fps={fps},scale={W}:{H},format={pix}", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE)
    fsz = W * H * bpp
    if use_cv:
        import cv2
        import numpy as np
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    prev, xs, i = None, [], 0
    total = max(1, int((end - start) * fps))
    while True:
        buf = p.stdout.read(fsz)
        if len(buf) < fsz:
            break
        x = None
        if use_cv:
            frame = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.15, 5, minSize=(W // 18, W // 18))
            if len(faces):
                fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
                x = (fx + fw / 2) / W
            elif prev is not None:
                x = _motion_x(prev, gray.tobytes(), W, H)
            prev = gray.tobytes()
        else:
            if prev is not None:
                x = _motion_x(prev, buf, W, H)
            prev = buf
        xs.append(x)
        i += 1
        job.progress = min(0.95, i / total)
    p.wait()
    # fill gaps, smooth (EMA), thin to <= ~1 keyframe/sec
    last = 0.5
    for k, v in enumerate(xs):
        if v is None:
            xs[k] = last
        last = xs[k]
    sm, cur = [], xs[0] if xs else 0.5
    for v in xs:
        cur += 0.3 * (v - cur)
        sm.append(cur)
    step = max(1, int(fps))
    kfs = [{"t": round(start + k / fps, 2), "x": round(sm[k], 3), "z": 1.0} for k in range(0, len(sm), step)]
    return {"keyframes": kfs[:40], "engine": "opencv-faces" if use_cv else "motion"}


def _motion_x(a, b, W, H):
    col = [0] * W
    for r in range(H):
        o = r * W
        for c in range(W):
            d = a[o + c] - b[o + c]
            col[c] += d if d > 0 else -d
    tot = sum(col)
    if tot < W * H * 1.5:  # almost static
        return None
    return sum(c * v for c, v in enumerate(col)) / tot / W


# --------------------------------------------------------------------------- export
def fmt(v):
    return f"{v:.4f}".rstrip("0").rstrip(".") or "0"


def piecewise(kfs, key, default):
    """ffmpeg expression in t that linearly interpolates kfs[key]; holds the ends."""
    pts = sorted((float(k["t"]), float(k.get(key, default))) for k in kfs)
    if not pts:
        return fmt(default)
    expr = fmt(pts[-1][1])
    for (t0, v0), (t1, v1) in reversed(list(zip(pts, pts[1:]))):
        seg = f"{fmt(v0)}+({fmt(v1 - v0)})*(t-{fmt(t0)})/{fmt(max(t1 - t0, 1e-3))}"
        expr = f"if(lt(t,{fmt(t1)}),{seg},{expr})"
    return f"if(lt(t,{fmt(pts[0][0])}),{fmt(pts[0][1])},{expr})"


def ass_color(hex_):
    h = hex_.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"&H00{b:02X}{g:02X}{r:02X}"


def ass_time(t):
    t = max(0.0, t)
    cs = int(round(t * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def ass_text(s):
    return s.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ")


def synth_words(seg):
    toks = seg["text"].split()
    if not toks:
        return []
    tot = sum(len(t) for t in toks)
    t, out = seg["start"], []
    for tok in toks:
        d = (seg["end"] - seg["start"]) * len(tok) / tot
        out.append({"start": t, "end": t + d, "word": tok})
        t += d
    return out


def caption_events(segments, t0, t1, words_per, upper, hi_col):
    events = []
    for seg in segments:
        words = seg.get("words") or synth_words(seg)
        words = [w for w in words if w["end"] > t0 and w["start"] < t1 and w["word"]]
        chunk = []
        chunks = []
        for w in words:
            if chunk and (len(chunk) >= words_per or w["start"] - chunk[-1]["end"] > 0.7
                          or chunk[-1]["word"][-1:] in ".?!"):
                chunks.append(chunk)
                chunk = []
            chunk.append(w)
        if chunk:
            chunks.append(chunk)
        for ch in chunks:
            for i, w in enumerate(ch):
                s = max(w["start"], t0) - t0
                e = (ch[i + 1]["start"] if i + 1 < len(ch) else w["end"])
                e = min(e, t1) - t0
                if e - s < 0.06:
                    e = s + 0.06
                parts = []
                for j, x in enumerate(ch):
                    word = ass_text(x["word"].upper() if upper else x["word"])
                    parts.append(f"{{\\c{hi_col}}}{word}{{\\c&H00FFFFFF&}}" if j == i else word)
                pop = "{\\fscx112\\fscy112\\t(0,90,\\fscx100\\fscy100)}"
                events.append((s, e, pop + " ".join(parts)))
    return events


def build_ass(spec, t0, t1):
    cap = spec.get("captions") or {}
    font = cap.get("font") or "Arial"
    hi = ass_color(cap.get("highlight") or "#ffe14a")
    size = int(cap.get("size") or 88)
    margin_v = int(1920 * (1 - float(cap.get("y", 0.72))))
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 0", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, "
        "Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
        "MarginR, MarginV, Encoding",
        f"Style: Cap,{font},{size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,9,3,2,70,70,{margin_v},1",
        f"Style: Title,{font},{int(size * 1.1)},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,10,4,8,60,60,230,1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"]
    n = 0
    title = spec.get("title") or {}
    if title.get("text"):
        d = float(title.get("duration", 2.5))
        lines.append(f"Dialogue: 1,{ass_time(0)},{ass_time(d)},Title,,0,0,0,,{{\\fad(150,250)}}{ass_text(title['text'].upper())}")
        n += 1
    if cap.get("enabled", True):
        for s, e, text in caption_events(cap.get("segments") or [], t0, t1, int(cap.get("words_per", 3)),
                                         bool(cap.get("upper", True)), hi):
            lines.append(f"Dialogue: 0,{ass_time(s)},{ass_time(e)},Cap,,0,0,0,,{text}")
            n += 1
    return "\n".join(lines) + "\n", n


def build_graph(spec, info, has_ass):
    iw, ih = info["width"], info["height"]
    ow, oh = 1080, 1920
    kfs = spec.get("keyframes") or []
    t0 = float(spec["start"])
    rel = [{"t": float(k["t"]) - t0, "x": k.get("x", 0.5), "z": k.get("z", 1.0)} for k in kfs]
    if spec.get("layout") == "blur":
        chain = (f"[0:v]split[a][b];[a]scale={ow}:{oh}:force_original_aspect_ratio=increase,crop={ow}:{oh},"
                 f"boxblur=30:5,eq=brightness=-0.12[bg];[b]scale={ow}:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2")
    else:
        cw = int(min(iw, ih * 9 / 16)) // 2 * 2
        ch = int(cw * 16 / 9) // 2 * 2
        ch = min(ch, ih)
        cx = piecewise(rel, "x", 0.5)
        x = f"max(0,min({iw - cw},({cx})*{iw}-{cw / 2}))"
        chain = f"[0:v]crop={cw}:{ch}:x='{x}':y='({ih - ch})/2',scale={ow}:{oh}:flags=lanczos"
    if any(abs(k["z"] - 1.0) > 1e-3 for k in rel):
        z = piecewise(rel, "z", 1.0)
        chain += (f",scale=w='trunc({ow}*({z})/2)*2':h='trunc({oh}*({z})/2)*2':eval=frame,"
                  f"crop={ow}:{oh}")
    chain += ",setsar=1,format=yuv420p"
    if has_ass:
        chain += ",ass=subs.ass"
    return chain + "[v]"


def do_export(job, spec):
    path = media_path(spec["source"])
    info = probe(path)
    t0 = max(0.0, float(spec["start"]))
    t1 = min(float(spec["end"]), info["duration"])
    if t1 - t0 < 0.5:
        raise ApiError("clip is too short")
    spec["start"] = t0
    out_name = f"{safe_stem(path.stem)[:40]}_{int(t0)}-{int(t1)}_{uuid.uuid4().hex[:4]}.mp4"
    with tempfile.TemporaryDirectory(dir=CACHE) as td:
        td = Path(td)
        ass_text_, n_events = build_ass(spec, t0, t1)
        has_ass = n_events > 0
        if has_ass:
            (td / "subs.ass").write_text(ass_text_, encoding="utf-8")
        (td / "graph.txt").write_text(build_graph(spec, info, has_ass), encoding="utf-8")
        cmd = ["ffmpeg", "-y", "-v", "error", "-nostats", "-progress", "pipe:1",
               "-ss", fmt(t0), "-t", fmt(t1 - t0), "-i", str(path),
               "-filter_complex_script", "graph.txt", "-map", "[v]", "-map", "0:a:0?"]
        if spec.get("loudnorm", True) and info["has_audio"]:
            cmd += ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
        cmd += ["-c:v", "libx264", "-preset", spec.get("preset", "veryfast"), "-crf", str(spec.get("crf", 18)),
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart",
                str(EXPORTS / out_name)]
        job.message = "Rendering 1080x1920"
        p = subprocess.Popen(cmd, cwd=td, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        err = []
        threading.Thread(target=lambda: err.extend(p.stderr.readlines()), daemon=True).start()
        for line in p.stdout:
            m = re.match(r"out_time_(?:us|ms)=(\d+)", line)
            if m:
                job.progress = min(0.99, int(m.group(1)) / 1e6 / (t1 - t0))
        if p.wait():
            (EXPORTS / out_name).unlink(missing_ok=True)
            raise ApiError("ffmpeg failed: " + "".join(err)[-400:])
    return {"file": out_name, "url": f"/exports/{out_name}", "captions": has_ass}


# --------------------------------------------------------------------------- http
def list_media():
    items = []
    for p in sorted(MEDIA.iterdir(), key=lambda p: -p.stat().st_mtime):
        if p.suffix.lower() in VIDEO_EXT:
            try:
                items.append({"name": p.name, "size": p.stat().st_size, **probe(p)})
            except ApiError:
                pass
    return items


def list_exports():
    return [{"name": p.name, "size": p.stat().st_size, "url": f"/exports/{p.name}"}
            for p in sorted(EXPORTS.glob("*.mp4"), key=lambda p: -p.stat().st_mtime)]


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ClipStudio/1.0"

    def log_message(self, fmt_, *a):
        if os.environ.get("CLIP_STUDIO_VERBOSE"):
            super().log_message(fmt_, *a)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def _file(self, path, download=False):
        size = path.stat().st_size
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1):
                    start = int(m.group(1))
                    end = int(m.group(2)) if m.group(2) else size - 1
                elif m.group(2):
                    start = max(0, size - int(m.group(2)))
                end = min(end, size - 1)
                code = 206
        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        if download:
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
        self.end_headers()
        try:
            with open(path, "rb") as f:
                f.seek(start)
                left = end - start + 1
                while left > 0:
                    chunk = f.read(min(262144, left))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    left -= len(chunk)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _static(self, base, rel, download=False):
        p = (base / unquote(rel)).resolve()
        if base.resolve() not in p.parents or not p.is_file():
            return self._json({"error": "not found"}, 404)
        self._file(p, download)

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        try:
            if u.path in ("/", "/index.html"):
                return self._file(WEB / "index.html")
            if u.path == "/api/capabilities":
                return self._json(capabilities())
            if u.path == "/api/media":
                return self._json(list_media())
            if u.path == "/api/exports":
                return self._json(list_exports())
            if u.path.startswith("/api/jobs/"):
                job = JOBS.get(u.path.rsplit("/", 1)[1])
                return self._json(job.to_dict() if job else {"error": "no such job"}, 200 if job else 404)
            if u.path.startswith("/media/"):
                return self._static(MEDIA, u.path[7:])
            if u.path.startswith("/exports/"):
                return self._static(EXPORTS, u.path[9:], "download" in q)
            return self._static(WEB, u.path.lstrip("/"))
        except ApiError as e:
            self._json({"error": str(e)}, 400)

    def do_POST(self):
        try:
            b = self._body()
            path = urlparse(self.path).path
            routes = {
                "/api/import": lambda: start_job("import", do_import, url=b.get("url", "")),
                "/api/analyze": lambda: start_job("analyze", analyze, name=b["name"],
                                                  clip_len=b.get("clip_len", 25), count=b.get("count", 8)),
                "/api/transcribe": lambda: start_job("transcribe", transcribe, name=b["name"], start=b["start"],
                                                     end=b["end"], model=b.get("model", "base")),
                "/api/track": lambda: start_job("track", track, name=b["name"], start=b["start"], end=b["end"]),
                "/api/export": lambda: start_job("export", do_export, spec=b),
            }
            if path not in routes:
                return self._json({"error": "not found"}, 404)
            self._json(routes[path]().to_dict())
        except (ApiError, KeyError, ValueError, json.JSONDecodeError) as e:
            self._json({"error": f"bad request: {e}"}, 400)

    def do_PUT(self):  # raw upload: PUT /api/upload?name=file.mp4
        u = urlparse(self.path)
        if u.path != "/api/upload":
            return self._json({"error": "not found"}, 404)
        name = safe_stem(Path(parse_qs(u.query).get("name", ["upload.mp4"])[0]).stem) + \
            Path(parse_qs(u.query).get("name", ["upload.mp4"])[0]).suffix.lower()
        if Path(name).suffix not in VIDEO_EXT:
            return self._json({"error": "unsupported file type"}, 400)
        left = int(self.headers.get("Content-Length") or 0)
        dest = MEDIA / name
        with open(dest, "wb") as f:
            while left > 0:
                chunk = self.rfile.read(min(1 << 20, left))
                if not chunk:
                    break
                f.write(chunk)
                left -= len(chunk)
        try:
            probe(dest)
        except ApiError as e:
            dest.unlink(missing_ok=True)
            return self._json({"error": str(e)}, 400)
        self._json({"name": name})


def main():
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8369))
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)  # local only: no auth on this server
    print(f"Clip Studio -> http://127.0.0.1:{port}   (media: {MEDIA})")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
