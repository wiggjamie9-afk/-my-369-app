"""All money maths for the app. Plain functions, integer cents, no AI, no floats.

Rules
  * Money is an int number of cents. Quantities are an int number of thousandths
    (2.5 m of pipe = 2500), so nothing here ever touches binary floating point.
  * Percentages are basis points (10% = 1000 bp).
  * Every rounding is half-up to the nearest cent, done once, at the point named.
  * GST is 10% of the ex-GST total, rounded once on the total (not per line).
"""
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

GST_BP = 1000  # Australian GST, 10%


def _round(d):
    return int(Decimal(d).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _int(name, v, minimum=None):
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError("%s must be a whole number, got %r" % (name, v))
    if minimum is not None and v < minimum:
        raise ValueError("%s must be at least %d, got %d" % (name, minimum, v))
    return v


def to_cents(value):
    """'12.345' / 12 / '1,200.50' / '$80' -> cents, half-up. Refuses floats' hidden error by going via str."""
    try:
        d = Decimal(str(value).replace(",", "").replace("$", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError("not a dollar amount: %r" % (value,))
    if not d.is_finite():
        raise ValueError("not a dollar amount: %r" % (value,))
    return _round(d * 100)


def to_milli(value):
    """'2.5' -> 2500 (a quantity in thousandths)."""
    try:
        d = Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError("not a quantity: %r" % (value,))
    if not d.is_finite() or d < 0:
        raise ValueError("not a quantity: %r" % (value,))
    return _round(d * 1000)


def to_bp(percent):
    """'12.5' (percent) -> 1250 basis points."""
    try:
        d = Decimal(str(percent).replace("%", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError("not a percentage: %r" % (percent,))
    if not d.is_finite():
        raise ValueError("not a percentage: %r" % (percent,))
    return _round(d * 100)


def discounted_cost(list_cost_cents, discount_bp):
    """Supplier list cost less the vendor discount = what the part really costs us."""
    _int("list cost", list_cost_cents, 0)
    _int("discount", discount_bp, 0)
    if discount_bp > 10000:
        raise ValueError("discount cannot exceed 100%")
    return _round(Decimal(list_cost_cents) * (10000 - discount_bp) / 10000)


def sell_from_cost(cost_cents, markup_bp):
    """Our cost plus markup = the unit sell price, ex GST."""
    _int("cost", cost_cents, 0)
    _int("markup", markup_bp, 0)
    return _round(Decimal(cost_cents) * (10000 + markup_bp) / 10000)


def extend(unit_cents, qty_milli):
    """Unit price x quantity, rounded once."""
    _int("unit price", unit_cents, 0)
    _int("quantity", qty_milli, 0)
    return _round(Decimal(unit_cents) * qty_milli / 1000)


def gst_on(ex_cents):
    return _round(Decimal(_int("ex-GST amount", ex_cents)) * GST_BP / 10000)


def margin_bp(profit_cents, sell_ex_cents):
    """Net profit as a share of the ex-GST sell price, in basis points. 0 when nothing is sold."""
    if sell_ex_cents <= 0:
        return 0
    return _round(Decimal(profit_cents) * 10000 / sell_ex_cents)


def quote_totals(lines, labour_hours_milli=0, labour_cost_rate_cents=0, labour_sell_rate_cents=0, adjust_cents=0):
    """The whole quote, to the cent.

    lines: dicts with qty_milli, unit_cost_cents, unit_sell_cents and optionally flagged.
    A flagged line, or one with no price, is left out of every total and counted in `unpriced`.
    adjust_cents is the human's own adjustment to the price (may be negative).
    """
    _int("labour hours", labour_hours_milli, 0)
    _int("labour cost rate", labour_cost_rate_cents, 0)
    _int("labour sell rate", labour_sell_rate_cents, 0)
    _int("adjustment", adjust_cents)
    external = materials_sell = unpriced = 0
    for ln in lines:
        if ln.get("flagged") or ln.get("unit_sell_cents") is None or ln.get("unit_cost_cents") is None:
            unpriced += 1
            continue
        external += extend(ln["unit_cost_cents"], ln["qty_milli"])
        materials_sell += extend(ln["unit_sell_cents"], ln["qty_milli"])
    labour_cost = extend(labour_cost_rate_cents, labour_hours_milli)
    labour_sell = extend(labour_sell_rate_cents, labour_hours_milli)
    ex = materials_sell + labour_sell + adjust_cents
    if ex < 0:
        raise ValueError("adjustment would make the quote negative")
    gst = gst_on(ex)
    profit = ex - external - labour_cost
    return {
        "external_cost_cents": external,
        "labour_cost_cents": labour_cost,
        "materials_sell_cents": materials_sell,
        "labour_sell_cents": labour_sell,
        "adjust_cents": adjust_cents,
        "total_ex_gst_cents": ex,
        "gst_cents": gst,
        "total_inc_gst_cents": ex + gst,
        "net_profit_cents": profit,
        "margin_bp": margin_bp(profit, ex),
        "unpriced_lines": unpriced,
    }


def fmt_money(cents):
    """123456 -> '$1,234.56'; negatives as '-$5.00'."""
    _int("amount", cents)
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "%s$%s.%02d" % (sign, format(cents // 100, ","), cents % 100)


def fmt_qty(qty_milli):
    """2500 -> '2.5', 3000 -> '3'."""
    whole, frac = divmod(_int("quantity", qty_milli, 0), 1000)
    return str(whole) if not frac else ("%d.%03d" % (whole, frac)).rstrip("0")


def fmt_percent(bp):
    """2074 -> '20.74%'."""
    sign = "-" if bp < 0 else ""
    bp = abs(bp)
    return "%s%d.%02d%%" % (sign, bp // 100, bp % 100)
