#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline parser for a USER-EXPORTED TradingView Pine V2.0 MA breadth chart CSV.

Source CSV should be exported from the original Pine script
research/tradingview/us_market_ma_breadth.pine on 1D NASDAQ:IXIC chart.
No TradingView scraping, no network requests, no raw bars publicly persisted.

20 expected columns: 4 proprietary percent-above-MA *symbols* x 5 rolling
means, where Avg5/10/20/60 averages the DAILY PERCENTAGE SERIES itself.
It is not the % of stocks above a 5/10/20/60-day STOCK moving average.

User should only provide CSV for their own personal analysis with permission
to do so. Never commit source TradingView data to a PUBLIC GitHub repo.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import math
import re
from collections import Counter
from pathlib import Path

SYMBOLS={
    "NCFI":{"universe":"NASDAQ_COMPOSITE_THIRD_PARTY_BREADTH","metric":"above_50dma_pct"},
    "NCTH":{"universe":"NASDAQ_COMPOSITE_THIRD_PARTY_BREADTH","metric":"above_200dma_pct"},
    "S5FI":{"universe":"SP500_THIRD_PARTY_BREADTH","metric":"above_50dma_pct"},
    "S5TH":{"universe":"SP500_THIRD_PARTY_BREADTH","metric":"above_200dma_pct"},
}
PERIODS={"Now":1,"Avg5":5,"Avg10":10,"Avg20":20,"Avg60":60}
EXPECTED={f"{symbol}_{period}" for symbol in SYMBOLS for period in PERIODS}
DATE_CANDIDATES={"time","date","datetime","timestamp"}


class ExportInvalid(ValueError):
    pass


def header_name(field):
    text=str(field).strip().strip("\ufeff").strip()
    if text.lower() in DATE_CANDIDATES:
        return "TIME"
    # TradingView can prefix Pine plot titles with the indicator title.
    found=[name for name in EXPECTED if re.search(r"(?<![A-Za-z0-9_])"+re.escape(name)+r"$",text,re.I)]
    if len(found)==1:
        return found[0]
    return None


def parse_date(source):
    text=str(source or "").strip()
    if not text:
        raise ExportInvalid("Missing session date")
    if re.fullmatch(r"\d{10}|\d{13}",text):
        epoch=int(text)
        if len(text)==13:
            epoch/=1000
        return dt.datetime.fromtimestamp(epoch,dt.timezone.utc).date()
    match=re.match(r"^(\d{4}-\d{2}-\d{2})",text)
    if match:
        return dt.date.fromisoformat(match.group(1))
    for pattern in ("%m/%d/%Y","%Y/%m/%d"):
        try:return dt.datetime.strptime(text,pattern).date()
        except ValueError:pass
    raise ExportInvalid("Unsupported date/time field format")


def percent(value,field,day):
    raw=str(value if value is not None else "").strip().replace("%","")
    if not raw or raw.lower() in {"na","n/a","nan","null","--","-"}:
        raise ExportInvalid(f"Missing value {field} on {day}")
    try:
        val=float(raw)
    except ValueError as exc:
        raise ExportInvalid(f"Invalid numeric value {field} on {day}") from exc
    if not math.isfinite(val) or val<0 or val>100:
        raise ExportInvalid(f"Percent outside [0,100] for {field} on {day}")
    return val


