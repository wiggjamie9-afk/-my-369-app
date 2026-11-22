"""Rights ledger, campaign tracker, queue and YouTube upload. The Google side is a local fake: these tests prove OUR code follows
the documented protocol (PKCE, resumable chunks, resume after a failure, private by default), not that Google accepts it."""
import base64
import hashlib
import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

os.environ.setdefault("CLIP_STUDIO_DATA", tempfile.mkdtemp(prefix="clipstudio_clip_"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import rights as RT  # noqa: E402
import server as S  # noqa: E402
import youtube as YTB  # noqa: E402


class Job:
    progress, message = 0.0, ""


class FakeGoogle(http.server.BaseHTTPRequestHandler):
    state = {}

    def log_message(self, *a):
        pass

    def _send(self, code, obj=None, headers=None):
        body = json.dumps(obj).encode() if obj is not None else b""
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n)
        st = FakeGoogle.state
        if self.path.startswith("/token"):
            f = {k: v[0] for k, v in urllib.parse.parse_qs(raw.decode()).items()}
            st.setdefault("token_calls", []).append(f)
            if f["grant_type"] == "authorization_code":
                digest = base64.urlsafe_b64encode(hashlib.sha256(f["code_verifier"].encode()).digest()).rstrip(b"=").decode()
                if digest != st.get("challenge") or f["code"] != "GOODCODE":
                    return self._send(400, {"error": "invalid_grant"})
                return self._send(200, {"access_token": "AT1", "refresh_token": "RT1", "expires_in": 3600})
            if f["refresh_token"] != "RT1":
                return self._send(400, {"error": "invalid_grant"})
            return self._send(200, {"access_token": "AT2", "expires_in": 3600})
        if self.path.startswith("/upload/youtube/v3/videos"):
            st["init_auth"] = self.headers.get("Authorization")
            st["meta"] = json.loads(raw)
            st["received"], st["failed_once"] = {}, False
            return self._send(200, headers={"Location": f"http://127.0.0.1:{self.server.server_port}/session/abc"})
        self._send(404, {})

    def do_PUT(self):
        n = int(self.headers.get("Content-Length") or 0)
        data = self.rfile.read(n)
        st = FakeGoogle.state
        rng = self.headers["Content-Range"]
        if rng.startswith("bytes */"):  # status query
            have = sum(len(v) for v in st["received"].values())
            return self._send(308, headers={"Range": f"bytes=0-{have - 1}"} if have else {})
        span, total = rng[6:].split("/")
        start, end = [int(x) for x in span.split("-")]
        if start >= 8192 and not st["failed_once"] and st.get("inject_failure"):
            st["failed_once"] = True
            return self._send(503, {})
        st["received"][start] = data
        if end + 1 == int(total):
            blob = b"".join(st["received"][k] for k in sorted(st["received"]))
            st["assembled"] = blob
            return self._send(200, {"id": "VID123"})
        return self._send(308, headers={"Range": f"bytes=0-{end}"})


class Clipping(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeGoogle)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{cls.srv.server_port}"
        YTB.TOKEN_URL, YTB.UPLOAD_URL = base + "/token", base + "/upload/youtube/v3/videos"
        (S.DATA / "youtube_client.json").write_text(json.dumps({"installed": {"client_id": "cid", "client_secret": "sec"}}))
        # a small fake "exported clip" (content is irrelevant to the protocol tests)
        cls.clip = S.EXPORTS / "test_clip.mp4"
        cls.clip.write_bytes(os.urandom(20000))

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        for n in ("rights", "campaigns", "queue"):
            S.STORE.write(n, [])
        S.YT.disconnect()
        FakeGoogle.state.clear()

    # ---------------- ledger
    def rights(self, **kw):
        d = {"basis": "written_permission", "source": "Stream VOD 12 Nov", "owner": "StreamerX", "proof": "DM screenshot 2026-11-01",
             "credit_text": "Clip from StreamerX (twitch.tv/streamerx)", "platforms": ["youtube"]}
        d.update(kw)
        return RT.add_rights(S.STORE, d)

    def test_01_rights_validation(self):
        self.assertEqual(RT.add_rights(S.STORE, {"basis": "own", "source": "my recording", "platforms": ["youtube"]})["basis"], "own")
        for bad in ({"basis": "nope", "source": "x", "platforms": ["youtube"]},
                    {"basis": "written_permission", "source": "x", "owner": "a", "platforms": ["youtube"]},          # no proof
                    {"basis": "creative_commons", "source": "x", "owner": "a", "proof": "p", "platforms": ["youtube"]},  # no credit
                    {"basis": "own", "source": "x", "platforms": ["myspace"]},
                    {"basis": "own", "source": "", "platforms": ["youtube"]}):
            with self.assertRaises(RT.RightsError):
                RT.add_rights(S.STORE, bad)

    def test_02_rights_ok_platform_and_expiry(self):
        r = self.rights(expires=(date.today() - timedelta(days=1)).isoformat())
        self.assertFalse(RT.rights_ok(r, "youtube")[0])
        r2 = self.rights(platforms=["tiktok"])
        self.assertIn("doesn't cover youtube", RT.rights_ok(r2, "youtube")[1])
        self.assertTrue(RT.rights_ok(self.rights(), "youtube")[0])
        self.assertFalse(RT.rights_ok(None)[0])

    # ---------------- queue guards
    def item(self, **kw):
        d = {"export_file": "test_clip.mp4", "title": "Funny moment", "description": "Highlights", "tags": "gta, clips",
             "rights_id": self.rights()["id"]}
        d.update(kw)
        return RT.save_item(S.STORE, d, S.export_exists)

    def test_03_approve_guards(self):
        with self.assertRaises(RT.RightsError) as c:
            RT.approve_item(S.STORE, self.item(rights_id="")["id"], S.export_exists)
        self.assertIn("no rights entry", str(c.exception))
        with self.assertRaises(RT.RightsError):
            RT.approve_item(S.STORE, self.item(title="x" * 101)["id"], S.export_exists)
        with self.assertRaises(RT.RightsError):
            RT.approve_item(S.STORE, self.item(description="[ADD: credit]")["id"], S.export_exists)
        past = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.assertRaises(RT.RightsError):
            RT.approve_item(S.STORE, self.item(publish_at=past)["id"], S.export_exists)
        fut = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        with self.assertRaises(RT.RightsError) as c:
            RT.approve_item(S.STORE, self.item(publish_at=fut, privacy="public")["id"], S.export_exists)
        self.assertIn("must be private", str(c.exception))
        with self.assertRaises(RT.RightsError):
            RT.save_item(S.STORE, {"export_file": "missing.mp4", "title": "t"}, S.export_exists)
        ok = RT.approve_item(S.STORE, self.item(publish_at=fut)["id"], S.export_exists)
        self.assertEqual(ok["status"], "approved")
        edited = RT.save_item(S.STORE, {"id": ok["id"], "title": "New title"}, S.export_exists)
        self.assertEqual(edited["status"], "draft")                               # changing a clip field un-approves it

    def test_04_credit_added_and_default_private(self):
        it = self.item()
        self.assertEqual(it["privacy"], "private")
        self.assertIn("Credit: Clip from StreamerX", RT.full_description(S.STORE, it))
        own = RT.add_rights(S.STORE, {"basis": "own", "source": "mine", "platforms": ["youtube"]})
        self.assertNotIn("Credit:", RT.full_description(S.STORE, self.item(rights_id=own["id"])))

    def test_05_earnings(self):
        camp = RT.add_campaign(S.STORE, {"name": "Launch week", "rate_per_1000": 2, "flat_fee": 1, "currency": "usd"})
        a = self.item(campaign_id=camp["id"], views=5000, hours_spent=1)
        RT.set_result(S.STORE, a["id"], status="uploaded")
        self.item(campaign_id=camp["id"], views=1000, hours_spent=1)                    # not live: no flat fee yet
        s = RT.summary(S.STORE)["campaigns"][0]
        self.assertEqual((s["views"], s["live"], s["earnings"], s["per_hour"]), (6000, 1, 13.0, 6.5))   # 6 x $2 + 1 x $1
        with self.assertRaises(RT.RightsError):
            RT.add_campaign(S.STORE, {"name": "x", "rate_per_1000": -1})

    def test_06_cannot_delete_rights_backing_approved_clip(self):
        it = self.item()
        RT.approve_item(S.STORE, it["id"], S.export_exists)
        with self.assertRaises(RT.RightsError):
            RT.delete_rights(S.STORE, it["rights_id"])

    # ---------------- YouTube (against the fake)
    def connect(self):
        url = S.YT.auth_url("http://127.0.0.1:8369/oauth/youtube/callback")
        q = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        self.assertEqual(q["code_challenge_method"], ["S256"])
        self.assertEqual(q["scope"], [YTB.SCOPE])
        self.assertEqual(q["access_type"], ["offline"])
        FakeGoogle.state["challenge"] = q["code_challenge"][0]
        S.YT.exchange("GOODCODE", q["state"][0])

    def test_07_oauth_pkce_and_state(self):
        self.assertFalse(S.YT.status()["connected"])
        with self.assertRaises(YTB.YouTubeError):
            S.YT.exchange("GOODCODE", "bogus-state")
        self.connect()
        self.assertTrue(S.YT.status()["connected"])
        self.assertEqual(FakeGoogle.state["token_calls"][0]["client_secret"], "sec")

    def test_08_resumable_upload_with_failure_and_resume(self):
        self.connect()
        FakeGoogle.state["inject_failure"] = True
        seen = []
        vid = S.YT.upload(self.clip, YTB.build_meta("T", "D", ["a"]), seen.append, chunk=8192)
        self.assertEqual(vid, "VID123")
        st = FakeGoogle.state
        self.assertEqual(st["assembled"], self.clip.read_bytes())                  # every byte arrived, in order, once
        self.assertEqual(st["meta"]["status"]["privacyStatus"], "private")
        self.assertEqual(st["init_auth"], "Bearer AT1")
        self.assertTrue(st["failed_once"])                                           # the 503 happened and we recovered
        self.assertTrue(len(seen) >= 1)

    def test_09_refresh_token_used_when_expired(self):
        self.connect()
        tok = json.loads(S.YT.token_file.read_text())
        tok["expires_at"] = 0
        S.YT.token_file.write_text(json.dumps(tok))
        S.YT.upload(self.clip, YTB.build_meta("T", "D", []), None, chunk=1 << 20)
        self.assertEqual(FakeGoogle.state["init_auth"], "Bearer AT2")

    def test_10_schedule_forces_private(self):
        m = YTB.build_meta("T", "D", ["a"], privacy="public", publish_at="2030-01-01T09:00:00Z")
        self.assertEqual((m["status"]["privacyStatus"], m["status"]["publishAt"]), ("private", "2030-01-01T09:00:00Z"))
        self.assertEqual(len(YTB.build_meta("x" * 200, "", [])["snippet"]["title"]), 100)

    def test_11_server_upload_flow_and_guards(self):
        with self.assertRaises(S.ApiError):                                          # not approved
            S.do_queue_upload(Job(), self.item()["id"])
        self.connect()
        it = self.item()
        RT.approve_item(S.STORE, it["id"], S.export_exists)
        res = S.do_queue_upload(Job(), it["id"])
        self.assertEqual((res["id"], res["privacy"]), ("VID123", "private"))
        row = next(i for i in S.STORE.read("queue") if i["id"] == it["id"])
        self.assertEqual((row["status"], row["url"]), ("uploaded", "https://youtu.be/VID123"))
        self.assertIn("Credit: Clip from StreamerX", FakeGoogle.state["meta"]["snippet"]["description"])
        # rights expire between approval and upload -> blocked at upload time
        it2 = self.item()
        RT.approve_item(S.STORE, it2["id"], S.export_exists)
        rows = S.STORE.read("rights")
        for r in rows:
            r["expires"] = (date.today() - timedelta(days=1)).isoformat()
        S.STORE.write("rights", rows)
        with self.assertRaises(S.ApiError) as c:
            S.do_queue_upload(Job(), it2["id"])
        self.assertIn("expired", str(c.exception))

    def test_12_api_surface(self):
        self.assertEqual(S.clipping_api("GET", "/api/rights", {}, {})[0], 200)
        code, row, _ = S.clipping_api("POST", "/api/rights", {}, {"basis": "own", "source": "mine", "platforms": ["youtube"]})
        self.assertEqual(code, 200)
        self.assertEqual(S.clipping_api("POST", "/api/rights", {}, {"basis": "own"})[0], 400)
        self.assertEqual(S.clipping_api("GET", "/api/youtube/status", {}, {})[0], 200)
        code, p, _ = S.clipping_api("GET", "/api/youtube/auth", {}, {}, "127.0.0.1:8369")
        self.assertIn("redirect_uri=http%3A%2F%2F127.0.0.1%3A8369%2Foauth%2Fyoutube%2Fcallback", p["url"])
        self.assertEqual(S.clipping_api("POST", "/api/queue/nope/approve", {}, {})[0], 404)


if __name__ == "__main__":
    unittest.main()
