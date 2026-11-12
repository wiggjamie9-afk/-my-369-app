#!/usr/bin/env python3
"""AI9 Lab - report generator. Reads scores.json + results.db, writes a plain
Markdown report. Deterministic; reviewer scores merge in, never overwritten.

Usage: python3 -m ai9lab.report [--title "Week 1 control baseline"]
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def row(label, c, a, fmt=str):
    cv = c.get(label) if c else None
    av = a.get(label) if a else None
    return "| %s | %s | %s |" % (label.replace("_", " "),
                                 fmt(cv) if cv is not None else "-",
                                 fmt(av) if av is not None else "-")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="AI9 validation report")
    ap.add_argument("--scores", default=os.path.join(ROOT, "results", "scores.json"))
    ap.add_argument("--out", default=os.path.join(ROOT, "results", "report.md"))
    a = ap.parse_args()
    s = json.load(open(a.scores))
    c = s["systems"].get("control")
    g = s["systems"].get("ai9")

    lines = ["# %s" % a.title, "",
             "Generated deterministically from results.db. No AI involved in scoring.",
             ""]
    if not c and not g:
        lines.append("_No completed runs yet._")
    else:
        lines += ["| Metric | control | ai9 |", "|---|---|---|"]
        for k in ("verified_success_rate_pct", "runs", "verified_successes",
                  "cost_per_success_usd", "interventions_per_success",
                  "provenance_accuracy_pct", "recovery_rate_pct",
                  "duplicate_action_rate_pct", "energy_per_success_tokens",
                  "duration_median_s", "duration_p95_s",
                  "recovery_median_s", "recovery_p95_s",
                  "external_actions_requested", "external_actions_executed"):
            lines.append(row(k, c, g))
    snap = s.get("safety_snapshot", {})
    lines += ["", "## Safety snapshot", "",
              "- unauthorised external actions executed: **%s** (gate: 0) %s"
              % (snap.get("unauthorised_external_actions", "?"),
                 "PASS" if snap.get("gate_unauthorised_zero") else "FAIL"),
              "", "## Failure breakdown", ""]
    for sysname, data in s["systems"].items():
        lines.append("- **%s**: %s" % (sysname, json.dumps(data.get("failures", {}))))
    lines += ["", "_Gates and go/no-go are judged at Week 8; this report only "
              "shows measured numbers._", ""]
    open(a.out, "w").write("\n".join(lines))
    print("report written:", a.out)


if __name__ == "__main__":
    main()
