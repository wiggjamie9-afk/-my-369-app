import http.server
import json
import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import panel  # noqa: E402

IDEA = {"name": "Snack Box", "pitch": "Snacks monthly", "price": 39, "currency": "AUD", "price_points": [19, 39, 59]}


class FakeAPI(http.server.BaseHTTPRequestHandler):
    script = []      # list of ("429"|"500"|"401"|"ok"|"junk", payload)
    calls = 0
    lock = threading.Lock()

    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers.get("content-length", 0)))
        with FakeAPI.lock:
            FakeAPI.calls += 1
            kind = FakeAPI.script.pop(0) if FakeAPI.script else "ok"
        if kind in ("429", "500", "401"):
            self.send_response(int(kind))
            self.send_header("retry-after", "0")
            self.end_headers()
            return
        text = "not json at all" if kind == "junk" else json.dumps(
            {"decision": "buy", "max_price": 45, "stars": 4, "objection": "weird_value", "reason": "<script>x</script> fine", "review": "ok"})
        body = json.dumps({"content": [{"type": "text", "text": text}]}).encode()
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.end_headers()
        self.wfile.write(body)


class Server:
    def __enter__(self):
        FakeAPI.script, FakeAPI.calls = [], 0
        self.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeAPI)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = "http://127.0.0.1:%d/v1/messages" % self.srv.server_address[1]
        return self

    def __exit__(self, *a):
        self.srv.shutdown()


def cfg(url, **kw):
    return panel.Config(api_key="test", base_url=url, backoff=0.01, **kw)


class Personas(unittest.TestCase):
    def test_repeatable_and_sized(self):
        a, b = panel.make_personas(500, 7), panel.make_personas(500, 7)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 500)
        self.assertNotEqual(a, panel.make_personas(500, 8))

    def test_mix_is_sensible(self):
        people = panel.make_personas(5000, 1)
        nsw = sum(1 for p in people if p["state"] == "NSW") / 5000
        self.assertTrue(0.28 < nsw < 0.36, nsw)
        self.assertTrue(all(18 <= p["age"] <= 82 for p in people))
        # retired households only for older people, share houses never for the old
        self.assertTrue(all(p["age"] >= 65 for p in people if "retired" in p["household"]))
        self.assertFalse(any(p["age"] >= 65 and "share house" in p["household"] for p in people))

    def test_prompt_contains_no_pitch_leakage_and_has_traits(self):
        t = panel.persona_text(panel.make_personas(1)[0])
        self.assertIn("Australia", t)


class Parsing(unittest.TestCase):
    def test_good_and_messy(self):
        r = panel.parse_answer('Sure!\n{"decision":"buy","max_price":"30","stars":9,"objection":"nonsense","reason":"r","review":"v"}\nthanks')
        self.assertEqual((r["decision"], r["max_price"], r["stars"], r["objection"]), ("BUY", 30.0, 5, "other"))

    def test_bad_inputs(self):
        for bad in ("", "no json", '{"decision":"YES"}', '{"decision":', '{"nodecision":1}'):
            self.assertIsNone(panel.parse_answer(bad), bad)

    def test_price_clamped(self):
        r = panel.parse_answer('{"decision":"BUY","max_price":-5,"stars":1}')
        self.assertEqual(r["max_price"], 0.0)


class Aggregation(unittest.TestCase):
    def setUp(self):
        self.people = panel.make_personas(10, 1)

    def result(self, i, d, mp):
        return {"id": i, "ok": True, "decision": d, "max_price": mp, "stars": 3, "objection": "too_expensive" if d != "BUY" else "none", "reason": "r"}

    def test_rates_and_price_curve(self):
        res = [self.result(i + 1, "BUY" if i < 2 else "MAYBE" if i < 4 else "PASS", 50 if i < 2 else 30 if i < 4 else 0) for i in range(10)]
        res.append({"id": 99, "ok": False, "error": "x"})
        agg = panel.aggregate(res, self.people, [20, 40, 60])
        self.assertEqual((agg["n"], agg["errors"]), (10, 1))
        self.assertAlmostEqual(agg["buy"], 0.2)
        self.assertAlmostEqual(agg["maybe"], 0.2)
        self.assertAlmostEqual(agg["pass"], 0.6)
        self.assertEqual([round(d["share"], 2) for d in agg["demand"]], [0.4, 0.2, 0.0])
        self.assertEqual(agg["objections"][0][0], "too_expensive")
        self.assertEqual(agg["median_max_price"], 40)

    def test_empty(self):
        self.assertEqual(panel.aggregate([], self.people, [1])["n"], 0)

    def test_control_verdict(self):
        self.assertTrue(panel.control_verdict({"n": 100, "buy": 0.4, "maybe": 0.1}).startswith("WARNING"))
        self.assertTrue(panel.control_verdict({"n": 100, "buy": 0.01, "maybe": 0.03}).startswith("Control check passed"))
        self.assertIsNone(panel.control_verdict(None))


