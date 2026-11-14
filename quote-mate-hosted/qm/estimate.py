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
    p = c.get("pricing") or {}
    if not _num(p.get("gstRate")) or not 0 <= p["gstRate"] <= 1:
        bad.append("GST rate should be like 0.10")
    if not _num(p.get("spread")) or not 0 <= p["spread"] < 1:
        bad.append("the range spread must be between 0% and 99%")
    if not _num(p.get("roundTo")) or p["roundTo"] < 1:
        bad.append("rounding must be $1 or more")
    if not _num(p.get("minimumJob")) or p["minimumJob"] < 0:
        bad.append("the minimum job must be zero or more")
    return bad


def _find(items, wanted):
    for item in items:
        if item["id"] == wanted:
            return item
    raise ValueError("unknown choice: %r" % (wanted,))


def estimate(c, type_id, difficulty_id, size_id):
    """-> dict(low, high, type, difficulty, size); whole dollars, GST included."""
    kind, diff, size = _find(c["jobTypes"], type_id), _find(c["difficulty"], difficulty_id), _find(c["sizes"], size_id)
    p = c["pricing"]
    d = lambda v: Decimal(str(v))
    rate_cents = ((d(kind["labourPerUnit"]) + d(kind["materialPerUnit"])) * 100).quantize(Decimal(1), ROUND_HALF_UP)
    gst = Decimal(1) if p.get("ratesIncludeGst") else 1 + d(p["gstRate"])
    step = d(p["roundTo"])
    low = (d(size["min"]) * rate_cents * d(diff["multiplier"]) * (1 - d(p["spread"])) * gst / 100).quantize(Decimal(1), ROUND_HALF_UP)
    high = (d(size["max"]) * rate_cents * d(diff["multiplier"]) * (1 + d(p["spread"])) * gst / 100).quantize(Decimal(1), ROUND_HALF_UP)
    low = (low / step).to_integral_value(ROUND_FLOOR) * step
    high = (high / step).to_integral_value(ROUND_CEILING) * step
    low = max(low, d(p["minimumJob"]))
    high = max(high, low)
    as_int = lambda v: int(v) if v == v.to_integral_value() else float(v)
    return {"low": as_int(low), "high": as_int(high), "type": kind, "difficulty": diff, "size": size}


def money(dollars):
    return "$" + format(int(round(dollars)), ",")
