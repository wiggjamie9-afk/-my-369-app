"""Hardware detection and optional AI engines for Clip Studio.

Everything here is optional and auto-detected; the core app works without any of it:
  * GPU / hardware video encoders (NVENC, VideoToolbox, QSV, AMF) with automatic fallback to x264
  * Whisper transcription (faster-whisper, openai-whisper, whisper.cpp)
  * Local LLM + vision scoring through Ollama (e.g. Qwen models) with a rule-based fallback
"""
import base64
import importlib.util
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not OLLAMA.startswith("http"):
    OLLAMA = "http://" + OLLAMA
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # Ollama is local: never via a proxy

_cache, _models = {}, {}


class EngineError(Exception):
    pass


def _once(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


# --------------------------------------------------------------------------- hardware
def gpu_info():
    def probe():
        exe = shutil.which("nvidia-smi")
        if not exe:
            return None
        try:
            line = subprocess.run([exe, "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
                                  capture_output=True, text=True, timeout=5).stdout.strip().splitlines()[0]
            name, mem = [x.strip() for x in line.rsplit(",", 1)]
            return {"name": name, "vram_mb": int(mem)}
        except Exception:
            return None
    return _once("gpu", probe)


HW_ENCODERS = ["h264_nvenc", "h264_videotoolbox", "h264_qsv", "h264_amf"]


def _encoder_works(enc):
    try:
        r = subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2",
                            "-pix_fmt", "yuv420p", "-c:v", enc, "-f", "null", "-"], capture_output=True, timeout=20)
        return r.returncode == 0
    except Exception:
        return False


def pick_encoder():
    """First hardware H.264 encoder that actually works on this machine, else libx264."""
    def pick():
        forced = os.environ.get("CLIP_STUDIO_ENCODER")
        if forced:
            return forced
        try:
            listed = subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True,
                                    timeout=10).stdout
        except Exception:
            return "libx264"
        for enc in HW_ENCODERS:
            if enc in listed and _encoder_works(enc):
                return enc
        return "libx264"
    return _once("enc", pick)


def encoder_args(enc, preset="veryfast", crf=18):
    q = str(crf + 2)
    if enc == "h264_nvenc":
        return ["-c:v", enc, "-preset", "p5", "-rc", "vbr", "-cq", q, "-b:v", "0"]
    if enc == "h264_videotoolbox":
        return ["-c:v", enc, "-q:v", "65"]
    if enc == "h264_qsv":
        return ["-c:v", enc, "-global_quality", q]
    if enc == "h264_amf":
        return ["-c:v", enc, "-quality", "quality", "-rc", "cqp", "-qp_i", q, "-qp_p", q]
    return ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]


# --------------------------------------------------------------------------- ollama
VISION_PAT = re.compile(r"(vl|vision|llava|minicpm-v|gemma3|moondream|bakllava)", re.I)
EMBED_PAT = re.compile(r"(embed|bge|nomic|minilm)", re.I)


def ollama_models(timeout=0.8):
    try:
        with _opener.open(OLLAMA + "/api/tags", timeout=timeout) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except Exception:
        return []


def split_models(models):
    text = [m for m in models if not EMBED_PAT.search(m) and not VISION_PAT.search(m)]
    vision = [m for m in models if VISION_PAT.search(m) and not EMBED_PAT.search(m)]
    return text, vision


def default_llm(text_models):
    forced = os.environ.get("CLIP_STUDIO_LLM")
    if forced:
        return forced
    for m in text_models:
        if "qwen" in m.lower():
            return m
    return text_models[0] if text_models else None


def default_vision(vision_models):
    return os.environ.get("CLIP_STUDIO_VISION") or (vision_models[0] if vision_models else None)


