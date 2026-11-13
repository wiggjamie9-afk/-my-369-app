"""End to end through the real HTTP server: the acceptance test, the review gate, sign-in, PDF, parts at scale."""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server
from bestmate import config, money, pdf

ACCEPTANCE = "two and a half kW Daikin split, back-to-back install, Smith job"


class Client:
    def __init__(self, base):
        self.base, self.cookie = base, ""

    def call(self, method, path, body=None, raw=None, ctype="application/json"):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        if data is not None:
            req.add_header("Content-Type", ctype)
        if self.cookie:
            req.add_header("Cookie", self.cookie)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                status, headers, payload = r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            status, headers, payload = e.code, e.headers, e.read()
        if headers.get("Set-Cookie"):
            self.cookie = headers["Set-Cookie"].split(";")[0]
        if headers.get("Content-Type", "").startswith("application/json"):
            payload = json.loads(payload)
        return status, payload, headers


class Base(unittest.TestCase):
    PASSWORD = ""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        saved = {k: os.environ.pop(k, None) for k in ("LLM_BASE_URL", "VOICE_BASE_URL", "APP_PASSWORD", "BESTMATE_DB", "PORT")}
        self.addCleanup(lambda: [os.environ.__setitem__(k, v) for k, v in saved.items() if v is not None])
        os.environ["BESTMATE_CONFIG"] = os.path.join(self.tmp.name, "none.json")
        cfg = config.load(ROOT)
        cfg.update(db=os.path.join(self.tmp.name, "t.db"), port=0, app_password=self.PASSWORD)
        self.server = server.make_server(cfg)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.c = Client("http://127.0.0.1:%d" % self.server.server_address[1])
        self.store = self.server.RequestHandlerClass.app.store

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def ok(self, method, path, body=None, **kw):
        status, payload, _ = self.c.call(method, path, body, **kw)
        self.assertEqual(status, 200, payload)
        return payload

    def draft(self):
        return self.ok("POST", "/api/ai/draft-quote", {"job_description": ACCEPTANCE, "create": True, "via": "voice"})["quote_id"]


class Acceptance(Base):
    def test_dictated_job_becomes_a_draft_then_a_reviewed_pdf_correct_to_the_cent(self):
        heard = self.ok("POST", "/api/voice/listen", raw=b"fake-audio", ctype="audio/mp4")
        self.assertTrue(heard["stub"])                       # no voice server here: the stub says so
        qid = self.ok("POST", "/api/ai/draft-quote", {"job_description": heard["text"], "create": True, "via": "voice"})["quote_id"]

        q = self.ok("GET", "/api/quotes/%d" % qid)["quote"]
        self.assertEqual((q["state"], q["source"], q["customer_name"]), ("draft", "voice", "Smith"))
        self.assertEqual(q["placeholder_lines"], 10)         # every seeded price is flagged "check price"
        t = q["totals"]
        self.assertEqual((t["total_ex_gst_cents"], t["gst_cents"], t["total_inc_gst_cents"]), (192135, 19214, 211349))

        # it cannot leave DRAFT without a person: not unreviewed, not with unchecked placeholder prices
        self.assertEqual(self.c.call("POST", "/api/quotes/%d/send" % qid, {})[0], 409)
        self.assertEqual(self.c.call("POST", "/api/quotes/%d/send" % qid, {"reviewed": "yes"})[0], 409)
        status, body, _ = self.c.call("POST", "/api/quotes/%d/send" % qid, {"reviewed": True})
        self.assertEqual(status, 400)
        self.assertIn("placeholder", body["error"])
        self.assertEqual(self.ok("GET", "/api/quotes/%d" % qid)["quote"]["state"], "draft")

        sent = self.ok("POST", "/api/quotes/%d/send" % qid, {"reviewed": True, "prices_checked": True})["quote"]
        self.assertEqual(sent["state"], "sent")
        self.assertIsNotNone(sent["reviewed_at"])

        status, data, headers = self.c.call("GET", "/api/quotes/%d/pdf" % qid)
        self.assertEqual((status, headers["Content-Type"]), (200, "application/pdf"))
        self.assertIn('filename="%s.pdf"' % sent["number"], headers["Content-Disposition"])
        text = pdf_text(data)
        for expected in ("$1,921.35", "$192.14", "$2,113.49", "Smith", sent["number"], "$1,170.00", "$440.00"):
            self.assertIn(expected, text)
        self.assertNotIn("DRAFT", pdf_drawn(data))

    def test_jarvis_route_and_feed_load(self):
        status, page, headers = self.c.call("GET", "/jarvis")
        self.assertEqual(status, 200)
        self.assertIn(b"app.js", page)
        self.draft()
        feed = self.ok("GET", "/api/jarvis/summary")
        self.assertEqual(feed["pipeline"]["states"]["draft"]["count"], 1)
        self.assertEqual(len(feed["pipeline"]["needs_attention"]), 1)
        self.assertEqual((feed["health"]["voice"], feed["health"]["parts"], feed["health"]["database"]), ("stub", 50, "ok"))

    def test_voice_contract(self):
        status, audio, headers = self.c.call("POST", "/api/voice/speak", {"text": "G'day"})
        self.assertEqual((status, headers["Content-Type"], headers["X-Voice-Mode"]), (200, "audio/wav", "stub"))
        self.assertEqual((audio[:4], audio[8:12]), (b"RIFF", b"WAVE"))
        self.assertEqual(self.c.call("POST", "/api/voice/speak", {"text": "  "})[0], 400)


