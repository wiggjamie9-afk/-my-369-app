# Demo Hunter: build brief

For: Kimi (or any developer). Written by Claude, 2026-10-31.
Business: The 48 AI Crew (https://48ai.jamiewiggautomation.au/), AI receptionist "Jane" for Perth trades.

Idea (from a social post claiming "cold DMs get 2% replies, a finished demo gets 31%"; figures not verified): don't pitch first. Show each prospect a demo that already has their business name on it, and let them hear Jane answer as their receptionist.

Read first: `CLAUDE.md`, `docs/organism-automation-brief.md` (data model, approvals queue), and the working demo page template `demo/index.html` with its tests `tests/demo-e2e.js`.

---

## 0. Rules (Australian law and platform terms)

1. **Spam Act 2003 (email and SMS):** commercial messages need consent. Inferred consent applies only when a business **conspicuously publishes** its email address, the message is relevant to its business, and it has **not** said it doesn't want unsolicited messages. Every message must identify The 48 AI Crew (name, ABN, contact) and include a working unsubscribe honoured within 5 business days. **No SMS to prospects without express consent.**
2. **Calls:** check the Do Not Call Register rules and the Telemarketing and Research Industry Standard before any outbound calling; calling hours and identification rules apply. Recommended: no cold calling in this module.
3. **Data sources:** only official APIs or data the business published itself (e.g. Google Places API under Google's terms, the business's own website). **No scraping** of Google Maps or sites that forbid it, no buying email lists.
4. **Privacy Act:** store only business contact details, keep them secure, delete on request, and say how they were collected if asked.
5. **Honesty (Australian Consumer Law):** demos are labelled as demos; the example conversation is labelled as an example; no fake testimonials or invented numbers.
6. **Owner approval:** nothing is sent until the owner approves it in the Approvals queue. Daily cap: 20 outreach messages maximum.
7. Jane always says she is an AI on demo calls.

---

## 1. Data

Add to the organism data model:

- **`prospects`**: business_name, trade, suburb, website, public_email, email_source_url (where it was published), phone (business line), owner_first_name (if published), no_marketing_notice (bool), status (found / qualified / demo_ready / approved / sent / viewed / called_demo / replied / trial / won / lost / unsubscribed / do_not_contact), score, notes, demo_slug, created_at.
- **`prospect_events`**: prospect_id, type (demo_viewed / demo_called / email_sent / replied / unsubscribed), at, meta.
- **`suppression_list`**: email or domain or phone, reason, at. Checked before every send, forever.

---

## 2. Find and qualify (weekly, owner-triggered)

1. Owner picks trade(s) and suburbs in the Command Center (e.g. plumbers in Joondalup, Wanneroo).
2. The server queries an **official** places source (Google Places API with an API key on the server) for businesses of that type in those suburbs.
3. For each result, read its own website (if robots.txt allows) to find: published email, opening hours, after-hours wording, online booking, and any "no unsolicited marketing" notice.
4. **Score** each 0–10 for likely fit: no after-hours cover (+3), "call 7–5 only" wording (+2), no online booking (+2), sole trader or small team (+2), good reviews but complaints about not answering (+1).
5. Keep the top 20 with a published email and no "no marketing" notice; others are kept as `found` but not contacted.

---

## 3. Personalised demo

1. Each qualified prospect gets a demo link: `https://<demo-host>/demo/?b=<business>&t=<trade>&s=<suburb>&o=<owner first name>&n=<demo line>&e=<opt-out email>`, or a short slug that maps to these values server-side (preferred, so links are short and can be tracked).
2. Use `demo/index.html` as the template (keep its tests passing). It already: puts the business name in the headline, plays an example call in which Jane discloses she is an AI, includes a missed-calls cost calculator, a Call Jane button, the free-trial link, and an opt-out line.
3. **Demo line:** one shared Twilio demo number. When a prospect opens their demo, store `demo_slug` in a short-lived session; when the demo line rings from any number within 30 minutes of a demo view, Jane greets with that business's name ("Thanks for calling about Dave's Plumbing's demo — I'm Jane, an AI assistant…"). Otherwise Jane uses a generic demo greeting. Never pretend to be the prospect's real business to the public: this line is only advertised on demo pages.
4. Track `demo_viewed` (page load with slug) and `demo_called` (call on the demo line matched to a view) into `prospect_events`.
5. `noindex` on all demo pages (already in the template).

---

## 4. Outreach drafts (approval required)

For each `demo_ready` prospect, draft one short email (no attachments), e.g.:

> Subject: Made this for [Business]
>
> Hi [Owner or "there"], I'm Jamie from The 48 AI Crew in Perth. I noticed [Business] takes calls [7–5 / without after-hours cover], so I built a quick demo of Jane answering as your receptionist: [demo link]. You can ring her and hear it. No obligation; if it's not for you, reply "stop" and I won't contact you again.
>
> Jamie · The 48 AI Crew · ABN [FILL IN] · [phone] · [unsubscribe link]

- Drafts go to the Approvals queue with the prospect's details and where the email was published.
- After approval: send from the business domain with SPF, DKIM and DMARC set up; log `email_sent`.
- **One follow-up maximum**, 4 days later, only if the demo wasn't viewed; also needs approval.
- Any reply containing "stop", "unsubscribe", "remove" → `unsubscribed`, add to suppression list, never contact again.

---

## 5. Command Center: Demo Hunter screen

- Pipeline board: found → qualified → demo ready → sent → viewed → called demo → replied → trial → won.
- Per prospect: score and reasons, demo link (open / copy), events timeline, notes.
- Weekly numbers: demos sent, viewed %, called %, replies %, trials, cost per trial. These replace the unverified "31%" claim with real numbers.

---

## 6. Tests

- Existing: `node tests/demo-e2e.js` must keep passing (personalisation, AI disclosure, calculator, opt-out link, escaping of hostile input, no overlap on mobile).
- New: suppression list blocks a send; message without unsubscribe or ABN fails validation; daily cap of 20 enforced; prospect with a "no marketing" notice never gets a draft; nothing sends without approval; demo call within 30 minutes of a view greets with that business name.

---

## 7. Build order

1. Data tables + suppression list.
2. Demo page hosting with slugs and view tracking (template already built).
3. Demo line with view-matched greeting.
4. Find and qualify (official API only).
5. Outreach drafts + approvals + sending + unsubscribe handling.
6. Demo Hunter screen and weekly numbers.

**Done** means: the owner picks "plumbers in Joondalup", approves 10 personalised emails in a few minutes, prospects open demos with their own name, hear Jane answer for them, and every step is tracked, legal and reversible.
