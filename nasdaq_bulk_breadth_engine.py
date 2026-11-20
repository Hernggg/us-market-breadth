#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nasdaq breadth batch calculation core and 3,400-security SYNTHETIC scale test.

This is a calculation engine, not a provider, a Nasdaq Composite membership
feed, or a publishable market report. Neither automated official GIW extraction
nor undocumented stock-price scraping is used here.

To connect LICENSED real historical data later, create these DuckDB tables:
  calendar(session_id INTEGER, trade_date DATE) -- 311 successive *market* days
  members(security_id VARCHAR, session_id INTEGER) -- correct PIT member-days
  prices(security_id VARCHAR, session_id INTEGER,
         adj_close DOUBLE, adj_high DOUBLE, adj_low DOUBLE)

security_id MUST uniquely and permanently identify the same security across
ticker changes/recycling. All 311 calendar sessions are DENSIFIED BEFORE
moving-window calculations. No missing candles are forward-filled.
Source-data and license attestation are mandatory before production use.
"""
from __future__ import annotations
import argparse
import datetime as dt
import json
import math
import statistics
from pathlib import Path

SESSIONS = 311
WINDOWS = (1,5,10,20,60)
REQUIRED_LAST = 60


class InvalidMarketData(ValueError):
    pass


def create_synthetic_fixture(con, n=3400):
    """Create about 1,057,400 synthetic price bars, never real quotes."""
    if not 2 <= n <= 6000:
        raise InvalidMarketData("Synthetic instrument count must be 2..6000")
    con.execute("CREATE TABLE calendar AS SELECT CAST(s AS INTEGER) session_id, "
                "CAST(DATE '2025-01-01' + CAST(s AS INTEGER) AS DATE) trade_date "
                "FROM range(311) z(s)")
    con.execute(f"""CREATE TABLE instruments AS
        SELECT 'S' || LPAD(CAST(t AS VARCHAR),6,'0') security_id, CAST(t AS INTEGER) t
        FROM range({int(n)}) a(t)""")
    con.execute("""CREATE TABLE prices AS
        SELECT i.security_id, c.session_id,
          CAST(50 + i.t*0.002 + CASE WHEN i.t%3=0 THEN c.session_id*0.04
                          ELSE -c.session_id*0.01 END AS DOUBLE) adj_close,
          CAST(50.5 + i.t*0.002 + CASE WHEN i.t%3=0 THEN c.session_id*0.04
                          ELSE -c.session_id*0.01 END AS DOUBLE) adj_high,
          CAST(49.5 + i.t*0.002 + CASE WHEN i.t%3=0 THEN c.session_id*0.04
                          ELSE -c.session_id*0.01 END AS DOUBLE) adj_low
        FROM instruments i CROSS JOIN calendar c
        WHERE NOT (i.t%103=0 AND c.session_id=300)
          AND NOT (i.t%131=0 AND c.session_id<280)""")
    con.execute("""CREATE TABLE members AS
        SELECT i.security_id, c.session_id
        FROM instruments i CROSS JOIN calendar c
        WHERE c.session_id >= 251
          AND NOT (i.t%127=0 AND c.session_id>287)
          AND NOT (i.t%131=0 AND c.session_id<282)""")


def verify_input(con):
    required={
        "calendar":{"session_id","trade_date"},
        "members":{"security_id","session_id"},
        "prices":{"security_id","session_id","adj_close","adj_high","adj_low"}
    }
    for table, expected in required.items():
        cols={r[1] for r in con.execute(f"PRAGMA table_info('{table}')").fetchall()}
        if not expected.issubset(cols):
            raise InvalidMarketData(f"Invalid {table} columns: missing {sorted(expected-cols)}")
    ids=con.execute("""SELECT COUNT(*), COUNT(DISTINCT session_id), MIN(session_id),
                       MAX(session_id), COUNT(DISTINCT trade_date)
                       FROM calendar""").fetchone()
    if ids != (SESSIONS,SESSIONS,0,SESSIONS-1,SESSIONS):
        raise InvalidMarketData(f"Calendar needs 311 unique exchange sessions indexed 0..310: {ids}")
    discontinuities=con.execute("""SELECT COUNT(*) FROM (
        SELECT session_id, LAG(session_id) OVER (ORDER BY session_id) previous,
               trade_date, LAG(trade_date) OVER (ORDER BY session_id) previous_day
        FROM calendar)
        WHERE (previous IS NOT NULL AND session_id-previous!=1)
           OR (previous_day IS NOT NULL AND trade_date<=previous_day)""").fetchone()[0]
    if discontinuities:
        raise InvalidMarketData("Calendar indexes or trading dates are not strictly sequential")
    bad_members=con.execute("""SELECT COUNT(*) FROM (
        SELECT security_id,session_id,COUNT(*) n FROM members
        GROUP BY 1,2 HAVING COUNT(*)>1)""").fetchone()[0]
    if bad_members:
        raise InvalidMarketData("Duplicated member security/day records")
    bad_prices=con.execute("""SELECT COUNT(*) FROM (
        SELECT security_id,session_id,COUNT(*) n FROM prices
        GROUP BY 1,2 HAVING COUNT(*)>1)""").fetchone()[0]
    if bad_prices:
        raise InvalidMarketData("Duplicated price security/day records")
    outside=con.execute("""SELECT
      (SELECT COUNT(*) FROM members m LEFT JOIN calendar c USING(session_id)
       WHERE c.session_id IS NULL OR m.security_id IS NULL OR m.security_id=''),
      (SELECT COUNT(*) FROM prices p LEFT JOIN calendar c USING(session_id)
       WHERE c.session_id IS NULL OR p.security_id IS NULL OR p.security_id='')""").fetchone()
    if outside != (0,0):
        raise InvalidMarketData(f"Unknown sessions or blank security IDs: {outside}")
    malformed=con.execute("""SELECT COUNT(*) FROM prices WHERE
       NOT (isfinite(adj_close) AND isfinite(adj_high) AND isfinite(adj_low))
       OR adj_close<=0 OR adj_low<=0 OR adj_high<adj_low
       OR adj_close>adj_high OR adj_close<adj_low""").fetchone()[0]
    if malformed:
        raise InvalidMarketData("Prices include missing, negative, nonfinite, or impossible adjusted OHLC")
    observed=con.execute("""SELECT COUNT(DISTINCT session_id),MIN(session_id),MAX(session_id)
                           FROM members""").fetchone()
    if observed != (REQUIRED_LAST,251,310):
        raise InvalidMarketData("Need exactly 60 member-universe dates 251..310")
    empty_days=con.execute("""SELECT COUNT(*) FROM calendar c
        WHERE c.session_id>=251 AND NOT EXISTS
          (SELECT 1 FROM members m WHERE m.session_id=c.session_id)""").fetchone()[0]
    if empty_days:
        raise InvalidMarketData("One or more of the 60 days have empty index membership")


def calculate_daily(con):
    """Compute full-sample breadth without storing per-security output."""
    verify_input(con)
    # DENSE GRID is required: ROWS window over observed price rows alone is
    # wrong whenever a security has a missing trading day.
    return con.execute("""
        WITH universe AS (SELECT DISTINCT security_id FROM members),
        dense AS (
          SELECT u.security_id, c.session_id, c.trade_date,
                 p.adj_close,p.adj_high,p.adj_low
          FROM universe u CROSS JOIN calendar c
          LEFT JOIN prices p ON p.security_id=u.security_id
                            AND p.session_id=c.session_id
        ), t AS (
          SELECT *,
            LAG(adj_close) OVER (PARTITION BY security_id ORDER BY session_id) prev_close,
            COUNT(adj_close) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) cnt50,
            AVG(adj_close) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) avg50,
            COUNT(adj_close) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) cnt200,
            AVG(adj_close) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 199 PRECEDING AND CURRENT ROW) avg200,
            COUNT(adj_high) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) cnt252high,
            COUNT(adj_low) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 251 PRECEDING AND CURRENT ROW) cnt252low,
            MAX(adj_high) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 251 PRECEDING AND 1 PRECEDING) prior251high,
            MIN(adj_low) OVER
              (PARTITION BY security_id ORDER BY session_id ROWS BETWEEN 251 PRECEDING AND 1 PRECEDING) prior251low
          FROM dense
        ), member_days AS (
          SELECT t.* FROM t INNER JOIN members m
          ON t.security_id=m.security_id AND t.session_id=m.session_id
        )
        SELECT CAST(session_id AS INTEGER) session_id, trade_date,
          COUNT(*) expected_members,
          COUNT(adj_close) priced_members,
          COUNT(*) FILTER (WHERE adj_close IS NOT NULL AND prev_close IS NOT NULL) ad_eligible,
          COUNT(*) FILTER (WHERE adj_close>prev_close) advances,
          COUNT(*) FILTER (WHERE adj_close<prev_close) declines,
          COUNT(*) FILTER (WHERE adj_close=prev_close AND adj_close IS NOT NULL) unchanged,
          COUNT(*) FILTER (WHERE cnt50=50) ma50_eligible,
          COUNT(*) FILTER (WHERE cnt50=50 AND adj_close>avg50) ma50_above,
          COUNT(*) FILTER (WHERE cnt200=200) ma200_eligible,
          COUNT(*) FILTER (WHERE cnt200=200 AND adj_close>avg200) ma200_above,
          COUNT(*) FILTER (WHERE cnt252high=252 AND cnt252low=252) hilo_eligible,
          COUNT(*) FILTER (WHERE cnt252high=252 AND cnt252low=252
                                 AND adj_high>prior251high) new_highs,
          COUNT(*) FILTER (WHERE cnt252high=252 AND cnt252low=252
                                 AND adj_low<prior251low) new_lows
        FROM member_days GROUP BY 1,2 ORDER BY 1
    """).fetchall()


def aggregate(rows):
    keys=("session_id","date","expected_members","priced_members","ad_eligible",
          "advances","declines","unchanged","ma50_eligible","ma50_above",
          "ma200_eligible","ma200_above","hilo_eligible","new_highs","new_lows")
    days=[dict(zip(keys,r,strict=True)) for r in rows]
    if len(days)!=60 or [x["session_id"] for x in days]!=list(range(251,311)):
        raise InvalidMarketData("Daily aggregation must contain exactly 60 trading sessions")
    for row in days:
        if row["advances"]+row["declines"]+row["unchanged"]!=row["ad_eligible"]:
            raise InvalidMarketData("A/D does not reconcile")
        if row["priced_members"]>row["expected_members"]:
            raise InvalidMarketData("More priced members than universe members")
        row["date"]=str(row["date"])
        for k,numerator,denom in (("ma50_pct","ma50_above","ma50_eligible"),
                                  ("ma200_pct","ma200_above","ma200_eligible")):
            row[k]=100*row[numerator]/row[denom] if row[denom] else None
    windows=[]
    for n in WINDOWS:
        part=days[-n:]
        totals={k:sum(r[k] for r in part) for k in keys[2:]}
        windows.append({
            "sessions":n,"asof":part[-1]["date"],
            "avg_advances":round(totals["advances"]/n,3),
            "avg_declines":round(totals["declines"]/n,3),
            "avg_unchanged":round(totals["unchanged"]/n,3),
            "ad_ratio":round(totals["advances"]/totals["declines"],5)
              if totals["declines"] else None,
            "mean_daily_ma50_above_pct":round(statistics.mean(
                r["ma50_pct"] for r in part if r["ma50_pct"] is not None),4)
                if any(r["ma50_pct"] is not None for r in part) else None,
            "mean_daily_ma200_above_pct":round(statistics.mean(
                r["ma200_pct"] for r in part if r["ma200_pct"] is not None),4)
                if any(r["ma200_pct"] is not None for r in part) else None,
            "avg_new_highs":round(totals["new_highs"]/n,3),
            "avg_new_lows":round(totals["new_lows"]/n,3),
            "avg_member_count":round(totals["expected_members"]/n,3),
            "price_memberday_coverage":round(totals["priced_members"]/totals["expected_members"],5),
            "ad_memberday_coverage":round(totals["ad_eligible"]/totals["expected_members"],5),
            "ma50_memberday_coverage":round(totals["ma50_eligible"]/totals["expected_members"],5),
            "ma200_memberday_coverage":round(totals["ma200_eligible"]/totals["expected_members"],5),
            "hilo_memberday_coverage":round(totals["hilo_eligible"]/totals["expected_members"],5),
        })
    return days, windows


def simulate(n):
    import duckdb
    con=duckdb.connect(database=":memory:")
    con.execute("SET threads=2")
    create_synthetic_fixture(con,n)
    source_counts=con.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    member_counts=con.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    daily,windows=aggregate(calculate_daily(con))
    con.close()
    return {
        "status":"SYNTHETIC_SCALE_QA_ONLY_NOT_MARKET_DATA",
        "publish_to_us_market":False,
        "synthetic_311_session_calendar":True,
        "synthetic_dates_are_not_actual_exchange_trading_days":True,
        "synthetic_security_count":n,
        "synthetic_OHLC_rows":source_counts,
        "synthetic_PIT_member_days":member_counts,
        "synthetic_daily_breadth_rows":len(daily),
        "tested_calculation_rules":[
            "Dense 311-session calendar before ROWS moving windows",
            "PIT member-only daily numerator and denominator",
            "Prior close for A/D, with missing sessions never forward-filled",
            "50 and 200 consecutive valid close observations for MA",
            "252 consecutive adjusted high/low observations for new highs and lows",
            "Daily average of above-MA proportions, rather than pooled numerator",
            "Five 1/5/10/20/60-day windows with explicit coverage",
        ],
        "last_day":daily[-1],
        "windows":windows,
    }


def main():
    p=argparse.ArgumentParser(description="Simulation only: no live Nasdaq data")
    p.add_argument("--synthetic-securities",type=int,default=3400)
    p.add_argument("--out",type=Path,default=Path("research/nasdaq_comp/bulk_engine_synthetic_scale.json"))
    args=p.parse_args()
    report=simulate(args.synthetic_securities)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,default=str,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"security_count":report["synthetic_security_count"],
                      "price_rows":report["synthetic_OHLC_rows"],
                      "membership_rows":report["synthetic_PIT_member_days"],
                      "windows":len(report["windows"]),
                      "last_day_coverage":report["windows"][0]["hilo_memberday_coverage"]}))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
