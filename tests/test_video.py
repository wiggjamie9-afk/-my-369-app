import os, tempfile, unittest
from ai9.agent import AI9
from ai9.memory import LocalBackend
from video import pipeline
from video.providers import HostedProvider, SlateProvider
from video.stitch import duration


def ai():
    return AI9(LocalBackend(os.path.join(tempfile.mkdtemp(), "m.json")), lambda s, u: "ok")


class Video(unittest.TestCase):
    def test_end_to_end_with_memory_style(self):
        a = ai(); pipeline.rate(a, "promo", True, "warm colours and short punchy video style")
        out = os.path.join(tempfile.mkdtemp(), "o.mp4")
        r = pipeline.make_video("We fix boilers fast. Call us for a quote today.", out, SlateProvider(), a, "promo2")
        self.assertEqual(r["shots"], 2); self.assertGreater(duration(out), 3.5)
        self.assertTrue(any("video-pipeline" == m.source for m in a.backend.all()))

    def test_paid_provider_blocked_without_budget(self):
        p = HostedProvider(); p.usd_per_second = 0.5
        with self.assertRaises(PermissionError):
            pipeline.make_video("One shot only here.", "/tmp/x.mp4", p, None, "t", approved_budget=0)

    def test_unpriced_provider_cannot_run(self):
        with self.assertRaises(NotImplementedError):
            pipeline.make_video("One shot only here.", "/tmp/x.mp4", HostedProvider())


if __name__ == "__main__":
    unittest.main()
