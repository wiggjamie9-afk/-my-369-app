"""End to end through the real server. Run: python3 -m unittest discover -s tests -v   (standard library only)"""
import csv
import io
import json
import os
import re
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
import server
from qm import deliver
from qm.estimate import check_config, estimate

JPEG = b"\xff\xd8\xff\xe0" + b"photo-bytes" * 40
PNG = b"\x89PNG\r\n\x1a\n" + b"logo-bytes" * 20
GOOD = {"name": "Sam Sample", "phone": "0400 000 000", "email": "sam@example.com", "suburb": "Fremantle",
        "type_id": "colorbond", "difficulty_id": "double", "size_id": "medium"}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


class Client:
    """A tiny browser: keeps cookies per path, sends forms, never follows redirects on its own."""

    def __init__(self, base):
        self.base, self.jar = base, {}
        self.opener = urllib.request.build_opener(NoRedirect)

    def call(self, method, path, form=None, files=None, headers=None, raw=None):
        data, hdrs = None, dict(headers or {})
        if raw is not None:
            data, hdrs["Content-Type"] = raw, "application/json"
        elif files is not None:
            boundary = "----test%d" % time.time_ns()
            parts = []
            for k, v in (form or {}).items():
                parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' % (boundary, k, v)).encode())
            for k, (fname, blob) in files.items():
                parts.append(('--%s\r\nContent-Disposition: form-data; name="%s"; filename="%s"\r\nContent-Type: application/octet-stream\r\n\r\n'
                              % (boundary, k, fname)).encode() + blob + b"\r\n")
            data = b"".join(parts) + ("--%s--\r\n" % boundary).encode()
            hdrs["Content-Type"] = "multipart/form-data; boundary=" + boundary
        elif form is not None:
            data = urllib.parse.urlencode(form).encode()
            hdrs["Content-Type"] = "application/x-www-form-urlencoded"
        cookies = "; ".join("%s=%s" % (n, v) for (n, p), v in self.jar.items() if path.startswith(p))
        if cookies:
            hdrs["Cookie"] = cookies
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=hdrs)
        try:
            with self.opener.open(req, timeout=10) as r:
                status, h, body = r.status, r.headers, r.read()
        except urllib.error.HTTPError as e:
            status, h, body = e.code, e.headers, e.read()
        for raw in h.get_all("Set-Cookie") or []:
            name, _, value = raw.split(";")[0].partition("=")
            self.jar[(name, re.search(r"Path=([^;]+)", raw).group(1))] = value
        return status, body, h

    def text(self, method, path, **kw):
        status, body, h = self.call(method, path, **kw)
        return status, body.decode("utf-8", "replace")


class Base(unittest.TestCase):
    ENV = {}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        env = {"QM_DB": os.path.join(self.tmp.name, "data", "t.db"), "PORT": "0", "ADMIN_PASSWORD": "owner-pass", **self.ENV}
        self.server = server.make_server(env)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.app = self.server.RequestHandlerClass.app
        self.store = self.app.store
        self.base = "http://127.0.0.1:%d" % self.server.server_address[1]
        self.c = Client(self.base)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.tmp.cleanup()

    def business(self, name="Acme Roofing", tier="lite", **kw):
        tenant, password = self.store.create_tenant(name, tier=tier, **kw)
        return tenant, password

    def signed_in(self, tenant, password):
        c = Client(self.base)
        status, _, h = c.call("POST", "/q/%s/admin/login" % tenant["slug"], form={"password": password})
        self.assertEqual(status, 303)
        return c

    def lead(self, slug, client=None, files=None, **changes):
        return (client or self.c).call("POST", "/q/%s/lead" % slug, form={**GOOD, **changes}, files=files or {})

    def wait_for(self, fn, seconds=5):
        end = time.time() + seconds
        while time.time() < end:
            out = fn()
            if out:
                return out
            time.sleep(0.05)
        self.fail("timed out waiting")


class QuotePage(Base):
    def test_each_business_gets_its_own_page_and_its_own_rates(self):
        a, _ = self.business("Acme Roofing")
        b, _ = self.business("Brush Brothers", preset="painting", tier="full")
        self.assertEqual(self.c.call("GET", "/q/acme-roofing")[0], 301)
        status, page = self.c.text("GET", "/q/acme-roofing/")
        self.assertEqual(status, 200)
        self.assertIn('src="config.js"', page)

        def config(slug):
            js = self.c.text("GET", "/q/%s/config.js" % slug)[1]
            return json.loads(js[js.index("{"):js.rindex("}") + 1])
        ca, cb = config("acme-roofing"), config("brush-brothers")
        self.assertEqual((ca["business"]["name"], ca["tier"], ca["webhookUrl"], ca["trade"]["unit"]), ("Acme Roofing", "lite", "/q/acme-roofing/lead", "m²"))
        self.assertEqual((cb["business"]["name"], cb["tier"], cb["webhookUrl"], cb["trade"]["unit"]), ("Brush Brothers", "full", "/q/brush-brothers/lead", "room"))
        self.assertFalse(ca["ratesConfirmed"])                    # new businesses start on example rates, and say so
        self.assertNotIn("pw_hash", json.dumps(ca))
        self.assertNotIn("notify", json.dumps(ca))

    def test_the_plan_is_enforced_by_the_server(self):
        self.business("Acme Roofing", tier="lite")
        self.business("Top Roofs", tier="full")
        lite = self.c.text("GET", "/q/acme-roofing/full.js")[1]
        full = self.c.text("GET", "/q/top-roofs/full.js")[1]
        self.assertNotIn("photos", lite)
        self.assertIn("RQM.full", full)
        # a lite business posting photos anyway gets none stored
        self.assertEqual(self.lead("acme-roofing", files={"photo1": ("a.jpg", JPEG)})[0], 200)
        self.assertEqual(self.store.leads(self.store.tenant("acme-roofing")["id"])[0]["photos"], 0)

    def test_demo_is_there_and_keeps_nothing(self):
        status, js = self.c.text("GET", "/q/demo/config.js")
        self.assertEqual(status, 200)
        self.assertIn("demoNotice", js)
        self.assertIn('"webhookUrl": ""', js)
        self.assertEqual(self.lead("demo")[0], 200)
        self.assertEqual(self.store.leads(self.store.tenant("demo")["id"]), [])

    def test_paused_business_shows_a_holding_page_and_takes_no_leads(self):
        t, _ = self.business("Acme Roofing", phone="08 0000 0000")
        self.store.update_tenant(t["id"], active=False)
        status, page = self.c.text("GET", "/q/acme-roofing/")
        self.assertIn("switched off right now", page)
        self.assertIn("tel:0800000000", page)
        self.assertEqual(self.lead("acme-roofing")[0], 403)
        self.assertEqual(self.c.call("GET", "/q/nobody-here/")[0], 404)

    def test_quote_tool_files_are_served_and_nothing_else(self):
        self.business("Acme Roofing")
        for name in ("app.js", "app.css", "estimate.js"):
            self.assertEqual(self.c.call("GET", "/q/acme-roofing/" + name)[0], 200, name)
        for path in ("/q/acme-roofing/test.js", "/q/acme-roofing/../server.py", "/server.py", "/data/t.db", "/q/acme-roofing/logo", "/qm/store.py"):
            self.assertEqual(self.c.call("GET", path)[0], 404, path)
        headers = self.c.call("GET", "/q/acme-roofing/")[2]
        self.assertIn("script-src 'self'", headers["Content-Security-Policy"])


