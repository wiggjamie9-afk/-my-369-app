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
