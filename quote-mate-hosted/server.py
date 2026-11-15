#!/usr/bin/env python3
"""Quote Mate, hosted: one server, many tradies.

Each business gets its own quote page at /q/<name>/ (the Roof Quote Mate tool, fed that business's
own rates), a lead inbox at /q/<name>/admin, and you get an owner console at /admin.

    ADMIN_PASSWORD=... python3 server.py        http://127.0.0.1:8090/

Standard library only. Settings come from environment variables; nothing secret is in the repo:
    ADMIN_PASSWORD   owner console password (the console is off without it)
    HOST, PORT       default 127.0.0.1:8090
    QM_DB            SQLite file (default data/quotemate.db; photos are stored beside it)
    QM_TOOL_DIR      folder holding the quote tool (default ../roof-quote-mate)
    PUBLIC_URL       e.g. https://quotes.example.com (used in emails; default: taken from the request)
    TRUST_PROXY=1    behind Caddy/nginx: read the visitor's address from X-Forwarded-For
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM, SMTP_TLS   to email leads
"""
import csv
import hashlib
import hmac
import io
import json
import os
import re
import secrets
import sys
import threading
import time
import urllib.parse
from email.parser import BytesParser
from email.policy import default as email_policy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from qm import deliver, pages                    # noqa: E402
from qm.estimate import estimate, money          # noqa: E402
from qm.store import Store, LEAD_STATES          # noqa: E402

VERSION = "1.0.0"
TOOL_FILES = {"app.css": "text/css; charset=utf-8", "app.js": "text/javascript; charset=utf-8",
              "estimate.js": "text/javascript; charset=utf-8", "full.js": "text/javascript; charset=utf-8"}
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; "
       "base-uri 'none'; form-action 'self'; frame-ancestors 'self'")
MAX_FORM, MAX_LEAD, MAX_PHOTO, MAX_LOGO = 64 * 1024, 18 * 1024 * 1024, 4 * 1024 * 1024, 400 * 1024
SESSION_DAYS = 30
EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")


def image_kind(data):
    """('jpg' | 'png' | 'webp', content type) from the file's first bytes, or None. The name and the
    type the browser claims are ignored; SVG is refused because it can carry script."""
    if data[:3] == b"\xff\xd8\xff":
        return "jpg", "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png", "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


class Halt(Exception):
    def __init__(self, status, message="", headers=None):
        super().__init__(message)
        self.status, self.headers = status, headers or {}


