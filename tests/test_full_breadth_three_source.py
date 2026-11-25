"""No vendor requests here; synthetic tests for independent 60-day source validation."""
import datetime as dt
import unittest
from research.all_us_52w.compute_full_breadth_three_json_once import validate_and_compute

def fixtures():
    d=dt.date(2026,8,3)
    rows_ad=[]; rows_ma=[]; rows_nh=[]; days=[]
    while len(days)<65:
        if d.weekday()<5:
            s=d.isoformat()
            days.append(s)
            i=len(days)
            rows_ad.append({
                "date":s,
                "advancing":2500+i,"declining":1800-i,"unchanged":90,
                "net_advances":700+2*i,
                "nasdaq_advancing":1400+i,"nasdaq_declining":1050-i,"nasdaq_unchanged":70,
            })
            rows_ma.append({"date":s,"pct_above_50d":30+i/10,
                            "pct_above_200d":35-i/10,"market_stocks":4700})
            rows_nh.append({"date":s,"new_highs":40+i,
                            "new_lows":280-i,"nh_nl_diff":2*i-240,
                            "total_issues":4350})
        d+=dt.timedelta(days=1)
    return ({"data":rows_ad},{"data":rows_ma},{"data":rows_nh},days[-60:])


class FullBreadthRealSchemaTests(unittest.TestCase):
    def test_all_three_true_daily_series_complete_with_five_exact_windows(self):
        ad,ma,nh,cal=fixtures()
        r=validate_and_compute(ad,ma,nh,cal)
        self.assertEqual(r["actual_asof_date"],cal[-1])
        for key in ("all_us_ad","all_us_ma","all_us_52w","nasdaq_exchange_ad"):
            self.assertEqual([t["sessions"] for t in r[key]["periods"]],[1,5,10,20,60])
        self.assertEqual(r["all_us_ad"]["periods"][0]["avg_advances"],2565)
        self.assertAlmostEqual(r["all_us_ad"]["periods"][0]["ad_ratio"],2565/1735,places=5)
        self.assertEqual(r["all_us_ma"]["periods"][0]["avg_above_50dma_pct"],36.5)
        self.assertEqual(r["all_us_52w"]["periods"][0]["avg_new_highs"],105)
        self.assertEqual(r["nasdaq_exchange_ad"]["periods"][0]["avg_unchanged"],70)
        self.assertNotEqual(r["all_us_ad"]["daily_sample_size"],r["all_us_ma"]["daily_sample_size"])
        self.assertFalse(r["source_is_official_exchange"])

    def test_denominator_inconsistency_is_not_silently_harmonized(self):
        ad,ma,nh,cal=fixtures()
        ma["data"][-1]["market_stocks"]=3200
        r=validate_and_compute(ad,ma,nh,cal)
        self.assertEqual(r["all_us_ma"]["daily_sample_size"],3200)
        self.assertNotEqual(r["all_us_ad"]["daily_sample_size"],3200)

    def test_different_60_session_date_sets_fail(self):
        ad,ma,nh,cal=fixtures()
        ma["data"][-10]["date"]="2026-11-25"
        with self.assertRaisesRegex(ValueError,"mismatched US equity"):
            validate_and_compute(ad,ma,nh,cal)

    def test_net_advances_must_reconcile(self):
        ad,ma,nh,cal=fixtures()
        ad["data"][-1]["net_advances"]=0
        with self.assertRaisesRegex(ValueError,"net does not reconcile"):
            validate_and_compute(ad,ma,nh,cal)

    def test_nh_nl_net_must_reconcile(self):
        ad,ma,nh,cal=fixtures()
        nh["data"][-1]["nh_nl_diff"]=999
        with self.assertRaisesRegex(ValueError,"diff mismatch"):
            validate_and_compute(ad,ma,nh,cal)

    def test_invalid_percentage_rejected(self):
        ad,ma,nh,cal=fixtures()
        ma["data"][-1]["pct_above_50d"]=101
        with self.assertRaisesRegex(ValueError,"Invalid 0-100"):
            validate_and_compute(ad,ma,nh,cal)

    def test_missing_daily_record_rejected(self):
        ad,ma,nh,cal=fixtures()
        ad["data"].pop(-2)
        with self.assertRaisesRegex(ValueError,"mismatched US equity"):
            validate_and_compute(ad,ma,nh,cal)


if __name__=="__main__":
    unittest.main()
