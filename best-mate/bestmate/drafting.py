"""Turning a job into a draft quote.

Three steps, and only the first may involve an AI:
  1. understand(): read the tradie's words into a small spec (install type, brand, kW, customer).
     Done by a local rule-based reader, or by an OpenAI-compatible model when one is configured.
  2. build_lines(): fixed install recipes turn the spec into line items. Every price is read
     from the parts library. Nothing here asks an AI for a number.
  3. check_ai_items() / scrub_notes(): anything else the model proposed is checked against the
     library. An item that is not in the library is kept as a flagged line with NO price, and
     any dollar figure the model wrote that the library cannot account for is removed and
     reported. A fabricated price is a failure, so it is never shown.
"""
import json
import math
import re
import urllib.error
import urllib.request

from . import money

INSTALL_TYPES = ("single_split", "multi_split", "ducted", "service")
INSTALL_LABEL = {"single_split": "Split system", "multi_split": "Multi-split system",
                 "ducted": "Ducted system", "service": "Service and maintenance"}

_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
          "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
          "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}
_NUM = "|".join(sorted(_WORDS, key=len, reverse=True))
_WORD_NUMBER = re.compile(
    r"\b(%s|\d+)(?:\s+and\s+a\s+(half)|\s+point\s+(%s|\d+))?\b" % (_NUM, _NUM))
_KW = re.compile(r"(?:\b(\d{1,2})\s*(?:x|×|by|of|lots? of)?\s+)?(\d{1,2}(?:\.\d{1,2})?)\s*(?:kw|kilowatts?|k\.w\.?)\b")
_NOT_NAMES = {"the", "a", "this", "that", "install", "split", "ducted", "new", "next", "big", "small", "same",
              "another", "one", "quick", "easy", "little", "service", "my", "our", "his", "her", "their",
              "back", "to", "standard", "simple", "straightforward", "multi", "system", "unit", "kw", "wall", "roof"}
# brands a tradie might say that the library may not stock yet: recognised, so they are never
# silently swapped for the preferred brand
KNOWN_BRANDS = ("Daikin", "Mitsubishi Electric", "Mitsubishi Heavy Industries", "Fujitsu", "Samsung", "Panasonic",
                "LG", "Hitachi", "Toshiba", "Carrier", "Kelvinator", "Gree", "Haier", "Hisense", "Midea", "TCL",
                "ActronAir", "Rinnai", "Braemar", "Bonaire", "Temperzone")
BRAND_ALIASES = {"mitsi": "Mitsubishi Electric", "mitsubishi": "Mitsubishi Electric", "mhi": "Mitsubishi Heavy Industries",
                 "actron": "ActronAir"}


def words_to_numbers(text):
    """'two and a half kw' -> '2.5 kw'; 'seven point one' -> '7.1'. Plain digits pass through."""
    def swap(m):
        whole = _WORDS.get(m.group(1), None)
        whole = int(m.group(1)) if whole is None else whole
        if m.group(2):
            return "%d.5" % whole
        if m.group(3) is not None:
            frac = _WORDS.get(m.group(3))
            return "%d.%s" % (whole, m.group(3) if frac is None else frac)
        return str(whole) if m.group(1) in _WORDS else m.group(0)
    return _WORD_NUMBER.sub(swap, text)


