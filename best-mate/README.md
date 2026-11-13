# The 48 — AI's Best Mate: Quotes

A quoting app for Australian tradies, built for the phone. Say or tap the job, get a
draft with prices from your own parts library, review it, and send a PDF quote with
GST worked out to the cent.

Pure Python 3 standard library on the server, plain HTML/CSS/JavaScript in the
browser. Nothing to `pip install`, nothing to compile, no keys in the repo.

## Run it (4 commands)

```bash
cd best-mate
python3 -m unittest discover -s tests     # 50 tests: money maths, fabrication check, end to end
python3 server.py                         # http://127.0.0.1:8048/
# open the address in a browser; on a phone it needs HTTPS (see Deploy)
```

## Deploy to a fresh Linux box (1 command)

```bash
bash deploy.sh
```

It checks Python, runs the tests, creates a sign-in password on the box, and starts
the app (a systemd service when run as root, otherwise a background process). It
prints the address, the password once, and the Caddy lines to add when you want it
on a public HTTPS address. It never touches DNS, Caddy or any other service.

## What is in it

| Screen | Route | What it does |
|---|---|---|
| Quotes | `/` | Every quote, filtered by Draft / Sent / Won / Lost |
| New | `/new` | Quote builder form: job type, brand, cycle, indoor units |
| Jane | `/voice` | Say or type the job; a draft quote comes back |
| Quote | `/quote/N` | Lines, labour, margin, GST totals, Review and send, PDF |
| Parts | `/parts` | Priced library, supplier CSV import, add a part |
| Settings | `/settings` | Business details for the PDF, markup, labour rates, vendor discounts |
| Jarvis | `/jarvis` | Job pipeline, quote states, system health |

## The rules it enforces

- **The AI never sets a final price.** Every quote starts as DRAFT. The only way out
  is `POST /api/quotes/N/send` with a person's review, enforced on the server.
- **Prices only come from the parts library.** An item the AI suggests that is not in
  the library is kept as a flagged line with no price. A dollar figure the AI writes
  that the library cannot account for is removed and reported.
- **Money maths is deterministic.** `bestmate/money.py`: integer cents, half-up
  rounding, GST once on the total. No AI and no floating point near the numbers.
- **No keys in the repo.** Everything secret comes from environment variables.

## Configuration

Environment variables (or `config.json`, copied from `config.example.json`):

| Variable | Purpose |
|---|---|
| `APP_PASSWORD` | Sign-in password. Required before the app will listen beyond this machine |
| `HOST`, `PORT` | Where to listen. Default `127.0.0.1:8048` |
| `BESTMATE_DB` | SQLite file. Default `data/bestmate.db` |
| `VOICE_BASE_URL`, `VOICE_KEY`, `VOICE_NAME` | Jane's voice server. Unset = local stub |
| `LLM_BASE_URL`, `LLM_KEY`, `LLM_MODEL` | OpenAI-compatible model for reading the job. Unset = built-in reader |

## The two contracts

```
POST /api/voice/speak   {"text": "..."}             -> audio/wav
POST /api/voice/listen  <audio bytes>               -> {"text": "..."}
POST /api/ai/draft-quote {"job_description": "..."} -> {"line_items": [...], "notes": "...", "flags": [...]}
```

With `VOICE_BASE_URL` set, the two voice calls are passed to the same paths on that
server. With `LLM_BASE_URL` set, the job description goes to `/chat/completions`
there; its answer is then checked against the parts library before anything is shown.

## Layout

```
best-mate/
├── server.py            HTTP server and JSON API
├── bestmate/
│   ├── money.py         all pricing, GST and margin maths
│   ├── drafting.py      job reader, install recipes, the fabrication check
│   ├── db.py            SQLite: settings, vendors, parts, quotes, the review gate
│   ├── pdf.py           PDF writer and the quote layout
│   ├── voice.py         voice stub and pass-through
│   ├── seed_parts.py    50 starter parts (placeholder prices)
│   └── config.py        environment / config.json loading
├── web/                 the app: index.html, app.css, app.js, jarvis.js, sw.js, icons
├── tests/               test_money.py, test_drafting.py, test_api.py
├── screenshots/         phone screens and a sample PDF
├── deploy.sh            one-command deploy
└── HANDOVER.md          what is built, what is stubbed, known gaps
```

See `HANDOVER.md` before relying on it for real quotes.
