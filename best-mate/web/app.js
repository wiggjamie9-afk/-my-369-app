// The 48 - AI's Best Mate. Front end: plain ES modules, no build step, no libraries.
// The server does every calculation; this file only shows numbers it was given.
import { mountJarvis } from "/jarvis.js";

// ---------------------------------------------------------------- small helpers
const $ = (sel, root = document) => root.querySelector(sel);

export function h(tag, attrs, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k in el && k !== "list" && k !== "form") el[k] = v;
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const kid of kids.flat(Infinity)) {
    if (kid == null || kid === false) continue;
    el.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
  }
  return el;
}

// replaceChildren/append that accept the same loose children h() does (arrays, null, false)
const tidy = (kids) => kids.flat(Infinity).filter((k) => k != null && k !== false);
const fill = (el, ...kids) => el.replaceChildren(...tidy(kids));
const add = (el, ...kids) => el.append(...tidy(kids));

export const money = (c) => (c < 0 ? "-" : "") + "$" + Math.floor(Math.abs(c) / 100).toLocaleString("en-AU") +
  "." + String(Math.abs(c) % 100).padStart(2, "0");
const qty = (m) => { const w = Math.floor(m / 1000), f = m % 1000; return f ? (w + "." + String(f).padStart(3, "0")).replace(/0+$/, "") : String(w); };
const pct = (bp) => (bp / 100).toFixed(2) + "%";
const plain = (c) => (c / 100).toFixed(2);            // cents -> "12.50" for an input box
const when = (ts) => new Date(ts * 1000).toLocaleDateString("en-AU", { day: "numeric", month: "short" });

let toastTimer;
function toast(msg, bad) {
  const t = $("#toast");
  t.textContent = msg; t.className = "toast" + (bad ? " bad" : ""); t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, bad ? 6000 : 2600);
}

function setOffline(off) {
  $("#offline").hidden = !off;
  $("#net").hidden = !off;
}
addEventListener("online", () => { setOffline(false); render(); });
addEventListener("offline", () => setOffline(true));

// ---------------------------------------------------------------- talking to the server
export async function api(method, path, body, raw) {
  if (method !== "GET" && !navigator.onLine) throw new Error("You're offline. Changes need a connection.");
  const opts = { method, credentials: "same-origin", headers: {} };
  if (raw) { opts.body = raw.body; opts.headers["Content-Type"] = raw.type; }
  else if (body !== undefined) { opts.body = JSON.stringify(body); opts.headers["Content-Type"] = "application/json"; }
  let res;
  try { res = await fetch(path, opts); }
  catch (e) { setOffline(true); throw new Error(method === "GET" ? "You're offline and this isn't saved on the phone yet." : "No connection. Nothing was changed."); }
  if (method === "GET") setOffline(res.headers.get("X-From-Cache") === "1");
  if (raw && raw.blob && res.ok) return res;
  let data = {};
  try { data = await res.json(); } catch (e) { /* not JSON */ }
  if (res.status === 401 && path !== "/api/login") { showLogin(); throw new Error("Sign in to continue."); }
  if (!res.ok) throw new Error(data.error || "That didn't work (" + res.status + ").");
  return data;
}

async function act(fn, done) {            // run a change, show any error as a toast
  try { const out = await fn(); if (done) toast(done); return out; }
  catch (err) { toast(err.message, true); return null; }
}

// ---------------------------------------------------------------- routing
const view = $("#view");
let leave = null;                         // cleanup for the view being left

function go(path) {
  history.pushState(null, "", path);
  render();
}
addEventListener("popstate", render);
document.addEventListener("click", (e) => {
  const a = e.target.closest("a[data-link]");
  if (!a || e.metaKey || e.ctrlKey) return;
  e.preventDefault();
  go(a.getAttribute("href"));
});

const ROUTES = [
  [/^\/$/, quotesView, "quotes"],
  [/^\/new$/, newView, "new"],
  [/^\/voice$/, voiceView, "voice"],
  [/^\/parts$/, partsView, "parts"],
  [/^\/more$/, moreView, "more"],
  [/^\/settings$/, settingsView, "more"],
  [/^\/jarvis$/, jarvisView, "more"],
  [/^\/quote\/(\d+)$/, quoteView, "quotes"],
];

async function render() {
  if (leave) { try { leave(); } catch (e) { /* ignore */ } leave = null; }
  const path = location.pathname;
  const hit = ROUTES.map(([re, fn, tab]) => [path.match(re), fn, tab]).find(([m]) => m);
  const [m, fn, tab] = hit || [[], quotesView, "quotes"];
  document.querySelectorAll("#tabs a").forEach((a) => a.classList.toggle("on", a.dataset.tab === tab));
  const box = h("div");
  fill(view, box);
  scrollTo(0, 0);
  try { leave = (await fn(box, ...m.slice(1))) || null; }
  catch (err) { fill(box, h("div", { class: "empty" }, err.message)); }
}

// ---------------------------------------------------------------- sign in
function showLogin() {
  if ($("#login")) return;
  const pw = h("input", { type: "password", id: "pw", autocomplete: "current-password", placeholder: "Password" });
  const form = h("form", { class: "sheet", id: "login", onsubmit: async (e) => {
    e.preventDefault();
    const ok = await act(() => api("POST", "/api/login", { password: pw.value }));
    if (ok) { dlg.close(); dlg.remove(); render(); }
  } },
    h("img", { src: "/logo-mark.jpg", alt: "", width: 96, height: 96 }),
    h("h3", {}, "Sign in"), h("label", { class: "f" }, "Password", pw),
    h("button", { class: "btn cta wide", type: "submit" }, "Sign in"));
  const dlg = h("dialog", {}, form);
  dlg.addEventListener("cancel", (e) => e.preventDefault());
  document.body.append(dlg);
  dlg.showModal();
}