def audit_tradingview_export(content, expected_session=None, tolerance=0.055):
    rows=list(csv.DictReader(io.StringIO(content)))
    if not rows:
        raise ExportInvalid("Empty export CSV")
    original_columns=rows[0].keys()
    mapped={}; duplicates=[]
    for col in original_columns:
        name=header_name(col)
        if name:
            if name in mapped:
                duplicates.append(name)
            else:
                mapped[name]=col
    if duplicates:
        raise ExportInvalid("Ambiguous repeated indicator export fields: "+", ".join(sorted(set(duplicates))))
    if "TIME" not in mapped:
        raise ExportInvalid("Missing TradingView Time column")
    missing=EXPECTED-set(mapped)
    if missing:
        raise ExportInvalid("Pine indicator plots missing from CSV: "+", ".join(sorted(missing)))
    observed={}
    for row in rows:
        day=parse_date(row[mapped["TIME"]])
        if day in observed:
            raise ExportInvalid("Duplicate export date: "+day.isoformat())
        if day.weekday()>=5:
            raise ExportInvalid("Expected an index 1D weekday session, got weekend "+day.isoformat())
        observed[day]=row
    dates=sorted(observed)
    last=dates[-1]
    if expected_session is not None:
        requested=dt.date.fromisoformat(str(expected_session))
        if last!=requested:
            raise ExportInvalid(f"STALE_OR_MISMATCHED_SESSION: requested {requested}, exported {last}")
    latest=observed[last]
    values={field:percent(latest.get(mapped[field]),field,last) for field in sorted(EXPECTED)}
    # Independent CSV self-consistency check: compare Pine's internal rolling
    # averages to the raw Now column over the relevant number of source rows.
    # This is a math integrity check, NOT a guarantee of TradingView input
    # coverage, licensing, or independent confirmation of source prices.
    verified={}
    for symbol in SYMBOLS:
        field_now=f"{symbol}_Now"
        for name,n in PERIODS.items():
            if n==1:
                verified[f"{symbol}_{name}"]="CURRENT_PERCENT_RANGE_CHECKED"
                continue
            series=dates[-n:]
            if len(series)!=n:
                verified[f"{symbol}_{name}"]="INSUFFICIENT_EXPORTED_ROWS_TO_RECHECK"
                continue
            source_data=[]
            for day in series:
                value=observed[day].get(mapped[field_now])
                try:
                    source_data.append(percent(value,field_now,day))
                except ExportInvalid:
                    break
            if len(source_data)<n:
                verified[f"{symbol}_{name}"]="INCOMPLETE_EXPORTED_HISTORY_TO_RECHECK"
                continue
            expected=sum(source_data)/n
            got=values[f"{symbol}_{name}"]
            if abs(expected-got)>tolerance:
                raise ExportInvalid(
                    f"ROLLING_AVERAGE_MISMATCH {symbol} {name}: CSV value {got:.4f} "
                    f"does not equal {n} visible 1D values (mean {expected:.4f}); "
                    "check daily timeframe, data revisions and indicator series"
                )
            verified[f"{symbol}_{name}"]="VERIFIED_WITH_EXPORTED_DAILY_HISTORY"
    report={
        "status":"PRIVATE_MANUAL_EXPORT_RESEARCH_NOT_AUTOMATED_FEED",
        "source":"TradingView Pine user-exported 1D CSV",
        "publication_allowed":False,
        "official_nasdaq_data":False,
        "nasdaq_100_substitute":False,
        "asof":last.isoformat(),
        "earliest_exported_session":dates[0].isoformat(),
        "exported_daily_rows":len(dates),
        "basis":"Daily percentage of index constituent stocks above their OWN MA50/MA200",
        "window_definition":"1D actual percentage; 5/10/20/60D arithmetic average of daily percentages, NOT individual-stock MA lengths",
        "data_license":"User-supplied personal visual chart export; permission for any GitHub storage, public reuse or automated retrieval not established",
        "quality_cross_check_counts":dict(Counter(verified.values())),
        "quality_checks":verified,
        "windows":[{
            "sessions":n,
            "asof":last.isoformat(),
            "nasdaq_composite_above_50dma_pct":round(values[f"NCFI_{tag}"],4),
            "nasdaq_composite_above_200dma_pct":round(values[f"NCTH_{tag}"],4),
            "sp500_above_50dma_pct":round(values[f"S5FI_{tag}"],4),
            "sp500_above_200dma_pct":round(values[f"S5TH_{tag}"],4),
        } for tag,n in PERIODS.items()],
    }
    return report


def main():
    p=argparse.ArgumentParser(description="Offline parse of personally exported TradingView Pine data")
    p.add_argument("--csv",type=Path,required=True)
    p.add_argument("--expected-session",required=True,help="YYYY-MM-DD exchange local calendar day")
    p.add_argument("--out",type=Path,default=None,help="PRIVATE optional output, never under public/")
    args=p.parse_args()
    source=args.csv
    if not source.is_file() or source.stat().st_size>5_000_000:
        raise ExportInvalid("Missing or oversized CSV")
    report=audit_tradingview_export(source.read_text(encoding="utf-8-sig"),args.expected_session)
    if args.out:
        if "public" in [p.lower() for p in args.out.parts] or args.out.resolve().is_relative_to(Path.cwd().resolve()):
            raise ExportInvalid("Do not save proprietary user-exported data/derivatives inside public GitHub working tree")
        args.out.parent.mkdir(parents=True,exist_ok=True)
        args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
