"""Rights ledger, campaign tracker and publishing queue.

The rule this module enforces: a clip can only be approved for upload if it traces to a rights entry that is valid today and
covers the platform. Credit text from the entry is added to the description automatically. Nothing is uploaded from here;
see youtube.py (private uploads only by default).
"""
import json
import threading
import uuid
from datetime import date, datetime, timezone
from pathlib import Path

BASES = {
    "own": "My own footage or recording",
    "written_permission": "Written permission from the owner",
    "campaign_terms": "A clipping campaign's terms (clips licensed)",
    "licence": "A licence I hold (paid or free)",
    "creative_commons": "Creative Commons (with the credit it requires)",
    "public_domain": "Public domain",
}
PLATFORMS = ("youtube", "tiktok", "instagram", "facebook")
PRIVACY = ("private", "unlisted", "public")
ITEM_STATUS = ("draft", "approved", "uploaded", "posted", "failed")


class RightsError(ValueError):
    pass


class Store:
    def __init__(self, root):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()

    def read(self, name):
        p = self.root / f"{name}.json"
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []

    def write(self, name, data):
        (self.root / f"{name}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")


def _num(v, default=0.0):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return default
    if x < 0:
        raise RightsError("numbers can't be negative")
    return x


def _date(v):
    if not v:
        return ""
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except ValueError:
        raise RightsError(f"bad date: {v}")


# --------------------------------------------------------------------------- rights ledger
def add_rights(store, d):
    basis = d.get("basis")
    if basis not in BASES:
        raise RightsError("choose what permission you have")
    source = str(d.get("source", "")).strip()
    if not source:
        raise RightsError("say what the footage is (file name or description)")
    owner = str(d.get("owner", "")).strip()
    proof = str(d.get("proof", "")).strip()
    if basis != "own" and not (owner and proof):
        raise RightsError("add the owner and proof (a link, message or document reference) unless it's your own footage")
    credit = str(d.get("credit_text", "")).strip()
    if basis == "creative_commons" and not credit:
        raise RightsError("Creative Commons needs the credit line the licence requires")
    plats = [p for p in d.get("platforms", []) if p in PLATFORMS]
    if not plats:
        raise RightsError("pick at least one platform this permission covers")
    entry = {"id": uuid.uuid4().hex[:8], "source": source, "owner": owner, "basis": basis, "proof": proof, "credit_text": credit,
             "platforms": plats, "expires": _date(d.get("expires")), "notes": str(d.get("notes", ""))[:500],
             "created": datetime.now().isoformat(timespec="seconds")}
    with store.lock:
        rows = store.read("rights")
        rows.append(entry)
        store.write("rights", rows)
    return entry


def get_rights(store, rid):
    return next((r for r in store.read("rights") if r["id"] == rid), None)


def rights_ok(entry, platform="youtube", today=None):
    """(ok, reason). A permission must exist, cover the platform and not be expired."""
    if not entry:
        return False, "no rights entry linked"
    if platform not in entry["platforms"]:
        return False, f"this permission doesn't cover {platform}"
    if entry.get("expires") and date.fromisoformat(entry["expires"]) < (today or date.today()):
        return False, f"permission expired on {entry['expires']}"
    return True, ""


def delete_rights(store, rid):
    with store.lock:
        if any(i["rights_id"] == rid and i["status"] != "draft" for i in store.read("queue")):
            raise RightsError("this entry backs approved or uploaded clips; keep it as your record")
        store.write("rights", [r for r in store.read("rights") if r["id"] != rid])


def credit_line(entry):
    if entry.get("credit_text"):
        return entry["credit_text"]
    if entry["basis"] == "own":
        return ""
    return f"Footage: {entry['owner']} ({BASES[entry['basis']].lower()})"


# --------------------------------------------------------------------------- campaigns
def add_campaign(store, d):
    name = str(d.get("name", "")).strip()
    if not name:
        raise RightsError("name the campaign")
    c = {"id": uuid.uuid4().hex[:8], "name": name, "marketplace": str(d.get("marketplace", "")).strip(),
         "owner": str(d.get("owner", "")).strip(), "rate_per_1000": _num(d.get("rate_per_1000")),
         "flat_fee": _num(d.get("flat_fee")), "currency": str(d.get("currency", "USD"))[:3].upper() or "USD",
         "rules": str(d.get("rules", ""))[:1500], "rights_id": str(d.get("rights_id", "")),
         "start": _date(d.get("start")), "end": _date(d.get("end"))}
    with store.lock:
        rows = store.read("campaigns")
        rows.append(c)
        store.write("campaigns", rows)
    return c


def delete_campaign(store, cid):
    with store.lock:
        store.write("campaigns", [c for c in store.read("campaigns") if c["id"] != cid])


# --------------------------------------------------------------------------- queue
def _find(rows, iid):
    it = next((i for i in rows if i["id"] == iid), None)
    if not it:
        raise KeyError(iid)
    return it


