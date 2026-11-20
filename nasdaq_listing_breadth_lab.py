#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nasdaq *listed security SAMPLE* rolling-breadth calculation prototype.

IMPORTANT: NOT Composite constituents, not statistically representative, not
for @us-market production, and not to be used as an index/market signal.
Evaluates actual historical prices for <= 24 deterministic sampled tickers;
prints/publishes only aggregates and source-quality metrics, NOT stock prices.

Price source: unofficial Yahoo chart history; terms/access subject to change.
Adjusted high/low is approximate: daily unadjusted OHLC multiplied by the
Yahoo adjusted-close / raw-close factor (including corporate-action revisions).
A/D, moving averages and 52-week adjusted intraday extremes require complete
daily observations at every underlying exchange trading session. Gaps never
forward-fill; newly listed names with <252 sessions do NOT count as 52W eligible.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import statistics
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo

from nasdaq_comp_candidate import verified_source, classification, load_calendar, AuditError
from nasdaq_price_source_probe import symbols_for_day, choose_sample, yahoo_chart, USER_AGENT

PERIODS=(1,5,10,20,60)
MAX_SAMPLE=24
REQUIRED_CALENDAR_SESSIONS=311
NY=ZoneInfo("America/New_York")


def parse_adjusted_ohlc(item):
    dates=item.get("timestamp") or []
    ind=item.get("indicators") or {}
    quote=(ind.get("quote") or [{}])[0]
    adjusted=(ind.get("adjclose") or [{}])[0].get("adjclose")
    closes=quote.get("close") or []
    highs=quote.get("high") or []
    lows=quote.get("low") or []
    if adjusted is None:
        raise ValueError("No Yahoo adjusted-close history")
    if not all(len(series)==len(dates) for series in (closes,highs,lows,adjusted)):
        raise ValueError("Misaligned OHLC timestamps")
    bars={}
    for stamp,raw_c,raw_h,raw_l,adj_c in zip(dates,closes,highs,lows,adjusted,strict=True):
        day=dt.datetime.fromtimestamp(int(stamp),NY).date()
        if day in bars:
            raise ValueError("Duplicate New York market date")
        def valid(v):
            try:return v is not None and math.isfinite(float(v)) and float(v)>0
            except (TypeError,ValueError,OverflowError):return False
        adj_close=float(adj_c) if valid(adj_c) else None
        high,low=None,None
        if all(valid(x) for x in (raw_c,raw_h,raw_l,adj_c)):
            factor=float(adj_c)/float(raw_c)
            high=float(raw_h)*factor
            low=float(raw_l)*factor
            if not (0<low<=high):
                high,low=None,None
        bars[day]={"close":adj_close,"high":high,"low":low}
    return bars


def fetch_yahoo_ohlc(ticker,timeout=25):
    symbol=ticker.replace(".","-").replace("/","-")
    attempts=[]
    for host in ("query1.finance.yahoo.com","query2.finance.yahoo.com"):
        url=f"https://{host}/v8/finance/chart/{urllib.parse.quote(symbol,safe='')}?range=2y&interval=1d"
        req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"application/json"})
        try:
            with urllib.request.urlopen(req,timeout=timeout) as res:
                raw=res.read(1_800_001)
            if len(raw)>1_800_000:
                raise ValueError("Oversized Yahoo payload")
            parsed=json.loads(raw)
            results=(parsed.get("chart") or {}).get("result")
            if not results:
                raise ValueError("No chart result")
            return parse_adjusted_ohlc(results[0]),"OK"
        except urllib.error.HTTPError as err:
            if err.code==429:
                return {},"SOURCE_RATE_LIMITED_429"
            attempts.append("HTTP_"+str(err.code))
        except (ValueError,KeyError,TypeError,urllib.error.URLError,TimeoutError) as err:
            attempts.append(type(err).__name__)
    return {},"|".join(attempts) if attempts else "UNKNOWN_ERROR"


