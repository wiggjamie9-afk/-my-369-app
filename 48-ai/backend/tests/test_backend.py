"""Simulated-Twilio tests: signed webhooks over real HTTP, API auth, metering, forwarding. Never touches real Twilio."""
import json, os, sys, tempfile, threading, unittest, urllib.error, urllib.parse, urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer
from datetime import timedelta

TMP = tempfile.mkdtemp(prefix="jane_")
os.environ.update(JANE_DB=os.path.join(TMP, "t.db"), TWILIO_AUTH_TOKEN="tok123", ADMIN_TOKEN="adm", JANE_PUBLIC_URL="https://jane.test")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import jane_backend as J  # noqa: E402

NUM, CALLER = "+61860000001", "+61400111222"


def post(base, path, form=None, js=None, hdr=None, sign=True):
    if form is not None:
        body = urllib.parse.urlencode(form).encode()
        h = {"Content-Type": "application/x-www-form-urlencoded"}
        if sign:
            h["X-Twilio-Signature"] = J.twilio_signature("tok123", "https://jane.test" + path, form)
    else:
        body, h = json.dumps(js or {}).encode(), {"Content-Type": "application/json"}
    h.update(hdr or {})
    req = urllib.request.Request(base + path, data=body, headers=h)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def get(base, path, key=None):
    req = urllib.request.Request(base + path, headers={"Authorization": f"Bearer {key}"} if key else {})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        J.init_db()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), J.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.srv.server_port}"
        c, r = post(cls.base, "/admin/business", js={"name": "Wigg's Plumbing", "owner": "Wigg", "twilio_number": NUM, "forward_phone": "+61400999888", "plan_minutes": 5},
                    hdr={"X-Admin-Token": "adm"})
        assert c == 200, r
        cls.key = json.loads(r)["api_key"]

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown(); cls.srv.server_close()

    def call(self, sid, say=None):
        form = {"CallSid": sid, "From": CALLER, "To": NUM}
        if say is None:
            return post(self.base, "/twilio/voice", form)
        form["SpeechResult"] = say
        return post(self.base, "/twilio/gather", form)

    def test_01_security(self):
        self.assertEqual(post(self.base, "/twilio/voice", {"CallSid": "x", "To": NUM}, sign=False)[0], 403)
        c, _ = post(self.base, "/admin/business", js={"name": "x", "twilio_number": "+1"}, hdr={"X-Admin-Token": "wrong"})
        self.assertEqual(c, 401)
        self.assertEqual(get(self.base, "/v1/me")[0], 401)
        self.assertEqual(get(self.base, "/v1/me", "jk_bad")[0], 401)
        self.assertEqual(post(self.base, "/admin/business", js={"name": "dup", "twilio_number": NUM}, hdr={"X-Admin-Token": "adm"})[0], 409)

    def test_02_booking_call_and_app_api(self):
        c, x = self.call("CA1")
        self.assertEqual(c, 200)
        self.assertIn("I'm Jane, an AI assistant", x)
        self.assertIn('input="speech"', x)
        self.assertIn("https://jane.test/twilio/gather", x)
        self.assertNotIn("record", x.lower())                                   # we don't record, so we don't claim to
        self.assertIn("name", self.call("CA1", "my kitchen tap is leaking")[1].lower())
        self.call("CA1", "Jamie Hall")
        self.call("CA1", "22 Beach Rd Scarborough")
        c, x = self.call("CA1", "tomorrow morning")
        self.assertIn("All booked", x)
        self.assertIn("Anything else", x)
        c, x = self.call("CA1", "no thanks")
        self.assertIn("<Hangup/>", x)
        c, today = get(self.base, "/v1/bookings", self.key)
        job = next(j for j in today["rows"] if j["customer"] == "Jamie Hall")
        self.assertEqual((job["status"], job["phone"], job["call_sid"]), ("Booked", CALLER, "CA1"))
        self.assertGreaterEqual(int(job["time"][:2]), 8)
        # second caller asking for the same slot gets a different one
        self.call("CA2"); self.call("CA2", "leaking tap again"); self.call("CA2", "Sam"); self.call("CA2", "Perth")
        self.call("CA2", "tomorrow morning")
        _, b = get(self.base, "/v1/bookings", self.key)
        slots = [(j["date"], j["time"]) for j in b["rows"]]
        self.assertEqual(len(slots), len(set(slots)))
        # app can mark done + create manual booking
        self.assertEqual(post(self.base, f"/v1/jobs/{job['id']}/done", js={}, hdr={"Authorization": f"Bearer {self.key}"})[0], 200)
        self.assertEqual(post(self.base, "/v1/bookings", js={"date": "2030-01-02", "time": "10:00", "customer": "M", "job": "J"}, hdr={"Authorization": f"Bearer {self.key}"})[0], 200)
        self.assertEqual(post(self.base, "/v1/bookings", js={"date": "2030-01-02"}, hdr={"Authorization": f"Bearer {self.key}"})[0], 400)

    def test_03_urgent_robot_human_price(self):
        self.call("CA3")
        c, x = self.call("CA3", "are you a robot?")
        self.assertIn("AI assistant", x)
        c, x = self.call("CA3", "how much for a quote?")
        self.assertIn("can't give prices", x)
        self.call("CA4")
        c, x = self.call("CA4", "I can smell gas")
        self.assertIn("triple zero", x)
        self.call("CA4", "Ann Lee")
        self.call("CA5"); c, x = self.call("CA5", "can I speak to a person")
        self.assertIn("call you back", x)
        _, ib = get(self.base, "/v1/inbox", self.key)
        names = {r["name"]: r for r in ib["rows"]}
        self.assertTrue(names["Ann Lee"]["urgent"])
        self.assertEqual(names["Ann Lee"]["phone"], CALLER)
        rid = names["Ann Lee"]["id"]
        post(self.base, f"/v1/inbox/{rid}/clear", js={}, hdr={"Authorization": f"Bearer {self.key}"})
        self.assertNotIn(rid, [r["id"] for r in get(self.base, "/v1/inbox", self.key)[1]["rows"]])

    def test_04_silence_and_xml_escaping(self):
        self.call("CA6")
        self.assertIn("say it again", self.call("CA6", "")[1])
        c, x = self.call("CA6", "")
        self.assertIn("<Hangup/>", x)
        post(self.base, "/admin/business", js={"name": "A & B <Plumbing>", "twilio_number": "+61860000009"}, hdr={"X-Admin-Token": "adm"})
        c, x = post(self.base, "/twilio/voice", {"CallSid": "CA7", "From": CALLER, "To": "+61860000009"})
        self.assertIn("A &amp; B &lt;Plumbing&gt;", x)

    def test_05_metering_modes_and_forwarding(self):
        _, me = get(self.base, "/v1/me", self.key)
        before = me["minutes_used"]
        post(self.base, "/twilio/status", {"CallSid": "CA1", "CallStatus": "completed", "CallDuration": "125"})
        post(self.base, "/twilio/status", {"CallSid": "CA1", "CallStatus": "completed", "CallDuration": "125"})   # duplicate callback: counted once
        self.assertAlmostEqual(get(self.base, "/v1/me", self.key)[1]["minutes_used"] - before, 2.1, places=1)
        # mode off -> forward to owner
        post(self.base, "/v1/settings", js={"mode": "off"}, hdr={"Authorization": f"Bearer {self.key}"})
        c, x = self.call("CA8")
        self.assertIn("<Dial>+61400999888</Dial>", x)
        post(self.base, "/v1/settings", js={"mode": "on"}, hdr={"Authorization": f"Bearer {self.key}"})
        # use up the plan (5 min) -> forwarded, and forwarded calls aren't metered
        post(self.base, "/twilio/status", {"CallSid": "CA2", "CallStatus": "completed", "CallDuration": "300"})
        c, x = self.call("CA9")
        self.assertIn("<Dial>", x)
        used = get(self.base, "/v1/me", self.key)[1]["minutes_used"]
        post(self.base, "/twilio/status", {"CallSid": "CA9", "CallStatus": "completed", "CallDuration": "600"})
        self.assertEqual(get(self.base, "/v1/me", self.key)[1]["minutes_used"], used)

    def test_06_unknown_number_and_engine_limits(self):
        c, x = post(self.base, "/twilio/voice", {"CallSid": "CA10", "From": CALLER, "To": "+61000"})
        self.assertIn("isn't set up", x)
        st = J.new_state(); biz = {"name": "N", "owner": "O"}
        for i in range(J.MAX_TURNS):
            say, end, _ = J.step(st, "hmm okay then", biz, CALLER, set(), J.now())
            if end:
                break
        self.assertTrue(end)                                                      # call length limit ends a stuck call
        d, h = J.parse_when("friday at 3pm", J.now())
        self.assertEqual(h, 15)
        self.assertEqual(J.parse_when("next sunday", J.now())[0].weekday(), 6)


if __name__ == "__main__":
    unittest.main()
