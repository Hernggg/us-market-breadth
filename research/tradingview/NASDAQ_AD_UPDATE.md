# TradingView Basic — single script with MA, 52W, Nasdaq A/D (2026-11-20)

The **one saved-script** Basic-plan version is:
- `us_market_combined_basic_with_nasdaq_ad.pine` (new; NOT yet compiled in the user's TradingView)
- It extends the **already tested** `us_market_combined_basic_one_script.pine` by exactly two vendor daily histories: `INDEX:ADVQ` and `INDEX:DECQ`.
- Pine static QA: 1 indicator declaration, 10 unique `request.security()` symbols, 50 plots (Pine limit 64), a single 5-column x 19-row table.
- The new Nasdaq A/D panel has Daily, 5, 10, 20, 60 days, mean number of advancers, mean number of decliners, A/D ratio (sum of advancers divided by sum of decliners, NOT average of daily ratios), mean net advancers.
- `ADVQ` and `DECQ` are **Nasdaq EXCHANGE issues** statistics, NOT confirmed Nasdaq Composite-only constituents. Do not claim they use the same universe as `NCFI`/`NCTH`. The A/D totals also differ in scope/definitions from Nasdaq Trader's own official files.
- Data provenance: [TradingView ADVQ](https://www.tradingview.com/symbols/INDEX-ADVQ/), [DECQ](https://www.tradingview.com/symbols/INDEX-DECQ/). Also [EODData ADVQ](https://eoddata.com/stockquote/INDEX/ADVQ.htm) and [DECQ](https://eoddata.com/stockquote/INDEX/DECQ.htm), both independent public symbol descriptions and history.
- Existing `MAHP` daily 0.01 vendor value remains **flagged as anomalous**; not coerced to zero or one. Derived averages from this source require corroboration.
- Important: TradingView's generic "Market breadth — Advancing and Declining" documentation includes unchanged as declines for its newer index breadth metrics, whereas `ADVQ`/`DECQ` are a historically established separate exchange series and must be independently compared. Do not combine without investigating category definitions.

## User operation (no paid plan)
1. On existing saved TradingView Basic indicator, open Pine Editor.
2. Copy the **Raw** new script and `Ctrl+A`, `Ctrl+V` to replace previous **one existing saved script** in editor.
3. Click **Save**, NOT **Save As**; click Add to chart if not auto-reloaded.
4. Check three blocks all display on chart and last bar is completed 2026-11-19 for as-of date.
5. Take screenshot of the Nasdaq A/D section and compare that single completed day's ADVQ/DECQ values against independent source if matching date; source-lag and definitions must be stated.
6. Save chart layout again. If any of 50 plots or request limits error on Basic, revise before proceeding; never ask to pay as first solution.

**Not done:** new Pine version has not been validated by an authenticated TradingView Pine compiler, nor is ChatGPT/GitHub unattended live ingestion available. Strict Composite constituent-only A/D remains unresolved.
