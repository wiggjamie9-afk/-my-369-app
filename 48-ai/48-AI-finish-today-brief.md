# 48 AI — "Finish today" build brief

Source of truth for screens: the **48 AI — Master App Mock** contact sheet (the drawings win over any stripped-down interpretation).
Goal for today: a **TestFlight/demo build that looks and behaves like the mock**, is honest about what is real vs sample data, and is safe to put in front of a first customer.

> Reality check: a full App Store release today is not realistic (App Store Connect setup, in-app purchases, privacy details and Apple review take time). Aim for a **demo/TestFlight build today**, a **paid pilot this week**. Don't promise customers anything the build doesn't do yet.

---

## 1. P0 — build today (device-side, no server needed)

Replace the current tab bar (Home · Talk · Bookings · Quotes) with the mock's: **Today · Inbox · Bookings · Jane**.

| Screen | Must have (acceptance) |
|---|---|
| **Today** | Date + Perth weather; "Jane is ON · N calls · N booked" pill; **Next job** card (time, customer, job, address, "25 min away") with **Call back / Maps / Play call / Done**; "Today's run" list with status chips (Booked / Quoted / New). Maps opens Apple Maps. |
| **Inbox** | "Needs a callback" cards with **URGENT** tag, caller, what they need, time, green call button; "swipe left to clear". |
| **Bookings** | Month calendar with today highlighted + dots on booked days; list of the day's jobs underneath. |
| **Jane** | Square live-call stage (avatar), **On / After hours / Off** toggle, **Test Jane** button, call-forwarding setup card, greeting preview, language chips, plan card ("412 of 600 min used"). |
| **Splash** | Your artwork ("THE 48 AI CREW"), "Open my desk" button. |
| **Your business** | Logo, business name, phone, ABN, what you do, service area, Save. Jane's greeting is built from these fields. |

Rules for P0:
- Show a small **"Sample data"** label on any screen not yet wired to real data. Never present sample data as live.
- Match the mock's layout, colours and wording. No "stripped" versions.

## 2. P1 — this week (needs a small server)

The mock itself marks these as needing server add-ons. Do them in this order:
1. **Real phone answering**: a phone number (e.g. Twilio) forwarding to Jane; booking written to Bookings; callback requests written to Inbox.
2. **Minutes metering** server-side (per account, per month) — needed before charging anyone.
3. **Call recordings + "Play call"** (only with consent handling below).
4. **Jobs map (GPS)**: pins on-device are easy; drive times need a routing API.
5. **Job photos** (needs storage), **Team chat + team accounts** (needs backend), **Invoice** (PDF on-device is possible), **Dictate notes** (on-device speech), **Smart quote** (needs past-job history), **SMS to customers** (costs money per text; only with the user's tick + consent).
6. **In-app purchase** (Starter / Pro / Company) via StoreKit, set up in App Store Connect.

## 3. P2 — later
iPad sidebar layout, Apple Watch app, lock-screen widget, "After the job" review flow.

---

## 4. Plans and pricing (make these editable settings, not hard-coded)

Do **not** launch at A$49.99 for 600 minutes until real cost per minute is measured. After GST and Apple's cut (15–30%, check Apple's current terms) the app keeps roughly 64–77% of the sticker price. Starting hypotheses to test:

| Plan | Suggested start | Included |
|---|---|---|
| Starter | ~A$59/mo | ~150 min |
| Pro | ~A$99–149/mo | ~400 min |
| Company (4 users) | A$199+/mo | shared pool |
| Extra minutes | ~A$0.30–0.50/min | above cost |

- Cap free-trial minutes (e.g. 60). A 30-day free trial with unlimited calls costs real money.
- Keep the **live avatar perk small** (e.g. up to 30 min/month, owner "Test Jane" only). Avatar minutes cost more than voice minutes.
- Measure: cost per minute (phone + speech-to-text + AI + voice + hosting). Break-even at the mock's numbers needs roughly **A$0.08–0.09/min or less** at 412 minutes used.

## 5. Jane's call flow (spec)

1. **Opening line must say it's an AI and mention recording.** Example: "G'day, you've reached *[Business]*. I'm Jane, an AI assistant. This call may be recorded to help book your job. How can I help?"  (The mock's greeting doesn't say AI — change it.)
2. Collect: name, number, address/suburb, what's wrong, urgency, preferred time.
3. Emergency/urgent → mark URGENT, text the owner immediately, offer callback.
4. Book only into free slots; otherwise take a message into Inbox.
5. Never give a price, medical, legal or safety advice unless the owner has set it. Say "I'll pass that to *[owner]*".
6. If the caller asks for a human, take a callback request. Don't pretend to be a person.
7. Confirm details back; end politely; write a short job summary.

## 6. Avatar ("Jane Live")
- One vendor first; test two side by side (reply delay, cost per minute, session limits, reliability).
- **API keys stay on the server**, never in the app.
- Enforce the monthly minute cap on the server; handle session limits (some plans cut sessions at 5 minutes).
- Use a licensed vendor avatar, or a real person's face only with written permission.
- Label it as an AI.

## 7. Languages
- Ship **EN-AU** as the supported language. Label **ES / ZH / IT / VI** as **beta** until each is tested with a native speaker on real call audio.
- Speech recognition and spoken replies are separate: check both per language.
- The AI disclosure and recording notice must be spoken in the caller's language.

## 8. Compliance checklist (not legal advice — verify before selling)
- [ ] Recording consent: several sources say WA needs all parties' consent. Announce at the start; offer a way to decline. Verify against the Surveillance Devices Act 1998 (WA).
- [ ] AI disclosure in the opening line.
- [ ] Privacy policy + App Store privacy answers; voice recordings are personal information (Privacy Act / APPs).
- [ ] SMS to customers: check the Spam Act 2003 / ACMA guidance (consent + opt-out) before enabling.
- [ ] Microphone permission text; delete/retention policy for recordings.
- [ ] No medical/legal advice from Jane; sensitive niches need extra care.

## 9. Hand-over checklist ("done" means all ticked)
- [ ] Tabs are Today · Inbox · Bookings · Jane.
- [ ] Every P0 screen matches the mock and is labelled "Sample data" where not live.
- [ ] Jane's greeting says it's an AI and mentions recording.
- [ ] Plans are editable settings; trial minutes capped.
- [ ] No API keys or secrets in the app; server holds them.
- [ ] Build runs on a real iPhone via TestFlight.
- [ ] A short **known gaps** list is included (what's sample, what's P1/P2).

## 10. Ten test calls before showing a customer
1. Normal booking. 2. Urgent leak at night. 3. Angry caller. 4. Bad line / background noise. 5. Caller with a strong accent. 6. Caller asks "are you a robot?" 7. Caller wants a price. 8. Caller wants a human. 9. Caller changes their mind mid-call. 10. Caller in a second language (beta).
Score each: booked correctly? details right? tone ok? any wrong promises?

## 11. Open questions to settle
- Real cost per minute (so the plans can be fixed).
- Which niche is first (trades is what the mock is built for).
- Whether to sell inside the App Store only, or also directly to businesses (check Apple's rules first).
