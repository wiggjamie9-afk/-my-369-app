"""SQLite storage for the hosted service: businesses (tenants), their leads and photos, sales enquiries, site settings."""
import copy
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager

from .estimate import check_config

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS tenants(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  tier TEXT NOT NULL DEFAULT 'lite',          -- lite | full
  active INTEGER NOT NULL DEFAULT 1,          -- 0 = quote page paused
  demo INTEGER NOT NULL DEFAULT 0,            -- 1 = public demo: leads are thrown away
  paid_until TEXT NOT NULL DEFAULT '',        -- YYYY-MM-DD, for the owner's own bookkeeping
  preset TEXT NOT NULL DEFAULT 'roofing',
  config_json TEXT NOT NULL,
  rates_confirmed INTEGER NOT NULL DEFAULT 0,
  phone TEXT NOT NULL DEFAULT '', licence TEXT NOT NULL DEFAULT '',
  contact_email TEXT NOT NULL DEFAULT '',     -- how the owner reaches this customer
  notify_email TEXT NOT NULL DEFAULT '',      -- where new leads are emailed
  forward_webhook TEXT NOT NULL DEFAULT '',   -- where new leads are also posted
  logo BLOB, logo_type TEXT NOT NULL DEFAULT '',
  pw_hash BLOB NOT NULL, pw_salt BLOB NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS leads(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL,
  name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL, suburb TEXT NOT NULL,
  job_type TEXT NOT NULL, difficulty TEXT NOT NULL, size TEXT NOT NULL,
  low INTEGER NOT NULL, high INTEGER NOT NULL,
  photos INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'new',         -- new | contacted | quoted | won | lost
  notes TEXT NOT NULL DEFAULT '',
  email_status TEXT NOT NULL DEFAULT '', forward_status TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS leads_tenant ON leads(tenant_id, created_at);
CREATE TABLE IF NOT EXISTS enquiries(
  id INTEGER PRIMARY KEY AUTOINCREMENT, created_at INTEGER NOT NULL,
  name TEXT NOT NULL, business TEXT NOT NULL, trade TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL,
  message TEXT NOT NULL DEFAULT '', handled INTEGER NOT NULL DEFAULT 0);
"""

SITE_DEFAULTS = {
    "service_name": "48 AI Crew Quoting",
    "tagline": "Turn website visitors into quote requests while you're on the tools.",
    "owner_name": "", "owner_phone": "", "owner_email": "",
    "price_lite": "", "price_full": "",          # shown as written; empty = "Ask for pricing"
}
LEAD_STATES = ("new", "contacted", "quoted", "won", "lost")
RESERVED = {"admin", "static", "api", "q", "enquire", "login", "logout", "demo-admin"}
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")


def now():
    return int(time.time())


def slugify(name):
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", str(name).lower())).strip("-")[:40]


def hash_password(password, salt=None):
    salt = salt or secrets.token_bytes(16)
    return hashlib.scrypt(str(password).encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32), salt


class Store:
    def __init__(self, path, presets_dir):
        self.path, self.presets_dir = path, presets_dir
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        self.photo_dir = os.path.join(os.path.dirname(os.path.abspath(path)), "photos")
        with self.tx() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def tx(self):
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    # ---------------------------------------------------------------- site settings
    def site(self):
        out = dict(SITE_DEFAULTS)
        with self.tx() as c:
            for r in c.execute("SELECT key, value FROM settings"):
                if r["key"] in out:
                    out[r["key"]] = r["value"]
        return out

    def save_site(self, changes):
        with self.tx() as c:
            for k, v in changes.items():
                if k in SITE_DEFAULTS:
                    c.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                              (k, " ".join(str(v).split())[:300]))
        return self.site()

    # ---------------------------------------------------------------- presets
    def presets(self):
        return sorted(f[:-5] for f in os.listdir(self.presets_dir) if f.endswith(".json"))

    def preset(self, name):
        if name not in self.presets():
            raise ValueError("unknown trade preset: %s" % name)
        with open(os.path.join(self.presets_dir, name + ".json"), encoding="utf-8") as fh:
            return json.load(fh)

    # ---------------------------------------------------------------- businesses
    def create_tenant(self, name, slug="", preset="roofing", tier="lite", contact_email="", phone="", demo=False):
        """-> (tenant, password). The password is returned once and stored only as a hash."""
        name = " ".join(str(name).split())[:80]
        if len(name) < 2:
            raise ValueError("the business needs a name")
        slug = slugify(slug or name)
        if not SLUG.match(slug) or slug in RESERVED:
            raise ValueError("the link name must be 3 to 40 letters, numbers or dashes (and not a reserved word)")
        if tier not in ("lite", "full"):
            raise ValueError("tier must be lite or full")
        config = self.preset(preset)
        password = secrets.token_urlsafe(9)
        pw_hash, salt = hash_password(password)
        with self.tx() as c:
            if c.execute("SELECT 1 FROM tenants WHERE slug=?", (slug,)).fetchone():
                raise ValueError("that link name is already taken: %s" % slug)
            c.execute("INSERT INTO tenants(slug,name,tier,demo,preset,config_json,rates_confirmed,phone,contact_email,pw_hash,pw_salt,created_at)"
                      " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                      (slug, name, tier, 1 if demo else 0, preset, json.dumps(config), 0, str(phone)[:40], str(contact_email)[:120],
                       pw_hash, salt, now()))
        return self.tenant(slug), password

    def tenant(self, slug=None, tenant_id=None):
        with self.tx() as c:
            r = c.execute("SELECT * FROM tenants WHERE " + ("slug=?" if slug is not None else "id=?"),
                          (slug if slug is not None else tenant_id,)).fetchone()
        if not r:
            return None
        t = dict(r)
        t["config"] = json.loads(t.pop("config_json"))
        return t

    def demos(self):
        """[(slug, product name)] for the public demos, one per trade, for the sales page."""
        with self.tx() as c:
            rows = c.execute("SELECT slug, config_json FROM tenants WHERE demo=1 AND active=1 ORDER BY slug").fetchall()
        trades = [json.loads(r["config_json"])["trade"] for r in rows]
        return [(r["slug"], t.get("label") or t["productName"]) for r, t in zip(rows, trades)]

    def tenants(self):
        since = now() - 30 * 86400
        with self.tx() as c:
            rows = c.execute(
                "SELECT t.id, t.slug, t.name, t.tier, t.active, t.demo, t.paid_until, t.preset, t.contact_email, t.phone,"
                " t.rates_confirmed, t.created_at,"
                " (SELECT COUNT(*) FROM leads l WHERE l.tenant_id=t.id) AS leads_total,"
                " (SELECT COUNT(*) FROM leads l WHERE l.tenant_id=t.id AND l.created_at>=?) AS leads_30d"
                " FROM tenants t ORDER BY t.demo, t.name COLLATE NOCASE", (since,)).fetchall()
        return [dict(r) for r in rows]

    def update_tenant(self, tenant_id, **changes):
        allowed = {"name", "tier", "active", "paid_until", "phone", "licence", "contact_email", "notify_email",
                   "forward_webhook", "rates_confirmed"}
        sets, args = [], []
        for k, v in changes.items():
            if k not in allowed:
                raise ValueError("cannot change %s" % k)
            if k == "tier" and v not in ("lite", "full"):
                raise ValueError("tier must be lite or full")
            if k == "paid_until" and v and not re.match(r"^\d{4}-\d{2}-\d{2}$", str(v)):
                raise ValueError("paid until must be a date like 2027-01-31")
            if k == "name" and len(" ".join(str(v).split())) < 2:
                raise ValueError("the business needs a name")
            if k in ("notify_email", "contact_email") and v and not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$", str(v)):
                raise ValueError("that email address doesn't look right")
            if k == "forward_webhook" and v and not re.match(r"^https://[^\s]+$", str(v)):
                raise ValueError("the webhook address must start with https://")
            sets.append(k + "=?")
            args.append(int(bool(v)) if k in ("active", "rates_confirmed") else " ".join(str(v).split())[:300])
        if sets:
            with self.tx() as c:
                c.execute("UPDATE tenants SET %s WHERE id=?" % ", ".join(sets), args + [tenant_id])
        return self.tenant(tenant_id=tenant_id)

    def save_config(self, tenant_id, config):
        problems = check_config(config)
        if problems:
            raise ValueError("; ".join(problems[:4]))
        with self.tx() as c:
            c.execute("UPDATE tenants SET config_json=? WHERE id=?", (json.dumps(config), tenant_id))

    def set_logo(self, tenant_id, data, ctype):
        with self.tx() as c:
            c.execute("UPDATE tenants SET logo=?, logo_type=? WHERE id=?", (data, ctype, tenant_id))

    def reset_password(self, tenant_id):
        password = secrets.token_urlsafe(9)
        pw_hash, salt = hash_password(password)
        with self.tx() as c:
            c.execute("UPDATE tenants SET pw_hash=?, pw_salt=? WHERE id=?", (pw_hash, salt, tenant_id))
        return password

    def check_password(self, tenant, password):
        return hmac.compare_digest(hash_password(password, tenant["pw_salt"])[0], tenant["pw_hash"])

    def public_config(self, tenant, lead_path):
        """The config.js contents for one business: its stored settings shaped the way the quote tool expects."""
        cfg = copy.deepcopy(tenant["config"])
        cfg.update({
            "tier": tenant["tier"],
            "business": {"name": tenant["name"], "logoPath": "logo" if tenant["logo"] else "", "phone": tenant["phone"], "licence": tenant["licence"]},
            "webhookUrl": "" if tenant["demo"] else lead_path,
            "ratesConfirmed": bool(tenant["rates_confirmed"]),
        })
        if tenant["tier"] != "full":      # lite pages carry the product's brand; full pages carry the business's own
            cfg["brand"] = {"name": self.site()["service_name"], "logoPath": "/static/48-ai-crew-icon.png"}
        if not tenant["demo"]:            # a homeowner sees this until the business confirms its own rates
            cfg["noticeTitle"] = "Heads up"
            cfg["ratesNotice"] = "Example prices only. This business is still putting in its own rates, so treat these as a rough guide."
        if tenant["demo"]:
            cfg["demoNotice"] = "This is a demo with example prices. Nothing you enter here is sent anywhere."
        return cfg

    # ---------------------------------------------------------------- leads
    def add_lead(self, tenant_id, lead, photos=()):
        with self.tx() as c:
            cur = c.execute(
                "INSERT INTO leads(tenant_id,created_at,name,phone,email,suburb,job_type,difficulty,size,low,high,photos)"
                " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (tenant_id, now(), lead["name"], lead["phone"], lead["email"], lead["suburb"], lead["job_type"],
                 lead["difficulty"], lead["size"], lead["low"], lead["high"], len(photos)))
            lead_id = cur.lastrowid
        if photos:
            folder = os.path.join(self.photo_dir, str(tenant_id), str(lead_id))
            os.makedirs(folder, exist_ok=True)
            for i, (data, ext) in enumerate(photos, 1):
                with open(os.path.join(folder, "%d.%s" % (i, ext)), "wb") as fh:
                    fh.write(data)
        return lead_id

    def photo(self, tenant_id, lead_id, n):
        """(bytes, content type) for one photo, only ever looked up under its own business's folder."""
        for ext, ctype in (("jpg", "image/jpeg"), ("png", "image/png"), ("webp", "image/webp")):
            path = os.path.join(self.photo_dir, str(int(tenant_id)), str(int(lead_id)), "%d.%s" % (int(n), ext))
            if os.path.isfile(path):
                with open(path, "rb") as fh:
                    return fh.read(), ctype
        return None

    def leads(self, tenant_id, status=""):
        sql = "SELECT * FROM leads WHERE tenant_id=?" + (" AND status=?" if status else "") + " ORDER BY created_at DESC, id DESC LIMIT 500"
        with self.tx() as c:
            return [dict(r) for r in c.execute(sql, (tenant_id, status) if status else (tenant_id,))]

    def lead(self, tenant_id, lead_id):
        with self.tx() as c:
            r = c.execute("SELECT * FROM leads WHERE id=? AND tenant_id=?", (lead_id, tenant_id)).fetchone()
        return dict(r) if r else None

    def update_lead(self, tenant_id, lead_id, status=None, notes=None, email_status=None, forward_status=None):
        sets, args = [], []
        if status is not None:
            if status not in LEAD_STATES:
                raise ValueError("unknown status")
            sets.append("status=?"); args.append(status)
        for col, val in (("notes", notes), ("email_status", email_status), ("forward_status", forward_status)):
            if val is not None:
                sets.append(col + "=?"); args.append(str(val)[:2000])
        if sets:
            with self.tx() as c:
                c.execute("UPDATE leads SET %s WHERE id=? AND tenant_id=?" % ", ".join(sets), args + [lead_id, tenant_id])
        return self.lead(tenant_id, lead_id)

    def lead_counts(self, tenant_id):
        with self.tx() as c:
            return {r[0]: r[1] for r in c.execute("SELECT status, COUNT(*) FROM leads WHERE tenant_id=? GROUP BY status", (tenant_id,))}

    # ---------------------------------------------------------------- sales enquiries
    def add_enquiry(self, e):
        with self.tx() as c:
            return c.execute("INSERT INTO enquiries(created_at,name,business,trade,phone,email,message) VALUES(?,?,?,?,?,?,?)",
                             (now(), e["name"], e["business"], e["trade"], e["phone"], e["email"], e.get("message", ""))).lastrowid

    def enquiries(self):
        with self.tx() as c:
            return [dict(r) for r in c.execute("SELECT * FROM enquiries ORDER BY handled, created_at DESC LIMIT 200")]

    def handle_enquiry(self, enquiry_id, handled=True):
        with self.tx() as c:
            c.execute("UPDATE enquiries SET handled=? WHERE id=?", (1 if handled else 0, enquiry_id))
