"""A small PDF writer and the quote layout. Standard library only.

It writes PDF 1.4 by hand: the two built-in Helvetica faces, filled rectangles, lines, and one
JPEG (the logo mark, embedded untouched). Text is measured with the real Helvetica widths so
prices right-align to the point. Every figure printed comes from money.quote_totals.
"""
import zlib

from . import money

A4 = (595.28, 841.89)

# Helvetica and Helvetica-Bold advance widths for characters 32..126 (1000 units per em)
_W = [278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556,
      556, 556, 556, 278, 278, 584, 584, 584, 556, 1015, 667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833,
      722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 278, 278, 278, 469, 556, 333, 556, 556, 500, 556,
      556, 278, 556, 556, 222, 222, 500, 222, 833, 556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500, 334,
      260, 334, 584]
_WB = [278, 333, 474, 556, 556, 889, 722, 238, 333, 333, 389, 584, 278, 333, 278, 278, 556, 556, 556, 556, 556, 556, 556,
       556, 556, 556, 333, 333, 584, 584, 584, 611, 975, 722, 722, 722, 722, 667, 611, 778, 722, 278, 556, 722, 611, 833,
       722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611, 333, 278, 333, 584, 556, 333, 556, 611, 556, 611,
       556, 333, 611, 611, 278, 278, 556, 278, 889, 611, 611, 611, 611, 389, 556, 333, 611, 556, 778, 556, 556, 500, 389,
       280, 389, 584]


def _enc(text):
    return str(text).replace("—", "-").replace("–", "-").encode("cp1252", "replace")


def text_width(text, size, bold=False):
    table = _WB if bold else _W
    return sum(table[b - 32] if 32 <= b <= 126 else 556 for b in _enc(text)) * size / 1000.0


def wrap(text, size, width, bold=False):
    out = []
    for para in str(text).replace("\r", "").split("\n"):
        line = ""
        for word in para.split():
            trial = (line + " " + word).strip()
            if line and text_width(trial, size, bold) > width:
                out.append(line)
                line = word
            else:
                line = trial
            while text_width(line, size, bold) > width and len(line) > 1:      # one very long word
                cut = len(line) - 1
                while cut > 1 and text_width(line[:cut], size, bold) > width:
                    cut -= 1
                out.append(line[:cut])
                line = line[cut:]
        out.append(line)
    return out or [""]


