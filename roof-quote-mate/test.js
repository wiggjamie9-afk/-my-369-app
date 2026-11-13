/* Checks the pricing sum and the config check. Run:  node test.js   (no installs needed) */
const assert = require("assert");
global.window = {};
require("./config.js");
const { estimate, checkConfig, money } = require("./estimate.js");
const config = global.window.RQM_CONFIG;
const clone = (o) => JSON.parse(JSON.stringify(o));
let n = 0;
const test = (name, fn) => { fn(); n++; console.log("ok  " + name); };

test("the shipped config is valid", () => assert.deepStrictEqual(checkConfig(config), []));

test("colorbond, double storey, medium - worked by hand", () => {
  // rate 55 + 65 = $120/m2, x1.25 for two storeys = $150/m2
  // low  120 m2 x 150 = 18,000 less 10% = 16,200 plus GST = 17,820 -> rounds down to 17,800
  // high 200 m2 x 150 = 30,000 plus 10% = 33,000 plus GST = 36,300 -> already on a hundred
  const e = estimate(config, { type: "colorbond", difficulty: "double", size: "medium" });
  assert.deepStrictEqual([e.low, e.high], [17800, 36300]);
});

test("tin, single storey, small", () => {
  // $85/m2: low 80 x 85 = 6,800 x 0.9 x 1.1 = 6,732 -> 6,700 ; high 120 x 85 = 10,200 x 1.1 x 1.1 = 12,342 -> 12,400
  const e = estimate(config, { type: "tin", difficulty: "single", size: "small" });
  assert.deepStrictEqual([e.low, e.high], [6700, 12400]);
});

test("every combination gives a sane range", () => {
  for (const t of config.jobTypes) for (const d of config.difficulty) for (const s of config.sizes) {
    const e = estimate(config, { type: t.id, difficulty: d.id, size: s.id });
    assert.ok(Number.isInteger(e.low) && Number.isInteger(e.high), "whole dollars");
    assert.ok(e.low % config.pricing.roundTo === 0 && e.high % config.pricing.roundTo === 0, "rounded");
    assert.ok(e.low >= config.pricing.minimumJob && e.high >= e.low, "ordered and above the minimum");
  }
});

test("harder jobs and bigger roofs never come out cheaper", () => {
  const at = (d, s) => estimate(config, { type: "tile", difficulty: d, size: s });
  assert.ok(at("double", "medium").high > at("single", "medium").high);
  assert.ok(at("triple", "medium").low > at("double", "medium").low);
  assert.ok(at("single", "large").low > at("single", "small").low);
});

test("rates that already include GST are not taxed twice", () => {
  const c = clone(config); c.pricing.ratesIncludeGst = true; c.pricing.spread = 0;
  const e = estimate(c, { type: "tile", difficulty: "single", size: "medium" });
  assert.deepStrictEqual([e.low, e.high], [120 * 130, 200 * 130]);
});

test("the minimum job charge is a floor", () => {
  const c = clone(config); c.pricing.minimumJob = 9000;
  const e = estimate(c, { type: "tin", difficulty: "single", size: "small" });
  assert.deepStrictEqual([e.low, e.high], [9000, 12400]);
  c.pricing.minimumJob = 50000;
  const f = estimate(c, { type: "tin", difficulty: "single", size: "small" });
  assert.deepStrictEqual([f.low, f.high], [50000, 50000]);
});

test("decimal rates do not drift", () => {
  const c = clone(config); c.jobTypes[0].labourPerUnit = 0.1; c.jobTypes[0].materialPerUnit = 0.2;
  c.pricing = { ratesIncludeGst: true, gstRate: 0.1, spread: 0, roundTo: 1, minimumJob: 0 };
  c.sizes[0].min = c.sizes[0].max = 1000;
  const e = estimate(c, { type: "tile", difficulty: "single", size: "small" });
  assert.deepStrictEqual([e.low, e.high], [300, 300]);              // 0.1 + 0.2 = 0.3, not 0.30000000000000004
});

test("another trade drops in by config alone", () => {
  const painter = clone(config);
  painter.trade = { productName: "Paint Quote Mate", jobName: "repaint", unit: "room" };
  painter.jobTypes = [{ id: "interior", label: "Inside", labourPerUnit: 450, materialPerUnit: 150 }];
  painter.difficulty = [{ id: "std", label: "Standard ceilings", multiplier: 1 }];
  painter.sizes = [{ id: "few", label: "3 to 4 rooms", min: 3, max: 4 }];
  painter.pricing = { ratesIncludeGst: true, gstRate: 0.1, spread: 0, roundTo: 50, minimumJob: 500 };
  assert.deepStrictEqual(checkConfig(painter), []);
  const e = estimate(painter, { type: "interior", difficulty: "std", size: "few" });
  assert.deepStrictEqual([e.low, e.high], [1800, 2400]);
});

test("a broken config is explained, not crashed on", () => {
  const c = clone(config);
  c.tier = "pro"; c.business.name = " "; c.webhookUrl = "zapier.com/hook"; c.jobTypes[1].labourPerUnit = "55";
  c.sizes[0].max = 10; c.difficulty[0].multiplier = 0; c.jobTypes[2].id = "tile"; c.pricing.spread = 2;
  const bad = checkConfig(c).join("\n");
  for (const expected of ['"lite" or "full"', "business.name", "https://", "labourPerUnit must be a number", "max is smaller than min",
                          "multiplier can't be 0", "already taken: tile", "pricing.spread"]) assert.ok(bad.includes(expected), expected + "\n" + bad);
  assert.strictEqual(checkConfig(undefined).length, 1);
  assert.throws(() => estimate(config, { type: "slate", difficulty: "single", size: "small" }), /Unknown choice/);
});

test("money formatting", () => {
  assert.deepStrictEqual([money(17800), money(950), money(1234567)], ["$17,800", "$950", "$1,234,567"]);
});

console.log("\n" + n + " checks passed");
