#!/usr/bin/env python3
"""Jane backend: Twilio voice webhooks + the REST API the 48 AI app talks to. Python 3.9+, standard library only.

Phone flow: Twilio calls POST /twilio/voice -> TwiML greeting + <Gather input="speech"> -> POST /twilio/gather (loop) -> bookings
and callback requests are written to SQLite. POST /twilio/status meters minutes. Jane says she is an AI at the start of every call.
She does NOT record calls (no recording code here), so the greeting doesn't claim recording.

Env: JANE_PUBLIC_URL (e.g. https://jane.example.com, must match what Twilio calls), TWILIO_AUTH_TOKEN (signature check),
     ADMIN_TOKEN (creates businesses), JANE_DB (default jane.db), JANE_VOICE (default Polly.Nicole), PORT (default 8470),
     JANE_INSECURE_DEV=1 (skip Twilio signature check: local testing only).
Tested here only with simulated Twilio requests, never with a real Twilio account or phone call.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from xml.sax.saxutils import escape

DB_PATH = os.environ.get("JANE_DB", "jane.db")
VOICE = os.environ.get("JANE_VOICE", "Polly.Nicole")
LANG = "en-AU"
TZ = timezone(timedelta(hours=float(os.environ.get("JANE_TZ_HOURS", "8"))))  # Perth: UTC+8, no daylight saving
MAX_TURNS = 12
LOCK = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS business(id TEXT PRIMARY KEY, name TEXT, owner TEXT, forward_phone TEXT, twilio_number TEXT UNIQUE,
  api_key TEXT UNIQUE, mode TEXT DEFAULT 'on', plan_minutes REAL DEFAULT 150, minutes_used REAL DEFAULT 0, month TEXT);
CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, business_id TEXT, date TEXT, time TEXT, customer TEXT, job TEXT, address TEXT,
  phone TEXT, status TEXT, call_sid TEXT, created TEXT);
CREATE TABLE IF NOT EXISTS inbox(id TEXT PRIMARY KEY, business_id TEXT, name TEXT, need TEXT, phone TEXT, urgent INTEGER,
  call_sid TEXT, created TEXT, cleared INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS calls(call_sid TEXT PRIMARY KEY, business_id TEXT, state TEXT, started TEXT, minutes REAL DEFAULT 0, outcome TEXT);
"""


def db():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with LOCK, db() as c:
        c.executescript(SCHEMA)


def now():
    return datetime.now(TZ)


def rows(c, sql, *a):
    return [dict(r) for r in c.execute(sql, a).fetchall()]


# --------------------------------------------------------------------------- conversation engine (pure)
DANGER = re.compile(r"(gas leak|smell(s|ing)? (of )?gas|fire|smoke|sparks?|electrocut|shock(ed)?|burning smell)", re.I)
WATER = re.compile(r"(burst|flood(ing|ed)?|water (everywhere|pouring)|sewage|overflow(ing)?)", re.I)
ROBOT = re.compile(r"\b(robot|bot|ai|artificial|machine|real person|real human|are you real)\b", re.I)
HUMAN = re.compile(r"\b(speak|talk|put me through|get)\b.*\b(person|human|owner|someone|boss|manager)\b", re.I)
PRICE = re.compile(r"\b(how much|price|cost|quote|rates?|charge)\b", re.I)
DAYS = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]


def new_state():
    return {"stage": "need", "d": {}, "urgent": False, "fails": 0, "turns": 0, "outcome": "Message"}


def greeting(biz):
    return (f"G'day, you've reached {biz['name']}. I'm Jane, an AI assistant. "
            f"I can take your details and book a time, and {biz['owner'] or 'the owner'} will follow up. How can I help?")


def parse_when(text, at):
    t, d, hour = text.lower(), at, None
    dow = next((i for i, x in enumerate(DAYS) if re.search(rf"\b{x}\b", t)), -1)
    if "tomorrow" in t:
        d = at + timedelta(days=1)
    elif dow >= 0:
        wd = (at.weekday() + 1) % 7  # python Monday=0 -> JS-style Sunday=0
        d = at + timedelta(days=((dow - wd) % 7) or 7)
    elif re.search(r"\b(today|asap|now)\b", t) and at.hour < 15:
        d = at
    else:
        d = at + timedelta(days=1)
    m = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", t)
    if m:
        hour = int(m.group(1)) % 12 + (12 if m.group(3) == "pm" else 0)
    elif "morning" in t:
        hour = 9
    elif re.search(r"arvo|afternoon", t):
        hour = 14
    elif re.search(r"evening|after work", t):
        hour = 17
    return d.date(), max(8, min(16, hour if hour is not None else 9))