class Leads(Base):
    def test_a_lead_is_priced_by_the_server_not_the_browser(self):
        t, _ = self.business("Acme Roofing")
        status, body, _ = self.lead("acme-roofing", ballpark_low="1", ballpark_high="2", job_type="Free roof")
        self.assertEqual((status, json.loads(body)), (200, {"ok": True}))
        lead = self.store.leads(t["id"])[0]
        self.assertEqual((lead["low"], lead["high"], lead["job_type"], lead["difficulty"], lead["size"]),
                         (17800, 36300, "Colorbond", "Double storey", "Medium"))
        self.assertEqual((lead["name"], lead["status"]), ("Sam Sample", "new"))

    def test_bad_leads_are_refused(self):
        t, _ = self.business("Acme Roofing")
        for change in ({"name": "S"}, {"phone": "12"}, {"phone": "0400 000 000 ext <b>"}, {"email": "nope"}, {"suburb": ""},
                       {"type_id": "gold"}, {"size_id": ""}, {"difficulty_id": "../x"}):
            status, body, _ = self.lead("acme-roofing", **change)
            self.assertEqual(status, 400, change)
            self.assertIn("error", json.loads(body))
        self.assertEqual(self.store.leads(t["id"]), [])

    def test_bots_and_floods_are_stopped(self):
        t, _ = self.business("Acme Roofing")
        self.assertEqual(self.lead("acme-roofing", company="Spam Ltd")[0], 200)       # the hidden box was filled in
        self.assertEqual(self.store.leads(t["id"]), [])
        statuses = [self.lead("acme-roofing")[0] for _ in range(9)]
        self.assertEqual(statuses.count(200), 7)                                       # 8 an hour per connection, one used above
        self.assertEqual(statuses[-2:], [429, 429])
        self.assertEqual(self.c.call("POST", "/q/acme-roofing/lead", form=GOOD, headers={"Origin": "https://evil.example"})[0], 403)

    def test_full_plan_photos_are_checked_and_stored(self):
        t, _ = self.business("Top Roofs", tier="full")
        files = {"photo1": ("roof.jpg", JPEG), "photo2": ("evil.jpg", b"<script>alert(1)</script>"), "photo3": ("b.png", PNG),
                 "photo4": ("c.jpg", JPEG), "photo5": ("d.jpg", JPEG), "photo6": ("e.svg", b"<svg onload=alert(1)>")}
        self.assertEqual(self.lead("top-roofs", files=files)[0], 200)
        lead = self.store.leads(t["id"])[0]
        self.assertEqual(lead["photos"], 3)                        # first four fields considered; the fake one dropped
        self.assertEqual(self.store.photo(t["id"], lead["id"], 1), (JPEG, "image/jpeg"))
        self.assertEqual(self.store.photo(t["id"], lead["id"], 2), (PNG, "image/png"))
        folder = os.path.join(self.store.photo_dir, str(t["id"]), str(lead["id"]))
        self.assertEqual(sorted(os.listdir(folder)), ["1.jpg", "2.png", "3.jpg"])       # our names, never the uploader's


class Inbox(Base):
    def test_sign_in_and_work_a_lead(self):
        t, pw = self.business("Top Roofs", tier="full")
        self.lead("top-roofs", files={"photo1": ("roof.jpg", JPEG)})
        self.assertIn("Sign in to Top Roofs", self.c.text("GET", "/q/top-roofs/admin")[1])
        self.assertEqual(self.c.call("POST", "/q/top-roofs/admin/login", form={"password": "wrong"})[0], 401)
        self.assertEqual(self.c.call("GET", "/q/top-roofs/admin/leads.csv")[0], 401)

        c = self.signed_in(t, pw)
        status, page = c.text("GET", "/q/top-roofs/admin")
        self.assertEqual(status, 200)
        for expected in ("Sam Sample", "$17,800 – $36,300", "Colorbond", "1 photo", self.base + "/q/top-roofs/", "example rates"):
            self.assertIn(expected, page)
        lead_id = self.store.leads(t["id"])[0]["id"]
        status, page = c.text("GET", "/q/top-roofs/admin/lead/%d" % lead_id)
        self.assertIn("tel:0400000000", page)
        self.assertIn("/q/top-roofs/admin/photo/%d/1" % lead_id, page)
        status, body, h = c.call("GET", "/q/top-roofs/admin/photo/%d/1" % lead_id)
        self.assertEqual((status, body, h["Content-Type"]), (200, JPEG, "image/jpeg"))

        status, page = c.text("POST", "/q/top-roofs/admin/lead/%d" % lead_id, form={"status": "quoted", "notes": "Rang, quoting Friday <b>"})
        self.assertIn("Saved.", page)
        self.assertIn("quoting Friday &lt;b&gt;", page)            # notes are escaped, never run
        self.assertEqual(self.store.lead(t["id"], lead_id)["status"], "quoted")
        self.assertEqual(c.call("POST", "/q/top-roofs/admin/lead/%d" % lead_id, form={"status": "stolen"})[0], 400)
        self.assertIn("No new leads", c.text("GET", "/q/top-roofs/admin?status=new")[1])

    def test_one_business_can_never_see_anothers_leads(self):
        a, pa = self.business("Acme Roofing", tier="full")
        b, pb = self.business("Brush Brothers", preset="painting", tier="full")
        self.lead("acme-roofing", files={"photo1": ("roof.jpg", JPEG)})
        secret = self.store.leads(a["id"])[0]["id"]
        cb = self.signed_in(b, pb)
        self.assertNotIn("Sam Sample", cb.text("GET", "/q/brush-brothers/admin")[1])
        self.assertEqual(cb.call("GET", "/q/brush-brothers/admin/lead/%d" % secret)[0], 404)
        self.assertEqual(cb.call("GET", "/q/brush-brothers/admin/photo/%d/1" % secret)[0], 404)
        self.assertEqual(cb.call("POST", "/q/brush-brothers/admin/lead/%d" % secret, form={"status": "lost"})[0], 404)
        # B's cookie is no use on A's pages, even moved there by hand
        self.assertEqual(cb.call("GET", "/q/acme-roofing/admin/lead/%d" % secret)[0], 401)
        stolen = Client(self.base)
        (name, path), value = next(iter(cb.jar.items()))
        stolen.jar[("qm_t%d" % a["id"], "/q/acme-roofing/admin")] = value
        self.assertEqual(stolen.call("GET", "/q/acme-roofing/admin/lead/%d" % secret)[0], 401)
        self.assertEqual(self.store.lead(a["id"], secret)["status"], "new")

    def test_spreadsheet_export_is_complete_and_defused(self):
        t, pw = self.business("Acme Roofing")
        self.lead("acme-roofing")
        self.lead("acme-roofing", name="=HYPERLINK(evil)", suburb="@home")
        c = self.signed_in(t, pw)
        status, body, h = c.call("GET", "/q/acme-roofing/admin/leads.csv")
        self.assertEqual(status, 200)
        rows = list(csv.reader(io.StringIO(body.decode("utf-8-sig"))))
        self.assertEqual(rows[0][:5], ["Received", "Name", "Phone", "Email", "Suburb"])
        self.assertEqual(len(rows), 3)
        risky = next(r for r in rows if "HYPERLINK" in r[1])
        self.assertEqual((risky[1], risky[4]), ("'=HYPERLINK(evil)", "'@home"))
        self.assertEqual(rows[2][8:10], ["17800", "36300"])

    def test_wrong_passwords_are_slowed_and_a_reset_signs_everyone_out(self):
        t, pw = self.business("Acme Roofing")
        c = self.signed_in(t, pw)
        self.assertEqual(c.call("GET", "/q/acme-roofing/admin/settings")[0], 200)
        new = self.store.reset_password(t["id"])
        self.assertEqual(c.call("GET", "/q/acme-roofing/admin/settings")[0], 401)       # the old session died with the old password
        guess = Client(self.base)
        codes = [guess.call("POST", "/q/acme-roofing/admin/login", form={"password": "guess%d" % i})[0] for i in range(7)]
        self.assertEqual(codes, [401] * 5 + [429] * 2)                 # six tries per five minutes; the sign-in above was the first
        self.assertNotEqual(new, pw)


