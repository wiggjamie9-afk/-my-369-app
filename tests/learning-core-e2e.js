// Proves the organism's learning core actually learns from outcomes.
// Run: node tests/learning-core-e2e.js
import { createLearner } from "../organism/learning-core.js";

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

console.log(failures ? `\n${failures} check(s) failed` : "\nAll checks passed");
process.exit(failures ? 1 : 0);
