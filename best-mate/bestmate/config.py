"""Configuration: environment variables first, then an optional config.json. No secret lives in the repo."""
import json
import os

KEYS = {
    # name: (environment variable, default)
    "host": ("HOST", "127.0.0.1"),
    "port": ("PORT", "8048"),
    "db": ("BESTMATE_DB", ""),
    "app_password": ("APP_PASSWORD", ""),
    "session_secret": ("SESSION_SECRET", ""),
    "llm_base_url": ("LLM_BASE_URL", ""),
    "llm_key": ("LLM_KEY", ""),
    "llm_model": ("LLM_MODEL", ""),
    "voice_base_url": ("VOICE_BASE_URL", ""),
    "voice_key": ("VOICE_KEY", ""),
    "voice_name": ("VOICE_NAME", "jane"),
    "voice_stub_text": ("VOICE_STUB_TEXT", ""),
}


def load(root):
    cfg = {}
    path = os.environ.get("BESTMATE_CONFIG") or os.path.join(root, "config.json")
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if isinstance(data, dict):
            cfg = {k: str(v) for k, v in data.items() if k in KEYS and v not in (None, "")}
    except FileNotFoundError:
        pass
    for key, (env, default) in KEYS.items():
        if os.environ.get(env):
            cfg[key] = os.environ[env]
        cfg.setdefault(key, default)
    cfg["port"] = int(cfg["port"])
    cfg["db"] = cfg["db"] or os.path.join(root, "data", "bestmate.db")
    return cfg
