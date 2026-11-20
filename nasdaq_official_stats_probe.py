#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only Nasdaq Trader YTD official NASDAQ-issues A/D audit.

Official NASDAQ Advances/Declines/Unchanged fields are NASDAQ-listed-issues
statistics. They are NOT demonstrated to have exactly the same constituent
universe as the NASDAQ Composite, and must not be labeled COMP index breadth.
This script never modifies S&P 500 or @us-market published output.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import re
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from nasdaq_comp_candidate import load_calendar, AuditError

BASE = "https://nasdaqtrader.com/dynamic/dailyfiles/daily{year}.csv"
MAX_BYTES = 5_000_000
WINDOWS = (1, 5, 10, 20, 60)

def norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.strip().lower())

def parse_day(value: str):
    val = value.strip().strip('"')
    for format_ in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y%m%d", "%Y/%m/%d", "%d-%b-%Y"):
        try:
            return dt.datetime.strptime(val, format_).date()
        except ValueError:
            pass
    raise ValueError(f"Bad date value: {val[:30]!r}")

def parse_number(value: str):
    raw = str(value or "").strip().replace(",", "").replace(" ", "").replace("$", "")
    if not raw or raw in {"N/A", "NA", "-", "--", "N.M."}:
        raise ValueError("Missing numeric data")
    return float(raw)

def fetch_csv(year: int):
    url = BASE.format(year=year)
    request = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (us-market-research; historical Nasdaq daily file)",
        "Accept": "text/csv,text/plain,application/octet-stream,*/*"
    })
    with urllib.request.urlopen(request, timeout=45) as response:
        raw = response.read(MAX_BYTES+1)
    if not raw or len(raw) > MAX_BYTES:
        raise AuditError("Official file empty or exceeds allowed size")
    # Some Nasdaq CSVs are offered as octet-stream; validate actual content.
    if raw.startswith((b"<html", b"<!DOC", b"%PDF", b"PK\x03\x04")):
        raise AuditError("Expected CSV but received HTML/PDF/ZIP")
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = raw.decode("cp1252")
    return url, decoded

def find_header(rows):
    for i, row in enumerate(rows[:25]):
        names = [norm(v) for v in row]
        adv = next((j for j,n in enumerate(names) if n in {"nasdaqadvances","advances"}), None)
        dec = next((j for j,n in enumerate(names) if n in {"nasdaqdeclines","declines"}), None)
        unch = next((j for j,n in enumerate(names) if n in {"nasdaqunchanged","unchanged"}), None)
        date = next((j for j,n in enumerate(names) if n in {"date","tradedate","day","trade_date"}), None)
        comp = next((j for j,n in enumerate(names) if n in {"nasdaqcompositeindex","nasdaqcomposite","compositeindex"}), None)
        computer = next((j for j,n in enumerate(names) if n in {"nasdaqcomputerindex","computerindex"}), None)
        if None not in (adv, dec, unch, date):
            return i, {"date":date, "advances":adv, "declines":dec, "unchanged":unch,
                       "composite":comp, "computer":computer}, row
    return None, None, rows[0] if rows else []

