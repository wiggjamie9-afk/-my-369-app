"""Drafting and the fabrication check: an AI may describe a job, but it never gets a price onto a quote."""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bestmate import drafting as d
from bestmate.db import Store

ACCEPTANCE = "two and a half kW Daikin split, back-to-back install, Smith job"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(os.path.join(self.tmp.name, "t.db"))

    def tearDown(self):
        self.tmp.cleanup()


class Reading(Base):
    def spec(self, text):
        return d.draft(self.store, text, {})

    def test_the_acceptance_sentence(self):
        r = self.spec(ACCEPTANCE)
        self.assertEqual(r["spec"]["install_type"], "single_split")
        self.assertEqual(r["spec"]["brand"], "Daikin")
        self.assertEqual([u["kw_milli"] for u in r["spec"]["units"]], [2500])
        self.assertTrue(r["spec"]["back_to_back"])
        self.assertEqual(r["customer_name"], "Smith")
        self.assertEqual(r["line_items"][0]["sku"], "SPL-DAI-25")
        self.assertEqual(r["labour_hours_milli"], 4000)
        self.assertEqual(r["engine"], "local")

    def test_spoken_numbers(self):
        self.assertEqual(d.words_to_numbers("two and a half kw"), "2.5 kw")
        self.assertEqual(d.words_to_numbers("seven point one kilowatt"), "7.1 kilowatt")
        self.assertEqual(d.words_to_numbers("three 2.5kw heads"), "3 2.5kw heads")
        self.assertEqual(d.words_to_numbers("12.5 kw"), "12.5 kw")

    def test_other_job_shapes(self):
        r = self.spec("three 2.5 kw and one 3.5kw mitsi multi for mrs jones")
        self.assertEqual((r["spec"]["install_type"], r["spec"]["brand"], r["customer_name"]),
                         ("multi_split", "Mitsubishi Electric", "Jones"))
        self.assertEqual([u["kw_milli"] for u in r["spec"]["units"]], [2500, 2500, 2500, 3500])
        r = self.spec("ducted 12.5kw daikin at the nguyen place")
        self.assertEqual((r["spec"]["install_type"], r["line_items"][0]["sku"], r["customer_name"]),
                         ("ducted", "DUC-DAI-125", "Nguyen"))
        r = self.spec("service 3 units")
        self.assertEqual((r["spec"]["install_type"], len(r["spec"]["units"])), ("service", 3))

    def test_a_brand_we_do_not_stock_is_flagged_not_swapped(self):
        r = self.spec("samsung seven point one kilowatt split")
        self.assertEqual(r["spec"]["brand"], "Samsung")
        unit = r["line_items"][0]
        self.assertTrue(unit["flagged"])
        self.assertIsNone(unit["unit_sell_cents"])
        self.assertIn("Samsung 7.1kW", unit["description"])

    def test_vague_jobs_say_what_was_assumed(self):
        r = self.spec("put an aircon in for the bloke down the road")
        self.assertTrue(any("installation type" in f for f in r["flags"]))
        self.assertTrue(any("kW" in f for f in r["flags"]))
        with self.assertRaises(ValueError):
            self.spec("   ")

    def test_every_price_on_a_draft_is_the_library_price(self):
        settings = self.store.settings()
        for text in (ACCEPTANCE, "ducted 10kw daikin", "two 3.5kw fujitsu splits on brackets"):
            for ln in self.spec(text)["line_items"]:
                if ln["flagged"]:
                    continue
                part = self.store.part(ln["sku"])
                self.assertEqual((ln["unit_cost_cents"], ln["unit_sell_cents"]), self.store.price_part(part, settings), ln["sku"])


