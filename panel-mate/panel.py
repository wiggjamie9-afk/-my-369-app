#!/usr/bin/env python3
"""Panel Mate - test a product idea on a panel of simulated Australian customers.

Standard library only. Each simulated customer is one model call. The customers
(age, state, household, income, shopping style) are drawn by this program from a
seeded random generator, NOT invented by the model, so the mix is controlled and
repeatable.

IMPORTANT: this is a way to find objections and weak spots in an idea. It does
NOT predict how many real people will buy. The built-in control check (an
obviously bad offer) tells you whether the panel is too agreeable to trust.

Usage:
  python3 panel.py run examples/snack-box.json --mock            # free, fake answers, to see the report
  ANTHROPIC_API_KEY=... python3 panel.py run idea.json --size 1000 --yes
"""
import argparse
import concurrent.futures as cf
import csv
import hashlib
import html
import json
import math
import os
import random
import statistics
import sys
import threading
import time
import urllib.error
import urllib.request

DEFAULT_MODEL = "claude-haiku-5-5"
API_URL = "https://api.anthropic.com/v1/messages"
DECISIONS = ("BUY", "MAYBE", "PASS")
OBJECTIONS = ("too_expensive", "dont_need_it", "dont_trust_brand", "prefer_alternative",
              "unclear_value", "delivery_or_hassle", "quality_doubts", "none")

# Illustrative weights, roughly Australian-shaped. NOT census-exact.
AGE_BANDS = [("18-24", 11, 18, 24), ("25-34", 18, 25, 34), ("35-44", 17, 35, 44),
             ("45-54", 15, 45, 54), ("55-64", 14, 55, 64), ("65+", 25, 65, 82)]
STATES = [("NSW", 32), ("VIC", 26), ("QLD", 20), ("WA", 11), ("SA", 7), ("TAS", 2), ("ACT", 1.7), ("NT", 1)]
INCOMES = [("under $50k", 28), ("$50-90k", 27), ("$90-150k", 28), ("over $150k", 17)]
STYLES = [("a bargain hunter who waits for sales", 22), ("someone who pays more for quality", 15),
          ("an impulse buyer", 12), ("a careful researcher who reads reviews first", 20),
          ("loyal to brands they already know", 11), ("a sceptic who distrusts most ads", 20)]
TRUST = [("fairly trusting", 25), ("cautious", 45), ("distrustful", 30)]
BUDGET_BY_INCOME = {"under $50k": [("tight", 70), ("ok", 28), ("comfortable", 2)],
                    "$50-90k": [("tight", 30), ("ok", 55), ("comfortable", 15)],
                    "$90-150k": [("tight", 10), ("ok", 50), ("comfortable", 40)],
                    "over $150k": [("tight", 3), ("ok", 25), ("comfortable", 72)]}
HOUSEHOLDS_YOUNG = [("living with parents", 35), ("in a share house", 30), ("single, living alone", 20), ("in a couple, no kids", 15)]
HOUSEHOLDS_MID = [("single, living alone", 20), ("in a couple, no kids", 25), ("a parent with young kids", 25),
                  ("a parent with teenagers", 20), ("in a share house", 10)]
HOUSEHOLDS_OLDER = [("a retired single", 30), ("a retired couple", 35), ("in a couple, no kids at home", 25), ("single, living alone", 10)]

SYSTEM = ("You are role-playing ONE specific Australian consumer, described below, who has just come across an offer. "
          "Stay in character and answer as that person would, not as a helpful assistant. "
          "Real people ignore most offers and say no to most of them: your default answer is PASS unless the offer "
          "clearly fits your life and you can comfortably afford it. Do not be polite or encouraging. "
          "Do not invent facts about the product beyond what the offer says. "
          "Reply with a single JSON object and nothing else.")


def pick(rng, table):
    return rng.choices([t[0] for t in table], weights=[t[1] for t in table])[0]


