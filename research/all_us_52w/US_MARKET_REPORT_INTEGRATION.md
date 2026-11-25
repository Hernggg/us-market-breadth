# @us-market V2.1 — report integration contract

Status: research branch; not deployed to private production. No public recurring live fetch or data publication.

When the user requests @us-market:
1. Determine latest completed US equity session from an exchange calendar (New York time, holidays and early closes). The target is independent of vendor publication dates.
2. Read S&P PIT latest/status from existing production repository. Keep original update process unchanged.
3. Use private report_adapter.py on demand after personal-use authorization and private execution path are available. It reads the three fixed publisher files once each and generates only five-window derived results. Do not copy raw historical data to public GitHub, public job logs, or public artifacts. No unattended schedule until provider usage permission is confirmed.
4. For verified output, require schema us-market-v2.1-breadth-1, status verified, actual_asof_date == target_trade_date and all source_end dates equal target. Each series must have exactly 1/5/10/20/60 windows.
5. Map 4.1 all_us_ad and nasdaq_exchange_ad, 4.2 all_us_ma, 4.3 all_us_52w and nasdaq_exchange_52w. Keep every daily_sample_size, source_file, actual date and universe note. Nasdaq Exchange is not Nasdaq Composite. Preserve TradingView NCFI/NCTH separately for Nasdaq Composite MA; no invented history. Preserve S&P PIT columns and 4.4/4.5 original exact-close returns.
6. If output unavailable or stale, disclose target and actual source dates; do not present an earlier snapshot as current. If an older independently verified result is available, show it only with its actual date and clear stale status. Continue news/narratives and other verified modules, with specific missing reasons, never fabricate numbers.
7. Retain the user's five-stage V2.1 report, emphasis on substantive news and market narratives. No user screenshots or local scripts should be required in the intended production path.

Private deployment prerequisite: create/authorize private repository; copy adapter + existing computation module + tests. Install Python 3.12 and exchange-calendars>=4.5,<5. A private on-demand runner may execute:
```sh
PRIVATE_BREADTH_AUTHORIZED=yes python -m research.all_us_52w.report_adapter --personal-use-confirmed --output private/latest.json
```
Keep only private derived output, not raw source files. On error the output is an explicit unavailable status, not an old result relabeled current. Test a new actual trading session end to end before claiming production readiness. Private storage does not itself grant vendor permission.

The public QA workflow uses synthetic fixtures and exchange calendars only. No vendor data access or publication is enabled. The connector does not currently expose repository creation or workflow dispatch; a private execution trigger must be confirmed before claiming automatic operation.
