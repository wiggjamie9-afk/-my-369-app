"""Hardware detection and optional AI engines for Clip Studio.

Everything here is optional and auto-detected; the core app works without any of it:
  * GPU / hardware video encoders (NVENC, VideoToolbox, QSV, AMF) with automatic fallback to x264
  * Whisper transcription (faster-whisper, openai-whisper, whisper.cpp)
  * Local LLM + vision scoring through Ollama or any OpenAI-compatible local server such as Jan
    (models from the latter appear as "jan:<id>"), with a rule-based fallback
"""
import base64
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

OLLAMA = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
if not OLLAMA.startswith("http"):
    OLLAMA = "http://" + OLLAMA
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # local servers: never via a proxy

# Jan (https://jan.ai) -> Settings > Local API Server (default http://127.0.0.1:1337/v1). Works with LM Studio,
# llama.cpp's server, etc. too: point CLIP_STUDIO_OPENAI_URL at their /v1 URL.
OPENAI_URL = os.environ.get("CLIP_STUDIO_OPENAI_URL", "http://127.0.0.1:1337/v1").rstrip("/")
OPENAI_KEY = os.environ.get("CLIP_STUDIO_OPENAI_KEY", "clip-studio")  # Jan accepts a placeholder; set yours if you enabled a key
JAN = "jan:"

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


_sizes = {}


def ram_gb():
    """Total physical memory in GB (None if unknown)."""
    def probe():
        try:
            if sys.platform == "darwin":
                return int(subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True,
                                          timeout=3).stdout) / 2 ** 30
            if sys.platform.startswith("linux"):
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            return int(line.split()[1]) / 2 ** 20
            if os.name == "nt":
                import ctypes

                class MS(ctypes.Structure):
                    _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]
                st = MS()
                st.dwLength = ctypes.sizeof(MS)
                ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
                return st.ullTotalPhys / 2 ** 30
        except Exception:
            pass
        return None
    return _once("ram", probe)


def ollama_models(timeout=0.8):
    try:
        with _opener.open(OLLAMA + "/api/tags", timeout=timeout) as r:
            tags = json.load(r).get("models", [])
    except Exception:
        return []
    for m in tags:
        _sizes[m["name"]] = m.get("size", 0)
    return [m["name"] for m in tags]


_backends = {"ollama": 0, "jan": 0}


def openai_models(timeout=0.8):
    """Models from an OpenAI-compatible local server (Jan etc.), prefixed with 'jan:'."""
    try:
        req = urllib.request.Request(OPENAI_URL + "/models", headers={"Authorization": "Bearer " + OPENAI_KEY})
        with _opener.open(req, timeout=timeout) as r:
            return [JAN + m["id"] for m in json.load(r).get("data", []) if "id" in m]
    except Exception:
        return []


def list_models():
    """All installed models from every local backend (Ollama + Jan/OpenAI-compatible)."""
    o, j = ollama_models(), openai_models()
    _backends["ollama"], _backends["jan"] = len(o), len(j)
    return o + j


def backends():
    return dict(_backends)


def est_size(model):
    """Bytes: exact for Ollama; for others estimate ~0.6 GB per billion params (4-bit) from the name."""
    if _sizes.get(model):
        return _sizes[model]
    m = re.search(r"(?<![\w.])(\d+(?:\.\d+)?)b(?![a-z])", model.lower())
    return int(float(m.group(1)) * 0.6e9) if m else 0


def fits(model):
    """Model weights should use at most ~40% of RAM (the rest is for macOS/Windows, Whisper and the app)."""
    return est_size(model) <= (ram_gb() or 16) * 0.4 * 2 ** 30


def split_models(models):
    text = [m for m in models if not EMBED_PAT.search(m) and not VISION_PAT.search(m)]
    vision = [m for m in models if VISION_PAT.search(m) and not EMBED_PAT.search(m)]
    return text, vision


def _best_fitting(models, prefer_qwen=True):
    pool = sorted([m for m in models if fits(m)], key=lambda m: -est_size(m))
    if prefer_qwen:
        q = [m for m in pool if "qwen" in m.lower()]
        pool = q or pool
    return pool[0] if pool else None


def default_llm(text_models):
    """Best installed text model that fits in memory (prefers Qwen); the smallest one if none fit."""
    forced = os.environ.get("CLIP_STUDIO_LLM")
    if forced:
        return forced
    if not text_models:
        return None
    return _best_fitting(text_models) or sorted(text_models, key=est_size)[0]


def default_vision(vision_models):
    """Best installed vision model that fits in memory, else None (vision is skipped rather than swapping)."""
    forced = os.environ.get("CLIP_STUDIO_VISION")
    if forced:
        return forced
    return _best_fitting(vision_models, prefer_qwen=False)


def _extract_json(content):
    content = re.sub(r"<think>.*?</think>", "", content or "", flags=re.S)
    m = re.search(r"\{.*\}", content, re.S)
    if not m:
        raise EngineError("model did not return JSON")
    try:
        return json.loads(m.group(0))
    except ValueError:
        raise EngineError("model returned invalid JSON")


def _chat_openai(model, prompt, images, timeout):
    if images:
        content = [{"type": "text", "text": prompt}] + [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64," + i}} for i in images]
    else:
        content = prompt
    body = {"model": model, "messages": [{"role": "user", "content": content}], "temperature": 0.2, "stream": False}
    headers = {"Content-Type": "application/json", "Authorization": "Bearer " + OPENAI_KEY}
    last = None
    for with_json in (True, False):  # some servers reject response_format: retry without it
        payload = dict(body, **({"response_format": {"type": "json_object"}} if with_json else {}))
        req = urllib.request.Request(OPENAI_URL + "/chat/completions", data=json.dumps(payload).encode(), headers=headers)
        try:
            with _opener.open(req, timeout=timeout) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last = e
            e.close()
            if e.code not in (400, 422):
                break
        except Exception as e:
            last = e
            break
    raise EngineError(f"OpenAI-compatible server request failed: {last}")


def chat_json(model, prompt, images=None, timeout=240):
    """Ask a local model for a JSON answer. Models named 'jan:<id>' go to the OpenAI-compatible server."""
    if model.startswith(JAN):
        return _extract_json(_chat_openai(model[len(JAN):], prompt, images, timeout))
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
    return _extract_json(content)


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
    return "base" if (ram_gb() or 16) < 6 else "small"


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