class ReviewGate(Base):
    def test_a_flagged_line_blocks_sending_until_a_person_prices_it(self):
        qid = self.ok("POST", "/api/ai/draft-quote", {"job_description": "samsung 7.1kw split for the lee job", "create": True})["quote_id"]
        q = self.ok("GET", "/api/quotes/%d" % qid)["quote"]
        flagged = [ln for ln in q["lines"] if ln["flagged"]]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(q["totals"]["unpriced_lines"], 1)
        before = q["totals"]["total_ex_gst_cents"]
        status, body, _ = self.c.call("POST", "/api/quotes/%d/send" % qid, {"reviewed": True, "prices_checked": True})
        self.assertEqual(status, 400)
        self.assertIn("no trusted price", body["error"])

        lid = flagged[0]["id"]
        self.assertEqual(self.c.call("PUT", "/api/quotes/%d/lines/%d" % (qid, lid), {"unit_sell": "2600"})[0], 400)   # cost too
        q = self.ok("PUT", "/api/quotes/%d/lines/%d" % (qid, lid), {"unit_cost": "2000", "unit_sell": "2600.00"})["quote"]
        line = next(ln for ln in q["lines"] if ln["id"] == lid)
        self.assertEqual((line["flagged"], line["price_status"], line["unit_sell_cents"]), (0, "manual", 260000))
        self.assertEqual(q["totals"]["total_ex_gst_cents"], before + 260000)
        self.assertEqual(self.ok("POST", "/api/quotes/%d/send" % qid, {"reviewed": True, "prices_checked": True})["quote"]["state"], "sent")

    def test_drafting_warnings_must_be_read_first(self):
        qid = self.ok("POST", "/api/ai/draft-quote", {"job_description": "3.5kw split at the brown house", "create": True})["quote_id"]
        q = self.ok("GET", "/api/quotes/%d" % qid)["quote"]
        self.assertTrue(q["flags"])                           # no brand was said
        self.assertEqual(self.c.call("POST", "/api/quotes/%d/send" % qid, {"reviewed": True, "prices_checked": True})[0], 400)
        self.ok("DELETE", "/api/quotes/%d/flags" % qid)
        self.assertEqual(self.ok("POST", "/api/quotes/%d/send" % qid, {"reviewed": True, "prices_checked": True})["quote"]["state"], "sent")

    def test_a_sent_quote_is_locked_and_reopening_needs_a_fresh_review(self):
        qid = self.draft()
        self.ok("POST", "/api/quotes/%d/send" % qid, {"reviewed": True, "prices_checked": True})
        self.assertEqual(self.c.call("PUT", "/api/quotes/%d" % qid, {"adjust": "-500"})[0], 409)
        self.assertEqual(self.c.call("POST", "/api/quotes/%d/lines" % qid, {"sku": "DRN-PUMP", "qty": "1"})[0], 409)
        self.assertEqual(self.c.call("DELETE", "/api/quotes/%d" % qid)[0], 409)
        q = self.ok("POST", "/api/quotes/%d/state" % qid, {"state": "draft"})["quote"]
        self.assertEqual((q["state"], q["reviewed_at"], q["sent_at"]), ("draft", None, None))
        self.assertEqual(self.c.call("POST", "/api/quotes/%d/state" % qid, {"state": "won"})[0], 409)   # not while a draft
        self.assertEqual(self.c.call("POST", "/api/quotes/%d/state" % qid, {"state": "sent"})[0], 400)  # only /send sends

    def test_draft_pdf_is_watermarked(self):
        qid = self.draft()
        status, data, headers = self.c.call("GET", "/api/quotes/%d/pdf" % qid)
        self.assertEqual(status, 200)
        self.assertIn("-DRAFT.pdf", headers["Content-Disposition"])
        self.assertIn("DRAFT", pdf_drawn(data))               # the watermark is drawn at an angle


