# Work log

One entry per stage: date, what was built, checks run and results, what was not checked, next step.

## 2026-10-30
- Built: Forge clover studio (rounds, judge, storyboard, library, stats, settings). Checks: headless browser tests with a fake Hugging Face client, all passed; phone layout checked. Not checked: live Hugging Face API.
- Built: standing rules, failure ledger, `CLAUDE.md`. Checks: rule reaches director and judge; benched model skipped; regression test passed.
- Built: Scout and its first run (4 winners, 1 steal sheet). Not checked: TrustMRR pages directly (blocked by network settings).

## 2026-10-31
- Built: open-source licence rule, second brain (`brain/`), agent team (`.claude/agents/`), Forge tests moved into `tests/`, morning briefing rules (`organism/`), weekly Scout and daily briefing schedules.
- Repo scan: no Kimi commits found on any branch; `main` has never received a merge (7 branches of work outstanding).
- Pointed the Scout at The 48 AI Crew's market (tradie pain, AI receptionist competitors and pricing, channels to reach tradies); side projects get one or two searches per run.
- Brain: added The 48 AI Crew, Dad's Code and AI receptionist market pages; saved the website screenshot as a source. Not checked: the live website (blocked by network settings).
- Wrote docs/48ai-website-improvement-brief.md for Kimi from the homepage screenshot (live site not reachable from this session).
- Wrote docs/organism-automation-brief.md for Kimi: data model, owner Command Center screens, nine automations with approvals and tests, Jane improvements, security checklist, build order.
- Wrote docs/embryo-organism-design.md: developmental-biology principles mapped to the organism design (genome, specialisation, signals, events, checkpoints, pruning, limits, immune system, target shape, learned layer).
- Wrote docs/jarvis-build-brief.md for Kimi: Jarvis interface, server, tools, memory, approvals, proactive jobs, voice, security, tests and 8 build stages. Repo found to be PUBLIC; owner told to make it private.
- Wrote docs/command-center-modules-brief.md: AI usage and cost panel, Perth jobs map, marketing helper for tradie customers, optional GitHub Replica prototyping.
- Wrote docs/KIMI-MASTER-SCRIPT.md: build order and paste-ready prompts for every brief.
- Brain upgrade: inbox/assets/sources/questions/overview/reports, brain-scout (Haiku) and librarian (Opus) agents, ingest/curate/ask skills, edit lock on brain/raw/, nightly night shift; ingested the Buzzoni guide as a source summary and two ideas. Lock currently also blocks new raw files (owner to widen).
- Brain upgrade 2: index summaries, front matter, evals (12 questions), gaps and quick capture, from Karpathy's LLM Wiki idea and open-source versions. Baseline: 0 broken links, eval facts present on all 8 pages.
- Moved the brain inbox to brain/inbox/ so new sources can be saved while brain/raw/ stays fully locked; updated rules, skills, scout agent and the night shift.
- Built demo/index.html (personalised prospect demo, 24 checks passing in tests/demo-e2e.js) and docs/demo-hunter-brief.md for Kimi; added Step 11b to the master script.
- Wrote docs/install-safety-checklist.md: defensive 'before you install' checklist for plugins, MCP servers, npm packages and 'paste this' skills, from the REA MCP-audit idea. Declined the trading, 'leaked hacking vault', reverse-engineer-paid-apps and giveaway-scam screenshots.
- Wrote docs/mobile-app-brief.md: Expo/React Native app for the owner's Command Center + Jarvis, reusing the existing server; recommends building the PWA first. Added as an optional step in the master script.
- Built command-center/index.html: owner dashboard shell (8 departments, orchestrator, approvals queue, stats, activity feed) on demo data, 20 checks passing. Front-end only; live data comes from the server per the organism brief.
- Added a monthly 'wide scan' lane to the Scout (any-niche verified-revenue small businesses) and scheduled it for the first Monday of each month. Weekly run stays focused on The 48 AI Crew.
- Wrote docs/sales-playbook.md: how AI-receptionist and SaaS companies sell, and a funnel for The 48 AI Crew built around the personalised Demo Hunter demo.
- Added n8n as the recommended automation runner in the organism brief (with secret/approval/licence rules and a warning against leaked workflow packs); noted licences in credits.
- Wrote docs/KIMI-STEP1-GO.md: the paste-ready message to start Kimi on Step 1 (website Part 1 fixes), plus what to send back and how to get Claude to audit it.
- Wrote docs/organism-upgrades-brief.md: target state + gap check, signals, event log, homeostasis limits + auto-pause, learning loop, CAC/LTV guardrail. Added as Step 10b in the master script.
- Wrote docs/forge-first-run.md: step-by-step for Forge's first real image and video generation with a Hugging Face token.
- Wrote organism/GENOME.md: the organism's DNA — one canonical file every part inherits (identity, values, hard rules, genes per part, homeostasis, immunity, reproduction, epigenome). Consolidates the scattered rules.
- Wrote docs/RECAP-latest.md: summary of recent decisions (Craft Anything, Forge, agent capabilities, organism anatomy/genome) and the ordered next actions.
