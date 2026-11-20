# @us-market V2.0 — TradingView official MCP path (2026-11-20)

## The breakthrough

**TradingView officially supports a ChatGPT custom MCP connection** at:
`https://mcp.tradingview.com/mcp`

Official docs: https://www.tradingview.com/mcp/docs

The authorized MCP provides:
- **get_ohlcv**: actual daily history for symbols, up to the plan/data entitlement. Request `INDEX:NCFI` or `INDEX:NCTH`, `1D`, `count=70` (enough for a 60-trading-session mean), as well as `INDEX:S5FI` and `INDEX:S5TH`.
- **run_pine_indicator**: compiles and runs a Pine script on the vendor chart servers and returns last closed bar plot values; supports `calc_bars_count`, output plot names and forming-bar flags. The prepared script is in `research/tradingview/us_market_ma_breadth.pine`.
- **validate_pine_script**: compile-checks the prepared script without saving; use it first.
- TradingView's official terms are PERSONAL question-answering only. Do not create a persistent dataset or GitHub scraper from MCP data, and do not distribute data outside the user's permitted private scope.

## One-time setup (user action, paid TradingView plan required)

According to TradingView's own instructions:
1. ChatGPT → Settings → Plugins → Add → MCPs → Add → Add MCP Server.
2. Type: Streamable HTTP.
3. URL: `https://mcp.tradingview.com/mcp`.
4. Save, open Plugins → MCPs, authenticate via OAuth and grant access.
5. Then test privately: `Use my connected TradingView account to retrieve the latest 70 completed daily bars for INDEX:NCFI and INDEX:NCTH; compute the 1/5/10/20/60-day arithmetic averages, show as-of exchange date and source status.`

The access token is kept by the connector; never place it in GitHub, chat or a downloaded file. Do not assert the connection succeeded until the authenticated TradingView actions actually appear and return data. TradingView docs say paid plan needed and request quotas apply (e.g., Essential 10, Plus 20, Premium 50 MCP calls/day, as documented when checked; plan could change).

## Private Q&A source priority after connected

1. Prefer TradingView official `get_ohlcv` on `INDEX:NCFI`, `INDEX:NCTH`, `INDEX:S5FI`, `INDEX:S5TH`, interval `1D`, `count>=70`, **only the last 60 completed unique exchange sessions**. Exclude a still-forming bar, any missing/duplicate date and implausible percentage outside 0..100. For closed day (d), `Avg60 = sum(last 60 daily closes of that indicator)/60`, similarly 5, 10, 20. Check that `symbol` actually resolved to requested symbol.
2. Alternatively use authorized `run_pine_indicator` to evaluate `research/tradingview/us_market_ma_breadth.pine` directly on `NASDAQ:IXIC`, timeframe `1D`; first `validate_pine_script`, then compare 1/5/10 day data against independent source pages on demand.
3. **Nasdaq exchange-wide A/D:** official Nasdaq Trader daily file already available in the repository research branch. This is **NOT strict Composite member A/D**; show its own universe and actual source end date (sometimes two days stale).
4. **Nasdaq 52-week highs/lows:** use a separate sourced series with provider population expressly stated; `INDEX:MAHQ`/`MALQ` are tagged Nasdaq exchange-like until verified. Likewise S&P500 `INDEX:MAHP`/`MALP` require provider confirmation.
5. All eligible U.S. ordinary stocks remain separate third universe and cannot be silently substituted with Nasdaq or SP500.

Report by universe, per-daily and 5/10/20/60-day window. Distinguish average of daily **percent above moving average** vs number of stocks. Never extrapolate 60D from 20D SMA. No simulation accepted.

## Compliance

TradingView states explicitly: MCP data for individual personal AI question answering only. No building datasets/databases/feeds, redistributing content or automated trading. Connecting to ChatGPT for personal answers is supported; building the same data in public GitHub via MCP would NOT be permitted. Our GitHub stores **only source code + procedures + synthetic QA**, not TradingView historical bars.

Official docs:
- Setup: https://www.tradingview.com/mcp/docs
- `get_ohlcv`: /mcp/docs market data section
- `run_pine_indicator`: /mcp/docs Pine scripts section
- Terms: /mcp/docs Terms of use

## Honest current status

- The ChatGPT runtime has **NO TradingView tool connected** as of this research check, so no live MCP command or end-to-end authorized 60-day result has yet been verified.
- A successful source code QA result or a Pine script in GitHub is not a completed live TradingView connection.
- There is no need to pay for another 3,400-stock historical feed to answer the *above-MA percentage* metrics when authorized TradingView source series are available.
- Original S&P 500 production pipeline on `main` is untouched.
