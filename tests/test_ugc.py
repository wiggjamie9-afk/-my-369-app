import json, os, tempfile, unittest
from ai9.agent import AI9
from ai9.memory import LocalBackend
from ugc import factory
from ugc.brand import Brief
from ugc.compliance import lint
from ugc.muapi import MuapiProvider
from video.providers import SlateProvider
from video.plan import Shot


def brief(**kw):
    d = dict(brand="Acme", product="boiler cover", audience="homeowners", pain="cold mornings",
             outcome="a warm house", verified_claims=["Fits most boilers"], verified_quotes=[])
    d.update(kw); return Brief(**d)


def _j(path):
    with open(path) as f:
        return json.load(f)


def ai():
    return AI9(LocalBackend(os.path.join(tempfile.mkdtemp(), "m.json")), lambda s, u: "ok")


class Compliance(unittest.TestCase):
    def test_fake_testimonial_blocked(self):
        for t in ["I tried this and loved it", "It changed my life", "My skin looks great after using it"]:
            self.assertTrue(lint(t, brief()), t)

    def test_demonstration_allowed(self):
        self.assertEqual(lint("Here is how the boiler cover fits. Fits most boilers.", brief()), [])

    def test_unverified_claim_blocked_verified_allowed(self):
        self.assertTrue(lint("Cuts bills by 40%", brief()))
        self.assertEqual(lint("Cuts bills by 40%", brief(verified_claims=["Cuts bills by 40%"])), [])

    def test_real_quote_allowed(self):
        q = "I tried it and loved it"
        self.assertEqual(lint(f'Customer says: "{q}"', brief(verified_quotes=[q])), [])


class Factory(unittest.TestCase):
    def test_batch_makes_labelled_videos_and_sidecars(self):
        d = tempfile.mkdtemp()
        r = factory.run_batch(brief(), SlateProvider(720, 1280), d, ai(), n=3)
        self.assertEqual(len(r["made"]), 3)
        for m in r["made"]:
            self.assertTrue(os.path.exists(m["file"]))
            self.assertTrue(_j(os.path.join(d, m["id"] + ".json"))["ai_generated"])

    def test_bad_llm_hooks_are_blocked_not_made(self):
        llm = lambda p: ["I tried this and loved it", "Meet the boiler cover and how it fits."]
        r = factory.run_batch(brief(), SlateProvider(720, 1280), tempfile.mkdtemp(), None, n=2, llm=llm)
        self.assertEqual(len(r["made"]), 1); self.assertEqual(len(r["blocked"]), 1)

    def test_results_feed_memory(self):
        a = ai(); self.assertTrue(factory.record_result(a, "Acme-00", "Meet the cover", 1000, 25, 12.5))
        self.assertIn("2.5% click rate", next(iter(a.backend.items.values())).what)


class Muapi(unittest.TestCase):
    shots = [Shot(0, "x", "x", 5.0)]

    def test_no_price_no_run(self):
        with self.assertRaises(NotImplementedError):
            MuapiProvider(api_key="k").estimate_cost(self.shots)

    def test_estimate(self):
        p = MuapiProvider(model="happy-horse", usd_per_credit=0.01, api_key="k")
        self.assertAlmostEqual(p.estimate_cost(self.shots), 5 * 36 * 0.01)

    def test_submit_poll_download(self):
        calls, got = [], []
        def http(m, url, h=None, b=None):
            calls.append((m, url))
            return {"request_id": "r1"} if m == "POST" else {"status": "completed", "outputs": ["http://v/1.mp4"]}
        p = MuapiProvider(api_key="k", http=http, download=lambda u, o: got.append((u, o)), poll_s=0)
        p.generate(self.shots[0], "/tmp/o.mp4")
        self.assertEqual(calls[0][0], "POST"); self.assertEqual(got, [("http://v/1.mp4", "/tmp/o.mp4")])

    def test_paid_run_blocked_without_budget(self):
        p = MuapiProvider(usd_per_credit=0.01, api_key="k", http=lambda *a, **k: self.fail("must not call API"))
        with self.assertRaises(PermissionError):
            factory.run_batch(brief(), p, tempfile.mkdtemp(), None, n=1, approved_budget=0)


if __name__ == "__main__":
    unittest.main()