// ---------------------------------------------------------------- quotes list
const STATE_LABEL = { draft: "Draft", sent: "Sent", won: "Won", lost: "Lost" };

async function quotesView(box) {
  let state = new URLSearchParams(location.search).get("state") || "";
  const list = h("div", { class: "stack" });
  const chips = h("div", { class: "chips" });
  const draw = async () => {
    fill(chips, ...[["", "All"], ...Object.entries(STATE_LABEL)].map(([s, label]) =>
      h("button", { class: "chip", type: "button", "aria-pressed": String(state === s), onclick: () => { state = s; draw(); } }, label)));
    fill(list, h("div", { class: "empty" }, "Loading…"));
    let data;
    try { data = await api("GET", "/api/quotes" + (state ? "?state=" + state : "")); }
    catch (err) { fill(list, h("div", { class: "empty" }, err.message)); return; }
    if (!data.quotes.length) {
      fill(list, h("div", { class: "empty" }, state ? "No " + STATE_LABEL[state].toLowerCase() + " quotes." :
        "No quotes yet. Tap Jane and describe a job, or build one with New."));
      return;
    }
    fill(list, ...data.quotes.map((q) => h("a", { class: "qcard", href: "/quote/" + q.id, "data-link": true },
      h("div", { class: "row spread" }, h("span", { class: "who grow" }, q.customer_name || "No customer yet"),
        h("span", { class: "amt" }, money(q.total_inc_gst_cents))),
      h("div", { class: "small dim" }, q.job_title || "Untitled job"),
      h("div", { class: "row spread", }, h("span", { class: "small dim mono" }, q.number + " · " + when(q.updated_at)),
        h("span", { class: "row" },
          q.flagged_lines ? h("span", { class: "badge bad" }, q.flagged_lines + " unpriced") : null,
          q.state === "draft" && q.placeholder_lines ? h("span", { class: "badge warn" }, "check prices") : null,
          h("span", { class: "badge " + q.state }, STATE_LABEL[q.state]))))));
  };
  add(box, h("h1", {}, "Quotes"), h("p", { class: "sub" }, "Every quote stays a draft until you review and send it."), chips, h("div", { class: "pad" }), list);
  await draw();
}

// ---------------------------------------------------------------- new quote (the form)
const TYPES = [["single_split", "Split system", "One indoor, one outdoor"], ["multi_split", "Multi-split", "Several rooms, one outdoor"],
               ["ducted", "Ducted", "Whole home, zoned"], ["service", "Service", "Clean and check"]];
const SIZES = ["2.5", "3.5", "5.0", "6.0", "7.1", "8.0", "10.0", "12.5", "14.0"];