class Editing(Base):
    def test_totals_follow_every_edit_exactly(self):
        qid = self.draft()
        q = self.ok("PUT", "/api/quotes/%d" % qid, {"labour_hours": "5.5", "adjust": "-100"})["quote"]
        # materials 1481.35 + labour 5.5 x 110 = 605.00 - 100.00 = 1986.35 ; GST 198.635 -> 198.64
        self.assertEqual((q["totals"]["total_ex_gst_cents"], q["totals"]["gst_cents"], q["totals"]["total_inc_gst_cents"]),
                         (198635, 19864, 218499))
        q = self.ok("POST", "/api/quotes/%d/lines" % qid, {"sku": "DRN-PUMP", "qty": "1"})["quote"]       # $140 + 30% = $182.00
        self.assertEqual(q["totals"]["total_ex_gst_cents"], 198635 + 18200)
        pipe = next(ln for ln in q["lines"] if ln["sku"] == "PIPE-PAIR-6-10")
        q = self.ok("PUT", "/api/quotes/%d/lines/%d" % (qid, pipe["id"]), {"qty": "4.5"})["quote"]          # +1.5 m x $15.60
        self.assertEqual(q["totals"]["total_ex_gst_cents"], 198635 + 18200 + 2340)
        q = self.ok("DELETE", "/api/quotes/%d/lines/%d" % (qid, pipe["id"]))["quote"]
        self.assertEqual(q["totals"]["total_ex_gst_cents"], 198635 + 18200 - 4680)
        self.assertEqual(self.c.call("PUT", "/api/quotes/%d" % qid, {"adjust": "-99999"})[0], 400)          # cannot go negative

    def test_bad_input_is_refused_cleanly(self):
        qid = self.draft()
        for method, path, body in (("PUT", "/api/quotes/%d" % qid, {"labour_hours": "lots"}),
                                   ("PUT", "/api/quotes/%d" % qid, {"state": "sent"}),
                                   ("POST", "/api/quotes/%d/lines" % qid, {"description": "Thing", "qty": "0", "unit_cost": "1", "unit_sell": "2"}),
                                   ("POST", "/api/quotes/%d/lines" % qid, {"description": "Thing", "qty": "1", "unit_sell": "abc", "unit_cost": "1"}),
                                   ("POST", "/api/quotes", {"spec": {"install_type": "igloo"}})):
            self.assertEqual(self.c.call(method, path, body)[0], 400, (path, body))
        self.assertEqual(self.c.call("POST", "/api/quotes/%d/lines" % qid, {"sku": "NOPE", "qty": "1"})[0], 404)
        self.assertEqual(self.c.call("GET", "/api/quotes/9999")[0], 404)
        self.assertEqual(self.c.call("POST", "/api/quotes", raw=b"{not json")[0], 400)
        self.assertEqual(self.c.call("POST", "/api/quotes", raw=b"x" * (300 * 1024))[0], 413)

    def test_quote_builder_form_and_settings_feed_new_quotes(self):
        self.ok("PUT", "/api/settings", {"markup_percent": "40", "labour_sell_rate": "120", "business_name": "Example Air"})
        self.ok("PUT", "/api/vendors", {"name": "Main supplier", "discount_percent": "10"})
        q = self.ok("POST", "/api/quotes", {"customer_name": "Jo", "spec": {"install_type": "single_split", "brand": "daikin",
                                                                             "units": [{"kw": "2.5"}], "back_to_back": True}})["quote"]
        unit = q["lines"][0]
        # $900 list, less 10% = $810.00 cost, plus 40% = $1,134.00
        self.assertEqual((unit["sku"], unit["unit_cost_cents"], unit["unit_sell_cents"]), ("SPL-DAI-25", 81000, 113400))
        self.assertEqual((q["source"], q["labour_sell_rate_cents"], q["spec"]["brand"]), ("form", 12000, "Daikin"))
        self.assertEqual(self.c.call("PUT", "/api/settings", {"markup_percent": "-5"})[0], 400)
        self.assertEqual(self.c.call("PUT", "/api/settings", {"nonsense": "1"})[0], 400)


