"""Voice. The contract the rest of the app builds against:

    POST /api/voice/speak   {"text": "..."}      -> audio/wav
    POST /api/voice/listen  <audio bytes>        -> {"text": "..."}

With VOICE_BASE_URL unset this is a local stub: speak returns a short chime (a real WAV, so the
player code is exercised) and listen returns a fixed sentence marked as a stub. With it set, both
calls are passed straight through to the same two paths on that server, which is where the
Pocket TTS "Jane" voice plugs in. No cloud voice key is used or stored anywhere.
"""
import io
import json
import math
import struct
import urllib.request
import wave

STUB_SENTENCE = "two and a half kW Daikin split, back-to-back install, Smith job"


def chime(seconds=0.42, rate=16000):
    """Two soft rising tones. Stands in for Jane until her voice server is connected."""
    frames = bytearray()
    total = int(seconds * rate)
    for i in range(total):
        t = i / rate
        freq = 660.0 if i < total // 2 else 880.0
        fade = min(1.0, i / 400.0, (total - i) / 2400.0)
        frames += struct.pack("<h", int(9000 * fade * math.sin(2 * math.pi * freq * t)))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
        w.writeframes(bytes(frames))
    return buf.getvalue()


def _post(url, data, content_type, key, timeout):
    headers = {"Content-Type": content_type}
    if key:
        headers["Authorization"] = "Bearer " + key
    with urllib.request.urlopen(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as r:
        return r.read(), r.headers.get("Content-Type", "")


def speak(text, cfg, timeout=30):
    """-> (wav bytes, mode) where mode is 'stub' or 'live'."""
    text = " ".join(str(text or "").split())[:1200]
    if not text:
        raise ValueError("nothing to say")
    if not cfg.get("voice_base_url"):
        return chime(), "stub"
    audio, _ = _post(cfg["voice_base_url"].rstrip("/") + "/api/voice/speak",
                     json.dumps({"text": text, "voice": cfg.get("voice_name") or "jane"}).encode(),
                     "application/json", cfg.get("voice_key"), timeout)
    if not audio.startswith(b"RIFF"):
        raise ValueError("the voice server did not return WAV audio")
    return audio, "live"


def listen(audio, content_type, cfg, timeout=60):
    """-> {"text": ..., "stub": bool}"""
    if not cfg.get("voice_base_url"):
        return {"text": cfg.get("voice_stub_text") or STUB_SENTENCE, "stub": True}
    if not audio:
        raise ValueError("no audio was received")
    body, _ = _post(cfg["voice_base_url"].rstrip("/") + "/api/voice/listen", audio,
                    content_type or "application/octet-stream", cfg.get("voice_key"), timeout)
    data = json.loads(body)
    if not isinstance(data, dict) or not isinstance(data.get("text"), str):
        raise ValueError("the voice server did not return {text}")
    return {"text": data["text"][:4000], "stub": False}