def understand_locally(job, brands, preferred_brands=()):
    """Rule-based reading of a job description. Returns a spec dict and a list of warnings."""
    text = words_to_numbers(" ".join(str(job).lower().split()))
    flags = []

    units = []
    for m in _KW.finditer(text):
        count = min(int(m.group(1)), 8) if m.group(1) else 1
        try:
            kw = money.to_milli(m.group(2))
        except ValueError:
            continue
        if 500 <= kw <= 30000:
            units += [{"kw_milli": kw}] * max(count, 1)

    if re.search(r"\bducted\b", text):
        kind = "ducted"
    elif re.search(r"\b(service|servicing|clean|maintenance)\b", text) and not units:
        kind = "service"
    elif re.search(r"\bmulti\b", text) or len(units) > 1:
        kind = "multi_split"
    elif units or re.search(r"\bsplit\b", text):
        kind = "single_split"
    else:
        kind = "single_split"
        flags.append("Could not tell the installation type from the description. Assumed a split system.")

    brand = ""
    for name in sorted(set(brands) | set(KNOWN_BRANDS), key=len, reverse=True):
        if name and re.search(r"\b%s\b" % re.escape(name.lower()), text):
            brand = name
            break
    if not brand:
        for alias, name in BRAND_ALIASES.items():
            if re.search(r"\b%s\b" % alias, text) and not (alias == "mitsubishi" and "heavy" in text):
                brand = name
                break
    if not brand and kind != "service":
        brand = (list(preferred_brands) or [""])[0]
        flags.append("No brand was mentioned. Used your preferred brand%s." % (" (" + brand + ")" if brand else ""))

    if kind != "service" and not units:
        flags.append("No capacity (kW) was mentioned. Add the unit yourself.")
    if kind == "service":
        m = re.search(r"\b(\d{1,2})\s+(?:units?|systems?|splits?|heads?)\b", text)
        units = [{"kw_milli": 0}] * (min(int(m.group(1)), 20) if m else 1)

    customer = ""
    found = list(re.finditer(r"\b(?:mr|mrs|ms|miss|dr)\.?\s+([a-z][a-z']+)", text)) + \
        list(re.finditer(r"\b([a-z][a-z']+?)(?:'s)?\s+(?:job|place|house|residence)\b", text))
    for m in found:
        word = m.group(1).strip("'")
        if word not in _NOT_NAMES and word not in _WORDS and len(word) > 1:
            customer = word.title()
            break

    spec = {"install_type": kind, "brand": brand,
            "cycle": "cooling_only" if re.search(r"\bcooling[\s-]*only\b", text) else "reverse_cycle",
            "units": units,
            "back_to_back": bool(re.search(r"\bback[\s-]*(?:to|2)[\s-]*back\b", text)),
            "wall_bracket": bool(re.search(r"\bbrackets?\b", text)),
            "customer_name": customer}
    return spec, flags


def clean_spec(raw, brands=()):
    """Force any spec (from the form, the local reader or a model) into the one shape recipes accept."""
    kind = raw.get("install_type")
    if kind not in INSTALL_TYPES:
        raise ValueError("install type must be one of: %s" % ", ".join(INSTALL_TYPES))
    units = []
    for u in (raw.get("units") or [])[:12]:
        kw = u.get("kw_milli") if isinstance(u, dict) else None
        if kw is None and isinstance(u, dict) and u.get("kw") is not None:
            kw = money.to_milli(u["kw"])
        if isinstance(kw, bool) or not isinstance(kw, int) or not 0 <= kw <= 30000:
            raise ValueError("unit capacity must be between 0 and 30 kW")
        count = u.get("count", 1) if isinstance(u, dict) else 1
        count = count if isinstance(count, int) and not isinstance(count, bool) else 1
        units += [{"kw_milli": kw, "room": str(u.get("room", ""))[:40]}] * max(1, min(count, 12))
    brand = str(raw.get("brand") or "").strip()[:60]
    for b in brands:                      # use the library's own spelling of the brand
        if b.lower() == brand.lower():
            brand = b
    return {"install_type": kind, "brand": brand,
            "cycle": "cooling_only" if raw.get("cycle") == "cooling_only" else "reverse_cycle",
            "units": units[:12], "back_to_back": bool(raw.get("back_to_back")),
            "wall_bracket": bool(raw.get("wall_bracket")),
            "customer_name": str(raw.get("customer_name") or "").strip()[:80]}


def _kw(kw_milli):
    return money.fmt_qty(kw_milli) + ("" if kw_milli % 1000 else ".0")