class Parts(Base):
    def test_supplier_import_replaces_placeholders_and_is_all_or_nothing(self):
        good = "SKU,Name,Cost,Brand,Category,kW,Vendor,Unit\nSPL-DAI-25,Daikin 2.5kW split,812.50,Daikin,unit-split,2.5,Main supplier,ea\nNEW-1,\"Bracket, heavy\",\"1,050.00\",,mounting,,,ea\n"
        out = self.ok("POST", "/api/parts/import", raw=good.encode(), ctype="text/csv")
        self.assertEqual((out["imported"], out["facets"]["count"], out["facets"]["placeholder"]), (2, 51, 49))
        part = self.store.part("SPL-DAI-25")
        self.assertEqual((part["cost_cents"], part["price_status"]), (81250, "supplier"))
        self.assertEqual(self.store.part("NEW-1")["cost_cents"], 105000)

        bad = "sku,name,cost\nA-1,Fine,10\nA-2,Broken,ten dollars\n"
        status, body, _ = self.c.call("POST", "/api/parts/import", raw=bad.encode(), ctype="text/csv")
        self.assertEqual(status, 400)
        self.assertIn("row 3", body["error"])
        self.assertIsNone(self.store.part("A-1"))            # nothing from a bad file gets in
        self.assertEqual(self.c.call("POST", "/api/parts/import", raw=b"name,price\nx,1\n", ctype="text/csv")[0], 400)

    def test_library_scales_to_fifteen_thousand_parts(self):
        rows = ["sku,name,cost,category,brand"] + ["BULK-%05d,Bulk fitting %05d size %d,%d.%02d,fittings,Generic" % (i, i, i % 40, 5 + i % 300, i % 100)
                                                   for i in range(15000)]
        t0 = time.time()
        self.assertEqual(self.ok("POST", "/api/parts/import", raw="\n".join(rows).encode(), ctype="text/csv")["imported"], 15000)
        loaded = time.time() - t0
        t0 = time.time()
        out = self.ok("GET", "/api/parts?q=fitting+14999&limit=20")
        searched = time.time() - t0
        self.assertEqual((out["total"], out["items"][0]["sku"], out["facets"]["count"]), (1, "BULK-14999", 15050))
        self.assertEqual(self.ok("GET", "/api/parts?category=fittings&limit=50&offset=14990")["items"][-1]["sku"], "BULK-14999")
        self.assertLess(searched, 1.0, "search took %.2fs" % searched)
        self.assertLess(loaded, 30.0)
        qid = self.draft()                                    # drafting is unaffected by library size
        self.assertEqual(self.ok("GET", "/api/quotes/%d" % qid)["quote"]["totals"]["total_inc_gst_cents"], 211349)