class Settings(Base):
    def form_for(self, tenant, **changes):
        c = tenant["config"]
        f = {"name": tenant["name"], "phone": "08 0000 0000", "licence": "EX1", "spread_pct": "10", "round_to": "100", "minimum_job": "3000",
             "gst_registered": "1",
             "w_headline": c["words"]["headline"], "w_subline": c["words"]["subline"], "w_ballparkNote": c["words"]["ballparkNote"],
             "w_thanksSub": c["words"]["thanksSub"], "notify_email": "", "forward_webhook": ""}
        for j in c["jobTypes"]:
            f.update({"jt_%s_label" % j["id"]: j["label"], "jt_%s_labour" % j["id"]: j["labourPerUnit"], "jt_%s_material" % j["id"]: j["materialPerUnit"]})
        for d in c["difficulty"]:
            f.update({"df_%s_label" % d["id"]: d["label"], "df_%s_mult" % d["id"]: d["multiplier"]})
        for s in c["sizes"]:
            f.update({"sz_%s_label" % s["id"]: s["label"], "sz_%s_min" % s["id"]: s["min"], "sz_%s_max" % s["id"]: s["max"]})
        f.update(changes)
        return f

    def test_a_tradie_sets_their_own_rates_and_the_ballpark_follows(self):
        t, pw = self.business("Acme Roofing")
        c = self.signed_in(t, pw)
        self.assertIn("Labour $ per m²", c.text("GET", "/q/acme-roofing/admin/settings")[1])
        form = self.form_for(t, jt_colorbond_labour="80", jt_colorbond_material="70.50", rates_confirmed="1", name="Acme Roofing WA",
                             w_headline="Need a new roof?", notify_email="boss@example.com")
        self.assertEqual(c.call("POST", "/q/acme-roofing/admin/settings", form=form, files={})[0], 303)
        t = self.store.tenant("acme-roofing")
        self.assertEqual((t["name"], t["phone"], t["rates_confirmed"], t["notify_email"]), ("Acme Roofing WA", "08 0000 0000", 1, "boss@example.com"))
        js = self.c.text("GET", "/q/acme-roofing/config.js")[1]
        self.assertIn('"ratesConfirmed": true', js)
        self.assertIn("Need a new roof?", js)
        # $150.50/m2 x 1.25 = $188.125: low 120 x 188.125 x 0.9 x 1.1 = 22,349.25 -> 22,300 ; high 200 x 188.125 x 1.1 x 1.1 = 45,526.25 -> 45,600
        self.lead("acme-roofing")
        lead = self.store.leads(t["id"])[0]
        self.assertEqual((lead["low"], lead["high"]), (22300, 45600))

    def test_gst_status_and_the_rebate_are_the_tradies_to_set(self):
        t, pw = self.business("Paws Mobile Grooming", preset="pets")
        c = self.signed_in(t, pw)
        page = c.text("GET", "/q/paws-mobile-grooming/admin/settings")[1]
        self.assertIn("with no GST", page)
        self.assertNotIn("rebate_per_unit", page)                       # no rebate for groomers
        self.assertNotIn(" checked> I&#x27;m registered for GST", page)
        self.lead("paws-mobile-grooming", type_id="full", difficulty_id="medium", size_id="one")
        before = self.store.leads(t["id"])[0]
        # full groom $85 + $10 = $95, x1.25 for a medium dog: 106.88 to 130.63 with the 10% spread -> $105 to $135, no GST added
        self.assertEqual((before["low"], before["high"]), (105, 135))
        # they register for GST: the sum adds it and the wording changes
        form = self.form_for(t, gst_registered="1", round_to="5", minimum_job="50")
        self.assertEqual(c.call("POST", "/q/paws-mobile-grooming/admin/settings", form=form, files={})[0], 303)
        self.lead("paws-mobile-grooming", type_id="full", difficulty_id="medium", size_id="one")
        after = self.store.leads(t["id"])[0]
        self.assertEqual((after["low"], after["high"]), (115, 145))          # the same sums with 10% GST added: 117.56 -> 115, 143.69 -> 145        
        self.assertIn("including GST", self.c.text("GET", "/q/paws-mobile-grooming/config.js")[1] + c.text("GET", "/q/paws-mobile-grooming/admin/lead/%d" % after["id"])[1])

    def test_bad_settings_change_nothing(self):
        t, pw = self.business("Acme Roofing")
        c = self.signed_in(t, pw)
        before = self.store.tenant("acme-roofing")["config"]
        for change, expect in (({"jt_tile_labour": "lots"}, "must be a number"), ({"jt_tile_labour": "-5"}, "zero or more"),
                               ({"sz_small_min": "500"}, "smaller than the smallest"), ({"df_single_mult": "0"}, "can&#x27;t be 0"),
                               ({"spread_pct": "150"}, "between 0% and 99%"), ({"round_to": "0"}, "$1 or more"),
                               ({"notify_email": "nope"}, "email address"), ({"forward_webhook": "http://example.com/x"}, "https://"),
                               ({"forward_webhook": "https://127.0.0.1/internal"}, "public internet")):
            status, page = c.text("POST", "/q/acme-roofing/admin/settings", form=self.form_for(t, **change), files={})
            self.assertEqual(status, 400, change)
            self.assertIn(expect, page, change)
        self.assertEqual(self.store.tenant("acme-roofing")["config"], before)

    def test_logo_upload_full_plan_only_and_images_only(self):
        t, pw = self.business("Top Roofs", tier="full")
        c = self.signed_in(t, pw)
        post = lambda blob, **kw: c.call("POST", "/q/top-roofs/admin/settings", form=self.form_for(t, **kw), files={"logo": ("logo.png", blob)} if blob else {})
        self.assertEqual(post(b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'/>")[0], 400)
        self.assertEqual(post(PNG + b"x" * (400 * 1024))[0], 400)
        self.assertEqual(self.c.call("GET", "/q/top-roofs/logo")[0], 404)
        self.assertEqual(post(PNG)[0], 303)
        status, body, h = self.c.call("GET", "/q/top-roofs/logo")
        self.assertEqual((status, body, h["Content-Type"]), (200, PNG, "image/png"))
        self.assertEqual(post(None, remove_logo="1")[0], 303)
        self.assertEqual(self.c.call("GET", "/q/top-roofs/logo")[0], 404)
        lite, pw2 = self.business("Acme Roofing")
        c2 = self.signed_in(lite, pw2)
        self.assertEqual(c2.call("POST", "/q/acme-roofing/admin/settings", form=self.form_for(lite), files={"logo": ("l.png", PNG)})[0], 303)
        self.assertEqual(self.c.call("GET", "/q/acme-roofing/logo")[0], 404)


class Owner(Base):
    def owner(self):
        c = Client(self.base)
        self.assertEqual(c.call("POST", "/admin/login", form={"password": "owner-pass"})[0], 303)
        return c

    def test_console_is_locked(self):
        self.assertIn("Owner sign in", self.c.text("GET", "/admin")[1])
        self.assertEqual(self.c.call("POST", "/admin/business", form={"name": "Sneaky"})[0], 401)
        self.assertEqual(self.c.call("POST", "/admin/login", form={"password": "nope"})[0], 401)
        t, pw = self.business("Acme Roofing")
        tradie = self.signed_in(t, pw)
        self.assertEqual(tradie.call("POST", "/admin/business", form={"name": "Sneaky"})[0], 401)   # a customer is not the owner
        self.assertEqual(self.owner().call("POST", "/admin/business", form={"name": "X"}, headers={"Origin": "https://evil.example"})[0], 403)

    def test_add_a_business_and_hand_over_its_password_once(self):
        o = self.owner()
        status, page = o.text("POST", "/admin/business", form={"name": "Kelly's Painting", "preset": "painting", "tier": "full",
                                                                "contact_email": "kelly@example.com", "phone": "0411 111 111"})
        self.assertEqual(status, 200)
        self.assertIn("/q/kelly-s-painting/admin", page)
        password = re.search(r'Password: <span class="mono">([^<]+)</span>', page).group(1)
        t = self.store.tenant("kelly-s-painting")
        self.assertTrue(self.store.check_password(t, password))
        self.assertNotIn(password, o.text("GET", "/admin")[1])              # shown once, then gone
        with open(self.store.path, "rb") as fh:
            self.assertNotIn(password.encode(), fh.read())                 # and only a hash on disk
        self.signed_in(t, password)
        for bad in ({"name": "K"}, {"name": "Kelly's Painting"}, {"name": "Admin", "slug": "admin"}, {"name": "Good Name", "preset": "plumbing"},
                    {"name": "Good Name", "tier": "platinum"}):
            self.assertEqual(o.call("POST", "/admin/business", form=bad)[0], 400, bad)

    def test_change_plan_record_payment_pause_and_reset(self):
        t, pw = self.business("Acme Roofing")
        o = self.owner()
        status, page = o.text("POST", "/admin/business/%d" % t["id"], form={"tier": "full", "paid_until": "2020-01-31", "active": "1"})
        self.assertIn("payment overdue", page)
        self.assertEqual(self.store.tenant("acme-roofing")["tier"], "full")
        self.assertEqual(self.c.call("GET", "/q/acme-roofing/")[0], 200)     # overdue is a flag for you; nothing switches off by itself
        self.assertIn('"tier": "full"', self.c.text("GET", "/q/acme-roofing/config.js")[1])
        o.call("POST", "/admin/business/%d" % t["id"], form={"tier": "full", "paid_until": "2020-01-31", "active": "0"})
        self.assertIn("switched off", self.c.text("GET", "/q/acme-roofing/")[1])
        self.assertEqual(o.call("POST", "/admin/business/%d" % t["id"], form={"tier": "full", "paid_until": "next week", "active": "1"})[0], 400)
        status, page = o.text("POST", "/admin/business/%d" % t["id"], form={"reset_password": "1"})
        new = re.search(r'Password: <span class="mono">([^<]+)</span>', page).group(1)
        self.assertFalse(self.store.check_password(self.store.tenant("acme-roofing"), pw))
        self.assertTrue(self.store.check_password(self.store.tenant("acme-roofing"), new))

    def test_sales_page_and_enquiries(self):
        status, page = self.c.text("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("Ask for pricing", page)                               # no price is invented for you
        self.assertIn("/q/demo/", page)
        o = self.owner()
        o.call("POST", "/admin/site", form={"service_name": "Quote Mate WA", "price_lite": "$49 a month", "price_full": "$89 a month",
                                            "owner_phone": "08 0000 0000", "tagline": "<script>x</script>"})
        page = self.c.text("GET", "/")[1]
        for expected in ("Quote Mate WA", "$49 a month", "$89 a month", "tel:0800000000", "&lt;script&gt;x&lt;/script&gt;"):
            self.assertIn(expected, page)
        self.assertNotIn("<script>x", page)

        good = {"name": "Kelly", "business": "Kelly's Painting", "trade": "Painting", "phone": "0411 111 111", "email": "kelly@example.com", "message": "Keen"}
        status, page = self.c.text("POST", "/enquire", form={**good, "email": "nope"})
        self.assertEqual(status, 400)
        self.assertIn('value="Kelly&#x27;s Painting"', page)                 # what they typed is kept
        self.assertEqual(self.c.call("POST", "/enquire", form={**good, "website": "http://spam"})[0], 303)
        self.assertEqual(self.store.enquiries(), [])
        self.assertEqual(self.c.call("POST", "/enquire", form=good)[0], 303)
        self.assertIn("We&#x27;ve got your details", self.c.text("GET", "/?sent=1")[1])
        page = o.text("GET", "/admin")[1]
        self.assertIn("Kelly&#x27;s Painting · Painting", page)
        enquiry = self.store.enquiries()[0]
        o.call("POST", "/admin/enquiry/%d" % enquiry["id"], form={"handled": "1"})
        self.assertEqual(self.store.enquiries()[0]["handled"], 1)

    def test_console_is_off_without_an_owner_password(self):
        self.app.admin_password = ""
        self.assertEqual(self.c.call("GET", "/admin")[0], 503)


def luminance(hex_colour):
    channels = [int(hex_colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


class Branding(Base):
    """The 48 AI Crew brand: the name, the logo, the blue, and who gets to see it where."""

    def test_the_accent_is_blue_everywhere_and_stays_readable(self):
        from qm.store import THEME
        with open(os.path.join(ROOT, "static", "site.css"), encoding="utf-8") as fh:
            css = fh.read()
        with open(os.path.join(os.path.dirname(ROOT), "roof-quote-mate", "app.css"), encoding="utf-8") as fh:
            tool = fh.read()
        self.assertIn("--accent: %s; --on-accent: %s;" % (THEME["accent"], THEME["onAccent"]), css)     # the stylesheet and the quote pages agree
        self.assertNotIn("F5A623", css.upper())                                  # none of the old orange is left on the hosted pages
        self.assertEqual(tool.upper().count("F5A623"), 1)                         # the quote tool keeps it only as its default value...
        for slug, tier in (("acme-roofing", "lite"), ("top-roofs", "full")):      # ...and a hosted business overrides it
            self.business(slug.replace("-", " ").title(), tier=tier)
            js = self.c.text("GET", "/q/%s/config.js" % slug)[1]
            cfg = json.loads(js[js.index("{"):js.rindex("}") + 1])
            self.assertEqual(cfg["theme"], THEME)
        # text on a blue button, and blue text on the charcoal page, must both be easy to read (WCAG AA is 4.5)
        self.assertGreaterEqual(contrast(THEME["onAccent"], THEME["accent"]), 4.5)
        self.assertGreaterEqual(contrast(THEME["accent"], "#1B1D21"), 4.5)
        self.assertIn(".badge.late { border-color: var(--red); color: var(--red); }", css)   # overdue is a warning, so it is red, not blue

    def test_the_logo_is_served_and_the_service_has_the_crew_name(self):
        for path, size in (("/static/48-ai-crew-logo.png", 256), ("/static/48-ai-crew-icon.png", 96)):
            status, body, h = self.c.call("GET", path)
            self.assertEqual((status, h["Content-Type"], body[:8]), (200, "image/png", b"\x89PNG\r\n\x1a\n"), path)
        self.assertEqual(self.store.site()["service_name"], "48 AI Crew Quoting")
        sales = self.c.text("GET", "/")[1]
        self.assertIn('class="hero-logo" src="/static/48-ai-crew-logo.png"', sales)
        self.assertIn('rel="icon" type="image/png" href="/static/48-ai-crew-icon.png"', sales)
        self.assertIn("48 AI Crew Quoting | Instant ballpark quotes for tradies", sales)

    def test_every_page_carries_the_brand(self):
        t, pw = self.business("Acme Roofing")
        login = self.c.text("GET", "/admin")[1]
        self.assertIn("The 48 AI Crew</b>", login)                          # sign-in and console pages get the brand bar
        inbox = self.signed_in(t, pw).text("GET", "/q/acme-roofing/admin")[1]
        self.assertIn("Powered by The 48 AI Crew", inbox)                  # a business's own pages say who powers them
        self.assertIn('rel="icon"', inbox)

    def test_lite_pages_carry_the_crew_brand_and_full_pages_the_businesses_own(self):
        self.business("Acme Roofing", tier="lite")
        self.business("Top Roofs", tier="full")

        def config(slug):
            js = self.c.text("GET", "/q/%s/config.js" % slug)[1]
            return json.loads(js[js.index("{"):js.rindex("}") + 1])
        lite, full = config("acme-roofing"), config("top-roofs")
        self.assertEqual(lite["brand"], {"name": "48 AI Crew Quoting", "logoPath": "/static/48-ai-crew-icon.png"})
        self.assertNotIn("brand", full)                                       # a full plan shows only the business's own name and logo
        self.assertEqual(full["business"]["name"], "Top Roofs")
        self.assertEqual(self.c.call("GET", "/q/acme-roofing/logo")[0], 404)  # a lite business has no logo of its own

    def test_a_homeowner_never_sees_instructions_meant_for_the_owner(self):
        self.business("Acme Roofing", tier="lite")
        js = self.c.text("GET", "/q/acme-roofing/config.js")[1]
        cfg = json.loads(js[js.index("{"):js.rindex("}") + 1])
        self.assertFalse(cfg["ratesConfirmed"])
        self.assertIn("still putting in its own rates", cfg["ratesNotice"])
        self.assertEqual(cfg["noticeTitle"], "Heads up")
        for text in (cfg["ratesNotice"], cfg["noticeTitle"]):
            self.assertNotIn("config.js", text)

    def test_a_renamed_service_flows_through_to_the_lite_pages(self):
        self.business("Acme Roofing", tier="lite")
        self.store.save_site({"service_name": "Crew Quotes WA"})
        js = self.c.text("GET", "/q/acme-roofing/config.js")[1]
        self.assertIn('"name": "Crew Quotes WA"', js)

    def test_the_demos_show_the_full_plans_own_logo_feature_with_the_crew_logo(self):
        status, body, h = self.c.call("GET", "/q/demo/logo")
        self.assertEqual((status, h["Content-Type"], body[:4]), (200, "image/png", b"\x89PNG"))
        js = self.c.text("GET", "/q/demo/config.js")[1]
        self.assertIn('"logoPath": "logo"', js)
        self.assertNotIn('"brand"', js)


class Trades(Base):
    """The four trades that ship: roofing, painting, pet grooming and home batteries."""

    def test_every_trade_has_a_public_demo_and_the_sales_page_links_to_them(self):
        page = self.c.text("GET", "/")[1]
        for slug, product in (("demo", "Roofing"), ("demo-painting", "Painting"), ("demo-pets", "Pet grooming"),
                              ("demo-batteries", "Home batteries"), ("demo-homecare", "Home care"),
                              ("demo-bookkeeping", "Bookkeeping (Payday Check)")):
            self.assertIn('href="/q/%s/"' % slug, page)
            self.assertIn(product, page)
            self.assertEqual(self.c.call("GET", "/q/%s/" % slug)[0], 200)
            self.assertIn("demoNotice", self.c.text("GET", "/q/%s/config.js" % slug)[1])
            self.assertEqual(self.lead(slug)[0] if slug == "demo" else 200, 200)

    def test_home_care_is_a_weekly_price_that_takes_no_photos_and_no_health_details(self):
        t, pw = self.business("Kind Hands Home Care", preset="homecare", tier="full")
        self.store.update_tenant(t["id"], notify_email="boss@example.com")
        js = self.c.text("GET", "/q/kind-hands-home-care/config.js")[1]
        cfg = json.loads(js[js.index("{"):js.rindex("}") + 1])
        self.assertEqual((cfg["pricing"]["priceSuffix"], cfg["photos"]["max"], cfg["tier"]), ("per week", 0, "full"))
        self.assertIn("We don't ask for any health information", cfg["words"]["privacyNote"])
        # 4 to 7 hours of personal care on weekends: $68 x 1.4 = $95.20 an hour -> 342.72 to 733.04 -> $340 to $735
        files = {"photo1": ("a.jpg", JPEG)}
        self.assertEqual(self.lead("kind-hands-home-care", type_id="personal", difficulty_id="weekend", size_id="some", files=files)[0], 200)
        lead = self.store.leads(t["id"])[0]
        self.assertEqual((lead["low"], lead["high"], lead["photos"]), (340, 735, 0))        # a photo sent anyway is not kept
        self.assertFalse(os.path.exists(os.path.join(self.store.photo_dir, str(t["id"]))))
        c = self.signed_in(t, pw)
        self.assertIn("per week", c.text("GET", "/q/kind-hands-home-care/admin/lead/%d" % lead["id"])[1])
        from qm import deliver
        self.assertIn("Ballpark: $340 to $735 per week (what they were shown)", deliver.lead_email(self.store.tenant("kind-hands-home-care"), lead, "https://x/y")[1])

    def test_payday_check_lists_what_to_check_for_the_options_picked(self):
        self.business("Ledger & Co Bookkeeping", preset="bookkeeping")
        js = self.c.text("GET", "/q/ledger-co-bookkeeping/config.js")[1]
        cfg = json.loads(js[js.index("{"):js.rindex("}") + 1])
        for item in cfg["jobTypes"]:
            self.assertIn("within 7 business days of payday", item["watch"])                 # the rule is shown whatever they pick
            self.assertIn("not when you send it", item["watch"])
        sheets = next(d for d in cfg["difficulty"] if d["id"] == "sheets")
        self.assertIn("can't send super to each fund", sheets["watch"])
        self.assertIn("not tax or payroll advice", cfg["words"]["ballparkNote"])
        t = self.store.tenant("ledger-co-bookkeeping")
        self.lead("ledger-co-bookkeeping", type_id="setup", difficulty_id="sheets", size_id="small")
        lead = self.store.leads(t["id"])[0]
        self.assertEqual((lead["low"], lead["high"], lead["difficulty"]), (500, 1750, "Spreadsheets or paper"))   # $85 x 1.6 = $136 each, GST added

    def test_pet_grooming_never_mentions_gst(self):
        t, pw = self.business("Paws Mobile Grooming", preset="pets")
        self.store.update_tenant(t["id"], notify_email="boss@example.com")
        js = self.c.text("GET", "/q/paws-mobile-grooming/config.js")[1]
        self.assertIn('"gstRegistered": false', js)
        self.assertEqual(self.lead("paws-mobile-grooming", type_id="wash", difficulty_id="small", size_id="two")[0], 200)
        lead = self.store.leads(t["id"])[0]
        self.assertEqual((lead["low"], lead["high"], lead["job_type"], lead["size"]), (115, 145, "Wash and tidy", "Two dogs"))   # 2 x $65 = $130, +/-10%: $117 to $143
        c = self.signed_in(t, pw)
        detail = c.text("GET", "/q/paws-mobile-grooming/admin/lead/%d" % lead["id"])[1]
        self.assertNotIn("GST", detail)
        from qm import deliver
        subject, body = deliver.lead_email(self.store.tenant("paws-mobile-grooming"), lead, "https://x/y")
        self.assertIn("Ballpark: $115 to $145 (what they were shown)", body)
        self.assertNotIn("GST", body)

    def test_battery_prices_come_after_the_rebate_and_say_so(self):
        t, pw = self.business("Sunny Solar & Batteries", preset="batteries", tier="full")
        cfg = self.store.tenant("sunny-solar-batteries")["config"]
        self.assertEqual(cfg["pricing"]["rebate"]["perUnit"], 250)
        self.lead("sunny-solar-batteries", type_id="add", difficulty_id="single", size_id="medium")
        lead = self.store.leads(t["id"])[0]
        # $200 + $650 = $850 per kWh, GST already in the rate. 10 kWh: 8,500 less 10 x $250 = 6,000 -> low 6,000 after 8% off the top
        # low: 10 x 850 x 0.92 = 7,820 less 2,500 = 5,320 -> 5,300 ; high: 15 x 850 x 1.08 = 13,770 less (14 + 0.6) x 250 = 3,650 -> 10,120 -> 10,200
        self.assertEqual((lead["low"], lead["high"]), (5300, 10200))
        c = self.signed_in(t, pw)
        detail = c.text("GET", "/q/sunny-solar-batteries/admin/lead/%d" % lead["id"])[1]
        self.assertIn("including GST, after the rebate", detail)
        self.assertIn("Rebate $ per kWh", c.text("GET", "/q/sunny-solar-batteries/admin/settings")[1])

    def test_the_battery_rebate_can_be_updated_and_is_checked(self):
        t, pw = self.business("Sunny Solar & Batteries", preset="batteries", tier="full")
        c = self.signed_in(t, pw)
        s = Settings.form_for(self, t, rebate_per_unit="200", spread_pct="8", minimum_job="3000", gst_included="1")
        self.assertEqual(c.call("POST", "/q/sunny-solar-batteries/admin/settings", form=s, files={})[0], 303)
        self.assertEqual(self.store.tenant("sunny-solar-batteries")["config"]["pricing"]["rebate"]["perUnit"], 200)
        self.lead("sunny-solar-batteries", type_id="add", difficulty_id="single", size_id="medium")
        lead = self.store.leads(t["id"])[0]
        self.assertEqual((lead["low"], lead["high"]), (5800, 10900))             # 7,820 - 10 x 200 = 5,820 ; 13,770 - 14.6 x 200 = 10,850
        for bad in ("lots", "-5"):
            status, page = c.text("POST", "/q/sunny-solar-batteries/admin/settings",
                                  form=Settings.form_for(self, t, rebate_per_unit=bad, spread_pct="8", gst_included="1"), files={})
            self.assertEqual(status, 400, bad)
        self.assertEqual(self.store.tenant("sunny-solar-batteries")["config"]["pricing"]["rebate"]["perUnit"], 200)


class Qualifying(Base):
    """Telling hot leads from tyre-kickers, and spotting the same person asking twice."""

    def test_a_hot_lead_stands_out_and_what_they_asked_for_is_kept(self):
        t, pw = self.business("Acme Roofing")
        self.assertEqual(self.lead("acme-roofing", urgency="asap", contact_time="morning")[0], 200)
        self.assertEqual(self.lead("acme-roofing", name="Cool Customer", phone="0411 222 333", urgency="later", contact_time="evening")[0], 200)
        self.assertEqual(self.lead("acme-roofing", name="Unsure Una", phone="0422 333 444", urgency="rubbish", contact_time="")[0], 200)
        by = {l["name"]: l for l in self.store.leads(t["id"])}
        self.assertEqual((by["Sam Sample"]["hot"], by["Sam Sample"]["urgency"], by["Sam Sample"]["contact_time"]), (1, "As soon as possible", "Morning"))
        self.assertEqual((by["Cool Customer"]["hot"], by["Cool Customer"]["urgency"]), (0, "Just exploring"))
        self.assertEqual((by["Unsure Una"]["hot"], by["Unsure Una"]["urgency"], by["Unsure Una"]["contact_time"]), (0, "", ""))   # an unknown answer is dropped

        c = self.signed_in(t, pw)
        page = c.text("GET", "/q/acme-roofing/admin")[1]
        self.assertIn('class="badge hot">Hot</span>', page)
        self.assertIn("Hot <span>1</span>", page)
        hot_only = c.text("GET", "/q/acme-roofing/admin?hot=1")[1]
        self.assertIn("Sam Sample", hot_only)
        self.assertNotIn("Cool Customer", hot_only)
        detail = c.text("GET", "/q/acme-roofing/admin/lead/%d" % by["Sam Sample"]["id"])[1]
        for expected in ("Ring them first", "Wants it: <b>As soon as possible</b>", "Best time to call: <b>Morning</b>"):
            self.assertIn(expected, detail)
        self.store.update_lead(t["id"], by["Sam Sample"]["id"], status="won")
        self.assertIn("Hot <span>0</span>", c.text("GET", "/q/acme-roofing/admin")[1])        # a won lead is no longer hot work
        csv_text = c.call("GET", "/q/acme-roofing/admin/leads.csv")[1].decode("utf-8-sig")
        self.assertIn("As soon as possible,Morning,yes", csv_text)

    def test_the_same_number_asking_again_is_flagged_however_it_is_written(self):
        t, pw = self.business("Acme Roofing")
        self.lead("acme-roofing", phone="0400 000 000")
        self.lead("acme-roofing", phone="+61 400-000-000", name="Sam Again")
        first, second = sorted(self.store.leads(t["id"]), key=lambda l: l["id"])
        self.assertEqual((first["repeat_of"], second["repeat_of"]), (0, first["id"]))
        self.lead("acme-roofing", phone="0455 555 555", name="Someone Else")
        self.assertEqual(max(self.store.leads(t["id"]), key=lambda l: l["id"])["repeat_of"], 0)
        detail = self.signed_in(t, pw).text("GET", "/q/acme-roofing/admin/lead/%d" % second["id"])[1]
        self.assertIn("Same phone number as an earlier enquiry", detail)
        # another business never sees or matches this number
        other, _ = self.business("Brush Brothers", preset="painting")
        self.lead("brush-brothers", phone="0400 000 000", type_id="interior", difficulty_id="single", size_id="small")
        self.assertEqual(self.store.leads(other["id"])[0]["repeat_of"], 0)

    def test_leads_nobody_has_rung_are_called_out(self):
        t, pw = self.business("Acme Roofing")
        c = self.signed_in(t, pw)
        self.lead("acme-roofing")
        self.assertNotIn("waiting more than a day", c.text("GET", "/q/acme-roofing/admin")[1])
        with self.store.tx() as db:
            db.execute("UPDATE leads SET created_at=created_at-172800 WHERE tenant_id=?", (t["id"],))
        self.assertIn("1 lead has been waiting more than a day", c.text("GET", "/q/acme-roofing/admin")[1])
        self.store.update_lead(t["id"], self.store.leads(t["id"])[0]["id"], status="contacted")
        self.assertNotIn("waiting more than a day", c.text("GET", "/q/acme-roofing/admin")[1])

    def test_the_quote_page_is_told_which_questions_to_ask(self):
        self.business("Acme Roofing")
        js = self.c.text("GET", "/q/acme-roofing/config.js")[1]
        cfg = json.loads(js[js.index("{"):js.rindex("}") + 1])
        self.assertEqual([o["id"] for o in cfg["leadQuestions"]["urgency"]["options"]], ["asap", "month", "later"])
        self.assertTrue(cfg["leadQuestions"]["urgency"]["options"][0]["hot"])
        self.assertEqual(cfg["eventsUrl"], "/q/acme-roofing/event")
        demo = self.c.text("GET", "/q/demo/config.js")[1]
        self.assertNotIn("eventsUrl", demo)                                              # the public demos aren't counted


class Funnel(Base):
    """Proof the quote page is working: anonymous counts, no cookies, nothing personal."""

    def event(self, slug, kind, option="", headers=None):
        return self.c.call("POST", "/q/%s/event" % slug, raw=json.dumps({"k": kind, "o": option}).encode(), headers=headers)

    def test_steps_are_counted_and_shown_against_the_step_before(self):
        t, pw = self.business("Acme Roofing")
        for _ in range(10):
            self.assertEqual(self.event("acme-roofing", "view")[0], 204)
        for _ in range(5):
            self.event("acme-roofing", "start")
        for kind_option in ("tile", "tile", "tin", "colorbond"):
            self.event("acme-roofing", "price", kind_option)
        self.lead("acme-roofing")
        f = self.store.funnel(t["id"])
        self.assertEqual((f["view"], f["start"], f["price"], f["lead"]), (10, 5, 4, 1))
        self.assertEqual(f["types"], {"tile": 2, "tin": 1, "colorbond": 1})
        page = self.signed_in(t, pw).text("GET", "/q/acme-roofing/admin")[1]
        for expected in ("Opened your quote page", "50% of the step before", "80% of the step before", "25% of the step before",
                         "Most asked about: Tile (2)", "Anonymous counts only. No cookies"):
            self.assertIn(expected, page)

    def test_nothing_personal_is_kept_and_no_cookie_is_set(self):
        t, _ = self.business("Acme Roofing")
        status, body, headers = self.event("acme-roofing", "view")
        self.assertEqual((status, body, headers.get("Set-Cookie")), (204, b"", None))
        with self.store.tx() as db:
            self.assertEqual([r[1] for r in db.execute("PRAGMA table_info(funnel)")], ["tenant_id", "day", "kind", "n"])   # a number per day, no addresses

    def test_junk_and_abuse_are_refused_or_ignored(self):
        t, _ = self.business("Acme Roofing")
        self.assertEqual(self.event("acme-roofing", "purchase")[0], 400)
        self.assertEqual(self.c.call("POST", "/q/acme-roofing/event", raw=b"{nope")[0], 400)
        self.assertEqual(self.c.call("POST", "/q/acme-roofing/event", raw=b"[1,2]")[0], 400)
        self.event("acme-roofing", "price", "../../etc/passwd")                           # an option that isn't one of theirs is dropped
        self.assertEqual(self.store.funnel(t["id"])["types"], {})
        self.assertEqual(self.store.funnel(t["id"])["price"], 1)                          # ...but the step itself still counts
        self.assertEqual(self.event("acme-roofing", "view", headers={"Origin": "https://evil.example"})[0], 403)
        self.store.update_tenant(t["id"], active=False)
        self.assertEqual(self.event("acme-roofing", "view")[0], 204)
        self.assertEqual(self.store.funnel(t["id"])["view"], 0)                          # a paused page counts nothing
        self.assertEqual(self.event("demo", "view")[0], 204)
        self.assertEqual(self.store.funnel(self.store.tenant("demo")["id"])["view"], 0)   # nor does a demo
        self.assertEqual(self.c.call("POST", "/q/nobody-here/event", raw=b"{}")[0], 404)

    def test_counting_is_rate_limited_without_telling_a_customer(self):
        t, _ = self.business("Acme Roofing")
        codes = {self.event("acme-roofing", "view")[0] for _ in range(310)}
        self.assertEqual(codes, {204})                                                    # a flood never errors for the visitor...
        self.assertEqual(self.store.funnel(t["id"])["view"], 300)                         # ...but only the first 300 an hour are counted

    def test_an_empty_funnel_says_how_to_get_visitors(self):
        t, pw = self.business("Acme Roofing")
        self.assertIn("No visits yet", self.signed_in(t, pw).text("GET", "/q/acme-roofing/admin")[1])


class Embedding(Base):
    """The quote tool on a business's own website."""

    def test_the_embed_script_is_served_and_only_trusts_its_own_frame(self):
        status, body, h = self.c.call("GET", "/embed.js")
        js = body.decode()
        self.assertEqual((status, h["Content-Type"]), (200, "text/javascript; charset=utf-8"))
        for expected in ('data-business', '/^[a-z0-9-]{3,40}$/', "e.origin !== origin", "e.source !== frame.contentWindow", "?embed=1"):
            self.assertIn(expected, js)

    def test_quote_pages_may_be_framed_anywhere_but_nothing_else_may(self):
        t, pw = self.business("Acme Roofing")
        quote = self.c.call("GET", "/q/acme-roofing/?embed=1")[2]["Content-Security-Policy"]
        self.assertIn("frame-ancestors *", quote)
        self.store.update_tenant(t["id"], active=False)
        self.assertIn("frame-ancestors *", self.c.call("GET", "/q/acme-roofing/")[2]["Content-Security-Policy"])    # the paused notice too
        for path in ("/", "/admin", "/q/acme-roofing/admin", "/q/acme-roofing/config.js", "/static/site.css"):
            policy = self.c.call("GET", path)[2]["Content-Security-Policy"]
            self.assertIn("frame-ancestors 'self'", policy, path)                         # sign-in and inbox pages can never be framed
            self.assertNotIn("frame-ancestors *", policy, path)

    def test_the_settings_page_hands_over_the_embed_code(self):
        t, pw = self.business("Acme Roofing")
        page = self.signed_in(t, pw).text("GET", "/q/acme-roofing/admin/settings")[1]
        self.assertIn("&lt;script src=&quot;%s/embed.js&quot; data-business=&quot;acme-roofing&quot; async&gt;&lt;/script&gt;" % self.base, page)
        self.assertIn("Put it on your website", page)


class Colour(Base):
    def test_a_full_plan_can_wear_its_own_colour_and_stays_readable(self):
        from qm.colour import contrast, on_accent
        t, pw = self.business("Top Roofs", tier="full")
        c = self.signed_in(t, pw)
        form = Settings.form_for(self, t, accent="#e4572e")
        self.assertEqual(c.call("POST", "/q/top-roofs/admin/settings", form=form, files={})[0], 303)
        js = self.c.text("GET", "/q/top-roofs/config.js")[1]
        cfg = json.loads(js[js.index("{"):js.rindex("}") + 1])
        self.assertEqual(cfg["theme"]["accent"], "#E4572E")
        self.assertEqual(cfg["theme"]["onAccent"], on_accent("#E4572E"))
        self.assertGreaterEqual(contrast(cfg["theme"]["onAccent"], cfg["theme"]["accent"]), 4.5)
        before = self.store.tenant("top-roofs")["config"]
        for bad, why in (("blue", "must look like"), ("#123456", "too dark"), ("#1B1D21", "too dark"), ("#GGGGGG", "must look like")):
            status, page = c.text("POST", "/q/top-roofs/admin/settings", form=Settings.form_for(self, t, accent=bad, jt_tile_labour="99"), files={})
            self.assertEqual(status, 400, bad)
            self.assertIn(why, page)
        self.assertEqual(self.store.tenant("top-roofs")["config"], before)                # a refused colour saves nothing, rates included
        self.assertEqual(self.store.tenant("top-roofs")["accent"], "#E4572E")
        form = Settings.form_for(self, t, accent="")
        c.call("POST", "/q/top-roofs/admin/settings", form=form, files={})
        js = self.c.text("GET", "/q/top-roofs/config.js")[1]
        self.assertIn('"accent": "#3D8BFF"', js)                                          # empty goes back to the crew blue

    def test_a_lite_plan_cannot_change_the_colour(self):
        t, pw = self.business("Acme Roofing", tier="lite")
        c = self.signed_in(t, pw)
        self.assertNotIn('name="accent"', c.text("GET", "/q/acme-roofing/admin/settings")[1])
        c.call("POST", "/q/acme-roofing/admin/settings", form=Settings.form_for(self, t, accent="#E4572E"), files={})
        js = self.c.text("GET", "/q/acme-roofing/config.js")[1]
        self.assertIn('"accent": "#3D8BFF"', js)


class Migration(unittest.TestCase):
    def test_a_database_from_before_these_features_is_upgraded_in_place(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "old.db")
            con = sqlite3.connect(path)
            con.executescript("""
CREATE TABLE settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE tenants(id INTEGER PRIMARY KEY AUTOINCREMENT, slug TEXT NOT NULL UNIQUE, name TEXT NOT NULL, tier TEXT NOT NULL DEFAULT 'lite',
  active INTEGER NOT NULL DEFAULT 1, demo INTEGER NOT NULL DEFAULT 0, paid_until TEXT NOT NULL DEFAULT '', preset TEXT NOT NULL DEFAULT 'roofing',
  config_json TEXT NOT NULL, rates_confirmed INTEGER NOT NULL DEFAULT 0, phone TEXT NOT NULL DEFAULT '', licence TEXT NOT NULL DEFAULT '',
  contact_email TEXT NOT NULL DEFAULT '', notify_email TEXT NOT NULL DEFAULT '', forward_webhook TEXT NOT NULL DEFAULT '',
  logo BLOB, logo_type TEXT NOT NULL DEFAULT '', pw_hash BLOB NOT NULL, pw_salt BLOB NOT NULL, created_at INTEGER NOT NULL);
CREATE TABLE leads(id INTEGER PRIMARY KEY AUTOINCREMENT, tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  created_at INTEGER NOT NULL, name TEXT NOT NULL, phone TEXT NOT NULL, email TEXT NOT NULL, suburb TEXT NOT NULL, job_type TEXT NOT NULL,
  difficulty TEXT NOT NULL, size TEXT NOT NULL, low INTEGER NOT NULL, high INTEGER NOT NULL, photos INTEGER NOT NULL DEFAULT 0,
  status TEXT NOT NULL DEFAULT 'new', notes TEXT NOT NULL DEFAULT '', email_status TEXT NOT NULL DEFAULT '', forward_status TEXT NOT NULL DEFAULT '');
INSERT INTO tenants(slug,name,config_json,pw_hash,pw_salt,created_at) VALUES('old-biz','Old Biz','{}',x'00',x'00',1);
INSERT INTO leads(tenant_id,created_at,name,phone,email,suburb,job_type,difficulty,size,low,high) VALUES(1,5,'Old Lead','0400 000 000','a@b.co','X','J','D','S',100,200);""")
            con.commit()
            con.close()
            store = server.Store(path, os.path.join(ROOT, "presets"))
            old = store.leads(1)[0]
            self.assertEqual((old["name"], old["hot"], old["urgency"], old["repeat_of"], old["reply_status"]), ("Old Lead", 0, "", 0, ""))
            tenant = store.tenant("old-biz")
            self.assertEqual((tenant["accent"], tenant["auto_reply"]), ("", 1))               # confirmation emails default on
            lead_id = store.add_lead(1, {"name": "New", "phone": "0400 000 000", "email": "n@b.co", "suburb": "Y", "job_type": "J",
                                         "difficulty": "D", "size": "S", "low": 1, "high": 2, "hot": True})
            self.assertEqual(store.lead(1, lead_id)["hot"], 1)
            server.Store(path, os.path.join(ROOT, "presets"))                                  # starting again changes nothing


class FakeSmtp(socketserver.StreamRequestHandler):
    """Speaks just enough SMTP to receive one message."""
    inbox = []

    def handle(self):
        self.wfile.write(b"220 test ESMTP\r\n")
        data, in_data = [], False
        for raw in self.rfile:
            line = raw.decode("utf-8", "replace")
            if in_data:
                if line == ".\r\n":
                    FakeSmtp.inbox.append("".join(data))
                    in_data = False
                    self.wfile.write(b"250 queued\r\n")
                else:
                    data.append(line)
            elif line[:4].upper() == "DATA":
                in_data = True
                self.wfile.write(b"354 go on\r\n")
            elif line[:4].upper() == "QUIT":
                self.wfile.write(b"221 bye\r\n")
                return
            else:
                self.wfile.write(b"250 ok\r\n")


class Hook(BaseHTTPRequestHandler):
    got = []

    def do_POST(self):
        Hook.got.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
        self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):
        pass


class Delivery(Base):
    def setUp(self):
        FakeSmtp.inbox, Hook.got = [], []
        self.smtp = socketserver.ThreadingTCPServer(("127.0.0.1", 0), FakeSmtp)
        self.hook = HTTPServer(("127.0.0.1", 0), Hook)
        for s in (self.smtp, self.hook):
            threading.Thread(target=s.serve_forever, daemon=True).start()
        self.ENV = {"SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(self.smtp.server_address[1]), "SMTP_FROM": "leads@quotemate.example",
                    "SMTP_TLS": "none", "QM_ALLOW_PRIVATE_FORWARD": "1", "PUBLIC_URL": "https://quotes.example.com"}
        super().setUp()

    def tearDown(self):
        super().tearDown()
        for s in (self.smtp, self.hook):
            s.shutdown()
            s.server_close()

    def test_a_new_lead_is_emailed_and_copied_to_the_tradies_webhook(self):
        t, _ = self.business("Acme Roofing")
        self.store.update_tenant(t["id"], notify_email="boss@acme.example")
        with self.store.tx() as c:                                    # test-only: a local address, normally refused by the settings page
            c.execute("UPDATE tenants SET forward_webhook=? WHERE id=?", ("http://127.0.0.1:%d/hook" % self.hook.server_address[1], t["id"]))
        self.assertEqual(self.lead("acme-roofing", name="Sam\r\nBcc: everyone@evil.example")[0], 200)
        lead = self.wait_for(lambda: next((l for l in self.store.leads(t["id"]) if l["email_status"] and l["forward_status"]), None))
        self.assertEqual((lead["email_status"], lead["forward_status"]), ("sent", "sent"))
        mail = FakeSmtp.inbox[0]
        for expected in ("To: boss@acme.example", "From: leads@quotemate.example", "Reply-To: sam@example.com", "0400 000 000",
                         "$17,800 to $36,300 including GST", "https://quotes.example.com/q/acme-roofing/admin/lead/%d" % lead["id"]):
            self.assertIn(expected, mail)
        headers = mail.split("\r\n\r\n")[0]
        self.assertFalse([h for h in headers.split("\r\n") if h.lower().startswith("bcc")])   # a name can't smuggle in a mail header
        self.assertIn("Subject: New quote request: Sam Bcc: everyone@evil.example, Fremantle", headers)   # it stays inside the subject text
        self.assertEqual((Hook.got[0]["name"], Hook.got[0]["low"], Hook.got[0]["business"]), ("Sam Bcc: everyone@evil.example", 17800, "Acme Roofing"))

    def test_a_dead_mail_server_never_loses_the_lead(self):
        t, _ = self.business("Acme Roofing")
        self.store.update_tenant(t["id"], notify_email="boss@acme.example")
        self.app.smtp["port"] = 1                                      # nothing is listening there
        self.assertEqual(self.lead("acme-roofing")[0], 200)
        lead = self.wait_for(lambda: next((l for l in self.store.leads(t["id"]) if l["email_status"]), None))
        self.assertTrue(lead["email_status"].startswith("failed"))
        self.assertEqual(lead["name"], "Sam Sample")


    def test_the_homeowner_gets_a_confirmation_and_can_be_switched_off(self):
        t, _ = self.business("Acme Roofing", phone="08 1111 1111")
        self.store.update_tenant(t["id"], notify_email="boss@acme.example")
        self.assertEqual(self.lead("acme-roofing", name="Sam\r\nBcc: everyone@evil.example", contact_time="morning", urgency="asap")[0], 200)
        lead = self.wait_for(lambda: next((l for l in self.store.leads(t["id"]) if l["reply_status"]), None))
        self.assertEqual(lead["reply_status"], "sent")
        self.wait_for(lambda: len(FakeSmtp.inbox) >= 2)
        mails = {("sam@example.com" if "\r\nTo: sam@example.com\r\n" in m else "boss@acme.example"): m for m in FakeSmtp.inbox}
        reply = mails["sam@example.com"]
        for expected in ("Subject: Your quote request to Acme Roofing", "Hi Sam,", "$17,800 to $36,300 including GST",
                         "best time to call is: morning", "Call 08 1111 1111", "Reply-To: boss@acme.example"):
            self.assertIn(expected, reply)
        self.assertFalse([h for h in reply.split("\r\n\r\n")[0].split("\r\n") if h.lower().startswith("bcc")])
        boss = mails["boss@acme.example"]
        self.assertIn("Subject: HOT: New quote request", boss)                              # the tradie's email leads with the hot flag
        self.assertIn("Wants it:  As soon as possible", boss)

        FakeSmtp.inbox.clear()
        self.store.update_tenant(t["id"], auto_reply=False)
        self.lead("acme-roofing", name="Second Person", phone="0433 444 555")
        self.wait_for(lambda: len(FakeSmtp.inbox) >= 1)
        time.sleep(0.4)
        self.assertEqual(len(FakeSmtp.inbox), 1)                                            # only the tradie's email
        self.assertIn("To: boss@acme.example", FakeSmtp.inbox[0])

    def test_no_mail_server_means_no_confirmation_but_the_lead_is_safe(self):
        t, _ = self.business("Acme Roofing")
        self.app.smtp = None
        self.lead("acme-roofing")
        lead = self.wait_for(lambda: next((l for l in self.store.leads(t["id"]) if l["reply_status"]), None))
        self.assertEqual(lead["reply_status"], "not sent: email is not set up")
        self.assertEqual(lead["name"], "Sam Sample")


class Guards(unittest.TestCase):
    def test_webhook_addresses_must_be_public_https(self):
        for bad in ("http://example.com/x", "https://127.0.0.1/x", "https://localhost/x", "https://10.0.0.5/x", "https://169.254.169.254/latest",
                    "https://[::1]/x", "https://user:pw@example.com/x", "ftp://example.com", "https:///nohost", "file:///etc/passwd"):
            with self.assertRaises(ValueError, msg=bad):
                deliver.safe_public_url(bad)

    def test_image_sniffing_ignores_names(self):
        self.assertEqual(server.image_kind(JPEG), ("jpg", "image/jpeg"))
        self.assertEqual(server.image_kind(PNG), ("png", "image/png"))
        self.assertEqual(server.image_kind(b"RIFF\x00\x00\x00\x00WEBPVP8 "), ("webp", "image/webp"))
        for bad in (b"<svg onload=alert(1)>", b"GIF89a", b"%PDF-1.4", b"", b"<html>"):
            self.assertIsNone(server.image_kind(bad))


class PricingAgreesWithTheBrowser(unittest.TestCase):
    """The server's sum and the quote tool's sum must give the same range for every choice."""

    def test_presets_are_valid(self):
        for name in ("roofing", "painting", "pets", "batteries", "homecare", "bookkeeping"):
            with open(os.path.join(ROOT, "presets", name + ".json"), encoding="utf-8") as fh:
                self.assertEqual(check_config(json.load(fh)), [], name)

    @unittest.skipUnless(shutil.which("node"), "node is not installed")
    def test_every_combination_matches_estimate_js(self):
        tool = os.path.join(os.path.dirname(ROOT), "roof-quote-mate", "estimate.js")
        script = ("const {estimate} = require(process.argv[1]); const c = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));"
                  "const out = []; for (const t of c.jobTypes) for (const d of c.difficulty) for (const s of c.sizes) {"
                  "const e = estimate(c, {type: t.id, difficulty: d.id, size: s.id}); out.push([t.id, d.id, s.id, e.low, e.high]); }"
                  "console.log(JSON.stringify(out));")
        checked = 0
        for name, tweak in (("roofing", {}), ("painting", {}), ("pets", {}), ("batteries", {}), ("homecare", {}), ("bookkeeping", {}),
                            ("homecare", {"gstRegistered": True, "ratesIncludeGst": True, "roundTo": 1}),
                            ("roofing", {"spread": 0.075, "roundTo": 1, "minimumJob": 0, "ratesIncludeGst": True}),
                            ("painting", {"spread": 0.333, "roundTo": 25, "gstRate": 0.125}),
                            ("pets", {"gstRegistered": True, "roundTo": 1}),
                            ("batteries", {"gstRegistered": False, "ratesIncludeGst": False, "roundTo": 1}),
                            ("batteries", {"spread": 0.173, "roundTo": 25, "rebate": {"label": "x", "perUnit": 187.5,
                                                                                         "bands": [{"upTo": 7, "share": 1}, {"upTo": 30, "share": 0.35}]}})):
            with open(os.path.join(ROOT, "presets", name + ".json"), encoding="utf-8") as fh:
                cfg = json.load(fh)
            cfg["pricing"].update(tweak)
            cfg["jobTypes"][0]["labourPerUnit"] = 61.37
            with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
                json.dump(cfg, fh)
            try:
                rows = json.loads(subprocess.run(["node", "-e", script, tool, fh.name], capture_output=True, text=True, check=True).stdout)
            finally:
                os.unlink(fh.name)
            for t, d, s, low, high in rows:
                e = estimate(cfg, t, d, s)
                self.assertEqual((e["low"], e["high"]), (low, high), (name, tweak, t, d, s))
                checked += 1
        self.assertGreater(checked, 11 * 12)


if __name__ == "__main__":
    unittest.main()