def recipe(spec):
    """The install recipe: what a job of this shape normally needs.
    Returns (items, labour_hours_milli). An item is (category-or-sku lookup, qty_milli)."""
    kind, units, items = spec["install_type"], spec["units"], []
    n = len(units)

    def part(sku, qty):
        items.append({"sku": sku, "qty_milli": int(qty * 1000)})

    def unit(category, kw, at_least=False, label=""):
        items.append({"unit": category, "kw_milli": kw, "at_least": at_least, "qty_milli": 1000, "label": label})

    def pipe(kw, metres):
        part("PIPE-PAIR-6-10" if kw <= 3500 else "PIPE-PAIR-6-12" if kw <= 5000 else "PIPE-PAIR-10-16", metres)

    if kind == "single_split":
        run = 3 if spec["back_to_back"] else 6
        for u in units:
            unit("unit-split", u["kw_milli"], label="wall split system (package)")
            pipe(u["kw_milli"], run)
            part("ELEC-INTER-15", run)
            part("TRK-80-2M", 1 if spec["back_to_back"] else math.ceil(run / 2))
            part("DRN-PVC-20", 3)
        k = max(n, 1)
        part("ELEC-ISO-20", k); part("ELEC-CB-20", k); part("ELEC-TPS-25", 10 * k)
        part("MNT-BRKT" if spec["wall_bracket"] else "MNT-SLAB", k)
        part("CON-SUNDRY", 1)
        return items, (4000 if spec["back_to_back"] else 6000) * k
    if kind == "multi_split":
        total = sum(u["kw_milli"] for u in units)
        unit("unit-multi-outdoor", total, at_least=True, label="multi-split outdoor unit")
        for u in units:
            unit("unit-multi-indoor", u["kw_milli"], label="multi-split indoor wall unit")
            pipe(u["kw_milli"], 8)
            part("ELEC-INTER-15", 8); part("TRK-80-2M", 2); part("DRN-PVC-20", 3)
        part("ELEC-ISO-20", 1); part("ELEC-CB-20", 1); part("ELEC-TPS-25", 12)
        part("MNT-BRKT" if spec["wall_bracket"] else "MNT-SLAB", 1)
        part("CON-SUNDRY", 1)
        return items, 5000 + 3000 * n
    if kind == "ducted":
        for u in units[:1]:
            unit("unit-ducted", u["kw_milli"], label="ducted system (package)")
        outlets, zones = 6, 2
        part("DCT-PLENUM", 1); part("DCT-FLEX-300", 2); part("DCT-FLEX-250", math.ceil(outlets / 2))
        part("DCT-DIFF", outlets); part("DCT-RAG", 1); part("DCT-DAMPER", zones); part("CTL-ZONE", 1)
        part("PIPE-PAIR-10-16", 10); part("ELEC-INTER-15", 10)
        part("ELEC-ISO-20", 1); part("ELEC-CB-20", 1); part("ELEC-TPS-25", 15)
        part("MNT-SLAB", 1); part("DRN-PVC-20", 6); part("CON-SUNDRY", 1)
        return items, 16000
    part("SVC-CALLOUT", 1)
    part("SVC-KIT", max(n, 1))
    return items, 1000 * max(n, 1)


def flagged_line(description, reason, qty_milli=1000, unit="ea"):
    return {"sku": None, "description": description[:300], "unit": unit, "qty_milli": qty_milli,
            "unit_cost_cents": None, "unit_sell_cents": None, "price_status": "none",
            "flagged": True, "flag_reason": reason}


def library_line(store, part, qty_milli, settings=None):
    cost, sell = store.price_part(part, settings)
    return {"sku": part["sku"], "description": part["name"], "unit": part["unit"], "qty_milli": qty_milli,
            "unit_cost_cents": cost, "unit_sell_cents": sell, "price_status": part["price_status"],
            "flagged": False, "flag_reason": ""}


