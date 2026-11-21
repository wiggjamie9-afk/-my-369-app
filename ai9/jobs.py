"""Scheduler entry point: python -m ai9.jobs <ring> [--store PATH] [--queue PATH]

Cron lines are in ai9/schedule.cron. Order matters if run together:
save -> rollup -> dedupe -> conflict -> link -> fade.
"""
from __future__ import annotations

import argparse
import json
import os

from . import loops
from .memory import LocalBackend, Memory
from dataclasses import asdict


def main(argv=None) -> dict:
    ap = argparse.ArgumentParser()
    ap.add_argument("ring", choices=loops.RINGS)
    ap.add_argument("--store", default="ai9_memory.json")
    ap.add_argument("--queue", default="ai9_queue.json")
    a = ap.parse_args(argv)
    be = LocalBackend(a.store)
    if a.ring == "save":
        q = [Memory(**d) for d in json.load(open(a.queue))] if os.path.exists(a.queue) else []
        out = loops.ring_save(q, be)
        json.dump([asdict(m) for m in q], open(a.queue, "w"))
    else:
        out = getattr(loops, f"ring_{a.ring}")(be)
    print(json.dumps(out))
    return out


if __name__ == "__main__":
    main()
