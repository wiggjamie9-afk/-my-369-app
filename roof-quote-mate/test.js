/* Checks the pricing sum and the config check. Run:  node test.js   (no installs needed) */
const assert = require("assert");
global.window = {};
require("./config.js");
const { estimate, checkConfig, money, priceNote } = require("./estimate.js");
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

test("a lead address can be a full URL or a path on the same site", () => {
  const c = clone(config);
  for (const ok of ["https://hooks.example.com/abc", "/q/acme/lead", ""]) { c.webhookUrl = ok; assert.deepStrictEqual(checkConfig(c), [], ok); }
  for (const bad of ["hooks.example.com/abc", "javascript:alert(1)", "ftp://x"]) { c.webhookUrl = bad; assert.strictEqual(checkConfig(c).length, 1, bad); }
});

test("a business not registered for GST adds none and never mentions it", () => {
  const c = clone(config); c.pricing.gstRegistered = false; c.pricing.spread = 0;
  const e = estimate(c, { type: "tile", difficulty: "single", size: "medium" });
  assert.deepStrictEqual([e.low, e.high], [120 * 130, 200 * 130]);
  assert.strictEqual(priceNote(c), "");
  assert.strictEqual(priceNote(config), "including GST");
});

test("a banded rebate comes off the price - worked by hand", () => {
  const c = clone(config);
  c.jobTypes = [{ id: "bat", label: "Battery", labourPerUnit: 200, materialPerUnit: 700 }];         // $900 per kWh
  c.difficulty = [{ id: "std", label: "Standard", multiplier: 1 }];
  c.sizes = [{ id: "family", label: "Family", min: 10, max: 20 }, { id: "huge", label: "Huge", min: 30, max: 60 }];
  c.pricing = { gstRegistered: true, ratesIncludeGst: true, gstRate: 0.1, spread: 0, roundTo: 100, minimumJob: 0,
                rebate: { label: "Battery rebate", perUnit: 250, bands: [{ upTo: 14, share: 1 }, { upTo: 28, share: 0.6 }, { upTo: 50, share: 0.15 }] } };
  assert.deepStrictEqual(checkConfig(c), []);
  // 10 kWh: 9,000 less 10 x 250 = 2,500 -> 6,500.   20 kWh: 18,000 less (14 + 6 x 0.6 = 17.6) x 250 = 4,400 -> 13,600
  let e = estimate(c, { type: "bat", difficulty: "std", size: "family" });
  assert.deepStrictEqual([e.low, e.high, e.grossLow, e.grossHigh, e.rebateLow, e.rebateHigh], [6500, 13600, 9000, 18000, 2500, 4400]);
  // 30 kWh: (14 + 8.4 + 2 x 0.15 = 22.7) x 250 = 5,675.   60 kWh: capped at 50 -> (14 + 8.4 + 3.3 = 25.7) x 250 = 6,425
  e = estimate(c, { type: "bat", difficulty: "std", size: "huge" });
  assert.deepStrictEqual([e.low, e.high, e.rebateLow, e.rebateHigh], [21300, 47600, 5700, 6400]);
  assert.strictEqual(priceNote(c), "including GST, after the rebate");
  c.pricing.rebate.bands[1].upTo = 10;
  assert.ok(checkConfig(c).join(" ").includes("bigger than the band before it"));
  c.pricing.rebate.bands[1] = { upTo: 28, share: 1.5 };
  assert.ok(checkConfig(c).join(" ").includes("share must be between 0 and 1"));
});

test("an option can carry a watch line, and a bad one is refused", () => {
  const c = clone(config);
  c.difficulty[0].watch = "Check this before you go ahead.";
  assert.deepStrictEqual(checkConfig(c), []);
  c.difficulty[0].watch = 5;
  assert.ok(checkConfig(c).join(" ").includes("watch must be text"));
  c.difficulty[0].watch = "x".repeat(301);
  assert.ok(checkConfig(c).join(" ").includes("watch must be text"));
});

test("a price can be labelled, e.g. per week", () => {
  const c = clone(config); c.pricing.priceSuffix = "per week"; c.pricing.gstRegistered = false;
  assert.strictEqual(priceNote(c), "per week");
  c.pricing.gstRegistered = true;
  assert.strictEqual(priceNote(c), "per week, including GST");
});

test("sums are exact: a half-dollar rounds up, never down by a floating-point hair", () => {
  // 15 hours x $55 x 1.4 x 0.9 is exactly $1,039.50. In floating point it can come out at 1039.4999999999998.
  const c = clone(config);
  c.jobTypes = [{ id: "a", label: "A", labourPerUnit: 55, materialPerUnit: 0 }];
  c.difficulty = [{ id: "d", label: "D", multiplier: 1.4 }];
  c.sizes = [{ id: "s", label: "S", min: 15, max: 25 }];
  c.pricing = { gstRegistered: false, ratesIncludeGst: false, gstRate: 0.1, spread: 0.1, roundTo: 1, minimumJob: 0, rebate: null };
  let e = estimate(c, { type: "a", difficulty: "d", size: "s" });
  assert.deepStrictEqual([e.low, e.high], [1040, 2118]);            // 1,039.50 -> 1,040 ; 25 x 77 x 1.1 = 2,117.50 -> 2,118
  c.pricing.roundTo = 5;
  e = estimate(c, { type: "a", difficulty: "d", size: "s" });
  assert.deepStrictEqual([e.low, e.high], [1040, 2120]);            // the whole-dollar figure is rounded first, then taken down or up to a 5
  c.jobTypes[0].labourPerUnit = 1.005;                              // a rate with a half-cent: $1.005 -> 101 cents, not 100
  c.sizes[0].min = c.sizes[0].max = 1000; c.difficulty[0].multiplier = 1; c.pricing.spread = 0; c.pricing.roundTo = 1;
  e = estimate(c, { type: "a", difficulty: "d", size: "s" });
  assert.deepStrictEqual([e.low, e.high], [1010, 1010]);
});

test("a product brand is optional and checked", () => {
  const c = clone(config);
  c.brand = { name: "48 AI Crew Quoting", logoPath: "/static/logo.png" };
  assert.deepStrictEqual(checkConfig(c), []);
  c.brand = { name: "No logo is fine" };
  assert.deepStrictEqual(checkConfig(c), []);
  for (const bad of [{ name: " " }, { logoPath: "x.png" }, { name: "x", logoPath: 5 }, "text"]) {
    c.brand = bad;
    assert.ok(checkConfig(c).join(" ").includes("brand needs a name"), JSON.stringify(bad));
  }
});

test("theme colours are optional and must be real colours", () => {
  const c = clone(config);
  c.theme = { accent: "#3D8BFF", onAccent: "#0B1220" };
  assert.deepStrictEqual(checkConfig(c), []);
  c.theme = { accent: "#3d8bff" };
  assert.deepStrictEqual(checkConfig(c), []);
  for (const bad of [{ accent: "blue" }, { accent: "red; background: url(x)" }, { onAccent: 5 }, "blue"]) {
    c.theme = bad;
    assert.ok(checkConfig(c).join(" ").includes("theme colours"), JSON.stringify(bad));
  }
});

test("money formatting", () => {
  assert.deepStrictEqual([money(17800), money(950), money(1234567)], ["$17,800", "$950", "$1,234,567"]);
});

console.log("\n" + n + " checks passed");
