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

## F. Bulk price coverage and second-source gap feasibility (2026-11-20)

**Official actual index component COUNT — not identity**
- Nasdaq Global Index Watch COMP overview explicitly reports 3,393 components **as of 2026-11-19**: https://indexes.nasdaqomx.com/Index/Overview/COMP
- Our 2026-11-19 PIT listing security-type screen still reports 3,397 likely common-like and 6 unresolved. Even identical counts are insufficient; list identities and one-day NOCP seasoning are still unverified. Full GIW Weighting list is behind login.

**Bulk daily price vendor one-day test (license-aware)**
- Candidate vendor MarketParquet publishes one full U.S. stock day as no-account PARQUET sample, with split-adjusted OHLCV. Vendor says free trial samples have NO redistribution license; neither these files nor their raw stock quotes were persisted, committed, or shared.
- On 2026-11-19, ephemeral sample had 6,460 symbols; PIT-listed common-like candidate screen had 3,397 symbols, of which 3,188 had a bulk sample price and 209 did not; one-day candidate match **93.8475%**. This is NOT an index-membership coverage rate or a 311-session price history coverage rate.
- Source page: https://marketparquet.com/guides/free-historical-stock-data
- Research code: nasdaq_bulk_price_probe.py; cloud run https://github.com/Hernggg/us-market-breadth/actions/runs/44706316421
- Vendor reports free trial access to ~365 calendar days, which is only about ~250 sessions; **not enough for the 311 sessions needed to calculate 60 trailing session close-based 52-week highs/lows with full history**. Full history is a paid/license question, not solved.

**Second source gap sample (Yahoo adjusted close)**
- Deterministic test selected **24 of 209** bulk-missing candidate tickers, plus **6 bulk-present controls**. This is a nonrepresentative probe, NOT validated full-universe coverage.
- All 24 bulk-missing names had a Yahoo adjusted closing price on **2026-11-19**; 13/24 had complete current-day 252-consecutive-session lookback needed for adjusted-close 52-week classification; 783 of 1,440 possible 60-day sample member-days had a full 200DMA lookback in Yahoo. New listings, missing sessions and symbol identity continuity need separate audits.
- The 6 controls also had Yahoo latest-session quotes; 5/6 had complete 252-session lookback; 341 of 360 possible sample member-days had the 200DMA lookback.
- No Yahoo/vendor prices or per-stock gap lists were committed. Research code: nasdaq_price_gap_probe.py; cloud run https://github.com/Hernggg/us-market-breadth/actions/runs/44706728331.

**Still blocking before official COMP breadth**
1. Actual member-by-member Nasdaq Composite historical constituent identity validation and listing effective day/NOCP seasoning.
2. Licensed, sustainable bulk historical price source with stock splits, ticker changes, delistings, minimum 311-day session backfill, and explicit handling for IPOs and thin names. Public free vendor samples must not be republished.
3. Classify missing prices separately from insufficient pre-IPO lookback; never forward-fill missing candles or assert 95%+ coverage without true cohort denominator.
4. Compute actual COMP-member 1/5/10/20/60 day A/D, MA50/200 and adjusted-close 52W NH/NL and cross-check against exchange-level A/D statistics (which remain a DIFFERENT universe).

**Branch safeguard:** all source experiments are under draft research PR #1. The original S&P 500 main branch and public/latest.json are untouched.

## G. Nasdaq GIW official COMP identity research and legal gate (2026-11-20)

### Technical validation (not a production authorization)
- Unauthenticated Nasdaq Global Index Watch COMP EOD Excel exports were technically accessible for the Nov 19 and Nov 18 2026 trading dates, producing spreadsheets with **3,393** and **3,394** unique member records respectively. On Nov 19 the count agrees with the public GIW Overview component count.
- A five-session prototype and then a single **60-session (2026-08-27..2026-11-19)** identity-level comparison technically executed successfully. These findings established that a no-survivorship-bias official historical roster *exists* and that some of our listing-type candidates differ from official membership.
- Raw member names, rosters and price quotes were NEVER committed to GitHub.
- **IMPORTANT POST-TEST LEGAL REVIEW**: Nasdaq's Global Index Watch/index data policy and Nasdaq legal site restrict automated extraction, non-display uses, creation/redistribution of derived index data, and external distribution of historical component data absent appropriate contractual permission. A publicly downloadable file does not establish the needed right to build a recurring automated index-data product.
- Primary sources: https://www.nasdaq.com/legal and https://www.nasdaq.com/products/global-indexes/policies and https://www.nasdaq.com/products/global-indexes/data/giw
- Consequently, the GIW component-fetching GitHub Actions workflows have been **deleted from this research branch**. The source-research prototype scripts are now **blocked by default** unless their executor has confirmed vendor entitlement and explicitly sets NASDAQ_GIW_PERMISSION_CONFIRMED=yes.
- Draft-branch counts-only experimental GIW component reconciliation JSON files were removed from the *current tree* to avoid ongoing public distribution of unlicensed Nasdaq-derived results. **Earlier commits may still preserve those files in public Git history**; deleting the files from HEAD is not equivalent to purging Git history. We must not claim full revocation of historical exposure.
- **Do NOT merge any unlicensed GIW automation into production** or treat this experiment as authorization to auto-export 60 official daily component sets.

