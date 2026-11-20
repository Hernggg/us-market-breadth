#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Offline adapter for USER-PROVIDED, RIGHTS-CLEARED full-universe Parquet data.

Does NOT fetch Nasdaq GIW, Yahoo, MarketParquet, or any web source.
Inputs must be private files, normalized to a persistent SECURITY identifier
(never reused ticker alone) and 311 ordered exchange sessions:

 calendar.parquet  trade_date DATE [one row for each session, oldest first]
 members.parquet   security_id VARCHAR, trade_date DATE
                   [all 60 most-recent sessions, PIT *actual* membership]
 prices.parquet    security_id VARCHAR, trade_date DATE,
                   adj_close DOUBLE, adj_high DOUBLE, adj_low DOUBLE
                   [split-adjusted OHLC for all applicable sessions,
                   including historical delisted securities]

All inputs must have explicit usage rights for automated calculation,
permitted derived aggregates, and requisite authorized Nasdaq index data.
Permission flags in CLI are user attestations, NOT license verification.
Even after calculation, outputs are flagged research-only until separate
independent official membership and vendor completeness validation.

No raw vendor prices or constituent rosters are emitted to results.
No network access is used. No auto-commit to any public branch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from nasdaq_bulk_breadth_engine import (
    InvalidMarketData, calculate_daily, aggregate
)

def require_rights(license_membership: bool, license_prices: bool):
    if not (license_membership and license_prices):
        raise InvalidMarketData(
            "STOP: explicit membership AND price usage/derived output permissions required"
        )


def import_authorized_parquet(con, calendar_path, members_path, prices_path,
                              membership_rights=False, price_rights=False):
    """Import only local files. Missing/extra rows and duplicated IDs fail closed."""
    require_rights(membership_rights,price_rights)
    paths=[Path(p).resolve() for p in (calendar_path,members_path,prices_path)]
    for path in paths:
        if path.suffix.lower()!=".parquet" or not path.is_file():
            raise InvalidMarketData("Must supply existing local .parquet files")
        if path.stat().st_size>2_000_000_000 or path.stat().st_size==0:
            raise InvalidMarketData("Invalid/oversized input file")
    # DuckDB parameter binding is used for file paths to avoid SQL injection.
    con.execute("""CREATE TABLE raw_calendar AS
        SELECT CAST(trade_date AS DATE) trade_date FROM read_parquet(?)""",[str(paths[0])])
    con.execute("""CREATE TABLE calendar AS
        SELECT CAST(row_number() OVER (ORDER BY trade_date)-1 AS INTEGER) session_id,
               trade_date FROM raw_calendar""")
    con.execute("""CREATE TABLE raw_members AS
        SELECT CAST(security_id AS VARCHAR) security_id,
               CAST(trade_date AS DATE) trade_date
        FROM read_parquet(?)""",[str(paths[1])])
    con.execute("""CREATE TABLE raw_prices AS
        SELECT CAST(security_id AS VARCHAR) security_id,
               CAST(trade_date AS DATE) trade_date,
               CAST(adj_close AS DOUBLE) adj_close,
               CAST(adj_high AS DOUBLE) adj_high,
               CAST(adj_low AS DOUBLE) adj_low
        FROM read_parquet(?)""",[str(paths[2])])
    join_counts=con.execute("""SELECT
          (SELECT COUNT(*) FROM raw_members),
          (SELECT COUNT(*) FROM raw_members m INNER JOIN calendar c USING (trade_date)),
          (SELECT COUNT(*) FROM raw_prices),
          (SELECT COUNT(*) FROM raw_prices p INNER JOIN calendar c USING (trade_date))
    """).fetchone()
    if join_counts[0]!=join_counts[1] or join_counts[2]!=join_counts[3]:
        raise InvalidMarketData("Source contains membership or price dates outside the 311-day calendar")
    con.execute("""CREATE TABLE members AS
        SELECT r.security_id, c.session_id
        FROM raw_members r JOIN calendar c USING(trade_date)""")
    con.execute("""CREATE TABLE prices AS
        SELECT r.security_id,c.session_id,r.adj_close,r.adj_high,r.adj_low
        FROM raw_prices r JOIN calendar c USING(trade_date)""")
    return {"license_flags_are_user_attestation_only":True,
            "input_security_keys":"permanent ID required; ticker recycling unresolved without identifier lineage",
            "calendar_days":con.execute("SELECT COUNT(*) FROM calendar").fetchone()[0],
            "private_member_rows":join_counts[0],
            "private_price_rows":join_counts[2]}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--calendar",type=Path,required=True)
    p.add_argument("--members",type=Path,required=True)
    p.add_argument("--prices",type=Path,required=True)
    p.add_argument("--membership-rights-confirmed",action="store_true")
    p.add_argument("--price-rights-confirmed",action="store_true")
    p.add_argument("--membership-provider",required=True)
    p.add_argument("--price-provider",required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    require_rights(args.membership_rights_confirmed,args.price_rights_confirmed)
    import duckdb
    con=duckdb.connect(":memory:")
    try:
        coverage=import_authorized_parquet(con,args.calendar,args.members,args.prices,
             membership_rights=True,price_rights=True)
        daily,windows=aggregate(calculate_daily(con))
    finally:
        con.close()
    report={
        "status":"PRIVATE_RIGHTS_ATTESTED_INPUT_QA_RESEARCH_ONLY",
        "publish_to_us_market":False,
        "membership_source_user_declared":args.membership_provider,
        "price_source_user_declared":args.price_provider,
        "rights_are_user_attested_not_independently_verified":True,
        "index_membership_identity_and_vendor_license_not_independently_verified":True,
        "asof":daily[-1]["date"],
        "source_row_counts":coverage,
        "daily":daily,
        "windows":windows,
        "data_limitations":"Must separately audit genuine Nasdaq Composite member IDs, full delisting/split continuity, source entitlement and sample sufficiency before publication",
    }
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"sessions":len(daily),
                      "last_date":report["asof"],
                      "one_day_coverage":windows[0]["price_memberday_coverage"],
                      "publication_allowed":False}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
