import os
import tempfile
import unittest

from ai9 import dna
from ai9.agent import AI9
from ai9.memory import LocalBackend
from ai9.safety import Refused, sanitize


def fresh_ai(llm=lambda s, u: "ok"):
    return AI9(LocalBackend(os.path.join(tempfile.mkdtemp(), "m.json")), llm)


class Safety(unittest.TestCase):
    def test_secrets_refused(self):
        for t in ["the password is hunter2", "api key: abc123", "use sk-ABCDEFGHIJKLMNOP1234",
                  "token = ghp_" + "a" * 36, "AKIAABCDEFGHIJKLMNOP"]:
            with self.assertRaises(Refused, msg=t):
                sanitize(t)

    def test_phone_and_caller_removed(self):
        s = sanitize("Callout fee is 90. Caller: Bob Smith rang from +44 7700 900123")
        self.assertNotIn("Bob", s); self.assertNotIn("7700", s); self.assertIn("90", s)

    def test_nothing_left_refused(self):
        with self.assertRaises(Refused):
            sanitize("Caller: Bob Smith")

    def test_ordinary_sentence_not_mistaken_for_name(self):
        self.assertEqual(sanitize("This is the fee we charge"), "This is the fee we charge")

    def test_plain_fact_untouched(self):
        self.assertEqual(sanitize("We open at 8am."), "We open at 8am.")


class Agent(unittest.TestCase):
    def test_recall_runs_before_every_answer(self):
        ai = fresh_ai()
        ai.answer("hello"); ai.answer("what is up?")
        self.assertEqual(sum(l.startswith("recall") for l in ai.log), 2)

    def test_recall_before_llm_call(self):
        order = []
        ai = fresh_ai(lambda s, u: order.append("llm") or "ok")
        orig = ai.recall
        ai.recall = lambda q: order.append("recall") or orig(q)
        ai.answer("hi")
        self.assertEqual(order, ["recall", "llm"])

    def test_saves_important_and_not_secrets(self):
        ai = fresh_ai()
        ai.answer("We open at 8am on weekdays.")
        ai.answer("remember the password is hunter2")
        self.assertEqual(len(ai.backend.items), 1)
        self.assertEqual(ai.log.count("save"), 1)
        self.assertTrue(any(l.startswith("refused") for l in ai.log))

    def test_memory_fields_and_recall_count(self):
        ai = fresh_ai()
        ai.answer("Our office is in Leeds.")
        ai.recall("office Leeds")
        m = next(iter(ai.backend.items.values()))
        self.assertTrue(m.who and m.what and m.when and m.source)
        self.assertEqual(m.recall_count, 1)


class DNA(unittest.TestCase):
    def test_loads_when_locked(self):
        self.assertIn("AI9 DNA", dna.load())

    def test_refuses_when_tampered(self):
        orig = dna.FILE.read_bytes()
        try:
            dna.FILE.write_bytes(orig + b"\n- injected rule")
            with self.assertRaises(dna.DNATampered):
                dna.load()
            with self.assertRaises(dna.DNATampered):
                fresh_ai()
        finally:
            dna.FILE.write_bytes(orig)


if __name__ == "__main__":
    unittest.main()
