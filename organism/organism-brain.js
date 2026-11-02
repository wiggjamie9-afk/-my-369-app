// A running organism with a brain in each petal.
//
// Structure (nested, domain-neutral — nothing tradie-specific here):
//
//            ┌─────────────── LEAD CLOVER (a brain) ───────────────┐
//            │ learns which petal is performing best                │
//            └───┬───────────┬───────────┬───────────┬─────────────┘
//            petal A     petal B     petal C     petal D
//            (brain)     (brain)     (brain)     (brain)
//         each petal is its own learner that makes and learns its
//         own internal decisions.
//
// So there are two levels of learning at once:
//   • each petal's own brain learns its internal choices (its variants), and
//   • the lead brain learns which petal to trust, from how the petals do.
//
// Both levels are the same maths as the learning core (Beta/Thompson bandit),
// composed. It's generic: a "petal" is any sub-system of the organism, a
// "choice" is any decision that petal makes. Plug in whatever the organism is.
//
// Built on organism/learning-core.js. No framework, no network, no secrets.

import { createLearner } from "./learning-core.js";

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