class SignIn(Base):
    PASSWORD = "correct horse"

    def test_everything_is_locked_until_signed_in(self):
        for method, path in (("GET", "/api/quotes"), ("GET", "/api/settings"), ("GET", "/api/jarvis/summary"),
                             ("POST", "/api/ai/draft-quote"), ("GET", "/api/quotes/1/pdf"), ("POST", "/api/voice/speak")):
            self.assertEqual(self.c.call(method, path, {} if method == "POST" else None)[0], 401, path)
        self.assertEqual(self.c.call("GET", "/api/health")[0], 200)
        self.assertEqual(self.ok("GET", "/api/session"), {"auth_required": True, "signed_in": False})
        self.assertEqual(self.c.call("POST", "/api/login", {"password": "wrong"})[0], 401)
        status, _, headers = self.c.call("POST", "/api/login", {"password": self.PASSWORD})
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        self.assertEqual(self.c.call("GET", "/api/quotes")[0], 200)
        self.c.cookie = "bm=" + "9" * 12 + ".forged"
        self.assertEqual(self.c.call("GET", "/api/quotes")[0], 401)

    def test_repeated_wrong_passwords_are_slowed_down(self):
        for _ in range(5):
            self.assertEqual(self.c.call("POST", "/api/login", {"password": "guess"})[0], 401)
        self.assertEqual(self.c.call("POST", "/api/login", {"password": self.PASSWORD})[0], 429)

    def test_refuses_to_listen_on_the_network_without_a_password(self):
        cfg = config.load(ROOT)
        cfg.update(db=os.path.join(self.tmp.name, "x.db"), port=0, host="0.0.0.0", app_password="")
        with self.assertRaises(SystemExit):
            server.make_server(cfg)


class Hygiene(Base):
    def test_only_the_app_is_served(self):
        for path in ("/server.py", "/config.json", "/data/bestmate.db", "/../server.py", "/bestmate/money.py", "/tests/test_api.py", "/.git/config"):
            self.assertEqual(self.c.call("GET", path)[0], 404, path)
        status, _, headers = self.c.call("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        for path in ("/app.js", "/app.css", "/sw.js", "/manifest.webmanifest", "/icons/icon-192.png", "/new", "/voice", "/quote/3"):
            self.assertEqual(self.c.call("GET", path)[0], 200, path)

    def test_no_keys_or_secrets_in_the_repo(self):
        with open(os.path.join(ROOT, "config.example.json")) as fh:
            example = json.load(fh)
        for key in ("app_password", "session_secret", "llm_key", "voice_key", "llm_base_url", "voice_base_url"):
            self.assertEqual(example[key], "", key)
        secretish = re.compile(r"(sk-[A-Za-z0-9]{16,}|Bearer\s+[A-Za-z0-9._-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|"
                               r"(?:password|secret|api_?key|token)\s*[=:]\s*[\"'][^\"'\s]{8,}[\"'])", re.I)
        hits = []
        for folder, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in ("data", "__pycache__", "screenshots", ".git", "tests")]
            for name in files:
                if name.endswith((".py", ".js", ".json", ".sh", ".md", ".html", ".css", ".webmanifest")):
                    with open(os.path.join(folder, name), encoding="utf-8") as fh:
                        for n, line in enumerate(fh, 1):
                            if secretish.search(line):
                                hits.append("%s:%d" % (name, n))
        self.assertEqual(hits, [])
        self.assertFalse(os.path.exists(os.path.join(ROOT, "config.json")), "config.json must not be committed")


