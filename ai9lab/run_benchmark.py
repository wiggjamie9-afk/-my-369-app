#!/usr/bin/env python3
"""AI9 Lab - benchmark CLI.

Usage:
  python3 -m ai9lab.run_benchmark --system control --pack dev --tasks DEV-R1 DEV-R2
  python3 -m ai9lab.run_benchmark --system ai9 --pack frozen --repeat 3 --seed 42
  python3 -m ai9lab.run_benchmark --system ai9 --pack dev --inject corrupted_checkpoint

Laws enforced here:
  - frozen pack runs are marked benchmark=1 and warn loudly (tune on dev only)
  - permitted external actions come from the task file (Week 1: none)
  - the registry is persistent: a crashed batch resumes where it stopped
"""
import argparse, json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai9lab import core, control_runner, ai9_runner
from ai9lab.db import DB

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TASKPACK = os.path.join(ROOT, "taskpack")
# AI9_RESULTS_DIR lets a test run keep its output away from the real results folder
RESULTS = os.environ.get("AI9_RESULTS_DIR") or os.path.join(ROOT, "results")

RUNNERS = {"control": control_runner.run, "ai9": ai9_runner.run}


def load_tasks(pack, only=None):
    d = os.path.join(TASKPACK, pack)
    tasks = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json"):
            t = json.load(open(os.path.join(d, fn)))
            if only and t["task_id"] not in only:
                continue
            tasks.append(t)
    return tasks


def verify_pack(pack):
    """Every task file must match taskpack/pack.json and nothing unlisted may run.
    Returns a list of problems (empty = intact)."""
    try:
        manifest = json.load(open(os.path.join(TASKPACK, "pack.json"))).get(pack + "_sha256", {})
    except (OSError, ValueError) as e:
        return ["taskpack/pack.json unreadable: %s" % e]
    d = os.path.join(TASKPACK, pack)
    files = sorted(fn for fn in os.listdir(d) if fn.endswith(".json"))
    problems = []
    for fn in files:
        if fn not in manifest:
            problems.append("%s/%s is not in the manifest" % (pack, fn))
        elif core.task_file_hash(os.path.join(d, fn)) != manifest[fn]:
            problems.append("%s/%s differs from the manifest" % (pack, fn))
    problems += ["%s/%s is in the manifest but missing" % (pack, fn)
                 for fn in sorted(manifest) if fn not in files]
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", choices=["control", "ai9"], required=True)
    ap.add_argument("--pack", choices=["frozen", "dev"], required=True)
    ap.add_argument("--repeat", type=int, default=1)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--tasks", nargs="*", default=None)
    ap.add_argument("--inject", default=None,
                    choices=["duplicate_packet", "corrupted_checkpoint",
                             "energy_depletion", "worker_kill"])
    ap.add_argument("--config", default=os.path.join(ROOT, "config.json"))
    ap.add_argument("--i-know-frozen", action="store_true",
                    help="required to run the frozen pack")
    a = ap.parse_args()

    if a.pack == "frozen" and not a.i_know_frozen:
        print("FROZEN PACK: benchmark runs only. Pass --i-know-frozen to confirm "
              "this is a scheduled benchmark run, not tuning.")
        sys.exit(2)

    problems = verify_pack(a.pack)
    if problems:
        print("TASK PACK CHECK FAILED - results would not be comparable:")
        for p in problems:
            print("  - " + p)
        print("Dev tasks changed on purpose: run  python3 taskpack/gen.py  to re-register them."
              if a.pack == "dev" else
              "Frozen tasks must never change. Restore them; do not re-register.")
        sys.exit(2)

    config = json.load(open(a.config)) if os.path.exists(a.config) else \
        {"model": {"backend": "offline-stub", "model": "offline-stub"}}
    os.makedirs(RESULTS, exist_ok=True)
    db = DB(os.path.join(RESULTS, "results.db"))

    tasks = load_tasks(a.pack, a.tasks)
    if not tasks:
        print("no tasks matched"); sys.exit(2)

    queued = 0
    for t in tasks:
        for rep in range(a.repeat):
            rid = core.run_id_for(t["task_id"], a.system, a.seed, rep)
            db.register({"run_id": rid, "task_id": t["task_id"],
                         "task_version": t["version"], "pack": a.pack,
                         "system": a.system, "config": config,
                         "model": config["model"].get("model", "?"),
                         "model_backend": config["model"].get("backend", "?"),
                         "seed": a.seed, "repeat_index": rep,
                         "budgets": t["limits"]})
            queued += 1

    # resume-safe: only run ids still queued/running
    pending = set(db.pending())
    done = failed = 0
    for t in tasks:
        for rep in range(a.repeat):
            rid = core.run_id_for(t["task_id"], a.system, a.seed, rep)
            if rid not in pending:
                print("skip (already done):", rid); continue
            db.start(rid)
            inject = a.inject or t.get("starting_state", {}).get("inject")
            t0 = time.time()
            try:
                ctx, record = RUNNERS[a.system](t, a.seed, rep, config, RESULTS, inject=inject)
                over = time.time() - t0
                if over > t["limits"]["time_limit_sec"]:
                    record["verified_success"] = 0
                    record["failure_type"] = "time_limit"
                record["duration_s"] = round(over, 3)
                db.finish(rid, record)
                done += 1
                uj = record["usage_json"]
                cost = (json.loads(uj) if isinstance(uj, str) else uj)["cost"]
                print("%s %s %s rep%d -> %s (%.1fs, $%.4f)" %
                      (rid, t["task_id"], a.system, rep,
                       "PASS" if record["verified_success"] else "FAIL:" +
                       str(record["failure_type"]), over, cost))
            except Exception as e:
                db.fail(rid, "runner_crash", str(e)[:150])
                failed += 1
                print(rid, "CRASH:", str(e)[:120])
    db.close()
    print("batch done: %d ran (%d ok-path, %d crashed) of %d queued" %
          (done, done - failed, failed, queued))


if __name__ == "__main__":
    main()
