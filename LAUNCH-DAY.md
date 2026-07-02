# 🚀 DAD'S CODE — LAUNCH DAY RUNBOOK
### Open this tomorrow morning. Work top to bottom. Tick as you go.

Everything below is already **built and saved in this repo.** Your job tomorrow is to
put it online and hit publish on the accounts (the things I can't log into for you).

**The tagline everywhere:** *Present, not perfect.*

---

## ⏱️ THE ABSOLUTE MINIMUM (be live & taking money in ~1 hour)
If you only do three things tomorrow, do these:
1. **Gumroad** → create 3 products + get their links (30 min)
2. **Paste those links** into `site/shop.html` + `site/index.html` (10 min)
3. **Host the `site/` folder** on Cloudflare Pages (drag-and-drop, 10 min)

That's it — you're live. Everything else below makes it *better*, not *live*.

---

## ✅ WHAT'S DONE (all in this repo — nothing to make)
| Asset | Where | Count |
|---|---|---|
| Products (interactive + books) | `podcast/dads-code/build/` | 18 |
| Print-ready PDFs | `podcast/dads-code/pdf/` | 11 |
| Promo video clips | `podcast/dads-code/video/dc-*.mp4` | 18 |
| Voiced flagship clip (your voice) | `podcast/dads-code/video/…VOICED-v2.mp4` | 1 |
| Website (landing + shop) | `site/index.html`, `site/shop.html` | 2 |
| Sales listings (paste-ready) | `podcast/dads-code/SALES-LISTINGS.md` | all |
| New podcast episodes (scripts) | `podcast/DADS-CODE-EPISODES-02-06.md` | 5 |
| Social launch posts | `podcast/SOCIAL.md` + SALES-LISTINGS | 9+ |
| Launch email | `podcast/dads-code/SALES-LISTINGS.md` (bottom) | 1 |

---

## 🔲 WHAT ONLY YOU CAN DO (accounts — I can't log in as you)

### STEP 1 — Money: Gumroad · ~30 min
- [ ] Create free account at **gumroad.com** → add payout (PayPal/bank) + tax form.
- [ ] Create the **launch set** first: two free list-builders (**Days Left**, **5-Minute Present Dad**) + two paid — **Present, Not Perfect** ($9) and **Dad's Code Kitchen** ($14, intro $9). *(Bundles come later — Step 6 / first week.)*
  - Upload the file from `podcast/dads-code/pdf/` (books) or `podcast/dads-code/build/` (tools).
  - Paste the description from **`podcast/dads-code/SALES-LISTINGS.md`**.
- [ ] Copy each Gumroad link.
- [ ] *(After launch)* add the other 14 products + the 4 bundles.

### STEP 2 — Put links in the site · ~10 min
- [ ] In `site/shop.html` + `site/index.html`, replace every `href="#" data-buy="…"` with the Gumroad link.
- [ ] Replace `data-link="podcast/instagram/tiktok"` with your real links.

### STEP 3 — Email capture · ~15 min  *(do this BEFORE hosting)*
- [ ] Free **MailerLite** account → make a form that delivers the free **5-Minute Present Dad** PDF.
- [ ] Paste the form URL into `<form action>` in `index.html` (remove the alert line).

### STEP 4 — Host the site (free) · ~10 min  *(do this LAST, after all edits above)*
- [ ] **Cloudflare Pages** (or Netlify) → drag in the whole **`site/`** folder → get a live URL.
- [ ] Test: click a Buy button and a "Try it" tool.
- [ ] ⚠️ If you edit any file in `site/` after this, **re-drag the `site/` folder** so the change goes live.

### STEP 5 — Podcast live · ~20 min
- [ ] 🔐 **Reset your Buzzsprout API token** (it was shown in a screenshot — do this first).
- [ ] **Upgrade Buzzsprout** off free (stops the 90-day episode deletion).
- [ ] Record + upload episodes (read-aloud scripts in `podcast/DADS-CODE-READ-ALOUD.md`, full versions in `podcast/DADS-CODE-EPISODES-02-06.md`). Lead with **"How Many Bedtimes Left?"**
- [ ] Submit to **Apple Podcasts, Spotify, YouTube Music** (Buzzsprout → Directories).
- [ ] Add your website link to the show notes.

### STEP 6 — Go social · ~30 min
- [ ] Post the **3 launch clips** (use your `dc-*.mp4` promos or the SOCIAL.md scripts).
- [ ] "Link in bio" = your new website URL.
- [ ] Send the **launch email** (in `podcast/dads-code/SALES-LISTINGS.md`) to your list.
- [ ] Ask 10 friends/family to grab the free tool + leave a review.

---

## 📣 LAUNCH-DAY POSTS (copy-paste)
**Post 1 (free hook):** "I built a tool that tells you how many bedtimes you've got left with your kid. I did NOT expect to cry. Link in bio — it's free. 👊 #dadsoftiktok #fatherhood"

**Post 2 (the story):** "Late-diagnosed ADHD dad of 4. I spent years feeling like I was failing at this. So I made everything I wish I'd had — starting with one free thing. Link in bio. #adhddad #girldad #parenting"

**Post 3 (a tool demo):** "POV: it's bedtime, you're exhausted, and this thing writes your kid a brand-new story with THEM in it. Every night. 🌙 #bedtime #dadlife"

*(Attach the matching `dc-*.mp4` promo clip to each.)*

---

## 📅 THE FIRST WEEK (after launch day)
- **Day 1:** launch set (2 free + 2 paid) + 3 posts + email.
- **Day 2–3:** add the other 14 products + the 4 bundles to Gumroad.
- **Day 3:** publish podcast episode 2.
- **Day 4–7:** post 1 promo clip/day; reply to every comment.
- **This week:** start Amazon KDP with **Present, Not Perfect** (see `podcast/dads-code/KDP-SETUP.md`).

---

## 🧯 IF SOMETHING GOES WRONG
- **No sales day 1?** Normal. Launch is about getting it *out*, not overnight money.
- **A buy link 404s?** You missed one `href="#"` — search the file for it.
- **Tool won't load on the site?** Make sure you hosted the whole `site/` folder (tools are in `site/tools/`).
- **Overwhelmed?** Do the "absolute minimum" 3 steps and stop. The rest can wait a day.

*You built all of this. Tomorrow you just open the doors. Present, not perfect.* 💛
