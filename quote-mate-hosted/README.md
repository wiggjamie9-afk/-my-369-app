# Quote Mate, hosted

One small server that lets you sell the quote tool to many tradies as a monthly service.

- **Sales page** at `/` with a live demo for each trade (roofing, painting, pet grooming, home batteries) and an enquiry form.
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
python3 -m unittest discover -s tests          # 32 tests
ADMIN_PASSWORD='pick-a-long-one' python3 server.py
# http://127.0.0.1:8090/        sales page
# http://127.0.0.1:8090/admin   owner console
```

To put it on the internet, run it behind Caddy or nginx with HTTPS and set `TRUST_PROXY=1`
and `PUBLIC_URL=https://your-domain`. Keep both folders (`quote-mate-hosted` and
`roof-quote-mate`) side by side, or point `QM_TOOL_DIR` at the quote tool.

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
├── presets/           one JSON file per trade (roofing, painting, pets, batteries)
├── deploy.sh          one-command deploy
├── LAUNCH.md          what's left to do on your side, in order
├── static/site.css
└── tests/test_hosted.py
```
