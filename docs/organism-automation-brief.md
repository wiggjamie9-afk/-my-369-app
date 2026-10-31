# The 48 AI Crew: business organism automation brief

For: Kimi (or any developer). Written by Claude, 2026-10-31.
Business: The 48 AI Crew (https://48ai.jamiewiggautomation.au/), AI receptionist "Jane" for trade businesses in Perth, WA: answers calls, texts and email 24/7, 7-day free trial.

Goal: connect the automation "organism" to the real business (leads, trials, customers, calls, money) so it watches, reports and follows up on its own, while the owner approves anything that sends, posts, charges or changes Jane.

Read first: the website brief `docs/48ai-website-improvement-brief.md` and the repo rules in `CLAUDE.md`.

---

## 0. Ground rules (apply to every part)

1. **Owner approval** before anything that sends a message to a customer or lead, posts publicly, charges money, or changes Jane's live settings. Build an "Approvals" queue (section 3) and route these actions through it.
2. **No secrets in browser code.** API keys (Twilio, Stripe, Supabase service role, OpenAI/Anthropic) live only in server environment variables.
3. **Privacy:** store the minimum. Never put call recordings, transcripts or customer contact details in logs, the Git repo, analytics or AI prompts unless needed for that job. Data stays in Australia where possible; say where it is stored in the privacy policy.
4. **Australian law:** Spam Act 2003 (consent, sender identified, unsubscribe in every marketing email or text), Privacy Act 1988 / APPs, Australian Consumer Law (accurate claims), AI disclosure on calls, call-recording notice (check WA rules).
5. **Cost limits:** every scheduled job has a daily cap on AI tokens and messages; alert the owner at 80% and stop at 100%.
6. **Everything logged:** each automation run writes one row to `automation_runs` (section 2) with what it did, what it cost and whether it failed.
7. **Fail safe:** if a job errors, it stops, logs the error and tells the owner; it never retries a send more than once.

---

## 1. Assumed stack (confirm or adapt)

The current stack is not known to Claude. If different, map each piece to the equivalent:

| Need | Assumed | Alternatives |
|---|---|---|
| Database + auth | Supabase (Postgres, Auth, Row Level Security) | Firebase, Neon + Clerk |
| Server jobs | Supabase Edge Functions + `pg_cron`, or a small Node server | Vercel cron, Cloudflare Workers |
| Phone + SMS | Twilio (Jane's number, call webhooks, SMS) | Vonage, Telnyx |
| Payments | Stripe (subscriptions, trials, webhooks) | — |
| Email | Resend or SendGrid | Postmark |
| Owner alerts | SMS to the owner + email | Slack, Telegram |

---

## 2. Data model (tables)

All tables have `id`, `created_at`, `updated_at`. Turn on Row Level Security so each customer only sees their own rows; the owner (admin role) sees all.

- **`leads`**: name, business_name, trade, suburb, phone, email, source (calculator / call_jane / text_it / form / referral), consent_marketing (bool + timestamp + how), status (new / contacted / trial / won / lost), notes.
- **`customers`**: lead_id, business_name, trade, suburb, plan, stripe_customer_id, trial_started_at, trial_ends_at, status (trial / active / past_due / cancelled), jane_phone_number, owner_mobile, timezone (default Australia/Perth).
- **`calls`**: customer_id, started_at, duration_s, caller_number_hash (hash, not the raw number, for stats), outcome (booked / message / urgent_forwarded / spam / failed), job_value_estimate, summary (short, no sensitive details), recording_url (only if recorded with notice), sentiment (positive / neutral / negative).
- **`messages`**: customer_id or lead_id, channel (sms / email), direction, template_id, status (draft / awaiting_approval / approved / sent / failed), body, approved_by, sent_at.
- **`approvals`**: kind (send_message / post / charge / change_jane), payload (JSON), reason, status (pending / approved / rejected), decided_at.
- **`automation_runs`**: job_name, started_at, finished_at, status (ok / failed / capped), items_processed, cost_cents, error.
- **`jane_issues`**: customer_id, call_id, issue (missed booking / wrong info / upset caller / didn't disclose AI), suggested_fix, status (open / applied / dismissed).

---

## 3. Owner Command Center additions

Add these screens to the existing Command Center (owner/admin only):

1. **Dashboard (home):** today and last 7 days: new leads, trials started, trials ending in 48 hours, paying customers, MRR (from Stripe), calls answered, jobs booked, estimated job value booked, failed calls, site uptime. Small trend chart for each.
2. **Approvals queue:** list of pending items with a preview, and Approve / Edit / Reject buttons. Approving executes the action and logs it. Show the count as a badge in the header.
3. **Automation runs:** table of `automation_runs` with filters; failed runs highlighted red; cost this month vs cap.
4. **Jane quality:** open `jane_issues` with the call summary and the suggested fix; "Apply fix" creates an approval of kind `change_jane`.
5. **Customers:** list with status, plan, trial days left, calls and bookings this month, last contact; click through to a customer page with history.

Each screen: works at phone width, shows loading and error states, never blank.

---

## 4. Automations to build (in this order)

Each one: what triggers it, what it does, what needs approval, and its test.

### 4.1 Site and Jane watchdog (every 15 minutes)
- Checks: homepage returns 200 in under 3 s; Command Center login page loads; Stripe and Twilio APIs reachable; Jane's number answers a test call once a day (Twilio test call at 3am Perth, hang up after greeting, check greeting audio played or call connected).
- On failure: alert the owner by SMS and email once, then every 2 hours while still failing; log to `automation_runs`.
- Approval: none (alerts only go to the owner).
- Test: point it at a URL that returns 500 and confirm one alert.

### 4.2 Lead capture (on event)
- Every source (calculator, Call Jane, Text it, form) creates or updates a `leads` row with source and consent.
- Calculator result is saved with the lead (missed calls, job value, monthly loss), so follow-ups can quote it.
- Owner gets an instant SMS: "New lead: Dave, plumber, Joondalup, losing about $2,400/month (calculator)."
- Test: submit each source and check the row and the alert.

### 4.3 Trial onboarding sequence (on trial start)
Messages are written once as templates; the owner approves each template once, then sends are automatic for trial customers who signed up (transactional, allowed without separate marketing consent; still identify the business and include help contact).
- Day 0 (immediately): welcome email + SMS: setup checklist (forward calls, set business hours, add prices, test call Jane).
- Day 1: if setup not finished, "Need a hand? Reply and we'll set it up for you."
- Day 3: "Jane has answered X calls and booked Y jobs so far." (real numbers from `calls`).
- Day 6: "Your trial ends tomorrow. Here's what Jane did: … Keep her for $___/week." with the billing link.
- Day 7: trial result to the owner: converted or not, plus a suggested personal call script if not.
- Test: create a test customer with a fake trial start date and fast-forward; check each message lands in `messages` with the right numbers.

### 4.4 Lead follow-up (daily 9:30am Perth)
- Leads with status `new` older than 24 hours and `consent_marketing = true`: draft one follow-up message using their calculator result; put it in the Approvals queue (not sent until approved).
- Leads without marketing consent: no message; listed in the owner's briefing as "call manually".
- Maximum 2 follow-ups per lead, ever; stop immediately on reply or unsubscribe.
- Test: leads with and without consent; only consenting ones get drafts.

### 4.5 Jane quality check (nightly 11pm Perth)
- Take up to 20 of the day's calls per customer (summaries only, not recordings or raw numbers).
- An AI reviewer flags: booking missed, wrong price or hours given, caller upset, AI not disclosed, call failed. Create `jane_issues` rows with a suggested fix (e.g. add "we don't do gas fitting" to the FAQ).
- Fixes only reach Jane through an approved `change_jane` approval.
- Daily cost cap for this job.
- Test: seed calls with known problems; confirm issues are found and nothing changes Jane without approval.

### 4.6 Monthly customer report (1st of each month, 8am Perth)
- For each active customer: calls answered, jobs booked, estimated value booked, busiest times, after-hours calls caught, one tip.
- Generated as an email (and a page in their Command Center). First month: owner approves each before sending; after that, auto-send unless the owner turns approval back on.
- Test: generate for a seeded customer; check numbers match the `calls` table.

### 4.7 Churn and payment watch (daily)
- Stripe webhook: `invoice.payment_failed` → customer status `past_due`, owner alerted, polite payment-update email drafted for approval.
- Customers with calls dropping more than 50% week on week, or no calls for 5 days: flag in the briefing ("check their call forwarding").
- `customer.subscription.deleted` → status `cancelled`, exit survey email drafted for approval.
- Test: Stripe test-mode events.

### 4.8 Owner morning briefing (daily 7:14am Sydney is already scheduled by Claude; switch to Perth time if preferred)
Add a server endpoint `GET /api/briefing-summary` (owner-only, API key in server env) that returns yesterday's numbers: leads, trials started and ending, conversions, MRR change, calls, bookings, failed calls, watchdog failures, pending approvals, open Jane issues. The Claude briefing routine (or an email at 7am) uses it. No customer contact details in the response.

### 4.9 Weekly growth loop (Mondays)
- Claude's Scout runs Monday 7:47am Sydney and writes findings to the repo (`scout/list.md`).
- Add: the top Scout finding becomes one task in the Command Center's task list for the week (e.g. "Post in Perth Sparkies Facebook group about missed calls"), owner ticks it off.
- Marketing posts and ads made in 369 Forge go into Approvals before posting.

---

## 5. Jane improvements (phone and text)

1. Greeting discloses AI: "Hi, you've reached [Business], I'm Jane, [Owner]'s AI assistant." If calls are recorded: "This call may be recorded."
2. Urgent detection (burst pipe, no power, gas smell, flooding) → immediately forward to the owner's mobile and SMS a summary; if the owner doesn't answer, tell the caller clearly what happens next.
3. After each call: SMS the business owner a summary within 1 minute (caller name, job, suburb, urgency, booking time if booked).
4. Booking: check the customer's calendar availability (Google Calendar or their job software) before offering times; never double-book.
5. Prices: only quote prices the customer has entered; otherwise "Dave will confirm the price."
6. Hand-off: caller can always say "real person" → take a message and flag it urgent.
7. Text-back: missed call from a mobile → automatic SMS "Sorry we missed you, this is Jane from [Business], how can we help?" (transactional reply to an inbound call; identify the business; stop if they reply STOP).

---

## 6. Security checklist (Command Center and APIs)

- Every page and API route requires login; admin routes require the admin role.
- Row Level Security on every table; test with two customer accounts that neither can read the other's rows.
- Twilio and Stripe webhooks verify signatures.
- No secret keys in browser code or network responses; search the built JS for `sk_`, `service_role`, `AC`, `secret`.
- Rate limits on public forms and the calculator; CAPTCHA or honeypot against spam.
- Backups enabled for the database; test a restore once.
- Audit log of admin actions and approvals.

---

## 7. Tests and monitoring

- Automated browser tests (Playwright) for the public site and Command Center critical paths (see the website brief, Part 6), plus the automation tests listed above.
- All scheduled jobs runnable on demand from the Automation runs screen with a "dry run" option that writes drafts but sends nothing.
- A weekly health email to the owner: jobs run, failures, costs, approvals pending.

---

## 8. Build order and definition of done

1. Data model + Row Level Security (section 2).
2. Watchdog (4.1) and lead capture (4.2): owner gets alerts the same day.
3. Approvals queue + Automation runs screens (section 3).
4. Trial onboarding (4.3) and Jane improvements 1–3 and 7 (section 5).
5. Dashboard + briefing endpoint (3.1, 4.8).
6. Lead follow-up (4.4), churn and payment watch (4.7).
7. Jane quality check (4.5) and monthly report (4.6).
8. Weekly growth loop (4.9).

After each step: run the tests, check on a phone, send the owner screenshots, and do not start the next step until the owner says it works.

**Done** means: the owner wakes up to one briefing with the real numbers, every lead and trial is followed up automatically or queued for one-tap approval, failures are caught within 15 minutes, customers get a monthly report proving Jane's value, and nothing reaches a customer or the public without passing the approval rules.

---

## Send back to Claude

- The repository (push to GitHub and share the name) or screenshots of each new screen.
- Which stack pieces were actually used (section 1), so Claude can test the automations, review security and connect the existing Scout, brain and briefing.
