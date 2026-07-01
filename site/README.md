# 🌐 Dad's Code — Website

A self-contained landing page for Dad's Code (`index.html`). No build step, no dependencies — just open it in a browser.

## Finish it (5 quick edits, all marked in the HTML)
1. **Buy links:** replace `href="#" data-buy="..."` with your **Gumroad** product URLs.
2. **Links:** replace `data-link="podcast/instagram/tiktok"` with your real links.
3. **Email form:** paste your **MailerLite** (or similar) form action URL into `<form action>` and delete the `onsubmit` alert.
4. **Photo:** drop a warm photo of you + the kids where the `[portrait]` placeholder is.
5. Optional: swap the free-tool links if you host the tools elsewhere.

## Host it for FREE (pick one)
- **Cloudflare Pages** or **Netlify:** drag-and-drop the `site` folder → instant live URL. Easiest.
- **GitHub Pages:** free, from this repo — Settings → Pages → deploy from branch → `/site`.
- **Custom domain:** buy `dadscode.com.au` (~$15/yr) and point it at whichever host above.

## Notes
- ✅ **Self-contained:** the interactive tools are bundled in `site/tools/`, so every "Try it" link works when you host **just the `site` folder** (drag-and-drop the whole `site` folder to Cloudflare Pages / Netlify).
- To add or update a tool later, copy the new `.html` from `../podcast/dads-code/build/` into `site/tools/` and link to `tools/<file>.html`.
- Everything is brand-consistent (charcoal + amber, "Present, not perfect."), responsive, and accessible.
