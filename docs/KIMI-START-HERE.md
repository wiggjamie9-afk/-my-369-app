# Paste this into Kimi first

Upload the whole `kimi-scripts` zip to Kimi, then paste the message below exactly. It starts Kimi safely: it reads everything, tells you the current setup, and does only the first two steps. Do not let it run ahead.

---

You are my build assistant for The 48 AI Crew, an AI receptionist ("Jane") for trade businesses in Perth, Australia. The website is https://48ai.jamiewiggautomation.au/ .

I've attached a set of build briefs. Work through them exactly as KIMI-MASTER-SCRIPT.md lays out, one step at a time, and stop after each step for me to check it.

Rules you must follow on every step (from CLAUDE.md):
- Plan before you code. Show me the plan and wait for my OK on anything bigger than a small fix.
- No API keys or secrets in front-end code or in any repo. Keys live on the server in environment variables.
- Nothing that sends, posts, emails, books or charges happens without me approving it first.
- Everything must work on a phone (390px wide) and on desktop, with no errors.
- After each step tell me exactly: what you changed, what you tested, what passed, and what you did NOT test.
- Australian law applies: label AI content, get consent before texting or cloning a voice, follow the Spam Act.

Do STEP 0 now and then stop:
1. Read every attached brief fully, starting with CLAUDE.md, then KIMI-MASTER-SCRIPT.md.
2. Tell me what my website and Command Center are built with today: the framework, where it's hosted, the database, how login works, and whether I'm using Twilio (calls/SMS), Stripe (payments) and Supabase.
3. List anything in the briefs that conflicts with how it's actually built.
4. Give me a short plan for STEP 1 (the website overlap fixes in 48ai-website-improvement-brief.md, Part 1): which files you'll change and how you'll test them.

Do not write any code yet. Wait for me to say "go" before STEP 1.

---

## After Step 0

- Read Kimi's answer. If it says what the site is built with, tell me (Claude) — that unblocks the live-site audit.
- When you're happy with the Step 1 plan, reply "go" to Kimi.
- After Step 1, ask Kimi for before/after screenshots, then push the code to a PRIVATE GitHub repo and tell me "audit Kimi's step 1".

## The order after that (from KIMI-MASTER-SCRIPT.md)

1–4: website (fixes → sales → speed/SEO → Command Center security check)
5–8: business data, alerts, approvals, dashboard, trial onboarding, Jane improvements, reports
9: cost panel, Perth jobs map, marketing helper
10: organism upgrades (signals, target, limits)
11: Jarvis · 11b: Demo Hunter · 12: second brain
Optional: mobile app, 369 Forge

One step at a time. Check each on your phone before the next.
