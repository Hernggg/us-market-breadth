#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only bulk price feed feasibility test, RESEARCH ONLY.

Only tests a MarketParquet *public* one-day sample:
 https://marketparquet.com/api/data/download/stock_daily/YYYY-MM-DD.parquet

IMPORTANT:
 - Free files are vendor test samples, with NO redistribution license.
 - Raw files are held only in an ephemeral temporary directory and deleted.
 - No raw prices or per-symbol datasets are printed or committed to Git.
 - Does NOT establish historical coverage or Nasdaq Composite eligibility.
 - Does NOT replace S&P 500 or any published @us-market report.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import os
import tempfile
import urllib.request
from pathlib import Path

from nasdaq_comp_candidate import verified_source, classification, load_calendar, AuditError

URL_BASE = "https://marketparquet.com/api/data/download/stock_daily/"
MAX_SAMPLE_BYTES = 35_000_000  # abort if unexpectedly large
SAFETY = "RESEARCH_SAMPLE_NO_REPUBLICATION_NOT_OFFICIAL_COMP"


def candidate_tickers(rows, day):
    active = {}
    for ticker, start, end, record in rows:
        if start <= day and (end is None or day < end):
            if ticker in active:
                raise AuditError("Overlapping source PIT membership for ticker " + ticker)
            active[ticker] = record
    if not 2500 <= len(active) <= 8000:
        raise AuditError("Unexpected Nasdaq listing directory size")
    output = {ticker for ticker,rec in active.items()
              if classification(rec) == "LIKELY_ELIGIBLE_TYPE"}
    unresolved = {ticker for ticker,rec in active.items()
                  if classification(rec) == "UNRESOLVED_TYPE"}
    return output, unresolved


def match_counts(candidate: set[str], unresolved: set[str], quotes):
    """Pure count-only reconciliation; avoid returning vendor prices or symbols."""
    if len(candidate & unresolved):
        raise AuditError("Eligible and unresolved tickers overlap")
    quote_set = set()
    invalid = 0
    duplicates = 0
    for symbol, close, volume in quotes:
        if not isinstance(symbol, str) or not symbol.strip():
            invalid += 1
            continue
        key = symbol.strip().upper().replace("-", ".")
        if key in quote_set:
            duplicates += 1
        quote_set.add(key)
        try:
            if close is None or not math.isfinite(float(close)) or float(close)<=0:
                invalid+=1
            if volume is not None and (not math.isfinite(float(volume)) or float(volume)<0):
                invalid+=1
        except (TypeError,ValueError,OverflowError):
            invalid+=1
    if duplicates:
        raise AuditError("Bulk price file contains duplicate ticker keys")
    return {
        "nasdaq_common_like_candidates":len(candidate),
        "unresolved_type_candidates":len(unresolved),
        "bulk_daily_symbols":len(quote_set),
        "candidate_symbols_with_bulk_daily_quote":len(candidate & quote_set),
        "candidate_symbols_missing_bulk_daily_quote":len(candidate - quote_set),
        "unresolved_symbols_with_quote":len(unresolved & quote_set),
        "invalid_price_or_volume_fields":invalid,
        "price_coverage_ratio":round(len(candidate & quote_set)/len(candidate),6) if candidate else None,
    }


def run(date: dt.date):
    import duckdb
    meta, archive_digest, intervals, floor = verified_source()
    if date < floor:
        raise AuditError("Requested day before historical Nasdaq listed directory starts")
    if dt.datetime.fromisoformat(meta["generated_at_utc"].replace("Z","+00:00")).date() < date:
        raise AuditError("Historical Nasdaq directory source not yet updated for date")
    candidate, unresolved = candidate_tickers(intervals, date)
    url=URL_BASE+date.isoformat()+".parquet"
    req=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (research source-format sample audit)"})
    with tempfile.TemporaryDirectory(prefix="nasdaq_bulk_probe_") as scratch:
        file=Path(scratch)/"sample.parquet"
        with urllib.request.urlopen(req, timeout=45) as response, file.open("wb") as out:
            total=0
            while True:
                b=response.read(1024*1024)
                if not b: break
                total+=len(b)
                if total>MAX_SAMPLE_BYTES:
                    raise AuditError("Price sample larger than safety cap; aborted")
                out.write(b)
        with file.open("rb") as check:
            if check.read(4)!=b"PAR1":
                raise AuditError("Bulk sample is not a Parquet file")
        con=duckdb.connect()
        try:
            columns={r[0].lower():r[0] for r in con.execute(
                "DESCRIBE SELECT * FROM read_parquet(?)",[str(file)]
            ).fetchall()}
            if not {"date","symbol","close","volume"}.issubset(columns):
                raise AuditError("Unexpected price feed schema; insufficient required columns")
            count_dates=con.execute("SELECT count(DISTINCT CAST(date AS DATE)), min(CAST(date AS DATE)), max(CAST(date AS DATE)) FROM read_parquet(?)",[str(file)]).fetchone()
            if count_dates[0]!=1 or count_dates[1]!=date or count_dates[2]!=date:
                raise AuditError("Bulk price file market date does not match requested session")
            # Full-day file is deliberately small enough to inspect in memory,
            # but the output contains only statistical counts.
            quotes=con.execute(
                "SELECT CAST(symbol AS VARCHAR),CAST(close AS DOUBLE),CAST(volume AS DOUBLE) FROM read_parquet(?)",
                [str(file)]
            ).fetchall()
            result=match_counts(candidate,unresolved,quotes)
        finally:
            con.close()
    return {
        "status":SAFETY,
        "asof":date.isoformat(),
        "source":url,
        "historical_directory_source":"https://github.com/TylerJForstrom/Stock-Data",
        "source_dataset":"MarketParquet free no-account one-day TEST SAMPLE",
        "license_notice":"Sample has no redistribution license. No price records persisted, printed or uploaded.",
        "reported_facts_are_only_sample_technical_feasibility":True,
        "actual_comp_member_universe_verified":False,
        "historical_311_sessions_verified":False,
        "max_allowed_sample_bytes":MAX_SAMPLE_BYTES,
        "sample_bytes":total,
        "sample_columns":sorted(columns),
        **result,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",type=Path,default=Path("public/sp500_pit_daily.csv"))
    p.add_argument("--asof",default=None)
    a=p.parse_args()
    dates=load_calendar(a.calendar,a.asof)
    result=run(dates[-1])
    print(json.dumps(result,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
