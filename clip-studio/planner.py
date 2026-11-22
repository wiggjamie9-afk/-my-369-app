"""Client content planner: client brief -> 30-day calendar -> human approval -> CSV / approval doc export.

Design rules (deliberate):
  * Posts are built from facts the CLIENT supplies (services, offers, FAQs, proof). Where a fact is missing the post
    gets an [ADD: ...] placeholder, and a post with a placeholder cannot be approved or exported. This keeps content
    original and specific, which is what Meta/YouTube reward, and stops mass-produced filler.
  * Nothing is published from here. Export a CSV for a scheduler (Buffer, Metricool, Blotato's importer/API, etc.) or paste
    into your own tool; connecting a publishing API is a separate step that needs your account and keys.
"""
import csv
import io
import json
import re
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import engines as E

PLATFORMS = ["instagram", "facebook", "tiktok", "youtube", "linkedin", "threads", "pinterest", "bluesky", "x"]
SHORT = {"threads": 500, "bluesky": 300, "x": 280}  # rough character limits for short-text networks
FORMATS = ("carousel", "clip", "photo", "text")
STATUSES = ("draft", "approved", "scheduled", "posted")
# pillar id, what it does, default format
PILLARS = [
    ("educate", "Teach one useful thing", "carousel"),
    ("proof", "Show real work, a result or a customer story", "photo"),
    ("behind", "Behind the scenes / meet the team", "clip"),
    ("offer", "Promote one specific offer or service", "carousel"),
    ("faq", "Answer a question customers really ask", "clip"),
    ("myth", "Bust a common myth", "text"),
    ("community", "Local, seasonal or community tie-in", "photo"),
]
TIMES = ["07:30", "12:15", "18:30"]  # starting suggestions only; adjust once you see the client's analytics
PLACEHOLDER = re.compile(r"\[ADD:[^\]]*\]")


def has_placeholder(post):
    blob = " ".join(str(post.get(k, "")) for k in ("hook", "caption", "cta")) + " ".join(
        f"{s.get('title', '')} {s.get('body', '')}" for s in post.get("slides", []))
    return bool(PLACEHOLDER.search(blob))


def fit_format(platform, fmt):
    """Make the planned format valid for the platform (e.g. TikTok/Shorts need video)."""
    if platform in ("tiktok", "youtube"):
        return "clip"
    if platform in ("threads", "bluesky", "x"):
        return fmt if fmt in ("text", "photo") else "photo"
    if platform == "linkedin":
        return fmt if fmt in ("text", "carousel", "photo") else "text"
    if platform == "pinterest":
        return fmt if fmt in ("photo", "carousel") else "photo"
    return fmt


def adapt(caption, hashtags, platform):
    tags = " ".join("#" + h.lstrip("#") for h in hashtags[: (2 if platform in ("linkedin", "x", "bluesky") else 5)])
    text = caption.strip()
    limit = SHORT.get(platform)
    if limit:
        room = limit - (len(tags) + 2 if tags else 0)
        if len(text) > room:
            text = text[: max(0, room - 1)].rstrip() + "…"
    return (text + ("\n\n" + tags if tags else "")).strip()


# --------------------------------------------------------------------------- schedule
def schedule_dates(start, weeks, per_week):
    """Evenly spread `per_week` posts across the week (Mon..Sun), for `weeks` weeks, starting on/after `start`."""
    per_week = max(1, min(int(per_week), 14))
    d0 = start - timedelta(days=start.weekday())  # Monday of the start week
    slots = []
    per_day = [0] * 7
    for i in range(per_week):
        per_day[round(i * 7 / per_week) % 7] += 1
    for w in range(int(weeks)):
        for dow in range(7):
            for k in range(per_day[dow]):
                d = d0 + timedelta(days=w * 7 + dow)
                if d >= start:
                    slots.append((d, TIMES[(len(slots) + k) % len(TIMES)]))
    return slots


# --------------------------------------------------------------------------- content
def _fact(facts, i):
    """Each fact is used once. When they run out the post gets an [ADD: ...] prompt instead of a repeat,
    because recycled content is what platforms treat as unoriginal."""
    return facts[i] if i < len(facts) else None


