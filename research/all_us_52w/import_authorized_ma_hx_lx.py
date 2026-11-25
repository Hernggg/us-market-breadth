#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Validate two explicitly authorized real 52W NH/NL COUNT history exports.

SOURCE PROVENANCE (do not confuse):
- Barchart '$MAHX' and '$MALX' = "52-Week Highs/Lows Overall",
  a provider-defined Overall US count universe, NOT independently verified
  identical to the user's all-eligible-US-common-stock target population.
- Barchart documentation explicitly states '0.01' represents ZERO issues
  on high/low historical CHARTS. This rule is provider-specific only.
- This program DOES NOT scrape Barchart, TradingView or EODData.
- Not a live connector: input must be privately obtained through a source
  whose use, derived statistics, automated processing and retention are allowed.

Expected authorized format for each of TWO CSV files:
  Date,Close
  2026-11-24,63.00
  ... (at least 60 completed US equity market sessions)
(The examples above are syntactic only, NOT a quote from Barchart!)

Calendar must be a genuine exchange-date list, e.g. known public SP500 PIT
date column, or a separately authorized complete NYSE calendar. The chosen
calendar must end at the same target date; do not fill skipped sessions.
The only permitted persisted output is a PRIVATE local file OUTSIDE
the public Git repository; source rows and vendor quote series not committed.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path

WINDOWS=(1,5,10,20,60)
SOURCE="BARCHART_OVERALL_US_52W_VENDOR_SERIES"
SYMBOLS={"highs":"MAHX","lows":"MALX"}


class HistoryRejected(ValueError):
    pass


def parse_day(value):
    s=str(value or "").strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d %b %y", "%d %b %Y", "%b %d, %Y"):
        try:
            d=dt.datetime.strptime(s,fmt).date()
            if d.weekday()>4:
                raise HistoryRejected("Weekend cannot be a regular US market session")
            return d
        except ValueError:
            pass
    raise HistoryRejected("Missing or unsupported daily US exchange date")


def sanitize_count(value, *, barchart_sentinel=False):
    s=str(value if value is not None else "").strip().replace(",","")
    if not s:
        raise HistoryRejected("Missing issue-count value, never replace with zero")
    try: v=float(s)
    except ValueError as exc: raise HistoryRejected("Issue count is nonnumeric") from exc
    if not math.isfinite(v) or v<0 or v>50000:
        raise HistoryRejected("Invalid issue-count number or unrealistic size")
    if barchart_sentinel and math.isclose(v,0.01,abs_tol=1e-9):
        return 0
    if v!=int(v):
        raise HistoryRejected("Daily issue counts must be integers; 0.01 only maps to zero for documented Barchart series")
    return int(v)


