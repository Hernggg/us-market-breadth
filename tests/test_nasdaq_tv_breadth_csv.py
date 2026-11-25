"""Offline tests for a personally exported TradingView Pine daily-breadth CSV.

All example values are fabricated *test data*, never market data or reports.
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import unittest

from research.tradingview.parse_private_breadth_csv import (
    audit_tradingview_export, ExportInvalid, EXPECTED, SYMBOLS, PERIODS
)


def fixture(trading_days=70, prefixed=False):
    first=dt.date(2026,6,1)
    dates=[]
    day=first
    while len(dates)<trading_days:
        if day.weekday()<5:
            dates.append(day)
        day+=dt.timedelta(days=1)
    symbols=list(SYMBOLS)
    titles=sorted(EXPECTED)
    columns=["Time"]+[
       ("@us-market Indicator: "+k if prefixed else k) for k in titles
    ]
    values={s:[] for s in symbols}
    out=io.StringIO(newline="")
    writer=csv.DictWriter(out,fieldnames=columns)
    writer.writeheader()
    for index,session in enumerate(dates):
        row={"Time":session.isoformat()+"T13:30:00Z"}
        for k,s in enumerate(symbols):
            v=25+k*11+0.3*index
            values[s].append(v)
            for period,n in PERIODS.items():
                val=sum(values[s][-n:])/n if len(values[s])>=n else ""
                label=s+"_"+period
                col=("@us-market Indicator: "+label if prefixed else label)
                row[col]=f"{val:.6f}" if val!="" else ""
        writer.writerow(row)
    return out.getvalue(),dates


class PrivateChartCsvTests(unittest.TestCase):
    def test_complete_60_window_and_five_periods(self):
        data,dates=fixture()
        output=audit_tradingview_export(data,dates[-1].isoformat())
        self.assertEqual(output["asof"],dates[-1].isoformat())
        self.assertFalse(output["publication_allowed"])
        self.assertEqual([w["sessions"] for w in output["windows"]],[1,5,10,20,60])
        self.assertEqual(output["quality_cross_check_counts"]["VERIFIED_WITH_EXPORTED_DAILY_HISTORY"],16)
        self.assertEqual(output["quality_cross_check_counts"]["CURRENT_PERCENT_RANGE_CHECKED"],4)
        self.assertAlmostEqual(output["windows"][0]["nasdaq_composite_above_50dma_pct"],45.7,places=3)

    def test_chart_export_prefixes_allowed(self):
        data,dates=fixture(prefixed=True)
        output=audit_tradingview_export(data,dates[-1].isoformat())
        self.assertEqual(output["exported_daily_rows"],70)

    def test_reject_stale_date(self):
        data,dates=fixture()
        with self.assertRaisesRegex(ExportInvalid,"STALE_OR_MISMATCHED_SESSION"):
            audit_tradingview_export(data,(dates[-1]+dt.timedelta(days=1)).isoformat())

    def test_reject_missing_symbol_or_plot(self):
        data,dates=fixture()
        data=data.replace("NCTH_Avg60","MISSING_NCTH_AVG60",1)
        with self.assertRaisesRegex(ExportInvalid,"Pine indicator plots missing"):
            audit_tradingview_export(data,dates[-1].isoformat())

    def test_reject_not_percentage(self):
        data,dates=fixture()
        rows=list(csv.DictReader(io.StringIO(data)))
        rows[-1]["NCFI_Now"]="112.5"
        file=io.StringIO()
        writer=csv.DictWriter(file,fieldnames=rows[0])
        writer.writeheader();writer.writerows(rows)
        with self.assertRaisesRegex(ExportInvalid,"outside"):
            audit_tradingview_export(file.getvalue(),dates[-1].isoformat())

    def test_reject_mismatched_moving_average(self):
        data,dates=fixture()
        rows=list(csv.DictReader(io.StringIO(data)))
        rows[-1]["NCFI_Avg10"]="3.5"
        file=io.StringIO()
        writer=csv.DictWriter(file,fieldnames=rows[0])
        writer.writeheader();writer.writerows(rows)
        with self.assertRaisesRegex(ExportInvalid,"ROLLING_AVERAGE_MISMATCH"):
            audit_tradingview_export(file.getvalue(),dates[-1].isoformat())

    def test_not_enough_history_is_transparently_flagged(self):
        data,dates=fixture(trading_days=30)
        # No real source could supply Avg60 with just 30 source bars. Here we
        # test an already-computed 60D value from the Pine chart context.
        rows=list(csv.DictReader(io.StringIO(data)))
        rows[-1]["NCFI_Avg60"]="40.0"
        rows[-1]["NCTH_Avg60"]="40.0"
        rows[-1]["S5FI_Avg60"]="40.0"
        rows[-1]["S5TH_Avg60"]="40.0"
        file=io.StringIO()
        writer=csv.DictWriter(file,fieldnames=rows[0])
        writer.writeheader();writer.writerows(rows)
        out=audit_tradingview_export(file.getvalue(),dates[-1].isoformat())
        self.assertEqual(out["quality_checks"]["NCFI_Avg60"],
                         "INSUFFICIENT_EXPORTED_ROWS_TO_RECHECK")


if __name__=="__main__":
    unittest.main()
