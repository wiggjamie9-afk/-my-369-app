# Clip Studio

Local long-video → Shorts/Reels/TikTok studio. **Find the moment → cut → reframe → caption → brand → export** — and a song mode that turns audio into a visualizer clip. Runs entirely on your machine.

```bash
./run.sh            # macOS / Linux          (./run.sh --install adds the optional extras in a .venv)
run.bat             # Windows                (run.bat --install)
python3 server.py   # anywhere               -> http://127.0.0.1:8369
```
Needs **Python 3.9+** and **ffmpeg 5+** on PATH. Everything else is optional and auto-detected (header chips show what was found).

## What it does
| Step | How |
|---|---|
| **Find highlights** | Audio-energy spikes + scene-cut density. Tick **Speech-aware ranking** to also transcribe the top candidates and have a local LLM (Ollama, e.g. a Qwen model) score hooks, payoffs and takeaways; add **vision** to have a vision model judge sampled frames. No LLM? A rule-based scorer is used. Each card gets a suggested hook title + transcript. |
| **Auto-produce** | One click: rank → transcribe → auto-reframe → caption → export the top N clips. |
| **Reframe** | Draggable crop box with keyframes + punch-in zoom, Auto-track (OpenCV faces, else motion), or Fit + blurred background. |
| **Formats** | 9:16, 4:5, 1:1, 16:9. |
| **Captions** | Word-by-word highlight, hook title, font/size/position; edit lines by hand. |
| **Branding** | Watermark/handle and a retention progress bar. |
| **Song mode** | Drop an mp3/wav/m4a: gradient equalizer visualizer + title + captions (lyrics, if you transcribe/type them). |
| **Export** | H.264 + AAC, -14 LUFS loudness, burned-in captions. Uses **NVENC / VideoToolbox / QSV / AMF** automatically when they work, else x264. |

Shortcuts: `Space` play · `I`/`O` in/out · `K` keyframe · `←/→` frame step (`Shift` = 5 s) · wheel zoom timeline.

## Jan and OpenFilm
- **Jan** ([jan.ai](https://jan.ai), offline ChatGPT alternative) works as the AI backend for speech-aware ranking. In Jan: *Settings → Local API Server → Start* (default `http://127.0.0.1:1337/v1`). Its models show up as `jan:<model>` next to Ollama's in the AI dropdown; the header chips show which backends were found. Works with any OpenAI-compatible local server (LM Studio, llama.cpp): set `CLIP_STUDIO_OPENAI_URL` (and `CLIP_STUDIO_OPENAI_KEY` if you enabled a key). Model size is estimated from the name (`…-4b-…` ≈ 2.4 GB) for the memory-fit check.
- **OpenFilm** ([openfilm/openfilm](https://github.com/openfilm/openfilm), MIT, an AI video agent + editor): **Send to OpenFilm** writes a project folder under `data/films/` (`film.html` + captions + a link to your source) so you can keep editing it there or hand it to a coding agent. Open it with `npx -y openfilm@latest open <folder>` (needs Node 22.2+; the app prints the exact command). Carried over: trim, canvas size, reframe pan, captions. Not carried over: hook title, watermark, progress bar, punch-in zoom, blurred background. **Written from OpenFilm's published draft spec (protocol 0.1) and not yet opened in OpenFilm itself**, so tell us if its strict reader rejects anything.

## Optional extras (install what you want)
- `pip install -r requirements-optional.txt` → yt-dlp, faster-whisper, OpenCV.
- **AI ranking:** install [Ollama](https://ollama.com), then e.g. `ollama pull qwen3:8b` (text) and any vision model. Set `CLIP_STUDIO_LLM` / `CLIP_STUDIO_VISION` to pin models, `OLLAMA_HOST` for a remote box.
- **Transcription model:** defaults to `small` on CPU, `medium`/`large-v3` on an NVIDIA GPU (by VRAM). Override with `CLIP_STUDIO_WHISPER`. Without faster-whisper: openai-whisper or whisper.cpp (`WHISPER_CPP_MODEL`) also work.
- `CLIP_STUDIO_ENCODER=libx264` forces software encoding; `CLIP_STUDIO_DATA` moves the data folder.

## Low-memory machines (e.g. 8 GB MacBook)
The app reads your RAM and only auto-picks AI models whose weights fit in ~40% of it, so macOS/Windows, Whisper and the app keep room. On 8 GB that means a ~4B text model (e.g. `ollama pull qwen3:4b`; check ollama.com/library for current tags), Whisper `small`, and vision scoring skipped unless you install a small vision model. You can still pick any installed model by hand in the dropdown. Close other heavy apps while ranking.

## Tests
`python3 -m unittest discover -s tests` — synthetic-media end-to-end tests (analysis, formats, visualizer, auto-produce). A fake Ollama server checks the AI plumbing, not model quality.

## Honest limits
- Speech/vision ranking is only as good as the model you plug in; the rule-based fallback is English-only and basic.
- Tested here on synthetic media. Not exercised in this repo's tests: real Whisper transcription, OpenCV face tracking, yt-dlp, GPU encoders, and the Windows launcher.
- Server binds to `127.0.0.1` with no auth – don't expose it.
- Preview needs a browser-playable codec (H.264/VP9 in mp4/webm); exotic sources may need transcoding first.
- Only download/clip footage you own or have permission to use (game footage, trailers, streams and music are usually copyrighted).