def read_calendar(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as fh:
        rd=csv.DictReader(fh)
        names={s.lower():s for s in (rd.fieldnames or [])}
        col=names.get("date") or names.get("trade_date")
        if not col: raise HistoryRejected("Calendar CSV needs 'date' or 'trade_date' column")
        days=[parse_day(row[col]) for row in rd]
    if len(set(days))!=len(days) or days!=sorted(days) or len(days)<60:
        raise HistoryRejected("Calendar needs >=60 DISTINCT ascending actual exchange dates")
    return days


def read_barchart_symbol(path, *, kind):
    if kind not in SYMBOLS:
        raise HistoryRejected("Expected independent highs/lows symbol")
    with Path(path).open(encoding="utf-8-sig",newline="") as fh:
        rd=csv.DictReader(fh)
        fields={s.strip().lower():s for s in (rd.fieldnames or [])}
        day_field=fields.get("date") or fields.get("trade_date")
        val_field=fields.get("close") or fields.get("last") or fields.get("count")
        if not day_field or not val_field:
            raise HistoryRejected("Source CSV needs Date and Close/Last/Count columns")
        rows={}
        for row in rd:
            d=parse_day(row.get(day_field))
            if d in rows:
                raise HistoryRejected("Duplicate daily row: "+d.isoformat())
            rows[d]=sanitize_count(row.get(val_field),barchart_sentinel=True)
    if not rows:
        raise HistoryRejected("Empty high/low quote history")
    return rows


def calculate(highs, lows, calendar, asof, *, private_use_rights):
    if not private_use_rights:
        raise HistoryRejected("Source export and derivative statistics use rights NOT attested")
    target=parse_day(asof)
    if calendar[-1]!=target:
        raise HistoryRejected("Calendar newest date must match EXACT requested as-of date")
    expected=calendar[-60:]
    if len(expected)!=60:
        raise HistoryRejected("Need 60 actual exchange sessions")
    available=set(highs)&set(lows)
    if not available:
        raise HistoryRejected("No paired highs/lows date coverage")
    # Only contiguous latest windows are allowed; no arithmetic treating
    # absent sessions as zero, no shifting a missing daily observation.
    windows=[]
    for n in WINDOWS:
        dates=calendar[-n:]
        absent=[day.isoformat() for day in dates if day not in available]
        if absent:
            windows.append({"sessions":n,"status":"MISSING_REAL_DAILY_ROWS",
                            "missing_count":len(absent),"first_missing_date":absent[0],
                            "avg_new_highs":None,"avg_new_lows":None,"avg_net_new_highs":None})
        else:
            a=sum(highs[d] for d in dates)/n
            b=sum(lows[d] for d in dates)/n
            windows.append({"sessions":n,"status":"CALCULATED_FROM_REAL_EXPORTED_COUNT_ROWS",
                            "missing_count":0,"first_missing_date":None,
                            "avg_new_highs":round(a,4),"avg_new_lows":round(b,4),
                            "avg_net_new_highs":round(a-b,4)})
    all_dates=sorted(available)
    report={
        "source":SOURCE,
        "universe":"Barchart Overall U.S. market provider-defined counts; NOT verified exact eligible common-stock universe",
        "source_rights":"Personally attested private use only; no public distribution",
        "publisher_rights_verified":False,
        "licensed_unattended_automation_verified":False,
        "strict_all_us_common_stock_scope_verified":False,
        "target_session":target.isoformat(),
        "source_first_pair_date":all_dates[0].isoformat(),
        "source_last_pair_date":all_dates[-1].isoformat(),
        "paired_source_dates":len(all_dates),
        "target_calendar_span_start":expected[0].isoformat(),
        "target_calendar_span_end":expected[-1].isoformat(),
        "target_calendar_coverage":sum(d in available for d in expected),
        "asof_current":target in available,
        "windows":windows,
    }
    return report


def save_private_report(path,report):
    if path is None:return
    p=Path(path).resolve()
    root=Path.cwd().resolve()
    if p==root or root in p.parents:
        raise HistoryRejected("DO NOT save private vendor series/results under the public repository")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ma-hx-csv",type=Path,required=True,help="Authorized Barchart $MAHX count history export")
    ap.add_argument("--ma-lx-csv",type=Path,required=True,help="Authorized Barchart $MALX count history export")
    ap.add_argument("--calendar-csv",type=Path,required=True)
    ap.add_argument("--asof",required=True,help="YYYY-MM-DD closed US trading date")
    ap.add_argument("--private-use-rights-confirmed",action="store_true")
    ap.add_argument("--out",type=Path,default=None)
    opt=ap.parse_args()
    for path in (opt.ma_hx_csv,opt.ma_lx_csv,opt.calendar_csv):
        if not path.is_file() or path.stat().st_size>4_000_000:
            raise HistoryRejected("Required LOCAL, non-oversized CSV file unavailable")
    highs=read_barchart_symbol(opt.ma_hx_csv,kind="highs")
    lows=read_barchart_symbol(opt.ma_lx_csv,kind="lows")
    cal=read_calendar(opt.calendar_csv)
    report=calculate(highs,lows,cal,opt.asof,private_use_rights=opt.private_use_rights_confirmed)
    save_private_report(opt.out,report)
    print(json.dumps(report,ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
