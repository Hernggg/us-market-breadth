# @us-market V2.0 — TradingView-based real market breadth data path

**2026-11-20 research update. This is NOT an unattended data feed.**
No scrapers, undocumented TradingView APIs, or automatic TradingView exports
are used or enabled. S&P production main and public/latest.json are unchanged.

## 1. Existing vendor indicators (not new stock-by-stock calculations)

| Universe | Purpose | TradingView symbol | Units |
|---|---|---|---|
| Nasdaq Composite | Percent of constituents above own 50-DMA | INDEX:NCFI | percent (0..100) |
| Nasdaq Composite | Percent above own 200-DMA | INDEX:NCTH | percent |
| S&P 500 | Percent above own 50-DMA | INDEX:S5FI | percent |
| S&P 500 | Percent above own 200-DMA | INDEX:S5TH | percent |
| Nasdaq / Nasdaq exchange issues | 52-week new HIGH issues | INDEX:MAHQ | number of issues |
| Nasdaq / Nasdaq exchange issues | 52-week new LOW issues | INDEX:MALQ | number |
| S&P 500 | 52-week new HIGH issues | INDEX:MAHP | number |
| S&P 500 | 52-week new LOW issues | INDEX:MALP | number |

TradingView's market breadth help explicitly defines above-MA as percent of
index constituents with daily CLOSE > own MA50 or MA200:
https://www.tradingview.com/support/solutions/43000794827-market-breadth-above-moving-averages/

Market breadth new highs/lows uses **current intraday high/low** and a
1-year lookback, with >= / <= definitions:
https://www.tradingview.com/support/solutions/43000794826-market-breadth-new-highs-and-lows/

**Critical universe note**: MAHQ/MALQ TradingView labels say "52-Week
Highs/Lows Nasdaq" and are not confirmed to be STRICT Nasdaq Composite
constituent-only counts; show as "Nasdaq exchange" until verified.
Nasdaq Trader official annual advances/declines counts Nasdaq-LISTED ISSUES,
NOT proven exact Composite membership. Do not conflate these series.

## 2. Pine scripts (actual series from user's TradingView)

A. [us_market_ma_breadth.pine](./us_market_ma_breadth.pine)
- Four actual percent-above-MA vendor series, five 1/5/10/20/60 trading-day
  values each, using TradingView's own request.security("INDEX:...", "1D").
- The **5/10/20/60** measure is the **daily arithmetic average** of the
  % above the 50DMA or % above 200DMA; it is NOT "% above 5DMA" or
  "% above 10DMA".
- On-chart table; 20 uniquely named plots in TradingView Data Window and
  chart CSV export.
- Source is static Pine code reviewed against the Pine v6 docs but
  **NOT COMPILED OR TESTED INSIDE A LIVE TRADINGVIEW CHART** yet.

B. [us_market_52w_nh_nl.pine](./us_market_52w_nh_nl.pine)
- Nasdaq exchange labeled MAHQ/MALQ and S&P 500 MAHP/MALP new-high/new-low
  issue counts for 1D and average over 5/10/20/60 days.
- Again, **not chart-runtime tested**; if any symbol returns N/A, display
  N/A with reason rather than substituting fake figures.
- MAHQ/MALQ must remain marked Nasdaq exchange *candidate* until explicit
  index-only membership verification.

### One-time personal visualization setup

1. Open a TradingView Superchart, preferably NASDAQ:IXIC, set **1D**.
2. In Pine Editor, paste script A, save it, add to chart.
3. Look for the on-chart table (five windows) and verify indicator
   symbols resolve to non-empty daily values; use script B optionally.
4. If a personal-export CSV is needed, TradingView's official
   **Download chart data...** can export the indicators' plots.
   Export availability and loaded history depend on plan and chart:
   https://www.tradingview.com/support/solutions/43000537255-how-to-export-chart-data/
5. NEVER upload chart-data CSV to the PUBLIC GitHub repo. It is not needed
   to see the Pine table on your private chart.

Offline personal CSV validation tool (not required to SEE the chart table):

```bash
python research/tradingview/parse_private_breadth_csv.py \
  --csv /private/US_Market_Breadth_export.csv \
  --expected-session 2026-11-19
```

- The tool requires all 20 plots and validates 0..100% bounds, duplicate
  dates, exact requested as-of date, and recomputes every rolling average
  when the export contains 5/10/20/60 observed rows. It never calls
  TradingView endpoints. An external private --out path can be selected;
  the source export and aggregate outputs must not be committed into
  the public GitHub working tree.
- This offline parser has automated **synthetic CSV fixture** unit tests:
  not evidence that the user's actual TradingView export already works.

## 3. Real-source verification without vendor data republication

- EODData's Nasdaq NCFI / NCTH pages display genuine completed end-of-day
  close series and on-page indicator SMA5, SMA10 and SMA20 values.
- A successful private one-off review checked 5/10 day arithmetic means of
  its latest 10 **historical close** observations against the site's SMA
  figures. The 20-day SMA was visible on the source page; a 60-day mean was
  not.
- IMPORTANT: those websites also show an intraday "LAST" quote.
  Do not mix intraday snapshots with the completed END OF DAY Close.
- https://eoddata.com/stockquote/INDEX/NCFI.htm
- https://www.eoddata.com/stockquote/INDEX/NCTH.htm
- Reuters also publishes daily Nasdaq **exchange-wide** A/D and
  Nasdaq Composite / S&P500 52-week NH/NL in its US market-close reports,
  explicitly noting different populations:
  https://www.reuters.com/business/nasdaq-futures-jump-anthropics-record-ipo-pricing-fuels-hopes-strong-debut-2026-11-19/

Avoid storing or redistributing source page quote tables or proprietary
vendor aggregates in this public GitHub repo without appropriate rights.
One-off private question answering should cite and date source pages.

## 4. Data availability / @us-market completion chart

- Nasdaq/S&P percent above 50/200DMA, 1/5/10/20D:
  genuine historical examples available; full 60D needs a 60-point
  TradingView chart export or another authorized historic feed.
- Nasdaq exchange A/D 1/5/10/20/60D: working official NasdaqTrader
  2026 YTD source through its reported actual latest date, which may lag
  by days; NEVER relabel Composite member-only A/D.
- Nasdaq 52-week NH/NL 1/5/10/20/60D: Pine reference scripts written,
  actual 60D vendor-series values NOT YET VALIDATED.
- Exact Nasdaq **Composite-only** advances/declines and highs/lows:
  still require true daily member population/authorized derivative data.
- Full eligible US common-stock universe: still separate and unsolved.
- S&P price/sector series and PIT breadth: already under its own
  **provisional**, not "official certified" S&P pipeline.

## 5. Rights and safety

TradingView prohibits automated collection, undocumented APIs and
unpermitted data extraction/storage; do not build daily GitHub scraping:
https://www.tradingview.com/policies/

Its official MCP, where available, permits personal question answering
but not bulk database creation or redistribution. No TradingView app
connector is currently installed in this project.
https://www.tradingview.com/mcp/docs

**Research branch only, draft PR.** GitHub auto-report with up-to-date
50/200 MA cannot be advertised as done until a clearly permitted automated
data service has been connected and verified. No invented historical bars,
no simulated values in @us-market report.
