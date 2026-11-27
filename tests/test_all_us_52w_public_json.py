"""Offline schema regression tests; input figures are SYNTHETIC, never published as quotes."""
import datetime as dt
import unittest
from research.all_us_52w.compute_public_history_once import calculate, calculate_both

def sample(days=65):
    dates=[]
    day=dt.date(2026,8,3)
    while len(dates)<days:
        if day.weekday()<5:
            dates.append(day)
        day+=dt.timedelta(days=1)
    rows=[]
    for i,d in enumerate(dates):
        rows.append({
            "date":d.isoformat(),
            "new_highs":10+i,
            "new_lows":110-i,
            "total_issues":4300,
            "nh_nl_diff":(10+i)-(110-i),
            "nasdaq_new_highs":3+i,
            "nasdaq_new_lows":80-i,
            "nasdaq_issues":2450,
        })
    return {"last_updated":"2026-11-25T00:00:00+00:00","data":rows},dates


class RealSourceSchemaTests(unittest.TestCase):
    def test_two_independent_real_input_shapes_compute_all_five_windows(self):
        source,days=sample()
        out=calculate_both(source,expected_date=days[-1].isoformat(),calendar=days)
        all_us=out["all_us_qualifying_common_stocks"]
        ndq=out["nasdaq_listed_qualifying_common_stocks"]
        self.assertEqual([w["sessions"] for w in all_us["windows"]],[1,5,10,20,60])
        self.assertEqual([w["avg_new_highs"] for w in all_us["windows"]],[74,72,69.5,64.5,44.5])
        self.assertEqual(ndq["windows"][0]["avg_new_highs"],67)
        self.assertEqual(ndq["windows"][-1]["avg_new_lows"],45.5)
        self.assertTrue(all_us["last_60_market_dates_crosschecked"])
        self.assertIn("NOT strict Nasdaq Composite",ndq["universe"])
        self.assertNotEqual(all_us["latest_universe_count"],ndq["latest_universe_count"])

    def test_less_than_60_real_records_is_rejected(self):
        s,d=sample(59)
        with self.assertRaisesRegex(ValueError,">=60"):
            calculate_both(s,calendar=d)

    def test_missing_day_is_rejected_against_independent_calendar(self):
        s,d=sample()
        s["data"].pop(-6)
        with self.assertRaisesRegex(ValueError,"Last 60 sessions differ"):
            calculate_both(s,calendar=d)

    def test_duplicate_day_is_rejected(self):
        s,d=sample()
        s["data"][-2]["date"]=s["data"][-1]["date"]
        with self.assertRaisesRegex(ValueError,"Duplicate or out-of-order"):
            calculate_both(s,calendar=d)

    def test_stale_last_session_is_rejected(self):
        s,d=sample()
        with self.assertRaisesRegex(ValueError,"Source is stale"):
            calculate_both(s,expected_date="2026-11-24")

    def test_malformed_net_new_highs_is_rejected(self):
        s,d=sample()
        s["data"][-1]["nh_nl_diff"]=10000
        with self.assertRaisesRegex(ValueError,"NET mismatch"):
            calculate_both(s)

    def test_missing_nasdaq_count_cannot_be_silently_inferred(self):
        s,d=sample()
        del s["data"][-1]["nasdaq_new_lows"]
        with self.assertRaisesRegex(ValueError,"complete NASDAQ"):
            calculate_both(s)

    def test_without_independent_calendar_it_is_explicitly_unverified(self):
        s,d=sample()
        out=calculate_both(s)
        self.assertFalse(out["all_us_qualifying_common_stocks"]["last_60_market_dates_crosschecked"])
        self.assertFalse(out["nasdaq_listed_qualifying_common_stocks"]["last_60_market_dates_crosschecked"])


if __name__=="__main__":
    unittest.main()
