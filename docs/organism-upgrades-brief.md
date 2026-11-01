# Organism upgrades: build brief

For: Kimi (or any developer). Written by Claude, 2026-11-01.
Purpose: take the business organism from "runs scheduled tasks" to "senses the business, learns, repairs itself, and stays within safe limits." Build these AFTER steps 5–6 of `docs/organism-automation-brief.md` (data model, watchdog, lead capture, approvals, dashboard), because they need real data and the approvals queue.

Read first: `CLAUDE.md`, `docs/organism-automation-brief.md`, `docs/embryo-organism-design.md`. These upgrades implement the "What to build first" list in the embryo design, plus a learning loop and a money guardrail.

Rules on every upgrade (unchanged): secrets on the server only; anything that sends/posts/charges/changes Jane goes through the approvals queue; works on a phone; every step has a test; nothing auto-posts.

---

## Upgrade 1: the target state (`organism/TARGET.md`) + nightly gap check

**Why:** the organism should know what "healthy" looks like and report the gap, instead of just running jobs.

1. Create `organism/TARGET.md` with the owner, listing the target state as checkable statements, e.g.:
   - Every new lead is contacted or queued within 24 hours.
   - Every trial customer is set up (calls forwarded, prices entered) by day 1.
   - Every active customer gets a monthly value report.
   - Zero failures (site, Jane, payments) older than 24 hours.
   - Cost to acquire a customer stays below [X]% of their first-year value.
2. A nightly job compares the live data to each target and writes the gaps to the morning briefing: which target is missed, by how much, and which routine owns it.

**Test:** seed data that violates two targets; the briefing lists exactly those two with the responsible routine.

## Upgrade 2: daily signals (`signals` table)

**Why:** one shared set of numbers every part reads, so they all pull the same way (the "morphogens" in the embryo design).

1. A nightly job writes one `signals` row: leads_this_week, trial_conversion_rate, jobs_booked_per_customer, open_failures, spend_vs_cap, cac (cost to acquire a customer), ltv_estimate.
2. Parts read the latest signals and adjust: low leads → Scout + content prioritise lead channels; low conversion → onboarding messages flagged for review; rising failures → new non-essential work pauses and the watchdog escalates.

**Test:** set leads low in a seeded signals row; confirm the next content/scout suggestion prioritises lead generation and the dashboard shows the signal.

## Upgrade 3: event log (`events` table)

**Why:** parts should trigger each other through readable events, not hidden timers or direct calls (easier to see, test, and change).

1. Every routine writes to `events` (type, payload, at) and reacts to events rather than calling other routines directly: `trial_started` → onboarding; `payment_failed` → churn watch; `jane_issue_found` → approval.
2. The dashboard shows a live event feed (it already has a demo one in `command-center/index.html`).

**Test:** emit a `trial_started` event for a test customer; confirm onboarding starts from the event alone.

## Upgrade 4: homeostasis limits + auto-pause (`limits`, pruning)

**Why:** the organism must stay within safe bounds and switch off parts that keep failing (the "homeostasis" and "apoptosis" in the embryo design).

1. One `limits` settings record: daily AI spend cap, max outbound messages/day, max follow-ups per lead, failure thresholds, site/Jane response limits. Each limit has an action: alert at 80%, stop non-essential jobs at 100%.
2. A routine that fails 3 runs in a row auto-pauses and is listed in the briefing with a one-tap "resume". A routine that produces nothing useful for 30 days is proposed for removal (owner approves).

**Test:** drive spend to 80% and 100% (one alert, then non-essential jobs stop); make a routine fail 3 times and confirm it pauses and appears in the briefing.

## Upgrade 5: learning loop (the biggest win)

**Why:** the organism should get better every week, not just repeat.

1. **Experiments:** for anything with a choice (a hook, a subject line, a follow-up message, a demo headline), store two variants and which one each send used. Track outcome (opened, replied, booked, converted). After enough data, the organism proposes making the winner the default — owner approves.
2. **Playbook memory:** when the owner corrects something ("don't text before 9am", "that hook flopped"), it's saved as a standing rule (like Forge's standing rules and `CLAUDE.md` "Rules learned") and applied everywhere from then on.
3. **Weekly self-review (Sundays):** the organism writes a short report — which rules saved the most retries, which messages/hooks won, what to change next week — and proposes one improvement for approval.

**Test:** seed two hook variants with outcomes where B clearly wins; confirm the weekly report recommends B and the owner can approve it as the new default.

## Upgrade 6: money guardrail (CAC vs LTV)

**Why:** the one number that decides whether the business works.

1. Compute cost-to-acquire-a-customer (ad/outreach + AI + setup cost ÷ new customers) and first-year value per customer, from Stripe + usage logs.
2. Show both on the dashboard with the ratio; alert the owner if CAC rises above the target share of LTV (from `TARGET.md`).

**Test:** seed numbers where CAC exceeds the limit; confirm the alert fires and the dashboard flags it red.

---

## Build order and done

1. TARGET.md + nightly gap check (Upgrade 1).
2. signals table (2) and events table (3).
3. limits + auto-pause (4).
4. money guardrail (6).
5. learning loop (5) — experiments, playbook memory, weekly review.

**Done** means: the owner's morning briefing shows the gaps against the target state and any paused parts; the organism stays inside its spend and message limits on its own; failing routines switch themselves off and ask to be resumed; and every week it tells the owner what worked and proposes one improvement to approve. Nothing sends, posts, charges or changes Jane without the owner's tap.

## Send back to Claude

Screenshots of the upgraded briefing and dashboard, or the private repo, so Claude can test the gap check, limits, auto-pause and learning loop.
