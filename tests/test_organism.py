"""Tests for organism.py. Run: python3 tests/test_organism.py"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import organism as org


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.store = org.Store(os.path.join(self.dir, "data"))
        self.out = os.path.join(self.dir, "status.json")
        self.here, org.HERE = org.HERE, self.dir       # never discover the repo's own results database

    def tearDown(self):
        org.HERE = self.here
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


class Watching(Base):
    def watcher(self, **kw):
        self.results = os.path.join(self.dir, "results")
        os.makedirs(self.results, exist_ok=True)
        self.log = []
        return org.Watcher(self.store, self.out, [self.dir], settle=0, log=self.log.append, **kw)

    def drop(self, name, rows):
        path = os.path.join(self.results, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(rows, fh)
        return path

    def test_new_files_are_archived_and_status_rebuilt(self):
        w = self.watcher()
        self.assertEqual(w.scan(), 0)
        self.drop("day1.json", [{"task": "A", "model": "m", "status": "PASS"}])
        self.assertEqual(w.scan(), 1)
        self.assertEqual(w.scan(), 0)                      # nothing new on the next look
        with open(self.out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["models"][0]["pass"], 1)

    def test_changed_file_is_read_again(self):
        w = self.watcher()
        path = self.drop("live.json", [{"task": "A", "model": "m", "status": "PASS"}])
        w.scan()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([{"task": "A", "model": "m", "status": "PASS"},
                       {"task": "B", "model": "m", "status": "FAIL"}], fh)
        os.utime(path, (2000000000, 2000000000))
        self.assertEqual(w.scan(), 2)
        with open(self.out, encoding="utf-8") as fh:
            status = json.load(fh)
        self.assertEqual(status["models"][0]["total"], 2)
        self.assertEqual(len(status["runs"]), 2)           # the grown file replaced its earlier self
        self.assertEqual(len(status["history"]), 1)

    def test_overwritten_file_with_different_runs_is_a_new_batch(self):
        w = self.watcher()
        path = self.drop("results.json", [{"task": "A", "model": "m", "status": "FAIL", "at": "2026-11-10T10:00:00Z"}])
        w.scan()
        with open(path, "w", encoding="utf-8") as fh:
            json.dump([{"task": "A", "model": "m", "status": "PASS", "at": "2026-11-11T10:00:00Z"}], fh)
        os.utime(path, (2000000000, 2000000000))
        w.scan()
        with open(self.out, encoding="utf-8") as fh:
            status = json.load(fh)
        self.assertEqual([(h["pass"], h["total"]) for h in status["history"]], [(0, 1), (1, 1)])
        self.assertEqual(len(status["runs"]), 2)

    def test_never_eats_its_own_output_or_archive(self):
        w = self.watcher()
        self.drop("day1.json", [{"task": "A", "model": "m", "status": "PASS"}])
        w.scan()                                           # writes status.json and data/ inside the watched folder
        w.seen.clear()
        self.assertEqual(w.scan(), 0)
        self.assertEqual(len(self.store.batches()), 1)
        copy = self.write("copy-of-status.json", open(self.out, encoding="utf-8").read())
        with self.assertRaises(ValueError):
            org.ingest(self.store, copy)

    def test_unreadable_file_is_reported_once_and_skipped(self):
        w = self.watcher()
        self.drop("notes.json", {"hello": "world"})
        self.drop("good.json", [{"task": "A", "model": "m", "status": "PASS"}])
        self.assertEqual(w.scan(), 1)
        w.scan()
        self.assertEqual(len([m for m in self.log if m.startswith("skipped")]), 1)

    def test_file_still_being_written_waits(self):
        w = self.watcher()
        w.settle = 3600
        self.drop("fresh.json", [{"task": "A", "model": "m", "status": "PASS"}])
        self.assertEqual(w.scan(), 0)
        w.settle = 0
        self.assertEqual(w.scan(), 1)


class Harness(Base):
    """Reading the AI9 validation harness's sqlite registry."""

    SCHEMA = """CREATE TABLE runs(run_id TEXT PRIMARY KEY, task_id TEXT, task_version TEXT, pack TEXT,
      system TEXT, config_json TEXT, model TEXT, model_backend TEXT, seed INTEGER, status TEXT,
      repeat_index INTEGER, ts_queued INTEGER, ts_start INTEGER, ts_end INTEGER, budget_json TEXT,
      usage_json TEXT, verified_success INTEGER, checks_json TEXT, failure_type TEXT,
      human_interventions INTEGER DEFAULT 0, recovery_json TEXT, claims_total INTEGER DEFAULT 0,
      claims_sourced INTEGER DEFAULT 0, ext_actions_requested INTEGER DEFAULT 0,
      ext_actions_executed INTEGER DEFAULT 0, packet_count INTEGER DEFAULT 0,
      duplicate_actions INTEGER DEFAULT 0, output_path TEXT, event_log_path TEXT,
      reviewer_score TEXT, notes TEXT)"""
    T0 = 1794500000

    def make(self, rows, folder="results"):
        import sqlite3
        os.makedirs(os.path.join(self.dir, folder), exist_ok=True)
        path = os.path.join(self.dir, folder, "results.db")
        con = sqlite3.connect(path)
        con.execute(self.SCHEMA)
        for i, r in enumerate(rows):
            row = {"run_id": "run-%d" % i, "pack": "dev", "model": "flint", "seed": 42, "status": "done",
                   "repeat_index": 0, "ts_queued": self.T0, "ts_start": self.T0 + i, "ts_end": self.T0 + i + 9,
                   "verified_success": 1, "claims_total": 4, "claims_sourced": 3, "packet_count": 8,
                   "recovery_json": json.dumps({"attempted": False})}
            row.update(r)
            con.execute("INSERT INTO runs(%s) VALUES(%s)" % (",".join(row), ",".join("?" * len(row))),
                        list(row.values()))
        con.commit()
        con.close()
        return path

    def rows(self):
        return [
            {"task_id": "DEV-R1", "system": "ai9"},
            {"task_id": "DEV-M3", "system": "ai9", "recovery_json": json.dumps({"attempted": True, "result": "success"})},
            {"task_id": "TREND-1", "system": "ai9", "verified_success": 0, "failure_type": "checks_failed",
             "checks_json": json.dumps([{"ok": True, "detail": "a"}, {"ok": False, "detail": "contains_any ['trigger']"}])},
            {"task_id": "DEV-R1", "system": "control"},
            {"task_id": "DEV-M3", "system": "control", "verified_success": 0, "failure_type": "checks_failed"},
            {"task_id": "TREND-1", "system": "control", "status": "failed", "verified_success": None,
             "failure_type": "runner_crash", "notes": "connection refused"},
        ]

    def test_scores_match_the_harness_definition(self):
        status = org.validate(org.harness_status(org.read_harness(self.make(self.rows())), {}))
        got = {m["name"]: (m["pass"], m["total"], m["avg_sec"]) for m in status["models"]}
        self.assertEqual(got, {"ai9 · flint": (2, 3, 9.0), "control · flint": (1, 2, 9.0)})   # crash not scored
        self.assertEqual(status["headline"], {"label": "ai9 · dev pack", "pass": 2, "total": 3})
        self.assertEqual([m["name"] for m in status["models"]][0], "ai9 · flint")
        self.assertEqual(status["history"], [{"at": status["history"][0]["at"], "pass": 2, "total": 3}])
        self.assertEqual(status["totals"], {"runs": 6, "pending": 0, "crashed": 1})

    def test_run_log_carries_reasons_and_crashes(self):
        runs = org.harness_status(org.read_harness(self.make(self.rows())), {})["runs"]
        by = {(r["task"], r["model"]): r for r in runs}
        self.assertEqual(by[("TREND-1", "ai9 · flint")]["reason"], "check failed: contains_any ['trigger']")
        self.assertEqual(by[("TREND-1", "control · flint")]["status"], "CRASH")
        self.assertEqual(by[("TREND-1", "control · flint")]["reason"], "runner crash: connection refused")
        self.assertNotIn("reason", by[("DEV-R1", "ai9 · flint")])
        self.assertEqual(by[("DEV-R1", "ai9 · flint")]["secs"], 9)

    def test_organs_read_the_harness_measurements(self):
        organs = {o["id"]: (o["state"], o["note"]) for o in
                  org.harness_status(org.read_harness(self.make(self.rows())), {})["organs"]}
        self.assertEqual(organs["sense"], ("ok", "9 of 12 claims carry a source"))
        self.assertEqual(organs["decide"], ("ok", "0 external requests · 0 executed"))
        self.assertEqual(organs["verify"], ("ok", "2 of 3 runs verified · 1 of 1 recoveries"))
        self.assertEqual(organs["model"][0], "ok")

    def test_safety_and_recovery_failures_turn_organs_down(self):
        rows = self.rows()
        rows[0]["ext_actions_executed"] = 1
        rows[1]["recovery_json"] = json.dumps({"attempted": True, "result": "failed: boom"})
        organs = {o["id"]: o["state"] for o in org.harness_status(org.read_harness(self.make(rows)), {})["organs"]}
        self.assertEqual((organs["decide"], organs["verify"]), ("down", "down"))

    def test_running_rows_mean_busy_but_stale_ones_do_not(self):
        rows = self.rows() + [{"task_id": "DEV-N1", "system": "ai9", "status": "running",
                               "verified_success": None, "ts_end": None, "ts_start": self.T0 + 50}]
        data = org.read_harness(self.make(rows))
        soon = datetime.fromtimestamp(self.T0 + 60, timezone.utc)
        later = datetime.fromtimestamp(self.T0 + 7200, timezone.utc)
        model = org.harness_status(data, {}, now=soon)["organs"][1]
        self.assertEqual((model["state"], model["note"]), ("busy", "1 run in progress"))
        model = org.harness_status(data, {}, now=later)["organs"][1]
        self.assertEqual(model["state"], "ok")
        self.assertIn("1 left queued by an interrupted batch", model["note"])

    def test_packs_are_never_blended(self):
        rows = self.rows() + [{"task_id": "RES-01", "system": "ai9", "pack": "frozen", "ts_end": self.T0 + 500}]
        status = org.harness_status(org.read_harness(self.make(rows)), {})
        self.assertIn("ai9 · flint · frozen", [m["name"] for m in status["models"]])
        self.assertEqual(status["headline"], {"label": "ai9 · frozen pack", "pass": 1, "total": 1})

    def taskpack(self, tamper=False):
        import hashlib
        folder = os.path.join(self.dir, "taskpack")
        tasks = {"dev": [("DEV-R1", "research", "Cite one source"), ("DEV-M3", "memory", "Persist checkpoint"),
                         ("TREND-1", "routines", "Agent workflow builder")], "frozen": []}
        manifest = {"version": "1.0.0"}
        for pack, items in tasks.items():
            os.makedirs(os.path.join(folder, pack))
            hashes = {}
            for tid, organ, title in items:
                blob = json.dumps({"task_id": tid, "organ": organ, "title": title})
                with open(os.path.join(folder, pack, tid.lower() + ".json"), "w") as fh:
                    fh.write(blob + "\n")
                hashes[tid.lower() + ".json"] = hashlib.sha256(blob.encode()).hexdigest()
            manifest[pack + "_sha256"] = hashes
        with open(os.path.join(folder, "pack.json"), "w") as fh:
            json.dump(manifest, fh)
        if tamper:
            with open(os.path.join(folder, "dev", "trend-1.json"), "a") as fh:
                fh.write(" ")
            with open(os.path.join(folder, "dev", "sneaked-in.json"), "w") as fh:
                fh.write("{}")

    def status(self, rows=None, **kw):
        path = self.make(rows or self.rows())
        return org.validate(org.harness_status(org.read_harness(path), {}, db=path, **kw))

    def test_task_pack_gives_titles_and_a_per_organ_breakdown(self):
        self.taskpack()
        status = self.status()
        self.assertEqual(status["pack"], {"ok": True, "problems": [], "version": "1.0.0", "frozen": 0, "dev": 3})
        self.assertEqual({r["task"]: r.get("title") for r in status["runs"]}["TREND-1"], "Agent workflow builder")
        self.assertEqual(status["breakdown"], [
            {"organ": "research", "ai9": {"pass": 1, "total": 1}, "control": {"pass": 1, "total": 1}},
            {"organ": "memory", "ai9": {"pass": 1, "total": 1}, "control": {"pass": 0, "total": 1}},
            {"organ": "routines", "ai9": {"pass": 0, "total": 1}, "control": {"pass": 0, "total": 0}},
        ])

    def test_a_changed_task_pack_is_flagged_and_turns_verify_down(self):
        self.taskpack(tamper=True)
        status = self.status()
        self.assertFalse(status["pack"]["ok"])
        self.assertEqual(status["pack"]["problems"], ["dev/sneaked-in.json is not in the manifest",
                                                      "dev/trend-1.json differs from the manifest"])
        verify = status["organs"][3]
        self.assertEqual(verify["state"], "down")
        self.assertIn("2 problems", verify["note"])

    def test_scores_json_is_passed_through_and_staleness_is_caught(self):
        path = self.make(self.rows())
        scores = {"systems": {"ai9": {"runs": 3, "verified_success_rate_pct": 66.67, "cost_per_success_usd": 0.01},
                              "control": {"runs": 2, "verified_success_rate_pct": 50.0, "cost_per_success_usd": 0.02,
                                          "recovery_rate_pct": None}}}
        with open(os.path.join(self.dir, "results", "scores.json"), "w") as fh:
            json.dump(scores, fh)
        cmp = org.harness_status(org.read_harness(path), {}, db=path)["comparison"]
        self.assertFalse(cmp["stale"])
        self.assertEqual(cmp["rows"][0], {"metric": "Verified success", "unit": "%", "better": "higher",
                                          "control": 50.0, "ai9": 66.67})
        self.assertEqual([r["metric"] for r in cmp["rows"]], ["Verified success", "Cost per success"])
        scores["systems"]["ai9"]["runs"] = 2                     # a run finished after score.py last ran
        with open(os.path.join(self.dir, "results", "scores.json"), "w") as fh:
            json.dump(scores, fh)
        self.assertTrue(org.harness_status(org.read_harness(path), {}, db=path)["comparison"]["stale"])

    def test_measured_duration_is_preferred_over_whole_seconds(self):
        import sqlite3
        path = self.make(self.rows())
        con = sqlite3.connect(path)
        con.execute("ALTER TABLE runs ADD COLUMN duration_s REAL")
        con.execute("UPDATE runs SET duration_s=0.25 WHERE task_id='DEV-R1' AND system='ai9'")
        con.commit(); con.close()
        runs = org.harness_status(org.read_harness(path), {})["runs"]
        by = {(r["task"], r["model"]): r["secs"] for r in runs}
        self.assertEqual((by[("DEV-R1", "ai9 · flint")], by[("DEV-M3", "ai9 · flint")]), (0.25, 9))

    def test_doctor_reports_what_needs_fixing(self):
        self.write("index.html", "<title>console</title>")
        self.taskpack(tamper=True)
        self.store.db = self.make(self.rows())
        lines, failures = org.doctor(self.store, self.out, 0)
        text = "\n".join(lines)
        self.assertEqual(failures, 1)
        self.assertIn("FAIL task pack does not match its manifest", text)
        self.assertIn("5 completed, 1 crashed, 0 queued or running", text)
        self.assertIn("warn no scores.json yet", text)
        self.assertNotIn("FAIL status.json", text)

    def test_watcher_picks_up_a_database_created_after_it_started(self):
        log = []
        w = org.Watcher(self.store, self.out, [self.dir], settle=0, log=log.append)
        w.scan()
        self.assertIsNone(self.store.db)
        path = self.make(self.rows())
        w.scan()
        self.assertEqual(self.store.db, path)
        with open(self.out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["source"], "harness")

    def test_database_is_found_left_untouched_and_wins(self):
        path = self.make(self.rows())
        before = open(path, "rb").read()
        self.assertEqual(org.find_harness_db([self.dir]), path)
        self.assertEqual(org.find_harness_db([os.path.join(self.dir, "results")]), path)
        self.assertIsNone(org.find_harness_db([os.path.join(self.dir, "data")]))
        args = ["--store", self.store.path, "--out", self.out]
        self.assertEqual(org.main(["build", "--db", path] + args), 0)
        with open(self.out, encoding="utf-8") as fh:
            self.assertEqual(org.validate(json.load(fh))["source"], "harness")
        self.assertEqual(open(path, "rb").read(), before)
        self.assertEqual(org.main(["build", "--db", self.write("x.db", "junk")] + args), 2)

    def test_watcher_follows_the_database_and_ignores_harness_files(self):
        import sqlite3
        path = self.make(self.rows())
        with open(os.path.join(self.dir, "results", "scores.json"), "w") as fh:
            json.dump([{"task": "A", "status": "PASS"}], fh)       # looks like results, but is the harness's own
        self.store.db = path
        log = []
        self.write("pack.json", json.dumps({"frozen_count": 40}))   # harness files above the database too
        w = org.Watcher(self.store, self.out, [self.dir], settle=0, log=log.append)
        self.assertEqual(w.scan(), 0)
        self.assertEqual(self.store.batches(), [])
        self.assertEqual(log, [])
        with open(self.out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["headline"]["total"], 3)
        con = sqlite3.connect(path)
        con.execute("UPDATE runs SET verified_success=1 WHERE task_id='TREND-1' AND system='ai9'")
        con.commit(); con.close()
        os.utime(path, (2000000000, 2000000000))
        w.scan()
        with open(self.out, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["headline"]["pass"], 3)