### Practical next licensed/unlicensed routes
1. **Free/clearly permitted route**: continue NasdaqTrader listed-issues aggregate A/D (its scope differs from COMP); maintain the PIT Nasdaq listing directory as an explicit research *approximation* with source quality disclosure and available trial data allowed for private analytics; never call it true Composite membership.
2. **Accurate COMP route**: obtain written data usage permission/licensed historical member API from Nasdaq Global Index Watch (or use Norgate's appropriately licensed historical COMP membership), and verify output/derived-data rights before re-enabling daily automatic analysis.
3. **Prices**: MarketParquet's stated standard license allows personal research and derivative non-reconstructable aggregate statistics, but its complete archive may require payment. Licensed 311-session daily prices and corporate-action continuity remain to be audited; do not publish raw bars.

## H. Real-price sampled 60-session breadth engine proven (2026-11-20)

**Executed deliverable**: `nasdaq_listing_breadth_lab.py` implements **A/D, MA50/200, and 52-week adjusted INTRADAY high/low events**, and five 1/5/10/20/60 trading-session windows, with actual Yahoo daily OHLC and Nasdaq PIT listing directory participation. No sample raw prices or ticker-level output are saved in the repository.

- Measured 60 exchange sessions 2026-08-27 to 2026-11-19; reference index calendar had 501 daily sessions, enough for previous 251-session OHLC lookback.
- Enhanced deterministic sample of 24 Nasdaq listed-security type candidates: 8 liquid controls, 12 other current listed issues, 2 new entrants, 2 formerly listed issues. **Purposeful QA cohort, NOT a probability sample and NOT official Nasdaq Composite index membership.**
- Yahoo adjusted OHLC source returned some history for 24/24 selected tickers.
- On Nov 19 sample, **22 historical PIT-listed sample securities were active; all 22 had adjusted closes; 22 were A/D eligible; 21 MA50 eligible; 20 MA200 and 252-session 52-week extreme eligible**. Missing historical windows are excluded from eligible indicator denominators, and recorded against the active-sample coverage denominator.
- The Nov 19 sampled A/D was 3 up, 18 down and 1 unchanged, MA50 above 4/21, MA200 above 10/20, 0 adjusted OHLC 52-week highs and 1 low. **NEVER INTERPRET THESE AS FULL NASDAQ MARKET SENTIMENT**; sample intentionally nonrepresentative.
- For all 60 trailing days, member-day priced coverage 96.031%; 50DMA-eligible coverage 92.374%; 200DMA and 52W extreme coverage 88.638%. These figures apply to the 24-symbol QA sample ONLY.
- 60-session averages are computed **from daily percentages**, NOT pooled cross-date numerator/denominator; A/D uses window total advancers ÷ total decliners; close price comparisons require prior session; 52-week highs/lows use current adjusted intraday high/low vs prior 251 high/low sessions, strict > or <, with no candle forward-fill.
- QA output: `research/nasdaq_comp/listed_sample_breadth_lab.json`.
- GitHub real-data success: https://github.com/Hernggg/us-market-breadth/actions/runs/44710883488
- Source is Yahoo undocumented web endpoint; may rate-limit and is not a suitably licensed full-universe feed. This code has **publish_to_us_market=false** and remains on draft research branch only.

**Remaining real blockers**: legally authorized daily Composite actual component list and complete properly licensed ~311-day historical price inputs for ~3,400 names with delisting/ticker continuity. The engineering formula is now proven; the production data entitlements and completeness are not.