async function newView(box) {
  const data = await api("GET", "/api/parts?limit=1");
  const settings = (await api("GET", "/api/settings")).settings;
  const brands = data.facets.brands;
  const spec = { install_type: "single_split", brand: settings.preferred_brands[0] || brands[0] || "", cycle: "reverse_cycle",
                 units: [{ kw: "2.5", room: "" }], back_to_back: false, wall_bracket: false };
  const form = h("div", { class: "stack" });
  const cust = { customer_name: "", customer_phone: "", site_address: "" };

  const draw = () => {
    const isService = spec.install_type === "service";
    const single = spec.install_type === "single_split" || spec.install_type === "ducted";
    if (spec.install_type === "ducted" && spec.units.length > 1) spec.units.length = 1;
    const other = !brands.includes(spec.brand);
    fill(form, 
      h("h2", {}, "What kind of job"),
      h("div", { class: "types" }, TYPES.map(([id, name, hint]) => h("button", { class: "type", type: "button",
        "aria-pressed": String(spec.install_type === id), onclick: () => { spec.install_type = id; draw(); } }, h("b", {}, name), h("span", {}, hint)))),

      isService ? null : [h("h2", {}, "Brand"),
        h("div", { class: "chips" }, brands.map((b) => h("button", { class: "chip", type: "button", "aria-pressed": String(spec.brand === b),
          onclick: () => { spec.brand = b; draw(); } }, b)),
          h("button", { class: "chip", type: "button", "aria-pressed": String(other), onclick: () => { spec.brand = ""; draw(); $("#otherBrand").focus(); } }, "Other")),
        other ? h("input", { type: "text", id: "otherBrand", placeholder: "Brand name", value: spec.brand, oninput: (e) => { spec.brand = e.target.value; } }) : null,
        h("h2", {}, "Operation"),
        h("div", { class: "chips" }, [["reverse_cycle", "Reverse cycle"], ["cooling_only", "Cooling only"]].map(([id, name]) =>
          h("button", { class: "chip", type: "button", "aria-pressed": String(spec.cycle === id), onclick: () => { spec.cycle = id; draw(); } }, name)))],

      h("h2", {}, isService ? "Units to service" : spec.install_type === "ducted" ? "System size" : "Indoor units"),
      h("div", { class: "stack" }, spec.units.map((u, i) => h("div", { class: "unit" },
        isService ? h("span", { class: "dim" }, "Unit " + (i + 1)) :
          h("select", { "aria-label": "Capacity of unit " + (i + 1), onchange: (e) => { u.kw = e.target.value; } },
            SIZES.map((s) => h("option", { value: s, selected: u.kw === s }, s + " kW"))),
        h("input", { type: "text", placeholder: "Room (optional)", value: u.room, "aria-label": "Room for unit " + (i + 1), oninput: (e) => { u.room = e.target.value; } }),
        spec.units.length > 1 ? h("button", { class: "btn sm quiet", type: "button", "aria-label": "Remove unit " + (i + 1),
          onclick: () => { spec.units.splice(i, 1); draw(); } }, "Remove") : h("span")))),
      spec.install_type === "ducted" ? null : h("button", { class: "btn line", type: "button",
        onclick: () => { spec.units.push({ kw: "2.5", room: "" }); if (spec.install_type === "single_split" && spec.units.length > 1) spec.install_type = "multi_split"; draw(); } },
        isService ? "Add another unit" : "Add indoor unit"),

      single && spec.install_type === "single_split" ? [h("h2", {}, "Install"),
        h("label", { class: "check" }, h("input", { type: "checkbox", checked: spec.back_to_back, onchange: (e) => { spec.back_to_back = e.target.checked; } }),
          h("span", {}, "Back-to-back", h("div", { class: "small dim" }, "Outdoor unit directly behind the indoor unit"))),
        h("label", { class: "check" }, h("input", { type: "checkbox", checked: spec.wall_bracket, onchange: (e) => { spec.wall_bracket = e.target.checked; } }),
          h("span", {}, "Wall bracket", h("div", { class: "small dim" }, "Mount the outdoor unit on brackets instead of a slab")))] : null,

      h("h2", {}, "Customer"),
      h("label", { class: "f" }, "Name", h("input", { type: "text", value: cust.customer_name, autocomplete: "off", oninput: (e) => { cust.customer_name = e.target.value; } })),
      h("label", { class: "f" }, "Phone", h("input", { type: "tel", value: cust.customer_phone, oninput: (e) => { cust.customer_phone = e.target.value; } })),
      h("label", { class: "f" }, "Site address", h("input", { type: "text", value: cust.site_address, oninput: (e) => { cust.site_address = e.target.value; } })),
      h("div", { class: "actions" }, h("button", { class: "btn cta wide", type: "button", onclick: async () => {
        const body = { ...cust, spec: { ...spec, units: spec.units.map((u) => ({ kw: isService ? "0" : u.kw, room: u.room })) } };
        const out = await act(() => api("POST", "/api/quotes", body));
        if (out) go("/quote/" + out.quote.id);
      } }, "Build the draft")));
  };
  add(box, h("h1", {}, "New quote"), h("p", { class: "sub" }, "Pick the job. The parts and prices come from your library."), form);
  draw();
}

// ---------------------------------------------------------------- Jane (voice to quote)
async function voiceView(box) {
  const modes = (await api("GET", "/api/settings")).modes;
  const text = h("textarea", { id: "job", placeholder: "e.g. two and a half kW Daikin split, back-to-back install, Smith job", "aria-label": "Job description" });
  const said = h("div", { class: "said" }, "Tap the mic and describe the job.");
  const mic = h("button", { class: "mic", type: "button", "aria-label": "Start listening" }, h("i", { class: "ico v" }));
  let recorder = null, stream = null, chunks = [];

  const stop = () => { if (stream) stream.getTracks().forEach((t) => t.stop()); stream = null; recorder = null; mic.classList.remove("live"); mic.setAttribute("aria-label", "Start listening"); };
  mic.addEventListener("click", async () => {
    if (recorder) { recorder.stop(); return; }
    if (!navigator.mediaDevices || !window.MediaRecorder) { said.textContent = "This browser can't record. Type the job below instead."; return; }
    try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); }
    catch (e) { said.textContent = "The microphone is blocked. Type the job below instead."; return; }
    chunks = [];
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = (e) => { if (e.data.size) chunks.push(e.data); };
    recorder.onstop = async () => {
      const type = recorder.mimeType || "audio/mp4";
      stop();
      said.textContent = "Jane is listening back…";
      const out = await act(() => api("POST", "/api/voice/listen", undefined, { body: new Blob(chunks, { type }), type }));
      if (!out) { said.textContent = "Jane couldn't hear that. Type the job below instead."; return; }
      text.value = out.text;
      said.textContent = out.stub ? "Sample sentence only: Jane's ears aren't connected yet. Edit it to match the job." : "Check Jane heard you right, then draft.";
    };
    recorder.start();
    mic.classList.add("live"); mic.setAttribute("aria-label", "Stop listening");
    said.textContent = "Listening… tap again when you're done.";
  });

  const draftBtn = h("button", { class: "btn cta wide", type: "button", onclick: async () => {
    if (!text.value.trim()) { toast("Describe the job first.", true); return; }
    draftBtn.disabled = true;
    const out = await act(() => api("POST", "/api/ai/draft-quote", { job_description: text.value, create: true, via: "voice" }));
    draftBtn.disabled = false;
    if (!out) return;
    const todo = out.line_items.filter((l) => l.flagged).length;
    speak("Drafted a quote" + (out.customer_name ? " for " + out.customer_name : "") + ". " +
      (todo ? todo + " item" + (todo === 1 ? " needs" : "s need") + " a price from you." : "Have a look, then review and send."));
    go("/quote/" + out.quote_id);
  } }, "Draft the quote");

  add(box, h("h1", {}, "Jane"), h("p", { class: "sub" }, "Say the job. Jane drafts it; you set the price."),
    h("div", { class: "jane-stage" }, mic, said),
    modes.voice === "stub" ? h("div", { class: "warn-box small" }, "Jane's voice server isn't connected yet, so the mic returns a sample sentence and she answers with a chime. Typing the job works now.") : null,
    h("h2", {}, "The job"), text, h("div", { class: "actions" }, draftBtn),
    h("p", { class: "small dim" }, "Drafting: " + (modes.ai === "model" ? "your AI model reads the job, then every item and price is checked against your parts library." :
      "built-in reader. Prices only ever come from your parts library.")));
  return stop;
}

