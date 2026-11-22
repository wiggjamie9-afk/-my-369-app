# BUILD BRIEF for Kimi: AI9 memory + UGC ad factory

You are finishing a project started by another AI. Read this whole file, then `HANDOFF.md`, then the code.
Repo: `wiggjamie9-afk/-my-369-app`. Work on branch `claude/eloquent-noether-akxmmx`. Python 3.13, stdlib only so far, ffmpeg required.
Run all tests: `python3 -m unittest discover -s tests -t .` (39 pass today). Do not break them. Add tests for everything you add.

## 0. The owner and the ground rules (Jamie)
1. NEVER save passwords, API keys, caller names or caller numbers (anywhere: memory, logs, test data, commits).
2. NEVER spend paid credits or call a paid API without Jamie approving a written dollar estimate first. The code already gates this (`approved_budget`); keep it.
3. ONLY Jamie edits `ai9/dna/DNA.md`. Never edit it. If it must change, ask Jamie, who edits it and runs `python3 -m ai9.dna lock`.
4. Secrets come from environment variables only (`HINDSIGHT_API_KEY`, `MUAPI_API_KEY`, model keys). Never write a key into a file or chat.
5. Do not claim anything works until it was run. Report real numbers. If a test fails, say so.
6. No fake testimonials. AI presenters demonstrate or explain; they never claim personal experience. Every ad is labelled AI-generated.
7. Do not open a pull request unless Jamie asks. Push to the branch above only.

## 1. What this is
**AI9** = a memory brain for AI assistants: recall before every answer, save after anything important, locked identity file, 7 self-tidying loops, and a test proving "looping memory" beats plain memory.
**UGC factory** = turns a brand brief into many short vertical "user-style" video ads: hooks -> scripts -> compliance check -> cost-gated generation -> AI label -> results fed back into memory.
Inspiration: an Instagram post showing a multi-agent "AI UGC studio" (trend research, scripts/hooks, AI creators, voice, edit, variants, testing, publishing). Its numbers were labelled "illustrative"; treat it as a target shape, not proof.

## 2. What already exists (tested offline only)
- `ai9/agent.py` recall-then-answer, save-after-important. `ai9/memory.py` Memory(who, what, when, source, recall_count, score, status, cluster, is_dna), `LocalBackend` (JSON file), `HindsightBackend` (REST, UNVERIFIED, add/search only).
- `ai9/safety.py` refuses secrets; strips phones + labelled caller names. `ai9/dna.py` hash-locked DNA, refuses to start if tampered. `.github/CODEOWNERS`.
- `ai9/loops.py` seven rings: save, rollup, dedupe, fade, link, conflict, checker twin (rule-based stand-ins). `ai9/jobs.py` runner, `ai9/schedule.cron`.
- `ai9/bench.py` Stage 3 harness (simulated models only). `ai9/recall_test.py` 10-fact recall test.
- `video/` planner, providers (Slate=free placeholder, Hosted/OpenWeights = stubs), ffmpeg stitcher, `pipeline.make_video`, `rate()`.
- `ugc/` Brief, compliance lint, hook writer, `MuapiProvider` (unverified), `factory.run_batch`, `record_result`. `NOTICE` credits the MIT-licensed Open-AI-UGC repo.

## 3. Build in this order (stop and report after each phase)

### Phase A - make memory real (needs keys from Jamie)
A1. Verify `HindsightBackend` against the live API (base `https://api.hindsight.vectorize.io`, bearer key, one shared bank id `ai9-shared`). Fix paths; docs: docs.hindsight.vectorize.io (retain, recall, banks). Optionally add an MCP route (`/mcp/{bank_id}/`) if Jamie wants MCP specifically.
A2. Add `all()`, `delete(id)`, `commit()` to the Hindsight backend (or an equivalent) so the 7 loops can run on the cloud bank.
A3. Wire a real LLM for `AI9.answer` (a `llm(system,user)->str` callable) and real `judge_important`.
A4. Run `python3 -m ai9.recall_test hindsight` with a real model. Report the score honestly. Pass target: all 10 facts correct in a fresh session.
Acceptance: live recall score reported; all earlier tests still pass.

