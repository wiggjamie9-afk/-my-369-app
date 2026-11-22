"""MuAPI hosted provider (the paid video API used by the MIT-licensed Open-AI-UGC repo).

Re-implemented in Python from the endpoint list and payload shape in that repo
(see NOTICE). UNVERIFIED against the live service: no key was available.
  * POST {base}/api/v1/<model-endpoint>  with header x-api-key, JSON payload  (shape from the repo)
  * Result polling path is NOT in the repo (it uses webhooks). `RESULT_PATH` is a best guess - fix from MuAPI docs.
  * credits_per_second numbers are the repo app's OWN credit units, not dollars. usd_per_credit must be set
    from MuAPI's real pricing before the cost gate will let anything run.
"""
from __future__ import annotations

import json
import os
import time
import urllib.request

BASE = "https://api.muapi.ai"
RESULT_PATH = "/api/v1/predictions/{id}/result"      # UNVERIFIED guess

MODELS = {   # endpoint, credits/sec by resolution (repo app units)
    "grok-video": ("grok-imagine-image-to-video", {"480p": 5, "720p": 10}),
    "veo-3-1": ("veo3.1-image-to-video", {"720p": 500, "1080p": 650, "4k": 740}),
    "happy-horse": ("happy-horse-1-image-to-video-720p", {"720p": 36}),
    "seedance-2": ("seedance-2-image-to-video", {"default": 50}),
}


def _http(method, url, headers=None, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **(headers or {})}, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


class MuapiProvider:
    paid = True

    def __init__(self, model="happy-horse", resolution="720p", reference_images=None,
                 usd_per_credit=None, api_key=None, http=_http, download=None, poll_s=5, max_polls=120):
        self.model, self.res, self.refs = model, resolution, reference_images or []
        self.usd_per_credit = usd_per_credit
        self.key = api_key or os.environ.get("MUAPI_API_KEY")
        self.http, self.poll_s, self.max_polls = http, poll_s, max_polls
        self.download = download or (lambda url, out: urllib.request.urlretrieve(url, out))

    def estimate_cost(self, shots) -> float:
        if self.usd_per_credit is None:
            raise NotImplementedError("set usd_per_credit from MuAPI's real price list first")
        rates = MODELS[self.model][1]
        rate = rates.get(self.res, rates.get("default"))
        return sum(s.seconds for s in shots) * rate * self.usd_per_credit

    def generate(self, shot, out: str) -> str:
        if not self.key:
            raise RuntimeError("MUAPI_API_KEY not set")
        payload = {"prompt": shot.prompt, "duration": int(round(shot.seconds)), "aspect_ratio": "9:16",
                   "images_list": self.refs, **({"image_url": self.refs[0]} if self.refs else {})}
        sub = self.http("POST", f"{BASE}/api/v1/{MODELS[self.model][0]}", {"x-api-key": self.key}, payload)
        rid = sub.get("request_id") or sub.get("id")
        for _ in range(self.max_polls):
            res = self.http("GET", BASE + RESULT_PATH.format(id=rid), {"x-api-key": self.key})
            if res.get("status") == "failed" or res.get("error"):
                raise RuntimeError(f"generation failed: {res.get('error')}")
            if res.get("status") == "completed" and res.get("outputs"):
                self.download(res["outputs"][0], out)
                return out
            time.sleep(self.poll_s)
        raise TimeoutError("generation did not finish")
