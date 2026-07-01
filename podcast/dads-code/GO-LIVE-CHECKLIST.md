# ✅ Dad's Code — Go-Live Checklist (one page)

Work top to bottom. ~2–3 hours total, spread over a few sittings. Tick as you go.

---

## STEP 1 — Set up the money (Gumroad) · ~30 min
- [ ] Create a free account at **gumroad.com**.
- [ ] Add your **payout details** (PayPal or bank) + do the quick tax form.
- [ ] Create your first **3 products** (launch set): **Present, Not Perfect** ($9), **Dad's Code Kitchen** ($14), and the **Present Dad Toolkit** bundle ($39).
  - Upload the file from `podcast/dads-code/pdf/` (books) or `build/` (tools).
  - Paste the description from **`SALES-LISTINGS.md`**.
  - Make a cover in **Canva** (brief is in each product's `.md`).
- [ ] Set the free ones (5-Minute Present Dad, Days Left) to **$0 / "name your price."**
- [ ] Copy each product's **Gumroad link.**

## STEP 2 — Put the buy links in the site · ~15 min
- [ ] Open `site/shop.html` (and `site/index.html`).
- [ ] Replace every `href="#"` (on `data-buy="..."` buttons) with the matching **Gumroad link.**
- [ ] Replace `data-link="podcast/instagram/tiktok"` with your real links.

## STEP 3 — Connect the email capture · ~15 min
- [ ] Create a free **MailerLite** account.
- [ ] Make a form/landing that delivers the **free 5-Minute Present Dad PDF.**
- [ ] Paste that form's action URL into `<form action>` in `index.html` (remove the alert line).

## STEP 4 — Put the website online (free) · ~10 min
- [ ] Go to **Cloudflare Pages** (or Netlify) → **drag in the whole `site/` folder.**
- [ ] You get a live URL. Test it — click a Preview button and a Buy button.
- [ ] *(Later)* buy **dadscode.com.au** (~$15/yr) and point it here.

## STEP 5 — Podcast on the directories · ~20 min
- [ ] **Upgrade Buzzsprout** off the free plan (stops the 90-day episode deletion).
- [ ] Buzzsprout → **Directories** → submit to **Apple Podcasts, Spotify, YouTube Music.**
- [ ] Add your website link to the show notes.
- [ ] 🔐 Reset your Buzzsprout **API token** (it was shown in a screenshot).

## STEP 6 — Amazon KDP (optional, later) · ~1 hr
- [ ] Follow **`KDP-SETUP.md`** — publish **Present, Not Perfect** first (eBook + paperback).

## STEP 7 — Launch! · ~30 min
- [ ] Post the **3 launch clips** (in `SOCIAL.md`) → "link in bio" = your website.
- [ ] Send the **launch email** (in `SALES-LISTINGS.md`) to your list.
- [ ] Ask 10 friends/family to grab the free tool + leave a review.

---

### The absolute minimum to be "live and taking money today"
**Steps 1 + 2 + 4.** (Gumroad products → links in the site → host the site.) Everything else can follow.

*Present, not perfect — including your launch. Just get it out there.* 💛