### Phase B - make the loops smart
B1. Replace rule stand-ins with model calls: rollup summarizer, contradiction detector, link clustering (embeddings or model).
B2. Checker twin = a DIFFERENT model/provider from the agent. `make_llm_checker` already refuses same-model; keep that.
B3. Install the schedule (`ai9/schedule.cron`) on a real runner (cron/GitHub Actions/cloud scheduler) only after Jamie says so.
Acceptance: unit tests with stubbed models + one live run on a scratch bank (never Jamie's real bank without approval).

### Phase C - UGC factory to real output
C1. Verify `MuapiProvider` live: confirm the result-polling path (`RESULT_PATH` in `ugc/muapi.py` is a guess; Open-AI-UGC uses webhooks) and the payload per model. Get real USD pricing and set `usd_per_credit` (the repo's credit rates are NOT dollars). First live test = ONE shortest clip, estimate approved by Jamie.
C2. Voice + lip-sync: add a TTS/voice provider (e.g. ElevenLabs) and a lip-sync step. Interface: `voice(script)->audio_path`.
C3. Edit polish: burned captions (check ffmpeg `drawtext`/subtitles works with a real font), b-roll slots, music bed, hook-first pacing, 9:16 normalisation. Keep the visible AI label + sidecar JSON.
C4. Trend/competitor research agent (inputs: public ad libraries, TikTok trends via an official/allowed API). Respect each platform's terms; no scraping that breaks them. Output feeds `write_hooks`.
C5. Hook writer with a real LLM + a variants step (same ad, N hooks). Everything still passes `ugc.compliance.lint`.
Acceptance: one real 9:16 AI-labelled ad from a real brief, estimate approved first, cost reported, compliance lint clean.

### Phase D - test, learn, publish
D1. Testing loop: given real results (views, clicks, spend) via `record_result`, pick winners, propose budget moves. Proposals only; a human approves any spend change.
D2. Publishing adapters (TikTok/Meta/Shorts) behind a human approval step. Never auto-post. Check each platform's AI-content label rules (not yet researched) and implement them.
D3. Stage 3 benchmark for real: Jamie writes 50 questions + notes first (`bench/README.md`), runs `python3 -m ai9.bench lock`, you send the cost estimate, Jamie approves, then run 100 runs per arm. Different model grades. Pass mark: looping >= 1.5x plain (relative; confirm with Jamie). Report % correct, confident-wrong %, cost per run.

## 4. Specs you must not weaken
- `ugc/compliance.py`: blocks first-person experience claims unless the text contains a quote listed in `brief.verified_quotes`; blocks `%`, `#1`, guarantee, cure, clinically, proven, doctor, "best in" unless in `brief.verified_claims`. You may make it stricter, never looser. Add tests for every new pattern.
- `ai9/safety.py`: secrets are refused whole; phones/labelled callers redacted. Known gap: unlabelled names in free text. Close it with the checker twin and add tests.
- Cost gate: any `paid` provider must raise before generating if `estimate > approved_budget`, and refuse if it has no price.
- Dedupe must never merge facts with different numbers or flipped negation (past bug, regression test exists).
- DNA memories are never faded, merged or superseded.

## 5. Legal / safety (not legal advice; Jamie should get a lawyer to review before paid ads)
The FTC bans fake and AI-generated testimonials (fines ~US$50k per violation). Do not generate reviews, ratings or customer stories. Use real quotes only with permission. Label AI content. Platform AI-label rules for TikTok/Meta still need researching.

## 6. Open questions for Jamie (ask, do not guess)
1. What is the content for (brand/product/audience)? The first message was cut off. Fill `ugc/brief.example.json`.
2. Hindsight key, a model key, and a SECOND-provider key (for checker/grader), MuAPI key, voice-provider key. Via the secure credential form, never chat.
3. "50% better" = relative (1.5x) or +50 points?
4. Stage 3 budget ceiling (current estimate ~US$190 using PLACEHOLDER prices - re-verify; excludes Hindsight fees and data loading).
5. Which platforms to publish to; is MCP required for Hindsight?
6. GitHub: turn on "Require review from Code Owners" for `ai9/dna/` (Jamie only; a repo setting).

## 7. Definition of done
All tests green; live recall score reported; one real approved-budget AI-labelled ad produced and its true cost reported; the 50-question benchmark run once with honest numbers; `HANDOFF.md` updated with what is verified vs not. No claims of "best in the world" without a measured comparison.
