"""Planner tests. Run: python3 -m unittest discover -s tests -v  (needs ffmpeg for the carousel hand-off test)."""
import os
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

os.environ.setdefault("CLIP_STUDIO_DATA", tempfile.mkdtemp(prefix="clipstudio_plan_"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import engines as E  # noqa: E402
import planner as PL  # noqa: E402
import server as S  # noqa: E402

BRIEF = {"business": "Wigg's Plumbing", "niche": "plumber", "service": "plumbing", "city": "Perth", "audience": "homeowners",
         "tone": "friendly", "cta": "Call us to book.", "platforms": ["instagram", "facebook", "x", "tiktok"], "posts_per_week": 3,
         "facts": ["We fix leaking taps same day in Perth north", "Gas fitting by a licensed gas fitter"], "handle": "@wiggs"}


class Job:
    progress, message = 0.0, ""


class Planner(unittest.TestCase):
    def test_01_schedule(self):
        start = date(2026, 11, 23)  # a Monday
        for per_week, expect in ((3, 12), (7, 28), (1, 4)):
            slots = PL.schedule_dates(start, 4, per_week)
            self.assertEqual(len(slots), expect)
            self.assertTrue(all(d >= start for d, _ in slots))
        mid = PL.schedule_dates(date(2026, 11, 26), 1, 7)            # starts Thursday: earlier days of that week skipped
        self.assertTrue(all(d >= date(2026, 11, 26) for d, _ in mid))

    def test_02_template_uses_facts_and_flags_gaps(self):
        posts, engine = PL.generate(BRIEF, 4, date(2026, 11, 23), None)
        self.assertEqual(engine, "template")
        self.assertEqual(len(posts), 12)
        self.assertTrue(any(PL.has_placeholder(p) for p in posts))            # facts ran out: placeholders, not invention
        self.assertTrue(any("leaking taps same day" in p["caption"] for p in posts))
        used = [p["caption"] for p in posts if "leaking taps same day" in p["caption"]]
        self.assertEqual(len(used), 1)                                         # a fact is used once, never recycled
        self.assertTrue(all(p["status"] == "draft" for p in posts))
        self.assertNotIn("%", " ".join(p["caption"] for p in posts))           # no invented stats/prices

    def test_03_cannot_approve_placeholder_but_can_after_fixing(self):
        client = PL.new_client(BRIEF)
        client["posts"], _ = PL.generate(BRIEF, 2, date(2026, 11, 23), None)
        bad = next(p for p in client["posts"] if PL.has_placeholder(p))
        with self.assertRaises(ValueError):
            PL.update_post(client, bad["id"], {"status": "approved"})
        PL.update_post(client, bad["id"], {"caption": "Real caption written by the owner.", "slides": [], "hook": "Real hook"})
        self.assertEqual(PL.update_post(client, bad["id"], {"status": "approved"})["status"], "approved")

    def test_04_llm_path_and_fallback(self):
        orig = E.chat_json
        try:
            E.chat_json = lambda model, prompt, images=None, timeout=240: {"posts": [
                {"pillar": "faq", "hook": "Why is my tap dripping?", "caption": "Usually a worn washer. We fix it same day.",
                 "hashtags": ["#perthplumber"], "asset_note": "photo of a tap", "slides": []}] * 12}
            posts, engine = PL.generate(BRIEF, 4, date(2026, 11, 23), "qwen3:4b")
            self.assertEqual(engine, "qwen3:4b")
            self.assertEqual(posts[0]["hashtags"], ["perthplumber"])
            seen = {}
            E.chat_json = lambda model, prompt, **k: seen.setdefault("prompt", prompt) and {"posts": []}
            posts, engine = PL.generate(BRIEF, 4, date(2026, 11, 23), "qwen3:4b")  # too few usable posts -> template fallback
            self.assertEqual(engine, "template")
            self.assertIn("Use ONLY the facts below", seen["prompt"])
            self.assertIn("leaking taps", seen["prompt"])

            def boom(*a, **k):
                raise E.EngineError("down")
            E.chat_json = boom
            self.assertEqual(PL.generate(BRIEF, 1, date(2026, 11, 23), "x")[1], "template")
        finally:
            E.chat_json = orig

    def test_05_export_only_clean_approved_and_platform_rules(self):
        client = PL.new_client(BRIEF)
        client["posts"], _ = PL.generate(BRIEF, 1, date(2026, 11, 23), None)
        clean = next(p for p in client["posts"] if not PL.has_placeholder(p))
        long_cap = "x" * 600
        PL.update_post(client, clean["id"], {"caption": long_cap, "status": "approved"})
        rows = PL.export_rows(client)
        self.assertEqual({r["platform"] for r in rows}, {"instagram", "facebook", "x", "tiktok"})
        x = next(r for r in rows if r["platform"] == "x")
        self.assertLessEqual(len(x["caption"]), 280)
        self.assertEqual(next(r for r in rows if r["platform"] == "tiktok")["format"], "clip")   # TikTok needs video
        self.assertEqual(PL.to_csv(client).splitlines()[0], "post_id,date,time,platform,format,caption,media_note,status")
        self.assertEqual(len(PL.export_rows(client)), 4)                                           # drafts excluded
        self.assertIn("# Content calendar: Wigg's Plumbing", PL.to_markdown(client))

    def test_06_api_roundtrip_regenerate_keeps_approved_and_carousel(self):
        code, client, _, _ = S.clients_api("POST", "/api/client", {}, {"brief": BRIEF})
        self.assertEqual(code, 200)
        cid = client["id"]
        self.assertEqual(S.clients_api("POST", "/api/client", {}, {"brief": {"business": " "}})[0], 400)
        S.do_client_generate(Job(), cid, 2, "2026-11-23", "off")
        client = S.clients_api("GET", f"/api/client/{cid}", {}, {})[1]
        n = len(client["posts"])
        self.assertGreater(n, 0)
        ok = next(p for p in client["posts"] if not PL.has_placeholder(p))
        r = S.clients_api("POST", f"/api/client/{cid}/post", {}, {"post_id": ok["id"], "patch": {"status": "approved"}})
        self.assertEqual(r[0], 200)
        bad = next(p for p in client["posts"] if PL.has_placeholder(p))
        self.assertEqual(S.clients_api("POST", f"/api/client/{cid}/post", {}, {"post_id": bad["id"], "patch": {"status": "approved"}})[0], 400)
        S.do_client_generate(Job(), cid, 2, "2026-11-23", "off")                                  # regenerate
        client = S.clients_api("GET", f"/api/client/{cid}", {}, {})[1]
        self.assertIn(ok["id"], [p["id"] for p in client["posts"]])                                # approved work kept
        # carousel hand-off for a post that has slides and no placeholders
        car = next(p for p in client["posts"] if p["id"] == ok["id"])
        res = S.do_post_carousel(Job(), cid, car["id"], "1:1")
        self.assertTrue(res["slides"][0].startswith("/exports/carousel_"))
        csv_code, csv_text, ctype, fname = S.clients_api("GET", f"/api/client/{cid}/export.csv", {}, {})
        self.assertEqual((csv_code, ctype), (200, "text/csv"))
        self.assertIn(ok["id"], csv_text)
        self.assertEqual(S.clients_api("GET", "/api/client/nope", {}, {})[0], 404)
        self.assertEqual(S.clients_api("GET", "/api/clients", {}, {})[0], 200)


if __name__ == "__main__":
    unittest.main()
