"""SQLite storage: settings, vendors, parts library, quotes and their lines.

One short-lived connection per call keeps this safe under the threaded server.
The parts table is indexed for search and paging, so it holds 15,000+ rows
as comfortably as the 50 it ships with.
"""
import csv
import io
import json
import os
import sqlite3
import time
from contextlib import contextmanager

from . import money
from .seed_parts import SEED_PARTS, SEED_VENDORS

SCHEMA = """
CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS vendors(name TEXT PRIMARY KEY, discount_bp INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS parts(
  sku TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT '',
  brand TEXT NOT NULL DEFAULT '',
  vendor TEXT NOT NULL DEFAULT '',
  unit TEXT NOT NULL DEFAULT 'ea',
  cost_cents INTEGER NOT NULL,              -- supplier list cost, before vendor discount
  kw_milli INTEGER,                         -- capacity for units, else NULL
  price_status TEXT NOT NULL DEFAULT 'supplier',   -- placeholder | supplier | manual
  active INTEGER NOT NULL DEFAULT 1,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS parts_name ON parts(name COLLATE NOCASE);
CREATE INDEX IF NOT EXISTS parts_cat ON parts(category, brand, kw_milli);
CREATE TABLE IF NOT EXISTS quotes(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  number TEXT NOT NULL UNIQUE,
  state TEXT NOT NULL DEFAULT 'draft',      -- draft | sent | won | lost
  source TEXT NOT NULL DEFAULT 'manual',    -- manual | form | voice | ai
  customer_name TEXT NOT NULL DEFAULT '',
  customer_phone TEXT NOT NULL DEFAULT '',
  customer_email TEXT NOT NULL DEFAULT '',
  site_address TEXT NOT NULL DEFAULT '',
  job_title TEXT NOT NULL DEFAULT '',
  scope TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  job_description TEXT NOT NULL DEFAULT '', -- what the tradie said or typed
  spec_json TEXT NOT NULL DEFAULT '{}',     -- install type, brand, cycle, units
  flags_json TEXT NOT NULL DEFAULT '[]',    -- quote-level warnings from the drafting check
  labour_hours_milli INTEGER NOT NULL DEFAULT 0,
  labour_cost_rate_cents INTEGER NOT NULL DEFAULT 0,
  labour_sell_rate_cents INTEGER NOT NULL DEFAULT 0,
  adjust_cents INTEGER NOT NULL DEFAULT 0,
  valid_days INTEGER NOT NULL DEFAULT 30,
  reviewed_at INTEGER, sent_at INTEGER, closed_at INTEGER,
  created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS quotes_state ON quotes(state, updated_at);
CREATE TABLE IF NOT EXISTS quote_lines(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  quote_id INTEGER NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  position INTEGER NOT NULL,
  sku TEXT,
  description TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT 'ea',
  qty_milli INTEGER NOT NULL,
  unit_cost_cents INTEGER,                  -- NULL while the line is flagged
  unit_sell_cents INTEGER,
  price_status TEXT NOT NULL DEFAULT 'supplier',   -- placeholder | supplier | manual | none
  flagged INTEGER NOT NULL DEFAULT 0,       -- 1 = no trusted price; left out of every total
  flag_reason TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS lines_quote ON quote_lines(quote_id, position);
CREATE TABLE IF NOT EXISTS events(
  id INTEGER PRIMARY KEY AUTOINCREMENT, quote_id INTEGER, ts INTEGER NOT NULL,
  kind TEXT NOT NULL, detail TEXT NOT NULL DEFAULT '');
"""

DEFAULT_SETTINGS = {
    "business_name": "", "business_abn": "", "business_licence": "", "business_phone": "",
    "business_email": "", "business_address": "",
    "markup_bp": 3000,                 # 30% on materials
    "labour_cost_rate_cents": 6000,    # what an hour costs the business
    "labour_sell_rate_cents": 11000,   # what an hour is charged at, ex GST
    "valid_days": 30,
    "preferred_brands": ["Daikin"],
    "payment_terms": "50% deposit on acceptance, balance on completion. Prices include GST where shown.",
    "quote_footer": "",
}
STATES = ("draft", "sent", "won", "lost")
QUOTE_FIELDS = ("customer_name", "customer_phone", "customer_email", "site_address", "job_title", "scope", "notes")