def pdf_drawn(data):
    """Every string the PDF draws, read straight from its content streams."""
    text = b""
    for m in re.finditer(rb"/FlateDecode >>\nstream\n(.*?)\nendstream", data, re.S):
        text += b" ".join(re.findall(rb"\((.*?)\) Tj", zlib.decompress(m.group(1)))) + b" "
    return text.decode("latin-1").replace("\\(", "(").replace("\\)", ")")


def pdf_text(data):
    """The text of a PDF: via pdftotext when it is installed, else from its content streams."""
    if shutil.which("pdftotext"):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as fh:
            fh.write(data)
            fh.flush()
            return subprocess.run(["pdftotext", "-layout", fh.name, "-"], capture_output=True, text=True, check=True).stdout
    return pdf_drawn(data)


class PdfFile(unittest.TestCase):
    def test_structure_is_sound_and_long_quotes_paginate(self):
        lines = [{"description": "Line %d with a fairly long description that has to wrap onto a second row" % i, "unit": "ea",
                  "qty_milli": 1000 + i, "unit_cost_cents": 1000, "unit_sell_cents": 1300 + i, "flagged": 0, "price_status": "supplier"}
                 for i in range(70)]
        lines.append({"description": "SECRET-UNPRICED", "unit": "ea", "qty_milli": 1000, "unit_cost_cents": None,
                      "unit_sell_cents": None, "flagged": 1, "price_status": "none"})
        q = {"number": "Q-2026-0042", "state": "sent", "customer_name": "Zoë O'Brien (Pty) \\ Ltd", "customer_phone": "", "customer_email": "",
             "site_address": "1 Long Street, Perth", "job_title": "Big job", "scope": "Scope " * 80, "notes": "Thanks — see you then.",
             "spec": {"units": [{"kw_milli": 2500}], "brand": "Daikin", "cycle": "reverse_cycle"}, "lines": lines,
             "labour_hours_milli": 8000, "labour_sell_rate_cents": 11000, "valid_days": 30, "sent_at": 1794500000, "updated_at": 1794500000,
             "totals": money.quote_totals(lines, 8000, 6000, 11000, 0)}
        data = pdf.quote_pdf(q, {"business_name": "Example Air", "payment_terms": "Pay on completion."}, None)
        self.assertTrue(data.startswith(b"%PDF-1.4"))
        self.assertTrue(data.rstrip().endswith(b"%%EOF"))
        xref = int(re.search(rb"startxref\n(\d+)", data).group(1))
        self.assertEqual(data[xref:xref + 4], b"xref")
        offsets = [int(x) for x in re.findall(rb"(\d{10}) 00000 n", data)]
        for n, off in enumerate(offsets, start=1):
            self.assertTrue(data[off:].startswith(b"%d 0 obj" % n), "object %d offset" % n)
        pages = int(re.search(rb"/Type /Pages /Count (\d+)", data).group(1))
        self.assertGreaterEqual(pages, 3)
        text = pdf_text(data)
        self.assertIn("Page %d of %d" % (pages, pages), text)
        self.assertIn(money.fmt_money(q["totals"]["total_inc_gst_cents"]), text)
        self.assertNotIn("SECRET-UNPRICED", text)            # an unpriced line never reaches the customer
        self.assertIn("O'Brien (Pty)", text)

    def test_text_measurement(self):
        self.assertAlmostEqual(pdf.text_width("$1,234.56", 10), 44.48, places=2)     # 7 glyphs x 556 + comma and point x 278, at 10pt
        self.assertEqual(pdf.wrap("one two three", 10, 30), ["one", "two", "three"])
        with open(os.path.join(ROOT, "web", "logo-mark.jpg"), "rb") as fh:
            self.assertEqual(pdf.jpeg_size(fh.read()), (400, 400, 3))


if __name__ == "__main__":
    unittest.main()
