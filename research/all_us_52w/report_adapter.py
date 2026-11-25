"""Private, on-demand @us-market report adapter. No scheduled fetch or public data storage.
Run only in an authorized personal environment. Requires exchange-calendars for live use.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
from research.all_us_52w.compute_full_breadth_three_json_once import (
    PATHS, load_public_json, validate_and_compute, count, calc_nhnl,
)

def latest_closed_sessions(now=None):
    import exchange_calendars as xcals
    import pandas as pd
    now = pd.Timestamp(now or dt.datetime.now(dt.timezone.utc))
    if now.tzinfo is None:
        raise ValueError("Timezone-aware clock required")
    now = now.tz_convert("UTC")
    cal = xcals.get_calendar("XNYS")
    labels = cal.sessions_in_range((now - pd.Timedelta(days=120)).date(), now.date())
    closed = [s for s in labels if cal.session_close(s) <= now]
    if len(closed) < 60:
        raise ValueError("Independent exchange calendar lacks 60 completed sessions")
    return [s.strftime("%Y-%m-%d") for s in closed[-60:]]

def report_payload(ad, ma, nh, sessions):
    if len(sessions) != 60 or sessions != sorted(set(sessions)):
        raise ValueError("Expected exactly 60 independent closed trading sessions")
    out = validate_and_compute(ad, ma, nh, sessions)
    rows = nh["data"][-60:]
    for row in rows:
        h, l, n = (count(row[k], k) for k in
                   ("nasdaq_new_highs", "nasdaq_new_lows", "nasdaq_issues"))
        if not 500 <= n <= 6000 or h > n or l > n:
            raise ValueError("Invalid Nasdaq NH/NL sample")
    out["nasdaq_exchange_52w"] = {
        "source_file": PATHS["nhnl"], "source_end": rows[-1]["date"],
        "daily_sample_size": rows[-1]["nasdaq_issues"],
        "periods": calc_nhnl(rows, "nasdaq_new_highs", "nasdaq_new_lows"),
    }
    out.update({"schema_version": "us-market-v2.1-breadth-1",
                "target_trade_date": sessions[-1], "status": "verified",
                "calendar_source": "XNYS exchange_calendars, closed sessions",
                "sections": {"4.1": ["all_us_ad", "nasdaq_exchange_ad"],
                             "4.2": ["all_us_ma"],
                             "4.3": ["all_us_52w", "nasdaq_exchange_52w"]},
                "nasdaq_ma_note": "Separate TradingView Composite NCFI/NCTH; not supplied by this adapter"})
    return out

def run(fetch=load_public_json, sessions=None):
    sessions = sessions if sessions is not None else latest_closed_sessions()
    data = {}
    actual_dates = {}
    try:
        for key, path in PATHS.items():
            data[key] = fetch(path)
            rows = data[key].get("data", [])
            actual_dates[key] = rows[-1].get("date") if rows else None
        return report_payload(data["ad"], data["ma"], data["nhnl"], sessions)
    except Exception as exc:
        return {"schema_version": "us-market-v2.1-breadth-1",
                "target_trade_date": sessions[-1], "status": "unavailable",
                "error": str(exc), "actual_source_dates": actual_dates, "source": "https://www.thetrading.tools/datasets",
                "note": "Do not reuse an older result as current or fill missing sessions."}

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True, help="Private local output file; never public GitHub")
    p.add_argument("--personal-use-confirmed", action="store_true")
    args = p.parse_args()
    if not args.personal_use_confirmed or os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("PRIVATE_BREADTH_AUTHORIZED") != "yes":
        p.error("Explicit personal-use authorization required; public CI must not run live fetch")
    result = run()
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    temp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(target)
    raise SystemExit(0 if result["status"] == "verified" else 1)

if __name__ == "__main__":
    main()