class Report(unittest.TestCase):
    def test_escapes_model_text_and_marks_mock(self):
        people = panel.make_personas(40, 1)
        res = [{"id": p["id"], "ok": True, "decision": "BUY", "max_price": 40, "stars": 5, "objection": "none",
                "reason": "<script>alert(1)</script>"} for p in people]
        agg = panel.aggregate(res, people, [39])
        page = panel.render_report(dict(IDEA, name="<b>x</b>"), agg, None, {"model": "mock", "mock": True})
        self.assertNotIn("<script>alert", page)
        self.assertNotIn("<b>x</b>", page)
        self.assertIn("MOCK RUN", page)
        self.assertIn("does <b>not</b> tell you", page)


class MockRun(unittest.TestCase):
    def test_end_to_end_and_control_separates(self):
        with tempfile.TemporaryDirectory() as d:
            idea = os.path.join(d, "idea.json")
            with open(idea, "w") as fh:
                json.dump(IDEA, fh)
            panel.main(["run", idea, "--size", "300", "--mock", "--out", os.path.join(d, "o"), "--control-size", "100"])
            s = json.load(open(os.path.join(d, "o", "summary.json")))
            self.assertEqual(s["panel"]["n"], 300)
            self.assertTrue(s["meta"]["mock"])
            self.assertLess(s["control"]["buy"], s["panel"]["buy"])
            for f in ("report.html", "answers.csv"):
                self.assertTrue(os.path.getsize(os.path.join(d, "o", f)) > 0)

    def test_resume_skips_done_work(self):
        people = panel.make_personas(20, 1)
        c = panel.Config(mock=True)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "r.jsonl")
            panel.run_arm(c, people, IDEA, p, 4, "t")
            n1 = len(open(p).read().splitlines())
            panel.run_arm(c, people, IDEA, p, 4, "t")
            self.assertEqual(len(open(p).read().splitlines()), n1)
            # a changed offer must not reuse stale answers
            panel.run_arm(c, people, dict(IDEA, price=99), p, 4, "t")
            self.assertEqual(len(open(p).read().splitlines()), n1 * 2)


class RealPath(unittest.TestCase):
    def test_success_and_retry_on_429(self):
        with Server() as s:
            FakeAPI.script = ["429", "500"]
            r = panel.ask(cfg(s.url), panel.make_personas(1)[0], IDEA, "fp")
            self.assertTrue(r["ok"])
            self.assertEqual(r["decision"], "BUY")
            self.assertEqual(r["objection"], "other")
            self.assertEqual(FakeAPI.calls, 3)

    def test_unparseable_then_retried_once_then_counted_as_error(self):
        with Server() as s:
            FakeAPI.script = ["junk", "junk"]
            r = panel.ask(cfg(s.url), panel.make_personas(1)[0], IDEA, "fp")
            self.assertFalse(r["ok"])
            self.assertEqual(FakeAPI.calls, 2)

    def test_bad_key_stops_the_whole_run(self):
        with Server() as s:
            FakeAPI.script = ["401"] * 50
            with tempfile.TemporaryDirectory() as d:
                with self.assertRaises(panel.Fatal):
                    panel.run_arm(cfg(s.url), panel.make_personas(30), IDEA, os.path.join(d, "r.jsonl"), 4, "t")

    def test_real_run_through_fake_server(self):
        with Server() as s, tempfile.TemporaryDirectory() as d:
            idea = os.path.join(d, "idea.json")
            with open(idea, "w") as fh:
                json.dump(IDEA, fh)
            os.environ["ANTHROPIC_API_KEY"], os.environ["ANTHROPIC_BASE_URL"] = "k", s.url
            try:
                panel.main(["run", idea, "--size", "25", "--control-size", "5", "--yes", "--out", os.path.join(d, "o")])
            finally:
                del os.environ["ANTHROPIC_API_KEY"], os.environ["ANTHROPIC_BASE_URL"]
            self.assertEqual(FakeAPI.calls, 30)
            self.assertFalse(json.load(open(os.path.join(d, "o", "summary.json")))["meta"]["mock"])


class Guards(unittest.TestCase):
    def run_cli(self, *extra, key="k"):
        with tempfile.TemporaryDirectory() as d:
            idea = os.path.join(d, "idea.json")
            with open(idea, "w") as fh:
                json.dump(IDEA, fh)
            old = os.environ.get("ANTHROPIC_API_KEY")
            if key:
                os.environ["ANTHROPIC_API_KEY"] = key
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)
            try:
                with self.assertRaises(SystemExit) as cm:
                    panel.main(["run", idea, "--out", os.path.join(d, "o"), *extra])
                return str(cm.exception)
            finally:
                os.environ.pop("ANTHROPIC_API_KEY", None)
                if old:
                    os.environ["ANTHROPIC_API_KEY"] = old

    def test_needs_yes(self):
        self.assertIn("--yes", self.run_cli("--size", "10"))

    def test_needs_key(self):
        self.assertIn("ANTHROPIC_API_KEY", self.run_cli("--size", "10", "--yes", key=""))

    def test_call_cap(self):
        self.assertIn("--max-calls", self.run_cli("--size", "5000", "--yes"))


if __name__ == "__main__":
    unittest.main()
