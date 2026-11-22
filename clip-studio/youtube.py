"""YouTube upload through the official YouTube Data API v3 (resumable upload, OAuth 2.0 installed-app flow with PKCE).

What you must do once (this code can't do it for you):
  1. In Google Cloud Console create a project, enable "YouTube Data API v3", and create an OAuth client of type "Desktop app".
  2. Save the downloaded JSON as  <data folder>/youtube_client.json
  3. Open Clipping > "Connect YouTube" and approve access to the account/channel you want to upload to.

Limits you should know (from Google's docs, which may change; check the live reference):
  * Videos uploaded through videos.insert by an API project that has NOT passed Google's audit are restricted to PRIVATE viewing.
    So this module uploads private by default; publish from YouTube Studio after you've reviewed, or complete Google's audit.
  * Quota for uploads is limited per project (the docs I found disagree on the exact figures).
This module has been tested only against a local fake of Google's endpoints, never against the real service.
"""
import base64
import hashlib
import http.client
import json
import secrets
import time
import urllib.parse
from pathlib import Path

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"
SCOPE = "https://www.googleapis.com/auth/youtube.upload"
CHUNK = 8 * 1024 * 1024  # must be a multiple of 256 KiB


class YouTubeError(Exception):
    pass


def _request(method, url, headers=None, body=None, timeout=120):
    """Plain http.client request: returns (status, headers_dict, bytes). Works for https and (in tests) http."""
    u = urllib.parse.urlsplit(url)
    conn_cls = http.client.HTTPSConnection if u.scheme == "https" else http.client.HTTPConnection
    conn = conn_cls(u.netloc, timeout=timeout)
    try:
        conn.request(method, (u.path or "/") + (("?" + u.query) if u.query else ""), body=body, headers=headers or {})
        r = conn.getresponse()
        data = r.read()
        return r.status, {k.lower(): v for k, v in r.getheaders()}, data
    finally:
        conn.close()


def build_meta(title, description, tags, privacy="private", publish_at="", category="22"):
    status = {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}
    if publish_at:  # scheduled publish needs the video to be private until then
        status["privacyStatus"] = "private"
        status["publishAt"] = publish_at
    clean, total = [], 0
    for t in tags:
        if total + len(t) > 450:
            break
        clean.append(t)
        total += len(t) + 1
    return {"snippet": {"title": title[:100], "description": description[:5000], "tags": clean, "categoryId": category}, "status": status}


