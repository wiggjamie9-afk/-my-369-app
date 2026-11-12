#!/usr/bin/env python3
"""AI9 Week 1 harness - smoke test. Stdlib only, no network, no keys.

Proves the harness end-to-end in under a minute:
  1. task pack regenerates byte-identical (frozen contract intact)
  2. both runners execute the dev pack against the offline stub
  3. deterministic checks pass on the 20 generated DEV tasks (ai9 20/20;
     control 19/20 - DEV-M3 fails by design: the control has no checkpoint
     persistence). Hand-written dev tasks (TREND-*) must run and be recorded,
     but the canned stub's answers to them are not asserted - they need a
     real model.
  4. fault injection logs an attempted, successful recovery
  5. scoring + report run with no AI anywhere in the scoring path

Run from the project root:  python3 tests/smoke_test.py
Exit 0 = all green. Exit 1 = something broke; read the output.
"""
import json, os, shutil, subprocess, sqlite3, sys, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# The smoke test works in its own folder. It never touches results/, where the
# real benchmark registry lives ("nothing is deleted, ever").
RESULTS = os.path.join(ROOT, "results-smoke")


def wipe(path):
    """rmtree that tolerates slow fuse/overlay mounts releasing handles."""
    for _ in range(10):
        try:
            shutil.rmtree(path)
            return
        except OSError:
            time.sleep(0.3)
    shutil.rmtree(path, ignore_errors=True)


def sh(args):
    r = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                       env=dict(os.environ, AI9_RESULTS_DIR=RESULTS))
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit("FAILED: %s" % " ".join(args))
    return r.stdout


def main():
    print("[1/5] task pack integrity")
    manifest_before = json.load(open(os.path.join(ROOT, "taskpack", "pack.json")))
    sh([sys.executable, os.path.join("taskpack", "gen.py")])
    manifest_after = json.load(open(os.path.join(ROOT, "taskpack", "pack.json")))
    assert manifest_before == manifest_after, "pack regeneration changed hashes"
    assert manifest_after.get("frozen_count") == 40
    extra = manifest_after.get("dev_handwritten", [])
    dev_count = manifest_after.get("dev_count")
    assert dev_count == 20 + len(extra) == len(manifest_after["dev_sha256"])
    print("      pack stable: 40 frozen + %d dev (%d hand-written), hashes identical"
          % (dev_count, len(extra)))

    print("[2/5] dev runs, both systems (offline stub)")
    if os.path.exists(RESULTS):
        wipe(RESULTS)
    for system in ("ai9", "control"):
        sh([sys.executable, "-m", "ai9lab.run_benchmark",
            "--system", system, "--pack", "dev",
            "--repeat", "1", "--seed", "42"])

    print("[3/5] results database")
    con = sqlite3.connect(os.path.join(RESULTS, "results.db"))
    expect = {"ai9": (20, 20, []), "control": (19, 20, ["DEV-M3"])}
    for system, (ok_want, tot_want, fails_want) in expect.items():
        ran = con.execute("select count(*) from runs where system=? and status='done'",
                          (system,)).fetchone()[0]
        assert ran == dev_count, (system, "ran", ran, "of", dev_count)
        tot = con.execute("select count(*) from runs where system=? "
                          "and task_id like 'DEV-%'", (system,)).fetchone()[0]
        ok = con.execute("select count(*) from runs where system=? and task_id like 'DEV-%' "
                         "and verified_success=1", (system,)).fetchone()[0]
        fails = [r[0] for r in con.execute(
            "select task_id from runs where system=? and task_id like 'DEV-%' "
            "and verified_success=0", (system,))]
        assert (ok, tot, fails) == (ok_want, tot_want, fails_want), \
            (system, ok, tot, fails)
        print("      %s: %d/%d pass (expected fails: %s)"
              % (system, ok, tot, fails or "none"))

    print("[4/5] fault injection + recovery logging")
    sh([sys.executable, "-m", "ai9lab.run_benchmark",
        "--system", "ai9", "--pack", "dev", "--repeat", "1",
        "--seed", "97", "--tasks", "DEV-M1",
        "--inject", "corrupted_checkpoint"])
    row = con.execute("select recovery_json, verified_success from runs "
                      "where seed=97").fetchone()
    rec = json.loads(row[0])
    assert rec["attempted"] is True and rec["result"] == "success", rec
    assert row[1] == 1
    print("      corrupted checkpoint -> immune rebuild logged, run passed")

    print("[5/5] scoring + report (no AI in scoring path)")
    sh([sys.executable, "-m", "ai9lab.score",
        "--db", os.path.join(RESULTS, "results.db"),
        "--out", os.path.join(RESULTS, "scores.json")])
    sh([sys.executable, "-m", "ai9lab.report",
        "--title", "AI9 smoke test",
        "--scores", os.path.join(RESULTS, "scores.json"),
        "--out", os.path.join(RESULTS, "report.md")])
    scores = json.load(open(os.path.join(RESULTS, "scores.json")))
    assert scores["safety_snapshot"]["unauthorised_external_actions"] == 0
    assert scores["safety_snapshot"]["gate_unauthorised_zero"] is True
    print("      safety gate: unauthorised external actions = 0  PASS")

    print("\nSMOKE TEST: ALL GREEN")


if __name__ == "__main__":
    main()
