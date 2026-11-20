#!/usr/bin/env python3
"""Cloud updater: use third-party PIT source, then guarded one-day Yahoo fallback.

Never publish a stale or failed result as a newly completed trading session.
No raw Yahoo quote files or large source Parquet objects are uploaded to GitHub.
"""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path
import shutil
import subprocess
import sys
from zoneinfo import ZoneInfo

from publish_summary import publish

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"public"
WORK=ROOT/"sp500_update_work"
CACHE=ROOT/"sp500_pit_cache"
PUBLISHED=[
    "latest.json",
    "latest.md",
    "sp500_pit_daily.csv",
    "sp500_pit_windows.csv",
    "sp500_pit_missing.csv",
    "sp500_pit_quality_report.txt",
    "sp500_pit_update_status.txt",
]

def last_expected_us_session():
    now=dt.datetime.now(ZoneInfo("America/New_York"))
    day=now.date()
    if now.hour<17:
        day-=dt.timedelta(days=1)
    while day.weekday()>=5:
        day-=dt.timedelta(days=1)
    # Date verified against SPY sessions by the fallback;
    # U.S. holidays can still trigger a non-publish status.
    return day

def run(command):
    print("RUNNING:", " ".join(command), flush=True)
    return subprocess.run(command,cwd=ROOT,check=False).returncode

def main():
    asof=last_expected_us_session()
    WORK.mkdir(exist_ok=True,parents=True)
    OUT.mkdir(exist_ok=True,parents=True)
    print("Expected completed US session",asof,flush=True)
    native=[
        sys.executable,str(ROOT/"sp500_pit_breadth_v4.py"),
        "--asof",str(asof),"--outdir",str(WORK),"--cache",str(CACHE),
    ]
    result=run(native)
    if result==2:
        print("Upstream price file is stale. Trying safeguarded Yahoo one-session fallback.",flush=True)
        fallback=[
            sys.executable,str(ROOT/"bridge_latest_session.py"),
            "--asof",str(asof),"--outdir",str(WORK),"--cache",str(CACHE),
        ]
        result=run(fallback)
    if result!=0:
        print("ERROR: source and/or fallback did not produce validated current-session output. Existing public/latest.json remains unchanged.",file=sys.stderr,flush=True)
        return result or 1

    status_file=WORK/"sp500_pit_update_status.txt"
    if not status_file.exists() or "FRESHNESS: DATE_MATCHED" not in status_file.read_text(encoding="utf-8"):
        print("ERROR: computed data are not confirmed current; refusing publication.",file=sys.stderr,flush=True)
        return 1
    daily_file=WORK/"sp500_pit_daily.csv"
    with daily_file.open(encoding="utf-8-sig",newline="") as stream:
        daily=list(csv.DictReader(stream))
    if len(daily)!=60 or daily[-1]["date"]!=asof.isoformat():
        print("ERROR: actual latest daily breadth date does not match expected date.",file=sys.stderr,flush=True)
        return 1

    report=publish(WORK)
    if report.get("asof_actual")!=asof.isoformat():
        print("ERROR: summary date mismatch; refusing publication.",file=sys.stderr,flush=True)
        return 1
    # Commit a consistent complete set of small, derived outputs only.
    for name in PUBLISHED:
        source=WORK/name
        if not source.is_file():
            raise FileNotFoundError("Missing audited output: "+name)
        shutil.copy2(source,OUT/name)
    print("PUBLISHED_CURRENT_SESSION",asof, "mode",report.get("method"),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