def free_slot(taken, day, hour):
    """taken: set of (date_iso, hour). Skips Sundays and clashes; returns (date_iso, 'HH:00')."""
    d, h = day, hour
    for _ in range(60):
        if d.weekday() != 6 and (d.isoformat(), h) not in taken:
            return d.isoformat(), f"{h:02d}:00"
        h += 1
        if h > 16:
            h, d = 8, d + timedelta(days=1)
    return day.isoformat(), f"{hour:02d}:00"


def step(st, text, biz, caller, taken, at):
    """One caller turn -> (say, end_call, actions). actions: ('job', dict) | ('inbox', dict). Mutates st."""
    st["turns"] += 1
    low, d, owner = text.lower().strip(), st["d"], biz["owner"] or "the owner"
    if st["turns"] >= MAX_TURNS and st["stage"] != "done":
        st["stage"] = "done"
        return f"I need to wrap up now. I'll ask {owner} to call you back.", True, [("inbox", cb(st, caller, "Call ended at the length limit"))]
    if st["stage"] == "done":
        if re.match(r"^(no|nope|nah|that's (all|it)|thanks|thank you|bye|cheers)", low) or st["turns"] >= MAX_TURNS - 2:
            return f"Thanks for calling {biz['name']}. Bye for now!", True, []
        return f"I've passed that on to {owner}. Anything else?", False, []
    if ROBOT.search(low) and re.search(r"\?|are you|is this", low):
        return f"Yes, I'm an AI assistant for {biz['name']}. I can take your details, and {owner} will follow up.", False, []
    if HUMAN.search(low):
        st["outcome"] = "Callback"
        st["stage"] = "done"
        return f"No worries. I'll ask {owner} to call you back on the number you're calling from. Anything else?", False, [("inbox", cb(st, caller, "Asked to speak to a person"))]
    if PRICE.search(low) and st["stage"] == "need":
        d["need"], d["quote"], st["stage"] = "Quote request", True, "name"
        return f"I can't give prices over the phone. {owner} confirms them after seeing the job. I'll book a quote visit. What's your name?", False, []
    if PRICE.search(low):
        return f"I can't give prices over the phone. {owner} will confirm.", False, []
    if st["stage"] == "need":
        if DANGER.search(low):
            st["urgent"], d["need"], st["stage"] = True, text, "name"
            return "If anyone is in danger or you smell gas, leave the building and call triple zero now. I'm marking this urgent. What's your name?", False, []
        if WATER.search(low):
            st["urgent"], d["need"], st["stage"] = True, text, "name"
            return f"That sounds urgent. If it's safe, turn the water off at the mains. I'm flagging it for {owner}. What's your name?", False, []
        if len(text.strip()) < 4:
            st["fails"] += 1
            if st["fails"] >= 2:
                st["stage"], st["outcome"] = "done", "Callback"
                return f"Sorry, I'm having trouble hearing you. I'll ask {owner} to call you back. Anything else?", False, [("inbox", cb(st, caller, "Bad line"))]
            return "Sorry, could you say that again?", False, []
        d["need"], st["stage"] = text[:200], "name"
        return "Got it. What's your name?", False, []
    if st["stage"] == "name":
        d["name"] = re.sub(r"^(my name is|it's|its|this is|i'm|im|i am)\s+", "", text.strip(), flags=re.I).strip(" .!")[:40]
        if st["urgent"]:
            st["stage"], st["outcome"] = "done", "Callback"
            return f"Thanks {d['name']}. I've marked it urgent and told {owner}. They'll call you straight back. Anything else?", False, [("inbox", cb(st, caller, d.get("need", "")))]
        st["stage"] = "address"
        return f"Thanks {d['name']}. What's the address or suburb for the job?", False, []
    if st["stage"] == "address":
        d["address"], st["stage"] = text[:80], "when"
        return "When suits you? For example, tomorrow morning.", False, []
    if st["stage"] == "when":
        day, hour = parse_when(low, at)
        date_s, time_s = free_slot(taken, day, hour)
        job = {"date": date_s, "time": time_s, "customer": d.get("name", "Caller"), "job": ("Quote visit" if d.get("quote") else d.get("need", "")[:50]),
               "address": d.get("address", "To confirm"), "phone": caller, "status": "Quoted" if d.get("quote") else "Booked"}
        st["stage"], st["outcome"] = "done", "Booked"
        when = datetime.fromisoformat(date_s + "T" + time_s + ":00").strftime("%A %d %B at %I:%M %p").replace(" 0", " ")
        return f"All booked: {job['job']} at {job['address']} on {when}. {owner} will confirm by text. Anything else?", False, [("job", job)]
    return "Sorry, can you say that again?", False, []


