#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Audit PIT Nasdaq listing security types left ambiguous by the free classifier.

Research only; cannot conclude Composite eligibility from company names.
Publishes a small deterministic sample, NEVER all Nasdaq source records.
"""
from __future__ import annotations
import argparse
import datetime as dt
import hashlib
import json
from collections import Counter
from pathlib import Path
from nasdaq_comp_candidate import verified_source, classification, load_calendar, AuditError

def run(day, rows):
    active={}
    for ticker, start, end, info in rows:
        if start <= day and (end is None or day < end):
            if ticker in active:
                raise AuditError("Overlapping intervals " + ticker)
            active[ticker] = info
    unresolved=[
        {"ticker":ticker,
         "name":str(info.get("name",""))[:170],
         "market_category":info.get("category"),
         "etf_flag":info.get("etf")}
        for ticker, info in active.items() if classification(info) == "UNRESOLVED_TYPE"
    ]
    excluded=[(ticker,info) for ticker,info in active.items()
              if classification(info)=="EXCLUDED_SECURITY_TYPE"]
    sample=sorted(unresolved,key=lambda x:hashlib.sha256(x["ticker"].encode()).hexdigest())[:45]
    token_flags=("unit","rights","warrant","preferred","depositary","reit",
                 "class","stock","share","note","fund","acquisition",
                 "trust","income","exchange","stapled")
    def flags(data):
        return {term:sum(term in row["name"].lower() for row in data) for term in token_flags}
    return {
        "market":"NASDAQ_LISTING_CANDIDATE_CLASSIFICATION_REVIEW_NOT_COMP",
        "eligible_for_comp_publication":False,
        "asof":day.isoformat(),
        "directory_total":len(active),
        "unresolved_count":len(unresolved),
        "unresolved_market_categories":dict(Counter(x["market_category"] for x in unresolved)),
        "unresolved_name_terms":flags(unresolved),
        "excluded_noncommon_type_count":len(excluded),
        "sample_selection":"45 SHA256-sorted tickers, stable and not a representative sample",
        "sample":sample,
        "limit":"Company descriptions are NOT a substitute for security instrument type or official Composite index status; do not auto-include ambiguous names."
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",type=Path,default=Path("public/sp500_pit_daily.csv"))
    p.add_argument("--out",type=Path,default=Path("research/nasdaq_comp/ambiguous_security_review.json"))
    a=p.parse_args()
    day=load_calendar(a.calendar,None)[-1]
    m,sha,rows,floor=verified_source()
    if day<floor:
        raise AuditError("Requested date precedes archived source")
    result=run(day,rows)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":"RESEARCH_ONLY","date":result["asof"],
                      "unresolved_count":result["unresolved_count"],
                      "sample":result["sample"][:10]},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
