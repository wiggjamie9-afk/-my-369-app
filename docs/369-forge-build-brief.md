# 369 Forge: Clover Studio, build brief

You are continuing development of **Vitruvian 369 Forge: Clover Studio**, an AI image and video studio for making social media clips (TikTok, YouTube Shorts, Instagram Reels, YouTube long-form). The current working app is `generator.html` (a single HTML file, about 1,600 lines). Read it fully before changing anything, and keep its style, structure and naming.

---

## 1. Product goal

One app that takes a creator from an idea to a finished, upload-ready clip:

idea → script → hook options → storyboard → generated shots (best of several AI models) → voiceover → captions → music → one exported MP4 → thumbnail → posting plan → performance tracking.

The core idea is the **clover system**: every generation runs on up to four AI models ("leaves") at once, an AI judge scores each result against the prompt, the prompt is improved from the judge's notes, and the loop retries until a result reaches the target score or the round limit.

---

## 2. Hard rules (do not break these)

1. **Original code only.** Do not copy code, assets, branding or prompt libraries from Higgsfield, Runway, Pika, HeyGen or any other product. Features may be inspired by them; implementation must be written from scratch.
2. **Models only through official APIs or open-source releases.** Never scrape, reverse-engineer or bypass a service's access controls.
3. **No secret keys in browser code.** The Hugging Face token the user pastes is stored in their own browser only. Any other paid API key (Google Veo, Runway, MiniMax, ElevenLabs, etc.) must live on a server (see section 6).
4. **Real people:** lip-sync, avatar and voice-clone features may only be used with the user's own face and voice, or with recorded consent. Show a consent checkbox before any face or voice upload, and do not add features for imitating real people without consent.
5. **Platform rules:** no fake engagement, no bots, no auto-posting spam, no mass-produced near-identical videos. Add a reminder in the export screen to label realistic AI content ("altered or synthetic content" on YouTube, the AI-generated label on TikTok).
6. **Cost safety:** every action that spends credits must show the maximum number of generations before it runs, and every loop must have a hard limit.

---

## 3. Current tech stack

- One file: `generator.html` with inline CSS and an ES module script. No build step, no framework.
- AI calls: `@huggingface/inference@4.13.32`, loaded lazily from `https://cdn.jsdelivr.net/npm/@huggingface/inference@4.13.32/+esm` on first use so the page still works offline.
- Client: `new InferenceClient(token)`. Methods in use: `textToImage`, `imageToImage`, `textToVideo`, `imageToVideo`, `chatCompletion`. Each call takes `{ provider, model, inputs, parameters }` and an options object with `signal` (AbortController).
- Storage:
  - `localStorage["forge_settings"]`: token, judge model and provider, leaves, presets, current mode.
  - `localStorage["forge_stats"]`: `{ runs, generations, seconds, rounds, wins: { image: {model: n}, video: {model: n} } }`.
  - `localStorage["forge_storyboard"]`: `{ shots: [{ id, prompt, clipUid }], length, clipSeconds, continueFrames }`.
  - IndexedDB `forge_gallery`, store `items`, key `uid`: `{ uid, mode, model, prompt, score, blob, timestamp }`.
- Wrap every storage read and write in try/catch; the app must still work if storage is blocked.
- Visual style: CSS variables `--bg-main #0c0a0e`, `--panel-bg #14121a`, `--accent-gold #dfb76c`, `--accent-purple #7045af`, `--text-light #e6dfd5`, `--text-muted #827b87`, `--border-color #2b2533`, `--input-bg #070609`. Gold uppercase letter-spaced headings, dark rounded panels. It must work at phone width (390px) with no horizontal scrolling.
- Escape all model output and user text with `escapeHtml()` before inserting it into HTML. Judge replies and prompts are untrusted text.

---

## 4. Already built (keep working, do not regress)

**Tabs:** Create, Storyboard, Library, Stats, Settings.

