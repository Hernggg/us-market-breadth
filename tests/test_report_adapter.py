import unittest
from test_full_breadth_three_source import fixtures
from research.all_us_52w.report_adapter import report_payload, run

def complete():
    ad,ma,nh,days=fixtures()
    for row in nh["data"]:
        row.update(nasdaq_new_highs=30,nasdaq_new_lows=170,nasdaq_issues=2450)
    return ad,ma,nh,days

class ReportAdapterTests(unittest.TestCase):
    def test_five_windows_and_nasdaq_nhnl(self):
        a,m,h,d=complete()
        out=report_payload(a,m,h,d)
        self.assertEqual(out["status"],"verified")
        self.assertEqual(out["target_trade_date"],d[-1])
        self.assertEqual(out["nasdaq_exchange_52w"]["daily_sample_size"],2450)
        for group in out["sections"].values():
            for key in group:
                self.assertEqual([p["sessions"] for p in out[key]["periods"]],[1,5,10,20,60])
        self.assertEqual(out["nasdaq_exchange_52w"]["periods"][-1]["avg_new_lows"],170)
    def test_stale_source_is_not_current(self):
        a,m,h,d=complete()
        a["data"].pop()
        sources={"ad_line.json":a,"market_breadth.json":m,"nh_nl.json":h}
        result=run(sources.__getitem__,d)
        self.assertEqual(result["status"],"unavailable")
        self.assertNotIn("all_us_ad",result)
    def test_inconsistent_source_date_rejected(self):
        a,m,h,d=complete()
        h["data"].pop()
        with self.assertRaises(ValueError):
            report_payload(a,m,h,d)
    def test_bad_nasdaq_sample_rejected(self):
        a,m,h,d=complete()
        h["data"][-1]["nasdaq_new_highs"]=2500
        with self.assertRaises(ValueError):
            report_payload(a,m,h,d)
    def test_source_failure_explicit(self):
        a,m,h,d=complete()
        def unavailable(path):
            raise TimeoutError("fixture timeout")
        result=run(unavailable,d)
        self.assertEqual(result["status"],"unavailable")
        self.assertEqual(result["target_trade_date"],d[-1])
        self.assertIn("timeout",result["error"])

if __name__=="__main__":
    unittest.main()
