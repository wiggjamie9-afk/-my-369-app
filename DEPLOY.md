# Deploying the Vitruvian 369 Core app

The app is a single static file — `index.html` (a faithful copy of the HTML in
`README.md`). No build step, no server, no database. Any static host works.
Pick **one** of the options below.

> All options are free. Options 2–4 require creating a free account on that
> host; **Option 1 (GitHub Pages) needs no new account** because your repo is
> already on GitHub.

---

## Option 1 — GitHub Pages (recommended, no new account)

A workflow is already included at `.github/workflows/deploy-pages.yml`. It
publishes the repo root (which contains `index.html`) every time you push to
`claude/awesome-free-services-f6homv`.

One-time setup:

1. Go to your repo on GitHub → **Settings** → **Pages**.
2. Under **Build and deployment → Source**, choose **GitHub Actions**.
3. Push any commit to the branch (or open the **Actions** tab → run
   *"Deploy 369 Core to GitHub Pages"* → **Run workflow**).
4. When the run finishes, the live URL appears in the workflow summary and on
   the Settings → Pages screen. It will look like:
   `https://wiggjamie9-afk.github.io/-my-369-app/`

To serve from `main` instead, change the `branches:` line in the workflow file.

---

## Option 2 — Netlify

Config is included at `netlify.toml` (publishes the repo root).

- **No-CLI way:** netlify.com → *Add new site* → *Import an existing project*
  → connect GitHub → pick this repo and branch → Deploy.
- **CLI way** (after `./install-clis.sh` installs `netlify`):
  ```bash
  netlify login
  netlify deploy --prod --dir .
  ```

---

## Option 3 — Vercel

Config is included at `vercel.json`.

- **No-CLI way:** vercel.com → *Add New… → Project* → import this repo →
  Framework Preset **Other** → Deploy.
- **CLI way** (after `./install-clis.sh` installs `vercel`):
  ```bash
  vercel login
  vercel --prod
  ```

---

## Option 4 — Cloudflare Pages

No config file needed for a plain static site.

- dash.cloudflare.com → **Workers & Pages** → *Create* → **Pages** →
  *Connect to Git* → pick this repo and branch.
- **Build command:** leave empty. **Build output directory:** `/` (root).
- Deploy. You get a `*.pages.dev` URL.

---

## Editing the app later

`index.html` is the deployed file. If you change the app in `README.md`, copy it
across so the two stay in sync:

```bash
cp README.md index.html
git add index.html && git commit -m "Sync app" && git push
```

(If you'd rather not keep two copies, you can keep `index.html` as the single
source of truth and drop the HTML from `README.md` — say the word and I'll
restructure it that way.)

---

## Notes

- The app stores its "vision log" in the browser's `localStorage`, so data is
  per-device and per-browser. There is no backend to set up.
- It uses the Web Audio API and `navigator.vibrate`, which require a user
  gesture (tapping a NODE button) and a secure context (HTTPS) — all four hosts
  above serve over HTTPS by default, so this works out of the box.