**Create**
- Image / Video mode.
- Prompt, Style preset (9: none, cinematic, anime, 3D animated, 2D cartoon, claymation, documentary, dreamlike, comic), Shape (16:9, 9:16, 1:1, 21:9), Camera move for video (10 presets).
- Character / start image upload and a character description that is added to every prompt.
- Target score (6–9), max rounds (1–5), "Director rewrite" toggle (a language model expands the prompt first).
- Cost hint: "N leaves × up to R rounds = at most X generations".
- Clover rounds: every active leaf generates in parallel; each finished result is judged (videos are judged from 4 frames sampled across the clip); a score of at least the target stops the round early and aborts the remaining leaves; otherwise the best result's `improved_prompt` becomes the next round's prompt.
- Each result card has "👍 Use this" (accepts it immediately; after the run ends it saves that card to the Library too) and Download.
- Director notes box: its text is sent to the judge as the highest-priority instruction.
- Stop button aborts everything in flight.
- Winner is saved to the Library. The winner banner offers "Animate this →" (image winner becomes the start image for a video run), "Add to storyboard" and "Use as reference".
- If the judge fails, the run stops after one round and asks the user to pick with 👍.

**Judge contract:** the judge model gets the target prompt, the user's notes and the image or frames, and must reply with JSON only:
`{"score": 0-10, "issues": ["short issue", ...], "improved_prompt": "..."}`. Parse the first `{...}` block, clamp the score to 0–10, and keep at most 5 issues.

**Storyboard**
- Target length (15 / 32 / 60 / 92 s) ÷ seconds per clip (5 / 10 / 15) gives the shot count; "Make shot list" creates the shots.
- Each shot has its own prompt and runs the clover engine in video mode. With "continue" on, each shot starts from the previous clip's last frame (image-to-video); otherwise it starts from the character image.
- Generate one shot or all shots; play the whole scene back to back; download all clips numbered in order; show total duration.

**Library:** all winners with Download, Use as reference, To storyboard, Delete.

**Stats:** runs, generations, rounds per run, generations per winner, time per winner, and a leaf-wins table. Smart routing (Settings): after 5 runs in a mode, use only the 2 leaves with the most wins.

**Settings:** HF token (needs the "Make calls to Inference Providers" permission), judge model (default `Qwen/Qwen3.8-27B`) and provider, smart routing, and editable leaves. Each leaf has: on/off, model, "from an image" model, provider.

Default leaves:
- Image: `Qwen/Qwen-Image-2.1`, `black-forest-labs/FLUX.1-dev`, `black-forest-labs/FLUX.1-schnell`, `stabilityai/stable-diffusion-3.5-large`; edit model for all: `black-forest-labs/FLUX.1-Kontext-dev`.
- Video: `Lightricks/LTX-2.5`, `MiniMaxAI/MiniMax-H3`, `Wan-AI/Wan2.2-T2V-A14B` (image model `Wan-AI/Wan2.2-I2V-A14B`), `Wan-AI/Wan2.2-TI2V-5B`.

**Known gaps:** never tested against the live Hugging Face API (only against a fake client). First job: run one real image and one real video generation, then fix whatever fails, such as model names that no provider serves or provider-specific parameter errors.

---

## 5. Features to build, in this order

Build one stage at a time. After each stage, test it at phone width and desktop width, check nothing in section 4 broke, and commit.

### Stage 1: Script writer and Hook lab (new "Script" tab)
- Input: topic or idea, platform template (see stage 4; default "TikTok 30 s"), tone (funny, dramatic, mysterious, educational, motivational), and an optional series character.
- The language model (same as the judge, via `chatCompletion`) writes a script as JSON: `{ "title", "hooks": [5 options], "shots": [{ "visual": "...", "narration": "...", "seconds": n }], "loop_or_cta": "..." }`.
- Show 5 hooks; the user picks one (or "Test 3" generates the first shot for 3 hooks so they can compare).
- "Send to storyboard" fills the storyboard shots from the script's visuals and stores each shot's narration.

