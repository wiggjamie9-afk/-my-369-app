"""MCP server tests: run mcp_server.py as a real subprocess and speak JSON-RPC to it, against a live Clip Studio on a random port.
Proves the protocol handshake, the tools, and the safety model (no approve/upload/rights-creation for agents).
Not tested here: a real Claude Desktop / Claude Code client."""
import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path

os.environ.setdefault("CLIP_STUDIO_DATA", tempfile.mkdtemp(prefix="clipstudio_mcp_"))
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import rights as RT  # noqa: E402
import server as S  # noqa: E402


class Client:
    def __init__(self, url):
        env = dict(os.environ, CLIP_STUDIO_URL=url)
        self.p = subprocess.Popen([sys.executable, str(ROOT / "mcp_server.py")], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True, env=env)
        self.n = 0

    def raw(self, line):
        self.p.stdin.write(line + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())

    def rpc(self, method, params=None):
        self.n += 1
        return self.raw(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}))

    def call(self, name, args=None):
        r = self.rpc("tools/call", {"name": name, "arguments": args or {}})
        res = r["result"]
        text = res["content"][0]["text"]
        return res["isError"], (text if res["isError"] else json.loads(text))

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=5)
        self.p.stdout.close()
        self.p.stderr.close()


class Mcp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), S.Handler)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_port}"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=15:duration=14",
                        "-f", "lavfi", "-i", "aevalsrc='sin(2*PI*220*t)*(0.05+0.9*between(t,4,7))':s=44100:d=14",
                        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                        str(S.MEDIA / "mcp_test.mp4")], check=True)
        cls.c = Client(cls.url)

    @classmethod
    def tearDownClass(cls):
        cls.c.close()
        cls.srv.shutdown()
        cls.srv.server_close()

    def test_01_handshake_and_tools(self):
        r = self.c.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "0"}})
        self.assertEqual(r["result"]["serverInfo"]["name"], "clip-studio")
        self.assertEqual(r["result"]["protocolVersion"], "2025-06-18")
        self.c.p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")   # notification: no reply
        self.c.p.stdin.flush()
        names = {t["name"] for t in self.c.rpc("tools/list")["result"]["tools"]}
        self.assertTrue({"cs_find_highlights", "cs_make_clips", "cs_queue_draft", "cs_plan_calendar", "cs_build_carousel"} <= names)
        for bad in ("approve", "upload", "delete", "add_rights", "remove", "publish"):
            self.assertFalse(any(bad in n for n in names), bad)                 # safety model: agents can't do these
        for t in self.c.rpc("tools/list")["result"]["tools"]:
            self.assertEqual(t["inputSchema"]["type"], "object")

    def test_02_protocol_errors(self):
        self.assertEqual(self.c.rpc("nope")["error"]["code"], -32601)
        self.assertEqual(self.c.rpc("tools/call", {"name": "cs_approve", "arguments": {}})["error"]["code"], -32602)
        self.assertEqual(self.c.raw("{not json")["error"]["code"], -32700)
        self.assertEqual(self.c.rpc("ping")["result"], {})

    def test_03_status_and_media(self):
        err, st = self.c.call("cs_status")
        self.assertFalse(err)
        self.assertTrue(st["capabilities"]["ffmpeg"])
        err, media = self.c.call("cs_list_media")
        self.assertIn("mcp_test.mp4", [m["name"] for m in media])

    def test_04_find_highlights_and_make_clips(self):
        err, r = self.c.call("cs_find_highlights", {"name": "mcp_test.mp4", "clip_len": 5, "count": 2, "wait_seconds": 60})
        self.assertFalse(err)
        self.assertEqual(r["status"], "done")
        self.assertTrue(r["result"]["clips"])
        self.assertNotIn("energy", r["result"])                                 # big arrays stripped for the agent
        err, r = self.c.call("cs_make_clips", {"name": "mcp_test.mp4", "count": 1, "clip_len": 5, "speech_aware": False, "wait_seconds": 90})
        self.assertFalse(err)
        self.assertEqual(r["status"], "done")
        f = r["result"]["clips"][0]["file"]
        self.assertTrue((S.EXPORTS / f).is_file())
        err, ex = self.c.call("cs_list_exports")
        self.assertIn(f, [e["name"] for e in ex])
        self.__class__.export = f

    def test_05_queue_draft_needs_existing_rights_and_stays_draft(self):
        f = getattr(self.__class__, "export", None) or next(S.EXPORTS.glob("*.mp4")).name
        err, msg = self.c.call("cs_queue_draft", {"export_file": f, "title": "T"})
        self.assertTrue(err)
        self.assertIn("rights_id", msg)
        self.assertIn("ask the human", msg)
        entry = RT.add_rights(S.STORE, {"basis": "own", "source": "mine", "platforms": ["youtube"]})          # the HUMAN creates this
        err, item = self.c.call("cs_queue_draft", {"export_file": f, "title": "My clip", "rights_id": entry["id"], "tags": ["a", "b"]})
        self.assertFalse(err)
        self.assertEqual(item["status"], "draft")
        row = next(i for i in S.STORE.read("queue") if i["id"] == item["id"])
        self.assertEqual((row["status"], row["privacy"]), ("draft", "private"))
        err, q = self.c.call("cs_queue_list")
        self.assertIn(item["id"], [i["id"] for i in q])
        err, rights = self.c.call("cs_list_rights")
        self.assertEqual(rights[0]["basis"], "own")

    def test_06_calendar_and_carousel(self):
        brief = {"business": "Test Plumbing", "niche": "plumber", "city": "Perth", "platforms": ["instagram"], "posts_per_week": 2,
                 "facts": ["We fix taps same day"]}
        err, r = self.c.call("cs_plan_calendar", {"brief": brief, "weeks": 2, "writer": "off", "wait_seconds": 30})
        self.assertFalse(err)
        self.assertEqual(r["status"], "done")
        self.assertGreater(r["posts"], 0)
        self.assertGreater(r["posts_needing_owner_input"], 0)                    # missing facts are flagged, not invented
        self.assertIn("do not invent", r["note"])
        err, c = self.c.call("cs_build_carousel", {"slides": [{"kind": "cover", "title": "Hi"}, {"kind": "text", "body": "Body"}], "wait_seconds": 60})
        self.assertFalse(err)
        self.assertEqual(len(c["result"]["slides"]), 2)
        err, m = self.c.call("cs_plan_calendar", {"brief": {}})
        self.assertTrue(err)

    def test_07_missing_server_gives_helpful_error(self):
        dead = Client("http://127.0.0.1:9")
        try:
            err, msg = dead.call("cs_status")
            self.assertTrue(err)
            self.assertIn("isn't running", msg)
            self.assertTrue(dead.rpc("tools/list")["result"]["tools"])           # protocol still works without the server
        finally:
            dead.close()


if __name__ == "__main__":
    unittest.main()
