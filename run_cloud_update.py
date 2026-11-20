#!/usr/bin/env python3
"""Cloud wrapper. Publishes only derived data, not proprietary/large source files."""
from __future__ import annotations
import datetime as dt
from zoneinfo import ZoneInfo
from pathlib import Path
import subprocess
import sys
from publish_summary import publish

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'public'
CACHE=ROOT/'sp500_pit_cache'

def last_expected_us_session():
    now=dt.datetime.now(ZoneInfo('America/New_York'))
    d=now.date()
    if now.hour < 17:
        d-=dt.timedelta(days=1)
    while d.weekday()>=5:
        d-=dt.timedelta(days=1)
    # Exchange holidays are not inferred: source freshness validation will flag them.
    return d

def main():
    asof=last_expected_us_session()
    OUT.mkdir(exist_ok=True,parents=True)
    print('Requested US market session:',asof,flush=True)
    cmd=[sys.executable,str(ROOT/'sp500_pit_breadth_v4.py'), '--asof',str(asof), '--outdir',str(OUT), '--cache',str(CACHE)]
    result=subprocess.run(cmd,cwd=ROOT,check=False)
    if result.returncode not in (0,2):
        print('ERROR: Cannot update dataset. Keeping previous committed public report untouched.',file=sys.stderr)
        return result.returncode or 1
    publish(OUT)
    print('Cloud result published for download/inspection. Return code',result.returncode)
    return 0

if __name__=='__main__':raise SystemExit(main())
