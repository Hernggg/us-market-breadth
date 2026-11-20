# Nasdaq Composite V2.0 research checkpoint (2026-11-20)

Research-only, not approved Nasdaq Composite index breadth.

## A. PIT listing directory
Source: https://github.com/TylerJForstrom/Stock-Data
PIT archive floor: 2026-07-28. Audited 60 market sessions 2026-08-27 through 2026-11-19.
2026-11-19: 5,602 Nasdaq-listed issues, 3,363 provisionally likely common-like, 429 unresolved.
Not actual official Nasdaq Composite membership. Results: research/nasdaq_comp/candidate_audit.json
Source program: nasdaq_comp_candidate.py

## B. Historical price availability
Results: research/nasdaq_comp/price_source_probe.json
2026-11-19: 18 sampled listed symbols had some Yahoo adjusted-close historical data.
Sample is deliberately mixed and NON-REPRESENTATIVE: eight mega-cap liquid controls plus former/current/unresolved names.
For sampled historical directory active-days, adjusted prices available 835/939; full 200DMA/52-week-close lookback available 772/939. Not a full-universe estimate.
Historical membership masks exclude quote dates after a Nasdaq directory exit. Yahoo v8 is unofficial and may rate limit or restrict uses. NO raw quotes published.
Run: https://github.com/Hernggg/us-market-breadth/actions/runs/44698052428

## C. Official Nasdaq Trader listed-issues A/D
Source: https://nasdaqtrader.com/dynamic/dailyfiles/daily2026.csv
Definitions: https://classic.nasdaqtrader.com/Trader.aspx?id=DailyMarketSummaryDefs
Results: research/nasdaq_comp/official_nasdaq_issues_ad.json
Current official CSV last valid date: 2026-11-17 (two exchange sessions behind requested 2026-11-19).
Last 60 source sessions 2026-08-25 through 2026-11-17.
Daily 2026-11-17: advances 1,329; declines 3,679; unchanged 210; A/D=0.36124.
5/10/20/60 session A/D: 0.53841 / 0.73640 / 0.84274 / 0.82404.
The CSV also has Composite and Computer INDEX LEVELS for market-performance comparisons, NOT breadth.
This is NASDAQ LISTED ISSUES A/D, not independently validated strict COMP member breadth.
Run: https://github.com/Hernggg/us-market-breadth/actions/runs/44698886811

## D. Gating requirements
1. Point-in-time actual Nasdaq Composite component membership, not Nasdaq-100 and not today's listing directory.
2. Full ~311 trading-session equity price lookback for 60-session MA/52W breadth including symbol continuity, delistings, IPOs, corporate actions.
3. Count 1/5/10/20/60 day COMP breadth (A/D, 50/200DMA, adjusted-close 52W NH/NL) with explicit denominator and coverage audits.
4. Cross-vendor corroboration of selected outputs and clear differentiation from the Nasdaq Trader listed-issues reference.

Research in branch research/nasdaq-composite-pit / draft PR #1.
Do not merge into production main until validated. S&P production remains unchanged.
