#!/usr/bin/env python3
"""One-shot personal-research validation and 5-window computation from publicly downloadable
The Trading Tools market breadth data. Never persist the provider's history to public GitHub.

Dataset catalog specifically licenses free personal/research/education uses with attribution,
see https://www.thetrading.tools/datasets. Systematic republication needs written permission.
"""
from __future__ import annotations
import csv
import datetime as dt
import json
import urllib.request
from pathlib import Path

ROOT = "https://www.thetrading.tools/data/market_breadth/"
PATHS = {"ad":"ad_line.json","ma":"market_breadth.json","nhnl":"nh_nl.json"}
WINDOWS = (1,5,10,20,60)

def load_public_json(path: str, *, limit=15_000_000):
    url=ROOT+path
    req=urllib.request.Request(url,headers={
        "User-Agent":"Personal-Noncommercial-USMarketBreadth/1.0",
        "Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=35) as f:
        data=f.read(limit+1)
    if len(data)>limit:
        raise ValueError("Oversized market vendor dataset: "+path)
    return json.loads(data)

def independent_calendar(path):
    with open(path,encoding="utf-8-sig",newline="") as f:
        dates=[row["date"] for row in csv.DictReader(f)]
    if len(dates)<60 or dates!=sorted(set(dates)):
        raise ValueError("Independent PIT 60-session calendar incomplete")
    return dates[-60:]

def valid_rows(payload,calendar,name):
    rows=payload.get("data")
    if not isinstance(rows,list) or len(rows)<60:
        raise ValueError(name+" missing 60 real market sessions")
    stamps=[r.get("date") for r in rows]
    if stamps!=sorted(set(stamps)):
        raise ValueError(name+" duplicate/unsorted rows")
    for day in stamps[-60:]:
        date=dt.date.fromisoformat(day)
        if date.weekday()>=5:raise ValueError(name+" contains weekend")
    if stamps[-60:]!=calendar:
        raise ValueError(name+" mismatched US equity market sessions "+
                         str({"source_last":stamps[-1],"calendar_last":calendar[-1]}))
    return rows[-60:]

def count(x,label):
    if type(x) is not int or x<0 or x>25000:raise ValueError("Invalid stock issue count: "+label)
    return x

def percentage(x,label):
    if type(x) not in (float,int) or not (0 <= x <= 100):
        raise ValueError("Invalid 0-100 moving average %: "+label)
    return float(x)

def calc_ad(rows,adv,dec,unchanged=None):
    out=[]
    for n in WINDOWS:
        a=sum(count(r[adv],adv) for r in rows[-n:])
        b=sum(count(r[dec],dec) for r in rows[-n:])
        if unchanged:
            c=sum(count(r[unchanged],unchanged) for r in rows[-n:])
        else:c=None
        out.append({
            "sessions":n,
            "avg_advances":round(a/n,3),
            "avg_declines":round(b/n,3),
            "avg_unchanged":round(c/n,3) if c is not None else None,
            "ad_ratio":round(a/b,5) if b else None})
    return out

def calc_ma(rows):
    out=[]
    for n in WINDOWS:
        a=sum(percentage(r["pct_above_50d"],"pct_above_50d") for r in rows[-n:])/n
        b=sum(percentage(r["pct_above_200d"],"pct_above_200d") for r in rows[-n:])/n
        out.append({"sessions":n,"avg_above_50dma_pct":round(a,3),
                    "avg_above_200dma_pct":round(b,3)})
    return out

def calc_nhnl(rows,hi,lo):
    out=[]
    for n in WINDOWS:
        a=sum(count(r[hi],hi) for r in rows[-n:])/n
        b=sum(count(r[lo],lo) for r in rows[-n:])/n
        out.append({"sessions":n,"avg_new_highs":round(a,3),"avg_new_lows":round(b,3),
                    "avg_net_new_highs":round(a-b,3)})
    return out

def validate_and_compute(ad,ma,nh,calendar):
    A=valid_rows(ad,calendar,"AD")
    M=valid_rows(ma,calendar,"MA")
    H=valid_rows(nh,calendar,"NHNL")
    for r in A:
        a=count(r["advancing"],"advancing")
        b=count(r["declining"],"declining")
        c=count(r["unchanged"],"unchanged")
        if not 2000<=a+b+c<=10000:
            raise ValueError("Invalid total ALL-US A/D daily membership")
        if r.get("net_advances") is not None and r["net_advances"]!=a-b:
            raise ValueError("Daily A/D net does not reconcile")
        n_adv=count(r["nasdaq_advancing"],"nasdaq_advancing")
        n_dec=count(r["nasdaq_declining"],"nasdaq_declining")
        n_unch=count(r["nasdaq_unchanged"],"nasdaq_unchanged")
        if not 500<=n_adv+n_dec+n_unch<=6000:
            raise ValueError("Invalid NASDAQ listed-source breadth membership")
    for r in M:
        n=count(r["market_stocks"],"market_stocks")
        if n<2000:raise ValueError("Market SMA denominator too low")
        percentage(r["pct_above_50d"],"pct_above_50d")
        percentage(r["pct_above_200d"],"pct_above_200d")
    for r in H:
        a=count(r["new_highs"],"new_highs")
        b=count(r["new_lows"],"new_lows")
        n=count(r["total_issues"],"total_issues")
        if a>n or b>n:raise ValueError("High/low exceeds eligible sample size")
        if r.get("nh_nl_diff") is not None and r["nh_nl_diff"]!=a-b:
            raise ValueError("Daily NH/NL diff mismatch")
    return {
        "source":"https://www.thetrading.tools/datasets",
        "actual_asof_date":calendar[-1],
        "calendar": {"start_60":calendar[0],"end_60":calendar[-1],"valid_session_count":len(calendar)},
        "all_us_ad": {"source_file":PATHS["ad"],"source_end":A[-1]["date"],
                      "daily_sample_size":A[-1]["advancing"]+A[-1]["declining"]+A[-1]["unchanged"],
                      "periods":calc_ad(A,"advancing","declining","unchanged")},
        "all_us_ma": {"source_file":PATHS["ma"],"source_end":M[-1]["date"],
                      "daily_sample_size":M[-1]["market_stocks"],
                      "periods":calc_ma(M)},
        "all_us_52w": {"source_file":PATHS["nhnl"],"source_end":H[-1]["date"],
                       "daily_sample_size":H[-1]["total_issues"],
                       "periods":calc_nhnl(H,"new_highs","new_lows")},
        "nasdaq_exchange_ad": {
            "source_file":PATHS["ad"],"source_end":A[-1]["date"],
            "daily_sample_size":A[-1]["nasdaq_advancing"]+A[-1]["nasdaq_declining"]+A[-1]["nasdaq_unchanged"],
            "periods":calc_ad(A,"nasdaq_advancing","nasdaq_declining","nasdaq_unchanged")},
        "warning":"Vendor-defined eligible samples vary among A/D, MA, NHNL. NOT identical to S&P PIT or ScreenerCharts universe. Nasdaq venue is NOT Nasdaq Composite PIT.",
        "license":"Personal noncommercial research with attribution; systematic public redistribution requires permission",
        "source_is_official_exchange":False,
    }

def main():
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument("--calendar",default="public/sp500_pit_daily.csv")
    op=ap.parse_args()
    calendar=independent_calendar(op.calendar)
    data={k:load_public_json(v) for k,v in PATHS.items()}
    out=validate_and_compute(data["ad"],data["ma"],data["nhnl"],calendar)
    print("REAL_US_60DAY_BREADTH_START")
    print(json.dumps(out,ensure_ascii=False,indent=2))
    print("REAL_US_60DAY_BREADTH_END")

if __name__=="__main__":main()
