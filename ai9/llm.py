"""Real-model adapters. Keys come from env vars only; HTTP is injectable so tests never hit the network.
Both return llm(system, user) -> str and track token usage in `.usage` for cost reporting.
UNVERIFIED live (no keys when written)."""
from __future__ import annotations

import json
import os
import urllib.request


def _post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


class _Base:
    def __init__(self):
        self.usage = {"in": 0, "out": 0}


class AnthropicLLM(_Base):
    def __init__(self, model: str, api_key: str | None = None, max_tokens: int = 600, http=_post):
        super().__init__()
        self.model, self.max_tokens, self.http = model, max_tokens, http
        self.key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

    def __call__(self, system: str, user: str) -> str:
        r = self.http("https://api.anthropic.com/v1/messages",
                      {"x-api-key": self.key, "anthropic-version": "2023-06-01"},
                      {"model": self.model, "max_tokens": self.max_tokens, "system": system,
                       "messages": [{"role": "user", "content": user}]})
        u = r.get("usage", {})
        self.usage["in"] += u.get("input_tokens", 0); self.usage["out"] += u.get("output_tokens", 0)
        return "".join(b.get("text", "") for b in r.get("content", []) if b.get("type") == "text")


class OpenAICompatLLM(_Base):
    """Second provider (checker / grader). Any OpenAI-compatible /chat/completions endpoint."""
    def __init__(self, base_url: str, model: str, api_key: str | None = None, http=_post):
        super().__init__()
        self.base, self.model, self.http = base_url.rstrip("/"), model, http
        self.key = api_key or os.environ.get("CHECKER_API_KEY")
        if not self.key:
            raise RuntimeError("CHECKER_API_KEY is not set")

    def __call__(self, system: str, user: str) -> str:
        r = self.http(f"{self.base}/chat/completions", {"Authorization": f"Bearer {self.key}"},
                      {"model": self.model, "messages": [{"role": "system", "content": system},
                                                         {"role": "user", "content": user}]})
        u = r.get("usage", {})
        self.usage["in"] += u.get("prompt_tokens", 0); self.usage["out"] += u.get("completion_tokens", 0)
        return r["choices"][0]["message"]["content"]