### Stage 2: Voiceover and captions
- Text-to-speech for each shot's narration through the HF client's `textToSpeech` (check the library for the exact method and supported models), with a voice picker. Store the audio blob per shot.
- Voice cloning only through a server-side provider (stage 6), behind the consent checkbox.
- Captions: build word timings by spreading each shot's words evenly over its audio length (simple, no extra model). Caption style presets: bold centred, karaoke highlight, minimal bottom. Keep captions inside the platform safe area.

### Stage 3: Join and export
- Combine the shots, voiceover, captions and an optional music track into **one MP4** in the browser using `ffmpeg.wasm` (`@ffmpeg/ffmpeg`, pinned version, loaded lazily). Fallback: render via canvas + `MediaRecorder` to WebM if ffmpeg.wasm fails.
- Burn captions in, mix the voiceover over music (music ducked under speech), use crossfades or hard cuts between shots, and add an optional intro/outro card for the series.
- Output in the template's aspect ratio and resolution. Show progress, and allow download.
- Export screen reminder: label realistic AI content when posting.

### Stage 4: Templates tab
Each template sets aspect ratio, target length, shot pacing, caption style, structure and safe area:
- TikTok / Reels: 9:16, 15–30 s, hook in the first 2 s, fast cuts, loop-friendly ending.
- YouTube Shorts: 9:16, up to 60 s, hook + payoff + loop.
- YouTube long-form: 16:9, chapters, intro hook, outro with call to action.
- Instagram feed: 4:5 or 1:1.
Users can save their own templates (stored in localStorage).

### Stage 5: Thumbnails, series lock, batch, calendar, analytics
- Thumbnail maker: image clover run in 16:9 with big title text overlaid on a canvas; 3 variations.
- Series lock: save a "series" (characters with reference images and descriptions, style, intro/outro, caption style, voice) and apply it to any new script with one click.
- Batch mode: queue several scripts and generate them one after another, with a total cost cap.
- Content calendar: a simple week/month view of planned posts per platform (localStorage).
- Analytics tracker: the user logs views, average watch time and likes per posted video; show which hooks, styles, lengths and models perform best, and feed the best-performing styles back as suggestions. (Manual entry first; platform APIs later, server only.)

### Stage 6: Server and premium leaves
- A small Node.js server (Express or Hono), deployable to Vercel, Railway or Render, that:
  - stores API keys in environment variables, never in the browser;
  - exposes `POST /generate` with `{ leafType, mode, prompt, refImage? }` and calls the official API of each premium provider through one adapter file per provider (Google Veo, Runway, MiniMax, Kling, Luma, ElevenLabs for voice);
  - adds simple auth so only the owner can use it.
- In the app, a leaf can be either a Hugging Face model or a server leaf.
- The clover engine, judge and stats must treat both kinds the same.

### Stage 7: Digital You (lip-sync avatar)
- Consent checkbox, then upload of the user's own front-facing photo or short video and a voice sample.
- Script → voice (the user's cloned voice via the server) → lip-synced talking clip through a lip-sync model (open model on HF or a server-side provider).
- Usable as a shot type in the storyboard.

---

## 6. Quality bar for every change

- Works at 390px width and on desktop, with no horizontal scrolling.
- Every credit-spending action shows its maximum cost first and has a hard limit.
- Every network call has error handling with a clear, human message (bad token, out of credits, model not served, network down).
- All model output and user text are escaped before rendering.
- Storage is wrapped in try/catch.
- No new dependencies unless needed; pin exact versions and load from cdn.jsdelivr.net or unpkg.com.
- Match the existing code style: same naming, comment density and structure.

---

## 7. Definition of done for the whole project

A creator can type one idea, pick "TikTok 30 s" and a series, and get back: 5 hook options, a storyboard of shots generated by the best of several models, a voiceover, burned-in captions, music, one exported vertical MP4, a thumbnail, and a calendar entry. After posting, they log the results, and the app suggests what to make next based on what performed best.
