// The organism's learning core.
//
// What it is, honestly: a Bayesian multi-armed bandit. Every decision the
// organism makes with more than one option (which SMS opener, which hook,
// which demo headline, which follow-up time) is a "choice" with "variants".
// The core tries variants, watches what really happens, and shifts toward
// what works. That is the whole of "learns from its mistakes and feeds as
// it learns" — expressed as equations, not vibes.
//
// The maths (per variant of a choice):
//   Beliefs are a Beta(alpha, beta) distribution over its success rate.
//   Start alpha=1, beta=1 (a flat prior: "no idea yet").
//   A recorded outcome r in [0,1] updates: alpha += r,  beta += (1 - r).
//   Posterior mean success rate  = alpha / (alpha + beta).
//   Uncertainty (variance) shrinks as evidence grows, so new variants get
//   explored and proven ones get exploited. That trade-off is automatic.
//
// Selection = Thompson sampling: draw one sample from each variant's Beta,
// play the highest. Early on (high uncertainty) it explores; as evidence
// piles up it converges on the real winner. This is the "organic" part.
//
// "Feeds as it learns": optional recency decay multiplies old evidence by
// a factor each update, so the organism adapts when the world changes
// (a hook that worked in winter stops working in summer) instead of being
// anchored to the past forever.
//
// Standing rules are hard constraints learned from the owner's corrections
// (like CLAUDE.md "Rules learned"): ban a variant, or force one. Rules win
// over the maths, always — the owner's judgement outranks the bandit.
//
// No framework, no build step, plain ES module. Deterministic when seeded,
// so it can be tested. It holds no secrets and makes no network calls.

