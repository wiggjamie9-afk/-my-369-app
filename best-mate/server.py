#!/usr/bin/env python3
"""The 48 - AI's Best Mate: quoting app server.

Standard library only. Serves the mobile web app from web/ and a JSON API under /api/.

    python3 server.py                 run on 127.0.0.1:8048
    APP_PASSWORD=... python3 server.py   require sign-in (always set this behind a public address)

Configuration comes from environment variables, or config.json (see config.example.json).
No key or password is stored in this repository.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from bestmate import config, drafting, money, pdf, voice   # noqa: E402
from bestmate.db import Store                               # noqa: E402

VERSION = "1.0.0"
WEB = os.path.join(ROOT, "web")
STATIC = {
    "/app.css": "text/css; charset=utf-8", "/app.js": "text/javascript; charset=utf-8",
    "/jarvis.js": "text/javascript; charset=utf-8", "/sw.js": "text/javascript; charset=utf-8",
    "/manifest.webmanifest": "application/manifest+json", "/logo-mark.jpg": "image/jpeg",
    "/THE-48-logo.jpg": "image/jpeg", "/icons/icon-180.png": "image/png",
    "/icons/icon-192.png": "image/png", "/icons/icon-512.png": "image/png",
}
APP_ROUTES = re.compile(r"^/(?:|new|voice|parts|settings|jarvis|more|quote/\d+)$")
SESSION_DAYS = 30
MAX_JSON, MAX_CSV, MAX_AUDIO = 256 * 1024, 8 * 1024 * 1024, 15 * 1024 * 1024
CSP = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; "
       "media-src 'self' blob:; connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")


class HttpError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status


class App:
    """Everything the handlers share."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.store = Store(cfg["db"])
        self.started = time.time()
        self.fails = []                               # times of recent failed sign-ins
        self.lock = threading.Lock()
        try:
            with open(os.path.join(WEB, "logo-mark.jpg"), "rb") as fh:
                self.logo = fh.read()
        except OSError:
            self.logo = None
        secret = cfg["session_secret"]
        if not secret:                                # generated once on this machine, never in the repo
            path = os.path.join(os.path.dirname(os.path.abspath(cfg["db"])), ".session-secret")
            try:
                with open(path) as fh:
                    secret = fh.read().strip()
            except OSError:
                secret = secrets.token_hex(32)
                fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                with os.fdopen(fd, "w") as fh:
                    fh.write(secret)
        self.secret = secret.encode()

    # ---- sessions
    def token(self):
        expiry = str(int(time.time()) + SESSION_DAYS * 86400)
        return expiry + "." + hmac.new(self.secret, expiry.encode(), hashlib.sha256).hexdigest()

    def valid(self, token):
        expiry, _, sig = (token or "").partition(".")
        if not expiry.isdigit() or int(expiry) < time.time():
            return False
        return hmac.compare_digest(sig, hmac.new(self.secret, expiry.encode(), hashlib.sha256).hexdigest())

    def sign_in(self, password):
        with self.lock:
            cutoff = time.time() - 300
            self.fails = [t for t in self.fails if t > cutoff]
            if len(self.fails) >= 5:
                raise HttpError(429, "Too many wrong passwords. Wait five minutes and try again.")
            if not hmac.compare_digest(str(password).encode(), self.cfg["app_password"].encode()):
                self.fails.append(time.time())
                raise HttpError(401, "Wrong password.")
            self.fails = []
        return self.token()

    # ---- the modes shown in the health strip
    def modes(self):
        return {"voice": "live" if self.cfg["voice_base_url"] else "stub",
                "ai": "model" if self.cfg["llm_base_url"] else "built-in reader",
                "auth": bool(self.cfg["app_password"])}


def dollars(v, name):
    try:
        return money.to_cents(v)
    except ValueError:
        raise ValueError("%s must be a dollar amount" % name)