class YouTube:
    def __init__(self, folder):
        self.dir = Path(folder)
        self.client_file = self.dir / "youtube_client.json"
        self.token_file = self.dir / "youtube_token.json"
        self._pending = {}

    # ------------------------------------------------------------------ setup state
    def _client(self):
        try:
            j = json.loads(self.client_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise YouTubeError(f"missing {self.client_file.name}: create a Desktop-app OAuth client in Google Cloud and save its JSON there")
        c = j.get("installed") or j.get("web") or j
        if not c.get("client_id"):
            raise YouTubeError("youtube_client.json has no client_id")
        return c

    def _token(self):
        try:
            return json.loads(self.token_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def status(self):
        return {"configured": self.client_file.is_file(), "connected": bool(self._token().get("refresh_token")),
                "note": "Uploads are private until Google audits your API project; publish from YouTube Studio."}

    def disconnect(self):
        try:
            self.token_file.unlink()
        except OSError:
            pass

    # ------------------------------------------------------------------ OAuth (loopback + PKCE)
    def auth_url(self, redirect_uri):
        c = self._client()
        state, verifier = secrets.token_urlsafe(16), secrets.token_urlsafe(48)
        self._pending[state] = (verifier, redirect_uri)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
        q = {"client_id": c["client_id"], "redirect_uri": redirect_uri, "response_type": "code", "scope": SCOPE,
             "access_type": "offline", "prompt": "consent", "state": state, "code_challenge": challenge,
             "code_challenge_method": "S256"}
        return AUTH_URL + "?" + urllib.parse.urlencode(q)

    def _token_call(self, form):
        body = urllib.parse.urlencode(form)
        st, _, data = _request("POST", TOKEN_URL, {"Content-Type": "application/x-www-form-urlencoded"}, body)
        try:
            j = json.loads(data or b"{}")
        except ValueError:
            j = {}
        if st != 200 or "access_token" not in j:
            raise YouTubeError("Google rejected the sign-in: " + str(j.get("error_description") or j.get("error") or st))
        return j

    def exchange(self, code, state):
        if state not in self._pending:
            raise YouTubeError("sign-in expired or didn't start here; press Connect YouTube again")
        verifier, redirect_uri = self._pending.pop(state)
        c = self._client()
        j = self._token_call({"grant_type": "authorization_code", "code": code, "client_id": c["client_id"],
                              "client_secret": c.get("client_secret", ""), "redirect_uri": redirect_uri, "code_verifier": verifier})
        if not j.get("refresh_token"):
            raise YouTubeError("Google didn't return a refresh token; remove this app at myaccount.google.com/permissions and connect again")
        tok = {"refresh_token": j["refresh_token"], "access_token": j["access_token"], "expires_at": time.time() + int(j.get("expires_in", 3600)) - 60}
        self.dir.mkdir(parents=True, exist_ok=True)
        self.token_file.write_text(json.dumps(tok), encoding="utf-8")
        try:
            self.token_file.chmod(0o600)
        except OSError:
            pass
        return True

    def _access(self):
        tok = self._token()
        if not tok.get("refresh_token"):
            raise YouTubeError("YouTube isn't connected yet")
        if tok.get("access_token") and tok.get("expires_at", 0) > time.time():
            return tok["access_token"]
        c = self._client()
        j = self._token_call({"grant_type": "refresh_token", "refresh_token": tok["refresh_token"], "client_id": c["client_id"],
                              "client_secret": c.get("client_secret", "")})
        tok.update(access_token=j["access_token"], expires_at=time.time() + int(j.get("expires_in", 3600)) - 60)
        self.token_file.write_text(json.dumps(tok), encoding="utf-8")
        return tok["access_token"]

    # ------------------------------------------------------------------ upload
    def upload(self, path, meta, progress=None, chunk=CHUNK):
        """Resumable upload. Returns the video id. `progress(fraction)` is called after each chunk."""
        path = Path(path)
        size = path.stat().st_size
        if size == 0:
            raise YouTubeError("the clip file is empty")
        token = self._access()
        hdr = {"Authorization": "Bearer " + token, "Content-Type": "application/json; charset=UTF-8",
               "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}
        st, h, data = _request("POST", UPLOAD_URL + "?uploadType=resumable&part=snippet,status", hdr, json.dumps(meta))
        if st != 200 or "location" not in h:
            raise YouTubeError(f"YouTube refused to start the upload (HTTP {st}): {data[:200].decode('utf-8', 'replace')}")
        session = h["location"]
        sent = 0
        with open(path, "rb") as f:
            while sent < size:
                f.seek(sent)
                buf = f.read(min(chunk, size - sent))
                end = sent + len(buf) - 1
                put = {"Content-Length": str(len(buf)), "Content-Range": f"bytes {sent}-{end}/{size}", "Content-Type": "video/mp4"}
                for attempt in range(4):
                    try:
                        st, h, data = _request("PUT", session, put, buf, timeout=300)
                    except (OSError, http.client.HTTPException):
                        st, h, data = 0, {}, b""
                    if st in (200, 201):
                        j = json.loads(data or b"{}")
                        if "id" not in j:
                            raise YouTubeError("upload finished but YouTube returned no video id")
                        if progress:
                            progress(1.0)
                        return j["id"]
                    if st == 308:
                        break
                    if st in (0, 500, 502, 503, 504) and attempt < 3:  # ask where the server got to, then resume
                        time.sleep(1 + attempt)
                        try:
                            qs, qh, _ = _request("PUT", session, {"Content-Length": "0", "Content-Range": f"bytes */{size}"})
                        except (OSError, http.client.HTTPException):
                            continue
                        if qs == 308 and "range" in qh:
                            got = int(qh["range"].split("-")[-1]) + 1
                            if got >= sent + len(buf):  # the server already has this chunk
                                break
                            if got != sent:
                                sent = got
                                f.seek(sent)
                                buf = f.read(min(chunk, size - sent))
                                end = sent + len(buf) - 1
                                put = {"Content-Length": str(len(buf)), "Content-Range": f"bytes {sent}-{end}/{size}", "Content-Type": "video/mp4"}
                        continue
                    raise YouTubeError(f"upload failed (HTTP {st}): {data[:200].decode('utf-8', 'replace')}")
                else:
                    raise YouTubeError("upload kept failing; try again later")
                sent = end + 1
                if progress:
                    progress(sent / size)
        raise YouTubeError("upload ended without a response from YouTube")