def make_personas(n, seed=48):
    rng = random.Random(seed)
    people = []
    for i in range(n):
        band = rng.choices(AGE_BANDS, weights=[b[1] for b in AGE_BANDS])[0]
        age = rng.randint(band[2], band[3])
        table = HOUSEHOLDS_YOUNG if age < 25 else HOUSEHOLDS_OLDER if age >= 65 else HOUSEHOLDS_MID
        income = pick(rng, INCOMES)
        people.append({"id": i + 1, "age": age, "age_band": band[0], "state": pick(rng, STATES),
                       "household": pick(rng, table), "income": income,
                       "budget": pick(rng, BUDGET_BY_INCOME[income]), "style": pick(rng, STYLES),
                       "trust": pick(rng, TRUST)})
    return people


def persona_text(p):
    return ("You are a %d-year-old living in %s, Australia. You are %s. Household income is %s a year, so money is %s. "
            "You are %s. Towards small online brands you have not heard of you are %s."
            % (p["age"], p["state"], p["household"], p["income"], p["budget"], p["style"], p["trust"]))


def money(x):
    x = float(x)
    return str(int(x)) if x == int(x) else "%.2f" % x


def offer_text(offer):
    lines = ["THE OFFER", "Name: %s" % offer["name"], "Price: %s %s" % (offer.get("currency", "AUD"), money(offer["price"])),
             "Pitch: %s" % offer["pitch"]]
    if offer.get("details"):
        lines.append("Details: %s" % offer["details"])
    return "\n".join(lines)


SCHEMA = ('Reply as JSON with exactly these keys: "decision" ("BUY", "MAYBE" or "PASS"), '
          '"max_price" (the highest price in the same currency at which you would actually buy it, or 0 if you would not at any price), '
          '"stars" (1-5, how appealing the offer is to you), '
          '"objection" (one of: %s), "reason" (one sentence in your own words), "review" (a one-line honest review/reaction).'
          % ", ".join(OBJECTIONS))


def parse_answer(text):
    """Return a cleaned dict, or None if the model's reply is unusable."""
    try:
        a, b = text.index("{"), text.rindex("}")
        raw = json.loads(text[a:b + 1])
        decision = str(raw["decision"]).strip().upper()
        if decision not in DECISIONS:
            return None
        max_price = float(raw.get("max_price") or 0)
        max_price = min(max(max_price, 0.0), 100000.0)
        stars = int(round(float(raw.get("stars", 3))))
        objection = str(raw.get("objection", "none")).strip().lower()
        return {"decision": decision, "max_price": max_price, "stars": min(max(stars, 1), 5),
                "objection": objection if objection in OBJECTIONS else "other",
                "reason": str(raw.get("reason", ""))[:300], "review": str(raw.get("review", ""))[:300]}
    except (ValueError, KeyError, TypeError):
        return None


class Fatal(Exception):
    pass


class Config:
    def __init__(self, model=DEFAULT_MODEL, api_key="", base_url=API_URL, retries=5, backoff=1.5, mock=False):
        self.model, self.api_key, self.base_url = model, api_key, base_url
        self.retries, self.backoff, self.mock = retries, backoff, mock


def call_model(cfg, system, user):
    body = json.dumps({"model": cfg.model, "max_tokens": 400, "system": system,
                       "messages": [{"role": "user", "content": user}]}).encode()
    headers = {"content-type": "application/json", "x-api-key": cfg.api_key, "anthropic-version": "2023-06-01"}
    last = "unknown"
    for attempt in range(cfg.retries):
        try:
            req = urllib.request.Request(cfg.base_url, data=body, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read())
            return "".join(c.get("text", "") for c in data.get("content", []) if c.get("type") == "text")
        except urllib.error.HTTPError as e:
            last = "HTTP %d" % e.code
            if e.code in (401, 403):
                raise Fatal("The API refused the key (HTTP %d). Check ANTHROPIC_API_KEY." % e.code)
            if e.code not in (408, 429, 500, 502, 503, 529):
                raise Fatal("The API rejected the request (HTTP %d)." % e.code)
            try:
                wait = min(float(e.headers.get("retry-after", "")), 30)
            except (TypeError, ValueError):
                wait = cfg.backoff * (2 ** attempt)
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last = type(e).__name__
            wait = cfg.backoff * (2 ** attempt)
        time.sleep(min(wait, 30))
    raise RuntimeError("gave up after %d tries (%s)" % (cfg.retries, last))


