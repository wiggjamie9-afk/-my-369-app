# Kimi master script

Everything Claude has written for Kimi, in the order to build it, with the exact message to paste for each step.
Owner: Jamie (Perth, WA). Main business: The 48 AI Crew, https://48ai.jamiewiggautomation.au/

## The files (attach all of them to Kimi once)

| # | File | What it covers |
|---|---|---|
| 1 | `CLAUDE.md` | Rules for any AI working on the projects: plan first, prove every step, no secrets in the browser, approval before anything is sent or spent, Australian law |
| 2 | `docs/48ai-website-improvement-brief.md` | Website fixes and sales improvements, compliance, speed and SEO, Command Center checks |
| 3 | `docs/organism-automation-brief.md` | Business data model, approvals queue, dashboard, watchdog, lead capture, trial onboarding, follow-ups, Jane quality, reports, churn watch |
| 4 | `docs/command-center-modules-brief.md` | AI cost panel, Perth jobs map, marketing helper for tradies, optional Replica prototyping |
| 5 | `docs/embryo-organism-design.md` | Design principles: shared rules, daily signals, event log, self-pausing routines, safety limits, target state |
| 6 | `docs/jarvis-build-brief.md` | Jarvis: voice and chat assistant over the business and the owner's memory |
| 7 | `docs/369-forge-build-brief.md` | 369 Forge AI image and video studio (content for marketing) |

## How to work with Kimi

- Send **one step at a time**. Don't let Kimi start the next step until you've checked the last one on your phone.
- After every step, ask Kimi for: screenshots (phone and desktop), what was tested, and what was not.
- Push Kimi's code to a **private** GitHub repository so Claude can test and review it.
- If Kimi says something is done, ask "show me the test that proves it."

---

## Step 0: set up (paste this first, with all files attached)

> Read every attached file fully before writing any code, starting with CLAUDE.md. Then tell me: (1) what the website and Command Center are built with today (framework, hosting, database, auth, phone/SMS provider, payments), (2) anything in the briefs that conflicts with how they're built, and (3) a short plan for Step 1 with the files you'll change and how you'll test it. Do not write code yet.

## Step 1: website fixes (website brief, Part 1)

> Do Part 1 of 48ai-website-improvement-brief.md only: fix the floating bars covering the Start button, make the phone number visible and tappable, fix the cramped mobile header, and make the background animation fainter and respect reduce-motion. Test at 390px and desktop, then send me before-and-after screenshots.

## Step 2: website sales improvements (website brief, Parts 2–3)

> Do Parts 2 and 3 of 48ai-website-improvement-brief.md: new hero copy, Call Jane as the main button, price line, the missed-calls calculator, how it works, hear Jane, proof, pricing, FAQ, and the legal pages and AI disclosure. Use placeholders marked [FILL IN] for anything you don't know (price, testimonials, ABN) instead of inventing it. Send screenshots.

## Step 3: speed, Google and tests (website brief, Parts 4 and 6)

> Do Parts 4 and 6 of 48ai-website-improvement-brief.md: Lighthouse 90+ on mobile, titles and descriptions, link previews, local SEO, accessibility, and Playwright tests for the critical buttons and forms. Send the Lighthouse scores and the test output.

## Step 4: Command Center check (website brief, Part 5)

> Go through Part 5 of 48ai-website-improvement-brief.md (Command Center security and quality) and report pass or fail for every item with evidence. Fix the failures, starting with security. Do not add features yet.

## Step 5: business data and alerts (organism brief, sections 2, 4.1, 4.2)

> Using organism-automation-brief.md, build the data model in section 2 with Row Level Security, then the watchdog (4.1) and lead capture with instant owner alerts (4.2). Include the tests listed for each. Show me an alert arriving on my phone.

## Step 6: approvals and dashboard (organism brief, section 3)

> Build the owner Command Center screens from section 3 of organism-automation-brief.md: dashboard, approvals queue, automation runs, Jane quality, customers. Nothing that sends, posts, charges or changes Jane may happen without going through the approvals queue. Screenshots on phone and desktop.

## Step 7: trial onboarding and Jane improvements (organism brief, 4.3 and section 5)

> Build trial onboarding (4.3) and Jane improvements 1, 2, 3 and 7 from section 5 of organism-automation-brief.md. I approve each message template once before it goes live. Test with a fake trial customer and fast-forwarded dates, and show me every message it would send.

## Step 8: follow-ups, churn, quality, reports (organism brief, 4.4–4.8)

> Build 4.4 lead follow-up (consent only, approval required), 4.7 churn and payment watch, 4.5 nightly Jane quality check, 4.6 monthly customer report, and 4.8 the briefing endpoint, one at a time with their tests.

## Step 9: new modules (modules brief)

> Build Module A (AI usage and cost panel) and Module B (Perth jobs map) from command-center-modules-brief.md, then Module C (marketing helper) with everything going through approvals. Use our own usage logs, not undocumented endpoints. Suburb-level data only on the map.

## Step 10: organism upgrades (embryo design)

> Apply the "What to build first" list in embryo-organism-design.md: write organism/TARGET.md with me, add the daily signals table, the event log, the safety limits and automatic pausing of failing routines, and show gaps and paused parts in the dashboard.

## Step 11: Jarvis (Jarvis brief)

> Build Jarvis from jarvis-build-brief.md, stage by stage (section 10). Start with stage 1, the prototype interface with demo data, and send screenshots before connecting anything real.

## Step 11b: Demo Hunter (after Steps 5 and 6)

Attach `demo-hunter-brief.md`, `demo/index.html` and `tests/demo-e2e.js`.

> Read demo-hunter-brief.md, especially section 0 (Spam Act, Do Not Call, no scraping, approvals, daily cap of 20). Keep demo/index.html as the template and keep tests/demo-e2e.js passing. Build section 7 one step at a time, starting with the data tables and suppression list. Show me a test prospect's demo link and the approval card for its email before anything can be sent.

## Step 12: second brain (brain kit)

Attach the `brain-kit` folder from the zip (BRAIN.md, evals.md, the three skills and the two agents).

> Read BRAIN.md, evals.md and the skills and agents in brain-kit. This is the owner's second brain: an Obsidian vault where new sources land in brain/inbox/, a cheap scout model summarises them, a strong librarian model writes linked wiki pages with a source for every fact, and a night shift tidies, scores the evals and writes a report. Do not change the rules. Wire Jarvis's memory_search and memory_save tools (Jarvis brief) to this vault, and show me Jarvis answering an eval question with its source.

## Optional: mobile app (mobile brief)

Attach `mobile-app-brief.md`. Only after the server and Jarvis PWA exist.

> Read mobile-app-brief.md. First tell me honestly whether I need a native app or whether the PWA from the Jarvis brief is enough. If native: build step 1 (create-expo-app + a fake-data Today screen) and tell me exactly how to run it on my iPhone with Expo Go. Reuse the existing server; build no new backend.

## Optional: 369 Forge (Forge brief)

> Read 369-forge-build-brief.md and generator.html. First run one real image and one real video generation with my Hugging Face token and fix what fails, then build Stage 1 (script writer and hook lab) only.

---

## Checks Jamie should do at every step

- Open it on your phone. Does it look right? Do the buttons work?
- Did anything get sent, posted or charged without your approval? (It must not.)
- Ask Kimi: "What did you test, what failed, and what didn't you test?"
- Push the code to the private repo and tell Claude "audit Kimi's step N" for an independent check.