def build_lines(store, spec):
    """Spec -> priced lines, straight from the library. Returns (lines, labour_hours_milli, title, scope)."""
    settings = store.settings()
    items, labour = recipe(spec)
    merged, order = {}, []
    lines = []
    for it in items:
        if "unit" in it:
            part = store.find_unit(it["unit"], spec["brand"], it["kw_milli"], it["at_least"]) if spec["brand"] else None
            if part:
                lines.append(library_line(store, part, it["qty_milli"], settings))
            else:
                what = ("%s %skW %s" % (spec["brand"] or "Unbranded", _kw(it["kw_milli"]), it["label"])).strip()
                lines.append(flagged_line(what, "Not in the parts library. Pick a part or set the price yourself."))
        else:
            if it["sku"] not in merged:
                merged[it["sku"]] = 0
                order.append(it["sku"])
            merged[it["sku"]] += it["qty_milli"]
    for sku in order:
        part = store.part(sku)
        if part:
            lines.append(library_line(store, part, merged[sku], settings))
        else:
            lines.append(flagged_line("Standard install item %s" % sku,
                                      "This standard item is missing from the parts library.", merged[sku]))

    kind, n = spec["install_type"], len(spec["units"])
    sizes = ", ".join("%skW" % _kw(u["kw_milli"]) for u in spec["units"] if u["kw_milli"])
    brand = (spec["brand"] + " ") if spec["brand"] else ""
    if kind == "service":
        title = "Air conditioning service, %d unit%s" % (max(n, 1), "" if n == 1 else "s")
        scope = "Service and clean %d air conditioning unit%s: wash filters, clean coils, check drains, test operation." % (
            max(n, 1), "" if n == 1 else "s")
    else:
        title = "%s%s installation%s" % (brand, INSTALL_LABEL[kind].lower(), " (" + sizes + ")" if sizes else "")
        title = title[0].upper() + title[1:]
        cycle = "cooling only" if spec["cycle"] == "cooling_only" else "reverse cycle"
        scope = "Supply and install %s%s%s, %s%s. Includes refrigeration pipework, electrical connection with isolator, " \
                "condensate drainage, commissioning and removal of rubbish." % (
                    brand, INSTALL_LABEL[kind].lower(), " (" + sizes + ")" if sizes else "", cycle,
                    ", installed back-to-back" if spec["back_to_back"] else "")
    return lines, labour, title, scope


# ---------------------------------------------------------------- the fabrication check

_PRICE = re.compile(r"(?:(?:\b(?:aud|au)\s?)?\$\s?\d[\d,]*(?:\.\d{1,2})?(?:\s?k\b)?|\b\d[\d,]*(?:\.\d{1,2})?\s?(?:dollars|bucks)\b)", re.I)


def _figure_cents(text):
    digits = re.sub(r"[^\d.,k]", "", text.lower())
    thousand = digits.endswith("k")
    try:
        cents = money.to_cents(digits.rstrip("k"))
    except ValueError:
        return None
    return cents * 1000 if thousand else cents


def scrub_notes(text, allowed_cents=()):
    """Remove every dollar figure the library cannot account for. Returns (clean text, figures removed)."""
    allowed, removed = set(allowed_cents), []

    def swap(m):
        cents = _figure_cents(m.group(0))
        if cents is not None and cents in allowed:
            return m.group(0)
        removed.append(m.group(0).strip())
        return "[price removed]"
    return _PRICE.sub(swap, str(text)), removed


def check_ai_items(store, items):
    """Vet line items proposed by a model. Returns (lines, flags).
    In the library -> priced from the library (the model's own number is discarded).
    Not in the library -> kept as a flagged line with no price."""
    lines, flags = [], []
    settings = store.settings()
    for it in (items or [])[:40]:
        if not isinstance(it, dict):
            continue
        desc = " ".join(str(it.get("description") or it.get("name") or "").split())[:200]
        try:
            qty = money.to_milli(it.get("qty", it.get("quantity", 1)) or 1)
        except ValueError:
            qty = 1000
        qty = qty if 0 < qty <= 10_000_000 else 1000
        offered = next((it[k] for k in ("unit_price", "price", "unit_price_cents", "cost", "total") if it.get(k) not in (None, "")), None)
        part = store.part(str(it.get("sku") or "").strip()) if it.get("sku") else None
        if part:
            lines.append(library_line(store, part, qty, settings))
            if offered is not None:
                flags.append("The AI suggested its own price for %s. It was discarded; the library price is used." % part["name"])
        elif desc:
            reason = "Suggested by the AI but not in the parts library, so it has no price."
            if offered is not None:
                reason = "The AI gave a price for this item that is not in the parts library. The price was not shown."
            lines.append(flagged_line(desc, reason, qty, str(it.get("unit") or "ea")[:12]))
    return lines, flags