def mock_answer(p, offer):
    """Deterministic fake answers so the pipeline can be tried for free. Not real opinions."""
    rng = random.Random("%s|%s|%s" % (p["id"], offer["name"], offer["price"]))
    score = 0.30 - float(offer["price"]) / 200.0
    score += {"tight": -0.08, "ok": 0.0, "comfortable": 0.05}[p["budget"]]
    score += 0.06 if "impulse" in p["style"] else -0.06 if "sceptic" in p["style"] else 0.0
    score -= 0.05 if p["trust"] == "distrustful" else 0.0
    p_buy = min(max(score, 0.01), 0.40)
    r = rng.random()
    price = float(offer["price"])
    if r < p_buy:
        d, mp, st = "BUY", price * (1 + rng.uniform(0, 0.4)), rng.choice([4, 5])
    elif r < p_buy + 0.12:
        d, mp, st = "MAYBE", price * rng.uniform(0.5, 0.95), 3
    else:
        d, mp, st = "PASS", (0 if rng.random() < 0.5 else price * rng.uniform(0, 0.5)), rng.choice([1, 2])
    obj = "none" if d == "BUY" else rng.choice(OBJECTIONS[:-1])
    return {"decision": d, "max_price": round(mp, 2), "stars": st, "objection": obj,
            "reason": "MOCK: simulated placeholder, not a real answer.", "review": "MOCK"}


def ask(cfg, p, offer, fingerprint):
    try:
        if cfg.mock:
            ans = mock_answer(p, offer)
        else:
            text = call_model(cfg, SYSTEM, persona_text(p) + "\n\n" + offer_text(offer) + "\n\n" + SCHEMA)
            ans = parse_answer(text)
            if ans is None:
                text = call_model(cfg, SYSTEM, persona_text(p) + "\n\n" + offer_text(offer) + "\n\n" + SCHEMA
                                  + "\n\nYour last reply was not valid JSON. Reply with the JSON object only.")
                ans = parse_answer(text)
            if ans is None:
                return {"id": p["id"], "fp": fingerprint, "ok": False, "error": "unparseable reply"}
        ans.update({"id": p["id"], "fp": fingerprint, "ok": True})
        return ans
    except Fatal:
        raise
    except Exception as e:  # one bad call must not sink the run
        return {"id": p["id"], "fp": fingerprint, "ok": False, "error": str(e)[:120]}


