# @us-market V2.1 — ALL-US 52-week NH/NL FIRST, optional Nasdaq exchange proxy
Research decision note · 2026-11-25 MYT

This note documents the user's requested order of work. It DOES NOT change the
locked five-stage report template, publish unlicensed market data, or claim that
the missing 60-day series is already acquired.

## Priority 1: All U.S. qualified ordinary shares — 52-week highs / lows

Required per the original V2.1 4.3:
- D, previous 5/10/20/60 U.S. equity TRADING-session averages of daily
  numbers of 52-week new highs (NH) and new lows (NL), plus net NH-NL.
- Each observation must carry exchange trading date, actual eligible security
  universe and size (denominator), source URL, intraday high/low or close
  method, update time/lag, coverage, and entitlement.
- Rolling averages use 5/10/20/60 distinct dated actual observations;
  10-day NET-only data cannot recover separate NH and NL histories.
- Any missing/partial historical window must remain absent and explain why;
  do NOT backfill 60 days from a plot, extrapolate, or merge changing vendors.

### Candidate source: thetrading.tools

https://www.thetrading.tools/new-highs-new-lows

Verified website display as-of Nov 24 2026:
- All U.S. eligible common shares: **63 NH / 280 NL, sample 4,360**;
- Website explicitly has research history back to 2010 and charts for
  NH-NL percent, 10-session average of percentage NH and NL separately,
  and cumulative NH-NL.
- Page separately states latest single-day NH and NL. The "Last 10 sessions"
  visible table reports NET NH-NL, not separate daily NH/NL counts.
- Therefore the public text/summary **does not prove that 60 daily NH AND
  NL numerical rows can be obtained, exported, or used by unattended
  GitHub Actions**. Investigate its documented export/API/licensing or
  ask the owner before building a programmatic ingestion.
- Sample methodology excludes ETFs, closed-end funds, structured products,
  warrants, units and preferred stocks, requires one year of prior price
  history and uses each issue's prior-365-calendar-day intraday extremes.
  The company list uses the *current* universe carried backwards, so
  long-range history shows survivor bias — state this if using history.
- The 4,360 denominator is NOT ScreenerCharts' 5,745-issue A/D universe:
  do NOT combine denominators or claim same statistical population.

### Alternatives / corroboration
- https://screenercharts.com/us/market-breadth has date-scoped past 20-day
  A/D and 50/200MA table but **does not furnish 52-week NH/NL 60-session
  historical rows** there.
- https://screenercharts.com/us/technicals displays a single-day
  52-week highs / lows scan; data population and data reuse permissions
  require independent checking.
- https://www.barchart.com/stocks/highs-lows "All US Exchanges" common
  share selection is useful and clearly excludes ETFs, special purpose
  acquisition companies and units, but any 60-day history export/API
  entitlement must be proven; its population differs again.
- StockCharts https://stockcharts.com/freecharts/marketsummary.html
  has exchange/index NH/NL market indicator charts, not automatically a
  U.S. eligible-common-stocks total. Exchange indicators may include
  ineligible security types and thus aren't drop-in replacements.

### Acceptance tests before reporting "complete"
- Authorized machine-readable NUMERIC daily NH and NL (not a picture-only
  chart or merely net difference), complete last 60 sessions.
- Same daily eligibility rule and lookback definition, last session exact,
  1/5/10/20/60 mean independently reproducible and sourced.
- Source license permits desired personal use and any automated/API work.
  Do not publish licensed third-party price databases to PUBLIC GitHub.
- Compare latest-day values with a second independent date-matched source.
  Ordinary differing definitions -> mark "third-party proxy", not precision
  error versus an unknown official truth.
- No new production work before this gate. Currently NOT DONE.

## Nasdaq breadth: recommended simplification for risk appetite

The user proposes NOT pursuing strict daily PIT Nasdaq Composite constituents
for A/D and 52-week high-low tables. For practical Nasdaq / growth-risk
breadth, use existing *Nasdaq exchange-listed securities* TradingView
`INDEX:ADVQ`, `INDEX:DECQ`, `INDEX:MAHQ`, `INDEX:MALQ`
with 1/5/10/20/60-day tables, clearly labeled with population and
vendor methodology. These already ran on the user's free TradingView chart.
They are **NOT** strict Composite component breadth.

Retain:
- Nasdaq Composite headline index and historical returns (actual `IXIC`).
- `INDEX:NCFI` / `INDEX:NCTH` 50/200DMA (Composite-labelled vendor series).
- Separate Nasdaq **exchange** A/D and 52-week NH/NL.

Consequence of changing strict original V2.1 contract:
- Do NOT call the exchange A/D/NH-NL tables "Composite member-only".
- In 4.1 / 4.3 the third market section can be renamed
  "**Nasdaq trading-exchange breadth (growth/risk sentiment proxy)**",
  explicitly note this replaces strict Composite member-only requirement
  **at user's election**. Do not leave a confusing second empty
  Nasdaq Composite subsection unless user still requests it.
- In 4.2 retain explicitly "Nasdaq Composite (TV vendor-derived)"
  because the sourced symbols are different constituents from the
  exchange market breadth symbols.
- Do NOT say this measures pure "technology sector": Nasdaq hosts
  biotechnology, small caps, financials and other industries;
  exchange listed-issues data may include funds / non-common issues.
- For TECH specifically, triangulate Nasdaq price, information
  technology XLK, SOX semiconductors, and possibly Nasdaq-100/QQQ,
  plus broad-exchange participation and 52W lows.
- Caveat: exchange breadth per TradingView ADVQ/DECQ cannot simply be
  assumed fully identical to Nasdaq Trader official A/D totals.

Nasdaq Composite index methodology (daily reconstitution, eligibility):
https://indexes.nasdaq.com/docs/methodology_COMP.pdf

The user's underlying V2.1 5-stage template remains in force. This note
captures *proposed* statistical-scope revision for only the Nasdaq
constituent-level metrics, prioritizing practical risk sentiment.
No change to existing user TradingView Pine code and no production
data-source substitution.

## Immediate action order
1. Confirm authorized 60-day *separate NH/NL daily counts* source for
   all-U.S. eligible common stock universe; build transparent provenance
   and quality checks around that original series.
2. Recompute 1/5/10/20/60 means and validate latest day, denominator,
   holidays and classifications; publish internally only if rights permit.
3. Use existing Nasdaq exchange 3-in-1 breadth as sentiment proxy,
   with explicit scope and source dates; no more expensive Composite
   membership reconstruction unless a material use-case requires it.
