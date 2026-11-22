#!/usr/bin/env python3
"""Clip Studio as an MCP server, so an AI agent (Claude Desktop, Claude Code, or any MCP-capable agent) can build content with it.

It talks to a running Clip Studio (python3 server.py) over its local HTTP API and speaks MCP (JSON-RPC 2.0 over stdio, no dependencies).

SAFETY MODEL: agents propose, humans approve.
  Exposed: look at media/exports/rights, find highlights, make clips, build carousels, plan calendars, queue DRAFTS.
  NOT exposed (on purpose): creating or deleting rights entries, approving, uploading, deleting queue items.
  An agent therefore can't invent a permission or publish anything. You approve and upload in the Clipping page.

Config (Claude Desktop / Claude Code):  {"mcpServers": {"clip-studio": {"command": "python3", "args": ["/full/path/to/mcp_server.py"]}}}
Env: CLIP_STUDIO_URL (default http://127.0.0.1:8369)
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

BASE = os.environ.get("CLIP_STUDIO_URL", "http://127.0.0.1:8369").rstrip("/")
_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # local server: never through a proxy
PROTOCOLS = ["2025-06-18", "2025-03-26", "2024-11-05"]


class ToolError(Exception):
    pass


def http(path, body=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json"} if body is not None else {})
    try:
        with _opener.open(req, timeout=60) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read()).get("error", e.reason)
        except ValueError:
            msg = e.reason
        raise ToolError(str(msg))
    except (urllib.error.URLError, OSError):
        raise ToolError(f"Clip Studio isn't running at {BASE}. Start it with:  python3 server.py")


def run_job(path, body, wait):
    """Start a background job and wait up to `wait` seconds. Long jobs return a job_id to poll with cs_job_status."""
    j = http(path, body)
    deadline = time.time() + max(0, wait)
    while j.get("status") == "running" and time.time() < deadline:
        time.sleep(1.0)
        j = http("/api/jobs/" + j["id"])
    return summarize_job(j)


def summarize_job(j):
    if j.get("status") == "error":
        raise ToolError(j.get("error") or "job failed")
    if j.get("status") == "running":
        return {"status": "running", "job_id": j["id"], "progress": j.get("progress"), "message": j.get("message"),
                "next": "call cs_job_status with this job_id in a minute"}
    res = j.get("result")
    if isinstance(res, dict):
        res = {k: v for k, v in res.items() if k not in ("energy", "cuts")}  # big arrays the agent doesn't need
    return {"status": "done", "result": res}


# --------------------------------------------------------------------------- tools
def t_status(a):
    caps = http("/api/capabilities")
    q = http("/api/queue")["rows"]
    return {"capabilities": {k: caps.get(k) for k in ("ffmpeg", "encoder", "whisper", "opencv", "llm", "vision", "ram_gb")},
            "media_files": len(http("/api/media")), "exports": len(http("/api/exports")),
            "queue": {s: sum(1 for i in q if i["status"] == s) for s in ("draft", "approved", "uploaded", "posted", "failed")}}


def t_list_media(a):
    return [{k: m[k] for k in ("name", "duration", "width", "height", "audio_only")} for m in http("/api/media")]


def t_list_exports(a):
    return http("/api/exports")


def t_find_highlights(a):
    return run_job("/api/analyze", {"name": a["name"], "clip_len": a.get("clip_len", 25), "count": a.get("count", 8),
                                    "deep": bool(a.get("speech_aware", False)), "llm": "auto", "vision": False}, a.get("wait_seconds", 50))


def t_make_clips(a):
    settings = {"format": a.get("format", "9:16"), "layout": a.get("layout", "crop"), "loudnorm": True,
                "brand": {"text": a.get("watermark", ""), "progress": bool(a.get("progress_bar", False))},
                "captions": {"enabled": bool(a.get("captions", True)), "words_per": 3, "upper": True}}
    return run_job("/api/auto", {"name": a["name"], "count": a.get("count", 3), "clip_len": a.get("clip_len", 25),
                                 "deep": bool(a.get("speech_aware", True)), "llm": "auto", "vision": False, "settings": settings},
                   a.get("wait_seconds", 50))


def t_build_carousel(a):
    if not a.get("slides"):
        raise ToolError("slides is required")
    return run_job("/api/carousel", {"format": a.get("format", "1:1"), "handle": a.get("handle", ""), "accent": a.get("accent", "#ff2e88"),
                                     "numbering": True, "video": False, "slides": a["slides"]}, a.get("wait_seconds", 50))


def t_plan_calendar(a):
    brief = a.get("brief") or {}
    if not str(brief.get("business", "")).strip():
        raise ToolError("brief.business is required")
    client = http("/api/client", {"id": a.get("client_id"), "brief": brief}) if a.get("client_id") else http("/api/client", {"brief": brief})
    out = run_job(f"/api/client/{client['id']}/generate", {"weeks": a.get("weeks", 4), "start": a.get("start"), "llm": a.get("writer", "auto")},
                  a.get("wait_seconds", 50))
    out["client_id"] = client["id"]
    if out.get("status") == "done":
        full = http(f"/api/client/{client['id']}")
        out["posts"] = len(full["posts"])
        out["posts_needing_owner_input"] = sum(1 for p in full["posts"] if "[ADD:" in json.dumps(p))
        out["note"] = "Posts with [ADD: ...] need real facts from the business owner. Ask them; do not invent."
    return out


def t_list_rights(a):
    return http("/api/rights")["rows"]


def t_queue_draft(a):
    need = [k for k in ("export_file", "title", "rights_id") if not str(a.get(k, "")).strip()]
    if need:
        raise ToolError("missing: " + ", ".join(need) + ". Use cs_list_rights; if no entry covers this clip, ask the human to add one.")
    body = {k: a[k] for k in ("export_file", "title", "description", "tags", "rights_id", "campaign_id") if k in a}
    body["privacy"] = "private"  # drafts are always private; the human decides later
    item = http("/api/queue", body)
    return {"id": item["id"], "status": item["status"], "note": "Draft only. The human approves and uploads in the Clipping page."}


def t_queue_list(a):
    return [{k: i[k] for k in ("id", "title", "status", "export_file", "rights_id", "error") if k in i} for i in http("/api/queue")["rows"]]


def t_job_status(a):
    return summarize_job(http("/api/jobs/" + a["job_id"]))


_WAIT = {"type": "integer", "description": "seconds to wait before returning a job_id to poll (default 50)"}
TOOLS = {
    "cs_status": (t_status, "What Clip Studio can do on this machine (encoder, transcription, local AI) and how many clips are queued.", {"type": "object", "properties": {}}),
    "cs_list_media": (t_list_media, "List source videos/audio in the media bin.", {"type": "object", "properties": {}}),
    "cs_list_exports": (t_list_exports, "List exported clips (mp4) available to queue.", {"type": "object", "properties": {}}),
    "cs_find_highlights": (t_find_highlights, "Rank the best moments in a source video by audio energy and cuts (optionally also by what is said). Returns start/end/score/reasons.",
                           {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "clip_len": {"type": "integer"}, "count": {"type": "integer"},
                                                                                  "speech_aware": {"type": "boolean"}, "wait_seconds": _WAIT}}),
    "cs_make_clips": (t_make_clips, "Find the best moments in a source video and export finished clips (reframed, captioned, loudness-normalised). Only use sources the human has permission to clip.",
                      {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "count": {"type": "integer"}, "clip_len": {"type": "integer"},
                                                                             "format": {"type": "string", "enum": ["9:16", "4:5", "1:1", "16:9"]}, "layout": {"type": "string", "enum": ["crop", "blur"]},
                                                                             "captions": {"type": "boolean"}, "speech_aware": {"type": "boolean"}, "watermark": {"type": "string"},
                                                                             "progress_bar": {"type": "boolean"}, "wait_seconds": _WAIT}}),
    "cs_build_carousel": (t_build_carousel, "Render a numbered image carousel (PNGs + zip) from slide copy. Slides: {kind: cover|text|cta, title, body, source?, t?}. Max 10.",
                          {"type": "object", "required": ["slides"], "properties": {"slides": {"type": "array", "items": {"type": "object"}}, "format": {"type": "string"},
                                                                                    "handle": {"type": "string"}, "accent": {"type": "string"}, "wait_seconds": _WAIT}}),
    "cs_plan_calendar": (t_plan_calendar, "Create/update a client brief and generate a content calendar from the business owner's real facts. Never invent facts: put only facts the owner supplied in brief.facts.",
                         {"type": "object", "required": ["brief"], "properties": {"brief": {"type": "object", "description": "business, niche, service, city, audience, tone, cta, handle, platforms[], posts_per_week, facts[]"},
                                                                               "client_id": {"type": "string"}, "weeks": {"type": "integer"}, "start": {"type": "string"}, "wait_seconds": _WAIT}}),
    "cs_list_rights": (t_list_rights, "Read the rights ledger (permissions the human recorded). You cannot create or change entries.", {"type": "object", "properties": {}}),
    "cs_queue_draft": (t_queue_draft, "Add an exported clip to the publishing queue as a PRIVATE DRAFT linked to an existing rights entry. Cannot approve or upload.",
                       {"type": "object", "required": ["export_file", "title", "rights_id"], "properties": {"export_file": {"type": "string"}, "title": {"type": "string"},
                                                                                                           "description": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}},
                                                                                                           "rights_id": {"type": "string"}, "campaign_id": {"type": "string"}}}),
    "cs_queue_list": (t_queue_list, "List queue items and their status (draft/approved/uploaded/failed).", {"type": "object", "properties": {}}),
    "cs_job_status": (t_job_status, "Check a long-running job started by another tool.", {"type": "object", "required": ["job_id"], "properties": {"job_id": {"type": "string"}}}),
}


# --------------------------------------------------------------------------- MCP / JSON-RPC over stdio
def handle(msg):
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if method == "initialize":
        want = params.get("protocolVersion")
        return {"jsonrpc": "2.0", "id": mid, "result": {"protocolVersion": want if want in PROTOCOLS else PROTOCOLS[0], "capabilities": {"tools": {}},
                                                       "serverInfo": {"name": "clip-studio", "version": "1.0"},
                                                       "instructions": "Agents propose, humans approve: you can make clips, carousels, calendars and queue drafts. Never invent rights, facts or approvals. Only clip material the human has permission to use."}}
    if method == "ping":
        return {"jsonrpc": "2.0", "id": mid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": [{"name": n, "description": d, "inputSchema": s} for n, (_, d, s) in TOOLS.items()]}}
    if method == "tools/call":
        name, args = params.get("name"), params.get("arguments") or {}
        if name not in TOOLS:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602, "message": f"unknown tool: {name}"}}
        try:
            out = TOOLS[name][0](args)
            text, err = json.dumps(out, indent=1, ensure_ascii=False)[:20000], False
        except ToolError as e:
            text, err = str(e), True
        except KeyError as e:
            text, err = f"missing argument: {e}", True
        except Exception as e:  # never crash the stdio loop
            text, err = f"unexpected error: {e}", True
        return {"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text}], "isError": err}}
    if mid is None:  # notification (e.g. notifications/initialized): no reply
        return None
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"method not found: {method}"}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}) + "\n")
            sys.stdout.flush()
            continue
        resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