def chat_json(model, prompt, images=None, timeout=240):
    msg = {"role": "user", "content": prompt}
    if images:
        msg["images"] = images
    body = json.dumps({"model": model, "messages": [msg], "stream": False, "format": "json",
                       "options": {"temperature": 0.2}}).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body, headers={"Content-Type": "application/json"})
    try:
        with _opener.open(req, timeout=timeout) as r:
            content = json.load(r)["message"]["content"]
    except Exception as e:
        raise EngineError(f"ollama request failed: {e}")
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.S)
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        raise EngineError("model did not return JSON")
    try:
        return json.loads(m.group(0))
    except ValueError:
        raise EngineError("model returned invalid JSON")


# --------------------------------------------------------------------------- scoring
HOOK_WORDS = set("never always secret secrets why how best worst crazy insane wait actually literally biggest "
                 "nobody everyone mistake truth shocking unbelievable stop need must free money won lost died "
                 "can't won't didn't".split())


def heuristic_score(text, dur):
    """No-AI fallback (English): questions, exclamations, numbers, hook words and speaking pace."""
    words = re.findall(r"[\w']+", text.lower())
    if len(words) < 5:
        return {"score": 1.0, "hook": "", "reason": "very little speech", "engine": "heuristic"}
    q, ex = text.count("?"), text.count("!")
    nums = sum(w.isdigit() for w in words)
    hooks = sum(w in HOOK_WORDS for w in words)
    wps = len(words) / max(dur, 1.0)
    raw = 1.2 * min(q, 3) + 0.8 * min(ex, 3) + 0.6 * min(nums, 3) + 0.7 * min(hooks, 5) + (1.5 if 2.0 <= wps <= 4.0 else 0)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.split()) >= 3]
    pick = next((s for s in sents if "?" in s or any(w in HOOK_WORDS for w in re.findall(r"[\w']+", s.lower()))),
                sents[0] if sents else text)
    return {"score": round(min(10.0, 1.5 + raw), 2), "hook": " ".join(pick.split()[:6]).strip(" .,!?"),
            "reason": "questions / hook words / pace", "engine": "heuristic"}


def llm_score(model, text):
    prompt = ("You choose moments for short-form vertical video (TikTok / Reels / Shorts). Rate the transcript "
              "excerpt from 0 to 10 for how likely it is to hook and hold viewers: strong opinion, surprise, humour, "
              "story payoff, clear takeaway, emotion. Be strict; most excerpts are 3-6.\n"
              'Reply with JSON only: {"score": <number>, "hook": "<on-screen title, max 6 words, same language as '
              'the transcript>", "reason": "<max 12 words>"}\n\nTranscript:\n' + text[:3500])
    j = chat_json(model, prompt)
    return {"score": max(0.0, min(10.0, float(j.get("score", 0)))), "hook": str(j.get("hook", ""))[:60],
            "reason": str(j.get("reason", ""))[:100], "engine": model}


def score_text(text, dur, model=None):
    if model:
        try:
            return llm_score(model, text)
        except (EngineError, ValueError, TypeError):
            pass
    return heuristic_score(text, dur)


def sample_frames(path, start, end, n=3):
    out = []
    for i in range(n):
        t = start + (end - start) * (i + 1) / (n + 1)
        r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                            "-vf", "scale=640:-2", "-f", "image2pipe", "-vcodec", "mjpeg", "-"],
                           capture_output=True, timeout=60)
        if r.returncode == 0 and r.stdout:
            out.append(base64.b64encode(r.stdout).decode())
    return out


def vision_score(model, path, start, end):
    frames = sample_frames(path, start, end)
    if not frames:
        return None
    prompt = ("These are frames, in order, from one short video clip. Rate 0-10 how visually engaging the clip is for "
              "social video: clear action or emotion, interesting subject, good framing. Penalise menus, loading "
              'screens, static or empty scenes. Reply with JSON only: {"score": <number>, "reason": "<max 12 words>"}')
    try:
        j = chat_json(model, prompt, images=frames)
        return {"score": max(0.0, min(10.0, float(j.get("score", 0)))), "reason": str(j.get("reason", ""))[:100]}
    except (EngineError, ValueError, TypeError):
        return None


