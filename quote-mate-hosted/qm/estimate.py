"""The pricing sum and config check, server side. Mirrors roof-quote-mate/estimate.js so the price a
homeowner saw is the price recorded with their lead (the server works it out again; it never trusts
a number sent by the browser). tests/ checks the two agree on every combination."""
from decimal import Decimal, ROUND_HALF_UP, ROUND_FLOOR, ROUND_CEILING


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def check_config(c):
    """Everything wrong with a tenant config, in plain words. Empty list = usable."""
    bad = []
    if not isinstance(c, dict):
        return ["the configuration is missing"]
    for group, keys in (("jobTypes", ("labourPerUnit", "materialPerUnit")), ("difficulty", ("multiplier",)), ("sizes", ("min", "max"))):
        items = c.get(group)
        if not isinstance(items, list) or not items:
            bad.append("%s needs at least one entry" % group)
            continue
        seen = set()
        for i, item in enumerate(items, 1):
            where = "%s #%d" % (group, i)
            if not isinstance(item, dict) or not item.get("id") or not str(item.get("label") or "").strip():
                bad.append("%s needs a name" % where)
                continue
            where += " (%s)" % item["label"]
            if item["id"] in seen:
                bad.append("%s repeats an id" % where)
            seen.add(item["id"])
            for k in keys:
                if not _num(item.get(k)) or item[k] < 0:
                    bad.append("%s: %s must be a number, zero or more" % (where, k))
            if group == "sizes" and _num(item.get("min")) and _num(item.get("max")) and item["max"] < item["min"]:
                bad.append("%s: the largest size is smaller than the smallest" % where)
            if group == "difficulty" and item.get("multiplier") == 0:
                bad.append("%s: the multiplier can't be 0" % where)
            if item.get("watch") is not None and (not isinstance(item["watch"], str) or len(item["watch"]) > 300):
                bad.append("%s: the note must be text under 300 letters" % where)
    p = c.get("pricing") or {}
    if not _num(p.get("gstRate")) or not 0 <= p["gstRate"] <= 1:
        bad.append("GST rate should be like 0.10")
    if not _num(p.get("spread")) or not 0 <= p["spread"] < 1:
        bad.append("the range spread must be between 0% and 99%")
    if not _num(p.get("roundTo")) or p["roundTo"] < 1:
        bad.append("rounding must be $1 or more")
    if not _num(p.get("minimumJob")) or p["minimumJob"] < 0:
        bad.append("the minimum job must be zero or more")
    r = p.get("rebate")
    if r:
        if not _num(r.get("perUnit")) or r["perUnit"] < 0:
            bad.append("the rebate amount must be zero or more")
        bands, last = r.get("bands"), 0
        if not isinstance(bands, list) or not bands:
            bad.append("the rebate needs at least one band")
        else:
            for i, band in enumerate(bands, 1):
                if not isinstance(band, dict) or not _num(band.get("upTo")) or band["upTo"] <= last:
                    bad.append("rebate band %d: its limit must be bigger than the band before it" % i)
                else:
                    last = band["upTo"]
                if not isinstance(band, dict) or not _num(band.get("share")) or not 0 <= band["share"] <= 1:
                    bad.append("rebate band %d: its share must be between 0% and 100%%" % i)
    return bad


def _find(items, wanted):
    for item in items:
        if item["id"] == wanted:
            return item
    raise ValueError("unknown choice: %r" % (wanted,))


def _d(v):
    return Decimal(str(v))


def rebate_cents(c, units):
    """A size-based rebate (so many dollars off per unit, tapering by band). Cents; 0 when there is none."""
    r = c["pricing"].get("rebate")
    if not r:
        return Decimal(0)
    start, counted = Decimal(0), Decimal(0)
    for band in r["bands"]:
        counted += max(Decimal(0), min(_d(units), _d(band["upTo"])) - start) * _d(band["share"])
        start = _d(band["upTo"])
    return counted * (_d(r["perUnit"]) * 100).quantize(Decimal(1), ROUND_HALF_UP)


def price_note(c):
    """The words under a price: GST is only mentioned by a business that charges it."""
    bits = []
    if c["pricing"].get("priceSuffix"):
        bits.append(str(c["pricing"]["priceSuffix"]))
    if c["pricing"].get("gstRegistered") is not False:
        bits.append("including GST")
    if c["pricing"].get("rebate"):
        bits.append("after the rebate")
    return ", ".join(bits)


def estimate(c, type_id, difficulty_id, size_id):
    """-> dict(low, high, gross_low, gross_high, rebate_low, rebate_high, type, difficulty, size) in whole dollars.
    low/high is what the customer pays: GST included where it applies, any rebate taken off."""
    kind, diff, size = _find(c["jobTypes"], type_id), _find(c["difficulty"], difficulty_id), _find(c["sizes"], size_id)
    p = c["pricing"]
    whole = lambda v: v.quantize(Decimal(1), ROUND_HALF_UP)
    rate_cents = whole((_d(kind["labourPerUnit"]) + _d(kind["materialPerUnit"])) * 100)
    gst = Decimal(1) if (p.get("gstRegistered") is False or p.get("ratesIncludeGst")) else 1 + _d(p["gstRate"])
    step = _d(p["roundTo"])
    gross_low = _d(size["min"]) * rate_cents * _d(diff["multiplier"]) * (1 - _d(p["spread"])) * gst / 100
    gross_high = _d(size["max"]) * rate_cents * _d(diff["multiplier"]) * (1 + _d(p["spread"])) * gst / 100
    off_low, off_high = rebate_cents(c, size["min"]) / 100, rebate_cents(c, size["max"]) / 100
    down = lambda v: (whole(v) / step).to_integral_value(ROUND_FLOOR) * step
    up = lambda v: (whole(v) / step).to_integral_value(ROUND_CEILING) * step
    near = lambda v: (whole(v) / step).quantize(Decimal(1), ROUND_HALF_UP) * step
    low = max(down(gross_low - off_low), _d(p["minimumJob"]))
    high = max(up(gross_high - off_high), low)
    as_int = lambda v: int(v) if v == v.to_integral_value() else float(v)
    return {"low": as_int(low), "high": as_int(high), "gross_low": as_int(down(gross_low)), "gross_high": as_int(up(gross_high)),
            "rebate_low": as_int(near(off_low)), "rebate_high": as_int(near(off_high)), "type": kind, "difficulty": diff, "size": size}


def money(dollars):
    return "$" + format(int(round(dollars)), ",")
