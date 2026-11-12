"""Tests for organism.py. Run: python3 -m unittest test_organism -v"""

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

import organism as org


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.store = org.Store(os.path.join(self.dir, "data"))
        self.out = os.path.join(self.dir, "status.json")

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, name, text):
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path


class Parsing(Base):
    def test_json_list(self):
        runs = org.parse_results(json.dumps([
            {"task": "TREND-1", "model": "m", "status": "PASS", "secs": 13.1},
            {"task": "TREND-2", "model": "m", "status": "fail", "secs": 30, "error": "timed  out\nafter 30s"},
        ]))
        self.assertEqual([r["status"] for r in runs], ["PASS", "FAIL"])
        self.assertEqual(runs[1]["reason"], "timed out after 30s")
        self.assertNotIn("reason", runs[0])

    def test_wrapped_object_inherits_model(self):
        runs = org.parse_results(json.dumps(
            {"model": "big-one", "results": [{"id": "A", "passed": True, "duration_ms": 1500}]}))
        self.assertEqual(runs, [{"task": "A", "model": "big-one", "status": "PASS", "secs": 1.5, "at": None}])

    def test_task_keyed_object(self):
        runs = org.parse_results(json.dumps({"T1": {"ok": False, "elapsed": 2}, "T2": True}), default_model="x")
        self.assertEqual([(r["task"], r["status"], r["model"]) for r in runs],
                         [("T1", "FAIL", "x"), ("T2", "PASS", "x")])

    def test_json_lines_skips_broken_line(self):
        text = '{"task":"A","status":"PASS"}\nnot json\n{"task":"B","result":"error"}\n'
        self.assertEqual([r["status"] for r in org.parse_results(text)], ["PASS", "FAIL"])

    def test_csv(self):
        runs = org.parse_results("Task,Model,Result,Seconds\nA,m1,pass,9.2\nB,m1,FAILED,11\n")
        self.assertEqual([(r["task"], r["status"], r["secs"]) for r in runs],
                         [("A", "PASS", 9.2), ("B", "FAIL", 11.0)])

    def test_time_field_is_duration_or_timestamp(self):
        a = org.normalise({"task": "A", "status": "pass", "time": 4.5})
        b = org.normalise({"task": "A", "status": "pass", "time": "2026-11-12T21:40:00Z"})
        self.assertEqual((a["secs"], a["at"]), (4.5, None))
        self.assertEqual((b["secs"], b["at"]), (None, "2026-11-12T21:40:00Z"))

    def test_rows_that_are_not_runs_are_dropped(self):
        self.assertEqual(org.parse_results(json.dumps([{"note": "hello"}, 3, None])), [])
        self.assertEqual(org.parse_results(""), [])

    def test_timestamps(self):
        self.assertEqual(org.parse_time(1794519600), "2026-11-12T21:40:00Z")
        self.assertEqual(org.parse_time(1794519600000), "2026-11-12T21:40:00Z")
        self.assertEqual(org.parse_time("2026-11-12T22:40:00+01:00"), "2026-11-12T21:40:00Z")
        self.assertIsNone(org.parse_time("yesterday"))
        self.assertIsNone(org.parse_time(13.1))


