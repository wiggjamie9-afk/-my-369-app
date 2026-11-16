#!/usr/bin/env python3
"""Swarm 1001 - check a business idea, app or product from every angle before you commit.

1,000 simulated customers (or business owners)  +  1 judge  =  1,001 nodes, plus:
  - a control check (a deliberately bad offer) to catch an over-agreeable panel,
  - the money maths (plain arithmetic in whole cents, no AI),
  - five specialist reviewers: red team, claims auditor, compliance flagger, pricing critic, clarity,
  - an optional reader of REAL competitor reviews you supply.

The verdict is decided by fixed rules in this program, never by the model. The judge only writes
the explanation. The best verdict is PROMISING, which means "worth testing with real people",
never "go".

  python3 swarm.py run examples/businesses/snack-box.json --mock
  python3 swarm.py batch examples/businesses --mock          # check every business in a folder
  ANTHROPIC_API_KEY=... python3 swarm.py run my-business.json --yes
"""
import argparse
import concurrent.futures as cf
import glob
import hashlib
import html
import json
import math
import os
import sys
from decimal import ROUND_HALF_UP, Decimal

import panel as P

SPECIALISTS = ("red_team", "claims_auditor", "compliance", "pricing_critic", "clarity")
TITLES = {"red_team": "Red team: why this could fail", "claims_auditor": "Claims auditor",
          "compliance": "Compliance flagger (not legal advice)", "pricing_critic": "Pricing critic", "clarity": "Clarity check"}
THEMES = ("price", "quality", "delivery", "customer_service", "accuracy_of_description", "safety", "durability", "taste_or_fit", "other")
REVIEW_CHUNK = 40
MAX_REVIEWS = 2000

# Rules of thumb, not science. Change them if you disagree.
MIN_BUY = 0.03            # below this share of BUY, the idea is weak
COMPLIANCE_SEVERITY = 4   # a medium/high-confidence issue this serious puts the idea on HOLD

RANK = {"PROMISING": 0, "FIX": 1, "HOLD": 2, "UNRELIABLE": 3, "INCOMPLETE": 4, "STOP": 5}
CSS_EXTRA = (".banner.warn{border-color:#F5A623}.tag{display:inline-block;background:#333741;border-radius:6px;padding:0 7px;margin-right:6px;font-size:.8em}"
             ".fatal{color:var(--bad)}td.num{text-align:right;font-variant-numeric:tabular-nums}.big{font-size:1.25em}a{color:var(--accent)}")


