# Quote Mate, hosted

One small server that lets you sell the quote tool to many tradies as a monthly service.

- **Sales page** at `/` with a live demo for each of six trades (roofing, painting, pet grooming, home batteries, home care,
  bookkeeping) and an enquiry form.
- **Each business** gets its own quote page at `/q/<name>/`, priced from its own rates,
  and a lead inbox at `/q/<name>/admin` (leads, photos, status, notes, spreadsheet export,
  its own rates and wording).
- **You** get an owner console at `/admin`: add a business, set its plan, record what it
  has paid up to, pause it, reset its password, and read enquiries from the sales page.

Python 3 standard library only. No installs, no API keys in the repo. The quote page itself
is the tool in `../roof-quote-mate/`, served unchanged; this server supplies each business's
`config.js` and receives the leads.

## Run it

```bash
cd quote-mate-hosted
python3 -m unittest discover -s tests          # 34 tests
ADMIN_PASSWORD='pick-a-long-one' python3 server.py
# http://127.0.0.1:8090/        sales page
# http://127.0.0.1:8090/admin   owner console
```

To put it on the internet, run it behind Caddy or nginx with HTTPS and set `TRUST_PROXY=1`
and `PUBLIC_URL=https://your-domain`. Keep both folders (`quote-mate-hosted` and
`roof-quote-mate`) side by side, or point `QM_TOOL_DIR` at the quote tool.

## What makes it more than a calculator

- **Put it on your own website.** Settings gives each business one line of code. It adds the quote tool to any page, fits
  itself to the space, and only trusts messages from its own frame. Sign-in, inbox and settings pages can never be framed.
- **See that it works.** The inbox shows the last 30 days: opened, started, saw a price, sent details, each as a share of
  the step before, and what people ask about most. Counts are anonymous: no cookies, no addresses, nothing personal.
- **Qualify the lead.** Under the price the customer says how soon they want it and the best time to call. "As soon as
  possible" marks a **Hot** lead (and puts HOT in the email subject), the same phone number asking twice is flagged, and
  leads nobody has rung in a day are called out at the top of the inbox.
- **Confirm to the customer.** With email switched on, the homeowner gets an instant email with the ballpark they were
  shown and when to expect a call. A business can switch it off in Settings.
- **Brand colour.** A full-plan business can choose its own accent colour; it must be readable on the dark page, and the
  text colour on buttons is picked automatically.

Not built, and why: measuring a roof from satellite images (needs paid imagery and keys), text messages (needs an SMS
provider), and connections to specific CRMs beyond the webhook (Zapier and Make cover most of them).

## Branding

The service ships as **48 AI Crew Quoting** with the 48 AI Crew logo:

- The name is a setting: `/admin` > "Sales page details" > Service name. It shows on the sales page, in the browser tab and
  on every lite-plan quote page.
- The logo is two files in `static/`: `48-ai-crew-logo.png` (256 px, the sales page) and `48-ai-crew-icon.png` (96 px,
  headers, browser tab, home-screen icon). Replace both, keeping the file names, to rebrand.
- The colour is the logo's blue, `#3D8BFF` (text on it is `#0B1220`). It's set in two places that a test keeps in step:
  `static/site.css` (the sales page, inboxes and console) and `THEME` in `qm/store.py` (every quote page). An overdue payment
  is red, not blue, so it still reads as a warning.
- Plans: a **lite** business's quote page shows this brand. A **full** business's page shows only that business's own name
  and logo, never yours (its logo is uploaded under its Settings).

## Settings (environment variables)

| Variable | What it does |
|---|---|
| `ADMIN_PASSWORD` | Owner console password. The console is off without it |
| `HOST`, `PORT` | Where to listen. Default `127.0.0.1:8090` |
| `QM_DB` | SQLite file. Default `data/quotemate.db`; customer photos are stored beside it |
| `PUBLIC_URL` | Your public address, used in lead emails |
| `TRUST_PROXY=1` | Behind a reverse proxy: take the visitor's address from `X-Forwarded-For` |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS` | Turns on lead emails. `SMTP_TLS` is `starttls` (default), `ssl` or `none` |

## How you'd use it

1. Open `/admin`, fill in "Sales page details": your service name, phone, and the prices
   you want shown. Until you set prices the page says "Ask for pricing".
2. When a tradie signs up, "Add a business". You're shown their sign-in page and a password
   **once**. Send both to them.
3. They sign in, put in their own rates, tick "These are my real rates", and share their link.
4. Leads land in their inbox, and in their email if you've set up SMTP.
5. When they pay, set "Paid until". An overdue business gets an "overdue" badge in your
   console. Nothing switches off by itself: pausing a business is your call.

## What it does not do

- **It does not take payments.** There is no Stripe or card handling. You invoice however
  you already do and record "Paid until" by hand.
- **No self sign-up.** A tradie sends an enquiry; you create their account.
- **No text messages.** Leads arrive in the inbox, by email (with SMTP set), and optionally
  as a copy posted to the tradie's own webhook (Zapier, Make).
- **Adding a new trade** means adding a file to `presets/` (copy `roofing.json`). A business
  can rename and re-price its options but not add or remove them from its settings page.
  Presets can also set `pricing.priceSuffix` ("per week"), `pricing.rebate`, a `watch` line on any option (listed
  under the price when picked), `words.privacyNote`, `photos.max: 0` (no photos) and `pricing.gstRegistered: false`.
- **Example rates.** The presets carry made-up rates. Each business's page says so until
  that business confirms its own.
- **The battery rebate figure is unverified.** See `LAUNCH.md` before selling to installers.
- **Privacy.** You will be holding homeowners' names, phones, emails and photos for your
  customers. Get proper advice on a privacy policy and terms before selling this.

## Safety built in

- A lead's price is worked out again on the server from the business's stored rates; a
  number sent by the browser is never trusted.
- Businesses are isolated: every lead and photo is looked up by business *and* id.
- Passwords are stored only as scrypt hashes; a reset signs every device out.
- Uploads are checked by their actual bytes (PNG, JPG, WebP only; no SVG), size-capped,
  and stored under names the server chooses.
- Lead and enquiry forms are rate-limited and have a hidden field that traps bots.
- A business's webhook must be public HTTPS, so it can't be pointed at this server's own
  network.
- Spreadsheet exports defuse cells that would run as formulas.

## Layout

```
quote-mate-hosted/
├── server.py          routes: sales page, quote pages, lead intake, inboxes, owner console
├── qm/
│   ├── store.py       SQLite: businesses, leads, photos, enquiries, site details
│   ├── estimate.py    the pricing sum (matches ../roof-quote-mate/estimate.js; tested)
│   ├── deliver.py     lead emails and webhook copies
│   └── pages.py       every server-rendered page
├── presets/           one JSON file per trade (roofing, painting, pets, batteries, homecare, bookkeeping)
├── deploy.sh          one-command deploy
├── LAUNCH.md          what's left to do on your side, in order
├── static/site.css
└── tests/test_hosted.py
```