def jpeg_size(data):
    """(width, height, components) of a JPEG, read from its frame header."""
    if data[:2] != b"\xff\xd8":
        raise ValueError("not a JPEG")
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            return (int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big"), data[i + 9])
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    raise ValueError("JPEG has no frame header")


class Document:
    """Pages are drawn top-down: y is the distance from the top edge, in points."""

    def __init__(self, title="", author=""):
        self.pages, self.image, self.title, self.author = [], None, title, author
        self.w, self.h = A4

    def add_page(self):
        self.pages.append([])

    def _put(self, s):
        self.pages[-1].append(s if isinstance(s, bytes) else s.encode("latin-1"))

    def rect(self, x, y, w, h, rgb):
        self._put("%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f\n" % (*rgb, x, self.h - y - h, w, h))

    def line(self, x1, y1, x2, y2, rgb=(0.8, 0.8, 0.8), width=0.6):
        self._put("%.3f %.3f %.3f RG %.2f w %.2f %.2f m %.2f %.2f l S\n" % (*rgb, width, x1, self.h - y1, x2, self.h - y2))

    def text(self, x, y, s, size=10, bold=False, rgb=(0.1, 0.1, 0.12), align="left"):
        """y is the baseline. align right/center positions the text against x."""
        if align != "left":
            w = text_width(s, size, bold)
            x -= w if align == "right" else w / 2
        raw = _enc(s).replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        self._put(b"BT /F%d %.2f Tf %.3f %.3f %.3f rg %.2f %.2f Td (" % (2 if bold else 1, size, *rgb, x, self.h - y)
                  + raw + b") Tj ET\n")

    def watermark(self, s, size=120, rgb=(0.93, 0.93, 0.95)):
        c = 0.7071
        raw = _enc(s)
        self._put(b"q %.4f %.4f %.4f %.4f %.2f %.2f cm BT /F2 %d Tf %.3f %.3f %.3f rg 0 0 Td (" % (
            c, c, -c, c, self.w / 2 - 190, self.h / 2 - 250, size, *rgb) + raw + b") Tj ET Q\n")

    def set_image(self, jpeg):
        self.image = (jpeg,) + jpeg_size(jpeg)

    def draw_image(self, x, y, w, h):
        if self.image:
            self._put("q %.2f 0 0 %.2f %.2f %.2f cm /Im1 Do Q\n" % (w, h, x, self.h - y - h))

    def build(self):
        objs = []                                   # object n is objs[n-1]

        def add(body):
            objs.append(body if isinstance(body, bytes) else body.encode("latin-1"))
            return len(objs)

        add(b"")                                    # 1 catalog (filled in below)
        add(b"")                                    # 2 pages
        f1 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
        f2 = add("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
        resources = "/Font << /F1 %d 0 R /F2 %d 0 R >>" % (f1, f2)
        if self.image:
            data, iw, ih, comps = self.image
            im = add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace /%s /BitsPerComponent 8 "
                     b"/Filter /DCTDecode /Length %d >>\nstream\n" % (
                         iw, ih, b"DeviceRGB" if comps == 3 else b"DeviceGray" if comps == 1 else b"DeviceCMYK",
                         len(data)) + data + b"\nendstream")
            resources += " /XObject << /Im1 %d 0 R >>" % im
        kids = []
        for content in self.pages:
            stream = zlib.compress(b"".join(content))
            c = add(b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(stream) + stream + b"\nendstream")
            kids.append(add("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources << %s >> /Contents %d 0 R >>"
                            % (self.w, self.h, resources, c)))
        objs[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
        objs[1] = ("<< /Type /Pages /Count %d /Kids [%s] >>" % (len(kids), " ".join("%d 0 R" % k for k in kids))).encode()
        esc = lambda t: _enc(t).replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
        info = add(b"<< /Title (" + esc(self.title) + b") /Author (" + esc(self.author) + b") /Producer (The 48 - AI's Best Mate) >>")

        out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        offsets = []
        for n, body in enumerate(objs, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % n + body + b"\nendobj\n"
        xref = len(out)
        out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
        for off in offsets:
            out += b"%010d 00000 n \n" % off
        out += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, info, xref)
        return bytes(out)


# ---------------------------------------------------------------- the quote

INK, MUTED, RULE = (0.09, 0.10, 0.13), (0.42, 0.45, 0.50), (0.85, 0.87, 0.90)
NIGHT, CYAN, ORANGE, PALE = (0.02, 0.03, 0.05), (0.10, 0.83, 1.0), (1.0, 0.54, 0.12), (0.955, 0.965, 0.975)
LEFT, RIGHT, BOTTOM = 42.0, A4[0] - 42.0, A4[1] - 64.0


def _date(ts):
    import time
    return time.strftime("%d %b %Y", time.localtime(ts)).lstrip("0")


def quote_pdf(q, settings, logo_jpeg=None):
    """Render a quote (as returned by Store.quote) to PDF bytes. A draft is watermarked DRAFT."""
    t = q["totals"]
    business = settings.get("business_name") or "Your business name"
    doc = Document(title="Quote %s" % q["number"], author=business)
    if logo_jpeg:
        doc.set_image(logo_jpeg)
    state = {"y": 0.0}

    def new_page(first=False):
        doc.add_page()
        if q["state"] == "draft":
            doc.watermark("DRAFT")
        if first:
            doc.rect(0, 0, doc.w, 128, NIGHT)
            doc.rect(0, 128, doc.w, 3, CYAN)
            x = LEFT
            if logo_jpeg:
                doc.draw_image(LEFT, 24, 80, 80)
                x = LEFT + 96
            doc.text(x, 56, business, 18, True, (1, 1, 1))
            y = 74
            details = [d for d in (settings.get("business_address"),
                                   " | ".join(d for d in (settings.get("business_phone"), settings.get("business_email")) if d),
                                   " | ".join(d for d in ("ABN " + settings["business_abn"] if settings.get("business_abn") else "",
                                                          "Licence " + settings["business_licence"] if settings.get("business_licence") else "") if d)) if d]
            for d in details:
                for ln in wrap(d, 9, 260)[:2]:
                    doc.text(x, y, ln, 9, False, (0.78, 0.82, 0.88))
                    y += 12
            doc.text(RIGHT, 52, "QUOTE", 22, True, CYAN, "right")
            doc.text(RIGHT, 70, q["number"], 11, True, (1, 1, 1), "right")
            doc.text(RIGHT, 86, "Date  %s" % _date(q["sent_at"] or q["updated_at"]), 9, False, (0.78, 0.82, 0.88), "right")
            doc.text(RIGHT, 99, "Valid until  %s" % _date((q["sent_at"] or q["updated_at"]) + q["valid_days"] * 86400),
                     9, False, (0.78, 0.82, 0.88), "right")
            state["y"] = 158
        else:
            doc.rect(0, 0, doc.w, 30, NIGHT)
            doc.text(LEFT, 20, business, 9, True, (1, 1, 1))
            doc.text(RIGHT, 20, "Quote %s" % q["number"], 9, False, (0.78, 0.82, 0.88), "right")
            state["y"] = 58

    def need(height):
        if state["y"] + height > BOTTOM:
            new_page()

    def heading(label):
        need(40)
        doc.text(LEFT, state["y"], label.upper(), 8, True, (0.0, 0.50, 0.66))
        doc.line(LEFT, state["y"] + 5, RIGHT, state["y"] + 5, RULE)
        state["y"] += 20

    def paragraph(text, size=10, width=RIGHT - LEFT, rgb=INK, lead=None):
        lead = lead or size * 1.4
        for ln in wrap(text, size, width):
            need(lead)
            doc.text(LEFT, state["y"], ln, size, False, rgb)
            state["y"] += lead

    new_page(first=True)

    # who and where
    heading("Prepared for")
    y0 = state["y"]
    doc.text(LEFT, y0, q["customer_name"] or "Customer", 12, True)
    y = y0 + 15
    for d in (q["customer_phone"], q["customer_email"]):
        if d:
            doc.text(LEFT, y, d, 9.5, False, MUTED)
            y += 13
    mid = LEFT + (RIGHT - LEFT) / 2
    doc.text(mid, y0 - 20, "SITE ADDRESS", 8, True, (0.0, 0.50, 0.66))
    y2 = y0
    for ln in wrap(q["site_address"] or "To be confirmed", 10, RIGHT - mid)[:4]:
        doc.text(mid, y2, ln, 10)
        y2 += 14
    state["y"] = max(y, y2) + 14

    if q["job_title"]:
        need(30)
        for ln in wrap(q["job_title"], 15, RIGHT - LEFT, True)[:2]:
            doc.text(LEFT, state["y"], ln, 15, True)
            state["y"] += 20
        state["y"] += 2
    if q["scope"]:
        heading("Scope of works")
        paragraph(q["scope"])
        state["y"] += 10

    units = [u for u in q["spec"].get("units", []) if u.get("kw_milli")]
    if units:
        heading("System summary")
        total_kw = sum(u["kw_milli"] for u in units)
        cells = [("%d" % len(units), "indoor unit%s" % ("" if len(units) == 1 else "s")),
                 (money.fmt_qty(total_kw) + " kW", "combined capacity"),
                 (q["spec"].get("brand") or "-", "brand"),
                 ("Cooling only" if q["spec"].get("cycle") == "cooling_only" else "Reverse cycle", "operation")]
        need(52)
        cw = (RIGHT - LEFT - 18) / 4
        for i, (big, small) in enumerate(cells):
            x = LEFT + i * (cw + 6)
            doc.rect(x, state["y"] - 12, cw, 44, PALE)
            size = 13
            while text_width(big, size, True) > cw - 16 and size > 8:
                size -= 1
            doc.text(x + 8, state["y"] + 6, big, size, True)
            doc.text(x + 8, state["y"] + 22, small, 8, False, MUTED)
        state["y"] += 50

    # price breakdown
    heading("Price breakdown")
    cols = (LEFT, RIGHT - 190, RIGHT - 150, RIGHT - 78, RIGHT)        # description | qty | unit | unit price | total

    def table_head():
        need(26)
        doc.rect(LEFT, state["y"] - 11, RIGHT - LEFT, 18, NIGHT)
        doc.text(cols[0] + 6, state["y"] + 1, "Item", 8, True, (1, 1, 1))
        doc.text(cols[1] + 22, state["y"] + 1, "Qty", 8, True, (1, 1, 1), "right")
        doc.text(cols[2] + 6, state["y"] + 1, "Unit", 8, True, (1, 1, 1))
        doc.text(cols[3] + 2, state["y"] + 1, "Unit price", 8, True, (1, 1, 1), "right")
        doc.text(cols[4] - 6, state["y"] + 1, "Amount", 8, True, (1, 1, 1), "right")
        state["y"] += 21

    def row(desc, qty, unit, unit_price, amount, shade):
        lines = wrap(desc, 9.5, cols[1] - cols[0] - 30)
        height = 13 * len(lines) + 5
        if state["y"] + height > BOTTOM:
            new_page()
            table_head()
        if shade:
            doc.rect(LEFT, state["y"] - 10, RIGHT - LEFT, height, PALE)
        for i, ln in enumerate(lines):
            doc.text(cols[0] + 6, state["y"] + 13 * i, ln, 9.5)
        doc.text(cols[1] + 22, state["y"], qty, 9.5, False, INK, "right")
        doc.text(cols[2] + 6, state["y"], unit, 9.5, False, MUTED)
        doc.text(cols[3] + 2, state["y"], unit_price, 9.5, False, INK, "right")
        doc.text(cols[4] - 6, state["y"], amount, 9.5, False, INK, "right")
        state["y"] += height

    table_head()
    n = 0
    for ln in q["lines"]:
        if ln["flagged"] or ln["unit_sell_cents"] is None:
            continue                                                  # an unpriced line never reaches a customer
        row(ln["description"], money.fmt_qty(ln["qty_milli"]), ln["unit"], money.fmt_money(ln["unit_sell_cents"]),
            money.fmt_money(money.extend(ln["unit_sell_cents"], ln["qty_milli"])), n % 2 == 1)
        n += 1
    if q["labour_hours_milli"]:
        row("Installation labour", money.fmt_qty(q["labour_hours_milli"]), "hr", money.fmt_money(q["labour_sell_rate_cents"]),
            money.fmt_money(t["labour_sell_cents"]), n % 2 == 1)
        n += 1
    if t["adjust_cents"]:
        row("Adjustment", "", "", "", money.fmt_money(t["adjust_cents"]), n % 2 == 1)

    need(92)
    state["y"] += 8
    box = RIGHT - 230
    for label, value in (("Subtotal (ex GST)", t["total_ex_gst_cents"]), ("GST (10%)", t["gst_cents"])):
        doc.text(box, state["y"], label, 10, False, MUTED)
        doc.text(RIGHT - 6, state["y"], money.fmt_money(value), 10, False, INK, "right")
        state["y"] += 16
    doc.rect(box - 10, state["y"] - 8, RIGHT - box + 10, 30, NIGHT)
    doc.text(box, state["y"] + 11, "Total (inc GST)", 11, True, (1, 1, 1))
    doc.text(RIGHT - 8, state["y"] + 12, money.fmt_money(t["total_inc_gst_cents"]), 15, True, CYAN, "right")
    state["y"] += 44

    if q["notes"]:
        heading("Notes")
        paragraph(q["notes"])
        state["y"] += 8
    terms = "\n".join(x for x in (settings.get("payment_terms"), "This quote is valid for %d days from the date shown." % q["valid_days"],
                                  settings.get("quote_footer")) if x)
    heading("Terms")
    paragraph(terms, 9, rgb=MUTED)

    every_page = doc.pages
    for i, content in enumerate(every_page):
        doc.pages = [content]                                         # draw the footer onto this page
        doc.line(LEFT, A4[1] - 44, RIGHT, A4[1] - 44, RULE)
        doc.text(LEFT, A4[1] - 30, "%s  |  Quote %s" % (business, q["number"]), 8, False, MUTED)
        doc.text(RIGHT, A4[1] - 30, "Page %d of %d" % (i + 1, len(every_page)), 8, False, MUTED, "right")
    doc.pages = every_page
    return doc.build()
