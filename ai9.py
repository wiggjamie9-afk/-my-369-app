#!/usr/bin/env python3
"""AI9 - one entry point for the validation harness and its live console.

    python3 ai9.py smoke      prove the harness end to end (offline stub, in its own folder)
    python3 ai9.py dev        run the dev pack on both systems, then score and report
    python3 ai9.py score      score + report from the results database (no AI in the path)
    python3 ai9.py console    live console; add --lan to open it from a phone
    python3 ai9.py doctor     check the page, database, task pack, scores and port

Extra arguments pass straight through, e.g.  ai9.py dev --seed 7 --tasks TREND-1
The frozen pack is deliberately not offered here: it is measurement only.
Run it once, on purpose, with ai9lab.run_benchmark --pack frozen --i-know-frozen.

Standard library only. No keys are read or printed here.
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable


def run(*args):
    code = subprocess.call([PY] + list(args), cwd=ROOT)
    if code:
        sys.exit(code)


def score():
    run("-m", "ai9lab.score")
    run("-m", "ai9lab.report")


def main(argv):
    cmd, rest = (argv[0], argv[1:]) if argv else ("help", [])
    if cmd == "smoke":
        run(os.path.join("tests", "smoke_test.py"))
    elif cmd == "dev":
        if "--pack" in rest or "--system" in rest:
            sys.exit("ai9.py dev always runs the dev pack on both systems; drop --pack/--system")
        for system in ("ai9", "control"):
            run("-m", "ai9lab.run_benchmark", "--system", system, "--pack", "dev", *rest)
        score()
    elif cmd == "score":
        score()
    elif cmd == "console":
        run("organism.py", "connect", *rest)
    elif cmd == "doctor":
        run("organism.py", "doctor", *rest)
    else:
        print(__doc__.strip())
        return 0 if cmd in ("help", "-h", "--help") else 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
