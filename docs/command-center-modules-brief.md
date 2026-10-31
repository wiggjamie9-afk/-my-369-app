# Command Center: new modules brief

For: Kimi (or any developer). Written by Claude, 2026-10-31.
Adds four modules to The 48 AI Crew's owner Command Center, inspired by tools the owner found on Threads. Build our own versions; do not copy other products' code, branding or text. Follow `CLAUDE.md`, `docs/organism-automation-brief.md` (data model, approvals) and `docs/embryo-organism-design.md` (homeostasis limits).

Order: build after steps 1–3 of the organism automation brief (data model, watchdog and lead capture, approvals queue).

---

## Module A: AI usage and cost panel

Inspired by: TokenBar, a usage and quota tracker for Claude, Codex, Cursor and other AI services. Its licence and maintainer could not be confirmed, so do **not** reuse its code; build our own.

Why: the business runs on paid AI and phone services. This panel is the organism's "energy" signal and enforces the cost caps.

Show (owner only):
- Spend today, this week and this month per service: Anthropic (Claude), OpenAI if used, Twilio (calls, SMS, numbers), speech and voice services, Hugging Face, hosting.
- Spend per customer (cost to serve each tradie) next to what they pay, so unprofitable plans are visible.
- Caps: daily and monthly cap per service with a progress bar; alert at 80%, non-essential jobs paused at 100% (per the homeostasis rules).
- Trend chart for the last 30 days, and the top 5 most expensive jobs or customers.

How:
1. **Primary source: our own logs.** Every AI or phone call made by our server writes a row to `usage_events` (service, customer_id, job_name, units such as tokens, minutes or messages, cost_cents, created_at). Costs are calculated from a `prices` table the owner can edit. This works for every provider and does not depend on undocumented endpoints.
2. **Cross-check daily** against official billing or usage APIs where they exist (Twilio Usage Records API; Anthropic and OpenAI organisation usage or cost reports, admin keys on the server only). Show a warning if our logs and the provider differ by more than 10%.
3. Never call undocumented or reverse-engineered endpoints, and never store anyone's login cookies.

Tests: seeded `usage_events` give the right totals; reaching 80% creates one alert; reaching 100% pauses a non-essential job and shows why.

---

## Module B: jobs map (Perth)

Inspired by: a location-based social app shown on a map of Sydney.

Why: see where leads, calls and booked jobs come from, which suburbs and trades to target, and where customers cluster.

Show:
- A map of Perth with suburb-level circles sized by count, switchable between: calls answered, jobs booked, leads, active customers.
- Filters: date range, trade, customer.
- Side list: top suburbs this month, with change versus last month.
- Click a suburb: counts and the latest few items (no caller phone numbers).

How:
- Leaflet (BSD-2-Clause) with OpenStreetMap tiles (show the required "© OpenStreetMap contributors" attribution) or another licensed tile provider; credit both in `docs/credits.md`.
- Store **suburb and postcode only** for map data (from the job address or caller-provided suburb); never plot exact home addresses or caller locations. Aggregate so a single caller can't be identified (hide suburbs with fewer than 3 items on any view a customer could see).
- Suburb centre points from a public dataset with a compatible licence (for example ABS suburb boundaries, CC BY 4.0, with attribution).

Tests: seeded data draws circles in the right suburbs; filters change counts; no exact addresses in the page data; works at 390px.

---

## Module C: marketing helper for tradie customers (possible upsell)

Inspired by: ads for Holo (AI marketing strategy for $12/month) and Marblism (AI agents doing SEO). Their results claims are marketing and were not verified.

Why: tradies want more jobs, not just answered calls. A simple helper that drafts their local marketing makes Jane stickier and could be a paid add-on.

Features (all drafts go to the approval queue; nothing is posted automatically):
1. **Google Business Profile post drafts:** one per week per customer from their recent jobs (trade, suburb, type of job, no customer names or addresses), e.g. "Hot water system replaced in Joondalup this week…".
2. **Review reply drafts:** for new Google reviews, a short, polite reply in the tradie's tone.
3. **Review requests:** after a booked job is marked done, a draft SMS asking the customer for a review. Only send with the end customer's consent; identify the business; include opt-out (Spam Act).
4. **Local SEO checklist** per customer: business profile complete, categories, service areas, hours, photos, website link, NAP (name, address, phone) consistent.
5. **Monthly marketing note** in the customer's monthly report: what was posted, reviews gained, calls from Google.

Rules: never invent reviews, results or testimonials; never claim rankings or traffic gains we can't show; Google's own policies on reviews apply (no incentives, no fake reviews).

Integration: Google Business Profile APIs require Google's approval for API access; until approved, drafts are copied by the tradie or owner manually.

Tests: drafts contain no customer names or addresses; nothing posts without approval; review request blocked when consent is missing.

---

## Module D: faster screen design with GitHub Replica (optional, for the builder)

GitHub open-sourced **Replica** on 2026-10-28 under the MIT licence: an AI prototyping tool that turns plain language into clickable prototypes using a team's own design system, prompted from the GitHub Copilot app, with an optional self-hosted hub for sharing and comments (source: GitHub changelog, https://github.blog/changelog/2026-10-28-introducing-replica-an-open-source-ai-prototyping-tool).

Use: before building each new Command Center screen, prototype it in Replica with the 369 / 48 AI Crew design system (colours, type, components), show the owner, then build. Optional; only if the builder uses GitHub Copilot.

---

## Not adding (and why)

- "Free vs paid AI tools" lists: useful references, but "free" usually means a limited free plan; tools are chosen per job in the main briefs.
- "100 AI business ideas", remote job posts: not relevant to the Command Center.
- Unknown accounts sending "Hi Mr Handsome" or "commented on your photo, big win!": common romance and phishing scam patterns; do not click links or reply.

---

## Send back to Claude

Screenshots of each module (mobile and desktop) or the private repository, so Claude can test them.
