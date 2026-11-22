"""Publishing behind a human gate. Nothing posts unless: AI-labelled, compliance-clean, approved by a named person."""
from __future__ import annotations

import json
import os
from typing import Protocol

from .compliance import lint


class Publisher(Protocol):
    def publish(self, meta: dict) -> str: ...


class DryRunPublisher:
    """Records what WOULD be posted. Real adapters (TikTok/Meta/Shorts) are TODO and must follow each
    platform's terms and AI-content label rules (not yet researched)."""
    def __init__(self):
        self.posted: list[str] = []

    def publish(self, meta: dict) -> str:
        self.posted.append(meta["id"]); return f"dry-run://{meta['id']}"


class ApprovalQueue:
    def __init__(self, path: str, brief):
        self.path, self.brief = path, brief
        self.items = {}
        if os.path.exists(path):
            with open(path) as f:
                self.items = json.load(f)

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.items, f, indent=1)

    def submit(self, meta: dict) -> None:
        if not meta.get("ai_generated"):
            raise ValueError("refused: not marked AI-generated")
        probs = lint(meta["script"], self.brief)
        if probs:
            raise ValueError(f"refused by compliance: {probs}")
        self.items[meta["id"]] = {"meta": meta, "status": "pending", "approved_by": ""}
        self._save()

    def approve(self, vid: str, by: str) -> None:
        if not by.strip():
            raise ValueError("a named human must approve")
        self.items[vid].update(status="approved", approved_by=by); self._save()

    def publish_approved(self, publisher: Publisher) -> list[str]:
        urls = []
        for vid, it in self.items.items():
            if it["status"] == "approved":
                urls.append(publisher.publish(it["meta"])); it["status"] = "published"
        self._save()
        return urls
