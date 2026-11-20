"""Offline tests for Nasdaq Trader historical annual file reconstruction."""
import datetime as dt
import unittest
from unittest.mock import patch
from nasdaq_official_history import annual_file, windows_for, AuditError

class ArchiveTests(unittest.TestCase):
    def csv_text(self, year=2025, n=220):
        start=dt.date(year,1,1)
        # synthetic dates (including weekends) only for validating schema parser
        days=[start+dt.timedelta(days=i) for i in range(n)]
        return "Date,N100,Composite,Computer,Advances,Declines,Unchanged\n" + "\n".join(
            f"{d.month}/{d.day}/{d.year} 0:00:00,100,120.5,135,2000,1750,50" for d in days
        )

    def test_annual_file_parses_timestamp_and_counts(self):
        with patch("nasdaq_official_history.fetch_csv", return_value=("https://test.invalid",self.csv_text())):
            url, daily, warnings, header=annual_file(2025)
        self.assertEqual(len(daily),220)
        self.assertEqual(daily[dt.date(2025,1,1)]["advances"],2000)
        self.assertEqual(daily[dt.date(2025,1,1)]["computer_index_level"],135)

    def test_trailing_windows_across_years(self):
        start=dt.date(2025,12,2)
        days=[(start+dt.timedelta(days=i)) for i in range(75)]
        daily=[{"date":d.isoformat(),"advances":2000,"declines":1000,"unchanged":50,
                "composite_index_level":100+i,"computer_index_level":200+2*i}
               for i,d in enumerate(days)]
        ws=windows_for(daily)
        self.assertEqual([x["sessions"] for x in ws],[1,5,10,20,60])
        self.assertEqual(ws[-1]["avg_advances"],2000)
        self.assertEqual(ws[-1]["ad_ratio"],2.0)
        self.assertEqual(ws[0]["index_return_reference_date"],days[-2].isoformat())

    def test_partial_annual_file_rejected(self):
        with patch("nasdaq_official_history.fetch_csv", return_value=("https://test.invalid",self.csv_text(n=40))):
            with self.assertRaisesRegex(AuditError,"only 40 valid sessions"):
                annual_file(2025)

    def test_duplicate_dates_refused(self):
        original=self.csv_text()
        duplicated=original+"\n"+original.splitlines()[1]
        with patch("nasdaq_official_history.fetch_csv", return_value=("https://test.invalid",duplicated)):
            with self.assertRaisesRegex(AuditError,"duplicate day"):
                annual_file(2025)


if __name__ == "__main__":
    unittest.main()
