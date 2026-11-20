#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only Nasdaq Trader multi-year A/D archive (NASDAQ-LISTED ISSUES).

This is NOT strict Nasdaq Composite constituent-only breadth.
It does not replace public/latest.json or the S&P production update pipeline.

Sources: Nasdaq Trader annual "Daily Market Statistics" CSV by calendar year.
Keep the annual source date, raw field names, missing-date/quality flags.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import math
from collections import Counter
from pathlib import Path

from nasdaq_official_stats_probe import (
    fetch_csv, find_header, parse_day, parse_number, load_calendar, AuditError, WINDOWS
)

EARLIEST_YEAR = 2006


def annual_file(year):
    url, raw = fetch_csv(year)
    rows = [r for r in csv.reader(io.StringIO(raw)) if any(c.strip() for c in r)]
    header_index, indices, header = find_header(rows)
    if indices is None:
        raise AuditError(f"{year}: cannot identify essential Nasdaq A/D columns: {rows[:2]}")
    cleaned, warnings = {}, []
    required = ("date", "advances", "declines", "unchanged")
    maxidx = max(indices[k] for k in required)
    for line_num, raw_row in enumerate(rows[header_index + 1:], header_index + 2):
        if len(raw_row) <= maxidx:
            if len(warnings) < 20: warnings.append(f"line {line_num}: short row")
            continue
        try:
            date = parse_day(raw_row[indices["date"]])
        except ValueError as exc:
            if len(warnings) < 20: warnings.append(f"line {line_num}: {exc}")
            continue
        if date.year != year:
            raise AuditError(f"{year}: foreign-year date {date}")
        if date in cleaned:
            raise AuditError(f"{year}: duplicate day {date}")
        try:
            numbers = [parse_number(raw_row[indices[k]]) for k in required[1:]]
            if any(not math.isfinite(x) or x < 0 or not x.is_integer() for x in numbers):
                raise ValueError("nonfinite, negative, or non-integral issue counts")
            if not (1500 <= sum(numbers) <= 10000):
                raise ValueError(f"issue-count total out of bounds: {sum(numbers)}")
        except ValueError as exc:
            if len(warnings) < 20: warnings.append(f"{date}: invalid A/D: {exc}")
            continue
        rec = {"date": date.isoformat(), "advances":int(numbers[0]),
               "declines":int(numbers[1]), "unchanged":int(numbers[2])}
        for tag in ("composite","computer"):
            i = indices.get(tag)
            if i is not None and i < len(raw_row):
                try:
                    level = parse_number(raw_row[i])
                    rec[tag+"_index_level"] = level if level>0 and math.isfinite(level) else None
                except ValueError:
                    rec[tag+"_index_level"] = None
        cleaned[date] = rec
    # On the first market days of January, a valid YTD file can have <100
    # trading sessions. Distinguish incomplete currently published years from
    # previously archived full years in main(); never assert a complete year.
    if not cleaned:
        raise AuditError(f"{year}: no valid Nasdaq A/D data")
    return url, cleaned, warnings, header


