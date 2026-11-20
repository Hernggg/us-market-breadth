# EODData API free-plan feasibility + 52-week high/low cross-source audit

Date of audit: **2026-11-21 (Malaysia)**. This is a *research and access* milestone, not a production feed or full EODData authenticated test.

## 1. EODData official API and rights

- Official API introduction: https://www.eoddata.com/products/API.aspx
- Official interactive API docs: https://api.eoddata.com/
- Published endpoints include `GET /Quote/List/{exchangeCode}/{symbolCode}` for series / historical quotes and `GET /Quote/Get/{exchangeCode}/{symbolCode}` for a single quote. The spec lists INDEX exchange and symbol codes, but does **not by itself establish that the FREE account may read each INDEX indicator**.
- EODData says every API request requires `apiKey`. Credentials must be saved privately, not in code or chat.
- Membership: Standard FREE plan is advertised with **100 API calls/day, 10 calls/minute, and a 30-day EOD historical-data entitlement tier**. It is not yet verified that free API responses include all 10 breadth INDEX symbols or complete 30 days per series.
- Terms: https://www.eoddata.com/about/terms.aspx — allow personal storing/manipulation/analysis; prohibit redistribution of vendor information and scraping the quote website. Use an authorized API subscription for programmatic access; **no public GitHub commit of raw or vendor-derived daily quotes**.
- Because the repository is PUBLIC, the probe only prints status, schema field names and counts/dates, never quote values. No cron schedule.

## 2. Completed GitHub test

Files:
- `research/eoddata/eoddata_api_probe.py`
- `.github/workflows/eoddata-api-feasibility.yml`
- `tests/test_eoddata_api_probe.py`

GitHub Actions run (5 tests passed): https://github.com/Hernggg/us-market-breadth/actions/runs/44834143415

Result: `NO_API_KEY_CONFIGURED` for an offline probe. This demonstrates a correctly gated probe, **NOT** actual free plan authenticated index data access. We cannot state that free INDEX history works until the user creates their own EODData API key and the authenticated test is manually executed.

Security: key stored only as repository secret `EODDATA_API_KEY`; never paste in chat or push to repo; workflow is READ-ONLY and does not save vendor prices. An authenticated `workflow_dispatch` tests NCFI, NCTH, MAHQ using at most three calls.

## 3. Source-side 52-week high/low differences

**Completed trading date November 19, 2026**

| Vendor/quote source | Nasdaq 52W new highs | Nasdaq 52W new lows | S&P500 new highs | S&P500 new lows |
| --- | ---: | ---: | ---: | ---: |
| TradingView user Pine screenshot, `MAHQ/MALQ/MAHP/MALP` | 11 | 450 | 0.01 (invalid number of stocks) | 16 |
| EODData `INDEX/MAHQ/MALQ/MAHP/MALP` historical EOD close | 11 | 450 | 0.01 (invalid count) | 16 |
| Reuters market-close article | 34 | 529 | 1 | 18 |

**Completed trading date November 20, 2026** (the user's prior screenshot was *Nov 19*, so this is a separate date)

| EODData INDEX source | Nasdaq highs | Nasdaq lows | S&P highs | S&P lows |
| --- | ---: | ---: | ---: | ---: |
| `MAHQ/MALQ/MAHP/MALP` latest completed historical EOD row | 3 | 284 | 1 | 25 |
| Reuters FINAL market-close article | 21 | 826 | 3 | 28 |

Sources:
- https://www.eoddata.com/stockquote/INDEX/MAHQ.htm
- https://www.eoddata.com/stockquote/INDEX/MALQ.htm
- https://www.eoddata.com/stockquote/INDEX/MAHP.htm
- https://www.eoddata.com/stockquote/INDEX/MALP.htm
- https://www.reuters.com/business/nasdaq-futures-jump-anthropics-record-ipo-pricing-fuels-hopes-strong-debut-2026-11-19/
- https://www.reuters.com/legal/transactional/wall-st-futures-slip-anthropic-debut-fails-reassure-ai-investors-2026-11-20/

**Conclusion:** the user's Pine code is NOT the source of the difference: its Nasdaq 11/450 and S&P 0.01/16 were reproduced exactly by an independent site (EODData) for Nov 19, which is a **cross-feed agreement for those published symbols**, not proof the counts are certified official. Reuters calls its count Nasdaq **Composite** while EODData uses **52-Week Highs/Lows Nasdaq**. Both series may implement different eligible security populations, price filters, quote cutoffs, intraday highs/lows vs closing highs/lows, or corporate-action rules. We do not have vendor identities/methodology to prove which cause(s) explain the exact gap; do not publish an invented precise cause or "correct" values using a constant factor.

Nov 19 relative gaps vs Reuters: Nasdaq high count 11 vs 34 (−67.65%), low count 450 vs 529 (−14.93%). Nov 20 high 3 vs 21 (−85.71%), low 284 vs 826 (−65.62%). The gaps are variable, proving a constant percentage correction is unsafe.

**Important**: EODData S&P500 `MAHP=0.01` on Nov 19 is an impossible count. Treat as a vendor anomaly / sentinel-like number (unconfirmed whether representing 0 or missing); do **not** round to 0 or 1 silently, and do not make unverified assumptions about its 5/10/20/60 day averages.

Generic TradingView documentation for **its newly defined** New Highs/Lows breadth metric gives current intraday high >= lookback high, current intraday low <= lookback low. That generic documentation does NOT prove the older `MAHQ` INDEX vendor series uses precisely the same scope/methodology:
https://www.tradingview.com/support/solutions/43000794826-market-breadth-new-highs-and-lows/

## 4. Guidance for @us-market practical market sentiment

- Use **one stable vendor** for within-series trend, not mixed-vendor rolling windows. The user accepts small differences for sentiment.
- Tag `MAHQ/MALQ` as `Nasdaq exchange-type 52W (vendor-specific)`, **NOT** proven Composite-only. Show Reuters dated official-article figures as a **separate row/cross-check**, not merged into the 60-day averages.
- Validate date as completed NY market session; EODData website simultaneously displays live LAST and completed historical EOD Close, which can differ.
- Prefer new lows versus 5/20/60-day averages to assess selling pressure; if signal is extreme, corroborate with above-50/200DMA and A/D before drawing conclusions.
- If daily 52W count is noninteger (e.g. 0.01), show `INVALID_VENDOR_COUNT` until source semantics are confirmed; flag rolling averages as potentially affected.
- Do not claim precise source-to-source *measurement error* unless same universe and method are proven. We are measuring **disagreement between definitions**, not ground-truth measurement error.
- Nasdaq Trader's free daily 2026 A/D file has **NO 52W high/low fields** in published field definitions, so cannot resolve this particular conflict (https://nasdaqtrader.com/Trader.aspx?id=DailyMarketSummaryDefs).

## 5. Honest open gate and next user-only step

The authenticated test cannot run without `EODDATA_API_KEY`. First register for an EODData Standard **free** personal account, locate **My Account → API** key and add it as a GitHub repository secret:
Settings → Secrets and variables → Actions → New repository secret:
**Name** `EODDATA_API_KEY`; **Value** pasted privately from EODData account.

Once configured, run the EODData API entitlement workflow manually. Until it returns actually authorized INDEX history and acceptable license/retention conditions, **do not schedule it daily or claim all 5 windows can automatically update**. Even if authenticated access succeeds, public GitHub publication of vendor values remains prohibited without permission; use private data storage/workflows or a permitted nonredistributable reporting route.

No change to the user-validated 3-in-1 TradingView Pine script or `main` S&P500 production.
