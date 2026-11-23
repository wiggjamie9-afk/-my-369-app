"""python -m ai9.chat  - talk to AI9. Each turn: recall -> answer -> save-if-important -> drain save ring."""
from __future__ import annotations

from . import loops
from .live import build_ai9


def main():
    ai, queue, checker, backend = build_ai9()
    print("AI9 ready (blank line to quit)")
    while (q := input("you> ").strip()):
        print("ai9>", ai.answer(q))
        print("   ", loops.ring_save(queue, backend, checker))


if __name__ == "__main__":
    main()
