#!/usr/bin/env python3
"""Isolated S&P 500 2026-11-19 EOD bridge proof of concept.

It never updates published public/latest.json. Mixed-source results are
EXPERIMENTAL until membership, adjustment and external quote checks pass.
"""
from __future__ import annotations

import csv
import datetime as dt
import json
import math
import time
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

import duckdb

from sp500_pit_breadth_v4 import ASSETS, calculate, download_if_needed, price_last_available

TARGET = dt.date(2026, 11, 19)
PRIOR = dt.date(2026, 11, 18)
CACHE = Path("candidate_probe_cache")
OUT = Path("candidate_probe_output")

def yahoo_total_return(ticker: str):
    symbol = ticker.replace(".", "-").replace("/", "-")
    errors = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        try:
            url = f"https://{host}/v8/finance/chart/{urllib.parse.quote(symbol)}?range=10d&interval=1d"
            request = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(request, timeout=16) as response:
                data = json.loads(response.read(1200000).decode("utf-8"))
            result = data["chart"]["result"][0]
            dates = [
                dt.datetime.fromtimestamp(int(t), ZoneInfo("America/New_York")).date()
                for t in result.get("timestamp", [])
            ]
            adj = result["indicators"]["adjclose"][0]["adjclose"]
            if TARGET not in dates or PRIOR not in dates:
                return ticker, None, "MISSING_DATE"
            old = adj[dates.index(PRIOR)]
            new = adj[dates.index(TARGET)]
            if old is None or new is None or not math.isfinite(float(old)) or not math.isfinite(float(new)) or old <= 0 or new <= 0:
                return ticker, None, "INVALID_ADJCLOSE"
            ratio = float(new) / float(old)
            if ratio < 0.5 or ratio > 1.5:
                return ticker, None, "UNUSUAL_TOTAL_RETURN"
            return ticker, ratio, "OK"
        except Exception as exc:
            errors.append(type(exc).__name__)
    return ticker, None, ",".join(errors)

def main():
    CACHE.mkdir(exist_ok=True)
    OUT.mkdir(exist_ok=True)
    files = {name: download_if_needed(CACHE, name, min_size) for name, min_size in ASSETS.items()}
    last = price_last_available(files["prices.parquet"])
    print("UPSTREAM_LAST", last, "TARGET", TARGET, flush=True)
    if last >= TARGET:
        raise RuntimeError("Upstream already includes target date; experimental bridge is unnecessary")
    if last != PRIOR:
        raise RuntimeError("Experimental bridge currently supports ONLY a one-session gap ending 2026-11-18")

    con = duckdb.connect()
    membership = files["membership_intervals.parquet"].as_posix()
    names = [
        row[0] for row in con.execute(
            """SELECT DISTINCT UPPER(CAST(ticker AS VARCHAR))
               FROM read_parquet(?)
               WHERE CAST(start AS DATE)<=?
                 AND ("end" IS NULL OR CAST("end" AS DATE)>?)
               ORDER BY 1""",
            [membership, TARGET, TARGET]
        ).fetchall()
    ]
    members = set(names)
    needed = sorted(members | {"SPY"})
    prices = files["prices.parquet"].as_posix()
    old_prices = {
        ticker: float(p)
        for ticker, p in con.execute(
            """SELECT UPPER(CAST(ticker AS VARCHAR)), CAST(adj_close AS DOUBLE)
               FROM read_parquet(?)
               WHERE CAST(date AS DATE)=?""",
            [prices, PRIOR]
        ).fetchall()
        if p is not None
    }
    print("MEMBERS", len(members), "PRIOR_PRICED", sum(s in old_prices for s in members), flush=True)
    if len(members) < 490 or len(members) > 510:
        raise RuntimeError("Unexpected PIT membership count")
    missing_prior = [s for s in needed if s not in old_prices]
    if missing_prior:
        raise RuntimeError("Previous-day price missing: "+str(missing_prior[:20]))

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(yahoo_total_return, needed))
    stat = Counter(status for _, _, status in results)
    print("YAHOO_STATUS", dict(stat), "total", len(needed), flush=True)
    failures = [(s, status) for s, ratio, status in results if ratio is None]
    print("YAHOO_FAILURES", failures[:35], flush=True)
    if len(failures) > 0:
        raise RuntimeError("Experimental proof requires 100% coverage; aborting rather than fabricating any quotes")

    patch = OUT / "patched_session.csv"
    with patch.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["date", "ticker", "adj_close", "source"])
        for ticker, ratio, status in results:
            writer.writerow([
                TARGET.isoformat(), ticker, format(old_prices[ticker] * ratio, ".14g"),
                "YAHOO_ADJRETURN_BRIDGE_EXPERIMENTAL"
            ])

    base = str(files["prices.parquet"].resolve()).replace("'", "''")
    csvpath = str(patch.resolve()).replace("'", "''")
    patched = OUT / "historical_plus_bridged.parquet"
    outfile = str(patched.resolve()).replace("'", "''")
    source_cols = {row[0] for row in con.execute(
        f"DESCRIBE SELECT * FROM read_parquet('{base}')"
    ).fetchall()}
    source = "CAST(source AS VARCHAR)" if "source" in source_cols else "CAST('' AS VARCHAR)"
    con.execute(f"""
        COPY (
          SELECT CAST(date AS DATE) AS date,
                 UPPER(CAST(ticker AS VARCHAR)) AS ticker,
                 CAST(adj_close AS DOUBLE) AS adj_close,
                 {source} AS source
          FROM read_parquet('{base}')
          WHERE CAST(date AS DATE) < DATE '{TARGET.isoformat()}'
          UNION ALL
          SELECT CAST(date AS DATE), CAST(ticker AS VARCHAR),
                 CAST(adj_close AS DOUBLE), CAST(source AS VARCHAR)
          FROM read_csv_auto('{csvpath}', header=true)
        ) TO '{outfile}' (FORMAT PARQUET, COMPRESSION ZSTD)
    """)
    con.close()
    print("BRIDGED_FILE_CREATED",patched.stat().st_size,flush=True)
    calculate(patched, files["membership_intervals.parquet"], files["recycled_tickers.csv"], OUT, TARGET)

    with (OUT/"sp500_pit_daily.csv").open(encoding="utf-8-sig",newline="") as stream:
        days = list(csv.DictReader(stream))
    prev = days[-2]; latest = days[-1]
    print("BRIDGED_PREV", {k: prev[k] for k in ("date","advances","declines","ma50_pct","ma200_pct","new_highs","new_lows")},flush=True)
    print("BRIDGED_LATEST", {k: latest[k] for k in ("date","expected_members","priced_members","advances","declines","ma50_pct","ma200_pct","new_highs","new_lows","price_coverage","ma200_coverage","hilo_coverage")},flush=True)
    if prev["date"]!=PRIOR.isoformat() or latest["date"]!=TARGET.isoformat():
        raise RuntimeError("Daily date validation failed")
    if int(prev["advances"])!=237 or int(prev["declines"])!=265:
        raise RuntimeError("Previous-day reconciliation failed: input history may have changed")
    if float(latest["price_coverage"])<0.99 or float(latest["hilo_coverage"])<0.95:
        raise RuntimeError("Insufficient candidate coverage")
    print("CANDIDATE_READY_ONLY: independent source agreement and membership audit are REQUIRED before public/latest.json can be replaced",flush=True)

if __name__=="__main__":
    main()
