import os, re, sys, tempfile, unittest
from pathlib import Path
os.environ.setdefault("CLIP_STUDIO_DATA", tempfile.mkdtemp(prefix="clipstudio_kit_"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kit as KIT, planner as PL, server as S  # noqa: E402


class Job:
    progress, message = 0.0, ""


class Kit(unittest.TestCase):
    def test_kit_builds_honest_content(self):
        r = S.do_kit(Job(), ["trades", "health"], "@48aicrew", "DM us to find out more.", 2, "2026-11-23", True, "off")
        self.assertEqual([n["niche"] for n in r["niches"]], ["trades", "health"])
        for n in r["niches"]:
            self.assertEqual(len(n["carousel"]), 7)
            self.assertTrue(Path(S.EXPORTS / n["carousel"][0].split("/exports/")[1]).is_file())
            self.assertGreater(n["needs_input"], 0)                         # launch status / price not invented
            c = PL.load_client(S.CLIENTS, n["client_id"])
            blob = " ".join(p["caption"] + p["hook"] for p in c["posts"]) + str(KIT.slides_for(n["niche"]))
            self.assertTrue(all(KIT.DISCLOSURE in p["caption"] for p in c["posts"]))
            self.assertIsNone(re.search(r"\$\d|guarantee|earn|while you sleep|%|ROI|10x", blob, re.I))
        with self.assertRaises(S.ApiError):
            S.do_kit(Job(), ["nope"])
        with self.assertRaises(S.ApiError):
            S.do_kit(Job(), ["trades"], cta="[ADD: cta]")


if __name__ == "__main__":
    unittest.main()
