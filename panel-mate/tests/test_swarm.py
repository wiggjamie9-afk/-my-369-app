import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import panel as P  # noqa: E402
import swarm as S  # noqa: E402
from test_panel import FakeAPI, Server  # noqa: E402

EXAMPLES = os.path.join(HERE, "..", "examples", "businesses")


def load(name):
    with open(os.path.join(EXAMPLES, name), encoding="utf-8") as fh:
        return S.normalise_business(json.load(fh))


class Money(unittest.TestCase):
    def test_cents_is_exact(self):
        self.assertEqual((S.cents(1.75), S.cents("0.3"), S.cents(9.5), S.cents(0.1 + 0.2)), (175, 30, 950, 30))

    def test_product_margin_by_hand(self):
        # price 3900c, GST 355c, revenue 3545c, fees 68+30, refunds 106, unit 1600, post 950, pack 200, ads 1200
        m = S.margin(load("snack-box.json"))
        self.assertEqual(m["contribution"], -609)
        self.assertEqual(m["missing"], [])
        self.assertIsNone(m["break_even"])

    def test_subscription_margin_by_hand(self):
        m = S.margin(load("48-ai-crew-quoting.json"))
        self.assertEqual(m["contribution"], 6270)
        self.assertEqual(m["ltv"], 125400)
        self.assertEqual((m["ltv_to_cac"], m["payback_months"]), (8.4, 2.4))
        self.assertEqual(m["break_even"], 2)   # $120 fixed costs / $62.70 per customer, rounded up

    def test_gst_off_and_missing_fields(self):
        biz = S.normalise_business({"name": "x", "pitch": "p", "price": 10, "gst_registered": False})
        m = S.margin(biz)
        self.assertIn("unit_cost", m["critical_missing"])
        self.assertEqual(m["lines"][1], ("GST to the ATO", 0))

    def test_validation(self):
        for bad in ({"name": "x", "pitch": "p"}, {"name": "x", "pitch": "p", "price": 0},
                    {"name": "x", "pitch": "p", "price": 5, "type": "nope"}, {"name": "x", "pitch": "p", "price": 5, "returns_pct": 150}):
            with self.assertRaises(SystemExit):
                S.normalise_business(dict(bad))


GOOD = {"n": 1000, "buy": 0.10, "maybe": 0.10, "pass": 0.80}
CTRL_OK = {"n": 200, "buy": 0.01, "maybe": 0.02}
CTRL_BAD = {"n": 200, "buy": 0.40, "maybe": 0.10}
NO_ISSUES = {"compliance": {"ok": True, "data": {"issues": []}}}
SUB = S.margin(load("48-ai-crew-quoting.json"))
LOSS = S.margin(load("snack-box.json"))


class Verdicts(unittest.TestCase):
    def label(self, m=SUB, agg=GOOD, control=CTRL_OK, side=NO_ISSUES):
        return S.verdict(m, agg, control, side)["label"]

    def test_promising_never_says_go(self):
        v = S.verdict(SUB, GOOD, CTRL_OK, NO_ISSUES)
        self.assertEqual(v["label"], "PROMISING")
        self.assertIn("real people", v["next"])

    def test_each_gate(self):
        self.assertEqual(self.label(m=LOSS), "STOP")
        self.assertEqual(self.label(control=CTRL_BAD), "UNRELIABLE")
        self.assertEqual(self.label(control=None), "UNRELIABLE")
        self.assertEqual(self.label(agg={"n": 0}), "UNRELIABLE")
        self.assertEqual(self.label(agg=dict(GOOD, buy=0.01)), "FIX")
        serious = {"compliance": {"ok": True, "data": {"issues": [{"issue": "bad claim", "severity": 5, "confidence": "high", "check_with": "a lawyer"}]}}}
        self.assertEqual(self.label(side=serious), "HOLD")
        weak = {"compliance": {"ok": True, "data": {"issues": [{"issue": "x", "severity": 5, "confidence": "low", "check_with": ""}]}}}
        self.assertEqual(self.label(side=weak), "PROMISING")

    def test_priority_order(self):
        self.assertEqual(self.label(m=LOSS, control=CTRL_BAD), "STOP")   # maths beats a bad panel
        incomplete = S.margin(S.normalise_business({"name": "x", "pitch": "p", "price": 10}))
        self.assertEqual(self.label(m=incomplete, control=CTRL_BAD), "INCOMPLETE")

    def test_customer_worth_less_than_cost_is_stop(self):
        biz = load("48-ai-crew-quoting.json")
        biz["ad_cost_per_order"] = 5000
        self.assertEqual(self.label(m=S.margin(biz)), "STOP")