def cb(st, caller, need):
    d = st["d"]
    return {"name": d.get("name") or "Unknown caller", "need": need or d.get("need", "Wants a callback"), "phone": caller, "urgent": bool(st["urgent"])}


# --------------------------------------------------------------------------- TwiML + Twilio security
def twiml(*parts):
    return '<?xml version="1.0" encoding="UTF-8"?><Response>' + "".join(parts) + "</Response>"


def say(t):
    return f'<Say voice="{VOICE}" language="{LANG}">{escape(t)}</Say>'


def gather(prompt, public):
    return (f'<Gather input="speech" action="{escape(public)}/twilio/gather" method="POST" language="{LANG}" speechTimeout="auto" timeout="6">'
            f"{say(prompt)}</Gather>")


def twilio_signature(token, url, params):
    data = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()


def valid_twilio(url, params, sig):
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    if not token:
        return os.environ.get("JANE_INSECURE_DEV") == "1"
    return bool(sig) and hmac.compare_digest(twilio_signature(token, url, params), sig)


# --------------------------------------------------------------------------- business logic
def month_key():
    return now().strftime("%Y-%m")


def get_business_by_number(c, number):
    r = c.execute("SELECT * FROM business WHERE twilio_number=?", (number,)).fetchone()
    if r and r["month"] != month_key():  # new month: reset usage
        c.execute("UPDATE business SET minutes_used=0, month=? WHERE id=?", (month_key(), r["id"]))
        r = c.execute("SELECT * FROM business WHERE id=?", (r["id"],)).fetchone()
    return dict(r) if r else None


def within_hours(at):
    return at.weekday() < 5 and 8 <= at.hour < 17


def should_answer(biz, at):
    if biz["mode"] == "off":
        return False, "off"
    if biz["mode"] == "after" and within_hours(at):
        return False, "business hours"
    if biz["minutes_used"] >= biz["plan_minutes"]:
        return False, "out of minutes"
    return True, ""


def forward_or_apologise(biz, reason, public):
    if biz.get("forward_phone"):
        return twiml(say(f"Putting you through to {biz['owner'] or 'the owner'}."), f"<Dial>{escape(biz['forward_phone'])}</Dial>")
    return twiml(say(f"Sorry, we can't take your call right now. Please try {biz['name']} again soon."), "<Hangup/>")


def apply_actions(c, biz, sid, actions):
    ts = now().isoformat(timespec="seconds")
    for kind, a in actions:
        if kind == "job":
            c.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)", (uuid.uuid4().hex[:10], biz["id"], a["date"], a["time"], a["customer"], a["job"],
                                                                      a["address"], a["phone"], a["status"], sid, ts))
        else:
            c.execute("INSERT INTO inbox(id,business_id,name,need,phone,urgent,call_sid,created) VALUES(?,?,?,?,?,?,?,?)",
                      (uuid.uuid4().hex[:10], biz["id"], a["name"], a["need"], a["phone"], int(a["urgent"]), sid, ts))


def voice_incoming(p, public):
    sid, to, caller = p.get("CallSid", ""), p.get("To", ""), p.get("From", "")
    with LOCK, db() as c:
        biz = get_business_by_number(c, to)
        if not biz:
            return twiml(say("Sorry, this number isn't set up yet."), "<Hangup/>")
        ok, why = should_answer(biz, now())
        if not ok:
            c.execute("INSERT OR REPLACE INTO calls(call_sid,business_id,state,started,outcome) VALUES(?,?,?,?,?)",
                      (sid, biz["id"], "{}", now().isoformat(), "Forwarded: " + why))
            return forward_or_apologise(biz, why, public)
        c.execute("INSERT OR REPLACE INTO calls(call_sid,business_id,state,started,outcome) VALUES(?,?,?,?,?)",
                  (sid, biz["id"], json.dumps(new_state()), now().isoformat(), "Started"))
        return twiml(gather(greeting(biz), public), say(f"I didn't catch that. {biz['owner'] or 'The owner'} will call you back."), "<Hangup/>")


