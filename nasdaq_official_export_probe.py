#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check whether Nasdaq GIW COMP historical component Excel export is PUBLIC.

Unauthenticated and bounded requests only. Explicitly refuse authentication
prompts or paywalls; no login, cookies, session replay or access bypass.
No component identities/quotes are persisted or printed; only count/schema
diagnostics. This is research only, not a license for mass ingestion.
"""
from __future__ import annotations
import datetime as dt
import io
import os
import json
import urllib.parse
import urllib.request
import urllib.error
import zipfile
import xml.etree.ElementTree as ET

HOST="https://indexes.nasdaq.com/Index/ExportWeightings/COMP"
MAX_BYTES=3_000_000
UA="Mozilla/5.0 (compatible; us-market-breadth GIW public access feasibility)"
DATES=("2026-11-19","2026-11-18")
NS = {"m":"http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
HEADERS={"User-Agent":UA,"Accept":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/octet-stream,*/*"}
class UnauthorizedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        path=urllib.parse.urlparse(newurl)
        if path.netloc.lower() != "indexes.nasdaq.com" or any(
            word in (path.path+path.query).lower() for word in ("login","signin","sso","auth","register")
        ):
            raise PermissionError("AUTHENTICATION_REDIRECT")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def check_one(date, shape):
    assert dt.date.fromisoformat(date).weekday()<5
    suffix=".xlsx" if shape=="xlsx_suffix" else ""
    qs=urllib.parse.urlencode({"tradeDate":date+"T00:00:00.000","timeOfDay":"EOD"+suffix})
    url=HOST+"?"+qs
    req=urllib.request.Request(url,headers=HEADERS)
    out={"date":date,"query_shape":shape,"access":"UNKNOWN"}
    try:
        with urllib.request.build_opener(UnauthorizedRedirect()).open(req,timeout=24) as r:
            result=r.read(MAX_BYTES+1)
            ct=(r.headers.get("Content-Type") or "").lower()
            out["http_status"]=r.status
            out["content_type_category"]="XLSX" if "spreadsheet" in ct else "OTHER"
            out["received_bytes"]=len(result)
            if len(result)>MAX_BYTES:
                out["access"]="TOO_LARGE_ABORT"
                return out
    except urllib.error.HTTPError as e:
        out["http_status"]=e.code
        out["access"]="RESTRICTED" if e.code in (401,403,404) else "HTTP_ERROR"
        return out
    except (PermissionError,TimeoutError,urllib.error.URLError) as e:
        out["access"]="AUTH_REQUIRED" if isinstance(e,PermissionError) else "NETWORK_FAILURE"
        out["error_type"]=type(e).__name__
        return out
    if not result.startswith(b"PK\x03\x04"):
        out["access"]="NO_XLSX_PUBLIC_FILE"
        return out
    try:
        with zipfile.ZipFile(io.BytesIO(result)) as z:
            names=z.namelist()
            if "[Content_Types].xml" not in names:
                out["access"]="ZIP_NOT_XLSX"
                return out
            sheets=[n for n in names if n.startswith("xl/worksheets/sheet") and n.endswith(".xml")]
            if not sheets:
                out["access"]="XLSX_WITHOUT_WORKSHEETS"
                return out
            root=ET.fromstring(z.read(sheets[0]))
            rows=root.findall(".//m:sheetData/m:row",NS)
            out["worksheet_rows"]=len(rows)
            out["estimated_nonheader_rows"]=max(0,len(rows)-2)
            # Source's public anonymous response may be an EMPTY template.
            out["access"]="POSSIBLE_PUBLIC_COMPONENT_EXPORT" if len(rows)>3000 else "EMPTY_OR_RESTRICTED_TEMPLATE"
    except (zipfile.BadZipFile,ET.ParseError,KeyError,RuntimeError,ValueError) as exc:
        out["access"]="UNPARSEABLE_XLSX"
        out["error_type"]=type(exc).__name__
    return out

def main():
    # GIW is copyrighted/licensed index data. Reuse of historical component
    # files for an automated analysis pipeline needs express vendor permission.
    # Gate this research prototype until that entitlement is established.
    if os.environ.get("NASDAQ_GIW_PERMISSION_CONFIRMED") != "yes":
        print("BLOCKED: Nasdaq GIW index constituent usage rights are not confirmed. Do not automate exports.")
        return 3
    outcomes=[check_one(DATES[0],"normal"),check_one(DATES[0],"xlsx_suffix"),
              check_one(DATES[1],"normal")]
    print(json.dumps({
        "status":"RESEARCH_ONLY_PUBLIC_ACCESS_CHECK",
        "source":"https://indexes.nasdaq.com/Index/Weighting/COMP",
        "no_authentication_attempted":True,
        "no_component_data_persisted":True,
        "do_not_assume_rights_to_republish":True,
        "outcomes":outcomes
    },ensure_ascii=False))
if __name__=="__main__":main()