class App:
    def __init__(self, env):
        self.env = env
        db = env.get("QM_DB") or os.path.join(ROOT, "data", "quotemate.db")
        self.store = Store(db, os.path.join(ROOT, "presets"))
        self.tool_dir = env.get("QM_TOOL_DIR") or os.path.join(os.path.dirname(ROOT), "roof-quote-mate")
        for name in ("index.html",) + tuple(TOOL_FILES):
            if not os.path.isfile(os.path.join(self.tool_dir, name)):
                raise SystemExit("The quote tool is missing %s (looked in %s). Set QM_TOOL_DIR." % (name, self.tool_dir))
        self.admin_password = env.get("ADMIN_PASSWORD", "")
        self.smtp = deliver.mail_settings(env)
        self.trust_proxy = env.get("TRUST_PROXY") == "1"
        self.allow_private_forward = env.get("QM_ALLOW_PRIVATE_FORWARD") == "1"      # tests only
        self.lock = threading.Lock()
        self.hits = {}                                 # (what, who) -> recent timestamps
        secret_path = os.path.join(os.path.dirname(os.path.abspath(db)), ".session-secret")
        try:
            with open(secret_path) as fh:
                secret = fh.read().strip()
        except OSError:
            secret = secrets.token_hex(32)
            fd = os.open(secret_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write(secret)
        self.secret = secret.encode()
        for preset in self.store.presets():            # a public demo for each trade, linked from the sales page
            slug = "demo" if preset == "roofing" else "demo-" + preset
            if not self.store.tenant(slug):
                self.store.create_tenant("Demo " + preset.capitalize(), slug, preset, "full", demo=True)

    # ---- signed session cookies
    def sign(self, scope):
        expiry = str(int(time.time()) + SESSION_DAYS * 86400)
        return expiry + "." + hmac.new(self.secret, (scope + "|" + expiry).encode(), hashlib.sha256).hexdigest()

    def signed(self, scope, token):
        expiry, _, sig = (token or "").partition(".")
        if not expiry.isdigit() or int(expiry) < time.time():
            return False
        return hmac.compare_digest(sig, hmac.new(self.secret, (scope + "|" + expiry).encode(), hashlib.sha256).hexdigest())

    @staticmethod
    def tenant_scope(tenant):                          # tied to the password, so a reset signs everyone out
        return "t%d:%s" % (tenant["id"], tenant["pw_hash"].hex()[:16])

    def allow(self, what, who, limit, window):
        """True if this is within `limit` tries per `window` seconds."""
        with self.lock:
            cutoff = time.time() - window
            recent = [t for t in self.hits.get((what, who), []) if t > cutoff]
            ok = len(recent) < limit
            if ok:
                recent.append(time.time())
            self.hits[(what, who)] = recent
            if len(self.hits) > 5000:
                self.hits = {k: v for k, v in self.hits.items() if v and v[-1] > cutoff}
            return ok

    # ---- after a lead is saved: tell the tradie
    def deliver_lead(self, tenant, lead, base_url):
        url = "%s/q/%s/admin/lead/%d" % (base_url, tenant["slug"], lead["id"])
        email = forward = None
        if tenant["notify_email"]:
            if not self.smtp:
                email = "not sent: email is not set up"
            else:
                try:
                    subject, body = deliver.lead_email(tenant, lead, url)
                    deliver.send_email(self.smtp, tenant["notify_email"], subject, body, reply_to=lead["email"])
                    email = "sent"
                except Exception as exc:
                    email = "failed: %s" % str(exc)[:120]
        if tenant["forward_webhook"]:
            try:
                deliver.forward(tenant["forward_webhook"], {
                    k: lead[k] for k in ("id", "name", "phone", "email", "suburb", "job_type", "difficulty", "size", "low", "high", "photos")
                } | {"business": tenant["name"], "link": url, "created_at": lead["created_at"]}, self.allow_private_forward)
                forward = "sent"
            except Exception as exc:
                forward = "failed: %s" % str(exc)[:120]
        self.store.update_lead(tenant["id"], lead["id"], email_status=email, forward_status=forward)


class Handler(BaseHTTPRequestHandler):
    app = None
    server_version = "QuoteMate/" + VERSION
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        if self.app.env.get("QM_LOG"):
            sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    # ---------------------------------------------------------------- replies
    def send(self, status, body, ctype="text/html; charset=utf-8", headers=None, cache="no-store"):
        body = body if isinstance(body, (bytes, bytearray)) else str(body).encode()
        self.send_response(status)
        for k, v in {"Content-Type": ctype, "Content-Length": str(len(body)), "Cache-Control": cache,
                     "X-Content-Type-Options": "nosniff", "Referrer-Policy": "same-origin", "Content-Security-Policy": CSP,
                     **(headers or {})}.items():
            if isinstance(v, list):
                for item in v:
                    self.send_header(k, item)
            else:
                self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def redirect(self, to, headers=None):
        self.send(303, b"", headers={"Location": to, **(headers or {})})

    def json(self, status, data):
        self.send(status, json.dumps(data), "application/json; charset=utf-8")

    def cookie(self, name, value, path, age):
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
        return "%s=%s; Path=%s; Max-Age=%d; HttpOnly; SameSite=Strict%s" % (name, value, path, age, secure)

    # ---------------------------------------------------------------- requests
    def cookies(self):
        out = {}
        for part in (self.headers.get("Cookie") or "").split(";"):
            k, _, v = part.strip().partition("=")
            out[k] = v
        return out

    def visitor(self):
        if self.app.trust_proxy and self.headers.get("X-Forwarded-For"):
            return self.headers["X-Forwarded-For"].split(",")[-1].strip()
        return self.client_address[0]

    def base_url(self):
        if self.app.env.get("PUBLIC_URL"):
            return self.app.env["PUBLIC_URL"].rstrip("/")
        scheme = "https" if self.headers.get("X-Forwarded-Proto") == "https" else "http"
        return "%s://%s" % (scheme, self.headers.get("Host", "localhost"))

    def same_origin(self):
        """Every form post must come from our own pages. Stops another site posting on a signed-in person's behalf."""
        origin = self.headers.get("Origin")
        if origin and urllib.parse.urlsplit(origin).netloc != self.headers.get("Host"):
            raise Halt(403, "That request came from another site.")

    def read(self, limit):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise Halt(400, "Bad request.")
        if length > limit:
            self.close_connection = True
            raise Halt(413, "That is too large.")
        return self.rfile.read(length) if length else b""

    def form(self, limit=MAX_FORM):
        """(fields, files) from a urlencoded or multipart post. files: name -> (filename, bytes)."""
        raw = self.read(limit)
        ctype = self.headers.get("Content-Type", "")
        fields, files = {}, {}
        if ctype.startswith("multipart/form-data"):
            msg = BytesParser(policy=email_policy).parsebytes(b"Content-Type: " + ctype.encode("latin-1") + b"\r\n\r\n" + raw)
            if not msg.is_multipart():
                raise Halt(400, "Bad form.")
            for part in msg.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if not name:
                    continue
                data = part.get_payload(decode=True) or b""
                if part.get_filename() is not None:
                    if data:
                        files[name] = (part.get_filename(), data)
                else:
                    fields[name] = data.decode("utf-8", "replace")
        else:
            fields = {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode("utf-8", "replace"), keep_blank_values=True).items()}
        return fields, files

    # ---------------------------------------------------------------- dispatch
    def do_GET(self):
        path = self.path.split("?", 1)[0]
        try:
            self.route(path)
        except Halt as h:
            if h.status in (301, 303):
                return self.send(h.status, b"", headers=h.headers)
            wants_json = path.endswith("/lead")
            body = json.dumps({"error": str(h)}) if wants_json else pages.layout("Sorry", "<h1>Sorry</h1><p class=\"lead\">%s</p>" % pages.e(str(h) or "That didn't work."))
            self.send(h.status, body, "application/json; charset=utf-8" if wants_json else "text/html; charset=utf-8", h.headers)
        except BrokenPipeError:
            pass
        except Exception as exc:
            sys.stderr.write("error on %s %s: %r\n" % (self.command, path, exc))
            self.send(500, pages.layout("Sorry", "<h1>Something went wrong</h1><p class=\"lead\">Nothing was lost. Please try again.</p>"))

    do_POST = do_HEAD = do_GET

    def query(self):
        return {k: v[0] for k, v in urllib.parse.parse_qs(self.path.partition("?")[2]).items()}

    def route(self, path):
        m, store = self.command, self.app.store
        if m == "POST":
            self.same_origin()

        if path == "/" and m in ("GET", "HEAD"):
            return self.send(200, pages.sales(store.site(), sent=self.query().get("sent") == "1", demos=store.demos()))
        if path == "/enquire" and m == "POST":
            return self.enquire()
        if path == "/static/site.css" and m in ("GET", "HEAD"):
            with open(os.path.join(ROOT, "static", "site.css"), "rb") as fh:
                return self.send(200, fh.read(), "text/css; charset=utf-8", cache="no-cache")
        if path == "/healthz":
            return self.json(200, {"ok": True, "version": VERSION})
        if path == "/admin" or path.startswith("/admin/"):
            return self.owner(path)

        match = re.match(r"^/q/([a-z0-9-]{3,40})(/.*)?$", path)
        if match:
            tenant = store.tenant(match.group(1))
            if not tenant:
                raise Halt(404, "That page doesn't exist.")
            rest = match.group(2)
            if rest is None:
                raise Halt(301, headers={"Location": "/q/%s/" % tenant["slug"]})
            if rest == "/admin" or rest.startswith("/admin/"):
                return self.inbox(tenant, rest[len("/admin"):])
            return self.tool(tenant, rest)
        raise Halt(404, "That page doesn't exist.")

    # ---------------------------------------------------------------- the public quote tool
    def tool(self, tenant, rest):
        m, slug = self.command, tenant["slug"]
        if rest == "/lead" and m == "POST":
            return self.lead(tenant)
        if m not in ("GET", "HEAD"):
            raise Halt(405, "Not allowed.")
        if rest == "/":
            if not tenant["active"]:
                return self.send(200, pages.paused(tenant))
            with open(os.path.join(self.app.tool_dir, "index.html"), "rb") as fh:
                return self.send(200, fh.read(), cache="no-cache")
        if rest == "/config.js":
            cfg = self.app.store.public_config(tenant, "/q/%s/lead" % slug)
            body = "window.RQM_CONFIG = %s;\n" % json.dumps(cfg, ensure_ascii=False).replace("</", "<\\/")
            return self.send(200, body, "text/javascript; charset=utf-8", cache="no-cache")
        if rest == "/full.js" and tenant["tier"] != "full":      # the plan is enforced here, not by a word in a file
            return self.send(200, "/* lite plan */\n", "text/javascript; charset=utf-8", cache="no-cache")
        if rest[1:] in TOOL_FILES:
            with open(os.path.join(self.app.tool_dir, rest[1:]), "rb") as fh:
                return self.send(200, fh.read(), TOOL_FILES[rest[1:]], cache="no-cache")
        if rest == "/logo":
            if tenant["logo"]:
                return self.send(200, bytes(tenant["logo"]), tenant["logo_type"], cache="no-cache")
            raise Halt(404, "No logo.")
        raise Halt(404, "That page doesn't exist.")

    def lead(self, tenant):
        app = self.app
        if not tenant["active"]:
            raise Halt(403, "Online quotes are switched off for this business.")
        if not app.allow("lead", (tenant["id"], self.visitor()), 8, 3600):
            raise Halt(429, "Too many requests from this connection. Please call us instead.")
        fields, files = self.form(MAX_LEAD)
        clean = lambda k, n: " ".join(fields.get(k, "").split())[:n]
        name, phone, email, suburb = clean("name", 80), clean("phone", 30), clean("email", 120), clean("suburb", 60)
        digits = re.sub(r"\D", "", phone)
        if len(name) < 2 or len(suburb) < 2 or not 8 <= len(digits) <= 12 or re.search(r"[^\d\s()+\-.]", phone) or not EMAIL.match(email):
            raise Halt(400, "Some details are missing or don't look right.")
        try:
            est = estimate(tenant["config"], fields.get("type_id"), fields.get("difficulty_id"), fields.get("size_id"))
        except (ValueError, KeyError):
            raise Halt(400, "That choice isn't one of the options.")
        if fields.get("company") or tenant["demo"]:               # a bot, or the public demo: accept and drop
            return self.json(200, {"ok": True})

        photos = []
        if tenant["tier"] == "full":
            for key in sorted(k for k in files if re.match(r"^photo\d$", k))[: int(tenant["config"]["photos"]["max"])]:
                data = files[key][1]
                kind = image_kind(data)
                if kind and len(data) <= MAX_PHOTO:
                    photos.append((data, kind[0]))
        lead = {"name": name, "phone": phone, "email": email, "suburb": suburb, "job_type": est["type"]["label"],
                "difficulty": est["difficulty"]["label"], "size": est["size"]["label"], "low": est["low"], "high": est["high"]}
        lead_id = app.store.add_lead(tenant["id"], lead, photos)
        saved = app.store.lead(tenant["id"], lead_id)
        threading.Thread(target=app.deliver_lead, args=(tenant, saved, self.base_url()), daemon=True).start()
        self.json(200, {"ok": True})

    def enquire(self):
        app, site = self.app, self.app.store.site()
        fields, _ = self.form()
        clean = lambda k, n: " ".join(fields.get(k, "").split())[:n]
        e = {"name": clean("name", 80), "business": clean("business", 80), "trade": clean("trade", 60), "phone": clean("phone", 30),
             "email": clean("email", 120), "message": clean("message", 800)}
        if fields.get("website"):                                 # hidden box only a bot fills in
            return self.redirect("/?sent=1#start")
        if len(e["name"]) < 2 or len(e["business"]) < 2 or len(e["trade"]) < 2 or len(re.sub(r"\D", "", e["phone"])) < 8 or not EMAIL.match(e["email"]):
            return self.send(400, pages.sales(site, error="Please fill in your name, business, trade, a phone number and an email.", form=e,
                                              demos=app.store.demos()))
        if not app.allow("enquiry", self.visitor(), 5, 3600):
            raise Halt(429, "Too many requests from this connection. Please call instead.")
        app.store.add_enquiry(e)
        if app.smtp and site["owner_email"]:
            body = "\n".join("%s: %s" % (k.capitalize(), v) for k, v in e.items())
            threading.Thread(target=lambda: _quietly(deliver.send_email, app.smtp, site["owner_email"],
                                                     "New enquiry: %s (%s)" % (e["business"], e["trade"]), body, e["email"]), daemon=True).start()
        self.redirect("/?sent=1#start")

    # ---------------------------------------------------------------- a business's inbox
    def inbox(self, tenant, rest):
        app, store, m, slug = self.app, self.app.store, self.command, tenant["slug"]
        base, cookie_name, scope = "/q/%s/admin" % slug, "qm_t%d" % tenant["id"], app.tenant_scope(tenant)

        if rest == "/login" and m == "POST":
            if not app.allow("login", ("t", tenant["id"], self.visitor()), 6, 300):
                raise Halt(429, "Too many wrong passwords. Wait five minutes and try again.")
            fields, _ = self.form()
            if not store.check_password(tenant, fields.get("password", "")):
                return self.send(401, pages.login("Sign in to %s" % tenant["name"], base + "/login", "Wrong password."))
            return self.redirect(base, {"Set-Cookie": self.cookie(cookie_name, app.sign(scope), base, SESSION_DAYS * 86400)})
        if not app.signed(scope, self.cookies().get(cookie_name)):
            if m == "POST":
                raise Halt(401, "Sign in first.")
            return self.send(200 if rest == "" else 401, pages.login("Sign in to %s" % tenant["name"], base + "/login"))
        if rest == "/logout" and m == "POST":
            return self.redirect(base, {"Set-Cookie": self.cookie(cookie_name, "gone", base, 0)})

        if rest == "" and m in ("GET", "HEAD"):
            status = self.query().get("status", "")
            status = status if status in LEAD_STATES else ""
            notes = []
            if not tenant["rates_confirmed"]:
                notes.append("Your quote page is still showing example rates. Put your own in under Settings.")
            if not tenant["active"]:
                notes.append("Your quote page is paused.")
            return self.send(200, pages.leads_list(tenant, store.leads(tenant["id"], status), store.lead_counts(tenant["id"]), status,
                                                   "%s/q/%s/" % (self.base_url(), slug), notes))
        if rest == "/leads.csv" and m == "GET":
            out = io.StringIO()
            w = csv.writer(out)
            w.writerow(["Received", "Name", "Phone", "Email", "Suburb", "Job", "Difficulty", "Size", "Ballpark low", "Ballpark high", "Photos", "Status", "Notes"])
            safe = lambda v: "'" + v if isinstance(v, str) and v[:1] in "=+-@\t\r" else v     # spreadsheets run cells that start like formulas
            for l in store.leads(tenant["id"]):
                w.writerow([safe(x) for x in (time.strftime("%Y-%m-%d %H:%M", time.localtime(l["created_at"])), l["name"], l["phone"], l["email"],
                                              l["suburb"], l["job_type"], l["difficulty"], l["size"], l["low"], l["high"], l["photos"], l["status"], l["notes"])])
            return self.send(200, out.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8",
                             {"Content-Disposition": 'attachment; filename="%s-leads.csv"' % slug})
        match = re.match(r"^/lead/(\d+)$", rest)
        if match:
            lead = store.lead(tenant["id"], int(match.group(1)))       # looked up by business AND id: never another's lead
            if not lead:
                raise Halt(404, "That lead doesn't exist.")
            if m == "POST":
                fields, _ = self.form()
                try:
                    lead = store.update_lead(tenant["id"], lead["id"], status=fields.get("status") or None, notes=fields.get("notes", ""))
                except ValueError as exc:
                    raise Halt(400, str(exc))
                return self.send(200, pages.lead_detail(tenant, lead, saved=True))
            return self.send(200, pages.lead_detail(tenant, lead))
        match = re.match(r"^/photo/(\d+)/(\d)$", rest)
        if match and m in ("GET", "HEAD"):
            if not store.lead(tenant["id"], int(match.group(1))):
                raise Halt(404, "No such photo.")
            photo = store.photo(tenant["id"], int(match.group(1)), int(match.group(2)))
            if not photo:
                raise Halt(404, "No such photo.")
            return self.send(200, photo[0], photo[1], {"Content-Disposition": "inline"}, cache="private, max-age=3600")
        if rest == "/settings":
            if m == "POST":
                return self.save_settings(tenant)
            return self.send(200, pages.tenant_settings(tenant, message="Saved." if self.query().get("saved") else "", mail_on=bool(app.smtp)))
        raise Halt(404, "That page doesn't exist.")

    def save_settings(self, tenant):
        app, store = self.app, self.app.store
        fields, files = self.form(MAX_LOGO + MAX_FORM)
        cfg = json.loads(json.dumps(tenant["config"]))

        def number(key, label):
            try:
                v = float(fields.get(key, "").strip())
            except ValueError:
                raise ValueError("%s must be a number" % label)
            if v != v or v in (float("inf"), float("-inf")) or v < 0:
                raise ValueError("%s must be zero or more" % label)
            return int(v) if v == int(v) else v
        text = lambda key, old, n=60: " ".join(fields.get(key, old).split())[:n] or old
        try:
            for j in cfg["jobTypes"]:
                j["label"] = text("jt_%s_label" % j["id"], j["label"])
                j["labourPerUnit"] = number("jt_%s_labour" % j["id"], j["label"] + " labour")
                j["materialPerUnit"] = number("jt_%s_material" % j["id"], j["label"] + " materials")
            for d in cfg["difficulty"]:
                d["label"] = text("df_%s_label" % d["id"], d["label"])
                d["multiplier"] = number("df_%s_mult" % d["id"], d["label"] + " multiplier")
            for s in cfg["sizes"]:
                s["label"] = text("sz_%s_label" % s["id"], s["label"])
                s["min"], s["max"] = number("sz_%s_min" % s["id"], s["label"] + " from"), number("sz_%s_max" % s["id"], s["label"] + " to")
            p = cfg["pricing"]
            p["gstRegistered"] = fields.get("gst_registered") == "1"
            p["ratesIncludeGst"] = fields.get("gst_included") == "1"
            if p.get("rebate"):
                p["rebate"]["perUnit"] = number("rebate_per_unit", "The rebate amount")
            p["spread"] = number("spread_pct", "The range spread") / 100
            p["roundTo"], p["minimumJob"] = number("round_to", "Rounding"), number("minimum_job", "The smallest job")
            for key, n in (("headline", 90), ("subline", 140), ("ballparkNote", 200), ("thanksSub", 140)):
                cfg["words"][key] = text("w_" + key, cfg["words"][key], n)
            if fields.get("forward_webhook", "").strip():
                deliver.safe_public_url(fields["forward_webhook"].strip(), app.allow_private_forward)
            logo = files.get("logo")
            if logo:
                kind = image_kind(logo[1])
                if not kind or len(logo[1]) > MAX_LOGO:
                    raise ValueError("The logo must be a PNG or JPG under 400 KB")
            store.save_config(tenant["id"], cfg)                       # runs the full config check
            store.update_tenant(tenant["id"], name=fields.get("name", tenant["name"]), phone=fields.get("phone", ""),
                                licence=fields.get("licence", ""), notify_email=fields.get("notify_email", "").strip(),
                                forward_webhook=fields.get("forward_webhook", "").strip(),
                                rates_confirmed=fields.get("rates_confirmed") == "1")
            if logo and tenant["tier"] == "full":
                store.set_logo(tenant["id"], logo[1], kind[1])
            elif fields.get("remove_logo") == "1":
                store.set_logo(tenant["id"], None, "")
        except ValueError as exc:
            return self.send(400, pages.tenant_settings(tenant, error=str(exc), mail_on=bool(app.smtp)))
        self.redirect("/q/%s/admin/settings?saved=1" % tenant["slug"])

    # ---------------------------------------------------------------- the owner's console
    def owner(self, path):
        app, store, m = self.app, self.app.store, self.command
        if not app.admin_password:
            raise Halt(503, "The owner console is off. Start the server with ADMIN_PASSWORD set.")
        if path == "/admin/login" and m == "POST":
            if not app.allow("login", ("admin", self.visitor()), 6, 300):
                raise Halt(429, "Too many wrong passwords. Wait five minutes and try again.")
            fields, _ = self.form()
            if not hmac.compare_digest(fields.get("password", "").encode(), app.admin_password.encode()):
                return self.send(401, pages.login("Owner sign in", "/admin/login", "Wrong password."))
            return self.redirect("/admin", {"Set-Cookie": self.cookie("qm_admin", app.sign("admin"), "/admin", SESSION_DAYS * 86400)})
        if not app.signed("admin", self.cookies().get("qm_admin")):
            if m == "POST":
                raise Halt(401, "Sign in first.")
            return self.send(200 if path == "/admin" else 401, pages.login("Owner sign in", "/admin/login"))

        def home(status=200, **kw):
            self.send(status, pages.admin_home(store.site(), store.tenants(), store.enquiries(), store.presets(),
                                               mail_on=bool(app.smtp), public_url=self.base_url(), **kw))
        if path == "/admin" and m in ("GET", "HEAD"):
            return home()
        if m != "POST":
            raise Halt(404, "That page doesn't exist.")
        if path == "/admin/logout":
            return self.redirect("/admin", {"Set-Cookie": self.cookie("qm_admin", "gone", "/admin", 0)})
        fields, _ = self.form()
        try:
            if path == "/admin/business":
                tenant, password = store.create_tenant(fields.get("name", ""), fields.get("slug", ""), fields.get("preset", "roofing"),
                                                       fields.get("tier", "lite"), fields.get("contact_email", ""), fields.get("phone", ""))
                return home(message="Created %s." % tenant["name"], issued={"name": tenant["name"], "slug": tenant["slug"], "password": password})
            match = re.match(r"^/admin/business/(\d+)$", path)
            if match:
                tenant = store.tenant(tenant_id=int(match.group(1)))
                if not tenant:
                    raise Halt(404, "No such business.")
                if fields.get("reset_password"):
                    return home(message="New password made for %s." % tenant["name"],
                                issued={"name": tenant["name"], "slug": tenant["slug"], "password": store.reset_password(tenant["id"])})
                store.update_tenant(tenant["id"], tier=fields.get("tier", tenant["tier"]), paid_until=fields.get("paid_until", ""),
                                    active=fields.get("active", "1") == "1")
                return home(message="Saved %s." % tenant["name"])
            match = re.match(r"^/admin/enquiry/(\d+)$", path)
            if match:
                store.handle_enquiry(int(match.group(1)), fields.get("handled") == "1")
                return home()
            if path == "/admin/site":
                store.save_site(fields)
                return home(message="Sales page details saved.")
        except ValueError as exc:
            return home(400, error=str(exc))
        raise Halt(404, "That page doesn't exist.")


def _quietly(fn, *args):
    try:
        fn(*args)
    except Exception as exc:
        sys.stderr.write("background task failed: %r\n" % (exc,))


def make_server(env):
    host, port = env.get("HOST", "127.0.0.1"), int(env.get("PORT") or 8090)
    handler = type("BoundHandler", (Handler,), {"app": App(env)})
    server = ThreadingHTTPServer((host, port), handler)
    server.daemon_threads = True
    return server


def main():
    server = make_server(dict(os.environ))
    app = server.RequestHandlerClass.app
    print("Quote Mate (hosted) %s on http://%s:%d/" % (VERSION, server.server_address[0], server.server_address[1]))
    print("  owner console: %s" % ("/admin" if app.admin_password else "OFF - set ADMIN_PASSWORD to use it"))
    print("  lead emails:   %s" % ("on, via " + app.smtp["host"] if app.smtp else "off - set SMTP_HOST and SMTP_FROM to turn on"))
    print("  demo:          /q/demo/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
