# Nasdaq V2.0 — full-universe calculation handoff (2026-11-20)

**STATUS: calculation engine technically ready; genuine Composite production data and rights NOT supplied.**

## What has been proven in GitHub Actions

1. `nasdaq_listing_breadth_lab.py`: real Yahoo OHLC in a deliberately nonrepresentative 24-ticker PIT **Nasdaq listing** QA sample. 60 sessions and all five windows, with incomplete IPO histories / missing observations excluded from denominators. **Do not report the sample as index breadth.**
2. `nasdaq_bulk_breadth_engine.py`: DuckDB computes 1/5/10/20/60-session A/D, percent above 50/200DMA (average of daily percentages), adjusted high/low 52-week new-high/new-low counts, and coverage in one batch. **Synthetic stress test**: 3,400 invented securities across 311 synthetic session numbers; 1,050,086 made-up OHLC rows and 202,573 synthetic constituent-day rows. All 60 daily rows and all five summary windows generated. The synthetic dates are not actual trading sessions and the simulated percentages are NOT market information. Run: https://github.com/Hernggg/us-market-breadth/actions/runs/44712820796
3. `nasdaq_licensed_input_adapter.py`: tested OFFLINE loading of local rights-cleared Parquet files. No network calls, paid API access, or raw prices and rosters committed to Git. Deliberately refuses missing license attestations. End-to-end import from temporary Parquet verified exactly against the in-memory reference.
4. Full regression suite passed **60 tests**: https://github.com/Hernggg/us-market-breadth/actions/runs/44713334375

## Required Parquet input contracts

**A — `calendar.parquet`**
- Exactly 311 unique ascending real US exchange trading dates.
- Column `trade_date` (DATE). No weekends/closed sessions in actual production calendar.
- This is **60 target sessions + 251 previous sessions** for 252-session high/low.

**B — `members.parquet`**
- Columns `security_id` (stable, non-reused share identifier), `trade_date` (DATE).
- Exactly all 60 target sessions of genuine **historical point-in-time** members.
- An actual Nasdaq Composite licensed constituent data source, or explicitly *different* Nasdaq listed-security research proxy; never interchange them.
- Include securities deleted/transferred/delisted before latest date on the exact prior sessions they belonged to. Never backfill current members to earlier dates.

**C — `prices.parquet`**
- Columns `security_id`, `trade_date`, `adj_close`, `adj_high`, `adj_low`.
- All relevant bars from the last 311 sessions for every member. Must use a *consistent split-adjustment basis* across all three OHLC fields; clarify whether dividend-adjusted and whether 52-week highs are intraday high/low.
- If a stock had not yet IPO'd, no earlier bar exists; leave missing. Do not synthesize a price to complete 252-day lookbacks.
- Permanent `security_id` must survive **ticker changes and reuse**, with lineage reconciled to the member provider; do not assume today's symbol equals identity.

## Usage (only after both data rights verified)

```bash
python nasdaq_licensed_input_adapter.py \
 --calendar /private/calendar.parquet \
 --members /private/members.parquet \
 --prices /private/prices.parquet \
 --membership-rights-confirmed --price-rights-confirmed \
 --membership-provider "EXACT LICENSED SOURCE" \
 --price-provider "EXACT LICENSED SOURCE" \
 --out /private/nasdaq_breadth_research.json
```

These CLI flags are a **user attestation** and are not a legal review. Results are always marked `publish_to_us_market=false` until separate data-license, actual index membership and coverage audit requirements pass. The work cannot be enabled by default on public repository without verifying rights and retention arrangements.

## Data quality and publication gates

- License for official COMP historical constituent use and derived-data storage/analysis; review Nasdaq GIW / Global Index Data Policy and any permitted vendor.
- License for stock OHLC history; complete historical delisted names and corporate actions. E.g. current MarketParquet data are split-adjusted, and its available sample and vendor coverage require verification; it cannot be treated as complete 311-session history by assumption.
- Source coverage separately by *member-day* for priced, prior close A/D, MA50, MA200, 252-day highs/lows.
- Benchmark daily member totals vs authorized official constituent source, document true universe and security-ID continuity.
- Pass 60-row QA and no forward fills; only after coverage and entitlement gates consider a production V2.0 Nasdaq Composite section.

## Current isolation
- Research branch: `research/nasdaq-composite-pit`, draft PR #1.
- S&P 500 production `main`, `public/latest.json` and existing daily update remain unchanged.
- No automation for Nasdaq GIW exports is active on this branch pending permission.
