"""Tests for the harness changes made when the console was merged in.
Run: python3 tests/test_harness.py   (standard library only, no network, no keys)"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from ai9lab import core, run_benchmark
from ai9lab.db import DB


class PackCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pack = os.path.join(self.tmp.name, "taskpack")
        shutil.copytree(os.path.join(ROOT, "taskpack"), self.pack,
                        ignore=shutil.ignore_patterns("*.bak-*", "__pycache__"))
        self.real, run_benchmark.TASKPACK = run_benchmark.TASKPACK, self.pack

    def tearDown(self):
        run_benchmark.TASKPACK = self.real
        self.tmp.cleanup()

    def test_shipped_pack_is_intact_and_covers_every_task_file(self):
        self.assertEqual(run_benchmark.verify_pack("dev"), [])
        self.assertEqual(run_benchmark.verify_pack("frozen"), [])
        manifest = json.load(open(os.path.join(self.pack, "pack.json")))
        self.assertEqual((manifest["frozen_count"], manifest["dev_count"]), (40, 25))
        self.assertEqual(manifest["dev_handwritten"], ["trend-%d.json" % i for i in range(1, 6)])

    def test_changed_added_and_missing_tasks_are_all_caught(self):
        with open(os.path.join(self.pack, "frozen", "res-01.json"), "a") as fh:
            fh.write(" ")
        with open(os.path.join(self.pack, "dev", "trend-9.json"), "w") as fh:
            fh.write("{}")
        os.remove(os.path.join(self.pack, "dev", "dev-r1.json"))
        self.assertEqual(run_benchmark.verify_pack("frozen"), ["frozen/res-01.json differs from the manifest"])
        self.assertEqual(run_benchmark.verify_pack("dev"), ["dev/trend-9.json is not in the manifest",
                                                            "dev/dev-r1.json is in the manifest but missing"])

    def test_benchmark_refuses_to_run_on_a_changed_pack(self):
        work = os.path.join(self.tmp.name, "repo")
        shutil.copytree(ROOT, work, ignore=shutil.ignore_patterns(
            "results*", ".git", "__pycache__", "organism-data", "*.bak-*"))
        with open(os.path.join(work, "taskpack", "dev", "trend-1.json"), "a") as fh:
            fh.write(" ")
        r = subprocess.run([sys.executable, "-m", "ai9lab.run_benchmark", "--system", "ai9", "--pack", "dev",
                            "--tasks", "DEV-R1"], cwd=work, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("TASK PACK CHECK FAILED", r.stdout)
        self.assertFalse(os.path.exists(os.path.join(work, "results", "results.db")))

    def test_hash_rule_matches_the_generator(self):
        manifest = json.load(open(os.path.join(self.pack, "pack.json")))
        for pack in ("frozen", "dev"):
            for fn, want in manifest[pack + "_sha256"].items():
                self.assertEqual(core.task_file_hash(os.path.join(self.pack, pack, fn)), want, fn)


class Registry(unittest.TestCase):
    def test_older_databases_gain_the_duration_column_without_losing_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "results.db")
            con = sqlite3.connect(path)
            con.execute("CREATE TABLE runs(run_id TEXT PRIMARY KEY, task_id TEXT, status TEXT, verified_success INTEGER)")
            con.execute("INSERT INTO runs VALUES('run-old', 'DEV-R1', 'done', 1)")
            con.commit(); con.close()
            db = DB(path)
            cols = [r[1] for r in db.conn.execute("PRAGMA table_info(runs)")]
            rows = db.conn.execute("SELECT run_id, duration_s FROM runs").fetchall()
            db.close()
            self.assertIn("duration_s", cols)
            self.assertEqual(rows, [("run-old", None)])

    def test_results_folder_can_be_redirected_for_tests(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, AI9_RESULTS_DIR=os.path.join(tmp, "elsewhere"))
            r = subprocess.run([sys.executable, "-m", "ai9lab.run_benchmark", "--system", "ai9", "--pack", "dev",
                                "--tasks", "DEV-R1", "--seed", "123456"], cwd=ROOT, env=env,
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            con = sqlite3.connect(os.path.join(tmp, "elsewhere", "results.db"))
            row = con.execute("SELECT verified_success, duration_s FROM runs").fetchone()
            con.close()
            self.assertEqual(row[0], 1)
            self.assertIsInstance(row[1], float)


if __name__ == "__main__":
    unittest.main()
