# Clip Studio

Local VOD → Shorts/Reels/TikTok pipeline: **find the moment → cut → reframe 9:16 → caption → export 1080×1920 MP4.**

```bash
# needs: python3 + ffmpeg on PATH
python3 server.py            # http://127.0.0.1:8369   (PORT=9000 python3 server.py to change)
pip install -r requirements-optional.txt   # optional extras
```

## Workflow
1. **Media bin** – add a file, paste a URL (needs `yt-dlp`), or drop files into `data/media/`. Record gameplay with OBS and drop it in.
2. **Find highlights** – ranks windows by audio-energy spikes + scene-cut density (ffmpeg, no extra deps). Click a card to load it.
3. **Trim** – drag the yellow `[ ]` handles or press `I` / `O`.
4. **Reframe** – drag the cyan 9:16 box (keys a keyframe at the playhead), add punch-in zoom, or hit **Auto-track** (faces via OpenCV, else motion). Or choose *Fit + blurred background*.
5. **Captions** – **Transcribe** (faster-whisper / openai-whisper / whisper.cpp) or type lines by hand. Word-by-word highlight, hook title, font/size/position.
6. **Export** – H.264 + AAC, loudness-normalised to -14 LUFS, burned-in captions via libass.

Shortcuts: `Space` play · `I`/`O` in/out · `K` keyframe · `←/→` frame step (`Shift` = 5 s) · wheel zoom timeline.

## How it maps to the "22 repos" stack
| Need | Used here |
|---|---|
| download | yt-dlp (optional) |
| timeline/cut/mix/filters/render | ffmpeg (the engine under OpenCut, Kdenlive, Shotcut, Editly, PyAV) |
| tracking/crop | OpenCV faces (optional) + built-in motion tracker |
| transcripts / word timing | faster-whisper, openai-whisper, whisper.cpp (optional) |
| captions | ASS subtitles rendered by libass |

Not wired in (add if you need them): speaker diarization (pyannote), object overlays (supervision), upscaling / frame interpolation (Real-ESRGAN, RIFE).

## Notes
- Server binds to `127.0.0.1` only and has no auth – don't expose it.
- Preview needs a browser-playable codec (H.264/VP9 in mp4/webm). Exotic sources (e.g. HEVC mkv) may need transcoding to H.264 first.
- Only download/clip footage you own or have permission to use (game trailers, streams and VODs are usually copyrighted).
