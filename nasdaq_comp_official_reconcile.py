#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Research-only COMP official EOD component export reconciliation.

Accesses only publicly accessible, unauthenticated Nasdaq GIW Excel exports,
never bypasses authorization; no raw component lists are persisted or printed.
Writes only aggregate counts and failure/audit diagnostics, never index-member
identities. Requests are bounded to 2/5 known trading sessions per invocation.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from nasdaq_comp_candidate import verified_source, classification, load_calendar, AuditError

HOST="https://indexes.nasdaq.com/Index/ExportWeightings/COMP"
MAX_DOWNLOAD_BYTES=3_000_000
NAMESPACE="{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
USER_AGENT="Mozilla/5.0 (us-market-breadth; noncommercial personal research)"
MAX_DAYS=5


class AuthSafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target=urllib.parse.urlparse(newurl)
        if target.netloc.lower() != "indexes.nasdaq.com" or any(
            x in (target.path+target.query).lower() for x in ("login","signin","sso","auth","register")
        ):
            raise AuditError("AUTHENTICATION_REDIRECT_REFUSED")
        return super().redirect_request(req,fp,code,msg,headers,newurl)


def get_export(day):
    q=urllib.parse.urlencode({
        "tradeDate":day.isoformat()+"T00:00:00.000",
        "timeOfDay":"EOD"
    })
    req=urllib.request.Request(HOST+"?"+q,headers={
        "User-Agent":USER_AGENT,
        "Accept":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    })
    try:
        with urllib.request.build_opener(AuthSafeRedirect()).open(req,timeout=35) as r:
            buf=r.read(MAX_DOWNLOAD_BYTES+1)
            if len(buf)>MAX_DOWNLOAD_BYTES:
                raise AuditError("Nasdaq export unusually large; refusing")
    except urllib.error.HTTPError as ex:
        if ex.code in (401,403):
            raise AuditError("AUTHORIZATION_REQUIRED") from ex
        raise
    if not buf.startswith(b"PK\x03\x04"):
        raise AuditError("Not a publicly accessible Excel file")
    return buf


def get_cell(cell, strings):
    typ=cell.attrib.get("t","")
    v=cell.find(NAMESPACE+"v")
    if typ=="s":
        if v is None:
            return ""
        idx=int(v.text)
        if idx<0 or idx>=len(strings):
            raise AuditError("Invalid shared string index")
        return strings[idx]
    if typ=="inlineStr":
        element=cell.find(NAMESPACE+"is")
        return "".join(n.text or "" for n in element.iter(NAMESPACE+"t")) if element is not None else ""
    return v.text if v is not None and v.text is not None else ""


def parse_xlsx(blob):
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as archive:
            paths=set(archive.namelist())
            if "[Content_Types].xml" not in paths:
                raise AuditError("Not Excel XLSX format")
            if "xl/sharedStrings.xml" in paths:
                ssroot=ET.fromstring(archive.read("xl/sharedStrings.xml"))
                strings=["".join(t.text or "" for t in si.iter(NAMESPACE+"t"))
                         for si in ssroot.findall(NAMESPACE+"si")]
            else:
                strings=[]
            sheet_names=sorted(x for x in paths if re.fullmatch(r"xl/worksheets/sheet\d+\.xml",x))
            if not sheet_names:
                raise AuditError("Missing Excel worksheets")
            root=ET.fromstring(archive.read(sheet_names[0]))
            rows=root.findall(".//"+NAMESPACE+"sheetData/"+NAMESPACE+"row")
            if not 3000 <= len(rows) <= 8000:
                raise AuditError(f"Unexpected number of worksheet rows: {len(rows)}")
            content=[]
            for row in rows:
                d={}
                for cell in row.findall(NAMESPACE+"c"):
                    col="".join(ch for ch in cell.attrib.get("r","") if ch.isalpha())
                    if col:
                        d[col]=get_cell(cell,strings)
                content.append(d)
    except (zipfile.BadZipFile, ET.ParseError, KeyError,ValueError,IndexError) as exc:
        raise AuditError("Invalid Excel structure "+type(exc).__name__) from exc

    header_index=None
    symbol_col=None
    company_col=None
    for idx,row in enumerate(content[:12]):
        n={k:re.sub(r"[^a-z0-9]","",str(v).lower()) for k,v in row.items()}
        symbol=[k for k,v in n.items() if v in {"securitysymbol","symbol","ticker"}]
        name=[k for k,v in n.items() if v in {"companyname","company","issuername"}]
        if symbol and name and symbol[0]!=name[0]:
            header_index=idx
            symbol_col=symbol[0]
            company_col=name[0]
            break
    if header_index is None:
        raise AuditError("Cannot establish ticker and company columns in official Excel header")
    members=[]
    for row in content[header_index+1:]:
        sym=str(row.get(symbol_col,"")).strip().upper()
        nm=str(row.get(company_col,"")).strip()
        if not sym and not nm:
            continue
        if not sym or not re.fullmatch(r"[A-Z0-9.\-]{1,12}",sym):
            raise AuditError("Invalid security symbol or footer in official table")
        if not nm:
            raise AuditError("Member row missing issuer name")
        members.append(sym)
    if len(members)<3000 or len(members)>6000:
        raise AuditError("Official component listing has implausible size")
    if len(members)!=len(set(members)):
        raise AuditError("Official listing has duplicate ticker symbols")
    return set(members),{
        "sheet_rows":len(rows),
        "header_row_index_1based":header_index+1,
        "valid_unique_component_rows":len(members),
        "header_verified":True,
    }


