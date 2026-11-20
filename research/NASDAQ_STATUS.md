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

## E. New verified follow-on milestones (2026-11-20)

**Official Nasdaq Trader daily archive**
- Program nasdaq_official_history.py; research CSV official_nasdaq_issues_daily_history.csv stores **220 official 2026 Nasdaq-listed issue A/D sessions** (2026-01-02 to 2026-11-17), and official_nasdaq_issues_history_summary.json stores all 1/5/10/20/60 session aggregates and freshness flags.
- Nasdaq Trader public page advertises only the CURRENT year's annual CSV (as of November 2026), so 2024-2025 archive backfill was NOT available by the guessed URLs. The new code retains its local committed archive across year rollover, provided GitHub Actions continues running after production approval. An earlier failed attempt is recorded; the corrected actual 2026 run succeeded: https://github.com/Hernggg/us-market-breadth/actions/runs/44700558505

**Official sector benchmark context**
- Program nasdaq_sector_rotation.py, research/official_sector_relative_strength.json; 11 index-level series and 1/5/10/20/60-session index close-to-close RETURNS, not sector stock breadth.
- For the 20-session window ending Nov 17 2026: Nasdaq Computer -11.992%, Nasdaq Composite -7.9336%, Nasdaq Industrial +0.4443%.
- Verified: https://github.com/Hernggg/us-market-breadth/actions/runs/44700849920

**Improved point-in-time Nasdaq listing type classification**
- Official methodology basis: https://indexes.nasdaqomx.com/docs/Methodology_COMP.pdf (2025). Excluded SPAC units, rights, debt notes, preferred, ETFs; considered eligible diverse common-share classes, ADS/ADRs, beneficial-interest securities.
- 2026-11-19 raw listed directory: 5,602; 3,397 **candidate common-like types**, 6 unresolved types, 910 excluded non-common types, 1,289 ETFs. This is still NOT official COMP membership: actual NOCP seasoning, exceptions, delisted securities and vendor/source errors remain unverified.
- Previously 429 ambiguous issue descriptions now only 6 (2026-11-19); multiple legal share classes were checked against SEC filings. Six cases and source URLs recorded in research/nasdaq_comp/manual_security_type_evidence_20261119.json. Three generic depositary-share cases were identified as preferred by SEC; two as common shares; one BDC still requires index exclusion-policy confirmation. These external observations are **not applied as index membership overrides** in the PIT algorithm.
- Separate TradingView NASDAQ:IXIC public screen reported 3,393 index component instruments when accessed Nov 20, but that is NOT an identity-level nor date-aligned constituent audit against 3,397 candidates (difference 4). Similar totals are insufficient proof of accuracy.
- Verified revised PIT classification: https://github.com/Hernggg/us-market-breadth/actions/runs/44701714367

**Safety**
- No changes to main branch S&P production update or public/latest.json.
- All Nasdaq results remain on draft research PR #1, not automatically merged into @us-market V2.0 official Nasdaq Composite breadth.
