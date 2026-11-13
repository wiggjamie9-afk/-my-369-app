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
    if (c.webhookUrl && !/^https?:\/\//i.test(c.webhookUrl)) bad.push("webhookUrl must start with https://");
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
    return bad;
  }

  function find(list, id) {
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    throw new Error("Unknown choice: " + id);
  }

  /* picks = { type, difficulty, size } (ids from the config)
     -> { low, high } in whole dollars, GST included.
     All sums are done in cents so 0.1 + 0.2 style errors can't creep in. */
  function estimate(c, picks) {
    var type = find(c.jobTypes, picks.type);
    var diff = find(c.difficulty, picks.difficulty);
    var size = find(c.sizes, picks.size);
    var p = c.pricing;

    var rateCents = Math.round((type.labourPerUnit + type.materialPerUnit) * 100);
    var gst = p.ratesIncludeGst ? 1 : 1 + p.gstRate;
    var low = size.min * rateCents * diff.multiplier * (1 - p.spread) * gst / 100;
    var high = size.max * rateCents * diff.multiplier * (1 + p.spread) * gst / 100;

    var step = p.roundTo;
    low = Math.floor(Math.round(low) / step) * step;
    high = Math.ceil(Math.round(high) / step) * step;
    if (low < p.minimumJob) low = p.minimumJob;
    if (high < low) high = low;
    return { low: low, high: high, type: type, difficulty: diff, size: size };
  }

  function money(dollars) {
    return "$" + String(Math.round(dollars)).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  }

  var api = { checkConfig: checkConfig, estimate: estimate, money: money };
  root.RQM = root.RQM || {};
  for (var k in api) root.RQM[k] = api[k];
  if (typeof module !== "undefined" && module.exports) module.exports = api;
})(typeof window !== "undefined" ? window : globalThis);
