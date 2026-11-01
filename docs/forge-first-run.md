# 369 Forge: your first real run

Forge (`generator.html`) is built and tested, but it has never generated a real image or video — it was only tested against a fake. This is how to make it produce for real. About 10 minutes.

## Step 1: get a free Hugging Face token (once)

1. Go to **huggingface.co** and make a free account (or sign in).
2. Go to **Settings → Access Tokens** (huggingface.co/settings/tokens).
3. **Create new token.** Give it a name like `369-forge`. Under permissions, tick **"Make calls to Inference Providers"** (this is the important one).
4. Copy the token (starts with `hf_...`). Keep it private — it's like a password.

## Step 2: open Forge and add the token

1. Open `generator.html` in Chrome or Edge (double-click the file, or host it).
2. Go to the **Settings** tab.
3. Paste your token into **Hugging Face access token**. It's saved only in your browser.

## Step 3: make your first image

1. Go to **Create**, mode **Image**.
2. Type a simple prompt, e.g. `a golden sacred-geometry vortex, cinematic, dark background`.
3. Leave rounds at 3, target 8. Press **GENERATE**.
4. Watch the four leaves generate, get judged, and a winner appear. It saves to the **Library**.

## Step 4: make your first video

1. When you have an image you like, press **"Animate this →"** on the winner (cheapest, best path), or switch to **Video** mode and prompt directly.
2. Press GENERATE. Video takes longer (1–5 min per clip) and costs more.

## What to expect

- **First run is the real test.** If a model isn't served that day, the card says so — pick another in Settings or try again.
- **Cost:** the free Hugging Face allowance covers a few images; after that it's cents per image, more per video. The cost hint shows the max per run before you press go.
- **Perfect scenes as images first, then Animate** — far cheaper than video retries.

## When it works, tell Claude

Send Claude: what generated, any error messages, and which models won (the Stats tab). Then Claude can:
- fix anything that failed against the live API,
- tune the default leaf models to what's actually fast and good right now,
- build Stage 1 of the Forge brief (script writer + hooks) so you go from an idea to a finished clip.

## If you hit an error

Common ones and what they mean (Forge shows a plain message):
- "Token rejected" → the token is missing the Inference Providers permission; remake it.
- "Out of credits" → free allowance used; add billing on Hugging Face or use cheaper leaves (FLUX.1-schnell).
- "No provider serves this model" → swap that leaf's model in Settings.

Bring the exact message to Claude and it'll sort it.
