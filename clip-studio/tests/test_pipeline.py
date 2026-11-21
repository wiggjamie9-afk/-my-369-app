"""End-to-end tests on synthetic media. Run:  python3 -m unittest discover -s tests -v
Needs ffmpeg/ffprobe. A fake Ollama server stands in for the local LLM, so this checks the plumbing
(requests, JSON parsing, re-ranking), not model quality."""
import http.server
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

TMP = tempfile.mkdtemp(prefix="clipstudio_test_")
os.environ["CLIP_STUDIO_DATA"] = TMP
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import engines as E  # noqa: E402
import server as S  # noqa: E402


def ff(*args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def probe_wh(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return tuple(int(x) for x in out.strip().split(","))


class FakeOllama(http.server.BaseHTTPRequestHandler):
    seen = []

    def log_message(self, *a):
        pass

    def do_GET(self):
        body = json.dumps({"models": [{"name": "qwen3:8b", "size": 5.2e9}, {"name": "qwen3:4b", "size": 2.5e9},
                                    {"name": "qwen3-vl:8b", "size": 6.1e9}, {"name": "nomic-embed-text", "size": 2.7e8}]}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeOllama.seen.append(req)
        prompt = req["messages"][0]["content"]
        if req["messages"][0].get("images"):
            out = {"score": 6, "reason": "clear action"}
        elif "SECOND" in prompt:  # the clip we want ranked first
            out = {"score": 9.5, "hook": "Wait for the ending", "reason": "strong payoff"}
        else:
            out = {"score": 2, "hook": "Boring intro", "reason": "filler"}
        body = json.dumps({"message": {"content": "<think>x</think>" + json.dumps(out)}}).encode()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


class Job:
    progress, message = 0.0, ""


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # 40 s video, loud bursts at 11-14 s and 29-32 s
        ff("-f", "lavfi", "-i", "testsrc2=size=640x360:rate=30:duration=40",
           "-f", "lavfi", "-i", "aevalsrc='sin(2*PI*220*t)*(0.05+0.9*(between(t,11,14)+between(t,29,32)))':s=44100:d=40",
           "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
           str(S.MEDIA / "vid.mp4"))
        ff("-f", "lavfi", "-i", "aevalsrc='sin(2*PI*330*t)*(0.1+0.8*between(t,5,8))':s=44100:d=20",
           "-c:a", "libmp3lame", str(S.MEDIA / "song.mp3"))
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        cls.srv = srv
        E.OLLAMA = f"http://127.0.0.1:{srv.server_port}"
        E.ram_gb = lambda: 32.0

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_01_audio_analysis_finds_both_bursts(self):
        r = S.analyze(Job(), "vid.mp4", clip_len=12, count=2)
        peaks = sorted(c["peak"] for c in r["clips"])
        self.assertEqual(len(peaks), 2)
        self.assertTrue(10 <= peaks[0] <= 15 and 28 <= peaks[1] <= 33, peaks)
        self.assertIsNone(r["engines"])

    def test_02_deep_rank_uses_transcript_and_llm(self):
        calls = []

        def fake_tr(path, a, b, model=None, job=None, tmp=None):
            calls.append((a, b))
            # the later burst (~30 s) is the interesting one
            text = "SECOND this is the story payoff nobody expected!" if a > 20 else "uh so welcome to the stream"
            return [{"start": a + 1, "end": b - 1, "text": text, "words": []}]

        E.transcribe_range, E.whisper_engine = fake_tr, lambda: "fake"
        r = S.analyze(Job(), "vid.mp4", clip_len=12, count=2, deep=True, llm="auto", vision=True)
        self.assertEqual(r["engines"]["llm"], "qwen3:8b")           # picks the qwen text model, not the embedder
        self.assertEqual(r["engines"]["vision"], "qwen3-vl:8b")
        top = r["clips"][0]
        self.assertGreater(top["start"], 20)                          # LLM promoted the second clip
        self.assertEqual(top["hook"], "Wait for the ending")
        self.assertTrue(top["segments"])
        self.assertTrue(any(m["messages"][0].get("images") for m in FakeOllama.seen))  # frames were sent

    def test_03_deep_without_engines_falls_back(self):
        E.whisper_engine = lambda: None
        r = S.analyze(Job(), "vid.mp4", clip_len=12, count=2, deep=True, llm="off")
        self.assertIsNone(r["engines"]["transcript"])
        self.assertTrue(r["engines"]["notes"])
        self.assertEqual(len(r["clips"]), 2)

    def test_04_heuristic_scores(self):
        hot = E.heuristic_score("Why is this the best secret? Nobody told me 3 things! Wait, actually it's insane.", 10)
        cold = E.heuristic_score("so yeah um okay so", 10)
        self.assertGreater(hot["score"], cold["score"])
        self.assertTrue(hot["hook"])

    def test_05_export_formats_and_branding(self):
        for fmt_, (w, h) in S.FORMATS.items():
            job = Job()
            r = S.do_export(job, {"source": "vid.mp4", "start": 8, "end": 12, "format": fmt_, "layout": "crop",
                                  "keyframes": [{"t": 8, "x": .3, "z": 1}, {"t": 12, "x": .7, "z": 1.2}],
                                  "title": {"text": "Hook"}, "brand": {"text": "@me", "progress": True},
                                  "captions": {"segments": [{"start": 9, "end": 11, "text": "hello there world", "words": []}]}})
            self.assertEqual(probe_wh(S.EXPORTS / r["file"]), (w, h), fmt_)

    def test_06_blur_layout(self):
        r = S.do_export(Job(), {"source": "vid.mp4", "start": 0, "end": 3, "layout": "blur", "format": "9:16"})
        self.assertEqual(probe_wh(S.EXPORTS / r["file"]), (1080, 1920))

    def test_07_song_visualizer(self):
        info = S.probe(S.MEDIA / "song.mp3")
        self.assertTrue(info["audio_only"])
        r = S.do_export(Job(), {"source": "song.mp3", "start": 4, "end": 10, "format": "9:16",
                                "title": {"text": "Artist - Song"}, "brand": {"progress": True}})
        self.assertEqual(probe_wh(S.EXPORTS / r["file"]), (1080, 1920))
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                            str(S.EXPORTS / r["file"])], capture_output=True, text=True).stdout
        self.assertAlmostEqual(float(d), 6.0, delta=0.4)
        self.assertIn("song.mp3", [m["name"] for m in S.list_media()])

    def test_08_auto_produce(self):
        E.whisper_engine = lambda: None
        job = Job()
        r = S.auto_produce(job, "vid.mp4", count=2, clip_len=10, deep=False, settings={"format": "9:16", "layout": "crop"})
        self.assertEqual(len(r["clips"]), 2)
        for c in r["clips"]:
            self.assertEqual(probe_wh(S.EXPORTS / c["file"]), (1080, 1920))

    def test_10_low_memory_machine_picks_small_models(self):
        E.ram_gb = lambda: 8.0                       # e.g. an 8 GB MacBook
        try:
            text, vision = E.split_models(E.ollama_models())
            self.assertEqual(E.default_llm(text), "qwen3:4b")      # 8B (5.2 GB) does not fit in 40% of 8 GB
            self.assertIsNone(E.default_vision(vision))            # 6.1 GB vision model skipped
            self.assertEqual(E.default_whisper_model(), "small")
            E.whisper_engine = lambda: None
            r = S.analyze(Job(), "vid.mp4", clip_len=12, count=2, deep=True, vision=True)
            self.assertTrue(any("visual scoring skipped" in n for n in r["engines"]["notes"]))
            E.ram_gb = lambda: 4.0
            self.assertEqual(E.default_whisper_model(), "base")
        finally:
            E.ram_gb = lambda: 32.0

    def test_09_capabilities(self):
        caps = S.capabilities()
        self.assertTrue(caps["ffmpeg"])
        self.assertIn(caps["encoder"], ["libx264"] + E.HW_ENCODERS)
        self.assertIn("qwen3:8b", caps["llm_models"])
        self.assertNotIn("nomic-embed-text", caps["llm_models"])


if __name__ == "__main__":
    unittest.main()