class Building(Base):
    def batch(self, name, rows):
        return org.ingest(self.store, self.write(name, json.dumps(rows)))

    def test_empty_archive_is_valid_and_resting(self):
        status, _ = org.build(self.store, self.out)
        self.assertEqual([o["state"] for o in status["organs"]], ["rest"] * 5)
        self.assertEqual((status["models"], status["runs"]), ([], []))

    def test_scores_come_from_each_models_latest_batch(self):
        day1 = [{"task": "T%d" % i, "model": "a", "status": "PASS" if i < 20 else "FAIL",
                 "secs": 10, "at": "2026-11-10T10:00:00Z"} for i in range(25)]
        day2 = [{"task": "T%d" % i, "model": "a", "status": "PASS" if i < 24 else "FAIL",
                 "secs": 9.2, "at": "2026-11-11T10:00:00Z"} for i in range(25)]
        self.batch("d2.json", day2)          # ingested out of order on purpose
        self.batch("d1.json", day1)
        status, _ = org.build(self.store, self.out)
        m = status["models"][0]
        self.assertEqual((m["pass"], m["total"], m["avg_sec"]), (24, 25, 9.2))
        self.assertEqual(len(m["tasks"]), 25)
        self.assertEqual(m["tasks"][-1], {"task": "T24", "status": "FAIL"})
        self.assertEqual([(h["pass"], h["total"]) for h in status["history"]], [(20, 25), (24, 25)])
        self.assertEqual(status["updated"], "2026-11-11T10:00:00Z")
        self.assertEqual(status["runs"][-1]["at"], "2026-11-11T10:00:00Z")   # newest run is last
        self.assertEqual(status["totals"], {"batches": 2, "runs": 50})

    def test_history_tracks_the_headline_across_models(self):
        self.batch("a.json", [{"task": "A", "model": "a", "status": "PASS", "at": "2026-11-10T10:00:00Z"}])
        self.batch("b.json", [{"task": "A", "model": "b", "status": "FAIL", "at": "2026-11-10T11:00:00Z"}])
        self.batch("a2.json", [{"task": "A", "model": "a", "status": "FAIL", "at": "2026-11-11T10:00:00Z"}])
        history = org.build(self.store, self.out)[0]["history"]
        self.assertEqual([(h["pass"], h["total"], h["models"]) for h in history], [(1, 1, 1), (1, 2, 2), (0, 2, 2)])

    def test_models_ranked_by_pass_rate_then_speed(self):
        self.batch("b.json", [
            {"task": "A", "model": "slow", "status": "PASS", "secs": 20},
            {"task": "A", "model": "fast", "status": "PASS", "secs": 5},
            {"task": "A", "model": "weak", "status": "FAIL", "secs": 1},
        ])
        status, _ = org.build(self.store, self.out)
        self.assertEqual([m["name"] for m in status["models"]], ["fast", "slow", "weak"])

    def test_ingest_is_idempotent(self):
        rows = [{"task": "A", "model": "m", "status": "PASS"}]
        self.assertEqual(self.batch("x.json", rows)[1], 1)
        self.assertEqual(self.batch("copy.json", rows)[1], 0)
        self.assertEqual(len(self.store.runs()), 1)

    def test_ingest_rejects_file_without_runs(self):
        with self.assertRaises(ValueError):
            org.ingest(self.store, self.write("junk.json", '{"hello": 1}'))
        self.assertEqual(self.store.batches(), [])

    def test_max_runs_keeps_the_newest(self):
        self.batch("b.json", [{"task": "T%d" % i, "model": "m", "status": "PASS"} for i in range(10)])
        status, _ = org.build(self.store, self.out, max_runs=3)
        self.assertEqual([r["task"] for r in status["runs"]], ["T7", "T8", "T9"])
        self.assertEqual(status["models"][0]["total"], 10)

    def test_rebuild_without_change_does_not_rewrite(self):
        self.batch("b.json", [{"task": "A", "model": "m", "status": "PASS", "at": "2026-11-11T10:00:00Z"}])
        self.assertTrue(org.build(self.store, self.out)[1])
        self.assertFalse(org.build(self.store, self.out)[1])
        with open(self.out, encoding="utf-8") as fh:
            org.validate(json.load(fh))

    def test_derived_organs_only_claim_what_the_archive_shows(self):
        self.batch("b.json", [{"task": "A", "model": "m", "status": "PASS", "secs": 2},
                              {"task": "B", "model": "m", "status": "FAIL", "secs": 4}])
        organs = {o["id"]: o for o in org.build(self.store, self.out)[0]["organs"]}
        self.assertEqual(organs["sense"]["state"], "rest")
        self.assertEqual(organs["decide"]["state"], "rest")
        self.assertEqual(organs["verify"]["note"], "1 pass · 1 fail judged")
        self.assertEqual(organs["model"]["state"], "ok")

    def test_heartbeat_overrides_and_expires(self):
        self.store.beat("sense", "busy", "scanning", ttl=60)
        status = org.build_status(self.store)
        sense = status["organs"][0]
        self.assertEqual((sense["state"], sense["note"], sense["source"]), ("busy", "scanning", "heartbeat"))
        later = datetime.now(timezone.utc) + timedelta(hours=3)
        sense = org.build_status(self.store, now=later)["organs"][0]
        self.assertEqual(sense["state"], "down")
        self.assertIn("no heartbeat for 3 h", sense["note"])

    def test_cli_round_trip(self):
        path = self.write("r.csv", "task,model,status,secs\nA,m,PASS,1\nB,m,FAIL,2\n")
        args = ["--store", self.store.path, "--out", self.out]
        self.assertEqual(org.main(["ingest", path] + args), 0)
        self.assertEqual(org.main(["beat", "decide", "ok", "idle"] + args), 0)
        self.assertEqual(org.main(["ingest", os.path.join(self.dir, "missing.json")] + args), 2)
        with open(self.out, encoding="utf-8") as fh:
            status = org.validate(json.load(fh))
        self.assertEqual(status["models"][0]["pass"], 1)
        self.assertEqual(status["organs"][2]["state"], "ok")


if __name__ == "__main__":
    unittest.main()