def stat_day(day,all_calendar, prices, active_symbols):
    j=all_calendar.index(day)
    if j<251:
        raise AuditError("Calendar must have at least 251 earlier sessions before the 60D window starts")
    today=all_calendar[j]
    yesterday=all_calendar[j-1]
    counters={"advances":0,"declines":0,"unchanged":0,
              "ma50_above":0,"ma200_above":0,"new_highs":0,"new_lows":0,
              "ad_eligible":0,"ma50_eligible":0,"ma200_eligible":0,"hilo_eligible":0,
              "priced_members":0,"missing_today_prices":0}
    for ticker in active_symbols:
        p=prices.get(ticker) or {}
        cur=p.get(today,{})
        close=cur.get("close")
        if close is None:
            counters["missing_today_prices"]+=1
            continue
        counters["priced_members"]+=1
        prev=p.get(yesterday,{}).get("close")
        if prev is not None and prev>0:
            counters["ad_eligible"]+=1
            if close>prev:counters["advances"]+=1
            elif close<prev:counters["declines"]+=1
            else:counters["unchanged"]+=1
        for n,tag in ((50,"ma50"),(200,"ma200")):
            recent=[p.get(k,{}).get("close") for k in all_calendar[j-n+1:j+1]]
            if len(recent)==n and all(x is not None and x>0 for x in recent):
                counters[tag+"_eligible"]+=1
                if close>sum(recent)/n:counters[tag+"_above"]+=1
        recent_52=[p.get(k,{}) for k in all_calendar[j-251:j+1]]
        if len(recent_52)==252 and all(
            r.get("high") is not None and r.get("low") is not None
            and r["high"]>=r["low"]>0 for r in recent_52
        ):
            counters["hilo_eligible"]+=1
            if recent_52[-1]["high"]>max(x["high"] for x in recent_52[:-1]):
                counters["new_highs"]+=1
            if recent_52[-1]["low"]<min(x["low"] for x in recent_52[:-1]):
                counters["new_lows"]+=1
    active=len(active_symbols)
    counters["expected_sample_members"]=active
    if counters["priced_members"]+counters["missing_today_prices"]!=active:
        raise AuditError("Membership/prices reconciliation failed")
    if counters["advances"]+counters["declines"]+counters["unchanged"]!=counters["ad_eligible"]:
        raise AuditError("A/D component reconciliation failed")
    counters["date"]=day.isoformat()
    counters["ad_ratio"]=counters["advances"]/counters["declines"] if counters["declines"] else None
    counters["ma50_pct"]=100*counters["ma50_above"]/counters["ma50_eligible"] if counters["ma50_eligible"] else None
    counters["ma200_pct"]=100*counters["ma200_above"]/counters["ma200_eligible"] if counters["ma200_eligible"] else None
    return counters


def summarize(days):
    if len(days)<60:
        raise AuditError("Require full 60 actual daily breadth rows")
    result=[]
    for n in PERIODS:
        arr=days[-n:]
        sums={key:sum(x[key] for x in arr) for key in (
            "expected_sample_members","priced_members","ad_eligible","advances","declines","unchanged",
            "ma50_eligible","ma50_above","ma200_eligible","ma200_above",
            "hilo_eligible","new_highs","new_lows")}
        means={key:round(sums[key]/n,3) for key in (
            "expected_sample_members","priced_members","advances","declines","unchanged",
            "new_highs","new_lows"
        )}
        means["mean_50dma_pct"]=round(statistics.mean(
            [x["ma50_pct"] for x in arr if x["ma50_pct"] is not None]),4) if any(
                x["ma50_pct"] is not None for x in arr) else None
        means["mean_200dma_pct"]=round(statistics.mean(
            [x["ma200_pct"] for x in arr if x["ma200_pct"] is not None]),4) if any(
                x["ma200_pct"] is not None for x in arr) else None
        result.append({
            "sessions":n,
            "asof":arr[-1]["date"],
            "daily_averages":means,
            "window_total_A_over_D":round(sums["advances"]/sums["declines"],5) if sums["declines"] else None,
            "mean_daily_50dma_pct_eligible_days":sum(x["ma50_pct"] is not None for x in arr),
            "mean_daily_200dma_pct_eligible_days":sum(x["ma200_pct"] is not None for x in arr),
            "priced_member_day_coverage":round(sums["priced_members"]/sums["expected_sample_members"],5) if sums["expected_sample_members"] else None,
            "ad_member_day_coverage":round(sums["ad_eligible"]/sums["expected_sample_members"],5) if sums["expected_sample_members"] else None,
            "ma50_member_day_coverage":round(sums["ma50_eligible"]/sums["expected_sample_members"],5) if sums["expected_sample_members"] else None,
            "ma200_member_day_coverage":round(sums["ma200_eligible"]/sums["expected_sample_members"],5) if sums["expected_sample_members"] else None,
            "hilo_member_day_coverage":round(sums["hilo_eligible"]/sums["expected_sample_members"],5) if sums["expected_sample_members"] else None
        })
    return result


