# Retention engine: build brief

For: Kimi (or any developer). Written by Claude, 2026-11-02.
Purpose: turn trial customers into paying ones, and paying ones into customers who never cancel, by sending each customer a monthly **"Jane booked you $X this month"** value report. This is the single highest-leverage money feature: it makes the value Jane creates visible, so cancelling feels like losing money.

Read first: `CLAUDE.md`, `organism/GENOME.md`, `docs/organism-automation-brief.md`. Build this **after** organism steps 5–6 (data model, lead/call capture, approvals queue), because it needs real call data and must send through approvals.

The template is built and tested: `retention/index.html`, tests in `tests/retention-e2e.js` (36 checks pass). Keep the template and keep the tests green.

## What exists now

`retention/index.html` is a self-contained report page, personalised by URL params, all values inserted as **text only** (never HTML). It shows:
- The hero number: estimated value = **jobs Jane booked × the customer's average job value** (an estimate, clearly labelled).
- Stats: calls answered, after-hours/weekend calls, jobs booked, emergencies sent to the owner.
- The jobs she booked (first name + suburb only).
- An honest "how we work out the dollars" section (estimate, counts only jobs Jane directly booked, under-promises).
- A reassurance CTA (keep Jane / message us). **Nothing on the page charges anything.**
- A SAMPLE banner when run without real data, so an example is never mistaken for real results.

Params: `b` business, `o` owner, `m` month, `v` avg job value, `ca` calls, `ah` after-hours, `jb` jobs booked, `em` emergencies, `pv` previous month's value, `n` owner phone, `e` owner email.

## What to build (in order)

### 1. Real numbers from the call log
Replace the sample bookings and stat defaults with the customer's real data for the month, from the organism's `calls`/`leads`/`customers` tables (organism brief, section 2):
- `calls` = calls Jane answered for that customer in the month.
- `afterHours` = those outside the customer's business hours.
- `jobs` = calls Jane booked or captured as a lead.
- `emergencies` = calls triaged straight to the owner.
- Bookings list = first name + suburb + short job note, for that customer only. **Never** show a caller's full name, number or address on the report.

**Test:** seed one customer with a known set of calls; the report's counts and job list match the seed exactly.

### 2. Average job value — from the customer, never invented
Store `avg_job_value` per customer (they set it at onboarding; default prompts them to confirm it). The estimate uses their number. If they haven't set it, show the stats but mark the dollar figure clearly as "estimate — set your average to make this real" (CLAUDE.md: no fabrication).

**Test:** a customer with no avg set sees stats but no hard dollar claim; once set, the hero value = jobs × their value.

### 3. Generate and store the report monthly
A nightly/month-end job builds each active customer's report (a stored record + a unique unguessable link, e.g. a random token, not the customer's name). Reports are private (`noindex`, token in the URL, served only to that customer).

**Test:** month-end run creates one report per active customer with the right month and a unique link; last month's `pv` is filled from the stored prior report.

### 4. Send it — through the approvals queue (hard rule)
The report is an outbound message, so it **must not auto-send**. It goes to the approvals queue (organism brief, section 3): the owner sees each month's batch, can read any report, and approves the send. Only then does it go out (email/SMS with the link), respecting consent and the customer's contact preference (Spam Act, unsubscribe honoured).

**Test:** generating reports creates approval cards, sends nothing; after approval, the send is logged; an opted-out customer is skipped.

### 5. Wire it into the loop
- Emit a `report_sent` event (organism events table) so the learning loop can later test subject lines/headlines (organism-upgrades-brief, Upgrade 5).
- Show on the Command Center: reports generated, approved, opened; and flag any active customer who got no report (a gap, per `TARGET.md` "every active customer gets a monthly value report").

**Test:** a customer missing a report shows as a gap in the briefing; an opened report updates the dashboard.

## Rules on every step (unchanged)
- Secrets on the server only; never in the page or the repo.
- Everything inserted into the page is text, never HTML (the template already does this — keep it).
- Nothing sends or charges without the approvals queue.
- No fabricated numbers, reviews or results; estimates are labelled estimates.
- Works on a phone (390px) and desktop; `tests/retention-e2e.js` stays green.

## Done means
Each active customer gets one honest, private monthly report showing what Jane actually did and a conservative dollar estimate; the owner approves the batch before anything sends; opted-out customers are skipped; and the dashboard shows who got one and who didn't. The report makes Jane's value impossible to miss — which is what keeps customers paying.

## Send back to Claude
A seeded test customer's report link and the approval card for its send, plus the test output, so Claude can verify the numbers, the privacy of caller data, and that nothing sends without approval.
