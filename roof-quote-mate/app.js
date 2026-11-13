/* Roof Quote Mate - the app. Reads everything from config.js; has no rates, names or trade words of its own. */
(function () {
  "use strict";
  var RQM = window.RQM, config = window.RQM_CONFIG;
  var app = document.getElementById("app");

  function el(tag, attrs, kids) {
    var n = document.createElement(tag);
    for (var k in attrs || {}) {
      var v = attrs[k];
      if (v == null || v === false) continue;
      if (k === "text") n.textContent = v;
      else if (k.slice(0, 2) === "on") n.addEventListener(k.slice(2), v);
      else if (k in n) n[k] = v;
      else n.setAttribute(k, v);
    }
    (kids || []).forEach(function (kid) { if (kid) n.appendChild(typeof kid === "string" ? document.createTextNode(kid) : kid); });
    return n;
  }
  function show(nodes) { app.textContent = ""; nodes.forEach(function (n) { if (n) app.appendChild(n); }); app.focus({ preventScroll: true }); window.scrollTo(0, 0); }

  // ---------------------------------------------------------------- can we run at all?
  var problems = RQM.checkConfig(config);
  if (problems.length) {
    show([el("h2", { text: "Setup needed" }), el("p", { className: "lead-in", text: "config.js has a problem. Fix these and refresh:" }),
      el("ul", {}, problems.map(function (p) { return el("li", { text: p }); }))]);
    return;
  }

  var words = config.words, biz = config.business;
  var full = config.tier === "full" && RQM.full ? RQM.full : null;      // no full.js in the folder = lite
  var demo = !config.webhookUrl;

  // ---------------------------------------------------------------- header, setup notice, footer
  if (full) full.brand(document.getElementById("brand"), config);
  else document.querySelector("#brand .brand-name").textContent = config.trade.productName;
  if (!full) document.title = config.trade.productName + " | Instant ballpark";

  var todo = [];
  if (!config.ratesConfirmed) todo.push("These are example rates, not real prices. Put yours in config.js, then set ratesConfirmed to true.");
  if (demo) todo.push("Demo mode: no webhook set, so leads are not sent anywhere. Add webhookUrl in config.js.");
  if (config.tier === "full" && !RQM.full) todo.push('tier is "full" but full.js is missing, so this is running as lite.');
  if (todo.length) {
    var setup = document.getElementById("setup");
    setup.hidden = false;
    setup.appendChild(el("b", { text: "Setup notice (your customers will see this until it's fixed)" }));
    setup.appendChild(el("ul", {}, todo.map(function (t) { return el("li", { text: t }); })));
  }
  document.getElementById("foot").textContent = "Ballpark prices only. " + biz.name + (biz.licence ? " · Licence " + biz.licence : "");

  // ---------------------------------------------------------------- the flow
  var picks = { type: null, difficulty: null, size: null, suburb: "" };
  var STEPS = [
    { key: "type", ask: words.askType, list: config.jobTypes },
    { key: "difficulty", ask: words.askDifficulty, list: config.difficulty },
    { key: "size", ask: words.askSize, list: config.sizes },
    { key: "suburb", ask: words.askSuburb }
  ];

  function progress(done) {
    return el("div", { className: "steps", role: "img", "aria-label": "Step " + Math.min(done + 1, STEPS.length) + " of " + STEPS.length },
      STEPS.map(function (_, i) { return el("i", { className: i < done ? "done" : "" }); }));
  }
  function backButton(to) { return el("button", { type: "button", className: "back", text: "‹ Back", onclick: to }); }

  function start() {
    show([el("h1", { text: words.headline }), el("p", { className: "lead-in", text: words.subline }),
      el("button", { type: "button", className: "btn", text: "Get my ballpark", onclick: function () { step(0); } })]);
  }

  function step(i) {
    var s = STEPS[i];
    var head = [progress(i), i > 0 ? backButton(function () { step(i - 1); }) : backButton(start), el("h2", { text: s.ask })];
    if (s.list) {
      show(head.concat([el("div", { className: "options" }, s.list.map(function (o) {
        return el("button", { type: "button", className: "option", "aria-pressed": String(picks[s.key] === o.id),
          onclick: function () { picks[s.key] = o.id; step(i + 1); } },
          [el("b", { text: o.label }), o.hint ? el("span", { text: o.hint }) : null]);
      }))]));
      return;
    }
    var input = el("input", { type: "text", id: "suburb", value: picks.suburb, placeholder: words.suburbPlaceholder,
      autocomplete: "address-level2", enterKeyHint: "go", maxLength: 60 });
    var err = el("p", { className: "error", role: "alert", hidden: true, text: "Pop your suburb in so we know where the job is." });
    var form = el("form", { noValidate: true, onsubmit: function (e) {
      e.preventDefault();
      picks.suburb = input.value.trim().replace(/\s+/g, " ");
      if (picks.suburb.length < 2) { err.hidden = false; input.setAttribute("aria-invalid", "true"); input.focus(); return; }
      result();
    } }, [el("label", { className: "field", htmlFor: "suburb" }, ["Suburb", input]), err,
      el("button", { type: "submit", className: "btn", text: "Show my ballpark" })]);
    show(head.concat([form]));
    input.focus();
  }

  // ---------------------------------------------------------------- ballpark + lead form
  function result() {
    var est = RQM.estimate(config, picks);
    var range = RQM.money(est.low) + " – " + RQM.money(est.high);
    var summary = [est.type.label, est.difficulty.label, est.size.label, picks.suburb].join(" · ");

    var f = {};
    function field(key, label, type, auto, mode) {
      f[key] = el("input", { type: type, id: key, autocomplete: auto, inputMode: mode, maxLength: 120 });
      return el("label", { className: "field", htmlFor: key }, [label, f[key]]);
    }
    var trap = el("input", { type: "text", name: "company", tabIndex: -1, autocomplete: "off", className: "trap", "aria-hidden": "true" });
    var err = el("p", { className: "error", role: "alert", hidden: true });
    var send = el("button", { type: "submit", className: "btn", text: words.sendButton });
    var photoBox = full ? full.photos(config) : null;

    function fail(input, message) {
      Object.keys(f).forEach(function (k) { f[k].removeAttribute("aria-invalid"); });
      err.textContent = message; err.hidden = false;
      if (input) { input.setAttribute("aria-invalid", "true"); input.focus(); }
    }

    var form = el("form", { noValidate: true, onsubmit: function (e) {
      e.preventDefault();
      var name = f.name.value.trim(), phone = f.phone.value.trim(), email = f.email.value.trim();
      var digits = phone.replace(/[^\d]/g, "");
      if (name.length < 2) return fail(f.name, "What's your name?");
      if (digits.length < 8 || digits.length > 12 || /[^\d\s()+\-.]/.test(phone)) return fail(f.phone, "That phone number doesn't look right.");
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return fail(f.email, "That email doesn't look right.");
      err.hidden = true;
      send.disabled = true; send.textContent = "Sending…";

      (photoBox ? photoBox.files() : Promise.resolve([])).then(function (files) {
        var lead = {
          name: name, phone: phone, email: email, suburb: picks.suburb,
          job_type: est.type.label, difficulty: est.difficulty.label, size: est.size.label,
          size_min: est.size.min, size_max: est.size.max, unit: config.trade.unit,
          ballpark_low: est.low, ballpark_high: est.high, ballpark: range + " inc GST",
          photos: files.length, business: biz.name, tier: full ? "full" : "lite",
          submitted_at: new Date().toISOString(), page: location.href.split("#")[0]
        };
        if (trap.value) return { bot: true };                 // a bot filled the hidden box: drop it quietly
        return sendLead(lead, files);
      }).then(function (out) { thanks(name, out && out.demo); })
        .catch(function () {
          send.disabled = false; send.textContent = words.sendButton;
          fail(null, "That didn't send. Check your signal and try again" + (biz.phone ? ", or call us on " + biz.phone + "." : "."));
        });
    } }, [
      field("name", "Your name", "text", "name"),
      field("phone", "Mobile", "tel", "tel", "tel"),
      field("email", "Email", "email", "email", "email"),
      trap, photoBox ? photoBox.node : null, err, send,
      el("p", { className: "small", text: "Your details go to " + biz.name + " for this quote only." })
    ]);

    show([progress(STEPS.length), backButton(function () { step(STEPS.length - 1); }),
      el("div", { className: "ballpark" }, [
        el("div", { className: "k", text: words.ballparkTitle + " for your " + config.trade.jobName }),
        el("div", { className: "price" }, [range, el("small", { text: "including GST" })]),
        el("p", { className: "small", text: words.ballparkNote }),
        el("div", { className: "picked" }, [summary + "  ", el("button", { type: "button", text: "Change", onclick: function () { step(0); } })])
      ]),
      el("h2", { text: words.leadTitle }), el("p", { className: "lead-in", text: words.leadSub }), form]);
  }

  /* Post the lead to the webhook as an ordinary form (works with Zapier, Make, n8n and plain servers).
     Every field is sent on its own, plus one "payload" field holding the lot as JSON. Photos go as photo1..photo4. */
  function sendLead(lead, files) {
    if (demo) return Promise.resolve({ demo: true });
    var body = new FormData();
    Object.keys(lead).forEach(function (k) { body.append(k, String(lead[k])); });
    body.append("payload", JSON.stringify(lead));
    files.forEach(function (file, i) { body.append("photo" + (i + 1), file, file.name); });
    var stop = typeof AbortController === "function" ? new AbortController() : null;
    var timer = stop ? setTimeout(function () { stop.abort(); }, 45000) : null;
    return fetch(config.webhookUrl, { method: "POST", body: body, signal: stop ? stop.signal : undefined })
      .then(function (res) { if (timer) clearTimeout(timer); if (!res.ok) throw new Error("webhook said " + res.status); return {}; },
            function (e) { if (timer) clearTimeout(timer); throw e; });
  }

  function thanks(name, wasDemo) {
    var first = name.split(/\s+/)[0];
    show([el("div", { className: "tick", "aria-hidden": "true", text: "✓" }),
      el("h1", { text: wasDemo ? "Demo: nothing sent" : words.thanksTitle }),
      el("p", { className: "lead-in", text: wasDemo ? "The form works, but no webhook is set in config.js, so this lead went nowhere."
        : words.thanksSub + " Cheers, " + first + "." }),
      !wasDemo && biz.phone ? el("p", {}, ["In a hurry? ", el("a", { className: "call", href: "tel:" + biz.phone.replace(/[^\d+]/g, ""), text: "Call " + biz.phone })]) : null,
      el("button", { type: "button", className: "btn btn-outline", text: "Start again", onclick: function () {
        picks = { type: null, difficulty: null, size: null, suburb: "" }; start(); } })]);
  }

  start();
})();
