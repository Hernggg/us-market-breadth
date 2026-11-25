#!/usr/bin/env python3
"""Personal-research calculation from thetrading.tools publicly downloaded JSON.
Use one request per invocation, without republishing the underlying raw series.
"""
import argparse
import csv
import datetime as dt
import json
import urllib.request
from pathlib import Path

URL = "https://www.thetrading.tools/data/market_breadth/nh_nl.json"
PERIODS = (1, 5, 10, 20, 60)

def calculate(payload, *, expected_date=None, calendar=None):
    rows=payload.get("data") if isinstance(payload,dict) else None
    if not isinstance(rows,list) or len(rows)<60:
        raise ValueError("Missing >=60 REAL exchange sessions; no guessing")
    dates=[]
    for row in rows:
        day=dt.date.fromisoformat(row["date"])
        hi,lo,n=(row[k] for k in ("new_highs","new_lows","total_issues"))
        if day.weekday()>4 or any(type(x) is not int for x in (hi,lo,n)) or not (0<=hi<=n<=10000 and 0<=lo<=n):
            raise ValueError("Malformed dated daily NH/NL count")
        if row.get("nh_nl_diff") is not None and row["nh_nl_diff"]!=hi-lo:
            raise ValueError("Historical daily NET mismatch")
        dates.append(day)
    if dates!=sorted(set(dates)):
        raise ValueError("Duplicate or out-of-order exchange trading day")
    if expected_date and dates[-1].isoformat()!=expected_date:
        raise ValueError("Source is stale: actual="+dates[-1].isoformat()+", expected="+expected_date)
    if calendar is not None and dates[-60:]!=calendar[-60:]:
        raise ValueError("Last 60 sessions differ from independent S&P 500 market-day calendar")
    if min(x["total_issues"] for x in rows[-60:])<2000:
        raise ValueError("Too few valid stocks within last 60 sessions")
    windows=[]
    for n in PERIODS:
        part=rows[-n:]
        hi=sum(x["new_highs"] for x in part)/n
        lo=sum(x["new_lows"] for x in part)/n
        windows.append({
            "window":"当日" if n==1 else str(n)+"日平均",
            "sessions":n,
            "avg_new_highs":round(hi,3),
            "avg_new_lows":round(lo,3),
            "avg_net_highs":round(hi-lo,3),
        })
    return {
        "source":URL,"asof_actual":dates[-1].isoformat(),
        "source_last_updated":payload.get("last_updated"),
        "universe":"third-party eligible US common-stock historical counts, current-membership survivorship bias",
        "latest_universe_count":rows[-1]["total_issues"],
        "min_universe_60d":min(x["total_issues"] for x in rows[-60:]),
        "max_universe_60d":max(x["total_issues"] for x in rows[-60:]),
        "last_60_market_dates_crosschecked":calendar is not None,
        "status":"REAL_VENDOR_DATA_60_SESSIONS_VERIFIED",
        "not_official":True,
        "source_rights":"Research quotations with attribution only; no systematic republication of raw data",
        "windows":windows,
    }

def load_calendar(path):
    with Path(path).open(encoding="utf-8-sig",newline="") as fh:
        dates=[dt.date.fromisoformat(row["date"]) for row in csv.DictReader(fh)]
    if len(dates)<60 or dates!=sorted(set(dates)):
        raise ValueError("Bad independent exchange-date calendar")
    return dates

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--expected-date",required=False)
    ap.add_argument("--calendar",required=False)
    ap.add_argument("--input",required=False,help="Optional locally authorized downloaded snapshot")
    opt=ap.parse_args()
    if opt.input:
        data=Path(opt.input).read_bytes()
    else:
        req=urllib.request.Request(URL,headers={
            "User-Agent":"Personal-Noncommercial-MarketBreadthResearch/1.0",
            "Accept":"application/json"})
        with urllib.request.urlopen(req,timeout=30) as response:
            data=response.read(9000001)
    if len(data)>9000000:raise ValueError("Public JSON exceeded 9MB safety limit")
    calendar=load_calendar(opt.calendar) if opt.calendar else None
    payload=json.loads(data)
    report=calculate(payload,expected_date=opt.expected_date,calendar=calendar)
    # The SAME real vendor file also contains separately dated Nasdaq-listed
    # eligible ordinary-stock histories: this is an EXCHANGE risk proxy, not
    # formal Nasdaq Composite PIT constituents nor all NASDAQ-listed securities.
    nasdaq_rows=[]
    for row in payload["data"]:
        hi=row.get("nasdaq_new_highs")
        lo=row.get("nasdaq_new_lows")
        n=row.get("nasdaq_issues")
        if all(type(v) is int for v in (hi,lo,n)):
            nasdaq_rows.append({"date":row["date"],"new_highs":hi,
                                "new_lows":lo,"total_issues":n,
                                "nh_nl_diff":hi-lo})
    if len(nasdaq_rows) != len(payload["data"]):
        raise ValueError("Cannot claim complete NASDAQ exchange-scope history")
    nasdaq=calculate({"data":nasdaq_rows,"last_updated":payload.get("last_updated")},
                     expected_date=opt.expected_date,calendar=calendar)
    nasdaq["universe"]="third-party NASDAQ-listed qualifying common stocks; NOT strict Nasdaq Composite members or vendor TradingView MAHQ/MALQ"
    print("REAL_ALL_US_52W_FIVE_WINDOWS_JSON_START")
    print(json.dumps({"all_us_qualifying_common_stocks":report,
                      "nasdaq_listed_qualifying_common_stocks":nasdaq},
                     ensure_ascii=False,indent=2))
    print("REAL_ALL_US_52W_FIVE_WINDOWS_JSON_END")

if __name__=="__main__":
    main()
