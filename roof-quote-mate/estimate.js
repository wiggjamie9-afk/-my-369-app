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

  /* A rebate that depends on size, e.g. so many dollars off per kWh, paid in full on the first
     band of units and at a smaller share on the next. Returns cents. No rebate set = 0. */
  function rebateCents(c, units) {
    var r = c.pricing.rebate;
    if (!r) return 0;
    var from = 0, counted = 0;
    r.bands.forEach(function (band) {
      counted += Math.max(0, Math.min(units, band.upTo) - from) * band.share;
      from = band.upTo;
    });
    return counted * Math.round(r.perUnit * 100);
  }

  /* The few words that go under a price: "including GST", "after the rebate", both, or nothing
     (a business that isn't registered for GST must not say it charges GST). */
  function priceNote(c) {
    var bits = [];
    if (c.pricing.gstRegistered !== false) bits.push("including GST");
    if (c.pricing.rebate) bits.push("after the rebate");
    return bits.join(", ");
  }

  /* picks = { type, difficulty, size } (ids from the config)
     -> { low, high } in whole dollars: what the customer pays, GST included where it applies and
     any rebate taken off. Also grossLow/grossHigh (before the rebate) and rebateLow/rebateHigh.
     All sums are done in cents so 0.1 + 0.2 style errors can't creep in. */
  function estimate(c, picks) {
    var type = find(c.jobTypes, picks.type);
    var diff = find(c.difficulty, picks.difficulty);
    var size = find(c.sizes, picks.size);
    var p = c.pricing;

    var rateCents = Math.round((type.labourPerUnit + type.materialPerUnit) * 100);
    var gst = (p.gstRegistered === false || p.ratesIncludeGst) ? 1 : 1 + p.gstRate;
    var grossLow = size.min * rateCents * diff.multiplier * (1 - p.spread) * gst / 100;
    var grossHigh = size.max * rateCents * diff.multiplier * (1 + p.spread) * gst / 100;
    var offLow = rebateCents(c, size.min) / 100, offHigh = rebateCents(c, size.max) / 100;

    var step = p.roundTo;
    var down = function (v) { return Math.floor(Math.round(v) / step) * step; };
    var up = function (v) { return Math.ceil(Math.round(v) / step) * step; };
    var near = function (v) { return Math.round(Math.round(v) / step) * step; };
    var low = down(grossLow - offLow), high = up(grossHigh - offHigh);
    if (low < p.minimumJob) low = p.minimumJob;
    if (high < low) high = low;
    return { low: low, high: high, grossLow: down(grossLow), grossHigh: up(grossHigh),
             rebateLow: near(offLow), rebateHigh: near(offHigh), type: type, difficulty: diff, size: size };
  }

  function money(dollars) {
    return "$" + String(Math.round(dollars)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  var api = { checkConfig: checkConfig, estimate: estimate, money: money, priceNote: priceNote };
  root.RQM = root.RQM || {};
  for (var k in api) root.RQM[k] = api[k];
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