# ---------- money (whole cents, no floats) ----------
def cents(x):
    return int((Decimal(str(x)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def hup(n, d):
    """n/d rounded half up, for n >= 0."""
    return (2 * n + d) // (2 * d)


def dollars(c):
    sign = "-" if c < 0 else ""
    c = abs(c)
    return "%s$%s.%02d" % (sign, format(c // 100, ","), c % 100)


PRODUCT_FIELDS = ("unit_cost", "freight_cost", "packaging_cost", "payment_fee_pct", "payment_fee_fixed", "returns_pct", "ad_cost_per_order")
SUB_FIELDS = ("unit_cost", "payment_fee_pct", "payment_fee_fixed", "returns_pct", "ad_cost_per_order", "churn_pct")


def margin(biz):
    """Per-order (product) or per-customer-per-month (subscription) money check. Costs are entered ex-GST."""
    sub = biz.get("type", "product") == "subscription"
    fields = SUB_FIELDS if sub else PRODUCT_FIELDS
    missing = [f for f in fields if f not in biz]
    critical = [f for f in ("unit_cost", "churn_pct") if f in missing and (f == "unit_cost" or sub)]
    price = cents(biz["price"])
    gst = hup(price, 11) if biz.get("gst_registered", True) else 0
    rev = price - gst
    fee = hup(price * cents(biz.get("payment_fee_pct", 0)), 10000) + cents(biz.get("payment_fee_fixed", 0))
    refunds = hup(rev * cents(biz.get("returns_pct", 0)), 10000)
    unit = cents(biz.get("unit_cost", 0))
    cac = cents(biz.get("ad_cost_per_order", 0))
    lines = [("Customer pays (incl. GST)", price), ("GST to the ATO", -gst), ("Revenue ex-GST", rev),
             ("Cost to make or serve", -unit)]
    if not sub:
        lines += [("Postage you pay", -cents(biz.get("freight_cost", 0))), ("Packaging", -cents(biz.get("packaging_cost", 0)))]
    lines += [("Payment fees", -fee), ("Expected refunds", -refunds)]
    out = {"type": "subscription" if sub else "product", "missing": missing, "critical_missing": critical, "break_even": None,
           "ltv": None, "cac": cac, "ltv_to_cac": None, "payback_months": None}
    contribution = rev - unit - fee - refunds - (0 if sub else cents(biz.get("freight_cost", 0)) + cents(biz.get("packaging_cost", 0)))
    if not sub:
        lines.append(("Ad cost to win the order", -cac))
        contribution -= cac
    out["lines"], out["contribution"] = lines, contribution
    out["margin_pct"] = round(100 * contribution / rev, 1) if rev > 0 else None
    fixed = cents(biz.get("monthly_fixed_costs", 0))
    if contribution > 0 and fixed:
        out["break_even"] = -(-fixed // contribution)
    if sub and contribution > 0 and biz.get("churn_pct"):
        out["ltv"] = hup(contribution * 10000, cents(biz["churn_pct"]))
        if cac:
            out["ltv_to_cac"] = round(out["ltv"] / cac, 1)
            out["payback_months"] = round(cac / contribution, 1)
    return out


# ---------- verdict (fixed rules; the model never decides) ----------
def verdict(m, agg, control, side):
    if m["critical_missing"]:
        return {"label": "INCOMPLETE", "why": "The maths cannot be checked: missing %s." % ", ".join(m["critical_missing"]),
                "next": "Add those numbers to the business file and run again."}
    if m["contribution"] <= 0:
        return {"label": "STOP", "why": "You lose %s on every %s before fixed costs." % (dollars(-m["contribution"]), "customer-month" if m["type"] == "subscription" else "order"),
                "next": "Raise the price or cut costs until the maths works, then run again."}
    if m["ltv"] is not None and m["cac"] and m["ltv"] < m["cac"]:
        return {"label": "STOP", "why": "A customer is worth %s over their life but costs %s to win." % (dollars(m["ltv"]), dollars(m["cac"])),
                "next": "Lower the cost of winning a customer, cut churn or raise the price."}
    if not agg.get("n"):
        return {"label": "UNRELIABLE", "why": "The customer panel returned no usable answers.", "next": "Check the API key and run again."}
    cv = P.control_verdict(control)
    if cv is None:
        return {"label": "UNRELIABLE", "why": "The control check did not run, so the panel cannot be trusted.", "next": "Run again without --no-control."}
    if cv.startswith("WARNING"):
        return {"label": "UNRELIABLE", "why": cv, "next": "Re-run, or tighten the panel prompt, before trusting any number."}
    issues = (side.get("compliance", {}).get("data") or {}).get("issues", [])
    serious = [i for i in issues if i["severity"] >= COMPLIANCE_SEVERITY and i["confidence"] in ("medium", "high")]
    if serious:
        return {"label": "HOLD", "why": "A specialist flagged a serious compliance issue: %s" % serious[0]["issue"],
                "next": "Get proper advice (%s) before going further." % (serious[0]["check_with"] or "a qualified adviser")}
    if agg["buy"] < MIN_BUY:
        return {"label": "FIX", "why": "Only %s of the panel would buy." % P.pct(agg["buy"]),
                "next": "Read the objections, change the pitch or price, and run again."}
    return {"label": "PROMISING", "why": "The maths works, the control check passed and %s of the panel would buy." % P.pct(agg["buy"]),
            "next": "Test with 5 to 10 real people before spending real money. A simulated panel is not evidence of demand."}


# ---------- specialists ----------
SPEC_SYSTEM = ("You are a specialist reviewer advising an Australian small business. Use ONLY the facts in the business description. "
               "Never invent prices, statistics, competitors, laws or facts, and say so when you are not sure. "
               "Reply with one JSON object and nothing else.")
SPEC_PROMPTS = {
    "red_team": 'Give the most likely reasons this business fails. JSON: {"failures":[{"reason":str,"severity":1-5,"fatal":true|false}]}. At most 8, worst first.',
    "claims_auditor": 'List every factual claim the pitch makes. For each say whether the description itself supports it, and give a safer rewrite. JSON: {"claims":[{"claim":str,"supported":true|false,"fix":str}]}. At most 8.',
    "compliance": ('You are NOT a lawyer: flag possible problems, never clear anything. Consider Australian Consumer Law, labelling, health or income claims, '
                   'privacy, licensing and tax. JSON: {"issues":[{"issue":str,"area":"consumer_law|labelling|health_claims|privacy|licensing|tax|other",'
                   '"severity":1-5,"confidence":"low|medium|high","check_with":str}]}. At most 8.'),
    "pricing_critic": ('Judge the price against the value described. You have no competitor data, so do not quote any; say what data would settle it. '
                       'JSON: {"verdict":"too_low|about_right|too_high|unclear","reasoning":str,"data_needed":[str]}.'),
    "clarity": 'Could a stranger understand this offer in five seconds? JSON: {"one_line":str,"clear":true|false,"confusions":[str]}.',
}


def business_text(biz):
    sub = biz.get("type") == "subscription"
    return "\n".join(["THE BUSINESS", "Name: " + biz["name"], "Type: " + ("subscription (price is per month)" if sub else "one-off product"),
                      "Sold to: " + ("small-business owners" if biz.get("audience") == "business" else "general consumers"),
                      "Price: %s %s%s" % (biz.get("currency", "AUD"), P.money(biz["price"]), " per month" if sub else ""),
                      "Pitch: " + biz["pitch"]] + (["Details: " + biz["details"]] if biz.get("details") else []))


def parse_json(text):
    try:
        return json.loads(text[text.index("{"):text.rindex("}") + 1])
    except (ValueError, TypeError):
        return None


def _s(x, n=300):
    return str(x)[:n]


def _n(x, lo, hi, d):
    try:
        return min(max(int(round(float(x))), lo), hi)
    except (TypeError, ValueError):
        return d


def _list(raw, key):
    v = raw.get(key, []) if isinstance(raw, dict) else []
    return [i for i in v if isinstance(i, dict)][:8] if key not in ("data_needed", "confusions") else [_s(i) for i in v][:8]


def normalise(name, raw):
    if name == "red_team":
        return {"failures": [{"reason": _s(i.get("reason")), "severity": _n(i.get("severity"), 1, 5, 3), "fatal": bool(i.get("fatal"))} for i in _list(raw, "failures")]}
    if name == "claims_auditor":
        return {"claims": [{"claim": _s(i.get("claim")), "supported": bool(i.get("supported")), "fix": _s(i.get("fix"))} for i in _list(raw, "claims")]}
    if name == "compliance":
        conf = lambda c: c if c in ("low", "medium", "high") else "low"
        return {"issues": [{"issue": _s(i.get("issue")), "area": _s(i.get("area"), 30), "severity": _n(i.get("severity"), 1, 5, 3),
                            "confidence": conf(str(i.get("confidence", "")).lower()), "check_with": _s(i.get("check_with"), 120)} for i in _list(raw, "issues")]}
    if name == "pricing_critic":
        v = str(raw.get("verdict", "unclear")).lower()
        return {"verdict": v if v in ("too_low", "about_right", "too_high", "unclear") else "unclear",
                "reasoning": _s(raw.get("reasoning")), "data_needed": _list(raw, "data_needed")}
    return {"one_line": _s(raw.get("one_line")), "clear": bool(raw.get("clear")), "confusions": _list(raw, "confusions")}


def mock_specialist(name):
    return {"red_team": {"failures": [{"reason": "MOCK: placeholder failure reason.", "severity": 3, "fatal": False}]},
            "claims_auditor": {"claims": [{"claim": "MOCK: placeholder claim.", "supported": False, "fix": "MOCK"}]},
            "compliance": {"issues": [{"issue": "MOCK: placeholder issue.", "area": "other", "severity": 2, "confidence": "low", "check_with": "MOCK"}]},
            "pricing_critic": {"verdict": "unclear", "reasoning": "MOCK: placeholder.", "data_needed": ["MOCK"]},
            "clarity": {"one_line": "MOCK: placeholder.", "clear": True, "confusions": []}}[name]


def run_specialist(cfg, name, biz):
    if cfg.mock:
        return {"ok": True, "data": mock_specialist(name)}
    try:
        user = business_text(biz) + "\n\n" + SPEC_PROMPTS[name]
        raw = parse_json(P.call_model(cfg, SPEC_SYSTEM, user, max_tokens=900))
        if raw is None:
            raw = parse_json(P.call_model(cfg, SPEC_SYSTEM, user + "\n\nYour last reply was not valid JSON. Reply with the JSON object only.", max_tokens=900))
        return {"ok": True, "data": normalise(name, raw)} if raw is not None else {"ok": False, "error": "unparseable reply"}
    except P.Fatal:
        raise
    except Exception as e:
        return {"ok": False, "error": str(e)[:120]}


# ---------- real competitor reviews ----------
def load_reviews(biz, base_dir):
    if not biz.get("reviews_file"):
        return []
    path = os.path.join(base_dir, biz["reviews_file"])
    if not os.path.exists(path):
        raise SystemExit("reviews_file not found: %s" % path)
    with open(path, encoding="utf-8") as fh:
        lines = [l.strip() for l in fh if l.strip()]
    return lines[:MAX_REVIEWS]


def chunks(lines):
    return [lines[i:i + REVIEW_CHUNK] for i in range(0, len(lines), REVIEW_CHUNK)]


def read_review_chunk(cfg, chunk):
    if cfg.mock:
        h = int(hashlib.sha1("\n".join(chunk).encode()).hexdigest(), 16)
        return {"ok": True, "themes": {THEMES[(h >> k) % len(THEMES)]: 1 + (h >> (k + 5)) % 4 for k in range(3)}, "quotes": ["MOCK review summary"]}
    system = ("You read real customer reviews of a competing product. Count how many of the reviews raise each complaint theme. "
              "Use only what the reviews say. Reply with one JSON object and nothing else.")
    user = ("Reviews, one per line:\n" + "\n".join(chunk) + '\n\nJSON: {"themes":{theme:count},"quotes":[up to 2 short verbatim quotes]}. Themes allowed: ' + ", ".join(THEMES))
    try:
        raw = parse_json(P.call_model(cfg, system, user, max_tokens=500))
        if raw is None:
            return {"ok": False}
        themes = {}
        for k, v in (raw.get("themes") or {}).items():
            key = k if k in THEMES else "other"
            themes[key] = themes.get(key, 0) + _n(v, 0, len(chunk), 0)
        return {"ok": True, "themes": themes, "quotes": [_s(q, 200) for q in (raw.get("quotes") or [])][:2]}
    except P.Fatal:
        raise
    except Exception:
        return {"ok": False}


def summarise_reviews(results, total):
    themes, quotes = {}, []
    for r in results:
        if r.get("ok"):
            for k, v in r["themes"].items():
                themes[k] = themes.get(k, 0) + v
            quotes += r["quotes"]
    return {"reviews_read": total, "chunks_failed": sum(1 for r in results if not r.get("ok")),
            "themes": sorted(themes.items(), key=lambda kv: -kv[1]), "quotes": quotes[:6]}


# ---------- judge (writes the explanation only) ----------
def run_judge(cfg, facts, fallback):
    if cfg.mock:
        return {"summary": "MOCK: placeholder summary. " + fallback["why"], "next_actions": ["MOCK: " + fallback["next"]], "ai": False}
    system = ("You are the chief judge of a business review swarm. You are given the verdict (decided by fixed rules) and the facts. "
              "Write a plain-English summary for a busy small-business owner. Do NOT change the verdict. "
              "Use only the numbers in the facts and never invent any. Reply with one JSON object and nothing else.")
    user = json.dumps(facts, indent=1) + '\n\nJSON: {"summary": "3-4 sentences", "next_actions": ["action", "action", "action"]}'
    try:
        raw = parse_json(P.call_model(cfg, system, user, max_tokens=600))
        if raw and raw.get("summary"):
            return {"summary": _s(raw["summary"], 800), "next_actions": [_s(a) for a in (raw.get("next_actions") or [])][:3], "ai": True}
    except P.Fatal:
        raise
    except Exception:
        pass
    return {"summary": fallback["why"], "next_actions": [fallback["next"]], "ai": False}


# ---------- orchestration ----------
def normalise_business(biz, base_dir=""):
    for key in ("name", "pitch", "price"):
        if key not in biz:
            raise SystemExit("Business file is missing '%s'." % key)
    biz["price"] = float(biz["price"])
    if biz["price"] <= 0:
        raise SystemExit("price must be above 0.")
    biz.setdefault("type", "product")
    biz.setdefault("audience", "consumer")
    if biz["type"] not in ("product", "subscription") or biz["audience"] not in ("consumer", "business"):
        raise SystemExit("type must be product or subscription; audience must be consumer or business.")
    for k in ("payment_fee_pct", "returns_pct", "churn_pct"):
        if k in biz and not 0 <= float(biz[k]) <= 100:
            raise SystemExit("%s must be between 0 and 100." % k)
    biz.setdefault("price_points", sorted({round(biz["price"] * m) for m in (0.5, 0.75, 1, 1.25, 1.5)}))
    return biz


def planned_calls(biz, size, control_n, base_dir):
    return size + control_n + len(SPECIALISTS) + len(chunks(load_reviews(biz, base_dir))) + 1


def run_side(cfg, biz, reviews, outdir, workers):
    fp = hashlib.sha1(json.dumps([biz, cfg.model, cfg.mock, reviews], sort_keys=True).encode()).hexdigest()[:12]
    path = os.path.join(outdir, "side.json")
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                cached = json.load(fh)
            if cached.get("fp") == fp:
                return cached["side"]
        except ValueError:
            pass
    with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        spec_f = {n: ex.submit(run_specialist, cfg, n, biz) for n in SPECIALISTS}
        rev_f = [ex.submit(read_review_chunk, cfg, c) for c in chunks(reviews)]
        side = {n: f.result() for n, f in spec_f.items()}
        side["reviews"] = summarise_reviews([f.result() for f in rev_f], len(reviews)) if reviews else None
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"fp": fp, "side": side}, fh)
    return side


def run_business(biz, cfg, outdir, size, seed, workers, control_size, control_on, base_dir=""):
    os.makedirs(outdir, exist_ok=True)
    people = P.make_personas(size, seed, biz["audience"])
    offer = {k: biz[k] for k in ("name", "pitch", "price", "currency", "details", "audience", "price_points") if k in biz}
    res = P.run_arm(cfg, people, offer, os.path.join(outdir, "raw-offer.jsonl"), workers, biz["name"])
    control = None
    if control_on and control_size:
        n = min(control_size, size)
        control = P.aggregate(P.run_arm(cfg, people[:n], P.control_offer(offer), os.path.join(outdir, "raw-control.jsonl"), workers, "control"), people, [])
    agg = P.aggregate(res, people, biz["price_points"])
    side = run_side(cfg, biz, load_reviews(biz, base_dir), outdir, workers)
    m = margin(biz)
    v = verdict(m, agg, control, side)
    facts = {"verdict": v, "money": {"contribution_cents": m["contribution"], "margin_pct": m["margin_pct"], "ltv_to_cac": m["ltv_to_cac"]},
             "panel": {k: agg.get(k) for k in ("n", "buy", "maybe", "pass")}, "top_objections": agg.get("objections", [])[:3],
             "specialists": {n: side[n].get("data") for n in SPECIALISTS}, "review_themes": (side.get("reviews") or {}).get("themes", [])[:3]}
    judge = run_judge(cfg, facts, v)
    meta = {"model": "mock" if cfg.mock else cfg.model, "mock": cfg.mock, "size": size, "seed": seed}
    summary = {"business": biz, "meta": meta, "verdict": v, "money": m, "panel": agg, "control": control, "specialists": side, "judge": judge}
    P.write_csv(outdir, res, people)
    with open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    with open(os.path.join(outdir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(render(summary, offer))
    return summary


# ---------- reports ----------
def render(sm, offer):
    e = html.escape
    v, m, side, judge = sm["verdict"], sm["money"], sm["specialists"], sm["judge"]
    cls = "good" if v["label"] == "PROMISING" else "warn" if v["label"] in ("FIX", "HOLD") else "bad"
    out = []
    if sm["meta"]["mock"]:
        out.append('<div class="banner bad">MOCK RUN: every AI answer below is a fake placeholder made by the program. It only shows the layout.</div>')
    out.append("<h1>%s</h1>" % e(sm["business"]["name"]))
    out.append('<div class="banner %s big"><b>%s</b><br>%s<br><br><b>Next:</b> %s</div>' % (cls, e(v["label"]), e(v["why"]), e(v["next"])))
    out.append("<p class='sub'>The verdict comes from fixed rules in the program, not from the AI. It can never say \"go\": the best it says is PROMISING, "
               "which means worth testing with real people.</p>")
    per = "per customer per month" if m["type"] == "subscription" else "per order"
    out.append("<h2>Money check (%s)</h2><table>" % per)
    for label, c in m["lines"]:
        out.append('<tr><td>%s</td><td class="num">%s</td></tr>' % (e(label), dollars(c)))
    out.append('<tr><td><b>Left over</b></td><td class="num"><b>%s</b>%s</td></tr></table>'
               % (dollars(m["contribution"]), " (%s%%)" % m["margin_pct"] if m["margin_pct"] is not None else ""))
    if m["break_even"]:
        out.append("<p>Break-even: <b>%d</b> %s a month to cover your fixed costs.</p>" % (m["break_even"], "customers" if m["type"] == "subscription" else "orders"))
    if m["ltv"] is not None:
        out.append("<p>A customer is worth about <b>%s</b> over their life%s.</p>" % (dollars(m["ltv"]), (", %.1fx what it costs to win them (pays back in %.1f months)" % (m["ltv_to_cac"], m["payback_months"])) if m["ltv_to_cac"] else ""))
    if m["missing"]:
        out.append('<div class="banner warn">Not provided, so counted as zero: %s. The result may look better than reality.</div>' % e(", ".join(m["missing"])))
    out.append("<h2>Summary</h2><p>%s</p>" % e(judge["summary"]))
    if judge["next_actions"]:
        out.append("<ul>" + "".join("<li>%s</li>" % e(a) for a in judge["next_actions"]) + "</ul>")
    out.append("<p class='sub'>%s</p>" % ("Written by the AI judge from the facts above; check it." if judge["ai"] else "Plain summary from the rules (no AI used)."))
    out.append("<h2>Specialist reviewers</h2><p class='sub'>AI opinions, unverified. They are prompts to check, not facts.</p>")
    for n in SPECIALISTS:
        out.append("<h3>%s</h3>" % e(TITLES[n]))
        r = side[n]
        if not r.get("ok"):
            out.append("<p>Failed: %s</p>" % e(r.get("error", "")))
            continue
        d = r["data"]
        if n == "red_team":
            out += ['<blockquote><span class="tag">severity %d</span>%s%s</blockquote>' % (i["severity"], '<span class="tag fatal">could be fatal</span>' if i["fatal"] else "", e(i["reason"])) for i in d["failures"]]
        elif n == "claims_auditor":
            out += ['<blockquote><span class="tag">%s</span>%s<br><span class="sub">Safer: %s</span></blockquote>' % ("supported" if i["supported"] else "NOT supported", e(i["claim"]), e(i["fix"])) for i in d["claims"]]
        elif n == "compliance":
            out += ['<blockquote><span class="tag">severity %d</span><span class="tag">%s confidence</span>%s<br><span class="sub">Check with: %s</span></blockquote>'
                    % (i["severity"], e(i["confidence"]), e(i["issue"]), e(i["check_with"])) for i in d["issues"]]
        elif n == "pricing_critic":
            out.append("<blockquote><span class='tag'>%s</span>%s<br><span class='sub'>Data that would settle it: %s</span></blockquote>"
                       % (e(d["verdict"].replace("_", " ")), e(d["reasoning"]), e("; ".join(d["data_needed"]) or "none given")))
        else:
            out.append("<blockquote><span class='tag'>%s</span>In one line: %s%s</blockquote>"
                       % ("clear" if d["clear"] else "UNCLEAR", e(d["one_line"]), ("<br><span class='sub'>Confusions: %s</span>" % e("; ".join(d["confusions"]))) if d["confusions"] else ""))
    rv = side.get("reviews")
    if rv:
        out.append("<h2>What real competitor reviews complain about</h2><p class='sub'>%d real reviews read; %d batches failed. This is real data you supplied, so it is worth more than the simulated panel.</p>" % (rv["reviews_read"], rv["chunks_failed"]))
        top = max([c for _, c in rv["themes"]] or [1])
        for k, c in rv["themes"]:
            out.append('<div class="bar"><span>%s</span><i style="width:%.0f%%"></i><em>%d</em></div>' % (e(k.replace("_", " ")), 100 * c / top, c))
        out += ["<blockquote>%s</blockquote>" % e(q) for q in rv["quotes"]]
    out.append("<h2>Customer panel</h2>")
    out.append(P.render_body(offer, sm["panel"], sm["control"], sm["meta"], title=False))
    return P.page("".join(out)).replace("</style>", CSS_EXTRA + "</style>")


def render_ranking(rows):
    e = html.escape
    out = ["<h1>Swarm ranking</h1><p class='sub'>Best first. A verdict is a rule-based check, not a prediction of success.</p><table>",
           "<tr><td><b>Business</b></td><td><b>Verdict</b></td><td><b>Would buy</b></td><td><b>Left over</b></td></tr>"]
    for r in rows:
        out.append('<tr><td><a href="%s/report.html">%s</a></td><td>%s</td><td class="num">%s</td><td class="num">%s</td></tr>'
                   % (e(r["dir"]), e(r["name"]), e(r["verdict"]), P.pct(r["buy"]) if r["buy"] is not None else "-", dollars(r["contribution"])))
    out.append("</table>")
    return P.page("".join(out)).replace("</style>", CSS_EXTRA + "</style>")


# ---------- command line ----------
def make_cfg(a):
    return P.Config(model=a.model, api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
                    base_url=os.environ.get("ANTHROPIC_BASE_URL", P.API_URL), mock=a.mock)


def check_spend(a, cfg, total):
    print("Plan: %d model calls in total (customers + control + 5 specialists + review readers + 1 judge)." % total, file=sys.stderr)
    if cfg.mock:
        return
    if not cfg.api_key:
        raise SystemExit("Set ANTHROPIC_API_KEY first, or use --mock to try it free with fake answers.")
    if total > a.max_calls:
        raise SystemExit("That is %d calls, above the safety cap of %d. If you mean it, add --max-calls %d." % (total, a.max_calls, total))
    if not a.yes:
        raise SystemExit("This will spend money on your API account. Check Anthropic's current pricing, then add --yes to run.")


def control_n(a):
    return (a.control_size if a.control_size is not None else max(200, a.size // 20)) if a.control else 0


def cmd_run(a):
    cfg = make_cfg(a)
    base = os.path.dirname(os.path.abspath(a.business))
    biz = normalise_business(json.load(open(a.business, encoding="utf-8")), base)
    check_spend(a, cfg, planned_calls(biz, a.size, min(control_n(a), a.size), base))
    try:
        sm = run_business(biz, cfg, a.out, a.size, a.seed, a.workers, control_n(a), a.control, base)
    except P.Fatal as e:
        raise SystemExit(str(e))
    print("%s: %s - %s" % (biz["name"], sm["verdict"]["label"], sm["verdict"]["why"]))
    print("Open %s" % os.path.join(a.out, "report.html"))


def cmd_batch(a):
    cfg = make_cfg(a)
    files = sorted(glob.glob(os.path.join(a.folder, "*.json")))
    if not files:
        raise SystemExit("No .json business files in %s" % a.folder)
    bizs = [(f, normalise_business(json.load(open(f, encoding="utf-8")), a.folder)) for f in files]
    check_spend(a, cfg, sum(planned_calls(b, a.size, min(control_n(a), a.size), a.folder) for _, b in bizs))
    rows = []
    try:
        for f, b in bizs:
            stem = os.path.splitext(os.path.basename(f))[0]
            sm = run_business(b, cfg, os.path.join(a.out, stem), a.size, a.seed, a.workers, control_n(a), a.control, a.folder)
            rows.append({"name": b["name"], "dir": stem, "verdict": sm["verdict"]["label"], "buy": sm["panel"].get("buy"),
                         "contribution": sm["money"]["contribution"], "why": sm["verdict"]["why"]})
            print("%-28s %-10s %s" % (b["name"], sm["verdict"]["label"], sm["verdict"]["why"]))
    except P.Fatal as e:
        raise SystemExit(str(e))
    rows.sort(key=lambda r: (RANK[r["verdict"]], -(r["buy"] or 0)))
    with open(os.path.join(a.out, "ranking.html"), "w", encoding="utf-8") as fh:
        fh.write(render_ranking(rows))
    json.dump(rows, open(os.path.join(a.out, "ranking.json"), "w", encoding="utf-8"), indent=2)
    print("Open %s" % os.path.join(a.out, "ranking.html"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Swarm 1001: check a business from every angle before you commit.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name, fn, arg in (("run", cmd_run, "business"), ("batch", cmd_batch, "folder")):
        r = sub.add_parser(name)
        r.add_argument(arg)
        r.add_argument("--size", type=int, default=1000)
        r.add_argument("--seed", type=int, default=48)
        r.add_argument("--model", default=P.DEFAULT_MODEL)
        r.add_argument("--workers", type=int, default=8)
        r.add_argument("--out", default="swarm-out")
        r.add_argument("--mock", action="store_true")
        r.add_argument("--no-control", dest="control", action="store_false")
        r.add_argument("--control-size", type=int, default=None)
        r.add_argument("--max-calls", type=int, default=2500)
        r.add_argument("--yes", action="store_true")
        r.set_defaults(func=fn)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
