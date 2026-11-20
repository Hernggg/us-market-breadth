"""No-network security and schema tests for EODData free-account API feasibility."""
import unittest

from research.eoddata.eoddata_api_probe import api_path,probe,summarize_json


class EoddataProbeTests(unittest.TestCase):
    def test_documented_endpoints_are_allowlisted(self):
        self.assertEqual(api_path("NCFI"),"/Quote/List/INDEX/NCFI")
        self.assertEqual(api_path("MALQ","Get"),"/Quote/Get/INDEX/MALQ")
        for item in ("../token","AAPL","NCFI?apiKey=leak"):
            with self.subTest(item=item),self.assertRaises(ValueError):
                api_path(item)
        with self.assertRaises(ValueError):
            api_path("NCFI","Write")

    def test_no_key_means_no_request(self):
        self.assertEqual(probe("NCFI",None)["status"],"NO_API_KEY_CONFIGURED")
        self.assertEqual(probe("MAHP","")["status"],"NO_API_KEY_CONFIGURED")

    def test_list_schema_retains_only_dates_and_counts(self):
        fixture=[
            {"TradeDate":"2026-11-19","Close":31.39,"Symbol":"NCFI"},
            {"TradeDate":"2026-11-20","Close":20.22,"Symbol":"NCFI"}
        ]
        out=summarize_json(fixture)
        self.assertEqual(out["observations"],2)
        self.assertEqual(out["distinct_sessions"],2)
        self.assertEqual(out["latest_observation_date"],"2026-11-20")
        self.assertNotIn("Close",str(out))
        self.assertNotIn("31.39",str(out))

    def test_nested_response(self):
        src={"data":{"prices":[{"Date":"2026-11-20","close":12.22}]}}
        out=summarize_json(src)
        self.assertEqual(out["observations"],1)
        self.assertEqual(out["earliest_observation_date"],"2026-11-20")
        self.assertEqual(out["json_shape"],"OBJECT")

    def test_missing_or_nonnumeric_unsupported_json(self):
        self.assertEqual(summarize_json({"error":"unauthorized"})["observations"],0)
        self.assertEqual(summarize_json({"data":"bad"})["observations"],0)
        self.assertEqual(summarize_json("raw")["json_shape"],"UNEXPECTED")


if __name__ == "__main__":
    unittest.main()