class Normalising(unittest.TestCase):
    def test_garbage_does_not_crash(self):
        r = S.normalise("red_team", {"failures": [{"reason": "x" * 999, "severity": "9", "fatal": 1}, "junk", None]})
        self.assertEqual((len(r["failures"]), r["failures"][0]["severity"], len(r["failures"][0]["reason"])), (1, 5, 300))
        self.assertEqual(S.normalise("compliance", {"issues": [{"issue": "a", "confidence": "SURE"}]})["issues"][0]["confidence"], "low")
        self.assertEqual(S.normalise("pricing_critic", {"verdict": "weird"})["verdict"], "unclear")
        for n in S.SPECIALISTS:
            S.normalise(n, {})
            S.normalise(n, {"x": 1})

    def test_parse_json(self):
        self.assertEqual(S.parse_json('ok {"a": 1} done'), {"a": 1})
        self.assertIsNone(S.parse_json("nothing"))


class Personas(unittest.TestCase):
    def test_business_panel(self):
        people = P.make_personas(300, 2, "business")
        self.assertTrue(all(p["kind"] == "business" and 25 <= p["age"] <= 64 for p in people))
        self.assertIn("Australia", P.persona_text(people[0]))
        self.assertIs(P.system_for(people[0]), P.SYSTEM_BUSINESS)
        self.assertIs(P.system_for(P.make_personas(1)[0]), P.SYSTEM)
        res = [P.mock_answer(p, {"name": "n", "price": 79}) | {"id": p["id"], "ok": True} for p in people]
        self.assertIn("trade", P.aggregate(res, people, [79])["segments"])


class EndToEnd(unittest.TestCase):
    def test_batch_mock_every_business(self):
        with tempfile.TemporaryDirectory() as d:
            S.main(["batch", EXAMPLES, "--mock", "--size", "300", "--out", d])
            rows = json.load(open(os.path.join(d, "ranking.json"), encoding="utf-8"))
            self.assertEqual(len(rows), 3)
            by = {r["name"]: r["verdict"] for r in rows}
            self.assertEqual(by["Healthy Snack Box"], "STOP")
            self.assertEqual(rows[-1]["verdict"], "STOP")           # worst ranked last
            report = open(os.path.join(d, "48-ai-crew-quoting", "report.html"), encoding="utf-8").read()
            for needle in ("MOCK RUN", "Money check", "Specialist reviewers", "Customer panel", "can never say"):
                self.assertIn(needle, report)
            self.assertTrue(os.path.getsize(os.path.join(d, "ranking.html")) > 0)

    def test_report_escapes_business_text(self):
        with tempfile.TemporaryDirectory() as d:
            biz = S.normalise_business(dict(json.load(open(os.path.join(EXAMPLES, "48-ai-crew-quoting.json"))), name="<img src=x onerror=alert(1)>"))
            S.run_business(biz, P.Config(mock=True), d, 60, 1, 4, 20, True)
            report = open(os.path.join(d, "report.html"), encoding="utf-8").read()
            self.assertNotIn("<img src=x", report)
            self.assertIn("&lt;img", report)

    def test_spend_guard_counts_everything(self):
        with self.assertRaises(SystemExit) as cm:
            S.main(["batch", EXAMPLES, "--size", "1000", "--yes"])
        msg = str(cm.exception)
        self.assertTrue("ANTHROPIC_API_KEY" in msg or "--max-calls 3618" in msg, msg)
        os.environ["ANTHROPIC_API_KEY"] = "k"
        try:
            with self.assertRaises(SystemExit) as cm:
                S.main(["batch", EXAMPLES, "--size", "1000", "--yes"])
            self.assertIn("--max-calls 3618", str(cm.exception))   # 3 x (1000 + 200 + 5 + 0 + 1)
            with self.assertRaises(SystemExit) as cm:
                S.main(["batch", EXAMPLES, "--size", "100"])
            self.assertIn("--yes", str(cm.exception))
        finally:
            del os.environ["ANTHROPIC_API_KEY"]


class RealPath(unittest.TestCase):
    def test_every_node_is_called_once_and_work_is_resumable(self):
        with Server() as s, tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "reviews.txt"), "w", encoding="utf-8") as fh:
                fh.write("\n".join("review number %d" % i for i in range(85)) + "\n")
            biz = S.normalise_business(dict(json.load(open(os.path.join(EXAMPLES, "48-ai-crew-quoting.json"))), reviews_file="reviews.txt"))
            self.assertEqual(S.planned_calls(biz, 30, 5, d), 30 + 5 + 5 + 3 + 1)
            cfg = P.Config(api_key="k", base_url=s.url, backoff=0.01)
            out = os.path.join(d, "o")
            sm = S.run_business(biz, cfg, out, 30, 1, 4, 5, True, d)
            self.assertEqual(FakeAPI.calls, 44)
            self.assertEqual(sm["verdict"]["label"], "UNRELIABLE")      # the fake says BUY to the bad offer too
            self.assertEqual(sm["specialists"]["reviews"]["reviews_read"], 85)
            self.assertFalse(sm["judge"]["ai"])                          # fake judge reply had no summary -> rule-based fallback
            S.run_business(biz, cfg, out, 30, 1, 4, 5, True, d)
            self.assertEqual(FakeAPI.calls, 45)                          # only the judge ran again


if __name__ == "__main__":
    unittest.main()
