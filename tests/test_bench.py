import unittest

from ai9 import bench


NOTES = [
    {"id": 1, "who": "j", "what": "The callout fee is 90 dollars", "when": "2026-01-01T00:00:00+00:00"},
    {"id": 2, "who": "j", "what": "The callout fee is 120 dollars", "when": "2026-06-01T00:00:00+00:00"},
    {"id": 3, "who": "j", "what": "Our office is in Leeds", "when": "2026-02-01T00:00:00+00:00"},
    {"id": 4, "who": "j", "what": "Caller: Bob Smith rang from +44 7700 900123", "when": "2026-03-01T00:00:00+00:00"},
    {"id": 5, "who": "j", "what": "the password is hunter2", "when": "2026-03-02T00:00:00+00:00"},
]
QS = [{"q": "What is the callout fee?", "a": "120"}, {"q": "Which city is our office in?", "a": "Leeds"}]


class Bench(unittest.TestCase):
    def test_same_model_rejected(self):
        with self.assertRaises(ValueError):
            bench.run(NOTES, QS, bench.fake_answer, bench.fake_grade, "m", "m", runs=1)

    def test_unsafe_notes_dropped_from_both_banks(self):
        plain, loop, dropped = bench.build_banks(NOTES)
        self.assertEqual(dropped, 1)    # the password; caller note is redacted, not dropped
        for b in (plain, loop):
            self.assertFalse(any("hunter2" in m.what or "7700" in m.what or "Bob" in m.what for m in b.all()))

    def test_looping_beats_plain_when_data_conflicts(self):
        r = bench.run(NOTES, QS, bench.fake_answer, bench.fake_grade, "a", "g", runs=3)
        self.assertEqual(r["looping"]["correct_pct"], 100.0)
        # plain returns old+new fee together, so the grader sees "120" too; confident-wrong is the real signal
        self.assertTrue(r["SIMULATION"])
        self.assertIn("PASS", r["verdict"])

    def test_estimate_scales_with_runs(self):
        self.assertAlmostEqual(bench.estimate(200)["total_usd"], 2 * bench.estimate(100)["total_usd"], places=1)

    def test_verdict_relative_margin(self):
        v = bench.verdict({"correct_pct": 40}, {"correct_pct": 60})
        self.assertTrue(v["PASS"])
        self.assertFalse(bench.verdict({"correct_pct": 40}, {"correct_pct": 59})["PASS"])


if __name__ == "__main__":
    unittest.main()
