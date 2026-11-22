# Video system brief for Kim

Paste this whole page to Kim. The working code is in **`clip-studio-bundle.py`** (one file; run `python3 clip-studio-bundle.py`). Kim can build on it, or rebuild the same behaviour another way.

---

## 1. What we're building
A **permission-first video clipping and content system** that runs on a Mac with no GPU:

> source video you have the right to use → find the best moments → cut → reframe to vertical → caption → export → record the permission → queue → **you approve** → upload to YouTube (private) → you publish. TikTok/Instagram are posted by hand (or through a scheduler).

It also makes carousels, slideshow/visualizer videos, and client content calendars, and an AI agent can drive it through a tool interface (MCP), but only a human approves and uploads.

## 2. Hard rules (do not break these)
1. **Permission first.** A clip can't be approved without a rights entry (own footage, written permission, a clipping campaign's terms, a licence, Creative Commons, or public domain) that has proof, covers the platform and hasn't expired. Credit text is added to the description automatically.
2. **No scraping and no unattended auto-reposting** of other people's streams or videos. Platforms (Meta, YouTube) penalise unoriginal, repetitive content, and unlicensed reposting is copyright infringement.
3. **Agents propose, humans approve.** Agents may make clips, carousels, calendars and *private drafts*. They may **not** create rights entries, approve, upload or delete.
4. **Uploads go up private.** Google restricts videos uploaded through the API by unaudited projects to private. The user reviews and publishes in YouTube Studio.
5. **Never invent facts** in captions or calendars. Missing facts become `[ADD: ...]` prompts that block approval.
6. **Be honest about AI.** Say when content is AI-generated or altered where the platform asks. Don't impersonate real people. Don't present game footage as something it isn't.
7. **Sample data is labelled as sample data.** Don't claim anything is tested that isn't.

## 3. Pipeline and specs
- **Formats:** 9:16 (1080×1920, default), 4:5 (1080×1350), 1:1 (1080×1080), 16:9 (1920×1080).
- **Length:** YouTube Shorts allow up to 3 minutes if vertical or square. Highlight clips default to ~25 s (5–90 s selectable); the user can trim any length. Start with 15–60 s and check retention.
- **Highlights:** audio-energy spikes plus scene-cut density; optional speech-aware re-ranking (transcribe the top candidates, then a local AI scores hooks/payoffs; rule-based fallback if no AI).
- **Reframe:** draggable 9:16 crop with keyframes and punch-in zoom, auto-track (faces with OpenCV, else motion), or fit + blurred background.
- **Captions:** word-by-word highlight, hook title, watermark/handle, optional progress bar; audio normalised to -14 LUFS.
- **Encode:** H.264 + AAC; picks a hardware encoder (NVENC, VideoToolbox, QSV, AMF) if one works, else x264.
- **Music/audio files:** exported as a gradient equalizer visualizer clip.
- **Carousels:** numbered PNGs + zip (+ optional slideshow video), up to 10 slides (YouTube Community posts; third-party guides say 10, Google's page says 5, so check).
- **Content planner:** brief + the owner's real facts → 4-week calendar → edit/approve → CSV for a scheduler + approval document for the client.
- **Earnings tracker:** rate per 1,000 views, flat fees, hours spent, so the user sees real income per hour.

## 4. Hardware and cost constraints
- Target machine: **MacBook with Apple A18 Pro and 8 GB memory**. Everything must be CPU-friendly.
- Pick local AI models that fit in ~40% of RAM (≈ a 4B text model, Whisper `small`); skip vision scoring unless a small vision model is installed.
- Free GPU notebooks (Kaggle ~30 h/week, Colab) are for occasional heavy jobs only, not for serving anything live.

## 5. Status
| Part | Status |
|---|---|
| Highlights, reframe, captions, formats, export, visualizer | Built and tested on synthetic media |
| Carousel maker, content planner, rights ledger, campaign tracker, queue | Built and tested |
| YouTube upload (OAuth + PKCE, resumable, private) | Built; tested **only against a local fake of Google** |
| MCP agent server | Built; tested with my own harness, **not a real MCP client** |
| OpenFilm project export | Built from its draft spec; **not opened in OpenFilm** |
| TikTok / Instagram direct posting | **Not built.** Both need app approval (TikTok unaudited apps post private only; Instagram needs Meta App Review and a public video URL). Post by hand or use a scheduler |
| Real Whisper transcription, OpenCV tracking, yt-dlp, GPU encoders | Code present, **not exercised here** |

## 6. One-time setup for the user
1. Install ffmpeg (5+) and Python 3.9+. Run `python3 clip-studio-bundle.py`, open http://127.0.0.1:8369.
2. YouTube: in Google Cloud enable *YouTube Data API v3*, create an OAuth client of type **Desktop app**, save its JSON as `data/youtube_client.json`, press *Connect YouTube* on `/clipping`.
3. Optional AI: install Ollama (e.g. a ~4B model) or run Jan's Local API Server; `pip install faster-whisper` for transcripts.
4. Agents: add `mcp_server.py` to the agent's MCP config (see `AGENT_PLAYBOOK.md`).

## 7. Acceptance checklist
- [ ] A 25 s clip exports at 1080×1920 with readable captions.
- [ ] A clip with no rights entry **cannot** be approved. An expired entry blocks upload.
- [ ] The credit line appears in the uploaded video's description.
- [ ] A test upload lands on YouTube as **private**.
- [ ] An agent can make clips and queue a draft, and **cannot** approve or upload.
- [ ] Calendar posts missing facts show `[ADD: ...]` and can't be approved.
- [ ] Everything runs on the 8 GB Mac without freezing it.

## 8. Open questions for the user
- Which source or campaign do we have **written permission** for first?
- Which platforms first (YouTube Shorts only, or TikTok and Instagram by hand too)?
- Real cost per minute and per clip, so prices/targets can be set.