class Serving(Base):
    def test_only_the_console_is_served_and_changes_are_pushed(self):
        import functools
        import threading
        import urllib.error
        import urllib.request
        from http.server import ThreadingHTTPServer

        self.write("index.html", "<!doctype html><title>console</title>")
        self.write("secret.txt", "not for serving")
        org.ingest(self.store, self.write("r.json", json.dumps([{"task": "A", "model": "m", "status": "PASS"}])))
        org.build(self.store, self.out)
        org.ConsoleHandler.store, org.ConsoleHandler.out = self.store, self.out
        org.ConsoleHandler.closing = threading.Event()
        server = ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(org.ConsoleHandler, directory=self.dir))
        server.block_on_close = False
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % server.server_address[1]
        try:
            self.assertIn(b"console", urllib.request.urlopen(base + "/", timeout=5).read())
            status = json.load(urllib.request.urlopen(base + "/status.json", timeout=5))
            self.assertEqual(status["models"][0]["pass"], 1)
            page = urllib.request.urlopen(base + "/", timeout=5)
            self.assertIn("connect-src 'self'", page.headers["Content-Security-Policy"])
            self.assertEqual(page.headers["X-Content-Type-Options"], "nosniff")
            for path in ("/secret.txt", "/data/runs.jsonl", "/r.json", "/../organism.py"):
                with self.assertRaises(urllib.error.HTTPError):
                    urllib.request.urlopen(base + path, timeout=5)

            feed = urllib.request.urlopen(base + "/events", timeout=5)
            self.assertEqual(feed.headers["Content-Type"], "text/event-stream")
            self.assertEqual(feed.readline(), b"event: status\n")       # first nudge on connect
            feed.readline(); feed.readline()
            self.store.beat("sense", "ok", "awake", None)
            org.build(self.store, self.out)
            self.assertEqual(feed.readline(), b"event: status\n")       # pushed after the change
        finally:
            org.ConsoleHandler.closing.set()
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
