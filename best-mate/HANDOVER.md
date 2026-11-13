# Handover — The 48: AI's Best Mate (v1)

Built 2026-11-13 from `THE48-BEST-MATE-builder-spec` and the feature teardown.
Original design and code throughout. Nothing was copied from any other product:
no branding, layout, wording, screenshots or prices. The competitor screenshots
were read for the list of feature *categories* only, as the spec instructed.

## Read this first

1. **Every seeded price is a placeholder.** The 50 starter parts carry round-number
   stand-in costs that I made up so the app could be exercised. They are not
   supplier prices. Each is stored as `placeholder`, shows a "check price" badge on
   quotes, and the review step will not send until a person ticks that they have
   checked them. Import your supplier list (Parts > Import) before quoting real jobs.
2. **Jane's voice is a stub.** The mic records and posts audio, but with no voice
   server connected `/api/voice/listen` returns a fixed sample sentence and
   `/api/voice/speak` returns a chime. The screen says so. Typing the job works now.
3. **It lives in `best-mate/` inside the `-my-369-app` repo**, on branch
   `claude/busy-fermat-69odbh`, not in its own clean repo. The spec asked for a
   clean repo; I can only write to this one. The folder is self-contained, so moving
   it is `cp -r best-mate <new repo>`.

## What is built and tested

| Spec item | Status |
|---|---|
| 1. Quote builder | Built. Job type, brand, cycle, indoor units; lines with cost, markup, sell; margin panel (materials cost / labour cost / net profit); GST ex and inc |
| 2. Parts library | Built. 50 seeded parts, vendor discounts, search and paging, CSV import. Tested with 15,050 parts (search under a second) |
| 3. Voice-to-quote (Jane) | Built against the contract with a local stub. Dictation or typed text becomes a draft quote |
| 4. PDF quote | Built. Header with logo and business details, customer, scope, system summary, price table, GST totals, terms, page numbers. Drafts are watermarked DRAFT |
| 5. Jarvis panel | Built at `/jarvis`: pipeline by state, needs-attention list, recent activity, health strip, and a marked slot for the existing console |
| 6. Settings | Built. Business details, markup, labour rates, preferred brands, payment terms, vendor discounts |

Hard rules:

- **AI never sets a final price** — every quote is created as `draft`; `send` needs
  `reviewed: true` from a person and is refused while any line is unpriced, any
  drafting warning is unread, or placeholder prices are unconfirmed. Editing or
  reopening a quote clears the review. Tested in `test_api.ReviewGate`.
- **No API keys in the repo** — all from environment; `config.example.json` ships
  empty; a test scans the tree for anything key-shaped.
- **Deterministic money maths** — `bestmate/money.py`, 20 unit tests with
  hand-worked expected values.
- **AI output checked before display** — `drafting.check_ai_items` and
  `drafting.scrub_notes`; tested against a fake model that invents prices.
- **Offline-tolerant PWA** — service worker keeps the app shell and the last quotes,
  parts and settings fetched. Offline is read-only: changes are refused with a
  message rather than queued.
- **iPhone Safari first** — see "Not verified" below.

## Test output

```
$ python3 -m unittest discover -s tests
..................................................
----------------------------------------------------------------------
Ran 50 tests in 10.9s

OK
```

The acceptance sentence, "two and a half kW Daikin split, back-to-back install,
Smith job", with seed prices, 30% markup and 4 hours labour, gives:

```
Parts and materials   $1,481.35
Labour  4 h x $110      $440.00
Subtotal ex GST       $1,921.35
GST 10%                 $192.14     (192.135 rounded half-up, once, on the total)
Total inc GST         $2,113.49
```

The same figures appear in the API, on screen and in the PDF (`test_api.Acceptance`).

## Acceptance test, step by step

| Step | Result here |
|---|---|
| 1. Fresh box, `bash deploy.sh` -> app up | Passed on a clean copy in a Linux container (background-process path). The systemd path could not be run here |
| 2. Dictate the sentence -> DRAFT with flagged items, correct GST | Passed with the sentence typed, and via the stubbed listen call. Real dictation needs Jane's server |
| 3. Review -> PDF downloads, totals to the cent | Passed |
| 4. Jarvis panel loads at its route, no dead buttons | Passed |
| 5. All tests pass; no keys in the repo | Passed |

## Not verified — please check on the real thing

- **A real iPhone.** Screens were driven in Chromium emulating an iPhone 14, not in
  Safari. The mic (MediaRecorder), `<dialog>` sheets and add-to-home-screen need a
  look on a real phone. Both the mic and offline mode require HTTPS.
- **The systemd branch of `deploy.sh`.** Written, not executed (no systemd here).
- **Jane's real server.** The pass-through assumes it accepts the same two paths
  (`/api/voice/speak`, `/api/voice/listen`). If Pocket TTS speaks a different shape,
  adapt the two functions in `bestmate/voice.py`; nothing else changes.
- **A real model.** The LLM path was tested against a fake OpenAI-compatible server
  only. Terry has not been pointed at it.

## Stubbed or deliberately not built

- **Sending.** "Send quote" marks the quote sent and makes the final PDF available
  to download or share. It does not email the customer; no mail service is wired.
- **Speech to text and text to speech.** Stubbed, as above.
- **One shared password, one business.** No user accounts or roles.
- **Offline edits.** Not queued; offline is read-only.
- **From the teardown, skipped for v1 as it said:** the AI room visualiser and a
  15,000-item library on day one. Also not built: a system diagram in the PDF,
  per-room pages, and customer accept/decline of a quote.

## Decisions I made that you may want to change

- **Stack:** standard library Python and SQLite, no framework, no front-end build.
  Reason: your next hand can read every line, and deploy has no install step.
- **Install recipes** (`drafting.recipe`): what a split, multi-split, ducted or
  service job normally needs, with default pipe runs and labour hours. These are my
  starting assumptions, not your practice. Adjust the quantities there.
- **Defaults:** 30% markup, $60/h labour cost, $110/h labour charge, 30-day
  validity, 50% deposit terms. All editable in Settings.
- **GST** is calculated once on the ex-GST total, not per line.
- **A brand you don't stock** (say, Samsung) is kept as said and flagged, never
  swapped silently for your preferred brand.
- **Logo:** used as supplied. The app icon and PDF mark are a square crop of the
  circular mark, not redrawn.

## Where your existing pieces plug in

| Asset | Where |
|---|---|
| Pocket TTS "Jane" | set `VOICE_BASE_URL` (and `VOICE_KEY`); adapter is `bestmate/voice.py` |
| Terry / llmgate | set `LLM_BASE_URL`, `LLM_KEY`, `LLM_MODEL`; prompt and parsing are in `bestmate/drafting.py` |
| JARVIS console | `web/jarvis.js` is the whole `/jarvis` view; fill `#jarvis-graft` or replace `mountJarvis()`. Feed: `GET /api/jarvis/summary` |
| AI9 validation harness | not connected; the draft endpoint is plain JSON in, JSON out, so it can be benchmarked as-is |

## Run the tests

```bash
cd best-mate
python3 -m unittest discover -s tests -v
```
