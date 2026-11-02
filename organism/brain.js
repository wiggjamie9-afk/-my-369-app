// ============================================================================
// ORGANISM BRAIN — single-file, drop-in, no dependencies.
// Everything in one file so you can download it and load it into your organism.
//
// What's inside (all tested, 25 + 9 checks green in the repo):
//   createLearner()   a Bayesian multi-armed bandit (learns from outcomes)
//   runClover()       the four-leaf loop (all leaves bloom, best wins)
//   runCloverMesh()   quadruple clover spinning like clockwork on one brain
//   createOrganism()  a lead clover with a learner brain inside each petal
//
// Plain ES module. No framework, no network, no secrets. Deterministic when
// seeded. Node: `import { createOrganism } from "./brain.js"`.
//
// HONEST NOTE: this is the brain, not the senses. It only learns from REAL
// outcomes you feed it via record(). With nothing fed in, it learns nothing.
// ============================================================================

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

// Quadruple clover, spinning like clockwork in one brain.
// Several clovers (gears) turn together on ONE shared learner. Each tick,
// every gear that isn't finished blooms its four leaves once — so all the
// clovers advance in lockstep, like meshed gears, and every leaf of every
// gear feeds the same brain. A gear stops when its best leaf hits target;
// the mesh stops when all gears are done or the ticks run out.
//
//   learner : one shared learner (one brain)
//   gears   : [{ name, score, target?, leaves? }]  — each is one clover
//   options : { ticks }  — max rounds per gear (default 3)
//
// Returns { gears: [{choice,winner,score,hitTarget,rounds}], ticksRun, allHitTarget }.
export async function runCloverMesh(learner, gears, options = {}) {
  const ticks = options.ticks == null ? 3 : options.ticks;
  const state = gears.map((g) => {
    const stats = learner.stats(g.name);
    return {
      name: g.name,
      score: g.score,
      target: g.target == null ? 0.8 : g.target,
      leaves: g.leaves || Object.keys(stats).filter((v) => !stats[v].banned),
      best: { variant: null, score: -1 },
      rounds: 0,
      done: false,
    };
  });

  let ticksRun = 0;
  for (let t = 0; t < ticks; t++) {
    const anyActive = state.some((g) => !g.done && g.leaves.length > 0);
    if (!anyActive) break;
    ticksRun = t + 1;
    for (const g of state) {
      if (g.done || g.leaves.length === 0) continue;
      for (const leaf of g.leaves) {
        const reward = Math.max(0, Math.min(1, Number(await g.score(leaf)) || 0));
        learner.record(g.name, leaf, reward); // one shared brain learns from every gear's every leaf
        if (reward > g.best.score) g.best = { variant: leaf, score: reward };
      }
      g.rounds += 1;
      if (g.best.score >= g.target) g.done = true;
    }
  }

  return {
    gears: state.map((g) => ({
      choice: g.name,
      winner: g.best.variant,
      score: g.best.score,
      hitTarget: g.best.score >= g.target,
      rounds: g.rounds,
    })),
    ticksRun,
    allHitTarget: state.every((g) => g.leaves.length === 0 || g.best.score >= g.target),
  };
}

export function createOrganism(spec = {}, options = {}) {
  const baseSeed = options.seed == null ? 1000 : options.seed;
  const decay = options.decay;

  // the lead clover: one brain that learns which petal is best
  const lead = createLearner({ seed: baseSeed, decay });
  const petalNames = (spec.petals || []).map((p) => p.name);
  lead.defineChoice("petal", petalNames);

  // one brain per petal, each with its own internal choices
  const brains = new Map();
  const petalChoices = new Map();
  (spec.petals || []).forEach((p, i) => {
    const brain = createLearner({ seed: baseSeed + i + 1, decay });
    const names = [];
    for (const [choice, variants] of Object.entries(p.choices || {})) {
      brain.defineChoice(choice, variants);
      names.push(choice);
    }
    brains.set(p.name, brain);
    petalChoices.set(p.name, names);
  });

  return {
    petals: petalNames,

    // the lead clover decides which petal to use now
    pickPetal() { return lead.pickPetal ? lead.pickPetal() : lead.pick("petal"); },
    bestPetal() { return lead.best("petal"); },

    // reach into a petal's own brain
    brain(name) { return brains.get(name); },

    // let a petal's brain make one of its internal decisions
    pick(petalName, choice) {
      const b = brains.get(petalName);
      return b ? b.pick(choice) : null;
    },

    // record an outcome: it teaches the PETAL's own brain its internal choice,
    // AND credits the LEAD brain for that petal. Two levels learn from one event.
    record(petalName, choice, variant, outcome) {
      const b = brains.get(petalName);
      if (b && choice != null && variant != null) b.record(choice, variant, outcome);
      lead.record("petal", petalName, outcome);
      return this;
    },

    // owner corrections flow to the right level
    banPetal(name) { lead.ban("petal", name); return this; },
    ban(petalName, choice, variant) { const b = brains.get(petalName); if (b) b.ban(choice, variant); return this; },

    // a plain-English-ish snapshot: who's winning, at both levels
    report() {
      const petals = {};
      for (const name of petalNames) {
        const b = brains.get(name);
        const bestChoices = {};
        for (const cn of petalChoices.get(name)) bestChoices[cn] = b.best(cn);
        petals[name] = { bestChoices, stats: Object.fromEntries(petalChoices.get(name).map((cn) => [cn, b.stats(cn)])) };
      }
      return {
        bestPetal: lead.best("petal"),
        leadRanking: lead.stats("petal"),
        petals,
      };
    },

    toJSON() {
      return {
        lead: lead.toJSON(),
        petals: Object.fromEntries([...brains].map(([n, b]) => [n, { brain: b.toJSON(), choices: petalChoices.get(n) }])),
      };
    },
    load(obj) {
      if (!obj) return this;
      if (obj.lead) lead.load(obj.lead);
      for (const [n, cs] of Object.entries(obj.petals || {})) {
        if (brains.has(n) && cs.brain) brains.get(n).load(cs.brain);
      }
      return this;
    },
  };
}