def windows_for(daily):
    out = []
    for n in WINDOWS:
        if len(daily) < n:
            raise AuditError(f"Need {n} observations, got {len(daily)}")
        part = daily[-n:]
        adv = sum(r["advances"] for r in part)
        dec = sum(r["declines"] for r in part)
        unch = sum(r["unchanged"] for r in part)
        ref = daily[-n-1] if len(daily)>n else None
        ret = {}
        for name in ("composite","computer"):
            last = daily[-1].get(name+"_index_level")
            prev = ref.get(name+"_index_level") if ref else None
            ret[name+"_index_return_pct"] = round(100*(last/prev -1),4) if (
                last is not None and prev is not None and prev>0
            ) else None
        out.append({
            "sessions":n, "asof_actual":daily[-1]["date"],
            "avg_advances":round(adv/n,3),
            "avg_declines":round(dec/n,3),
            "avg_unchanged":round(unch/n,3),
            "ad_ratio":round(adv/dec,5) if dec else None,
            "avg_net_advances":round((adv-dec)/n,3),
            "index_return_reference_date":ref["date"] if ref else None,
            **ret
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-year", type=int, default=2026,
                        help="Earliest LOCAL archived year; historical Nasdaq Trader CSV links are not guaranteed")
    parser.add_argument("--calendar", type=Path, default=Path("public/sp500_pit_daily.csv"))
    parser.add_argument("--outdir", type=Path, default=Path("research/nasdaq_comp"))
    args = parser.parse_args()
    requested = load_calendar(args.calendar, None)[-1]
    if not EARLIEST_YEAR <= args.first_year <= requested.year:
        raise AuditError("Invalid starting year")
    annuals, all_days, warnings, headers = {}, {}, {}, {}
    old_archive = args.outdir / "official_nasdaq_issues_daily_history.csv"
    past_rows = 0
    if old_archive.exists():
        with old_archive.open(encoding="utf-8-sig",newline="") as f:
            for rec in csv.DictReader(f):
                day=dt.date.fromisoformat(rec["date"])
                if day > requested:
                    raise AuditError("Old archive contains future trading dates")
                if day in all_days:
                    raise AuditError("Duplicate dates in previously saved archive")
                try:
                    a,d,u=(int(rec[k]) for k in ("advances","declines","unchanged"))
                    if min(a,d,u)<0 or not 1500<=a+d+u<=10000:
                        raise ValueError("Implausible prior issue counts")
                    stored={"date":day.isoformat(),"advances":a,"declines":d,"unchanged":u}
                    for tag in ("composite","computer"):
                        value=rec.get(tag+"_index_level")
                        stored[tag+"_index_level"]=float(value) if value not in (None,"") else None
                    all_days[day]=stored
                    past_rows+=1
                except (ValueError,KeyError) as exc:
                    raise AuditError("Corrupt historical archive: "+str(exc)) from exc
    # The public Nasdaq Trader annual index lists ONLY THE CURRENT YEAR.
    # Persist the current YTD file into Git for post-December archive continuity.
    year=requested.year
    url,items,warn,header=annual_file(year)
    annuals[str(year)]={"url":url,"sessions":len(items),
                        "first":min(items).isoformat(),"last":max(items).isoformat()}
    warnings[str(year)]=warn
    headers[str(year)]=header
    changed_prior_dates=[]
    for day,rec in items.items():
        if day in all_days and all_days[day]!=rec:
            changed_prior_dates.append(day.isoformat())
        all_days[day]=rec
    dates = sorted(d for d in all_days if d <= requested)
    if len(dates) < 60 or dates[-1] < requested - dt.timedelta(days=14):
        raise AuditError("Archive too short for rolling 60 day analysis or older than two weeks")
    # A revision across existing dates should be visible in the source audit;
    # the annual provider is authoritative for the active calendar year.
    # Source will sometimes lag 1-2 sessions behind SP500's validated dates.
    # Refuse GAPS INSIDE the last source-overlapping 60 sessions.
    recent_calendar = load_calendar(args.calendar, None)
    overlap = [d for d in recent_calendar if d <= dates[-1]]
    absent = [d.isoformat() for d in overlap if d not in all_days]
    if absent:
        raise AuditError("Official archive missing internal reference sessions: " + str(absent))
    daily = [all_days[d] for d in dates]
    windows = windows_for(daily)
    asof = dates[-1]
    report = {
        "market":"NASDAQ_LISTED_ISSUES_STATISTICS_NOT_STRICT_COMP",
        "official_data": True,
        "official_nasdaq_composite_constituents": False,
        "eligible_for_us_market_comp_publication": False,
        "asof_actual":asof.isoformat(),
        "requested_session":requested.isoformat(),
        "freshness":"DATE_MATCHED" if asof==requested else "SOURCE_LAGGED",
        "requested_missing_sessions":[d.isoformat() for d in recent_calendar if d>asof],
        "first_source_day":dates[0].isoformat(), "source_trading_sessions":len(dates),
        "annual_files":annuals, "headers":headers, "warnings":warnings,
        "previously_archived_rows":past_rows,
        "official_revision_count":len(changed_prior_dates),
        "official_revised_dates_sample":changed_prior_dates[:20],
        "historical_backfill_limitation":"Nasdaq Trader public page currently exposes current-year CSV only. Prior years only if archived previously; do not assume public historical annual file URLs exist.",
        "last_day":daily[-1], "windows":windows,
        "note":"Nasdaq Trader NASDAQ-listed issues A/D, NOT verified member-only Nasdaq Composite index A/D. Includes ETFs in listing universe. Composite and Computer index levels are performance context, NOT breadth.",
    }
    args.outdir.mkdir(parents=True,exist_ok=True)
    with (args.outdir / "official_nasdaq_issues_daily_history.csv").open("w",encoding="utf-8",newline="") as f:
        fieldnames=["date","advances","declines","unchanged","composite_index_level","computer_index_level"]
        writer=csv.DictWriter(f,fieldnames=fieldnames,extrasaction="ignore")
        writer.writeheader()
        writer.writerows(daily)
    (args.outdir / "official_nasdaq_issues_history_summary.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"
    )
    print(json.dumps({"status":"RESEARCH_COMPLETED","asof":asof.isoformat(),
                      "sessions":len(daily),"years":annuals,
                      "last":report["last_day"],"windows":windows,
                      "source_lag":report["requested_missing_sessions"]},ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