def fingerprint_for(offer, cfg):
    blob = json.dumps([offer, cfg.model, bool(cfg.mock)], sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()[:12]


def run_arm(cfg, people, offer, path, workers, label):
    """Ask every persona about this offer. Resumes from `path` if it matches."""
    fp = fingerprint_for(offer, cfg)
    done = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("ok") and r.get("fp") == fp:
                    done[r["id"]] = r
    pending = [p for p in people if p["id"] not in done]
    lock = threading.Lock()
    count = [0]
    with open(path, "a", encoding="utf-8") as out:
        def job(p):
            r = ask(cfg, p, offer, fp)
            with lock:
                out.write(json.dumps(r) + "\n")
                out.flush()
                count[0] += 1
                if count[0] % 50 == 0:
                    print("  %s: %d/%d" % (label, count[0], len(pending)), file=sys.stderr)
            return r
        with cf.ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
            futures = [ex.submit(job, p) for p in pending]
            try:
                for f in cf.as_completed(futures):
                    r = f.result()
                    done[r["id"]] = r
            except Fatal:
                for f in futures:
                    f.cancel()
                raise
    return [done[p["id"]] for p in people if p["id"] in done]


def interval(p, n):
    return 1.96 * math.sqrt(p * (1 - p) / n) if n else 0.0


def aggregate(results, people, price_points):
    by_id = {p["id"]: p for p in people}
    ok = [r for r in results if r.get("ok")]
    n = len(ok)
    agg = {"n": n, "errors": len(results) - n}
    if not n:
        return agg
    cnt = {d: sum(1 for r in ok if r["decision"] == d) for d in DECISIONS}
    agg.update({"buy": cnt["BUY"] / n, "maybe": cnt["MAYBE"] / n, "pass": cnt["PASS"] / n,
                "buy_noise": interval(cnt["BUY"] / n, n), "stars": sum(r["stars"] for r in ok) / n})
    prices = [r["max_price"] for r in ok if r["max_price"] > 0]
    agg["median_max_price"] = statistics.median(prices) if prices else 0
    agg["demand"] = [{"price": pp, "share": sum(1 for r in ok if r["max_price"] >= pp) / n} for pp in price_points]
    obj = {}
    for r in ok:
        if r["decision"] != "BUY":
            obj[r["objection"]] = obj.get(r["objection"], 0) + 1
    non_buyers = sum(obj.values())
    agg["objections"] = sorted(([k, v, v / non_buyers] for k, v in obj.items()), key=lambda x: -x[1])
    segs = {}
    for dim in ("age_band", "income", "household", "style", "state"):
        groups = {}
        for r in ok:
            groups.setdefault(by_id[r["id"]][dim], []).append(r)
        rows = [{"label": k, "n": len(v), "buy": sum(1 for r in v if r["decision"] == "BUY") / len(v),
                 "interest": sum(1 for r in v if r["decision"] != "PASS") / len(v)} for k, v in groups.items()]
        if dim == "age_band":
            order = [b[0] for b in AGE_BANDS]
            rows.sort(key=lambda x: order.index(x["label"]))
        else:
            rows.sort(key=lambda x: -x["n"])
        segs[dim] = rows
    agg["segments"] = segs
    agg["quotes_buy"] = [r["reason"] for r in sorted(ok, key=lambda r: r["id"]) if r["decision"] == "BUY"][:6]
    agg["quotes_pass"] = [r["reason"] for r in sorted(ok, key=lambda r: r["id"]) if r["decision"] == "PASS"][:6]
    return agg


def control_verdict(control):
    """A deliberately bad offer should almost never sell. If it does, the panel is too agreeable."""
    if not control or not control.get("n"):
        return None
    if control["buy"] > 0.10 or control["buy"] + control["maybe"] > 0.20:
        return ("WARNING: the panel said BUY or MAYBE to a deliberately bad offer %.0f%% of the time. "
                "This panel is too agreeable, so treat the results as noise." % (100 * (control["buy"] + control["maybe"])))
    return "Control check passed: the bad offer got only %.0f%% BUY/MAYBE." % (100 * (control["buy"] + control["maybe"]))


def pct(x):
    return "%.0f%%" % (100 * x)


def render_report(offer, agg, control, meta):
    e = html.escape
    verdict = control_verdict(control)
    warn = verdict is not None and verdict.startswith("WARNING")
    rows = []
    if meta.get("mock"):
        rows.append('<div class="banner bad">MOCK RUN: these answers are fake placeholders made by the program, not by a model. '
                    'They only show what the report looks like.</div>')
    rows.append('<div class="banner">A simulated panel finds objections and weak spots. It does <b>not</b> tell you how many real '
                'people will buy. Test with real customers before spending real money.</div>')
    if verdict:
        rows.append('<div class="banner %s">%s</div>' % ("bad" if warn else "good", e(verdict)))
    rows.append("<h1>%s</h1><p class='sub'>%s %s &middot; %d answered, %d failed &middot; model %s</p>"
                % (e(offer["name"]), e(offer.get("currency", "AUD")), e(money(offer["price"])), agg["n"], agg["errors"], e(meta["model"])))
    if not agg["n"]:
        return page("".join(rows) + "<p>No usable answers.</p>")
    rows.append('<div class="tiles">'
                '<div class="tile"><b>%s</b><span>would BUY<br>&plusmn;%.0f pts simulation noise</span></div>'
                '<div class="tile"><b>%s</b><span>MAYBE</span></div>'
                '<div class="tile"><b>%s</b><span>PASS</span></div>'
                '<div class="tile"><b>%.1f / 5</b><span>appeal</span></div>'
                '<div class="tile"><b>%s</b><span>median top price</span></div></div>'
                % (pct(agg["buy"]), 100 * agg["buy_noise"], pct(agg["maybe"]), pct(agg["pass"]), agg["stars"], e("%.0f" % agg["median_max_price"])))
    rows.append("<h2>Price test</h2><p class='sub'>Share of the panel whose stated top price is at least this much.</p>")
    for d in agg["demand"]:
        rows.append('<div class="bar"><span>%s</span><i style="width:%.0f%%"></i><em>%s</em></div>' % (e(str(d["price"])), 100 * d["share"], pct(d["share"])))
    rows.append("<h2>Why people said no</h2>")
    for k, v, share in agg["objections"]:
        rows.append('<div class="bar"><span>%s</span><i style="width:%.0f%%"></i><em>%s</em></div>' % (e(k.replace("_", " ")), 100 * share, pct(share)))
    rows.append("<h2>Who bought</h2><p class='sub'>Groups under 30 people are greyed out: too small to read anything into.</p>")
    for dim, label in (("age_band", "Age"), ("income", "Household income"), ("household", "Household"), ("style", "Shopping style"), ("state", "State")):
        rows.append("<h3>%s</h3><table>" % label)
        for s in agg["segments"][dim]:
            rows.append('<tr class="%s"><td>%s</td><td>%d</td><td>BUY %s</td><td>BUY+MAYBE %s</td></tr>'
                        % ("small" if s["n"] < 30 else "", e(s["label"]), s["n"], pct(s["buy"]), pct(s["interest"])))
        rows.append("</table>")
    rows.append("<h2>In their words</h2><p class='sub'>The first six by panel number, not hand-picked.</p><h3>Buyers</h3>")
    rows += ["<blockquote>%s</blockquote>" % e(q) for q in agg["quotes_buy"]] or ["<p>None.</p>"]
    rows.append("<h3>Passers</h3>")
    rows += ["<blockquote>%s</blockquote>" % e(q) for q in agg["quotes_pass"]] or ["<p>None.</p>"]
    rows.append("<p class='sub'>Panel drawn with a fixed seed from illustrative Australian-shaped weights (not census-exact). "
                "Customer details come from the program, not the model.</p>")
    return page("".join(rows))


def page(body):
    return ("<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<title>Panel Mate report</title><style>"
            ":root{--bg:#1B1D21;--card:#262930;--ink:#EDEFF2;--mute:#A4AAB5;--accent:#3D8BFF;--good:#3DDC97;--bad:#FF6B6B}"
            "body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif;padding:16px;max-width:760px;margin:auto}"
            "h1{margin:.4em 0 0}h2{margin-top:1.8em}h3{color:var(--mute);font-size:1em;margin:1.2em 0 .3em}.sub{color:var(--mute);margin:.2em 0 .8em}"
            ".banner{background:var(--card);border-left:4px solid var(--accent);padding:10px 12px;border-radius:8px;margin:10px 0}"
            ".banner.bad{border-color:var(--bad)}.banner.good{border-color:var(--good)}"
            ".tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px;margin-top:14px}"
            ".tile{background:var(--card);border-radius:10px;padding:12px}.tile b{display:block;font-size:1.7em;color:var(--accent)}.tile span{color:var(--mute);font-size:.85em}"
            ".bar{display:grid;grid-template-columns:130px 1fr 44px;gap:8px;align-items:center;margin:5px 0}.bar i{display:block;height:14px;background:var(--accent);border-radius:7px}.bar em{font-style:normal;color:var(--mute);text-align:right}"
            "table{width:100%;border-collapse:collapse}td{padding:5px 4px;border-bottom:1px solid #333741;font-size:.92em}tr.small{opacity:.4}"
            "blockquote{margin:8px 0;padding:8px 12px;background:var(--card);border-radius:8px}"
            "</style></head><body>" + body + "</body></html>")


def load_idea(path):
    with open(path, encoding="utf-8") as fh:
        idea = json.load(fh)
    for key in ("name", "pitch", "price"):
        if key not in idea:
            raise SystemExit("Idea file is missing '%s'." % key)
    idea["price"] = float(idea["price"])
    if idea["price"] <= 0:
        raise SystemExit("price must be above 0.")
    idea.setdefault("price_points", sorted({round(idea["price"] * m) for m in (0.5, 0.75, 1, 1.25, 1.5)}))
    return idea


def control_offer(idea):
    return {"name": "CONTROL: empty box", "pitch": "A plain cardboard box with nothing inside. No brand, no extras.",
            "price": round(idea["price"] * 5), "currency": idea.get("currency", "AUD")}


def write_outputs(outdir, offer, agg, control_agg, results, people, meta):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "report.html"), "w", encoding="utf-8") as fh:
        fh.write(render_report(offer, agg, control_agg, meta))
    with open(os.path.join(outdir, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"offer": offer, "meta": meta, "panel": agg, "control": control_agg}, fh, indent=2)
    by_id = {p["id"]: p for p in people}
    with open(os.path.join(outdir, "answers.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "age", "state", "household", "income", "style", "decision", "max_price", "stars", "objection", "reason"])
        for r in results:
            if r.get("ok"):
                p = by_id[r["id"]]
                w.writerow([p["id"], p["age"], p["state"], p["household"], p["income"], p["style"],
                            r["decision"], r["max_price"], r["stars"], r["objection"], r["reason"]])


def cmd_run(a):
    offer = load_idea(a.idea)
    people = make_personas(a.size, a.seed)
    control_n = min(a.control_size, a.size) if a.control else 0
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    cfg = Config(model=a.model, api_key=api_key, base_url=os.environ.get("ANTHROPIC_BASE_URL", API_URL), mock=a.mock)
    total = a.size + control_n
    print("Plan: %d simulated customers on your offer + %d on the control = %d model calls (about 500 tokens in and 150 out each)."
          % (a.size, control_n, total), file=sys.stderr)
    if not a.mock:
        if not api_key:
            raise SystemExit("Set ANTHROPIC_API_KEY first, or use --mock to try it free with fake answers.")
        if total > a.max_calls:
            raise SystemExit("That is %d calls, above --max-calls %d. Lower --size or raise the cap." % (total, a.max_calls))
        if not a.yes:
            raise SystemExit("This will spend money on your API account. Check Anthropic's current pricing, then add --yes to run.")
    os.makedirs(a.out, exist_ok=True)
    try:
        res = run_arm(cfg, people, offer, os.path.join(a.out, "raw-offer.jsonl"), a.workers, "offer")
        control_agg = None
        if control_n:
            ctrl = run_arm(cfg, people[:control_n], control_offer(offer), os.path.join(a.out, "raw-control.jsonl"), a.workers, "control")
            control_agg = aggregate(ctrl, people, [])
    except Fatal as e:
        raise SystemExit(str(e))
    agg = aggregate(res, people, offer["price_points"])
    meta = {"model": "mock" if a.mock else a.model, "mock": a.mock, "size": a.size, "seed": a.seed}
    write_outputs(a.out, offer, agg, control_agg, res, people, meta)
    print("Done. Open %s" % os.path.join(a.out, "report.html"))
    if control_agg:
        print(control_verdict(control_agg))
    if agg.get("n"):
        print("BUY %s  MAYBE %s  PASS %s  (%d answered, %d failed)" % (pct(agg["buy"]), pct(agg["maybe"]), pct(agg["pass"]), agg["n"], agg["errors"]))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Test a product idea on a panel of simulated Australian customers.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("idea")
    r.add_argument("--size", type=int, default=1000)
    r.add_argument("--seed", type=int, default=48)
    r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--workers", type=int, default=8, help="calls in flight at once")
    r.add_argument("--out", default="panel-out")
    r.add_argument("--mock", action="store_true", help="fake answers, no API, free")
    r.add_argument("--no-control", dest="control", action="store_false")
    r.add_argument("--control-size", type=int, default=200)
    r.add_argument("--max-calls", type=int, default=2500)
    r.add_argument("--yes", action="store_true", help="confirm you are happy to spend on the API")
    r.set_defaults(func=cmd_run)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