class Fabrication(Base):
    def test_unknown_item_is_kept_but_never_priced(self):
        lines, flags = d.check_ai_items(self.store, [{"description": "Crane hire half day", "qty": 1, "unit_price": 450}])
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0]["flagged"])
        self.assertIsNone(lines[0]["unit_sell_cents"])
        self.assertIsNone(lines[0]["unit_cost_cents"])
        self.assertIn("not shown", lines[0]["flag_reason"])
        self.assertNotIn("450", json.dumps(lines))

    def test_made_up_sku_is_treated_as_unknown(self):
        lines, _ = d.check_ai_items(self.store, [{"sku": "TOTALLY-REAL-9000", "description": "Turbo isolator", "price": "19.99"}])
        self.assertTrue(lines[0]["flagged"])
        self.assertIsNone(lines[0]["sku"])

    def test_known_item_uses_library_price_and_the_ai_price_is_discarded(self):
        lines, flags = d.check_ai_items(self.store, [{"sku": "DRN-PUMP", "qty": 2, "unit_price": 1}])
        part = self.store.part("DRN-PUMP")
        self.assertFalse(lines[0]["flagged"])
        self.assertEqual((lines[0]["unit_cost_cents"], lines[0]["unit_sell_cents"]), self.store.price_part(part))
        self.assertEqual(lines[0]["qty_milli"], 2000)
        self.assertTrue(any("discarded" in f for f in flags))

    def test_junk_from_a_model_cannot_break_the_check(self):
        lines, flags = d.check_ai_items(self.store, [None, 7, "x", {}, {"description": "  "}, {"description": "Thing", "qty": "lots"},
                                                     {"description": "Other", "qty": -4}])
        self.assertEqual([(ln["description"], ln["qty_milli"], ln["flagged"]) for ln in lines],
                         [("Thing", 1000, True), ("Other", 1000, True)])

    def test_dollar_figures_in_notes_are_removed_unless_the_library_backs_them(self):
        text, removed = d.scrub_notes("Unit is $1,170.00. Allow about $450 for a crane, AUD $90 parking and 80 bucks for lunch.", {117000})
        self.assertEqual(text, "Unit is $1,170.00. Allow about [price removed] for a crane, [price removed] parking and [price removed] for lunch.")
        self.assertEqual(removed, ["$450", "AUD $90", "80 bucks"])
        self.assertEqual(d.scrub_notes("Customer wants it done before Christmas. Access via side gate 2.", set()),
                         ("Customer wants it done before Christmas. Access via side gate 2.", []))
        self.assertEqual(d.scrub_notes("ballpark $3k all up", set())[1], ["$3k"])


class FakeModel(BaseHTTPRequestHandler):
    """An OpenAI-compatible endpoint that misbehaves the way a model can."""
    reply = {}

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        body = json.dumps({"choices": [{"message": {"content": type(self).reply}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


class WithAModel(Base):
    def setUp(self):
        super().setUp()
        self.server = HTTPServer(("127.0.0.1", 0), FakeModel)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.cfg = {"llm_base_url": "http://127.0.0.1:%d/v1" % self.server.server_address[1], "llm_key": "", "llm_model": "test"}

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        super().tearDown()

    def test_a_model_that_invents_prices_gets_none_of_them_through(self):
        FakeModel.reply = "Sure! " + json.dumps({
            "install_type": "single_split", "brand": "Daikin", "units": [{"kw": 2.5, "unit_price": 1}], "customer_name": "Smith",
            "back_to_back": True,
            "extra_items": [{"description": "Crane hire", "qty": 1, "unit_price": 450.0},
                            {"sku": "DRN-PUMP", "qty": 1, "unit_price": 9.99},
                            {"sku": "FAKE-1", "description": "Gold-plated isolator", "price": "$3,000"}],
            "notes": "Should come in around $2,500 all up. Crane is $450."})
        r = d.draft(self.store, ACCEPTANCE, self.cfg)
        self.assertEqual(r["engine"], "llm")
        by = {ln["description"]: ln for ln in r["line_items"]}
        self.assertEqual(by["Daikin 2.5kW wall split system (package)"]["unit_sell_cents"], 117000)   # library, not the model's 1
        self.assertTrue(by["Crane hire"]["flagged"] and by["Gold-plated isolator"]["flagged"])
        self.assertIsNone(by["Crane hire"]["unit_sell_cents"])
        self.assertEqual(by["Condensate pump"]["unit_sell_cents"], self.store.price_part(self.store.part("DRN-PUMP"))[1])
        self.assertEqual(r["notes"], "Should come in around [price removed] all up. Crane is [price removed].")
        self.assertTrue(any("cannot account for" in f for f in r["flags"]))
        prices = {ln[k] for ln in r["line_items"] for k in ("unit_cost_cents", "unit_sell_cents")}
        for invented_cents in (100, 45000, 999, 300000, 250000):         # every figure the model made up
            self.assertNotIn(invented_cents, prices)
        for invented_text in ("$450", "$2,500", "$3,000", "9.99"):
            self.assertNotIn(invented_text, json.dumps([r["notes"], [ln["description"] for ln in r["line_items"]]]))

    def test_a_model_that_returns_nonsense_falls_back_to_the_built_in_reader(self):
        FakeModel.reply = "I'm sorry, I can't help with that."
        r = d.draft(self.store, ACCEPTANCE, self.cfg)
        self.assertEqual(r["engine"], "local")
        self.assertEqual(r["line_items"][0]["sku"], "SPL-DAI-25")
        self.assertTrue(any("could not be used" in f for f in r["flags"]))

    def test_an_unreachable_model_falls_back_too(self):
        r = d.draft(self.store, ACCEPTANCE, {"llm_base_url": "http://127.0.0.1:1/v1", "llm_key": "", "llm_model": ""})
        self.assertEqual((r["engine"], r["customer_name"]), ("local", "Smith"))


if __name__ == "__main__":
    unittest.main()