def candidate_sets(rows,day):
    d={}
    for ticker,lo,hi,r in rows:
        if lo<=day and (hi is None or day<hi):
            if ticker in d:
                raise AuditError("Duplicate PIT ticker interval")
            d[ticker]=r
    likely={t for t,v in d.items() if classification(v)=="LIKELY_ELIGIBLE_TYPE"}
    unresolved={t for t,v in d.items() if classification(v)=="UNRESOLVED_TYPE"}
    return likely, unresolved, len(d)


def normalize(symbol):
    return symbol.strip().upper().replace("-", ".")


def reconcile(official, likely, unresolved, total):
    if likely & unresolved:
        raise AuditError("Candidate categories overlap")
    # Do NOT alter constituents by non-verified heuristics. Show both exact
    # and a plausible class-suffix-normalized match as separate diagnostics.
    intersection=official & likely
    exact_missing=official - likely
    extra=likely - official
    norm_official={normalize(t) for t in official}
    norm_likely={normalize(t) for t in likely}
    return {
        "nasdaq_directory_total":total,
        "official_comp_members":len(official),
        "likely_type_candidate_count":len(likely),
        "unresolved_type_count":len(unresolved),
        "exact_match_count":len(intersection),
        "official_not_likely_candidate_count":len(exact_missing),
        "candidate_not_official_count":len(extra),
        "official_in_unresolved_count":len(official & unresolved),
        "normalized_match_count":len(norm_official & norm_likely),
        "normalized_official_unmatched_count":len(norm_official-norm_likely),
        "normalized_candidate_extra_count":len(norm_likely-norm_official),
        "exact_identity_equality": official == likely,
    }


def audit(days):
    meta, sha, history, floor=verified_source()
    if days[0] < floor:
        raise AuditError("Date predates source listing archive")
    result=[]
    previous=None
    for day in days:
        raw=get_export(day)
        official, quality=parse_xlsx(raw)
        likely, unresolved, total=candidate_sets(history,day)
        result.append({
            "date":day.isoformat(),
            "source":"https://indexes.nasdaq.com/Index/Weighting/COMP",
            "official_export_retrieved_without_login":True,
            "export_byte_count":len(raw),
            "export_sha256":hashlib.sha256(raw).hexdigest(),
            **quality,
            **reconcile(official,likely,unresolved,total),
            "official_added_since_prior_checked_day":len(official-previous) if previous is not None else None,
            "official_removed_since_prior_checked_day":len(previous-official) if previous is not None else None,
        })
        previous=official
        time.sleep(0.7)  # avoid rapid repeated access to public web service
    return {
        "status":"RESEARCH_ONLY_UNAUTHENTICATED_OFFICIAL_COMPONENT_COMPARISON",
        "official_file_contains_actual_component_rows":True,
        "no_raw_member_tickers_or_names_stored":True,
        "license_note":"Publicly accessible export does not grant redistribution; use derived counts only until official rights/usage confirmed.",
        "historical_membership_sample_only":True,
        "days":[d.isoformat() for d in days],
        "daily":result,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",type=Path,default=Path("public/sp500_pit_daily.csv"))
    p.add_argument("--sessions",type=int,default=2)
    p.add_argument("--out",type=Path,default=Path("research/nasdaq_comp/official_component_reconciliation.json"))
    a=p.parse_args()
    if not 1<=a.sessions<=MAX_DAYS:
        raise AuditError("Only 1..5 dates allowed per study run; avoid unbounded vendor access")
    days=load_calendar(a.calendar,None)[-a.sessions:]
    report=audit(days)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
