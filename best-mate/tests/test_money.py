"""Money maths. Every expected figure below was worked out by hand, to the cent.
Run: python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bestmate import money as m


class Parsing(unittest.TestCase):
    def test_dollars_to_cents_rounds_half_up(self):
        self.assertEqual(m.to_cents("12.345"), 1235)
        self.assertEqual(m.to_cents("12.344"), 1234)
        self.assertEqual(m.to_cents("$1,200.50"), 120050)
        self.assertEqual(m.to_cents(80), 8000)
        self.assertEqual(m.to_cents("-50"), -5000)
        self.assertEqual(m.to_cents("0.1") + m.to_cents("0.2"), 30)          # the float trap: 0.1 + 0.2

    def test_rubbish_is_refused(self):
        for bad in ("", "abc", "1.2.3", "NaN", "Infinity", None):
            with self.assertRaises(ValueError):
                m.to_cents(bad)
        for bad in ("", "-1", "lots", "NaN"):
            with self.assertRaises(ValueError):
                m.to_milli(bad)

    def test_quantities_and_percentages(self):
        self.assertEqual(m.to_milli("2.5"), 2500)
        self.assertEqual(m.to_milli(10), 10000)
        self.assertEqual(m.to_bp("12.5"), 1250)
        self.assertEqual(m.to_bp("30%"), 3000)


class Pricing(unittest.TestCase):
    def test_vendor_discount(self):
        self.assertEqual(m.discounted_cost(100000, 1250), 87500)             # $1,000 less 12.5%
        self.assertEqual(m.discounted_cost(999, 3333), 666)                  # 999 x 0.6667 = 666.03
        self.assertEqual(m.discounted_cost(5000, 0), 5000)
        self.assertEqual(m.discounted_cost(5000, 10000), 0)
        with self.assertRaises(ValueError):
            m.discounted_cost(5000, 10001)

    def test_markup(self):
        self.assertEqual(m.sell_from_cost(90000, 3000), 117000)              # $900 + 30%
        self.assertEqual(m.sell_from_cost(333, 3333), 444)                   # 333 x 1.3333 = 443.99
        self.assertEqual(m.sell_from_cost(1, 5000), 2)                       # 1.5c rounds half-up to 2c
        self.assertEqual(m.sell_from_cost(0, 3000), 0)

    def test_extension_rounds_once(self):
        self.assertEqual(m.extend(1560, 3000), 4680)                         # 3 m at $15.60
        self.assertEqual(m.extend(333, 2500), 833)                           # 2.5 x $3.33 = $8.325 -> $8.33
        self.assertEqual(m.extend(1, 500), 1)                                # half a cent rounds up
        self.assertEqual(m.extend(1, 499), 0)

    def test_floats_and_negatives_are_refused(self):
        for args in ((10.5, 1000), (-1, 1000), (100, -1), (True, 1000)):
            with self.assertRaises(ValueError):
                m.extend(*args)


class Gst(unittest.TestCase):
    def test_ten_percent_rounded_once_on_the_total(self):
        self.assertEqual(m.gst_on(192135), 19214)                            # $1,921.35 -> $192.135 -> $192.14
        self.assertEqual(m.gst_on(100000), 10000)
        self.assertEqual(m.gst_on(5), 1)                                     # 0.5c rounds up
        self.assertEqual(m.gst_on(4), 0)
        self.assertEqual(m.gst_on(0), 0)

    def test_gst_is_not_summed_per_line(self):
        # three lines of $0.05: per-line GST would be 1c each (3c); on the total it is 1.5c -> 2c
        lines = [{"qty_milli": 1000, "unit_cost_cents": 0, "unit_sell_cents": 5}] * 3
        t = m.quote_totals(lines)
        self.assertEqual((t["total_ex_gst_cents"], t["gst_cents"], t["total_inc_gst_cents"]), (15, 2, 17))


class QuoteTotals(unittest.TestCase):
    # the acceptance-test job: 2.5 kW split, back-to-back, 4 h labour, 30% markup, seed prices
    LINES = [
        {"qty_milli": 1000, "unit_cost_cents": 90000, "unit_sell_cents": 117000},
        {"qty_milli": 3000, "unit_cost_cents": 1200, "unit_sell_cents": 1560},
        {"qty_milli": 3000, "unit_cost_cents": 350, "unit_sell_cents": 455},
        {"qty_milli": 1000, "unit_cost_cents": 2800, "unit_sell_cents": 3640},
        {"qty_milli": 3000, "unit_cost_cents": 400, "unit_sell_cents": 520},
        {"qty_milli": 1000, "unit_cost_cents": 2500, "unit_sell_cents": 3250},
        {"qty_milli": 1000, "unit_cost_cents": 1800, "unit_sell_cents": 2340},
        {"qty_milli": 10000, "unit_cost_cents": 300, "unit_sell_cents": 390},
        {"qty_milli": 1000, "unit_cost_cents": 4500, "unit_sell_cents": 5850},
        {"qty_milli": 1000, "unit_cost_cents": 3500, "unit_sell_cents": 4550},
    ]

    def test_whole_quote_to_the_cent(self):
        t = m.quote_totals(self.LINES, labour_hours_milli=4000, labour_cost_rate_cents=6000, labour_sell_rate_cents=11000)
        self.assertEqual(t["external_cost_cents"], 113950)      # 900 + 36 + 10.50 + 28 + 12 + 25 + 18 + 30 + 45 + 35
        self.assertEqual(t["materials_sell_cents"], 148135)     # the same lines at sell
        self.assertEqual(t["labour_cost_cents"], 24000)         # 4 h x $60
        self.assertEqual(t["labour_sell_cents"], 44000)         # 4 h x $110
        self.assertEqual(t["total_ex_gst_cents"], 192135)
        self.assertEqual(t["gst_cents"], 19214)
        self.assertEqual(t["total_inc_gst_cents"], 211349)      # $2,113.49
        self.assertEqual(t["net_profit_cents"], 54185)          # 1921.35 - 1139.50 - 240.00
        self.assertEqual(t["margin_bp"], 2820)                  # 541.85 / 1921.35 = 28.20%
        self.assertEqual(t["unpriced_lines"], 0)

    def test_inc_gst_always_equals_ex_plus_gst(self):
        for adjust in (-5000, 0, 1, 333, 99999):
            t = m.quote_totals(self.LINES, 4000, 6000, 11000, adjust)
            self.assertEqual(t["total_inc_gst_cents"], t["total_ex_gst_cents"] + t["gst_cents"])
            self.assertEqual(t["net_profit_cents"], t["total_ex_gst_cents"] - t["external_cost_cents"] - t["labour_cost_cents"])

    def test_adjustment_moves_price_and_profit_together(self):
        base = m.quote_totals(self.LINES, 4000, 6000, 11000, 0)
        less = m.quote_totals(self.LINES, 4000, 6000, 11000, -10000)
        self.assertEqual(less["total_ex_gst_cents"], base["total_ex_gst_cents"] - 10000)
        self.assertEqual(less["net_profit_cents"], base["net_profit_cents"] - 10000)
        self.assertEqual(less["gst_cents"], 18214)              # $1,821.35 -> $182.135 -> $182.14

    def test_flagged_and_unpriced_lines_never_reach_a_total(self):
        lines = self.LINES + [
            {"qty_milli": 1000, "unit_cost_cents": None, "unit_sell_cents": None, "flagged": True},
            {"qty_milli": 2000, "unit_cost_cents": 5000, "unit_sell_cents": 999999, "flagged": True},
            {"qty_milli": 1000, "unit_cost_cents": 100, "unit_sell_cents": None},
        ]
        t = m.quote_totals(lines, 4000, 6000, 11000)
        self.assertEqual(t["total_inc_gst_cents"], 211349)
        self.assertEqual(t["unpriced_lines"], 3)

    def test_empty_quote_and_negative_total(self):
        t = m.quote_totals([])
        self.assertEqual((t["total_inc_gst_cents"], t["margin_bp"]), (0, 0))
        with self.assertRaises(ValueError):
            m.quote_totals([], adjust_cents=-1)

    def test_a_loss_shows_as_a_negative_margin(self):
        t = m.quote_totals([{"qty_milli": 1000, "unit_cost_cents": 10000, "unit_sell_cents": 8000}])
        self.assertEqual((t["net_profit_cents"], t["margin_bp"]), (-2000, -2500))


class Formatting(unittest.TestCase):
    def test_money(self):
        self.assertEqual(m.fmt_money(211349), "$2,113.49")
        self.assertEqual(m.fmt_money(5), "$0.05")
        self.assertEqual(m.fmt_money(-500), "-$5.00")
        self.assertEqual(m.fmt_money(123456789), "$1,234,567.89")

    def test_quantity_and_percent(self):
        self.assertEqual([m.fmt_qty(x) for x in (1000, 2500, 10000, 125)], ["1", "2.5", "10", "0.125"])
        self.assertEqual(m.fmt_percent(2820), "28.20%")
        self.assertEqual(m.fmt_percent(-2500), "-25.00%")


if __name__ == "__main__":
    unittest.main()
