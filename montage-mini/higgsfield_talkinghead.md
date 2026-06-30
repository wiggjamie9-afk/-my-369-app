# Photoreal "man saying hello" — ready-to-run Higgsfield recipe

The stylized version (`demos/hello-man/final.html`) runs anywhere. For a
**photoreal** talking man, you need Higgsfield video generation, which requires
an **interactive session** — every Higgsfield call shows a per-call approval
prompt that a background/cloud session can't display. Open this repo in Claude
Code (terminal/desktop) or claude.ai with the Higgsfield connector + approvals
enabled, then paste the steps below.

Always run the `get_cost: true` preflight first — it prices the job in credits
and spends nothing.

---

## Step 0 — pick the model (optional but recommended)

```
models_explore(action="recommend",
  query="photoreal talking head, a man waving and saying hello, lip sync, 10 seconds",
  type="video", input="image")
```

Good candidates at time of writing: **kling3_0** (multi-shot, audio/motion),
**seedance_2_0** (identity-consistent), or **kling3_0_turbo** (cheaper/faster).
For true lip-sync to spoken words, a dedicated talking-avatar provider
(HeyGen via OpenMontage's `HEYGEN_API_KEY` gateway) is the strongest option.

## Step 1 — generate the man's portrait (the identity/start frame)

```
generate_image(model="soul_2", params={
  aspect_ratio: "9:16",
  prompt: "Photoreal portrait of a friendly man in his early 30s, short dark hair, "
        + "blue crew-neck shirt, soft studio lighting, neutral grey backdrop, "
        + "looking at camera, natural skin texture, shallow depth of field"})
```

Use `nano_banana_pro` instead for crisp 4K. Note the returned `job_id` — that's
the reference you feed into the video step.

## Step 2 — animate it into a 10s talking clip (cost preflight first)

```
generate_video(model="kling3_0", params={
  aspect_ratio: "9:16",
  duration: 10,
  get_cost: true,                       // <-- preflight; remove to actually generate
  medias: [{ role: "start_image", value: "<job_id from Step 1>" }],
  prompt: "The man smiles warmly, raises his hand and waves, and says 'Hello! I'm Alex. "
        + "Nice to meet you.' Natural head movement, blinking, subtle camera, "
        + "soft studio light. Lip movements match the speech."})
```

Read the credit cost, then re-run the same call **without** `get_cost` to
produce the video. Display it with `job_display(id="<new job_id>")`.

## Step 3 (optional) — dedicated voice

For a specific voice instead of the model's built-in audio, create one with
`create_voice`, then reference it per the model's `medias` audio role (check
`models_explore(action="get", model_id="kling3_0")` for the exact role name).

---

## Cost expectation

Per the estimates we worked out: a single ~10s photoreal clip is the low end of
the motion range — roughly **$0.30–1.00** depending on model/credits. The
`get_cost` preflight gives you the exact number before you spend.

## Why it can't run from the background session

Confirmed across both Higgsfield connectors, on `balance`, and on the no-spend
`get_cost` preflight: every call returns `requires approval` / closes the
permission stream. That gate needs an interactive client to tap "Approve" — it
is an environment limitation, not a problem with the prompt or credits.