class Handler(BaseHTTPRequestHandler):
    app = None
    server_version = "BestMate/" + VERSION
    protocol_version = "HTTP/1.1"

    # ---------------------------------------------------------------- plumbing
    def log_message(self, fmt, *args):
        if os.environ.get("BESTMATE_LOG"):
            sys.stderr.write("%s %s\n" % (time.strftime("%H:%M:%S"), fmt % args))

    def send(self, status, body, ctype="application/json; charset=utf-8", extra=None):
        if not isinstance(body, (bytes, bytearray)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", CSP)
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def body(self, limit):
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            raise HttpError(400, "Bad request.")
        if length > limit:
            self.close_connection = True
            raise HttpError(413, "That is too large.")
        return self.rfile.read(length) if length else b""

    def json(self):
        raw = self.body(MAX_JSON)
        try:
            data = json.loads(raw or b"{}")
        except ValueError:
            raise HttpError(400, "That was not valid JSON.")
        if not isinstance(data, dict):
            raise HttpError(400, "Send a JSON object.")
        return data

    def signed_in(self):
        if not self.app.cfg["app_password"]:
            return True
        for part in (self.headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == "bm" and self.app.valid(value):
                return True
        return False

    def cookie(self, value, age):
        secure = "; Secure" if self.headers.get("X-Forwarded-Proto") == "https" else ""
        return {"Set-Cookie": "bm=%s; Path=/; Max-Age=%d; HttpOnly; SameSite=Strict%s" % (value, age, secure)}

    # ---------------------------------------------------------------- dispatch
    def do_GET(self):
        self.handle_any()

    do_HEAD = do_POST = do_PUT = do_DELETE = do_GET

    def handle_any(self):
        path = self.path.split("?", 1)[0]
        try:
            if not path.startswith("/api/"):
                return self.static(path)
            if self.command == "HEAD":
                raise HttpError(405, "Not allowed.")
            self.api(path)
        except HttpError as exc:
            self.send(exc.status, {"error": str(exc)})
        except LookupError as exc:
            self.send(404, {"error": str(exc) or "Not found."})
        except PermissionError as exc:
            self.send(409, {"error": str(exc)})
        except ValueError as exc:
            self.send(400, {"error": str(exc)})
        except BrokenPipeError:
            pass
        except Exception as exc:                       # never leak a traceback to the phone
            sys.stderr.write("error on %s %s: %r\n" % (self.command, path, exc))
            self.send(500, {"error": "Something went wrong on the server."})

    def static(self, path):
        if self.command not in ("GET", "HEAD"):
            raise HttpError(405, "Not allowed.")
        if path in STATIC:
            name, ctype = path.lstrip("/"), STATIC[path]
        elif APP_ROUTES.match(path):
            name, ctype = "index.html", "text/html; charset=utf-8"
        else:
            raise HttpError(404, "Not found.")
        with open(os.path.join(WEB, name), "rb") as fh:
            extra = {"Service-Worker-Allowed": "/"} if name == "sw.js" else None
            self.send(200, fh.read(), ctype, extra)

    def query(self):
        from urllib.parse import parse_qs
        return {k: v[0] for k, v in parse_qs(self.path.partition("?")[2]).items()}

    def api(self, path):
        app, store, m = self.app, self.app.store, self.command

        # ---- open endpoints
        if path == "/api/health" and m == "GET":
            return self.send(200, {"ok": True, "version": VERSION})
        if path == "/api/session" and m == "GET":
            return self.send(200, {"auth_required": bool(app.cfg["app_password"]), "signed_in": self.signed_in()})
        if path == "/api/login" and m == "POST":
            if not app.cfg["app_password"]:
                return self.send(200, {"ok": True})
            return self.send(200, {"ok": True}, extra=self.cookie(app.sign_in(self.json().get("password", "")), SESSION_DAYS * 86400))
        if path == "/api/logout" and m == "POST":
            return self.send(200, {"ok": True}, extra=self.cookie("gone", 0))
        if not self.signed_in():
            raise HttpError(401, "Sign in first.")

        # ---- settings and vendors
        if path == "/api/settings":
            if m == "GET":
                return self.send(200, {"settings": store.settings(), "vendors": store.vendors(), "modes": app.modes()})
            if m == "PUT":
                d = self.json()
                changes = {}
                for k, v in d.items():
                    if k in ("labour_cost_rate", "labour_sell_rate"):
                        changes[k + "_cents"] = dollars(v, k.replace("_", " "))
                    elif k == "markup_percent":
                        changes["markup_bp"] = money.to_bp(v)
                    elif k == "preferred_brands" and isinstance(v, str):
                        changes[k] = [x for x in (p.strip() for p in v.split(",")) if x]
                    else:
                        changes[k] = v
                return self.send(200, {"settings": store.save_settings(changes), "vendors": store.vendors(), "modes": app.modes()})
        if path == "/api/vendors" and m == "PUT":
            d = self.json()
            return self.send(200, {"vendors": store.save_vendor(d.get("name", ""), money.to_bp(d.get("discount_percent", 0)))})

        # ---- parts library
        if path == "/api/parts":
            if m == "GET":
                q = self.query()
                out = store.search_parts(q.get("q", ""), q.get("category", ""), q.get("brand", ""),
                                         q.get("limit", 50), q.get("offset", 0))
                settings = store.settings()
                for p in out["items"]:
                    p["unit_cost_cents"], p["unit_sell_cents"] = store.price_part(p, settings)
                out["facets"] = store.parts_facets()
                return self.send(200, out)
            if m == "POST":
                d = self.json()
                kw = d.get("kw")
                sku = store.save_part({"sku": d.get("sku", ""), "name": d.get("name", ""), "category": d.get("category", ""),
                                       "brand": d.get("brand", ""), "vendor": d.get("vendor", ""), "unit": d.get("unit", ""),
                                       "cost_cents": dollars(d.get("cost", ""), "cost"),
                                       "kw_milli": money.to_milli(kw) if kw not in (None, "") else None}, status="manual")
                return self.send(200, {"sku": sku})
        if path == "/api/parts/import" and m == "POST":
            raw = self.body(MAX_CSV)
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError("save the price list as UTF-8 CSV")
            return self.send(200, {"imported": store.import_parts_csv(text), "facets": store.parts_facets()})

        # ---- drafting from words (the AI contract)
        if path == "/api/ai/draft-quote" and m == "POST":
            d = self.json()
            draft = drafting.draft(store, d.get("job_description", ""), app.cfg)
            if d.get("create"):
                draft["quote_id"] = store.create_quote(
                    {"customer_name": draft["customer_name"], "site_address": draft["site_address"],
                     "job_title": draft["job_title"], "scope": draft["scope"], "notes": draft["notes"],
                     "job_description": d.get("job_description", ""), "spec": draft["spec"], "flags": draft["flags"],
                     "labour_hours_milli": draft["labour_hours_milli"]},
                    draft["line_items"], source="voice" if d.get("via") == "voice" else "ai")
            return self.send(200, draft)

        # ---- voice (the voice contract)
        if path == "/api/voice/speak" and m == "POST":
            try:
                audio, mode = voice.speak(self.json().get("text", ""), app.cfg)
            except OSError as exc:
                raise HttpError(502, "The voice server did not answer (%s)." % str(exc)[:80])
            return self.send(200, audio, "audio/wav", {"X-Voice-Mode": mode})
        if path == "/api/voice/listen" and m == "POST":
            try:
                return self.send(200, voice.listen(self.body(MAX_AUDIO), self.headers.get("Content-Type"), app.cfg))
            except OSError as exc:
                raise HttpError(502, "The voice server did not answer (%s)." % str(exc)[:80])

        # ---- the Jarvis panel's data
        if path == "/api/jarvis/summary" and m == "GET":
            facets = store.parts_facets()
            return self.send(200, {"pipeline": store.pipeline(), "health": {
                "version": VERSION, "uptime_s": int(time.time() - app.started), "database": "ok",
                "parts": facets["count"], "placeholder_prices": facets["placeholder"], **app.modes()}})

        # ---- quotes
        if path == "/api/quotes":
            if m == "GET":
                return self.send(200, {"quotes": store.list_quotes(self.query().get("state", ""))})
            if m == "POST":
                d = self.json()
                header = {k: d.get(k, "") for k in ("customer_name", "customer_phone", "customer_email", "site_address")}
                if d.get("spec"):
                    spec = drafting.clean_spec(d["spec"], store.parts_facets()["brands"])
                    lines, labour, title, scope = drafting.build_lines(store, spec)
                    header.update(job_title=title, scope=scope, spec=spec, labour_hours_milli=labour)
                    qid = store.create_quote(header, lines, source="form")
                else:
                    qid = store.create_quote(header, [], source="manual")
                return self.send(200, {"quote": store.quote(qid)})

        match = re.match(r"^/api/quotes/(\d+)(?:/(pdf|send|state|lines|flags)(?:/(\d+))?)?$", path)
        if match:
            qid, action, lid = int(match.group(1)), match.group(2), match.group(3)
            if not action:
                if m == "GET":
                    q = store.quote(qid)
                    if not q:
                        raise LookupError("No such quote.")
                    return self.send(200, {"quote": q})
                if m == "PUT":
                    d, changes = self.json(), {}
                    for k, v in d.items():
                        if k == "labour_hours":
                            changes["labour_hours_milli"] = money.to_milli(v)
                        elif k == "adjust":
                            changes["adjust_cents"] = dollars(v, "adjustment")
                        elif k in ("labour_cost_rate", "labour_sell_rate"):
                            changes[k + "_cents"] = dollars(v, k.replace("_", " "))
                        else:
                            changes[k] = v
                    return self.send(200, {"quote": store.update_quote(qid, changes)})
                if m == "DELETE":
                    store.delete_quote(qid)
                    return self.send(200, {"ok": True})
            if action == "pdf" and m == "GET":
                q = store.quote(qid)
                if not q:
                    raise LookupError("No such quote.")
                data = pdf.quote_pdf(q, store.settings(), app.logo)
                name = "%s%s.pdf" % (q["number"], "-DRAFT" if q["state"] == "draft" else "")
                return self.send(200, data, "application/pdf", {"Content-Disposition": 'attachment; filename="%s"' % name})
            if action == "send" and m == "POST":
                d = self.json()
                return self.send(200, {"quote": store.send(qid, d.get("reviewed"), d.get("prices_checked"))})
            if action == "state" and m == "POST":
                return self.send(200, {"quote": store.set_state(qid, self.json().get("state"))})
            if action == "flags" and m == "DELETE":
                return self.send(200, {"quote": store.clear_flags(qid)})
            if action == "lines":
                if m == "POST" and not lid:
                    return self.send(200, {"quote": store.add_line(qid, self.line_from(self.json()))})
                if m == "PUT" and lid:
                    return self.send(200, {"quote": store.update_line(qid, int(lid), self.line_changes(qid, int(lid), self.json()))})
                if m == "DELETE" and lid:
                    return self.send(200, {"quote": store.delete_line(qid, int(lid))})
        raise HttpError(404, "Not found.")

    # ---------------------------------------------------------------- line helpers
    def qty(self, v):
        q = money.to_milli(v)
        if not 0 < q <= 100_000_000:
            raise ValueError("quantity must be more than zero")
        return q

    def line_from(self, d):
        """A new line: from the library (sku), or one a person typed with their own cost and price."""
        store = self.app.store
        qty = self.qty(d.get("qty", 1))
        if d.get("sku"):
            part = store.part(str(d["sku"]))
            if not part:
                raise LookupError("That part is not in the library.")
            return drafting.library_line(store, part, qty)
        desc = " ".join(str(d.get("description", "")).split())
        if not desc:
            raise ValueError("describe the item")
        return {"sku": None, "description": desc, "unit": str(d.get("unit") or "ea")[:12], "qty_milli": qty,
                "unit_cost_cents": dollars(d.get("unit_cost", ""), "cost"),
                "unit_sell_cents": dollars(d.get("unit_sell", ""), "price"), "price_status": "manual"}

    def line_changes(self, qid, lid, d):
        store = self.app.store
        q = store.quote(qid)
        line = next((ln for ln in (q or {}).get("lines", []) if ln["id"] == lid), None)
        if not line:
            raise LookupError("No such line.")
        changes = {}
        if "qty" in d:
            changes["qty_milli"] = self.qty(d["qty"])
        if d.get("sku"):                                # swap in a library part (this is how a flag is cleared)
            part = store.part(str(d["sku"]))
            if not part:
                raise LookupError("That part is not in the library.")
            new = drafting.library_line(store, part, changes.get("qty_milli", line["qty_milli"]))
            changes.update({k: new[k] for k in ("sku", "description", "unit", "unit_cost_cents", "unit_sell_cents", "price_status")},
                           flagged=0, flag_reason="")
        elif "unit_sell" in d or "unit_cost" in d:      # a person sets the price: their call, recorded as manual
            sell = dollars(d["unit_sell"], "price") if "unit_sell" in d else line["unit_sell_cents"]
            cost = dollars(d["unit_cost"], "cost") if "unit_cost" in d else line["unit_cost_cents"]
            if sell is None or cost is None:
                raise ValueError("give both your cost and your price for this item")
            changes.update(unit_sell_cents=sell, unit_cost_cents=cost, price_status="manual", flagged=0, flag_reason="")
        if "description" in d:
            desc = " ".join(str(d["description"]).split())
            if not desc:
                raise ValueError("describe the item")
            changes["description"] = desc[:300]
        return changes


def make_server(cfg):
    loopback = cfg["host"] in ("127.0.0.1", "localhost", "::1")
    if not cfg["app_password"] and not loopback:
        raise SystemExit("Refusing to listen on %s without APP_PASSWORD: customer data would be open to the network."
                         % cfg["host"])
    handler = type("BoundHandler", (Handler,), {"app": App(cfg)})
    server = ThreadingHTTPServer((cfg["host"], cfg["port"]), handler)
    server.daemon_threads = True
    return server


def main():
    cfg = config.load(ROOT)
    server = make_server(cfg)
    modes = server.RequestHandlerClass.app.modes()
    print("The 48 - AI's Best Mate %s on http://%s:%d/" % (VERSION, cfg["host"], server.server_address[1]))
    print("  voice: %s | drafting: %s | sign-in: %s" % (modes["voice"], modes["ai"], "on" if modes["auth"] else
          "OFF (fine on this machine only; set APP_PASSWORD before putting it behind a public address)"))
    print("  database: %s" % cfg["db"], flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