def run(sample_size,calendar_path):
    days=load_calendar(calendar_path,None)
    meta,source_sha,rows,floor=verified_source()
    if days[0]<floor:raise AuditError("PIT listing directory too recent")
    index_prices,index_status=yahoo_chart("^IXIC")
    if index_status!="OK":raise AuditError("Could not obtain reference exchange sessions: "+index_status)
    calendar=sorted(d for d in index_prices if d<=days[-1])
    if len(calendar)<REQUIRED_CALENDAR_SESSIONS or calendar[-60:]!=days:
        raise AuditError("Reference Nasdaq index sessions do not align to 60-day S&P exchange calendar")
    candidates=choose_sample(rows,days[0],days[-1],sample_size)
    sampled=[t for t,b in candidates]
    source_status={}
    bars={}
    def one(t):
        history,status=fetch_yahoo_ohlc(t)
        return t,history,status
    with ThreadPoolExecutor(max_workers=2) as pool:
        for ticker,history,status in pool.map(one,sampled):
            bars[ticker]=history
            source_status[ticker]=status
    membership={}
    for day in days:
        active=symbols_for_day(rows,day)
        membership[day]=set(sampled)&{t for t,r in active.items() if classification(r)=="LIKELY_ELIGIBLE_TYPE"}
    daily=[stat_day(d,calendar,bars,membership[d]) for d in days]
    if not any(row["ma200_eligible"] for row in daily):
        raise AuditError("Prototype has no historical MA200 observations; could not validate engine")
    counts=Counter(source_status.values())
    return {
        "market":"NONREPRESENTATIVE_NASDAQ_LISTED_SAMPLE_NOT_COMPOSITE",
        "publish_to_us_market":False,
        "usage":"QA_PIT_BREADTH_ENGINE_ONLY_NOT_MARKET_SENTIMENT",
        "asof":days[-1].isoformat(),
        "first_day":days[0].isoformat(),
        "sample_size":len(sampled),
        "sampling_policy":"Deterministic controls and cohorts of former/current/unresolved Nasdaq listings, not probability sampled",
        "data_source":"Yahoo unofficial chart adjusted close and approximate adjusted intraday high/low",
        "source_status_counts":dict(counts),
        "underlying_calendar_sessions":len(calendar),
        "pit_listing_archive_floor":floor.isoformat(),
        "universe_warning":"PIT Nasdaq-listed common-like type sample only, NOT actual Composite historical component membership",
        "high_low_definition":"252 consecutive exchange sessions of adjusted intraday OHLC; strict new high over prior 251 highs, strict new low under prior 251 lows",
        "ma_definition":"Adjusted closing prices, current price strictly above simple mean of latest 50 or 200 contiguous exchange sessions",
        "coverage_warning":"Insufficient price lookbacks excluded from eligible numerator/denominator, but counted against active sample population coverage. No gap filling.",
        "historical_price_copyright":"No raw daily bars, symbol-level output, or vendor download cache stored in GitHub",
        "windows":summarize(daily),
        "daily":daily,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--size",type=int,default=18)
    p.add_argument("--calendar",type=Path,default=Path("public/sp500_pit_daily.csv"))
    p.add_argument("--out",type=Path,default=Path("research/nasdaq_comp/listed_sample_breadth_lab.json"))
    a=p.parse_args()
    if not 1<=a.size<=MAX_SAMPLE:raise AuditError("Sample size capped at 24")
    report=run(a.size,a.calendar)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":"RESEARCH_ONLY_FINISHED","asof":report["asof"],
        "sample":report["sample_size"],
        "sources":report["source_status_counts"],
        "windows":report["windows"],
    },ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
