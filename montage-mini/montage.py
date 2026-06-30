#!/usr/bin/env python3
"""montage-mini CLI.

Usage:
    python montage.py "Make a 45-second animated explainer about why the sky is blue"
    python montage.py --out demos "Create a 60s cinematic trailer about Mars"

The agent (you, or your AI assistant) describes a video in plain language and
montage-mini runs the full pipeline, prints the decision log + review, and
writes a playable HTML video to projects/<slug>/final.html.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser

from montagemini import run_pipeline


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="montage-mini: offline agentic video pipeline")
    ap.add_argument("request", nargs="+", help="plain-language video brief")
    ap.add_argument("--out", default="projects", help="output root directory")
    ap.add_argument("--open", action="store_true", help="open the result in a browser")
    args = ap.parse_args(argv)

    request = " ".join(args.request)
    print(f"\n  brief: {request}\n")

    result = run_pipeline(request, out_root=args.out)

    # Decision log
    print("  decision log")
    print("  " + "-" * 60)
    for d in result.decisions:
        print(f"  {d['stage']:<11} {d['choice']}")
        print(f"  {'':<11} └ {d['why']}")
    print()

    # Review
    r = result.review_report
    status = "PASSED" if r["passed"] else "FAILED"
    print(f"  self-review: {status}  "
          f"({r['actual_duration_s']:.1f}s / target {r['target_duration_s']}s, "
          f"{r['scene_count']} scenes)")
    for c in r["checks"]:
        mark = "ok " if c["ok"] else "XX "
        print(f"    [{mark}] {c['name']}: {c['detail']}")
    print()

    print(f"  video:      {result.html_path}")
    print(f"  production: {result.project_dir}/production.json")
    print(f"  checkpoint: {result.project_dir}/checkpoint.json\n")

    if args.open:
        webbrowser.open("file://" + __import__("os").path.abspath(result.html_path))

    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
