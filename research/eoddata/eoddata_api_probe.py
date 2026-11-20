#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EODData authenticated API access feasibility: INDEX series, COUNTS ONLY.

This does not scrape EODData stock-quote web pages. EODData documents:
  https://api.eoddata.com/Quote/List/{exchangeCode}/{symbolCode}?apiKey=KEY
  https://api.eoddata.com/Quote/Get/{exchangeCode}/{symbolCode}?apiKey=KEY
and API plans at https://www.eoddata.com/products/API.aspx .

The user must generate their own free-account API key and, if willing, place
it in the GH Actions secret EODDATA_API_KEY. NEVER put it in this repo/chat.
Test uses only up to three INDEX symbols, only after an explicit run.
No raw quotes, price bars, API payloads, credentials or URLs containing the
key are printed, saved or uploaded. Access/coverage diagnostics only.

Do not run an unattended schedule or persist data to public GitHub. Test-only.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter

BASE = "https://api.eoddata.com"
ALLOWED = {"NCFI","NCTH","S5FI","S5TH","MAHQ","MALQ","MAHP","MALP","ADVQ","DECQ"}
MAX_BYTES=2_000_000


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        dest=urllib.parse.urlparse(newurl)
        if dest.netloc.lower() != "api.eoddata.com" or dest.scheme != "https":
            raise PermissionError("Unsafe API redirect refused")
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def api_path(symbol, kind="List"):
    if symbol not in ALLOWED or kind not in {"List","Get"}:
        raise ValueError("Unexpected symbol or API operation")
    return f"/Quote/{kind}/INDEX/{symbol}"


def summarize_json(payload):
    """Return structural diagnostics without numbers that reproduce quotes."""
    if not isinstance(payload,(dict,list)):
        return {"json_shape":"UNEXPECTED","observations":0}
    if isinstance(payload,dict):
        keys=sorted(str(k)[:70] for k in payload.keys())
        rows=next((v for k,v in payload.items()
                   if k.lower() in ("data","results","result","quotes","items","prices","history")
                   and isinstance(v,list)),None)
        if rows is None:
            rows=payload.get("data") or payload.get("Data")
            if isinstance(rows,dict):
                rows=next((v for v in rows.values() if isinstance(v,list)),None)
        if rows is None:
            rows=[]
        result={"json_shape":"OBJECT","top_level_fields":keys[:25]}
    else:
        rows=payload
        result={"json_shape":"ARRAY","top_level_fields":[]}
    if not isinstance(rows,list):
        rows=[]
    # Never output actual vendor quote values, only rows and calendar coverage.
    session_dates=[]
    for record in rows[:500]:
        if not isinstance(record,dict):
            continue
        for k,v in record.items():
            if str(k).lower() in ("date","datetime","tradedate","trade_date","timestamp"):
                val=str(v)
                hit=re.search(r"\d{4}-\d{2}-\d{2}",val)
                if hit:
                    try: session_dates.append(dt.date.fromisoformat(hit.group(0)))
                    except ValueError:pass
                break
    result.update({
        "observations":len(rows),
        "distinct_sessions":len(set(session_dates)),
        "earliest_observation_date":min(session_dates).isoformat() if session_dates else None,
        "latest_observation_date":max(session_dates).isoformat() if session_dates else None,
        "has_at_least_20_sessions":len(set(session_dates))>=20,
        "has_at_least_60_sessions":len(set(session_dates))>=60,
    })
    return result


def probe(symbol,key,kind="List",timeout=25):
    if symbol not in ALLOWED:
        raise ValueError("Symbol not in fixed allowlist")
    if not key:
        return {"symbol":symbol,"status":"NO_API_KEY_CONFIGURED","source":"EODData authenticated official REST"}
    url=BASE+api_path(symbol,kind)+"?"+urllib.parse.urlencode({"apiKey":key})
    request=urllib.request.Request(url,headers={
        "User-Agent":"us-market-breadth EODData private license check (research)",
        "Accept":"application/json"
    })
    try:
        with urllib.request.build_opener(SafeRedirect()).open(request,timeout=timeout) as response:
            status=response.status
            data=response.read(MAX_BYTES+1)
        if len(data)>MAX_BYTES:
            return {"symbol":symbol,"status":"RESPONSE_TOO_LARGE_ABORTED","http_status":status}
        try: payload=json.loads(data)
        except (ValueError,UnicodeDecodeError):
            return {"symbol":symbol,"status":"NON_JSON_RESPONSE","http_status":status}
        result=summarize_json(payload)
        result.update({"symbol":symbol,"http_status":status,
                       "status":"ACCESSIBLE_NEEDS_SCHEMA_CHECK" if result["observations"]==0 else "AUTHENTICATED_HISTORY_ROWS_FOUND"})
        return result
    except urllib.error.HTTPError as exc:
        return {"symbol":symbol,"status":{
            400:"API_REQUEST_REJECTED",401:"AUTHENTICATION_REQUIRED_OR_BAD_KEY",
            402:"PLAN_RESTRICTED",403:"PLAN_RESTRICTED",
            404:"ENDPOINT_OR_SYMBOL_NOT_AVAILABLE",429:"RATE_LIMITED"
        }.get(exc.code,"HTTP_ERROR"),"http_status":exc.code}
    except (urllib.error.URLError,TimeoutError,PermissionError) as exc:
        return {"symbol":symbol,"status":"NETWORK_OR_REDIRECT_FAILURE","error_type":type(exc).__name__}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbols",nargs="+",default=["NCFI","NCTH","MAHQ"])
    p.add_argument("--operation",choices=["List","Get"],default="List")
    args=p.parse_args()
    if len(args.symbols)>3 or len(args.symbols)!=len(set(args.symbols)) or any(s not in ALLOWED for s in args.symbols):
        raise SystemExit("Only 1-3 allowed unique INDEX symbols per study, no scraping")
    key=os.environ.get("EODDATA_API_KEY","").strip()
    status=[probe(symbol,key,args.operation) for symbol in args.symbols]
    print(json.dumps({
        "stage":"EODDATA_FREE_API_ENTITLEMENT_TEST_ONLY",
        "authenticated_request_attempted":bool(key),
        "api_key_was_never_output":True,
        "real_index_history_access_confirmed":any(s["status"]=="AUTHENTICATED_HISTORY_ROWS_FOUND" for s in status),
        "license_scope":"personal nonredistributable, not yet authorized for publication",
        "vendor_data_persisted":False,
        "results":status,
    },ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