async function speak(textToSay) {
  try {
    const res = await api("POST", "/api/voice/speak", { text: textToSay }, { body: JSON.stringify({ text: textToSay }), type: "application/json", blob: true });
    const audio = new Audio(URL.createObjectURL(await res.blob()));
    audio.play().catch(() => {});
  } catch (e) { /* voice is a nicety: never block the quote on it */ }
}

// ---------------------------------------------------------------- one quote
function partPicker(onPick) {
  const input = h("input", { type: "search", placeholder: "Search parts", "aria-label": "Search parts" });
  const results = h("div");
  const dlg = h("dialog", {}, h("div", { class: "sheet" }, h("div", { class: "row spread" }, h("h3", {}, "Pick a part"),
    h("button", { class: "btn sm quiet", type: "button", onclick: () => dlg.close() }, "Close")), input, results));
  let timer;
  const search = async () => {
    let data;
    try { data = await api("GET", "/api/parts?limit=30&q=" + encodeURIComponent(input.value)); }
    catch (err) { fill(results, h("div", { class: "empty" }, err.message)); return; }
    fill(results, ...(data.items.length ? data.items.map((p) => h("button", { class: "pick", type: "button",
      onclick: () => { dlg.close(); onPick(p); } },
      h("div", { class: "row spread" }, h("span", { class: "grow" }, p.name), h("span", { class: "mono" }, money(p.unit_sell_cents))),
      h("div", { class: "small dim mono" }, p.sku + " · per " + p.unit + (p.price_status === "placeholder" ? " · placeholder price" : "")))) :
      [h("div", { class: "empty" }, "Nothing in the library matches.")]));
  };
  input.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(search, 220); });
  dlg.addEventListener("close", () => dlg.remove());
  document.body.append(dlg);
  dlg.showModal();
  search();
}

