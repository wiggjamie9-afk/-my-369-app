#!/usr/bin/env python3
"""Offline self-tests for montage-mini. No network, no deps beyond stdlib.

Run: python3 test_pipeline.py
"""

import os
import tempfile
import unittest

from montagemini.brief import parse_brief
from montagemini.script import write_script
from montagemini.sceneplan import plan_scenes, total_duration
from montagemini.assets import build_assets
from montagemini.compose import build_production, render_html
from montagemini.review import review
from montagemini import run_pipeline


class TestBrief(unittest.TestCase):
    def test_duration_forms(self):
        self.assertEqual(parse_brief("a 30 second video").duration_s, 30)
        self.assertEqual(parse_brief("a 30-second video").duration_s, 30)
        self.assertEqual(parse_brief("a 1 minute video").duration_s, 60)
        self.assertEqual(parse_brief("a 1:30 clip").duration_s, 90)

    def test_profile_and_tone(self):
        b = parse_brief("energetic tiktok about coffee")
        self.assertEqual(b.profile, "tiktok")
        self.assertEqual(b.aspect, "9:16")
        self.assertEqual(b.tone, "energetic")

    def test_narration_off(self):
        self.assertFalse(parse_brief("montage, no narration").narration)

    def test_topic_cleaned(self):
        b = parse_brief("Make a 45-second animated explainer about why the sky is blue")
        self.assertEqual(b.topic, "why the sky is blue")
        self.assertEqual(b.width, 1920)  # regression: width must not be clobbered


class TestPipelineStages(unittest.TestCase):
    def test_scene_timing_and_review(self):
        brief = parse_brief("Make a 45-second explainer about photosynthesis")
        script = write_script(brief)  # template backend offline
        self.assertEqual(script.backend, "template")
        scenes = plan_scenes(script, brief.duration_s)
        self.assertGreaterEqual(len(scenes), 3)
        # duration lands near target
        self.assertAlmostEqual(total_duration(scenes), brief.duration_s, delta=0.5)
        # captions within bounds
        for s in scenes:
            if s.words:
                self.assertLessEqual(s.words[-1].end, s.duration + 0.05)
        visuals = build_assets(scenes, brief.tone)
        self.assertEqual(len(visuals), len(scenes))
        passed, report = review(scenes, brief.duration_s, brief.narration)
        self.assertTrue(passed, report["findings"])

    def test_html_is_self_contained(self):
        brief = parse_brief("Make a 30s cinematic trailer about the deep sea")
        script = write_script(brief)
        scenes = plan_scenes(script, brief.duration_s)
        visuals = build_assets(scenes, brief.tone)
        prod = build_production(brief, script, scenes, visuals)
        html = render_html(prod)
        self.assertNotIn("/*__PRODUCTION__*/", html)  # marker replaced
        # No external resource loading. (An inline SVG data-URI legitimately
        # contains the w3.org *namespace* URI; that's not a network fetch, so
        # we check the loading mechanisms, not the bare substring.)
        for ref in ('src="http', "src='http", 'href="http', "href='http",
                    "url(http", 'url("http', "url('http"):
            self.assertNotIn(ref, html)
        self.assertIn("const P = {", html)


class TestEndToEnd(unittest.TestCase):
    def test_run_pipeline_writes_files(self):
        with tempfile.TemporaryDirectory() as d:
            res = run_pipeline("Make a 20s explainer about black holes", out_root=d)
            self.assertTrue(os.path.exists(res.html_path))
            self.assertTrue(os.path.exists(os.path.join(res.project_dir, "production.json")))
            self.assertTrue(os.path.exists(os.path.join(res.project_dir, "checkpoint.json")))
            self.assertTrue(res.passed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