def voice_gather(p, public):
    sid, caller, text = p.get("CallSid", ""), p.get("From", ""), p.get("SpeechResult", "")
    with LOCK, db() as c:
        row = c.execute("SELECT * FROM calls WHERE call_sid=?", (sid,)).fetchone()
        if not row:
            return twiml(say("Sorry, something went wrong. Please call back."), "<Hangup/>")
        biz = dict(c.execute("SELECT * FROM business WHERE id=?", (row["business_id"],)).fetchone())
        st = json.loads(row["state"])
        at = now()
        taken = {(r["date"], int(r["time"][:2])) for r in c.execute("SELECT date,time FROM jobs WHERE business_id=? AND status!='Done'", (biz["id"],))}
        if not text.strip():
            st["fails"] += 1
            if st["fails"] >= 2:
                apply_actions(c, biz, sid, [("inbox", cb(st, caller, "Caller said nothing clear"))])
                c.execute("UPDATE calls SET state=?, outcome=? WHERE call_sid=?", (json.dumps(st), "Callback", sid))
                return twiml(say(f"Sorry, I couldn't hear you. {biz['owner'] or 'The owner'} will call you back."), "<Hangup/>")
            reply, end, actions = "Sorry, I didn't catch that. Could you say it again?", False, []
        else:
            reply, end, actions = step(st, text, biz, caller, taken, at)
        apply_actions(c, biz, sid, actions)
        c.execute("UPDATE calls SET state=?, outcome=? WHERE call_sid=?", (json.dumps(st), st["outcome"], sid))
        if end:
            return twiml(say(reply), "<Hangup/>")
        return twiml(gather(reply, public), say("I'll let them know. Goodbye."), "<Hangup/>")