async function quoteView(box, id) {
  let q = (await api("GET", "/api/quotes/" + id)).quote;
  let open = null;                                   // id of the line being edited
  const change = async (fn, done) => { const out = await act(fn, done); if (out && out.quote) { q = out.quote; draw(); } return out; };
  const put = (body) => change(() => api("PUT", "/api/quotes/" + id, body));
  const field = (label, key, type = "text") => h("label", { class: "f" }, label,
    h("input", { type, value: q[key], disabled: q.state !== "draft", onchange: (e) => put({ [key]: e.target.value }) }));

  function lineRow(ln) {
    const editable = q.state === "draft";
    const amount = ln.flagged ? "no price" : money(Math.round(ln.unit_sell_cents * ln.qty_milli / 1000));
    const head = h("div", { class: "row spread" },
      h("div", { class: "grow" }, h("div", { class: "d" }, ln.description),
        h("div", { class: "small dim mono" }, qty(ln.qty_milli) + " " + ln.unit + (ln.flagged ? "" : " × " + money(ln.unit_sell_cents)),
          ln.price_status === "placeholder" && q.state === "draft" ? h("span", { class: "badge warn" }, "check price") : null,
          ln.price_status === "manual" ? h("span", { class: "badge" }, "your price") : null)),
      h("div", { class: "a" }, amount));
    const row = h("div", { class: "line" + (ln.flagged ? " flag" : "") }, head);
    if (ln.flagged) add(row, h("div", { class: "why" }, ln.flag_reason));
    if (!editable) return row;

    if (open !== ln.id && !ln.flagged) {
      head.style.cursor = "pointer";
      head.addEventListener("click", () => { open = ln.id; draw(); });
      return row;
    }
    const qIn = h("input", { inputmode: "decimal", value: qty(ln.qty_milli), "aria-label": "Quantity" });
    const cIn = h("input", { inputmode: "decimal", value: ln.unit_cost_cents == null ? "" : plain(ln.unit_cost_cents), placeholder: "0.00", "aria-label": "Your cost each" });
    const sIn = h("input", { inputmode: "decimal", value: ln.unit_sell_cents == null ? "" : plain(ln.unit_sell_cents), placeholder: "0.00", "aria-label": "Your price each" });
    add(row, h("div", { class: "edit" },
      h("div", { class: "two" }, h("label", { class: "f" }, "Quantity (" + ln.unit + ")", qIn), h("span")),
      h("div", { class: "two" }, h("label", { class: "f" }, "Your cost each, ex GST", cIn), h("label", { class: "f" }, "Your price each, ex GST", sIn)),
      h("div", { class: "row" },
        h("button", { class: "btn sm cta", type: "button", onclick: async () => {
          const body = { qty: qIn.value };
          const priced = sIn.value.trim() !== "" || cIn.value.trim() !== "";
          const changed = ln.flagged || sIn.value !== (ln.unit_sell_cents == null ? "" : plain(ln.unit_sell_cents)) || cIn.value !== (ln.unit_cost_cents == null ? "" : plain(ln.unit_cost_cents));
          if (priced && changed) { body.unit_sell = sIn.value; body.unit_cost = cIn.value; }
          else if (ln.flagged) { toast("Pick a part, or enter your cost and price.", true); return; }
          open = null;
          await change(() => api("PUT", "/api/quotes/" + id + "/lines/" + ln.id, body), "Saved");
        } }, "Save"),
        h("button", { class: "btn sm line", type: "button", onclick: () => partPicker((p) =>
          change(() => api("PUT", "/api/quotes/" + id + "/lines/" + ln.id, { sku: p.sku, qty: qIn.value }), "Part swapped in")) }, "Pick a part"),
        h("button", { class: "btn sm danger", type: "button", onclick: () => change(() => api("DELETE", "/api/quotes/" + id + "/lines/" + ln.id), "Removed") }, "Remove"),
        ln.flagged ? null : h("button", { class: "btn sm quiet", type: "button", onclick: () => { open = null; draw(); } }, "Cancel"))));
    return row;
  }

  function customItem() {
    const d = h("input", { type: "text", placeholder: "What is it?", "aria-label": "Item description" });
    const n = h("input", { inputmode: "decimal", value: "1", "aria-label": "Quantity" });
    const c = h("input", { inputmode: "decimal", placeholder: "0.00", "aria-label": "Your cost each" });
    const s = h("input", { inputmode: "decimal", placeholder: "0.00", "aria-label": "Your price each" });
    const dlg = h("dialog", {}, h("div", { class: "sheet" }, h("h3", {}, "Add your own item"),
      h("label", { class: "f" }, "Description", d), h("label", { class: "f" }, "Quantity", n),
      h("div", { class: "two" }, h("label", { class: "f" }, "Your cost each, ex GST", c), h("label", { class: "f" }, "Your price each, ex GST", s)),
      h("button", { class: "btn cta wide", type: "button", onclick: async () => {
        const out = await change(() => api("POST", "/api/quotes/" + id + "/lines", { description: d.value, qty: n.value, unit_cost: c.value, unit_sell: s.value }), "Added");
        if (out) dlg.close();
      } }, "Add to quote"),
      h("button", { class: "btn quiet wide", type: "button", onclick: () => dlg.close() }, "Cancel")));
    dlg.addEventListener("close", () => dlg.remove());
    document.body.append(dlg); dlg.showModal();
  }

  function review() {
    const t = q.totals;
    const blockers = [];
    if (t.unpriced_lines) blockers.push(t.unpriced_lines + " line" + (t.unpriced_lines === 1 ? " has" : "s have") + " no price. Pick a part or set a price.");
    if (q.flags.length) blockers.push("Read and clear the " + q.flags.length + " drafting warning" + (q.flags.length === 1 ? "" : "s") + ".");
    if (!q.customer_name.trim()) blockers.push("Add the customer's name.");
    if (!q.lines.length && !q.labour_hours_milli) blockers.push("The quote is empty.");
    const a = h("input", { type: "checkbox" }), b = h("input", { type: "checkbox" });
    const send = h("button", { class: "btn cta wide", type: "button", disabled: true }, "Send quote");
    const sync = () => { send.disabled = blockers.length > 0 || !a.checked || (q.placeholder_lines > 0 && !b.checked); };
    a.addEventListener("change", sync); b.addEventListener("change", sync);
    send.addEventListener("click", async () => {
      const out = await change(() => api("POST", "/api/quotes/" + id + "/send", { reviewed: true, prices_checked: b.checked }), "Sent. The PDF is ready.");
      if (out) dlg.close();
    });
    const dlg = h("dialog", {}, h("div", { class: "sheet" },
      h("h3", {}, "Review and send"),
      h("div", { class: "card" }, h("div", { class: "small dim" }, (q.customer_name || "No customer") + " · " + q.number),
        h("div", { class: "total" }, h("span", { class: "dim" }, "Total inc GST"), h("span", { class: "big" }, money(t.total_inc_gst_cents))),
        h("div", { class: "small dim mono" }, money(t.total_ex_gst_cents) + " ex GST + " + money(t.gst_cents) + " GST · margin " + pct(t.margin_bp))),
      blockers.length ? h("div", { class: "warn-box" }, h("b", {}, "Fix these first"), h("ul", {}, blockers.map((x) => h("li", {}, x)))) : null,
      h("label", { class: "check" }, a, h("span", {}, "I've checked every line and the total. This is my price.")),
      q.placeholder_lines ? h("label", { class: "check" }, b, h("span", {}, q.placeholder_lines + " line" + (q.placeholder_lines === 1 ? " uses a" : "s use") +
        " placeholder price" + (q.placeholder_lines === 1 ? "" : "s") + ", not from a supplier list. I've checked " + (q.placeholder_lines === 1 ? "it" : "them") + ".")) : null,
      send, h("button", { class: "btn quiet wide", type: "button", onclick: () => dlg.close() }, "Back to the quote")));
    dlg.addEventListener("close", () => dlg.remove());
    document.body.append(dlg); dlg.showModal();
  }

  function draw() {
    const t = q.totals, draft = q.state === "draft";
    const parts = t.external_cost_cents + t.labour_cost_cents + Math.max(t.net_profit_cents, 0) || 1;
    const seg = (cls, cents) => { const i = h("i", { class: cls }); i.style.width = (Math.max(cents, 0) / parts * 100) + "%"; return i; };
    const key = (colour, label, cents) => { const s = h("span", {}, label); s.style.setProperty("--k", colour); return h("div", { class: "row spread" }, s, h("span", { class: "mono" }, money(cents))); };
    const adj = h("input", { inputmode: "decimal", value: plain(q.adjust_cents), disabled: !draft, "aria-label": "Adjust the price", onchange: (e) => put({ adjust: e.target.value || "0" }) });
    const hours = h("input", { inputmode: "decimal", value: qty(q.labour_hours_milli), disabled: !draft, "aria-label": "Labour hours", onchange: (e) => put({ labour_hours: e.target.value || "0" }) });
    const pdf = (label, cls) => h("a", { class: "btn " + cls, href: "/api/quotes/" + id + "/pdf", download: "" }, label);

    fill(box, 
      h("div", { class: "row spread" }, h("a", { href: "/", "data-link": true, class: "small" }, "‹ Quotes"),
        h("span", { class: "row" }, q.source === "voice" || q.source === "ai" ? h("span", { class: "badge" }, "drafted by Jane") : null,
          h("span", { class: "badge " + q.state }, STATE_LABEL[q.state]))),
      h("h1", {}, q.customer_name || "New quote"),
      h("p", { class: "sub mono" }, q.number + (q.sent_at ? " · sent " + when(q.sent_at) : " · not sent")),

      h("div", { class: "card" }, h("div", { class: "total" }, h("span", { class: "dim" }, "Total inc GST"), h("span", { class: "big" }, money(t.total_inc_gst_cents))),
        h("div", { class: "small dim mono" }, money(t.total_ex_gst_cents) + " ex GST + " + money(t.gst_cents) + " GST")),

      q.flags.length ? [h("h2", {}, "Drafting warnings"), h("div", { class: "warn-box" }, h("b", {}, "Jane wasn't sure about these"),
        h("ul", {}, q.flags.map((f) => h("li", {}, f))),
        draft ? h("button", { class: "btn sm", type: "button", onclick: () => change(() => api("DELETE", "/api/quotes/" + id + "/flags"), "Cleared") }, "I've read these") : null)] : null,

      h("h2", {}, "Customer"),
      h("div", { class: "stack" }, field("Name", "customer_name"), h("div", { class: "two" }, field("Phone", "customer_phone", "tel"), field("Email", "customer_email", "email")),
        field("Site address", "site_address")),

      h("h2", {}, "Job"),
      h("div", { class: "stack" }, field("Title", "job_title"),
        h("label", { class: "f" }, "Scope of works", h("textarea", { value: q.scope, disabled: !draft, onchange: (e) => put({ scope: e.target.value }) })),
        h("label", { class: "f" }, "Notes for the customer", h("textarea", { value: q.notes, disabled: !draft, onchange: (e) => put({ notes: e.target.value }) }))),

      h("h2", {}, "Parts and materials"),
      h("div", { class: "card" }, q.lines.length ? q.lines.map(lineRow) : h("div", { class: "empty" }, "No items yet.")),
      draft ? h("div", { class: "two pad0" }, h("button", { class: "btn line", type: "button", onclick: () => partPicker((p) =>
        change(() => api("POST", "/api/quotes/" + id + "/lines", { sku: p.sku, qty: "1" }), "Added")) }, "Add a part"),
        h("button", { class: "btn", type: "button", onclick: customItem }, "Add your own")) : null,

      h("h2", {}, "Labour"),
      h("div", { class: "card stack" }, h("div", { class: "two" }, h("label", { class: "f" }, "Hours", hours),
        h("div", { class: "f" }, "Charged at", h("div", { class: "mono" }, money(q.labour_sell_rate_cents) + " / hr"))),
        h("div", { class: "row spread small" }, h("span", { class: "dim" }, "Labour on this quote"), h("span", { class: "mono" }, money(t.labour_sell_cents)))),

      h("h2", {}, "Your margin"),
      h("div", { class: "card" },
        h("div", { class: "total" }, h("span", { class: "dim" }, "Net profit"), h("span", { class: "big" }, money(t.net_profit_cents))),
        h("div", { class: "small dim mono" }, pct(t.margin_bp) + " margin on " + money(t.total_ex_gst_cents) + " ex GST"),
        h("div", { class: "pad0" }), h("div", { class: "bar", role: "img", "aria-label": "Costs and profit" },
          seg("x", t.external_cost_cents), seg("l", t.labour_cost_cents), seg("p", t.net_profit_cents)),
        h("div", { class: "legend" }, key("var(--blue)", "Parts and materials cost", t.external_cost_cents),
          key("#7F8DA6", "Your labour cost", t.labour_cost_cents), key("var(--cyan)", "Net profit", t.net_profit_cents)),
        h("div", { class: "pad0" }), h("label", { class: "f" }, "Adjust the price, ex GST (use a minus to discount)", adj)),

      h("h2", {}, "Totals"),
      h("div", { class: "card sums" },
        h("div", { class: "row spread" }, h("span", { class: "dim" }, "Parts and materials"), h("span", { class: "mono" }, money(t.materials_sell_cents))),
        h("div", { class: "row spread" }, h("span", { class: "dim" }, "Labour"), h("span", { class: "mono" }, money(t.labour_sell_cents))),
        t.adjust_cents ? h("div", { class: "row spread" }, h("span", { class: "dim" }, "Adjustment"), h("span", { class: "mono" }, money(t.adjust_cents))) : null,
        h("div", { class: "row spread" }, h("span", { class: "dim" }, "Subtotal ex GST"), h("span", { class: "mono" }, money(t.total_ex_gst_cents))),
        h("div", { class: "row spread" }, h("span", { class: "dim" }, "GST 10%"), h("span", { class: "mono" }, money(t.gst_cents))),
        h("div", { class: "row spread" }, h("span", {}, "Total inc GST"), h("b", {}, money(t.total_inc_gst_cents)))),

      h("div", { class: "actions" },
        draft ? [h("button", { class: "btn cta wide", type: "button", onclick: review }, "Review and send"), pdf("Preview PDF (marked DRAFT)", "line"),
          h("button", { class: "btn danger", type: "button", onclick: async () => {
            const dlg = h("dialog", {}, h("div", { class: "sheet" }, h("h3", {}, "Delete this draft?"), h("p", { class: "dim" }, "This can't be undone."),
              h("button", { class: "btn danger wide", type: "button", onclick: async () => { const ok = await act(() => api("DELETE", "/api/quotes/" + id)); dlg.close(); if (ok) go("/"); } }, "Delete draft"),
              h("button", { class: "btn quiet wide", type: "button", onclick: () => dlg.close() }, "Keep it")));
            dlg.addEventListener("close", () => dlg.remove()); document.body.append(dlg); dlg.showModal();
          } }, "Delete draft")]
          : [pdf("Download PDF", "cta wide"),
            q.state === "sent" ? h("button", { class: "btn line", type: "button", onclick: () => change(() => api("POST", "/api/quotes/" + id + "/state", { state: "won" }), "Marked won") }, "Mark as won") : null,
            q.state === "sent" ? h("button", { class: "btn", type: "button", onclick: () => change(() => api("POST", "/api/quotes/" + id + "/state", { state: "lost" }), "Marked lost") }, "Mark as lost") : null,
            h("button", { class: "btn quiet", type: "button", onclick: () => change(() => api("POST", "/api/quotes/" + id + "/state", { state: "draft" }), "Reopened as a draft") }, "Reopen as a draft")]));
  }
  draw();
}

