# The 48 AI Crew: mobile app brief

For: Kimi (or any developer). Written by Claude, 2026-10-31.
Owner: Jamie, Perth WA. Business: The 48 AI Crew (AI receptionist "Jane" for trades).

Goal: a phone app (iOS + Android) that is the owner's Command Center and Jarvis in your pocket: see today's leads, calls and bookings, approve drafts with one tap, and get push notifications for urgent leads and site/Jane outages.

**Decide first — do you even need native?** The Jarvis brief (`docs/jarvis-build-brief.md`) already specifies an **installable web app (PWA)**: it installs to the home screen, works on iPhone and Android, sends push, and is far less work. Build the PWA first. Only build this native app if you specifically need: App Store / Play Store presence, reliable background push on iOS, or device features a PWA can't reach. If you go native, this app reuses the **same server and APIs** as the PWA — do not rebuild the backend.

Read first: `CLAUDE.md`, `docs/jarvis-build-brief.md`, `docs/organism-automation-brief.md`.

---

## Stack

- **Expo (React Native), SDK pinned to the latest stable.** `npx create-expo-app`.
- **expo-router** for navigation. **TypeScript.**
- **expo-notifications** for push. **expo-secure-store** for the login token (never plain storage).
- Talks only to the existing 48 AI Crew server (same endpoints as the PWA). **No API keys in the app** — the app logs in and the server holds all secrets.
- Test on your own phone with the **Expo Go** app during development; build store binaries later with **EAS Build**.

## Screens (reuse the Command Center + Jarvis designs)

1. **Today:** leads today, trials ending, calls answered, jobs booked yesterday, failures; big "approvals waiting" badge. Pull to refresh.
2. **Approvals:** pending drafts (emails, SMS, Jane changes) with Approve / Edit / Reject. This is the app's main job on the go.
3. **Calls:** recent calls with caller, suburb, outcome, urgency. Urgent ones highlighted.
4. **Ask (Jarvis):** chat + push-to-talk; answers from the brain and business data with sources (same API as the Jarvis brief).
5. **Settings:** login, push on/off, quiet hours, sign out everywhere.

## Non-negotiables (same as every brief)

- Owner-only login (passkey or magic link + second factor); token in `expo-secure-store`.
- **Nothing sends, posts, books or charges without an approval tap.**
- No secrets in the app bundle. All data over HTTPS to the owner's server.
- Push for: urgent lead, site down, Jane down, trial ending tomorrow, payment failed. Respect quiet hours except site/Jane down.
- Works offline for viewing the last-loaded Today and Calls (cache); actions require connection.
- Australian privacy: no customer phone numbers or recordings cached on the phone beyond what's needed to show the list.

## Build order

1. `create-expo-app`, expo-router, a fake-data Today screen. Run it on your phone via Expo Go. (This is the "it works on my phone" moment.)
2. Login against the server; secure-store the token.
3. Today + Approvals wired to the real server APIs.
4. Push notifications (expo-notifications) for the alert list.
5. Calls + Ask (Jarvis) screens.
6. EAS Build for a TestFlight / internal Android build; then store submission.

## App Store reality check (so you're not surprised)

- **Apple Developer Program: ~US$99/year. Google Play: one-time US$25.** Both needed to publish.
- App Store review takes days and can reject apps; plan for it.
- You do **not** need the stores to use the app yourself — Expo Go (dev) and EAS internal builds let you and testers run it now, for free.

## Done

The owner opens the app on their phone, sees today's real numbers, gets a push when an urgent lead comes in, and approves the follow-up with one tap — all against the same server as the website and PWA, with nothing sent without approval.