# --------------------------------------------------------------------------- whisper
def whisper_engine():
    if importlib.util.find_spec("faster_whisper"):
        return "faster-whisper"
    if importlib.util.find_spec("whisper"):
        return "openai-whisper"
    if shutil.which("whisper-cli") and os.environ.get("WHISPER_CPP_MODEL"):
        return "whisper.cpp"
    return None


def default_whisper_model():
    forced = os.environ.get("CLIP_STUDIO_WHISPER")
    if forced:
        return forced
    g = gpu_info()
    if g:
        return "large-v3" if g["vram_mb"] >= 8000 else "medium"
    return "small"


def _fw_load(name, force_cpu=False):
    from faster_whisper import WhisperModel
    key = ("fw", name, force_cpu)
    if key not in _models:
        cuda = bool(gpu_info()) and not force_cpu
        try:
            _models[key] = (WhisperModel(name, device="cuda" if cuda else "cpu",
                                         compute_type="float16" if cuda else "int8"), cuda)
        except Exception:
            if not cuda:
                raise
            return _fw_load(name, True)
    return _models[key]


def _fw_segments(m, wav, offset, total, job):
    out = []
    it, _ = m.transcribe(str(wav), word_timestamps=True, vad_filter=True)
    for s in it:
        out.append({"start": s.start + offset, "end": s.end + offset, "text": s.text.strip(),
                    "words": [{"start": w.start + offset, "end": w.end + offset, "word": w.word.strip()}
                              for w in (s.words or [])]})
        if job is not None:
            job.progress = min(0.95, 0.15 + 0.8 * (s.end / max(1e-3, total)))
    return out


def transcribe_range(path, start, end, model=None, job=None, tmp=None):
    eng = whisper_engine()
    if not eng:
        raise EngineError("No transcription engine found. pip install faster-whisper "
                          "(or openai-whisper, or set WHISPER_CPP_MODEL with whisper-cli on PATH)")
    model = model or default_whisper_model()
    segs = []
    with tempfile.TemporaryDirectory(dir=tmp) as td:
        wav = os.path.join(td, "a.wav")
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", str(start), "-t", str(end - start), "-i", str(path),
                            "-vn", "-ac", "1", "-ar", "16000", wav], capture_output=True, text=True)
        if r.returncode:
            raise EngineError("audio extract failed: " + r.stderr[-200:])
        if job is not None:
            job.message, job.progress = f"Transcribing ({eng}, {model})", 0.15
        if eng == "faster-whisper":
            m, cuda = _fw_load(model)
            try:
                segs = _fw_segments(m, wav, start, end - start, job)
            except Exception:
                if not cuda:
                    raise
                segs = _fw_segments(_fw_load(model, True)[0], wav, start, end - start, job)
        elif eng == "openai-whisper":
            import whisper
            m = _models.setdefault(("ow", model), whisper.load_model(model))
            res = m.transcribe(wav, word_timestamps=True)
            for s in res["segments"]:
                segs.append({"start": s["start"] + start, "end": s["end"] + start, "text": s["text"].strip(),
                             "words": [{"start": w["start"] + start, "end": w["end"] + start, "word": w["word"].strip()}
                                       for w in s.get("words", [])]})
        else:  # whisper.cpp: segment-level only
            of = os.path.join(td, "out")
            r = subprocess.run(["whisper-cli", "-m", os.environ["WHISPER_CPP_MODEL"], "-f", wav, "-oj", "-of", of],
                               capture_output=True, text=True)
            if r.returncode:
                raise EngineError("whisper.cpp failed: " + r.stderr[-200:])
            with open(of + ".json", encoding="utf-8") as f:
                for s in json.load(f)["transcription"]:
                    segs.append({"start": s["offsets"]["from"] / 1000 + start, "end": s["offsets"]["to"] / 1000 + start,
                                 "text": s["text"].strip(), "words": []})
    return [s for s in segs if s["text"]]
