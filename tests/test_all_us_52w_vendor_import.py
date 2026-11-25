"""Offline arithmetic/scope tests. Prices in fixtures are FAKE; no real market data."""
from __future__ import annotations

import csv
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from research.all_us_52w.import_authorized_ma_hx_lx import (
    HistoryRejected, sanitize_count, calculate, read_barchart_symbol,
    read_calendar, save_private_report,
)

def dates(n=65):
    out=[]
    d=dt.date(2026,8,3)
    while len(out)<n:
        if d.weekday()<5:
            out.append(d)
        d+=dt.timedelta(days=1)
    return out


class VendorHistoryTests(unittest.TestCase):
    def test_zero_sentinel_has_documented_vendor_meaning_only(self):
        self.assertEqual(sanitize_count("0.01",barchart_sentinel=True),0)
        with self.assertRaisesRegex(HistoryRejected,"must be integers"):
            sanitize_count("0.01",barchart_sentinel=False)
        for invalid in ("", "-1", "2.2", "nan", "inf"):
            with self.subTest(invalid=invalid),self.assertRaises(HistoryRejected):
                sanitize_count(invalid,barchart_sentinel=True)

    def test_60_sessions_all_windows_exact(self):
        ds=dates()
        highs={d:10+i for i,d in enumerate(ds)}
        lows={d:130-i for i,d in enumerate(ds)}
        out=calculate(highs,lows,ds,ds[-1].isoformat(),private_use_rights=True)
        self.assertEqual([x["sessions"] for x in out["windows"]],[1,5,10,20,60])
        self.assertTrue(all(x["status"]=="CALCULATED_FROM_REAL_EXPORTED_COUNT_ROWS" for x in out["windows"]))
        self.assertEqual(out["windows"][0]["avg_new_highs"],74)
        self.assertEqual(out["windows"][0]["avg_new_lows"],66)
        self.assertAlmostEqual(out["windows"][-1]["avg_new_highs"],44.5)
        self.assertAlmostEqual(out["windows"][-1]["avg_new_lows"],95.5)
        self.assertAlmostEqual(out["windows"][-1]["avg_net_new_highs"],-51)
        self.assertFalse(out["strict_all_us_common_stock_scope_verified"])
        self.assertFalse(out["licensed_unattended_automation_verified"])

    def test_missing_seventh_day_no_synthetic_fill(self):
        ds=dates()
        hi={d:33 for d in ds}
        lo={d:66 for d in ds}
        hi.pop(ds[-7])
        result=calculate(hi,lo,ds,ds[-1].isoformat(),private_use_rights=True)
        self.assertEqual([w["status"] for w in result["windows"][:2]],
                         ["CALCULATED_FROM_REAL_EXPORTED_COUNT_ROWS"]*2)
        self.assertEqual([w["status"] for w in result["windows"][2:]],
                         ["MISSING_REAL_DAILY_ROWS"]*3)
        self.assertEqual(result["windows"][-1]["avg_new_highs"],None)
        self.assertEqual(result["target_calendar_coverage"],59)

    def test_missing_source_asof_no_relabeling(self):
        ds=dates()
        hi={d:3 for d in ds[:-1]}
        lo={d:5 for d in ds[:-1]}
        result=calculate(hi,lo,ds,ds[-1].isoformat(),private_use_rights=True)
        self.assertFalse(result["asof_current"])
        self.assertTrue(all(w["status"]=="MISSING_REAL_DAILY_ROWS" for w in result["windows"]))

    def test_wrong_target_rejected(self):
        ds=dates()
        with self.assertRaisesRegex(HistoryRejected,"EXACT"):
            calculate({d:1 for d in ds},{d:2 for d in ds},ds,ds[-2].isoformat(),private_use_rights=True)

    def test_rights_gate(self):
        ds=dates()
        with self.assertRaisesRegex(HistoryRejected,"NOT attested"):
            calculate({d:1 for d in ds},{d:2 for d in ds},ds,ds[-1].isoformat(),private_use_rights=False)

    def test_csv_duplicate_and_calendar_check(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            h=root/"MAHX.csv"
            h.write_text("Date,Close\n2026-11-23,0.01\n2026-11-24,4\n",encoding="utf-8")
            self.assertEqual(read_barchart_symbol(h,kind="highs"),
                {dt.date(2026,11,23):0,dt.date(2026,11,24):4})
            h.write_text("Date,Close\n2026-11-23,3\n2026-11-23,4\n",encoding="utf-8")
            with self.assertRaisesRegex(HistoryRejected,"Duplicate"):
                read_barchart_symbol(h,kind="highs")
            cal=root/"calendar.csv"
            ds=dates()
            cal.write_text("date\n"+"\n".join(x.isoformat() for x in ds)+"\n",encoding="utf-8")
            self.assertEqual(read_calendar(cal)[-1],ds[-1])
            cal.write_text("date\n"+"\n".join(x.isoformat() for x in ds[:-1])+"\n"+ds[-2].isoformat()+"\n",encoding="utf-8")
            with self.assertRaisesRegex(HistoryRejected,"DISTINCT"):
                read_calendar(cal)

    def test_output_stays_outside_repo(self):
        with self.assertRaisesRegex(HistoryRejected,"DO NOT save"):
            save_private_report("public/all_us_nh_nl.json",{"demo":True})


if __name__=="__main__":
    unittest.main()
