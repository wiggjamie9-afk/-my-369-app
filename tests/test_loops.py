import os, tempfile, unittest
from ai9 import loops
from ai9.agent import AI9
from ai9.memory import LocalBackend, Memory


def be():
    return LocalBackend(os.path.join(tempfile.mkdtemp(), "m.json"))


class Rings(unittest.TestCase):
    def test_save_queue_checker_and_safety(self):
        b, q = be(), []
        ai = AI9(b, lambda s, u: "ok", queue=q)
        ai.answer("We open at 8am on weekdays.")
        self.assertEqual(len(b.items), 0)                       # not stuck yet
        q.append(Memory("jamie", "ok?", "chat"))                # junk
        q.append(Memory("jamie", "the password is hunter2", "chat"))
        r = loops.ring_save(q, b)
        self.assertEqual(r, {"saved": 1, "rejected": 2}); self.assertEqual(len(b.items), 1)

    def test_checker_must_be_different_model(self):
        with self.assertRaises(ValueError):
            loops.make_llm_checker(lambda p: "YES", "claude-x", "claude-x")
        c = loops.make_llm_checker(lambda p: "NO: vague", "other-y", "claude-x")
        self.assertFalse(c(Memory("a", "something maybe", "s"))[0])

    def test_rollup(self):
        b = be(); b.add(Memory("jamie", "remember that we open at 8am", "chat"))
        loops.ring_rollup(b)
        facts = [m.what for m in b.all() if m.source == "rollup"]
        self.assertEqual(facts, ["We open at 8am."])
        self.assertEqual(loops.ring_rollup(b), {"rolled": 0})   # idempotent

    def test_dedupe_merges_and_sums_recalls(self):
        b = be()
        a = Memory("j", "Our office is in Leeds city centre", "s", when="2026-01-01T00:00:00+00:00", recall_count=2)
        c = Memory("j", "Our office is in Leeds city centre.", "s", when="2026-02-01T00:00:00+00:00", recall_count=3)
        c.id = "other"; b.add(a); b.items["other"] = c
        self.assertEqual(loops.ring_dedupe(b), {"merged": 1})
        self.assertEqual(len(b.items), 1); self.assertEqual(a.recall_count, 5)

    def test_fade_lowers_unused_never_dna(self):
        b = be(); u = Memory("j", "unused fact here", "s"); d = Memory("j", "dna fact here", "s", is_dna=True)
        used = Memory("j", "used fact here", "s", recall_count=1)
        for m in (u, d, used): b.add(m)
        loops.ring_fade(b)
        self.assertLess(u.score, 1.0); self.assertEqual(d.score, 1.0); self.assertEqual(used.score, 1.0)

    def test_link_clusters(self):
        b = be(); x = Memory("j", "callout fee is 90 dollars", "s"); y = Memory("j", "callout fee covers travel", "s")
        z = Memory("j", "office closes Friday five", "s")
        for m in (x, y, z): b.add(m)
        loops.ring_link(b)
        self.assertEqual(x.cluster, y.cluster); self.assertNotEqual(x.cluster, z.cluster)

    def test_conflict_newest_wins_and_keeps_date(self):
        b = be()
        old = Memory("j", "The callout fee is 90 dollars", "s", when="2026-01-01T00:00:00+00:00")
        new = Memory("j", "The callout fee is 120 dollars", "s", when="2026-06-01T00:00:00+00:00")
        b.add(old); b.add(new)
        self.assertEqual(loops.ring_conflict(b)["conflicts"], 1)
        self.assertEqual(old.status, "superseded"); self.assertIn("2026-06-01", old.what)
        self.assertEqual([m.what for m in b.search("callout fee")], [new.what])  # recall returns only newest

    def test_dna_never_touched_by_conflict_or_dedupe(self):
        b = be(); d = Memory("j", "The callout fee is 90 dollars", "s", is_dna=True, when="2026-01-01T00:00:00+00:00")
        n = Memory("j", "The callout fee is 120 dollars", "s", when="2026-06-01T00:00:00+00:00")
        b.add(d); b.add(n); loops.ring_conflict(b); loops.ring_dedupe(b)
        self.assertEqual(d.status, "active")


if __name__ == "__main__":
    unittest.main()
