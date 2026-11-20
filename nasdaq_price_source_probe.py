#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only historical-price availability probe for Nasdaq listing candidates.

It samples real point-in-time Nasdaq directory names and queries historical
daily prices. It does NOT compute Nasdaq Composite breadth or claim that
Nasdaq-listed securities equal official COMP membership.

Never publish Yahoo raw historical quotes; only source/coverage diagnostics.
Yahoo chart is an undocumented service: use a capped sample and report blocks.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

from nasdaq_comp_candidate import verified_source, classification, AuditError

INDEX = "^IXIC"
REQUIRED_SESSIONS = 311  # 60 trailing sessions, with 251 prior closes for first day's 52W
MAX_SAMPLE = 24
DEFAULT_SAMPLE = 18
FIXED = ("AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "AMD")
USER_AGENT = "Mozilla/5.0 (compatible; us-market-breadth-research/1.0)"
NEW_YORK = ZoneInfo("America/New_York")


def symbols_for_day(rows, day):
    result = {}
    for ticker, start, end, record in rows:
        if start <= day and (end is None or day < end):
            if ticker in result:
                raise AuditError("Overlapping PIT intervals: " + ticker)
            result[ticker] = record
    return result


def choose_sample(rows, start, end, sample_size):
    if not 1 <= sample_size <= MAX_SAMPLE:
        raise AuditError("Sample size must be between 1 and 24")
    today = symbols_for_day(rows, end)
    first = symbols_for_day(rows, start)
    liquid = [x for x in FIXED if x in today and classification(today[x]) == "LIKELY_ELIGIBLE_TYPE"]
    # Deterministic selection, with an explicit inclusion of actual removed
    # directory names when they exist: don't test today's survivors only.
    former = sorted(
        t for t, r in first.items()
        if t not in today and classification(r) == "LIKELY_ELIGIBLE_TYPE"
    )
    current = sorted(t for t, r in today.items() if classification(r) == "LIKELY_ELIGIBLE_TYPE")
    unresolved = sorted(t for t, r in today.items() if classification(r) == "UNRESOLVED_TYPE")
    buckets = [("FIXED_LIQUID", liquid), ("FORMER_LISTED", former),
               ("CURRENT_LIKELY", current), ("CURRENT_UNRESOLVED", unresolved)]
    picked = []
    used = set()
    # Seed buckets with at least one non-survivor and one unresolved whenever
    # capacity allows, then select the rest deterministically.
    for kind, tickers in buckets:
        if kind in ("FORMER_LISTED", "CURRENT_UNRESOLVED") and len(picked) < sample_size and tickers:
            t = tickers[0]
            if t not in used:
                picked.append((t, kind)); used.add(t)
    for kind, tickers in buckets:
        for ticker in tickers:
            if len(picked) >= sample_size:
                return picked
            if ticker in used:
                continue
            picked.append((ticker, kind)); used.add(ticker)
    return picked


def yahoo_chart(ticker, timeout=20):
    symbol = ticker.replace(".", "-").replace("/", "-")
    errors = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{urllib.parse.quote(symbol, safe='')}?range=2y&interval=1d"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                body = response.read(1_800_001)
            if len(body) > 1_800_000:
                raise ValueError("RESPONSE_TOO_LARGE")
            parsed = json.loads(body)
            results = (parsed.get("chart") or {}).get("result")
            if not results:
                raise ValueError("EMPTY_RESULT")
            item = results[0]
            timestamp = item.get("timestamp") or []
            indicators = item.get("indicators") or {}
            quote = (indicators.get("quote") or [{}])[0]
            adj_items = indicators.get("adjclose") or []
            adj = adj_items[0].get("adjclose") if adj_items else None
            closes = quote.get("close") or []
            if len(timestamp) != len(closes):
                raise ValueError("CLOSE_TIMESTAMP_MISMATCH")
            if adj is not None and len(adj) != len(timestamp):
                raise ValueError("ADJ_TIMESTAMP_MISMATCH")
            # A split-and-dividend-adjusted close is required for comparability;
            # never silently replace with unadjusted close.
            if adj is None:
                raise ValueError("NO_ADJUSTED_CLOSE")
            result = {}
            for epoch, raw_close, raw_adj in zip(timestamp, closes, adj, strict=True):
                day = dt.datetime.fromtimestamp(int(epoch), NEW_YORK).date()
                if (raw_adj is not None and math.isfinite(float(raw_adj)) and float(raw_adj)>0
                        and raw_close is not None and math.isfinite(float(raw_close)) and float(raw_close)>0):
                    if day in result:
                        raise ValueError("DUPLICATE_DATE")
                    result[day] = float(raw_adj)
            return result, "OK"
        except Exception as error:
            kind = f"{type(error).__name__}"
            if isinstance(error, urllib.error.HTTPError):
                kind += f"_{error.code}"
                # Avoid repeatedly retrying if a provider is rate limiting.
                if error.code == 429:
                    return {}, "RATE_LIMITED_HTTP_429"
            errors.append(kind)
    return {}, "|".join(errors) or "UNKNOWN_SOURCE_ERROR"


def session_coverage(prices, index_sessions):
    """Count genuine consecutive-session lookbacks: no forward fill."""
    if len(index_sessions) < REQUIRED_SESSIONS:
        raise AuditError("Need >=311 index sessions for 60D 52W lookback audit")
    last = index_sessions[-REQUIRED_SESSIONS:]
    statuses = []
    for j in range(REQUIRED_SESSIONS - 60, REQUIRED_SESSIONS):
        day = last[j]
        if day not in prices:
            statuses.append({"date": day.isoformat(), "priced": False,
                             "ad": False, "ma50": False, "ma200": False, "hilo": False})
            continue
        def continuous(n):
            return all(d in prices for d in last[j - (n-1):j+1])
        ad = j >= 1 and last[j-1] in prices
        ma50 = continuous(50)
        ma200 = continuous(200)
        # 52W close-only extremes require 251 preceding daily closes + today.
        hilo = j >= 251 and continuous(252)
        statuses.append({"date": day.isoformat(), "priced": True,
                         "ad": ad, "ma50": ma50, "ma200": ma200, "hilo": hilo})
    return statuses


def main():
    p = argparse.ArgumentParser(description="RESEARCH ONLY Nasdaq price-history source probe")
    p.add_argument("--calendar", type=Path, default=Path("public/sp500_pit_daily.csv"))
    p.add_argument("--size", type=int, default=DEFAULT_SAMPLE)
    p.add_argument("--out", type=Path, default=Path("research/nasdaq_comp/price_source_probe.json"))
    args = p.parse_args()
    # Use the already-audited date pair and 60 actual sessions from GitHub CSV.
    from nasdaq_comp_candidate import load_calendar
    dates = load_calendar(args.calendar, None)
    meta, digest, rows, floor = verified_source()
    if dates[0] < floor:
        raise AuditError("PIT archive cannot substantiate requested date window")
    asof = dates[-1]
    sample = choose_sample(rows, dates[0], asof, args.size)
    index_data, index_status = yahoo_chart(INDEX)
    if index_status != "OK":
        raise AuditError("Cannot fetch Nasdaq exchange calendar: " + index_status)
    sessions = sorted(day for day in index_data if day <= asof)
    if len(sessions) < REQUIRED_SESSIONS:
        raise AuditError(f"Nasdaq historical calendar insufficient: {len(sessions)} sessions")
    tail = sessions[-60:]
    if tail != dates:
        raise AuditError("Nasdaq reference index calendar disagrees with published S&P 500 sessions")
    results = []
    # Only a small, rate-limited feasibility sample; full-universe download
    # requires a licensed/supported source or a separately accepted policy.
    def one(item):
        ticker, bucket = item
        prices, status = yahoo_chart(ticker)
        spans = session_coverage(prices, sessions) if status == "OK" else []
        eligible = {
            key: sum(int(s[key]) for s in spans)
            for key in ("priced", "ad", "ma50", "ma200", "hilo")
        }
        return {"ticker": ticker, "selection": bucket, "source_status": status,
                "history_bars": len(prices),
                "eligible_sessions_out_of_60": eligible,
                "first_price_date": min(prices).isoformat() if prices else None,
                "last_price_date": max(prices).isoformat() if prices else None}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for item in pool.map(one, sample):
            results.append(item)
    statuses = Counter(item["source_status"] for item in results)
    report = {
        "market": "NASDAQ_LISTING_CANDIDATE_PRICE_SOURCE_PROBE_NOT_COMPOSITE",
        "status": "RESEARCH_SAMPLE_ONLY",
        "eligible_for_us_market_publication": False,
        "asof_actual": asof.isoformat(),
        "first_session": dates[0].isoformat(),
        "calendar_source": "Yahoo ^IXIC historical daily sessions matched to existing S&P500 60-session calendar",
        "price_source": "Yahoo Finance undocumented v8 daily adjusted close",
        "point_in_time_archive": "https://github.com/TylerJForstrom/Stock-Data",
        "historical_membership_verified": False,
        "sample_size": len(sample),
        "source_status_counts": dict(statuses),
        "coverage": {
            key: {"eligible_member_days": sum(r["eligible_sessions_out_of_60"][key] for r in results),
                  "possible_member_days": len(results)*60}
            for key in ("priced", "ad", "ma50", "ma200", "hilo")
        },
        "limitations": [
            "These are sampled Nasdaq-listed security types, not actual Composite index membership",
            "Sample symbols do not establish full historical-price coverage, especially delisted shares",
            "52W denotes adjusted CLOSE-only extremes, not intraday 52-week highs/lows",
            "No raw prices or index breadth statistics published",
            "Yahoo v8 chart is unofficial and rate-limited; viability and usage terms must be reviewed",
        ],
        "symbols": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "asof": report["asof_actual"],
                      "sample": len(results), "sources": report["source_status_counts"],
                      "coverage": report["coverage"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