def template_post(brief, pillar, idx):
    """Rule-based fallback. Uses the client's own facts; otherwise leaves an [ADD: ...] prompt."""
    biz, svc = brief.get("business", "the business"), brief.get("service") or brief.get("niche") or "what we do"
    city, facts = brief.get("city", ""), [f for f in brief.get("facts", []) if f.strip()]
    f = _fact(facts, idx)
    cta = brief.get("cta") or "Message us to book."
    pid = pillar[0]
    if pid == "educate":
        hook = f"3 things to know before you book {svc}"
        body = f or "[ADD: one practical tip from your real experience]"
        slides = [{"kind": "cover", "title": hook, "body": biz}, {"kind": "text", "title": "1", "body": body},
                  {"kind": "text", "title": "2", "body": "[ADD: second tip]"}, {"kind": "text", "title": "3", "body": "[ADD: third tip]"},
                  {"kind": "cta", "title": "Save this", "body": cta}]
        cap = f"{hook}.\n\n{body}\n\n{cta}"
    elif pid == "proof":
        hook = "A recent job we're proud of"
        body = f or "[ADD: what you did, where, and the result]"
        slides = []
        cap = f"{hook}: {body}\n\n{cta}"
    elif pid == "behind":
        hook = f"A day at {biz}"
        body = f or "[ADD: what happens on a typical day, who the team are]"
        slides = []
        cap = f"{hook}. {body}\n\n{cta}"
    elif pid == "offer":
        hook = f"This month: {svc}"
        body = f or "[ADD: the offer, who it's for, and how to claim it]"
        slides = [{"kind": "cover", "title": hook, "body": biz}, {"kind": "text", "title": "The offer", "body": body},
                  {"kind": "cta", "title": "Book now", "body": cta}]
        cap = f"{hook}.\n\n{body}\n\n{cta}"
    elif pid == "faq":
        hook = "A question we get all the time"
        body = f or "[ADD: the question and your honest answer]"
        slides = []
        cap = f"{hook}: {body}\n\n{cta}"
    elif pid == "myth":
        hook = f"Myth: {svc} is always expensive or complicated"
        body = f or "[ADD: the myth and what's actually true]"
        slides = []
        cap = f"{hook}\n\n{body}\n\n{cta}"
    else:
        hook = f"Local to {city}" if city else "Local and proud"
        body = f or "[ADD: a local event, season or community story]"
        slides = []
        cap = f"{hook}. {body}\n\n{cta}"
    tags = [re.sub(r"\W+", "", w.lower()) for w in (brief.get("hashtags") or [svc, city, biz]) if w]
    return {"pillar": pid, "hook": hook, "caption": cap, "hashtags": [t for t in tags if t][:5],
            "asset_note": {"photo": "Real photo from a recent job", "clip": "Short phone video (15-30 s)",
                           "carousel": "Carousel (build from slides)", "text": "Text only"}[pillar[2]],
            "slides": slides}


