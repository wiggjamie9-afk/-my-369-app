// Proves the nested organism brain: a brain in each petal + a lead brain
// that learns which petal is best. Run: node tests/organism-brain-e2e.js
import { createOrganism } from "../organism/organism-brain.js";

let failures = 0;
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!ok) failures++;
}

// Four petals, each its own brain with an internal "move" choice.
const org = createOrganism({
  petals: [
    { name: "sense", choices: { move: ["a", "b"] } },
    { name: "plan", choices: { move: ["a", "b"] } },
    { name: "act", choices: { move: ["a", "b"] } },
    { name: "reflect", choices: { move: ["a", "b"] } },
  ],
}, { seed: 42 });

// Reality: the "act" petal is the strongest performer overall; and inside
// every petal, internal move "b" is better than "a".
const rng = (() => { let s = 7; return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; }; })();
const petalStrength = { sense: 0.3, plan: 0.4, act: 0.8, reflect: 0.35 };

for (let i = 0; i < 600; i++) {
  const petal = org.pickPetal();
  const move = org.pick(petal, "move");
  // outcome depends on both: which petal, and whether its internal move was "b"
  const base = petalStrength[petal];
  const moveBonus = move === "b" ? 0.15 : -0.15;
  const success = rng() < Math.max(0, Math.min(1, base + moveBonus));
  org.record(petal, "move", move, success);
}

const rep = org.report();

check("lead brain learned the best petal = 'act'", org.bestPetal() === "act", "best=" + org.bestPetal());
check("each petal has its own brain", org.brain("sense") && org.brain("act") && org.brain("reflect"));
// The lead exploits the winner, so only well-used petals gather enough data
// to learn their internals. The winning petal ('act') definitely should.
check("the used petal's own brain learned internal move 'b' is better",
  rep.petals.act.bestChoices.move === "b", "act.move=" + rep.petals.act.bestChoices.move);
// honest: a petal the lead abandons stays uncertain — that's correct, not a bug.
check("a starved petal has little internal data (expected)",
  rep.petals.sense.stats.move.a.tries + rep.petals.sense.stats.move.b.tries < 50,
  "sense tries=" + (rep.petals.sense.stats.move.a.tries + rep.petals.sense.stats.move.b.tries));
check("lead explored all four petals", ["sense", "plan", "act", "reflect"].every((p) => rep.leadRanking[p].tries > 0));
check("lead exploited the winner (act tried most)",
  rep.leadRanking.act.tries >= Math.max(rep.leadRanking.sense.tries, rep.leadRanking.plan.tries, rep.leadRanking.reflect.tries),
  `act=${rep.leadRanking.act.tries}`);

// owner correction at the lead level: never use 'reflect'
org.banPetal("reflect");
check("banned petal never gets picked", (() => {
  for (let i = 0; i < 100; i++) if (org.pickPetal() === "reflect") return false;
  return true;
})());

// persistence across restarts (both levels)
const saved = JSON.stringify(org.toJSON());
const org2 = createOrganism({
  petals: [
    { name: "sense", choices: { move: ["a", "b"] } },
    { name: "plan", choices: { move: ["a", "b"] } },
    { name: "act", choices: { move: ["a", "b"] } },
    { name: "reflect", choices: { move: ["a", "b"] } },
  ],
}, { seed: 42 }).load(JSON.parse(saved));
check("reloaded organism remembers best petal", org2.bestPetal() === "act", "best=" + org2.bestPetal());
check("reloaded organism remembers a petal's internal winner", org2.report().petals.act.bestChoices.move === "b");

console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
process.exit(failures ? 1 : 0);