// ---------------------------------------------------------------- parts library
async function partsView(box) {
  const list = h("div", { class: "card" });
  const search = h("input", { type: "search", placeholder: "Search 2.5kW, isolator, SKU…", "aria-label": "Search parts" });
  const cat = h("select", { "aria-label": "Category" });
  const note = h("div");
  let offset = 0, timer;
  const load = async (more) => {
    offset = more ? offset + 50 : 0;
    let data;
    try { data = await api("GET", "/api/parts?limit=50&offset=" + offset + "&q=" + encodeURIComponent(search.value) + "&category=" + encodeURIComponent(cat.value)); }
    catch (err) { fill(list, h("div", { class: "empty" }, err.message)); return; }
    if (!cat.options.length) fill(cat, h("option", { value: "" }, "All categories"), ...data.facets.categories.map((c) => h("option", { value: c }, c)));
    fill(note, data.facets.placeholder ? h("div", { class: "warn-box small" }, h("b", {}, data.facets.placeholder + " of " + data.facets.count + " prices are placeholders."),
      " They are stand-ins, not supplier prices. Import your supplier list below to replace them.") : h("p", { class: "small dim" }, data.facets.count.toLocaleString("en-AU") + " parts, all priced from your lists."));
    const rows = data.items.map((p) => h("div", { class: "line" }, h("div", { class: "row spread" },
      h("div", { class: "grow" }, h("div", { class: "d" }, p.name), h("div", { class: "small dim mono" }, p.sku + " · " + (p.vendor || "no vendor") +
        (p.price_status === "placeholder" ? " · " : ""), p.price_status === "placeholder" ? h("span", { class: "badge warn" }, "placeholder") : null)),
      h("div", { class: "right" }, h("div", { class: "a mono" }, money(p.unit_sell_cents)), h("div", { class: "small dim mono" }, "cost " + money(p.unit_cost_cents) + " / " + p.unit)))));
    if (!more) fill(list, );
    else list.querySelector(".more")?.remove();
    add(list, ...(rows.length || more ? rows : [h("div", { class: "empty" }, "Nothing matches.")]));
    if (offset + data.items.length < data.total) add(list, h("button", { class: "btn quiet wide more", type: "button", onclick: () => load(true) }, "Show more (" + (data.total - offset - data.items.length) + ")"));
  };
  search.addEventListener("input", () => { clearTimeout(timer); timer = setTimeout(() => load(false), 220); });
  cat.addEventListener("change", () => load(false));

  const f = {};
  const inp = (key, label, extra = {}) => h("label", { class: "f" }, label, f[key] = h("input", { type: "text", ...extra }));
  const file = h("input", { type: "file", accept: ".csv,text/csv", "aria-label": "Supplier price list CSV" });
  add(box, h("h1", {}, "Parts"), h("p", { class: "sub" }, "Your priced library. Sell price is your cost, less vendor discount, plus your markup."),
    note, h("div", { class: "pad0" }), h("div", { class: "stack" }, search, cat), h("div", { class: "pad0" }), list,
    h("h2", {}, "Import a supplier price list"),
    h("div", { class: "card stack" }, h("p", { class: "small dim" }, "CSV with a header row. Needs sku, name, cost. Optional: category, brand, vendor, unit, kw. Existing SKUs are updated."),
      file, h("button", { class: "btn line", type: "button", onclick: async () => {
        if (!file.files[0]) { toast("Choose a CSV file first.", true); return; }
        const out = await act(async () => api("POST", "/api/parts/import", undefined, { body: await file.files[0].text(), type: "text/csv" }));
        if (out) { toast("Imported " + out.imported + " parts."); file.value = ""; load(false); }
      } }, "Import")),
    h("h2", {}, "Add one part"),
    h("div", { class: "card stack" }, inp("sku", "SKU"), inp("name", "Name"), h("div", { class: "two" }, inp("cost", "Your list cost, ex GST", { inputmode: "decimal", placeholder: "0.00" }), inp("unit", "Unit", { placeholder: "ea" })),
      h("div", { class: "two" }, inp("category", "Category"), inp("brand", "Brand")), h("div", { class: "two" }, inp("vendor", "Vendor"), inp("kw", "kW (units only)", { inputmode: "decimal" })),
      h("button", { class: "btn line", type: "button", onclick: async () => {
        const out = await act(() => api("POST", "/api/parts", Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value]))));
        if (out) { toast("Saved " + out.sku + "."); Object.values(f).forEach((el) => { el.value = ""; }); load(false); }
      } }, "Save part")));
  await load(false);
}

