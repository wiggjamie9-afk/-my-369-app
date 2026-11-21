"""Stage 3 harness: plain Hindsight-style memory vs the looping version.

Rules baked in (from the brief):
  * Questions + known answers are written BEFORE testing (bench/questions.json,
    frozen by SHA-256 in bench/questions.lock - the run refuses if they change).
  * Real data only, caller details stripped (ingest runs every note through
    safety.sanitize; anything it refuses is dropped and counted).
  * Answer model and grader model must differ (hard check).
  * 100 runs per arm. Measures % correct, confident-wrong %, cost per run.
  * Pass = looping correct% >= plain correct% * (1 + 0.5)  [relative; configurable].
  * Cost estimate is printed FIRST; `run` refuses without --approved-budget >= estimate.

Usage:
  python -m ai9.bench estimate [--runs 100]
  python -m ai9.bench lock                       # freeze questions (Jamie, once written)
  python -m ai9.bench run --approved-budget USD  # SIMULATION unless live models wired
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import tempfile
from dataclasses import dataclass

from . import loops
from .agent import AI9
from .memory import LocalBackend, Memory
from .safety import Refused, sanitize

DIR = pathlib.Path(__file__).resolve().parent.parent / "bench"
CONF_WRONG = 70   # a wrong answer given with confidence >= this counts as "confident wrong"

# USD per 1M tokens (input, output). PLACEHOLDERS - verify against current price lists before approving a budget.
PRICES = {"answer-model": (3.0, 15.0), "grader-model": (1.0, 5.0)}
# Per-call token assumptions for the estimate (replace with measured values after the first 5 runs).
TOK = {"plain_in": 3000, "loop_in": 5000, "out": 300, "grade_in": 1500, "grade_out": 200}


@dataclass
class Answer:
    text: str
    confidence: int          # 0-100, self-reported
    tokens_in: int = 0
    tokens_out: int = 0


# ---- cost -----------------------------------------------------------------
def estimate(runs: int = 100, nq: int = 50, hindsight_per_recall: float = 0.0) -> dict:
    pa, pg = PRICES["answer-model"], PRICES["grader-model"]
    ans = lambda i: (i * pa[0] + TOK["out"] * pa[1]) / 1e6
    grade = (TOK["grade_in"] * pg[0] + TOK["grade_out"] * pg[1]) / 1e6
    n = runs * nq
    plain = n * (ans(TOK["plain_in"]) + grade + hindsight_per_recall)
    loop = n * (ans(TOK["loop_in"]) + grade + hindsight_per_recall)
    return {"answers_per_arm": n, "plain_usd": round(plain, 2), "looping_usd": round(loop, 2),
            "total_usd": round(plain + loop, 2), "note": "excludes Hindsight usage fees and data loading; prices are placeholders"}


def cost_of(a: Answer, grade_tokens=(TOK["grade_in"], TOK["grade_out"])) -> float:
    pa, pg = PRICES["answer-model"], PRICES["grader-model"]
    return (a.tokens_in * pa[0] + a.tokens_out * pa[1] + grade_tokens[0] * pg[0] + grade_tokens[1] * pg[1]) / 1e6


# ---- data -----------------------------------------------------------------
def load_questions() -> list[dict]:
    raw = (DIR / "questions.json").read_bytes()
    lock = DIR / "questions.lock"
    if not lock.exists() or lock.read_text().strip() != hashlib.sha256(raw).hexdigest():
        raise SystemExit("questions.json is not locked (or changed after locking). Write all 50 first, then: python -m ai9.bench lock")
    qs = json.loads(raw)
    if len(qs) != 50:
        raise SystemExit(f"need exactly 50 questions, found {len(qs)}")
    return qs


def build_banks(notes: list[dict]) -> tuple[LocalBackend, LocalBackend, int]:
    """Same sanitized data in both banks; only the looping bank runs the rings."""
    d = tempfile.mkdtemp()
    plain, loop = LocalBackend(f"{d}/plain.json"), LocalBackend(f"{d}/loop.json")
    dropped = 0
    for n in notes:
        try:
            what = sanitize(n["what"])
        except Refused:
            dropped += 1; continue
        for b in (plain, loop):   # separate objects so rings can't leak across arms
            b.items[f"{n['id']}"] = Memory(n.get("who", "unknown"), what, n.get("source", "data"), when=n["when"], id=str(n["id"]))
    loops.ring_rollup(loop); loops.ring_dedupe(loop); loops.ring_conflict(loop); loops.ring_link(loop); loops.ring_fade(loop)
    return plain, loop, dropped


# ---- running --------------------------------------------------------------
def run_arm(backend, answer_fn, grade_fn, questions, runs: int) -> dict:
    ai = AI9(backend, lambda s, u: "")          # uses its recall + DNA path; answer_fn gets the built context
    correct = conf_wrong = 0; cost = 0.0; total = 0
    for _ in range(runs):
        for q in questions:
            hits = ai.recall(q["q"])
            ctx = "\n".join(f"- [{m.when[:10]}] {m.what}" for m in hits) or "(none)"
            a: Answer = answer_fn(f"{ai.dna}\n\n## Recalled memories\n{ctx}", q["q"])
            ok = grade_fn(q["q"], q["a"], a.text)
            correct += ok; total += 1
            conf_wrong += (not ok) and a.confidence >= CONF_WRONG
            cost += cost_of(a)
    return {"correct_pct": round(100 * correct / total, 1), "confident_wrong_pct": round(100 * conf_wrong / total, 1),
            "cost_per_run_usd": round(cost / runs, 4), "answers": total}


def verdict(plain: dict, loop: dict, margin: float = 0.5) -> dict:
    need = plain["correct_pct"] * (1 + margin)
    return {"needed_correct_pct": round(need, 1), "looping_correct_pct": loop["correct_pct"],
            "PASS": loop["correct_pct"] >= need and plain["correct_pct"] > 0}


def run(notes, questions, answer_fn, grade_fn, answer_model, grader_model, runs=100, simulated=True) -> dict:
    if answer_model == grader_model:
        raise ValueError("grader must be a DIFFERENT model from the answerer")
    plain, loop, dropped = build_banks(notes)
    p = run_arm(plain, answer_fn, grade_fn, questions, runs)
    l = run_arm(loop, answer_fn, grade_fn, questions, runs)
    return {"SIMULATION": simulated, "dropped_unsafe_notes": dropped, "plain": p, "looping": l, "verdict": verdict(p, l)}


# ---- offline stand-ins (SIMULATION ONLY - results say nothing about real quality) -----
def fake_answer(system: str, q: str) -> Answer:
    ctx = system.split("## Recalled memories\n", 1)[-1]
    has = ctx.strip() != "(none)"
    return Answer(ctx if has else "I don't know", 90 if has else 10, tokens_in=len(system) // 4, tokens_out=60)


def fake_grade(q: str, expected: str, answer: str) -> bool:
    return expected.lower() in answer.lower()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["estimate", "lock", "run"])
    ap.add_argument("--runs", type=int, default=100)
    ap.add_argument("--approved-budget", type=float)
    ap.add_argument("--questions", default=None, help="override path (dry-run only)")
    a = ap.parse_args(argv)
    if a.cmd == "estimate":
        print(json.dumps(estimate(a.runs), indent=1)); return
    if a.cmd == "lock":
        (DIR / "questions.lock").write_text(hashlib.sha256((DIR / "questions.json").read_bytes()).hexdigest() + "\n")
        print("questions locked"); return
    est = estimate(a.runs)
    if a.approved_budget is None or a.approved_budget < est["total_usd"]:
        raise SystemExit(f"Estimate is ${est['total_usd']}. Re-run with --approved-budget >= that after Jamie approves it.")
    raise SystemExit("Live models are not wired (needs Hindsight, answer-model and a different grader-model keys). "
                     "Harness is tested by tests/test_bench.py with simulated models.")


if __name__ == "__main__":
    main()
