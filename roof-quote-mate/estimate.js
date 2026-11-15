/* Roof Quote Mate - the pricing sum and the config check.
   Pure functions, no page needed, so they can be tested on their own (see test.js).
   Nothing here mentions roofs: it prices "units x rate x difficulty" for any trade. */
(function (root) {
  "use strict";

  function isNum(v) { return typeof v === "number" && isFinite(v); }

  /* List everything wrong with a config, in plain words. Empty list = good to go. */
  function checkConfig(c) {
    var bad = [];
    if (!c || typeof c !== "object") return ["config.js did not load. Check the file is in the folder and has no typos."];
    if (c.tier !== "lite" && c.tier !== "full") bad.push('tier must be "lite" or "full".');
    if (!c.business || !String(c.business.name || "").trim()) bad.push("business.name is empty.");
    // a full address, or a path on the same site (used when the app is hosted for you)
    if (c.webhookUrl && !/^(https?:\/\/|\/)/i.test(c.webhookUrl)) bad.push("webhookUrl must start with https://");
    [["jobTypes", ["labourPerUnit", "materialPerUnit"]], ["difficulty", ["multiplier"]], ["sizes", ["min", "max"]]].forEach(function (group) {
      var list = c[group[0]];
      if (!Array.isArray(list) || !list.length) { bad.push(group[0] + " needs at least one entry."); return; }
      var seen = {};
      list.forEach(function (item, i) {
        var where = group[0] + " #" + (i + 1) + (item && item.label ? " (" + item.label + ")" : "");
        if (!item || !item.id || !item.label) { bad.push(where + " needs an id and a label."); return; }
        if (seen[item.id]) bad.push(where + " uses an id that is already taken: " + item.id);
        seen[item.id] = true;
        group[1].forEach(function (key) {
          if (!isNum(item[key]) || item[key] < 0) bad.push(where + ": " + key + " must be a number, zero or more.");
        });
        if (group[0] === "sizes" && isNum(item.min) && isNum(item.max) && item.max < item.min) bad.push(where + ": max is smaller than min.");
        if (group[0] === "difficulty" && item.multiplier === 0) bad.push(where + ": multiplier can't be 0.");
        if (item.watch != null && (typeof item.watch !== "string" || item.watch.length > 300)) bad.push(where + ": watch must be text under 300 letters.");
      });
    });
    var p = c.pricing || {};
    if (!isNum(p.gstRate) || p.gstRate < 0 || p.gstRate > 1) bad.push("pricing.gstRate should be like 0.10.");
    if (!isNum(p.spread) || p.spread < 0 || p.spread >= 1) bad.push("pricing.spread should be like 0.10.");
    if (!isNum(p.roundTo) || p.roundTo < 1) bad.push("pricing.roundTo should be 1 or more.");
    if (!isNum(p.minimumJob) || p.minimumJob < 0) bad.push("pricing.minimumJob must be a number, zero or more.");
    if (p.rebate) {
      var last = 0;
      if (!isNum(p.rebate.perUnit) || p.rebate.perUnit < 0) bad.push("pricing.rebate.perUnit must be a number, zero or more.");
      if (!Array.isArray(p.rebate.bands) || !p.rebate.bands.length) bad.push("pricing.rebate.bands needs at least one band.");
      else p.rebate.bands.forEach(function (band, i) {
        if (!band || !isNum(band.upTo) || band.upTo <= last) bad.push("pricing.rebate band #" + (i + 1) + ": upTo must be bigger than the band before it.");
        else last = band.upTo;
        if (!band || !isNum(band.share) || band.share < 0 || band.share > 1) bad.push("pricing.rebate band #" + (i + 1) + ": share must be between 0 and 1.");
      });
    }
    return bad;
  }

  function find(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    throw new Error("Unknown choice: " + id);
  }

  /* ---- exact arithmetic ----
     Browsers do sums in floating point, where 15 x 55 x 1.4 x 0.9 can land a hair under 1039.5 and
     round the wrong way. A price must match what the server records, to the dollar, so every
     figure here is scaled to a whole number (6 decimal places) and worked in BigInt. */
  var M = 1000000n;
  function scale(x) { return BigInt(Math.round(x * 1e6)); }
  function halfUp(n, d) { return (2n * n + d) / (2n * d); }          // n / d rounded to the nearest, halves going up (n >= 0)

  /* A rebate that depends on size, e.g. so many dollars off per unit, paid in full on the first
     band of units and at a smaller share on the next. Returns dollars x 1e26 (the same scale the price sum uses). */
  function rebateScaled(c, units) {
    var r = c.pricing.rebate;
    if (!r) return 0n;
    var u = scale(units), from = 0n, counted = 0n;                    // counted: units x share, scaled 1e12
    r.bands.forEach(function (band) {
      var upTo = scale(band.upTo), top = u < upTo ? u : upTo;
      if (top > from) counted += (top - from) * scale(band.share);
      from = upTo;
    });
    var perUnitCents = halfUp(scale(r.perUnit) * 100n, M);
    return counted * perUnitCents * M * M;                            // (counted / 1e12 x cents / 100 dollars) x 1e26
  }

  /* The few words that go under a price: "including GST", "after the rebate", both, or nothing
     (a business that isn't registered for GST must not say it charges GST). */
  function priceNote(c) {
    var bits = [];
    if (c.pricing.priceSuffix) bits.push(c.pricing.priceSuffix);          // e.g. "per week"
    if (c.pricing.gstRegistered !== false) bits.push("including GST");
    if (c.pricing.rebate) bits.push("after the rebate");
    return bits.join(", ");
  }

  /* picks = { type, difficulty, size } (ids from the config)
     -> { low, high } in whole dollars: what the customer pays, GST included where it applies and
     any rebate taken off. Also grossLow/grossHigh (before the rebate) and rebateLow/rebateHigh.
     The server (qm/estimate.py) does the same sum and a test checks they agree on every choice. */
  function estimate(c, picks) {
    var type = find(c.jobTypes, picks.type);
    var diff = find(c.difficulty, picks.difficulty);
    var size = find(c.sizes, picks.size);
    var p = c.pricing;

    var rateCents = halfUp((scale(type.labourPerUnit) + scale(type.materialPerUnit)) * 100n, M);
    var taxed = !(p.gstRegistered === false || p.ratesIncludeGst);
    var gst = M + (taxed ? scale(p.gstRate) : 0n);
    var mult = scale(diff.multiplier);
    var S = 100n * M * M * M * M;                                     // price sum is dollars x 1e26: 100 cents, four 1e6 factors
    var gross = function (units, spreadSign) {
      var spread = spreadSign < 0 ? M - scale(p.spread) : M + scale(p.spread);
      return scale(units) * rateCents * mult * spread * gst;
    };
    var step = scale(p.roundTo);
    var whole = function (n) { return n < 0n ? 0n : halfUp(n, S) * M; };           // whole dollars, x 1e6
    var down = function (n) { return (whole(n) / step) * step; };
    var up = function (n) { var w = whole(n); return ((w + step - 1n) / step) * step; };
    var near = function (n) { return halfUp(whole(n), step) * step; };
    var dollars = function (n) { return Number(n) / 1e6; };

    var grossLow = gross(size.min, -1), grossHigh = gross(size.max, 1);
    var offLow = rebateScaled(c, size.min), offHigh = rebateScaled(c, size.max);
    var low = dollars(down(grossLow - offLow)), high = dollars(up(grossHigh - offHigh));
    if (low < p.minimumJob) low = p.minimumJob;
    if (high < low) high = low;
    return { low: low, high: high, grossLow: dollars(down(grossLow)), grossHigh: dollars(up(grossHigh)),
             rebateLow: dollars(near(offLow)), rebateHigh: dollars(near(offHigh)), type: type, difficulty: diff, size: size };
  }

  function money(dollars) {
    return "$" + String(Math.round(dollars)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  var api = { checkConfig: checkConfig, estimate: estimate, money: money, priceNote: priceNote };
  root.RQM = root.RQM || {};
  for (var k in api) root.RQM[k] = api[k];
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