// ---------------------------------------------------------------- settings
async function settingsView(box) {
  let data = await api("GET", "/api/settings");
  const draw = () => {
    const s = data.settings, f = {};
    const inp = (key, label, value, extra = {}) => h("label", { class: "f" }, label, f[key] = h("input", { type: "text", value, ...extra }));
    const terms = h("textarea", { value: s.payment_terms });
    fill(box, h("a", { href: "/more", "data-link": true, class: "small" }, "‹ More"), h("h1", {}, "Settings"),
      h("p", { class: "sub" }, "Set these once. They feed every quote and the PDF header."),
      h("h2", {}, "Your business (PDF header)"),
      h("div", { class: "stack" }, inp("business_name", "Business name", s.business_name), h("div", { class: "two" }, inp("business_abn", "ABN", s.business_abn), inp("business_licence", "Licence number", s.business_licence)),
        h("div", { class: "two" }, inp("business_phone", "Phone", s.business_phone, { type: "tel" }), inp("business_email", "Email", s.business_email, { type: "email" })),
        inp("business_address", "Address", s.business_address)),
      h("h2", {}, "Pricing"),
      h("div", { class: "stack" }, inp("markup_percent", "Markup on parts and materials (%)", (s.markup_bp / 100).toString(), { inputmode: "decimal" }),
        h("div", { class: "two" }, inp("labour_cost_rate", "What an hour costs you ($)", plain(s.labour_cost_rate_cents), { inputmode: "decimal" }),
          inp("labour_sell_rate", "What you charge an hour, ex GST ($)", plain(s.labour_sell_rate_cents), { inputmode: "decimal" })),
        inp("preferred_brands", "Preferred brands, in order (comma separated)", s.preferred_brands.join(", "))),
      h("h2", {}, "Quote terms"),
      h("div", { class: "stack" }, inp("valid_days", "Quote valid for (days)", String(s.valid_days), { inputmode: "numeric" }), h("label", { class: "f" }, "Payment terms", terms)),
      h("div", { class: "actions" }, h("button", { class: "btn cta wide", type: "button", onclick: async () => {
        const body = Object.fromEntries(Object.entries(f).map(([k, el]) => [k, el.value]));
        body.valid_days = parseInt(body.valid_days, 10) || 0;
        body.payment_terms = terms.value;
        const out = await act(() => api("PUT", "/api/settings", body), "Saved. New quotes use these.");
        if (out) { data = out; draw(); }
      } }, "Save settings")),
      h("h2", {}, "Vendor discounts"),
      h("div", { class: "card stack" }, h("p", { class: "small dim" }, "The discount you get off each vendor's list price. Applied to new quote lines."),
        data.vendors.map((v) => { const d = h("input", { inputmode: "decimal", value: (v.discount_bp / 100).toString(), "aria-label": "Discount percent for " + v.name });
          return h("div", { class: "row" }, h("span", { class: "grow" }, v.name), h("span", { class: "row" }, d, h("span", { class: "dim" }, "%")),
            h("button", { class: "btn sm line", type: "button", onclick: async () => { const out = await act(() => api("PUT", "/api/vendors", { name: v.name, discount_percent: d.value }), "Saved"); if (out) { data.vendors = out.vendors; draw(); } } }, "Save")); }),
        (() => { const n = h("input", { type: "text", placeholder: "New vendor name", "aria-label": "New vendor name" });
          return h("div", { class: "row" }, h("span", { class: "grow" }, n), h("button", { class: "btn sm", type: "button", onclick: async () => {
            const out = await act(() => api("PUT", "/api/vendors", { name: n.value, discount_percent: "0" }), "Added"); if (out) { data.vendors = out.vendors; draw(); } } }, "Add vendor")); })()));
  };
  draw();
}

// ---------------------------------------------------------------- more, jarvis
async function moreView(box) {
  const session = await api("GET", "/api/session");
  const link = (href, title, hint) => h("a", { class: "qcard", href, "data-link": true }, h("div", { class: "who" }, title), h("div", { class: "small dim" }, hint));
  add(box, h("h1", {}, "More"), h("div", { class: "pad0" }), h("div", { class: "stack" },
    link("/jarvis", "Jarvis", "Job pipeline, quote states and system health"),
    link("/settings", "Settings", "Business details, markup, labour rates, vendor discounts"),
    session.auth_required ? h("button", { class: "btn danger", type: "button", onclick: async () => {
      await act(() => api("POST", "/api/logout"));
      if (window.caches) await caches.delete("bm-data-v1");        // don't leave quotes on a signed-out phone
      showLogin();
    } }, "Sign out") : null));
}

async function jarvisView(box) {
  return mountJarvis(box, { api, go, money, h });
}

// ---------------------------------------------------------------- start
if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});
setOffline(!navigator.onLine);
render();
