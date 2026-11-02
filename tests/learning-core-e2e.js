// Proves the organism's learning core actually learns from outcomes.
// Run: node tests/learning-core-e2e.js
import { createLearner, runClover } from "../organism/learning-core.js";

let failures = 0;
function check(name, ok, detail = "") {
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? "  (" + detail + ")" : ""}`);
  if (!ok) failures++;
}

// 1. It converges on the better variant from real outcomes.
// Variant B wins 70% of the time, A wins 20%. Feed real outcomes.
{
  const L = createLearner({ seed: 7 });
  L.defineChoice("sms-opener", ["A", "B"]);
  const rng = (() => { let s = 99; return () => { s = (s * 1103515245 + 12345) & 0x7fffffff; return s / 0x7fffffff; }; })();
  for (let i = 0; i < 400; i++) {
    const v = L.pick("sms-opener");
    const trueRate = v === "B" ? 0.7 : 0.2;
    L.record("sms-opener", v, rng() < trueRate);
  }
  check("learns which opener works (best = B)", L.best("sms-opener") === "B", "best=" + L.best("sms-opener"));
  const st = L.stats("sms-opener");
  check("B's learned rate is higher than A's", st.B.successRate > st.A.successRate,
    `A=${st.A.successRate} B=${st.B.successRate}`);
  check("it explored both (A has tries too)", st.A.tries > 0 && st.B.tries > 0,
    `A.tries=${st.A.tries} B.tries=${st.B.tries}`);
  check("it exploited the winner (B tried more than A)", st.B.tries > st.A.tries,
    `A.tries=${st.A.tries} B.tries=${st.B.tries}`);
}

// 2. A standing rule (owner correction) outranks the maths.
{
  const L = createLearner({ seed: 3 });
  L.defineChoice("send-time", ["8am", "10am", "7pm"]);
  // learn that 8am is great
  for (let i = 0; i < 50; i++) L.record("send-time", "8am", true);
  check("without a rule, best = 8am", L.best("send-time") === "8am");
  // owner says: never text before 9am
  L.ban("send-time", "8am");
  check("after ban, pick never returns 8am", (() => {
    for (let i = 0; i < 100; i++) if (L.pick("send-time") === "8am") return false;
    return true;
  })());
  check("after ban, best is no longer 8am", L.best("send-time") !== "8am", "best=" + L.best("send-time"));
}

// 3. "Feeds as it learns": decay lets it change its mind when the world changes.
{
  const L = createLearner({ seed: 5, decay: 0.9 });
  L.defineChoice("hook", ["old", "new"]);
  // old hook used to win a lot
  for (let i = 0; i < 40; i++) L.record("hook", "old", true);
  check("old hook leads at first", L.best("hook") === "old");
  // the world changed: now 'new' wins and 'old' flops
  for (let i = 0; i < 40; i++) { L.record("hook", "new", true); L.record("hook", "old", false); }
  check("after the world changes, best flips to new", L.best("hook") === "new", "best=" + L.best("hook"));
}

// 4. It persists and reloads (keeps learning across restarts).
{
  const L = createLearner({ seed: 1 });
  L.defineChoice("headline", ["x", "y"]);
  for (let i = 0; i < 20; i++) L.record("headline", "y", true);
  const saved = JSON.stringify(L.toJSON());
  const L2 = createLearner({ seed: 1 }).load(JSON.parse(saved));
  check("reloaded brain remembers the winner", L2.best("headline") === "y", "best=" + L2.best("headline"));
  check("reloaded brain keeps the evidence count", L2.stats("headline").y.tries === 20,
    "tries=" + L2.stats("headline").y.tries);
}

// 5. Honest empty state: with no evidence it still returns a valid option, not a crash.
{
  const L = createLearner({ seed: 2 });
  L.defineChoice("empty", ["p", "q"]);
  const p = L.pick("empty");
  check("cold start returns a real variant (no data yet)", p === "p" || p === "q", "picked=" + p);
  check("cold start best is one of the variants", ["p", "q"].includes(L.best("empty")));
}

// 6. The four-leaf looping system (clover): all leaves bloom, best wins,
//    the brain learns from every leaf, and it stops early on target.
await (async () => {
  const L = createLearner({ seed: 11 });
  L.defineChoice("headline-clover", ["leaf-a", "leaf-b", "leaf-c", "leaf-d"]);
  // a fixed judge: leaf-c is the strongest
  const judge = (leaf) => ({ "leaf-a": 0.3, "leaf-b": 0.5, "leaf-c": 0.9, "leaf-d": 0.4 }[leaf]);
  const res = await runClover(L, "headline-clover", judge, { rounds: 3, target: 0.8 });
  check("clover picks the best leaf", res.winner === "leaf-c", "winner=" + res.winner);
  check("clover reports the winning score", res.score === 0.9, "score=" + res.score);
  check("clover stops early when target hit (1 round)", res.rounds.length === 1, "rounds=" + res.rounds.length);
  check("clover bloomed all four leaves", res.rounds[0].bloom.length === 4, "leaves=" + res.rounds[0].bloom.length);
  check("the brain learned from every leaf", (() => {
    const s = L.stats("headline-clover");
    return s["leaf-a"].tries === 1 && s["leaf-b"].tries === 1 && s["leaf-c"].tries === 1 && s["leaf-d"].tries === 1;
  })());
  check("after the clover, brain's best = the winner", L.best("headline-clover") === "leaf-c",
    "best=" + L.best("headline-clover"));

  // when nothing hits target, it loops the full number of rounds
  const L2 = createLearner({ seed: 12 });
  L2.defineChoice("hard", ["x", "y"]);
  const weak = () => 0.4; // never reaches 0.8
  const res2 = await runClover(L2, "hard", weak, { rounds: 3, target: 0.8 });
  check("clover loops all rounds when target never met", res2.rounds.length === 3, "rounds=" + res2.rounds.length);
  check("clover reports hitTarget false when it falls short", res2.hitTarget === false);

  // a banned leaf never blooms
  const L3 = createLearner({ seed: 13 });
  L3.defineChoice("c3", ["ok", "bad"]);
  L3.ban("c3", "bad");
  const res3 = await runClover(L3, "c3", (v) => (v === "bad" ? 1 : 0.5), { rounds: 2, target: 0.9 });
  check("clover never blooms a banned leaf", res3.winner === "ok", "winner=" + res3.winner);
})();

console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
process.exit(failures ? 1 : 0);