def voice_status(p):
    sid, secs = p.get("CallSid", ""), p.get("CallDuration")
    if p.get("CallStatus") != "completed" or secs is None:
        return
    mins = round(-(-float(secs) // 6) / 10, 1)  # seconds -> minutes, rounded up to 0.1
    with LOCK, db() as c:
        row = c.execute("SELECT * FROM calls WHERE call_sid=?", (sid,)).fetchone()
        if row and not row["minutes"] and not str(row["outcome"]).startswith("Forwarded"):
            c.execute("UPDATE calls SET minutes=? WHERE call_sid=?", (mins, sid))
            c.execute("UPDATE business SET minutes_used = minutes_used + ? WHERE id=?", (mins, row["business_id"]))


# --------------------------------------------------------------------------- app API (Bearer key per business)
class ApiError(Exception):
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def api(method, path, q, body, key, admin_token):
    parts = [x for x in path.split("/") if x]
    if parts == ["admin", "business"] and method == "POST":
        if not admin_token or not hmac.compare_digest(admin_token, os.environ.get("ADMIN_TOKEN", "\0")):
            raise ApiError(401, "admin token required")
        for k in ("name", "twilio_number"):
            if not str(body.get(k, "")).strip():
                raise ApiError(400, f"{k} is required")
        bid, api_key = uuid.uuid4().hex[:8], "jk_" + secrets.token_urlsafe(24)
        with LOCK, db() as c:
            try:
                c.execute("INSERT INTO business(id,name,owner,forward_phone,twilio_number,api_key,plan_minutes,month) VALUES(?,?,?,?,?,?,?,?)",
                          (bid, body["name"], body.get("owner", ""), body.get("forward_phone", ""), body["twilio_number"], api_key,
                           float(body.get("plan_minutes", 150)), month_key()))
            except sqlite3.IntegrityError:
                raise ApiError(409, "that Twilio number is already used")
        return 200, {"id": bid, "api_key": api_key, "note": "Store the key securely; it is shown once."}
    with LOCK, db() as c:
        b = c.execute("SELECT * FROM business WHERE api_key=?", (key or "",)).fetchone()
        if not b or not key:
            raise ApiError(401, "missing or bad API key")
        b = dict(b)
        bid = b["id"]
        if parts == ["v1", "me"]:
            return 200, {k: b[k] for k in ("id", "name", "owner", "twilio_number", "forward_phone", "mode", "plan_minutes")} | {"minutes_used": round(b["minutes_used"], 1)}
        if parts == ["v1", "today"]:
            td = now().date().isoformat()
            jobs = rows(c, "SELECT * FROM jobs WHERE business_id=? AND date=? ORDER BY time", bid, td)
            calls = c.execute("SELECT COUNT(*) FROM calls WHERE business_id=? AND substr(started,1,10)=?", (bid, td)).fetchone()[0]
            return 200, {"date": td, "mode": b["mode"], "calls": calls, "booked": sum(1 for j in jobs if j["status"] == "Booked"),
                         "next": next((j for j in jobs if j["status"] != "Done"), None), "jobs": jobs}
        if parts == ["v1", "inbox"] and method == "GET":
            return 200, {"rows": [dict(r, urgent=bool(r["urgent"])) for r in rows(c, "SELECT * FROM inbox WHERE business_id=? AND cleared=0 ORDER BY created DESC", bid)]}
        if len(parts) == 4 and parts[:2] == ["v1", "inbox"] and parts[3] == "clear" and method == "POST":
            c.execute("UPDATE inbox SET cleared=1 WHERE id=? AND business_id=?", (parts[2], bid))
            return 200, {"ok": True}
        if parts == ["v1", "bookings"] and method == "GET":
            lo, hi = q.get("from", ["0000-01-01"])[0], q.get("to", ["9999-12-31"])[0]
            return 200, {"rows": rows(c, "SELECT * FROM jobs WHERE business_id=? AND date BETWEEN ? AND ? ORDER BY date,time", bid, lo, hi)}
        if parts == ["v1", "bookings"] and method == "POST":
            for k in ("date", "time", "customer", "job"):
                if not str(body.get(k, "")).strip():
                    raise ApiError(400, f"{k} is required")
            jid = uuid.uuid4().hex[:10]
            c.execute("INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?,?,?,?)", (jid, bid, body["date"], body["time"], body["customer"], body["job"], body.get("address", ""),
                                                                      body.get("phone", ""), "Booked", "", now().isoformat(timespec="seconds")))
            return 200, {"id": jid}
        if len(parts) == 4 and parts[:2] == ["v1", "jobs"] and parts[3] == "done" and method == "POST":
            c.execute("UPDATE jobs SET status='Done' WHERE id=? AND business_id=?", (parts[2], bid))
            return 200, {"ok": True}
        if parts == ["v1", "settings"] and method == "POST":
            if body.get("mode") in ("on", "after", "off"):
                c.execute("UPDATE business SET mode=? WHERE id=?", (body["mode"], bid))
            if "forward_phone" in body:
                c.execute("UPDATE business SET forward_phone=? WHERE id=?", (str(body["forward_phone"])[:20], bid))
            return 200, {"ok": True}
    raise ApiError(404, "not found")


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, payload, ctype):
        data = payload if isinstance(payload, bytes) else payload.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _json(self, code, obj):
        self._send(code, json.dumps(obj), "application/json")

    def _handle(self, method):
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        public = os.environ.get("JANE_PUBLIC_URL", f"http://{self.headers.get('Host', '')}").rstrip("/")
        try:
            if u.path.startswith("/twilio/"):
                params = {k: v[0] for k, v in parse_qs(raw.decode(), keep_blank_values=True).items()}
                if not valid_twilio(public + u.path, params, self.headers.get("X-Twilio-Signature", "")):
                    return self._send(403, "bad signature", "text/plain")
                if u.path == "/twilio/voice":
                    return self._send(200, voice_incoming(params, public), "text/xml")
                if u.path == "/twilio/gather":
                    return self._send(200, voice_gather(params, public), "text/xml")
                if u.path == "/twilio/status":
                    voice_status(params)
                    return self._send(200, "", "text/plain")
                return self._send(404, "", "text/plain")
            if u.path == "/health":
                return self._json(200, {"ok": True})
            body = json.loads(raw or b"{}") if method == "POST" else {}
            auth = self.headers.get("Authorization", "")
            key = auth[7:] if auth.startswith("Bearer ") else ""
            admin = self.headers.get("X-Admin-Token", "")
            code, payload = api(method, u.path, parse_qs(u.query), body, key, admin)
            self._json(code, payload)
        except ApiError as e:
            self._json(e.code, {"error": e.msg})
        except (ValueError, KeyError) as e:
            self._json(400, {"error": f"bad request: {e}"})

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")


def main():
    init_db()
    port = int(os.environ.get("PORT", "8470"))
    if not os.environ.get("TWILIO_AUTH_TOKEN") and os.environ.get("JANE_INSECURE_DEV") != "1":
        print("Warning: TWILIO_AUTH_TOKEN not set, so Twilio webhooks will be rejected. Set it, or JANE_INSECURE_DEV=1 for local testing.")
    print(f"Jane backend on http://0.0.0.0:{port}")
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