// --- a small seedable RNG so behaviour is testable (mulberry32) ---
function makeRng(seed) {
  let s = seed >>> 0;
  return function () {
    s |= 0; s = (s + 0x6d2b79f5) | 0;
    let t = Math.imul(s ^ (s >>> 15), 1 | s);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// Sample from a Gamma(k>=1-ish) then build a Beta sample as X/(X+Y).
// Marsaglia-Tsang for shape>=1; bump shape up by 1 and correct for <1.
function sampleGamma(rng, shape) {
  if (shape < 1) {
    const u = rng() || 1e-12;
    return sampleGamma(rng, shape + 1) * Math.pow(u, 1 / shape);
  }
  const d = shape - 1 / 3;
  const c = 1 / Math.sqrt(9 * d);
  for (;;) {
    let x, v;
    do {
      // Box-Muller normal
      const u1 = rng() || 1e-12;
      const u2 = rng();
      x = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
      v = 1 + c * x;
    } while (v <= 0);
    v = v * v * v;
    const u = rng();
    if (u < 1 - 0.0331 * x * x * x * x) return d * v;
    if (Math.log(u) < 0.5 * x * x + d * (1 - v + Math.log(v))) return d * v;
  }
}

function sampleBeta(rng, a, b) {
  const x = sampleGamma(rng, a);
  const y = sampleGamma(rng, b);
  return x / (x + y);
}

export function createLearner(options = {}) {
  // decay in (0,1]; 1 = never forget. 0.99 = gently favour recent evidence.
  const decay = options.decay == null ? 1 : options.decay;
  const rng = makeRng(options.seed == null ? 12345 : options.seed);
  const choices = new Map(); // name -> { variants: Map(name -> {alpha,beta,tries}), rules }

  function ensure(choiceName) {
    if (!choices.has(choiceName)) {
      choices.set(choiceName, { variants: new Map(), rules: { banned: new Set(), forced: null } });
    }
    return choices.get(choiceName);
  }

  function ensureVariant(choice, variant) {
    if (!choice.variants.has(variant)) {
      choice.variants.set(variant, { alpha: 1, beta: 1, tries: 0 });
    }
    return choice.variants.get(variant);
  }

  function allowedVariants(choice) {
    const names = [...choice.variants.keys()].filter((v) => !choice.rules.banned.has(v));
    if (choice.rules.forced && !choice.rules.banned.has(choice.rules.forced)) {
      return [choice.rules.forced];
    }
    return names;
  }

  return {
    // Register a choice and its options. Safe to call again to add variants.
    defineChoice(choiceName, variants) {
      const c = ensure(choiceName);
      (variants || []).forEach((v) => ensureVariant(c, v));
      return this;
    },

    // Pick a variant to use now (Thompson sampling over allowed variants).
    pick(choiceName) {
      const c = ensure(choiceName);
      const allowed = allowedVariants(c);
      if (allowed.length === 0) return null;
      if (allowed.length === 1) return allowed[0];
      let bestName = allowed[0];
      let bestDraw = -1;
      for (const name of allowed) {
        const v = ensureVariant(c, name);
        const draw = sampleBeta(rng, v.alpha, v.beta);
        if (draw > bestDraw) { bestDraw = draw; bestName = name; }
      }
      return bestName;
    },

    // Record what happened. outcome: true/false, or a reward in [0,1].
    record(choiceName, variant, outcome) {
      const c = ensure(choiceName);
      const v = ensureVariant(c, variant);
      const r = outcome === true ? 1 : outcome === false ? 0 : Math.max(0, Math.min(1, Number(outcome) || 0));
      if (decay < 1) {
        // decay existing evidence toward the prior before adding new evidence
        v.alpha = 1 + (v.alpha - 1) * decay;
        v.beta = 1 + (v.beta - 1) * decay;
      }
      v.alpha += r;
      v.beta += 1 - r;
      v.tries += 1;
      return this;
    },

    // Current best variant by posterior mean success rate (the one to default to).
    best(choiceName) {
      const c = ensure(choiceName);
      const allowed = allowedVariants(c);
      let bestName = null;
      let bestMean = -1;
      for (const name of allowed) {
        const v = ensureVariant(c, name);
        const mean = v.alpha / (v.alpha + v.beta);
        if (mean > bestMean) { bestMean = mean; bestName = name; }
      }
      return bestName;
    },

    // Per-variant numbers, so the dashboard/briefing can show its reasoning.
    stats(choiceName) {
      const c = ensure(choiceName);
      const out = {};
      for (const [name, v] of c.variants) {
        const mean = v.alpha / (v.alpha + v.beta);
        // variance of a Beta(a,b)
        const n = v.alpha + v.beta;
        const variance = (v.alpha * v.beta) / (n * n * (n + 1));
        out[name] = {
          tries: v.tries,
          successRate: Number(mean.toFixed(4)),
          uncertainty: Number(Math.sqrt(variance).toFixed(4)),
          banned: c.rules.banned.has(name),
          forced: c.rules.forced === name,
        };
      }
      return out;
    },

    // Standing rules from the owner's corrections. These outrank the maths.
    ban(choiceName, variant) { ensure(choiceName).rules.banned.add(variant); return this; },
    unban(choiceName, variant) { ensure(choiceName).rules.banned.delete(variant); return this; },
    force(choiceName, variant) { ensure(choiceName).rules.forced = variant; return this; },
    clearForce(choiceName) { ensure(choiceName).rules.forced = null; return this; },

    // Persist and restore, so the organism keeps learning across restarts.
    toJSON() {
      const obj = { decay, choices: {} };
      for (const [cn, c] of choices) {
        obj.choices[cn] = {
          variants: Object.fromEntries([...c.variants].map(([n, v]) => [n, { ...v }])),
          banned: [...c.rules.banned],
          forced: c.rules.forced,
        };
      }
      return obj;
    },
    load(obj) {
      if (!obj || !obj.choices) return this;
      for (const [cn, cs] of Object.entries(obj.choices)) {
        const c = ensure(cn);
        for (const [vn, v] of Object.entries(cs.variants || {})) {
          c.variants.set(vn, { alpha: v.alpha, beta: v.beta, tries: v.tries || 0 });
        }
        c.rules.banned = new Set(cs.banned || []);
        c.rules.forced = cs.forced || null;
      }
      return this;
    },
  };
}

// The four-leaf looping system (the "clover"), the same pattern Forge uses,
// put into the brain. Each round all the leaves (allowed variants) bloom:
// every one is scored, every score is fed back so the brain learns from
// ALL of them (not just the winner), and the loop repeats — improving —
// until a leaf hits the target or the rounds run out. The best leaf wins.
//
//   learner   : a learner from createLearner()
//   choiceName: a choice already defined with its variants (the leaves)
//   score     : (variant) => reward in [0,1]  (your judge; sync or async)
//   options   : { rounds=3, target=0.8, leaves }
//
// Returns { winner, score, rounds: [...], hitTarget }.
export async function runClover(learner, choiceName, score, options = {}) {
  const rounds = options.rounds == null ? 3 : options.rounds;
  const target = options.target == null ? 0.8 : options.target;
  const stats = learner.stats(choiceName);
  // the leaves = the allowed (non-banned) variants of this choice
  let leaves = options.leaves || Object.keys(stats).filter((v) => !stats[v].banned);
  if (leaves.length === 0) return { winner: null, score: 0, rounds: [], hitTarget: false };

  let best = { variant: null, score: -1 };
  const history = [];

  for (let r = 0; r < rounds; r++) {
    const bloom = [];
    for (const leaf of leaves) {
      const reward = Math.max(0, Math.min(1, Number(await score(leaf)) || 0));
      learner.record(choiceName, leaf, reward); // every leaf teaches the brain
      bloom.push({ leaf, reward });
      if (reward > best.score) best = { variant: leaf, score: reward };
    }
    history.push({ round: r + 1, bloom, best: { ...best } });
    if (best.score >= target) break; // good enough — stop looping
  }

  return {
    winner: best.variant,
    score: best.score,
    rounds: history,
    hitTarget: best.score >= target,
  };
}