# ---------------------------------------------------------------- optional: an OpenAI-compatible model

SYSTEM_PROMPT = """You read a tradesperson's spoken job description for an air conditioning quote and return ONLY a JSON object:
{"install_type": "single_split" | "multi_split" | "ducted" | "service",
 "brand": "", "cycle": "reverse_cycle" | "cooling_only", "back_to_back": false, "wall_bracket": false,
 "units": [{"kw": 2.5, "count": 1}], "customer_name": "", "site_address": "",
 "extra_items": [{"description": "", "sku": "", "qty": 1}], "notes": ""}
Rules: never state or guess a price, cost or dollar amount anywhere. Only put a sku in extra_items if it is in the list
you are given. extra_items is only for things the tradie explicitly asked for beyond a standard install. No prose."""


def understand_with_llm(job, cfg, store, timeout=40):
    extras = store.search_parts(limit=200)["items"]
    catalogue = "\n".join("%s | %s" % (p["sku"], p["name"]) for p in extras if not p["category"].startswith("unit-"))[:6000]
    body = {"model": cfg["llm_model"] or "default", "temperature": 0, "messages": [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Known brands: %s\nExtra parts you may reference by sku:\n%s\n\nJob description:\n%s" % (
            ", ".join(store.parts_facets()["brands"]), catalogue, str(job)[:3000])}]}
    headers = {"Content-Type": "application/json"}
    if cfg["llm_key"]:
        headers["Authorization"] = "Bearer " + cfg["llm_key"]
    req = urllib.request.Request(cfg["llm_base_url"].rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        text = json.loads(r.read())["choices"][0]["message"].get("content") or ""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("the model did not return JSON")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("the model did not return an object")
    return data


def draft(store, job_description, cfg):
    """job description -> a checked draft. Never raises for a bad model reply: it falls back to the local reader."""
    job = " ".join(str(job_description or "").split())
    if not job:
        raise ValueError("describe the job first")
    settings, facets = store.settings(), store.parts_facets()
    spec, flags = understand_locally(job, facets["brands"], settings["preferred_brands"])
    engine, ai_items, ai_notes, site = "local", [], "", ""
    if cfg.get("llm_base_url"):
        try:
            data = understand_with_llm(job, cfg, store)
            local = spec
            spec = clean_spec({**data, "install_type": data.get("install_type") if data.get("install_type") in INSTALL_TYPES
                               else local["install_type"]}, facets["brands"])
            if not spec["units"]:
                spec["units"] = local["units"]
            if not spec["brand"]:
                spec["brand"] = local["brand"]
            if not spec["customer_name"]:
                spec["customer_name"] = local["customer_name"]
            flags = [f for f in flags if "brand" not in f.lower() or not data.get("brand")]
            ai_items, ai_notes, site = data.get("extra_items") or [], str(data.get("notes") or ""), str(data.get("site_address") or "")
            engine = "llm"
        except (urllib.error.URLError, OSError, ValueError, KeyError, IndexError, TypeError) as exc:
            flags.append("The AI model could not be used (%s). Drafted with the built-in reader instead." % str(exc)[:80])
    spec = clean_spec(spec, facets["brands"])

    lines, labour, title, scope = build_lines(store, spec)
    extra_lines, extra_flags = check_ai_items(store, ai_items)
    lines += extra_lines
    flags += extra_flags
    allowed = {ln["unit_sell_cents"] for ln in lines if ln["unit_sell_cents"] is not None}
    notes, removed = scrub_notes(ai_notes, allowed)
    if removed:
        flags.append("The AI wrote %d dollar figure%s that the parts library cannot account for (%s). Removed." % (
            len(removed), "" if len(removed) == 1 else "s", ", ".join(removed[:4])))
    return {
        "line_items": [dict(ln, qty=money.fmt_qty(ln["qty_milli"])) for ln in lines],
        "notes": notes[:2000],
        "flags": flags, "spec": spec, "labour_hours_milli": labour, "job_title": title, "scope": scope,
        "customer_name": spec["customer_name"], "site_address": site[:300], "engine": engine,
    }