def llm_posts(brief, n, model):
    """Ask a local LLM for n posts built only from the client's facts. Returns a list or raises E.EngineError."""
    facts = "\n".join("- " + f for f in brief.get("facts", []) if f.strip()) or "(none given)"
    pillars = ", ".join(p[0] for p in PILLARS)
    prompt = (f"You write social media posts for a small business. Business: {brief.get('business')}. Type: {brief.get('niche')}. "
              f"City: {brief.get('city', '')}. Audience: {brief.get('audience', '')}. Tone: {brief.get('tone', 'friendly, plain')}. "
              f"Call to action: {brief.get('cta', '')}.\n"
              "Use ONLY the facts below. Never invent prices, results, reviews, names, dates or claims. If a post needs a fact you "
              "don't have, write [ADD: what is needed] in its place. Write like a real local business, not an ad.\n"
              f"Facts from the owner:\n{facts}\n\n"
              f'Reply with JSON only: {{"posts":[{{"pillar":"<one of: {pillars}>","hook":"<=10 words","caption":"<=60 words","hashtags":["tag"],'
              f'"asset_note":"what real photo/video to use","slides":[{{"title":"","body":""}}]}}]}} with exactly {n} posts, '
              "rotating the pillars. Include 3-5 slides only for carousel-style posts; otherwise an empty slides list.")
    j = E.chat_json(model, prompt)
    out = []
    for p in (j.get("posts") or [])[:n]:
        if isinstance(p, dict) and p.get("caption"):
            out.append({"pillar": p.get("pillar") if p.get("pillar") in [x[0] for x in PILLARS] else "educate",
                        "hook": str(p.get("hook", ""))[:90], "caption": str(p["caption"])[:900],
                        "hashtags": [str(h).lstrip("#") for h in (p.get("hashtags") or [])][:5],
                        "asset_note": str(p.get("asset_note", ""))[:120],
                        "slides": [{"kind": "text", "title": str(s.get("title", ""))[:60], "body": str(s.get("body", ""))[:200]}
                                   for s in (p.get("slides") or []) if isinstance(s, dict)][:8]})
    if len(out) < max(1, n // 2):
        raise E.EngineError("model returned too few usable posts")
    return out


def generate(brief, weeks=4, start=None, model=None):
    """Build the calendar. Returns (posts, engine)."""
    start = start or date.today()
    if isinstance(start, str):
        start = datetime.strptime(start, "%Y-%m-%d").date()
    slots = schedule_dates(start, weeks, brief.get("posts_per_week", 4))
    pillars = {p[0]: p for p in PILLARS}
    engine, drafts = "template", None
    if model:
        try:
            drafts, engine = llm_posts(brief, len(slots), model), model
        except (E.EngineError, AttributeError, TypeError, ValueError):
            drafts = None
    platforms = [p for p in brief.get("platforms", ["instagram", "facebook"]) if p in PLATFORMS] or ["instagram"]
    posts = []
    for i, (d, tm) in enumerate(slots):
        pil = PILLARS[i % len(PILLARS)]
        base = drafts[i] if drafts and i < len(drafts) else template_post(brief, pil, i)
        fmt = pillars.get(base["pillar"], pil)[2]
        if base.get("slides") and fmt != "carousel":
            fmt = "carousel"
        posts.append({"id": uuid.uuid4().hex[:8], "date": d.isoformat(), "time": tm, "platforms": platforms, "format": fmt,
                      "status": "draft", "assets": [], **{k: base[k] for k in ("pillar", "hook", "caption", "hashtags", "asset_note", "slides")}})
    return posts, engine


# --------------------------------------------------------------------------- store
def _path(root, cid):
    return Path(root) / f"{re.sub(r'[^a-z0-9_-]', '', cid.lower())}.json"


def save_client(root, client):
    Path(root).mkdir(parents=True, exist_ok=True)
    _path(root, client["id"]).write_text(json.dumps(client, indent=1), encoding="utf-8")
    return client


def load_client(root, cid):
    p = _path(root, cid)
    if not p.is_file():
        raise KeyError(cid)
    return json.loads(p.read_text(encoding="utf-8"))


def list_clients(root):
    out = []
    for p in sorted(Path(root).glob("*.json")) if Path(root).is_dir() else []:
        c = json.loads(p.read_text(encoding="utf-8"))
        n = c.get("posts", [])
        out.append({"id": c["id"], "business": c["brief"].get("business", ""), "posts": len(n),
                    "approved": sum(1 for x in n if x["status"] in ("approved", "scheduled", "posted"))})
    return out


def new_client(brief):
    brief = dict(brief)
    brief["facts"] = [f.strip() for f in brief.get("facts", []) if str(f).strip()]
    return {"id": uuid.uuid4().hex[:8], "brief": brief, "posts": [], "created": datetime.now().isoformat(timespec="seconds")}


def update_post(client, post_id, patch):
    post = next((p for p in client["posts"] if p["id"] == post_id), None)
    if not post:
        raise KeyError(post_id)
    for k in ("hook", "caption", "hashtags", "date", "time", "platforms", "format", "asset_note", "slides", "status"):
        if k in patch:
            post[k] = patch[k]
    if post["format"] not in FORMATS or post["status"] not in STATUSES:
        raise ValueError("bad format or status")
    if post["status"] != "draft" and has_placeholder(post):
        raise ValueError("fill in every [ADD: ...] before approving")
    return post


# --------------------------------------------------------------------------- export
def export_rows(client, only_approved=True):
    rows = []
    for p in sorted(client["posts"], key=lambda x: (x["date"], x["time"])):
        if only_approved and p["status"] == "draft":
            continue
        if has_placeholder(p):
            continue
        for pf in p["platforms"]:
            rows.append({"post_id": p["id"], "date": p["date"], "time": p["time"], "platform": pf,
                         "format": fit_format(pf, p["format"]), "caption": adapt(p["caption"], p["hashtags"], pf),
                         "media_note": p.get("asset_note", ""), "status": p["status"]})
    return rows


def to_csv(client, only_approved=True):
    rows = export_rows(client, only_approved)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=["post_id", "date", "time", "platform", "format", "caption", "media_note", "status"])
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()


def to_markdown(client):
    """Client approval document."""
    b = client["brief"]
    lines = [f"# Content calendar: {b.get('business', '')}", "", f"Prepared {date.today().isoformat()}. Please reply with changes or approve each post.", ""]
    for p in sorted(client["posts"], key=lambda x: (x["date"], x["time"])):
        lines += [f"## {p['date']} {p['time']} · {', '.join(p['platforms'])} · {p['format']}", f"**{p['hook']}**", "", p["caption"], "",
                  f"Tags: {' '.join('#' + h for h in p['hashtags'])}", f"Visual: {p.get('asset_note', '')}", f"Status: {p['status']}", ""]
    return "\n".join(lines)
