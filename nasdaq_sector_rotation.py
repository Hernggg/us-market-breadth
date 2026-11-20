#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nasdaq Trader official *index level* sector/industry relative-strength study.

These are sector/index PRICE RETURNS, not sector breadth or index constituent
A/D. Reuses public annual Nasdaq Trader CSV, no external stock price service.
Outputs only research diagnostics; never publishes official COMP breadth.
"""
from __future__ import annotations
import argparse
import csv
import datetime as dt
import io
import json
import math
from pathlib import Path

from nasdaq_official_stats_probe import fetch_csv, find_header, parse_day, parse_number, norm, WINDOWS
from nasdaq_comp_candidate import AuditError, load_calendar

NAMES = {
    "composite": "Nasdaq Composite",
    "n100": "Nasdaq-100",
    "financial100": "Nasdaq Financial-100",
    "industrial": "Nasdaq Industrial",
    "bank": "Nasdaq Bank",
    "insurance": "Nasdaq Insurance",
    "financial": "Nasdaq Financial",
    "transportation": "Nasdaq Transportation",
    "telecom": "Nasdaq Telecommunications",
    "biotech": "Nasdaq Biotechnology",
    "computer": "Nasdaq Computer",
}


def build_sector_report(csv_text, requested):
    rows = [r for r in csv.reader(io.StringIO(csv_text)) if any(x.strip() for x in r)]
    head_i, standard, header = find_header(rows)
    if standard is None:
        raise AuditError("Nasdaq Trader source did not contain mandatory A/D columns")
    cols = {norm(name):i for i,name in enumerate(header)}
    required = list(NAMES)
    absent = [name for name in required if name not in cols]
    if absent:
        raise AuditError("Missing selected index level columns: "+str(absent))
    date_col = standard["date"]
    observed, warnings = {}, []
    for line,row in enumerate(rows[head_i+1:],head_i+2):
        if len(row) <= max(cols[n] for n in required):
            continue
        try:
            day = parse_day(row[date_col])
        except ValueError:
            continue
        if day>requested:
            continue
        if day in observed:
            raise AuditError("Duplicate source date: "+day.isoformat())
        data = {}
        for name in NAMES:
            try:
                value = parse_number(row[cols[name]])
                if not (math.isfinite(value) and value > 0):
                    raise ValueError("not positive finite")
                data[name] = value
            except (ValueError, IndexError):
                data[name] = None
        observed[day] = data
    dates = sorted(observed)
    if len(dates) < 61:
        raise AuditError("Need at least 61 actual trading-day index levels for 60-session returns")
    latest=dates[-1]
    result = []
    for n in WINDOWS:
        start = dates[-n-1]
        sectors = []
        base0, base1 = observed[start]["composite"],observed[latest]["composite"]
        if base0 is None or base1 is None:
            raise AuditError("Nasdaq Composite benchmark prices missing")
        benchmark=100*(base1/base0-1)
        for key, title in NAMES.items():
            old,new = observed[start][key],observed[latest][key]
            if old is None or new is None:
                raise AuditError("Missing "+key+" index level for "+start.isoformat()+"/"+latest.isoformat())
            pct=100*(new/old-1)
            sectors.append({
                "index_id":key,"name":title,
                "return_pct":round(pct,4),
                "relative_to_composite_percentage_points":round(pct-benchmark,4)
            })
        result.append({
            "sessions":n,
            "from_prior_close":start.isoformat(),
            "through_close":latest.isoformat(),
            "nasdaq_composite_return_pct":round(benchmark,4),
            "indices":sectors,
        })
    return {
        "market":"NASDAQ_OFFICIAL_INDEX_PERFORMANCE_NOT_CONSTITUENT_BREADTH",
        "eligible_for_us_market_comp_breadth_publication":False,
        "source":"https://nasdaqtrader.com/dynamic/dailyfiles/daily"+str(requested.year)+".csv",
        "requested_session":requested.isoformat(),
        "asof_actual":latest.isoformat(),
        "source_lag_status":"DATE_MATCHED" if latest==requested else "SOURCE_LAGGED",
        "observed_sessions_in_current_year":len(dates),
        "method":"Close-to-close n-trading-session index-level return, not daily average return",
        "limitation":"Nasdaq Computer and other index returns provide sector leadership context, not constituent member breadth, official technology sector taxonomy or investible total return.",
        "periods":result,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",type=Path,default=Path("public/sp500_pit_daily.csv"))
    p.add_argument("--out",type=Path,default=Path("research/nasdaq_comp/official_sector_relative_strength.json"))
    args=p.parse_args()
    requested=load_calendar(args.calendar,None)[-1]
    url,source=fetch_csv(requested.year)
    report=build_sector_report(source,requested)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    summary={}
    for w in report["periods"]:
        n=w["sessions"]
        summary[str(n)]={x["index_id"]:x["return_pct"] for x in w["indices"]}
    print(json.dumps({"status":"RESEARCH_ONLY_INDEX_LEVELS","actual":report["asof_actual"],
                      "source_lag":report["source_lag_status"],"returns":summary},ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
