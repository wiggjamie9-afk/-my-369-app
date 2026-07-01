# 🎬 Dad's Code — Sample Video Clip

A real, rendered **30-second promo clip** for the flagship product **"Present, Not Perfect."**
This is a genuine MP4 (1920×1080, 30fps, H.264), not a storyboard — made entirely
in-house with open-source tooling, **no paid AI video service and no API keys.**

## Files
- `dadscode-present-not-perfect.mp4` — the finished 30s clip.
- `thumbnail.png` — opening frame (title card).
- `dadscode-present-not-perfect.json` — the "script": the scene-by-scene source. Edit this
  to change wording, timing, stats or colours, then re-render.

## The 6 scenes (30s)
1. **0–4.5s** Title: *Present, Not Perfect* — amber + cream (brand)
2. **4.5–9s** *"You don't have to be the perfect dad. You just have to be a present one."*
3. **9–13.5s** Stat: **5 min** — a bedtime chapter your kids remember forever
4. **13.5–19s** Bar chart: real phone-down attention a day (6 → 30 min) + "5×" reveal
5. **19–24s** Compare: *Perfect (the tidy house)* vs *Present (you, on the floor, playing)*
6. **24–30s** Close: **Present, not perfect.** — Dad's Code, the book, out now.

## How it was made (and how to re-make / re-brand it)
Engine: **OpenMontage → Remotion** (React video renderer) rendered locally with the
system Chromium. All animation is code-driven, so it's infinitely re-usable for the
other 17 products — just write a new `.json` and render.

```bash
# one-time (already done in this environment):
#   git-free download of OpenMontage, then:  cd remotion-composer && npm install
cd <OpenMontage>/remotion-composer
npx remotion render src/index.tsx Explainer out/<name>.mp4 \
  --props public/demo-props/<name>.json --codec h264 \
  --browser-executable=<path-to>/headless_shell --ignore-certificate-errors
```

### To make clips for the other products
Copy the `.json`, change the `text`/`stat`/`chartData` in each cut, keep the brand
colours (`#14121A` bg, `#DFB76C` amber, `#F4F1EA` cream, `#B4AEC0` muted), re-render.
15 minutes per product once you know the pattern.

## To post it
It's a finished 16:9 MP4 — upload straight to YouTube, or drop into CapCut and crop
to 9:16 for TikTok / Reels / Shorts, add your voiceover or a trending sound, and post.

*Present, not perfect.* 💛
