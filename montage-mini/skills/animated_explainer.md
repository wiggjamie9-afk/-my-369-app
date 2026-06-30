# Stage Director — Animated Explainer

This is the instruction file an agent reads to run the `animated_explainer`
pipeline. Each stage below names the tool to call, what to produce, and the
quality bar to hold. The Python tools do the mechanical work; this file is the
"how OpenMontage wants it used" layer.

The whole pipeline is wired together in `montagemini/pipeline.py` —
`run_pipeline(request)` runs every stage in order, writes a project directory,
and returns a decision log + review report. Run it directly with
`python montage.py "<your brief>"`.

---

## brief

**Tool:** `montagemini.brief.parse_brief(request) -> Brief`

Read the request and extract: `topic`, `duration_s`, output `profile`
(youtube / shorts / tiktok / square / cinematic), `tone`, and whether
narration is wanted. Defaults: 45s, youtube 16:9, professional tone, narration
on. Keep duration in [8, 180] so the HTML player stays responsive.

Hold the bar: the topic must be the clean subject, with directive scaffolding
("make a 30s ... about") stripped.

## script

**Tool:** `montagemini.script.write_script(brief) -> Script`

Author a title plus one beat per scene. A beat is a 1-4 word Title-Case
headline and one spoken sentence (12-22 words). Scene count scales with
duration (~5.5s per scene).

Two backends, recorded in the decision log:
- **llm** — if `anthropic` is importable and credentials resolve (env var or
  `ant auth login` profile), Claude writes a grounded, factual script. Set
  `MONTAGE_LLM_MODEL` to choose the model.
- **template** — deterministic narrative-arc scaffold (hook -> context ->
  points -> takeaway -> outro). Always works offline; prose is structural,
  not researched. Treat it as a frame to fill, not finished copy.

Hold the bar: never invent statistics; keep sentences narration-ready.

## scene_plan

**Tool:** `montagemini.sceneplan.plan_scenes(script, target_duration_s) -> [Scene]`

Give each scene a duration weighted by its narration length, then scale the
whole timeline toward the requested target. Compute word-level caption timings
so captions highlight in sync with the (browser) narration.

Hold the bar: captions must finish inside their scene; total duration should
land near the target.

## assets

**Tool:** `montagemini.assets.build_assets(scenes, tone) -> [visual]`

Synthesize a vector visual per scene from the style playbook
(`montagemini/styles.py`): a gradient with a gentle hue walk across the piece,
a motif (grid / rays / burst / waves / embers), and deterministic Ken-Burns
camera params. This is the zero-key analogue of "an image per scene" — no
model, no network.

Hold the bar: the look must stay coherent (one palette family), not a slideshow
of unrelated colors.

## compose

**Tool:** `montagemini.compose.build_production(...)` then `render_html(...)`

Emit a single self-contained `final.html`: a canvas animates each scene's
background with Ken-Burns motion, headlines fade through kinetically, captions
highlight word by word, and optional narration uses the browser's
SpeechSynthesis. No FFmpeg, no Remotion — the HTML *is* the video.

Hold the bar: the delivery promise is "motion-led", so backgrounds animate
every frame; never ship static cards.

## review

**Tool:** `montagemini.review.review(scenes, target, narration) -> (passed, report)`

The pre-/post-render gate. There's no mp4 to ffprobe, so validate the plan:
every scene complete, captions in bounds, duration on target, slideshow risk
low. A failing report is surfaced to the user, not swallowed.

Hold the bar: do not present a video whose review failed without saying so.
