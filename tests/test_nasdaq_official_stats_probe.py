"""Offline schema and rolling-window tests for Nasdaq Trader official statistics."""
import datetime as dt
import unittest

from nasdaq_official_stats_probe import find_header, reconstruct, parse_day


class OfficialMarketFileTests(unittest.TestCase):
    def setUp(self):
        self.dates = [dt.date(2026, 9, 1)+dt.timedelta(days=k) for k in range(60)]
        self.csv = "Trade Date,NASDAQ Advances,NASDAQ Declines,NASDAQ Unchanged,NASDAQ Composite Index,NASDAQ Computer Index\n" + "\n".join(
            f"{d.isoformat()},1900,1700,100,25000.25,5000.75" for d in self.dates
        )

    def test_direct_field_detection(self):
        header, columns, raw = find_header([self.csv.splitlines()[0].split(",")])
        self.assertEqual(header,0)
        self.assertEqual(columns["advances"],1)
        self.assertEqual(columns["declines"],2)
        self.assertEqual(columns["computer"],5)

    def test_five_windows_and_composite_level(self):
        report = reconstruct(self.csv, self.dates)
        self.assertEqual(report["status"],"FULL_60_SESSION_NASDAQ_ISSUES_AD_AVAILABLE")
        self.assertEqual([w["sessions"] for w in report["windows"]],[1,5,10,20,60])
        self.assertEqual(report["windows"][-1]["avg_advances"],1900)
        self.assertEqual(report["windows"][0]["ad_ratio"],round(1900/1700,5))
        self.assertEqual(report["daily"][-1]["composite_index_level"],25000.25)

    def test_missing_date_refuses_complete_status(self):
        partial = "\n".join(self.csv.splitlines()[:-1])
        report = reconstruct(partial, self.dates)
        self.assertEqual(report["status"],"INCOMPLETE_REQUIRED_60_SESSIONS")
        self.assertIn(self.dates[-1].isoformat(), report["missing_session_dates"])

    def test_ambiguous_schema_halts(self):
        report = reconstruct("A,B,C\n2026-01-01,1,2", self.dates)
        self.assertEqual(report["status"],"NEEDS_CSV_SCHEMA_REVIEW")

    def test_explicit_date_format(self):
        self.assertEqual(parse_day("11/19/2026"),dt.date(2026,11,19))


if __name__ == "__main__":
    unittest.main()