def now():
    return int(time.time())


class Store:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
        with self.tx() as c:
            c.executescript(SCHEMA)
            if not c.execute("SELECT 1 FROM settings LIMIT 1").fetchone():
                for k, v in DEFAULT_SETTINGS.items():
                    c.execute("INSERT INTO settings VALUES(?,?)", (k, json.dumps(v)))
                c.executemany("INSERT OR IGNORE INTO vendors VALUES(?,?)", SEED_VENDORS)
                for sku, name, cat, brand, vendor, unit, cost, kw in SEED_PARTS:
                    c.execute("INSERT INTO parts(sku,name,category,brand,vendor,unit,cost_cents,kw_milli,price_status,updated_at)"
                              " VALUES(?,?,?,?,?,?,?,?,?,?)",
                              (sku, name, cat, brand, vendor, unit, money.to_cents(cost),
                               money.to_milli(kw) if kw else None, "placeholder", now()))

    @contextmanager
    def tx(self):
        con = sqlite3.connect(self.path, timeout=15)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        con.execute("PRAGMA journal_mode=WAL")
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    # ---------------------------------------------------------------- settings and vendors
    def settings(self):
        with self.tx() as c:
            out = dict(DEFAULT_SETTINGS)
            for r in c.execute("SELECT key, value FROM settings"):
                out[r["key"]] = json.loads(r["value"])
            return out

    def save_settings(self, changes):
        clean = {}
        for k, v in changes.items():
            if k not in DEFAULT_SETTINGS:
                raise ValueError("unknown setting: %s" % k)
            want = DEFAULT_SETTINGS[k]
            if isinstance(want, int):
                if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                    raise ValueError("%s must be a whole number, zero or more" % k)
                if k == "valid_days" and not 1 <= v <= 365:
                    raise ValueError("valid_days must be between 1 and 365")
            elif isinstance(want, list):
                if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
                    raise ValueError("%s must be a list of names" % k)
                v = [x.strip()[:60] for x in v if x.strip()][:20]
            else:
                if not isinstance(v, str):
                    raise ValueError("%s must be text" % k)
                v = v.strip()[:600]
            clean[k] = v
        with self.tx() as c:
            for k, v in clean.items():
                c.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                          (k, json.dumps(v)))
        return self.settings()

    def vendors(self):
        with self.tx() as c:
            return [dict(r) for r in c.execute("SELECT name, discount_bp FROM vendors ORDER BY name COLLATE NOCASE")]

    def save_vendor(self, name, discount_bp):
        name = str(name).strip()[:80]
        if not name:
            raise ValueError("vendor needs a name")
        if isinstance(discount_bp, bool) or not isinstance(discount_bp, int) or not 0 <= discount_bp <= 10000:
            raise ValueError("discount must be between 0% and 100%")
        with self.tx() as c:
            c.execute("INSERT INTO vendors VALUES(?,?) ON CONFLICT(name) DO UPDATE SET discount_bp=excluded.discount_bp",
                      (name, discount_bp))
        return self.vendors()

    # ---------------------------------------------------------------- parts
    def part(self, sku, c=None):
        def get(c):
            r = c.execute("SELECT * FROM parts WHERE sku=? AND active=1", (sku,)).fetchone()
            return dict(r) if r else None
        if c is not None:
            return get(c)
        with self.tx() as c:
            return get(c)

    def search_parts(self, q="", category="", brand="", limit=50, offset=0):
        where, args = ["active=1"], []
        for word in str(q).split()[:6]:
            where.append("(name LIKE ? OR sku LIKE ?)")
            args += ["%" + word + "%"] * 2
        if category:
            where.append("category=?"); args.append(category)
        if brand:
            where.append("brand=?"); args.append(brand)
        limit, offset = max(1, min(int(limit), 200)), max(0, int(offset))
        sql = " FROM parts WHERE " + " AND ".join(where)
        with self.tx() as c:
            total = c.execute("SELECT COUNT(*)" + sql, args).fetchone()[0]
            rows = [dict(r) for r in c.execute("SELECT *" + sql + " ORDER BY category, name COLLATE NOCASE LIMIT ? OFFSET ?",
                                               args + [limit, offset])]
        return {"total": total, "items": rows, "limit": limit, "offset": offset}

    def parts_facets(self):
        with self.tx() as c:
            return {
                "count": c.execute("SELECT COUNT(*) FROM parts WHERE active=1").fetchone()[0],
                "placeholder": c.execute("SELECT COUNT(*) FROM parts WHERE active=1 AND price_status='placeholder'").fetchone()[0],
                "categories": [r[0] for r in c.execute("SELECT DISTINCT category FROM parts WHERE active=1 ORDER BY 1")],
                "brands": [r[0] for r in c.execute("SELECT DISTINCT brand FROM parts WHERE active=1 AND brand<>'' ORDER BY 1")],
            }

    def find_unit(self, category, brand, kw_milli, at_least=False):
        """The library unit for a brand and capacity. at_least picks the smallest that is big enough."""
        with self.tx() as c:
            if at_least:
                r = c.execute("SELECT * FROM parts WHERE active=1 AND category=? AND brand=? COLLATE NOCASE AND kw_milli>=?"
                              " ORDER BY kw_milli LIMIT 1", (category, brand, kw_milli)).fetchone()
            else:
                r = c.execute("SELECT * FROM parts WHERE active=1 AND category=? AND brand=? COLLATE NOCASE AND kw_milli=?"
                              " LIMIT 1", (category, brand, kw_milli)).fetchone()
            return dict(r) if r else None

    def save_part(self, p, status="manual", c=None):
        sku = str(p.get("sku", "")).strip()[:60]
        name = str(p.get("name", "")).strip()[:200]
        if not sku or not name:
            raise ValueError("a part needs a SKU and a name")
        cost = p.get("cost_cents")
        if isinstance(cost, bool) or not isinstance(cost, int) or cost < 0:
            raise ValueError("part %s: cost must be zero or more cents" % sku)
        kw = p.get("kw_milli")
        if kw is not None and (isinstance(kw, bool) or not isinstance(kw, int) or kw <= 0):
            raise ValueError("part %s: kW must be a positive number" % sku)
        row = (sku, name, str(p.get("category", "")).strip()[:40], str(p.get("brand", "")).strip()[:60],
               str(p.get("vendor", "")).strip()[:80], (str(p.get("unit", "")).strip() or "ea")[:12], cost, kw, status, now())

        def put(c):
            c.execute("INSERT INTO parts(sku,name,category,brand,vendor,unit,cost_cents,kw_milli,price_status,updated_at)"
                      " VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(sku) DO UPDATE SET name=excluded.name,"
                      " category=excluded.category, brand=excluded.brand, vendor=excluded.vendor, unit=excluded.unit,"
                      " cost_cents=excluded.cost_cents, kw_milli=excluded.kw_milli, price_status=excluded.price_status,"
                      " active=1, updated_at=excluded.updated_at", row)
            if row[4]:
                c.execute("INSERT OR IGNORE INTO vendors VALUES(?,0)", (row[4],))
        if c is not None:
            put(c)
        else:
            with self.tx() as c:
                put(c)
        return sku

    def import_parts_csv(self, text):
        """Supplier list as CSV with a header row: sku,name,cost and optionally category,brand,vendor,unit,kw.
        All-or-nothing: one bad row and nothing is imported."""
        reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
        if not reader.fieldnames:
            raise ValueError("the CSV is empty")
        heads = {h.strip().lower(): h for h in reader.fieldnames if h}
        missing = [h for h in ("sku", "name", "cost") if h not in heads]
        if missing:
            raise ValueError("CSV needs columns sku, name, cost (missing: %s)" % ", ".join(missing))
        get = lambda row, k: (row.get(heads[k]) or "").strip() if k in heads else ""
        n = 0
        with self.tx() as c:
            for i, row in enumerate(reader, start=2):
                if not any((v or "").strip() for v in row.values()):
                    continue
                try:
                    kw = get(row, "kw")
                    self.save_part({"sku": get(row, "sku"), "name": get(row, "name"),
                                    "cost_cents": money.to_cents(get(row, "cost")),
                                    "category": get(row, "category"), "brand": get(row, "brand"),
                                    "vendor": get(row, "vendor"), "unit": get(row, "unit"),
                                    "kw_milli": money.to_milli(kw) if kw else None}, status="supplier", c=c)
                except ValueError as exc:
                    raise ValueError("row %d: %s" % (i, exc))
                n += 1
            if not n:
                raise ValueError("the CSV has no part rows")
        return n

    # ---------------------------------------------------------------- pricing a part for a quote line
    def price_part(self, part, settings=None, c=None):
        """(unit cost after vendor discount, unit sell ex GST) for a library part, right now."""
        settings = settings or self.settings()

        def disc(c):
            r = c.execute("SELECT discount_bp FROM vendors WHERE name=?", (part["vendor"],)).fetchone()
            return r[0] if r else 0
        if c is not None:
            d = disc(c)
        else:
            with self.tx() as c2:
                d = disc(c2)
        cost = money.discounted_cost(part["cost_cents"], d)
        return cost, money.sell_from_cost(cost, settings["markup_bp"])

    # ---------------------------------------------------------------- quotes
    def _next_number(self, c):
        year = time.strftime("%Y")
        r = c.execute("SELECT value FROM settings WHERE key=?", ("seq_" + year,)).fetchone()
        n = (json.loads(r[0]) if r else 0) + 1
        c.execute("INSERT INTO settings VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                  ("seq_" + year, json.dumps(n)))
        return "Q-%s-%04d" % (year, n)

    def create_quote(self, header, lines, source="manual"):
        """header: customer/job fields plus spec, flags, labour_hours_milli. lines: ready-made line dicts."""
        s = self.settings()
        t = now()
        with self.tx() as c:
            number = self._next_number(c)
            cur = c.execute(
                "INSERT INTO quotes(number,state,source,customer_name,customer_phone,customer_email,site_address,job_title,"
                "scope,notes,job_description,spec_json,flags_json,labour_hours_milli,labour_cost_rate_cents,"
                "labour_sell_rate_cents,valid_days,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (number, "draft", source, *[str(header.get(k, ""))[:2000] for k in QUOTE_FIELDS],
                 str(header.get("job_description", ""))[:4000], json.dumps(header.get("spec", {})),
                 json.dumps(header.get("flags", [])), int(header.get("labour_hours_milli", 0)),
                 s["labour_cost_rate_cents"], s["labour_sell_rate_cents"], s["valid_days"], t, t))
            qid = cur.lastrowid
            for i, ln in enumerate(lines):
                self._insert_line(c, qid, i, ln)
            c.execute("INSERT INTO events(quote_id,ts,kind,detail) VALUES(?,?,?,?)", (qid, t, "created", source))
        return qid

    @staticmethod
    def _insert_line(c, qid, position, ln):
        c.execute("INSERT INTO quote_lines(quote_id,position,sku,description,unit,qty_milli,unit_cost_cents,unit_sell_cents,"
                  "price_status,flagged,flag_reason) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                  (qid, position, ln.get("sku"), str(ln["description"])[:300], ln.get("unit") or "ea", int(ln["qty_milli"]),
                   ln.get("unit_cost_cents"), ln.get("unit_sell_cents"), ln.get("price_status", "supplier"),
                   1 if ln.get("flagged") else 0, str(ln.get("flag_reason", ""))[:300]))

    def quote(self, qid):
        with self.tx() as c:
            r = c.execute("SELECT * FROM quotes WHERE id=?", (qid,)).fetchone()
            if not r:
                return None
            q = dict(r)
            q["spec"] = json.loads(q.pop("spec_json") or "{}")
            q["flags"] = json.loads(q.pop("flags_json") or "[]")
            q["lines"] = [dict(x) for x in c.execute("SELECT * FROM quote_lines WHERE quote_id=? ORDER BY position, id", (qid,))]
        q["totals"] = money.quote_totals(q["lines"], q["labour_hours_milli"], q["labour_cost_rate_cents"],
                                         q["labour_sell_rate_cents"], q["adjust_cents"])
        q["placeholder_lines"] = sum(1 for ln in q["lines"] if not ln["flagged"] and ln["price_status"] == "placeholder")
        return q

    def list_quotes(self, state=""):
        with self.tx() as c:
            ids = [r[0] for r in c.execute(
                "SELECT id FROM quotes" + (" WHERE state=?" if state else "") + " ORDER BY updated_at DESC, id DESC LIMIT 300",
                (state,) if state else ())]
        out = []
        for qid in ids:
            q = self.quote(qid)
            out.append({k: q[k] for k in ("id", "number", "state", "source", "customer_name", "site_address", "job_title",
                                          "updated_at", "created_at", "sent_at", "placeholder_lines")}
                       | {"total_inc_gst_cents": q["totals"]["total_inc_gst_cents"],
                          "total_ex_gst_cents": q["totals"]["total_ex_gst_cents"],
                          "flagged_lines": q["totals"]["unpriced_lines"]})
        return out

    def _draft(self, c, qid):
        r = c.execute("SELECT state FROM quotes WHERE id=?", (qid,)).fetchone()
        if not r:
            raise LookupError("no such quote")
        if r["state"] != "draft":
            raise PermissionError("this quote has been sent. Reopen it as a draft to change it.")

    def _touch(self, c, qid):
        # any change to a draft means it has to be reviewed again before it can be sent
        c.execute("UPDATE quotes SET updated_at=?, reviewed_at=NULL WHERE id=?", (now(), qid))

    def update_quote(self, qid, changes):
        sets, args = [], []
        for k, v in changes.items():
            if k in QUOTE_FIELDS:
                sets.append(k + "=?"); args.append(str(v)[:2000])
            elif k in ("labour_hours_milli", "labour_cost_rate_cents", "labour_sell_rate_cents"):
                if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                    raise ValueError("%s must be zero or more" % k)
                sets.append(k + "=?"); args.append(v)
            elif k == "adjust_cents":
                if isinstance(v, bool) or not isinstance(v, int):
                    raise ValueError("adjustment must be a whole number of cents")
                sets.append(k + "=?"); args.append(v)
            elif k == "valid_days":
                if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 365:
                    raise ValueError("valid_days must be between 1 and 365")
                sets.append(k + "=?"); args.append(v)
            else:
                raise ValueError("cannot change %s" % k)
        with self.tx() as c:
            self._draft(c, qid)
            if sets:
                c.execute("UPDATE quotes SET %s WHERE id=?" % ", ".join(sets), args + [qid])
            self._touch(c, qid)
        q = self.quote(qid)          # raises if the adjustment drives the total below zero
        return q

    def add_line(self, qid, ln):
        with self.tx() as c:
            self._draft(c, qid)
            pos = c.execute("SELECT COALESCE(MAX(position),-1)+1 FROM quote_lines WHERE quote_id=?", (qid,)).fetchone()[0]
            self._insert_line(c, qid, pos, ln)
            self._touch(c, qid)
        return self.quote(qid)

    def update_line(self, qid, lid, changes):
        with self.tx() as c:
            self._draft(c, qid)
            if not c.execute("SELECT 1 FROM quote_lines WHERE id=? AND quote_id=?", (lid, qid)).fetchone():
                raise LookupError("no such line")
            sets, args = [], []
            for k, v in changes.items():
                if k not in ("sku", "description", "unit", "qty_milli", "unit_cost_cents", "unit_sell_cents",
                             "price_status", "flagged", "flag_reason"):
                    raise ValueError("cannot change %s" % k)
                sets.append(k + "=?"); args.append(v)
            if sets:
                c.execute("UPDATE quote_lines SET %s WHERE id=?" % ", ".join(sets), args + [lid])
            self._touch(c, qid)
        return self.quote(qid)

    def delete_line(self, qid, lid):
        with self.tx() as c:
            self._draft(c, qid)
            c.execute("DELETE FROM quote_lines WHERE id=? AND quote_id=?", (lid, qid))
            self._touch(c, qid)
        return self.quote(qid)

    def clear_flags(self, qid):
        with self.tx() as c:
            self._draft(c, qid)
            c.execute("UPDATE quotes SET flags_json='[]' WHERE id=?", (qid,))
            self._touch(c, qid)
        return self.quote(qid)

    def send(self, qid, reviewed, prices_checked):
        """The only way out of DRAFT. A person must have reviewed it; nothing unpriced may remain."""
        q = self.quote(qid)
        if not q:
            raise LookupError("no such quote")
        if q["state"] != "draft":
            raise PermissionError("only a draft can be sent")
        if reviewed is not True:
            raise PermissionError("a person must review the quote before it is sent")
        if q["totals"]["unpriced_lines"]:
            raise ValueError("%d line(s) have no trusted price. Pick a part or set a price first." % q["totals"]["unpriced_lines"])
        if q["flags"]:
            raise ValueError("clear the %d drafting warning(s) first" % len(q["flags"]))
        if not q["lines"] and not q["labour_hours_milli"]:
            raise ValueError("the quote is empty")
        if q["placeholder_lines"] and prices_checked is not True:
            raise ValueError("%d line(s) use placeholder prices. Confirm you have checked them." % q["placeholder_lines"])
        if not q["customer_name"].strip():
            raise ValueError("add the customer's name first")
        t = now()
        with self.tx() as c:
            c.execute("UPDATE quotes SET state='sent', reviewed_at=?, sent_at=?, updated_at=? WHERE id=? AND state='draft'",
                      (t, t, t, qid))
            c.execute("INSERT INTO events(quote_id,ts,kind,detail) VALUES(?,?,?,?)", (qid, t, "sent", "reviewed by a person"))
        return self.quote(qid)

    def set_state(self, qid, state):
        if state not in ("draft", "won", "lost"):
            raise ValueError("state must be draft, won or lost")
        t = now()
        with self.tx() as c:
            r = c.execute("SELECT state FROM quotes WHERE id=?", (qid,)).fetchone()
            if not r:
                raise LookupError("no such quote")
            if state in ("won", "lost") and r["state"] == "draft":
                raise PermissionError("send the quote before marking it won or lost")
            if state == "draft":      # reopening always clears the review
                c.execute("UPDATE quotes SET state='draft', reviewed_at=NULL, sent_at=NULL, closed_at=NULL, updated_at=? WHERE id=?",
                          (t, qid))
            else:
                c.execute("UPDATE quotes SET state=?, closed_at=?, updated_at=? WHERE id=?", (state, t, t, qid))
            c.execute("INSERT INTO events(quote_id,ts,kind,detail) VALUES(?,?,?,?)", (qid, t, state, ""))
        return self.quote(qid)

    def delete_quote(self, qid):
        with self.tx() as c:
            self._draft(c, qid)
            c.execute("DELETE FROM quotes WHERE id=?", (qid,))

    # ---------------------------------------------------------------- pipeline (for the Jarvis panel)
    def pipeline(self):
        quotes = self.list_quotes()
        states = {s: {"count": 0, "total_inc_gst_cents": 0} for s in STATES}
        for q in quotes:
            states[q["state"]]["count"] += 1
            states[q["state"]]["total_inc_gst_cents"] += q["total_inc_gst_cents"]
        closed = states["won"]["count"] + states["lost"]["count"]
        with self.tx() as c:
            events = [dict(r) for r in c.execute(
                "SELECT e.ts, e.kind, e.detail, q.number, q.customer_name, q.id AS quote_id FROM events e"
                " LEFT JOIN quotes q ON q.id=e.quote_id ORDER BY e.id DESC LIMIT 12")]
        return {"states": states, "win_rate_bp": money.margin_bp(states["won"]["count"], closed) if closed else None,
                "needs_attention": [q for q in quotes if q["state"] == "draft" and (q["flagged_lines"] or q["placeholder_lines"])][:8],
                "recent": events}
