"""Locked DNA file (Stage 1, rule 4).

ai9/dna/DNA.md holds identity, rules and business facts. Only Jamie edits it.
How "locked" is enforced:
  1. GitHub CODEOWNERS requires Jamie's review on ai9/dna/** (turn on
     "Require review from Code Owners" in branch protection - a repo setting
     I cannot switch on from here).
  2. ai9/dna/DNA.lock holds the SHA-256 of DNA.md. AI9 REFUSES TO START if
     the file does not match the lock. Jamie re-locks with:
         python -m ai9.dna lock
  3. Loaded at every startup into the system prompt. It is never written to
     memory and the agent has no tool that can write it.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

DIR = pathlib.Path(__file__).parent / "dna"
FILE, LOCK = DIR / "DNA.md", DIR / "DNA.lock"


class DNATampered(Exception):
    pass


def _hash() -> str:
    return hashlib.sha256(FILE.read_bytes()).hexdigest()


def load() -> str:
    if not LOCK.exists() or LOCK.read_text().strip() != _hash():
        raise DNATampered("DNA.md does not match DNA.lock - only Jamie may change it (run: python -m ai9.dna lock)")
    return FILE.read_text()


if __name__ == "__main__":
    if sys.argv[1:] == ["lock"]:
        LOCK.write_text(_hash() + "\n")
        print("locked", _hash())
    else:
        print(load())
