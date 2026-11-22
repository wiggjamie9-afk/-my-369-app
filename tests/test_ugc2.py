import json, os, tempfile, unittest
from ugc import factory, publish, testing
from ugc.research import Trend, rank_trends
from ugc.voice import SilentVoice, mux
from video.captions import burn_captions
from video.plan import plan_shots
from video.providers import SlateProvider
from video.stitch import duration
from tests.test_ugc import brief


class Testing(unittest.TestCase):
    R = [testing.Result("a", "h", 20, 5), testing.Result("b", "h", 5000, 200), testing.Result("c", "h", 3000, 60)]

    def test_small_sample_cannot_win(self):
        r = testing.rank(self.R, min_views=500)
        self.assertEqual([x.vid for x in r["ranked"]], ["b", "c"]); self.assertEqual(r["insufficient_data"], ["a"])

    def test_proposal_needs_named_human_and_sums(self):
        p = testing.propose_budget(self.R, 100.0)
        self.assertEqual(p.status, "pending"); self.assertAlmostEqual(sum(v for _, v in p.moves), 100.0, delta=0.05)
        with self.assertRaises(ValueError): p.approve(" ")
        p.approve("Jamie"); self.assertEqual(p.status, "approved")

    def test_no_data_no_move(self):
        self.assertEqual(testing.propose_budget([testing.Result("a", "h", 10, 5)], 100).moves, [])


class Publish(unittest.TestCase):
    def meta(self, **kw):
        m = {"id": "v1", "script": "Here is how the boiler cover fits.", "ai_generated": True}; m.update(kw); return m

    def q(self):
        return publish.ApprovalQueue(os.path.join(tempfile.mkdtemp(), "q.json"), brief())

    def test_unapproved_never_posts(self):
        q = self.q(); q.submit(self.meta()); pub = publish.DryRunPublisher()
        self.assertEqual(q.publish_approved(pub), []); self.assertEqual(pub.posted, [])

    def test_approved_posts_once(self):
        q = self.q(); q.submit(self.meta()); q.approve("v1", "Jamie"); pub = publish.DryRunPublisher()
        self.assertEqual(len(q.publish_approved(pub)), 1); self.assertEqual(q.publish_approved(pub), [])

    def test_refuses_unlabelled_and_noncompliant(self):
        q = self.q()
        with self.assertRaises(ValueError): q.submit(self.meta(ai_generated=False))
        with self.assertRaises(ValueError): q.submit(self.meta(script="I tried this and loved it"))

    def test_anonymous_approval_refused(self):
        q = self.q(); q.submit(self.meta())
        with self.assertRaises(ValueError): q.approve("v1", "")


class Media(unittest.TestCase):
    def test_captions_voice_and_trends_in_factory(self):
        d = tempfile.mkdtemp()
        tr = [Trend("POV storytime", "manual", 9.0)]
        self.assertEqual(rank_trends(tr + [Trend("x", "m", 1)], 1)[0].name, "POV storytime")
        r = factory.run_batch(brief(), SlateProvider(720, 1280), d, None, n=2, trends=tr, captions=True)
        self.assertEqual(len(r["made"]), 2)
        self.assertTrue(any("POV storytime" in m["hook"] for m in r["made"]))
        f = r["made"][0]["file"]; self.assertGreater(duration(f), 2.0)
        a = SilentVoice().speak("x", os.path.join(d, "a.wav"), 3)
        self.assertGreater(duration(mux(f, a, os.path.join(d, "m.mp4"))), 1.0)


if __name__ == "__main__":
    unittest.main()
