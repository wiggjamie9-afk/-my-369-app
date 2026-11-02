# The organism's learning core

Written by Claude, 2026-11-02. The real, mathematical version of "an organism that learns from its mistakes and feeds as it learns." Built and tested: `organism/learning-core.js`, `tests/learning-core-e2e.js` (13 checks pass).

## What it actually is

A **Bayesian multi-armed bandit** — the standard, proven way to make a system that learns which choice works from real outcomes. No mysticism: it's the maths that powers A/B testing, ad optimisation and recommendation systems, written small and plain for this organism.

Every decision with more than one option is a **choice** with **variants**:
- which SMS opener to use
- which demo headline
- which follow-up time
- which hook on a clip

The core tries variants, watches what really happens, and shifts toward what works.

## The maths (per variant)

- Beliefs about a variant's success rate are a **Beta(α, β)** distribution. Start α=1, β=1 ("no idea yet").
- An outcome `r` in [0,1] updates it: **α += r, β += (1 − r)**.
- **Posterior mean success rate = α / (α + β)** — that's the learned "how good is this."
- Selection is **Thompson sampling**: draw one sample from each variant's Beta, play the highest. Uncertain variants get explored; proven ones get exploited. The explore/exploit balance is automatic.
- **Decay** (optional) gently forgets old evidence, so the organism adapts when the world changes ("feeds as it learns") instead of being stuck in the past.
- **Standing rules** (ban / force) are the owner's corrections and **outrank the maths**, exactly like `CLAUDE.md` "Rules learned".

## Proven behaviour (from the tests)

- Fed outcomes where variant B wins 70% and A wins 20%, it converged on **B** (learned B=0.69, A=0.17) — exploring both (A: 4 tries, B: 396) then exploiting the winner.
- An owner ban ("never text before 9am") overrode a learned favourite instantly.
- With decay, when a once-great hook started flopping, it **changed its mind** to the new winner.
- It saves and reloads, so it keeps learning across restarts.
- Cold start (no data) returns a valid option and never crashes.

## How it plugs into the business

This is the engine for **Upgrade 5 (learning loop)** in `organism/organism-upgrades-brief.md`. Wire each real decision through it:
1. `pick(choice)` to choose a variant for a real send/action.
2. Record the real outcome with `record(choice, variant, result)` (opened? replied? booked? converted?).
3. `best(choice)` and `stats(choice)` feed the weekly self-review and the dashboard, and propose the winner as the new default — **owner approves** before it becomes the default.

## The honest limit

**It only learns from real outcomes.** Right now the organism has no customers and no live sends, so there is nothing feeding it. This core is the brain, built and ready — but a brain with no senses learns nothing. It comes alive the moment real events flow in: Jane handling real calls, real messages going out and getting real replies. The maths is done. The food is customers.
