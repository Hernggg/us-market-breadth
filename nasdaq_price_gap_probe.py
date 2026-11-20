#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only bounded second-source gap probe for one day's Nasdaq sample.

Checks whether Yahoo Finance has historical adjusted closes for a deterministic
sample of Nasdaq listed common-like candidates missing from a one-day bulk
Parquet SAMPLE. Never saves prices, tickers, vendor files or patch data.
This cannot validate actual Nasdaq Composite index membership.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
import tempfile
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from nasdaq_bulk_price_probe import (
    URL_BASE, MAX_SAMPLE_BYTES, candidate_tickers, AuditError
)
from nasdaq_comp_candidate import verified_source, load_calendar
from nasdaq_price_source_probe import yahoo_chart, session_coverage, REQUIRED_SESSIONS

SAMPLE_SIZE = 24


def representative_gap_sample(missing, n=SAMPLE_SIZE):
    if not missing or n<1:
        return []
    return sorted(missing, key=lambda s: hashlib.sha256(("missing_bulk:" + s).encode()).hexdigest())[:n]


def audit(asof):
    import duckdb
    meta, _, intervals, floor = verified_source()
    candidate, unresolved = candidate_tickers(intervals, asof)
    url=URL_BASE+asof.isoformat()+".parquet"
    request=urllib.request.Request(url,headers={"User-Agent":"Mozilla/5.0 (research-only source test)"})
    with tempfile.TemporaryDirectory(prefix="nasdaq_price_gap_") as t:
        p=Path(t)/"sample.parquet"
        with urllib.request.urlopen(request,timeout=40) as resp,p.open("wb") as f:
            data=resp.read(MAX_SAMPLE_BYTES+1)
            if len(data)>MAX_SAMPLE_BYTES:
                raise AuditError("Vendor sample size exceeded cap")
            f.write(data)
        if p.open("rb").read(4)!=b"PAR1":
            raise AuditError("Vendor sample is not Parquet")
        con=duckdb.connect()
        try:
            dates=con.execute("SELECT count(DISTINCT CAST(date AS DATE)), min(CAST(date AS DATE)) FROM read_parquet(?)",[str(p)]).fetchone()
            if dates[0]!=1 or dates[1]!=asof:
                raise AuditError("Price sample's date does not match the PIT session")
            quoted={r[0].strip().upper().replace("-",".") for r in con.execute(
                "SELECT CAST(symbol AS VARCHAR) FROM read_parquet(?)",[str(p)]).fetchall() if r[0]}
        finally:
            con.close()
    missing=candidate-quoted
    control=candidate & quoted
    sample=representative_gap_sample(missing)
    controls=sorted(control,key=lambda s:hashlib.sha256(("control:"+s).encode()).hexdigest())[:6]

    calendar,status=yahoo_chart("^IXIC")
    if status!="OK":
        raise AuditError("Yahoo reference index 2y calendar unavailable: "+status)
    index_days=sorted(d for d in calendar if d<=asof)
    if len(index_days)<REQUIRED_SESSIONS or index_days[-1]!=asof:
        raise AuditError("Yahoo index reference calendar lacks 311 sessions to date")

    def one(x):
        ticker,bucket=x
        prices,status=yahoo_chart(ticker)
        eligible={"priced":0,"ad":0,"ma50":0,"ma200":0,"hilo":0}
        if status=="OK":
            spans=session_coverage(prices,index_days)
            eligible={metric:sum(int(d[metric]) for d in spans)
                      for metric in eligible}
        return {"bucket":bucket,"status":status,
                "priced_current_day": asof in prices,
                "has_full_252_close_52w_lookback": bool(prices) and
                     sum(int(d["hilo"]) for d in session_coverage(prices,index_days)[-1:])==1
                     if status=="OK" else False,
                "eligible_sessions_last_60":eligible}

    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(one,[(s,"BULK_MISSING") for s in sample]+
                                  [(s,"BULK_PRESENT_CONTROL") for s in controls]))
    by_bucket={}
    for bucket in ("BULK_MISSING","BULK_PRESENT_CONTROL"):
        selected=[x for x in results if x["bucket"]==bucket]
        by_bucket[bucket]={
            "selected":len(selected),
            "yahoo_statuses":dict(Counter(x["status"] for x in selected)),
            "yahoo_price_for_asof":sum(x["priced_current_day"] for x in selected),
            "yahoo_valid_252_session_hilo":sum(x["has_full_252_close_52w_lookback"] for x in selected),
            "yahoo_valid_60day_ma200_member_days":sum(x["eligible_sessions_last_60"]["ma200"] for x in selected),
            "max_possible_60day_member_days":60*len(selected),
        }
    return {
        "status":"RESEARCH_ONLY_BOUNDED_VENDOR_GAP_EVALUATION",
        "asof":asof.isoformat(),
        "licensing_notice":"No vendor prices, identifiers, or datasets saved; test-sample-only evaluation; source terms prohibit sample redistribution.",
        "not_official_comp_membership":True,
        "vendor_daily_price_candidate_universe":len(candidate),
        "vendor_daily_price_candidate_missing":len(missing),
        "sample_bias":"Deterministic SHA-256 selection of 24 daily price gaps, plus 6 vendor-present controls; NOT a full-universe coverage estimate.",
        "comparison":by_bucket,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",type=Path,default=Path("public/sp500_pit_daily.csv"))
    p.add_argument("--asof",default="2026-11-19")
    args=p.parse_args()
    date=load_calendar(args.calendar,args.asof)[-1]
    print(json.dumps(audit(date),ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
