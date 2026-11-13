// The Jarvis panel: job pipeline, quote states and a system health strip.
//
// MODULE BOUNDARY. This file is the only thing behind the /jarvis route. To graft the existing
// JARVIS console in, replace the body of mountJarvis() (or just fill the #jarvis-graft element it
// leaves at the bottom). Everything it needs arrives through the `host` argument:
//   host.api(method, path, body)   same-origin JSON calls (GET /api/jarvis/summary is the feed)
//   host.go(path)                  in-app navigation
//   host.money(cents), host.h      formatting and the element helper
// It returns a function that stops its refresh timer when the view is left.

export async function mountJarvis(root, host) {
  const { h, money } = host;
  const body = h("div", { class: "stack" }, h("div", { class: "empty" }, "Loading the pipeline…"));
  root.append(
    h("h1", {}, "Jarvis"),
    h("p", { class: "sub" }, "Where every job stands, and whether the system is healthy."),
    body,
    h("h2", {}, "Console"),
    h("div", { class: "graft", id: "jarvis-graft" },
      "The full JARVIS command console plugs in here. Until it is grafted, this panel shows the pipeline and health above.")
  );

  const LABEL = { draft: "Draft", sent: "Sent", won: "Won", lost: "Lost" };
  const ago = (ts) => {
    const s = Math.max(0, Math.round(Date.now() / 1000 - ts));
    return s < 90 ? "just now" : s < 5400 ? Math.round(s / 60) + " min ago" : s < 172800 ? Math.round(s / 3600) + " h ago" : Math.round(s / 86400) + " d ago";
  };

  async function draw() {
    let data;
    try { data = await host.api("GET", "/api/jarvis/summary"); }
    catch (err) { body.replaceChildren(h("div", { class: "empty" }, err.message)); return; }
    const p = data.pipeline, hl = data.health;
    const tiles = h("div", { class: "pipe" }, Object.keys(LABEL).map((s) =>
      h("a", { class: "card", href: "/?state=" + s, "data-link": true },
        h("span", { class: "badge " + s }, LABEL[s]), h("b", {}, String(p.states[s].count)),
        h("span", { class: "small dim mono" }, money(p.states[s].total_inc_gst_cents)))));

    const win = p.win_rate_bp === null ? "No jobs closed yet" : "Win rate " + (p.win_rate_bp / 100).toFixed(0) + "% of closed quotes";
    const attention = p.needs_attention.length
      ? h("div", { class: "stack" }, p.needs_attention.map((q) =>
          h("a", { class: "qcard", href: "/quote/" + q.id, "data-link": true },
            h("div", { class: "row spread" }, h("span", { class: "who" }, q.customer_name || "No customer yet"),
              h("span", { class: "badge " + (q.flagged_lines ? "bad" : "warn") },
                q.flagged_lines ? q.flagged_lines + " unpriced" : q.placeholder_lines + " to check")),
            h("div", { class: "small dim" }, q.number + " · " + (q.job_title || "Untitled job")))))
      : h("div", { class: "empty" }, "Nothing is waiting on you.");

    const recent = p.recent.length
      ? h("div", { class: "card stack" }, p.recent.map((e) =>
          h("div", { class: "row spread small" },
            h("span", {}, (e.number || "Quote") + " " + ({ created: "drafted", sent: "sent", won: "won", lost: "lost", draft: "reopened" }[e.kind] || e.kind) +
              (e.customer_name ? " · " + e.customer_name : "")),
            h("span", { class: "dim mono" }, ago(e.ts)))))
      : h("div", { class: "empty" }, "No activity yet.");

    const light = (ok) => { const d = h("span", { class: "dot" }); if (!ok) d.style.setProperty("--k", "var(--orange)"); return d; };
    const cell = (name, value, ok = true) => h("div", {}, h("b", {}, name), light(ok), value);
    const health = h("div", { class: "health" },
      cell("Database", hl.database),
      cell("Parts", hl.parts.toLocaleString("en-AU") + " in library"),
      cell("Prices", hl.placeholder_prices ? hl.placeholder_prices + " placeholders" : "all from suppliers", !hl.placeholder_prices),
      cell("Jane's voice", hl.voice === "live" ? "connected" : "stub, not connected", hl.voice === "live"),
      cell("Drafting", hl.ai === "model" ? "AI model" : "built-in reader"),
      cell("Sign-in", hl.auth ? "on" : "off", hl.auth),
      cell("Version", hl.version),
      cell("Up for", ago(Date.now() / 1000 - hl.uptime_s).replace(" ago", "").replace("just now", "under 2 min")));

    body.replaceChildren(
      h("h2", {}, "Pipeline"), tiles, h("p", { class: "small dim" }, win),
      h("h2", {}, "Needs your eye"), attention,
      h("h2", {}, "Recent"), recent,
      h("h2", {}, "System health"), health);
  }

  await draw();
  const timer = setInterval(() => { if (!document.hidden) draw(); }, 20000);
  return () => clearInterval(timer);
}
