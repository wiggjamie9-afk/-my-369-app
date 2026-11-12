#!/usr/bin/env python3
"""Writes the AI9 Week-1 task pack: 40 frozen + 20 dev task files + versioned
manifest (sha256 per file). Run once to (re)generate; the JSON files are the
frozen artifact - edit by bumping 'version', never silently.

Usage: python3 taskpack/gen.py
"""
import hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_research import RESEARCH
from gen_memory import MEMORY
from gen_routines import ROUTINES
from gen_money import MONEY
from gen_dev import DEV

HERE = os.path.dirname(os.path.abspath(__file__))
FROZEN_DIR = os.path.join(HERE, "frozen")
DEV_DIR = os.path.join(HERE, "dev")

PACK_VERSION = "1.0.0"


def write_tasks(tasks, outdir, pack):
    os.makedirs(outdir, exist_ok=True)
    manifest = {}
    for t in tasks:
        fn = os.path.join(outdir, t["task_id"].lower() + ".json")
        t["pack"] = pack
        blob = json.dumps(t, indent=2, sort_keys=True)
        open(fn, "w").write(blob + "\n")
        manifest[os.path.basename(fn)] = hashlib.sha256(blob.encode()).hexdigest()
    return manifest


def file_hash(path):
    """sha256 of a task file as the manifest records it (one trailing newline ignored)."""
    blob = open(path, "rb").read()
    if blob.endswith(b"\n"):
        blob = blob[:-1]
    return hashlib.sha256(blob).hexdigest()


def handwritten(outdir, generated):
    """Task files in the folder that no generator produced. They are hashed as
    they stand and never rewritten, so a hand-written dev task (TREND-*) is
    covered by the manifest like any other."""
    extra = {}
    for fn in sorted(os.listdir(outdir)):
        if fn.endswith(".json") and fn not in generated:
            json.load(open(os.path.join(outdir, fn)))      # must at least parse
            extra[fn] = file_hash(os.path.join(outdir, fn))
    return extra


def main():
    frozen = RESEARCH + MEMORY + ROUTINES + MONEY
    assert len(frozen) == 40, "frozen pack must be exactly 40, got %d" % len(frozen)
    assert len(DEV) == 20, "dev pack must be exactly 20, got %d" % len(DEV)
    ids = [t["task_id"] for t in frozen + DEV]
    assert len(ids) == len(set(ids)), "duplicate task ids"
    m1 = write_tasks(frozen, FROZEN_DIR, "frozen")
    m2 = write_tasks(DEV, DEV_DIR, "dev")
    stray = handwritten(FROZEN_DIR, m1)
    assert not stray, "frozen pack holds files no generator made: %s" % sorted(stray)
    extra = handwritten(DEV_DIR, m2)
    m2.update(extra)
    pack = {"pack": "ai9-week1", "version": PACK_VERSION,
            "frozen_count": len(frozen), "dev_count": len(m2),
            "dev_handwritten": sorted(extra),
            "frozen_sha256": m1, "dev_sha256": m2,
            "law": "Do not run the frozen benchmark repeatedly while tuning. "
                   "Tune only on development tasks."}
    open(os.path.join(HERE, "pack.json"), "w").write(json.dumps(pack, indent=2) + "\n")
    print("pack written: %d frozen + %d dev (%d generated, %d hand-written), version %s"
          % (len(frozen), len(m2), len(DEV), len(extra), PACK_VERSION))


if __name__ == "__main__":
    main()
