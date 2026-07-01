# 🎬 Dad's Code — Promo Video Clips

Real, rendered promo clips (1920×1080, 30fps, H.264) — genuine MP4s, not storyboards —
made entirely in-house with open-source tooling, **no paid AI video service and no API keys.**

## The full set — one clip per product (`dc-01` … `dc-18`)
Every one of the 18 products has a ~24-second on-brand promo clip: hero title →
hook line → a key number → a "Without / With Dad's Code" comparison → the
"Present, not perfect." close, with a "Dad's Code · by Jamie Wigg" badge.

| # | File | Product |
|---|------|---------|
| 01 | `dc-01-5-minute-present-dad.mp4` | The 5-Minute Present Dad |
| 02 | `dc-02-present-not-perfect.mp4` | Present, Not Perfect |
| 03 | `dc-03-30-day-present-dad-journal.mp4` | The 30-Day Present Dad Journal |
| 04 | `dc-04-dads-code-kitchen.mp4` | Dad's Code Kitchen |
| 05 | `dc-05-dad-fuel.mp4` | Dad Fuel |
| 06 | `dc-06-adhd-dads-playbook.mp4` | The ADHD Dad's Playbook |
| 07 | `dc-07-steady.mp4` | Steady |
| 08 | `dc-08-still-choosing-you.mp4` | Still Choosing You |
| 09 | `dc-09-dad-and-me-cards.mp4` | Dad & Me: 100 Conversation Cards |
| 10 | `dc-10-dads-bedtime-stories.mp4` | Dad's Bedtime Stories |
| 11 | `dc-11-90-day-rebuilt-dad.mp4` | The 90-Day Rebuilt Dad |
| 12 | `dc-12-days-left.mp4` | Days Left (free tool) |
| 13 | `dc-13-the-play-machine.mp4` | The Play Machine |
| 14 | `dc-14-letters-to-you.mp4` | Letters to You |
| 15 | `dc-15-the-dad-deck.mp4` | The Dad Deck |
| 16 | `dc-16-dad-battery.mp4` | Dad Battery |
| 17 | `dc-17-the-bedtime-engine.mp4` | The Bedtime Engine |
| 18 | `dc-18-time-capsule.mp4` | Time Capsule |

Each clip's source "script" is the matching `dc-*.json`. To re-word or re-brand any
clip, edit its JSON and re-render (command below). To regenerate all 18 props at once,
see `../gen_props.py` in the OpenMontage composer.

---

## Flagship reference clip
`dadscode-present-not-perfect.mp4` — the original hand-tuned 30-second clip for
**"Present, Not Perfect"** (slightly longer, with a bar chart), used to dial in the brand look.

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