def reconstruct(raw_text: str, expected_sessions):
    parsed = [line for line in csv.reader(io.StringIO(raw_text)) if any(field.strip() for field in line)]
    header_i, indices, header = find_header(parsed)
    if indices is None:
        return {"status": "NEEDS_CSV_SCHEMA_REVIEW",
                "sample_headers": parsed[:3],
                "reason": "Could not unambiguously find NASDAQ Advances, Declines, Unchanged and Date fields"}
    columns = {k: header[v] if v is not None else None for k,v in indices.items()}
    data = {}
    errors = []
    for line_num, row in enumerate(parsed[header_i+1:], header_i+2):
        if len(row) <= max(indices[k] for k in ("date","advances","declines","unchanged")):
            continue
        try:
            day = parse_day(row[indices["date"]])
            adv,dec,unch = (parse_number(row[indices[k]]) for k in ("advances","declines","unchanged"))
            if any(not x.is_integer() or x < 0 for x in (adv,dec,unch)):
                raise ValueError("Negative/nonintegral issue counts")
            if (adv+dec+unch) < 1000 or (adv+dec+unch) > 10000:
                raise ValueError("Implausible daily Nasdaq-issues issue count")
            if day in data:
                raise ValueError("Duplicate trading date")
            item = {"date": day.isoformat(), "advances":int(adv),
                    "declines":int(dec), "unchanged":int(unch)}
            for field in ("composite","computer"):
                index = indices[field]
                if index is not None and index < len(row):
                    try:
                        item[field + "_index_level"] = parse_number(row[index])
                    except ValueError:
                        item[field + "_index_level"] = None
            data[day] = item
        except ValueError as e:
            if len(errors) < 5:
                errors.append({"line":line_num, "reason":str(e)})
    if not data:
        return {"status":"NEEDS_CSV_SCHEMA_REVIEW", "columns":columns,
                "sample_headers":parsed[:3],"errors":errors}
    missing = [day.isoformat() for day in expected_sessions if day not in data]
    if missing:
        return {"status":"INCOMPLETE_REQUIRED_60_SESSIONS",
                "actual_latest":max(data).isoformat(), "columns":columns,
                "missing_session_dates":missing,"valid_observed_sessions":len(data),
                "errors":errors}
    daily = [data[d] for d in expected_sessions]
    windows = []
    for n in WINDOWS:
        part = daily[-n:]
        advances = sum(r["advances"] for r in part)
        declines = sum(r["declines"] for r in part)
        unchanged = sum(r["unchanged"] for r in part)
        windows.append({
            "sessions":n, "end": part[-1]["date"],
            "avg_advances":round(advances/n,3),
            "avg_declines":round(declines/n,3),
            "avg_unchanged":round(unchanged/n,3),
            "ad_ratio":round(advances/declines,5) if declines else None,
            "avg_net_advances":round((advances-declines)/n,3)
        })
    return {"status":"FULL_60_SESSION_NASDAQ_ISSUES_AD_AVAILABLE",
            "source_columns":columns,
            "calendar_status":"MATCHED_60_SESSIONS",
            "actual_latest":expected_sessions[-1].isoformat(),
            "actual_first":expected_sessions[0].isoformat(),
            "daily":daily, "windows":windows,
            "minor_nondate_errors":errors}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--calendar",type=Path,default=Path("public/sp500_pit_daily.csv"))
    parser.add_argument("--out",type=Path,default=Path("research/nasdaq_comp/official_nasdaq_issues_ad.json"))
    args = parser.parse_args()
    days = load_calendar(args.calendar, None)
    url, text = fetch_csv(days[-1].year)
    result = reconstruct(text, days)
    report = {
        "market":"NASDAQ_LISTED_ISSUES_STATISTICS_NOT_VERIFIED_COMP_INDEX",
        "official_data":True,
        "actual_nasdaq_composite_constituents":False,
        "eligible_for_us_market_comp_publication":False,
        "source":url,
        "notes":[
            "Official Nasdaq Trader daily market statistics for Nasdaq-listed issues",
            "Nasdaq Trader does NOT say these figures are exactly Nasdaq Composite constituent-only A/D",
            "Do not count ETF/test/security-type issues as COMP by assumption",
            "No 50/200DMA or 52-week new highs/lows provided by this source",
            "Source can serve as independent A/D comparison to future reconstructed COMP breadth"
        ],
        **result,
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"market":report["market"],"status":report["status"],
                      "actual_latest":report.get("actual_latest"),
                      "columns":report.get("source_columns"),
                      "missing":report.get("missing_session_dates"),
                      "windows":report.get("windows")},ensure_ascii=False))
    return 0 if result["status"].startswith("FULL_60_") else 2


if __name__ == "__main__":
    raise SystemExit(main())