def save_item(store, d, export_exists):
    """Create or update a draft/queue item. Updating an approved item sends it back to draft if clip fields change."""
    with store.lock:
        rows = store.read("queue")
        if d.get("id"):
            it = _find(rows, d["id"])
        else:
            it = {"id": uuid.uuid4().hex[:8], "status": "draft", "youtube_id": "", "url": "", "views": 0, "hours_spent": 0,
                  "error": "", "created": datetime.now().isoformat(timespec="seconds")}
            rows.append(it)
        editable = ("export_file", "title", "description", "tags", "privacy", "publish_at", "rights_id", "campaign_id",
                    "views", "hours_spent")
        changed_clip = False
        for k in editable:
            if k in d:
                v = d[k]
                if k == "tags":
                    v = [str(t).strip().lstrip("#") for t in (v if isinstance(v, list) else str(v).replace(",", " ").split()) if str(t).strip()][:15]
                elif k in ("views", "hours_spent"):
                    v = _num(v)
                elif k == "privacy" and v not in PRIVACY:
                    raise RightsError("privacy must be private, unlisted or public")
                elif k not in ("views", "hours_spent") and it.get(k) != v:
                    changed_clip = True
                it[k] = v
        for k, dv in (("export_file", ""), ("title", ""), ("description", ""), ("tags", []), ("privacy", "private"),
                      ("publish_at", ""), ("rights_id", ""), ("campaign_id", "")):
            it.setdefault(k, dv)
        if changed_clip and it["status"] in ("approved",):
            it["status"] = "draft"
        if d.get("status") in ("posted",) and it["status"] in ("uploaded", "posted"):
            it["status"] = "posted"
        if it["export_file"] and not export_exists(it["export_file"]):
            raise RightsError("that exported clip isn't in the exports folder")
        store.write("queue", rows)
        return it


def approve_item(store, iid, export_exists, today=None):
    with store.lock:
        rows = store.read("queue")
        it = _find(rows, iid)
        problems = []
        if not it["export_file"] or not export_exists(it["export_file"]):
            problems.append("pick an exported clip")
        t = it["title"].strip()
        if not t:
            problems.append("add a title")
        elif len(t) > 100:
            problems.append("title is over YouTube's 100 characters")
        if "[ADD" in (it["title"] + it["description"]):
            problems.append("replace the [ADD: ...] placeholders")
        ok, why = rights_ok(get_rights(store, it["rights_id"]), "youtube", today)
        if not ok:
            problems.append(why)
        if it["publish_at"]:
            try:
                when = datetime.fromisoformat(it["publish_at"].replace("Z", "+00:00"))
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                if when <= datetime.now(timezone.utc):
                    problems.append("schedule time is in the past")
            except ValueError:
                problems.append("schedule time must look like 2026-12-01T09:00:00Z")
            if it["privacy"] != "private":
                problems.append("a scheduled upload must be private until it goes live")
        if problems:
            raise RightsError("; ".join(problems))
        it["status"] = "approved"
        it["error"] = ""
        store.write("queue", rows)
        return it


def unapprove_item(store, iid):
    with store.lock:
        rows = store.read("queue")
        it = _find(rows, iid)
        if it["status"] in ("uploaded", "posted"):
            raise RightsError("already uploaded")
        it["status"] = "draft"
        store.write("queue", rows)
        return it


def full_description(store, it):
    entry = get_rights(store, it["rights_id"])
    cl = credit_line(entry) if entry else ""
    return (it["description"].rstrip() + (f"\n\nCredit: {cl}" if cl else "")).strip()


def set_result(store, iid, **kw):
    with store.lock:
        rows = store.read("queue")
        it = _find(rows, iid)
        it.update(kw)
        store.write("queue", rows)
        return it


def delete_item(store, iid):
    with store.lock:
        rows = store.read("queue")
        it = _find(rows, iid)
        if it["status"] in ("approved", "uploaded", "posted"):
            raise RightsError("unapprove it first (uploaded clips stay as your record)") if it["status"] == "approved" else RightsError("uploaded clips stay as your record")
        store.write("queue", [i for i in rows if i["id"] != iid])


# --------------------------------------------------------------------------- earnings
def summary(store):
    camps = {c["id"]: c for c in store.read("campaigns")}
    items = store.read("queue")
    out, tot = [], {"views": 0, "earnings": 0.0, "hours": 0.0, "clips": 0}
    for cid, c in camps.items():
        its = [i for i in items if i.get("campaign_id") == cid]
        live = [i for i in its if i["status"] in ("uploaded", "posted")]
        views = sum(i["views"] for i in its)
        earn = views / 1000 * c["rate_per_1000"] + c["flat_fee"] * len(live)
        hrs = sum(i["hours_spent"] for i in its)
        out.append({"id": cid, "name": c["name"], "currency": c["currency"], "clips": len(its), "live": len(live), "views": views,
                    "earnings": round(earn, 2), "hours": hrs, "per_hour": round(earn / hrs, 2) if hrs else None})
        tot["views"] += views
        tot["earnings"] += earn
        tot["hours"] += hrs
        tot["clips"] += len(its)
    tot["earnings"] = round(tot["earnings"], 2)
    tot["per_hour"] = round(tot["earnings"] / tot["hours"], 2) if tot["hours"] else None
    return {"campaigns": out, "total": tot}
