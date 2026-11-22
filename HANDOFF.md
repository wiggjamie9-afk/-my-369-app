# AI9 + Video Machine - handoff to Kimmy

Branch: `claude/eloquent-noether-akxmmx`. Run everything: `python3 -m unittest discover -s tests -t .` (28 tests; needs ffmpeg).

## What it is
AI9 = a memory brain (recall before answering, save after important things, locked identity file, 7 self-tidying loops).
`video/` = a pipeline that turns a script into a video, using AI9 memory for brand/style and feedback.
Flow: `script -> plan_shots (recalls style) -> cost gate -> provider.generate per shot -> ffmpeg stitch -> save to memory -> rate() feeds the next video`.

## Done and tested (offline)
- `ai9/` memory loop, safety filter (secrets refused, phones/labelled callers stripped), hash-locked DNA, 7 rings (`ai9/loops.py`), cron timings, Stage 3 harness (`ai9/bench.py`).
- `video/` planner, ffmpeg stitcher, budget gate (paid providers blocked without an approved number), memory + rating hooks, `SlateProvider` (free colour slates that prove the pipeline).

## NOT done - Kimmy's list, in order
1. **Pick the video generator** (`video/providers.py`). Hosted: `HostedProvider` (set `usd_per_second` from the real price list, then `generate`). Higgsfield is connected to this workspace as MCP but was never called. Open weights: `OpenWeightsProvider` needs a GPU box; this container has none.
2. **Audio/voice, captions, music, transitions**: not built. Slates are silent. ffmpeg can do captions/mix; voice needs a TTS service.
3. **Real memory backend**: Hindsight key not supplied; `HindsightBackend` is untested and has no list/delete, so the 7 loops cannot run on it yet.
4. **Real AI parts**: rollup wording, contradiction detection and the checker twin are cheap rules; swap in model calls. The checker/grader must be a different model from the agent.
5. **Jamie must**: fill the TODOs in `ai9/dna/DNA.md` then `python3 -m ai9.dna lock`; turn on GitHub "Require review from Code Owners"; supply 50 real questions + notes (`bench/README.md`); approve the Stage 3 cost (about $190 estimate, placeholder prices - verify) before `python3 -m ai9.bench run`.
6. Nothing here has been measured against real models. No claim of "best" has been tested.

## Source research (opinion pieces, not benchmarks - verify before committing)
Open-weight video models: Wan (Alibaba), LTX (Lightricks), HunyuanVideo (Tencent), CogVideoX, Mochi, SkyReels. Guides disagree on the leader and many are vendor blogs. Check each model card and licence (commercial use varies) and test on your own hardware.
- [Open-source AI video generators in 2026 (dev.to)](https://dev.to/jondavis/open-source-ai-video-generators-in-2026-a-developers-benchmark-stack-guide-54i3)
- [Best open-source video generation models (LTX blog - vendor)](https://ltx.io/blog/best-open-source-video-generation-models)
- [Top 5 open-source video generation models (KDnuggets)](https://www.kdnuggets.com/top-5-open-source-video-generation-models)
- [The 8 best open source AI video models (Morphic)](https://morphic.com/resources/list/best-open-source-ai-video-models)

Editing/assembly: ffmpeg (base layer, used here); MoviePy (Python); Remotion (React, source-available - paid licence for companies); alternatives VideoFlow (Apache-2.0 core), Revideo, OpenCut (MIT).
- [Best open source video editor SDKs (IMG.LY)](https://img.ly/blog/best-open-source-video-editor-sdks-2025-roundup/)
- [Open-source AI video tools compared: OpenMontage, Remotion, auto-editor (dev.to)](https://dev.to/eliofbm/open-source-ai-video-tools-compared-openmontage-remotion-and-auto-editor-2odk)
- [Remotion + AI APIs automation pipeline (dev.to)](https://dev.to/comlaterra_38/building-a-video-automation-pipeline-with-remotion-and-ai-apis-4i82)

## Rules to keep
Never save passwords/keys/caller names or numbers. Never spend credits without an approved estimate. Only Jamie edits DNA.
