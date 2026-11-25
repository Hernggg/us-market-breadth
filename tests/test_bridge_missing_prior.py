"""Regression coverage for guarded bridge when a stock has no upstream prior close."""
import unittest
from bridge_latest_session import select_priceable_members


class PreviousDayGapBridgeTests(unittest.TestCase):
    def setUp(self):
        self.members = {"SNDK"} | {f"TICK{n:03d}" for n in range(502)}
        self.old_prices={s:100.0 for s in self.members if s!="SNDK"}
        self.old_prices["SPY"]=600.0
        self.baseline={"expected_members":"503","priced_members":"502"}

    def test_known_one_member_gap_is_audited_and_skipped_without_price_fabrication(self):
        needed, missing=select_priceable_members(self.members,self.old_prices,self.baseline)
        self.assertEqual(missing,["SNDK"])
        self.assertNotIn("SNDK",needed)
        self.assertEqual(len(needed),503)
        self.assertEqual(self.old_prices.get("SNDK"),None)
        self.assertIn("SPY",needed)

    def test_no_gap_uses_all_securities(self):
        full=dict(self.old_prices,SNDK=100.0)
        needed,missing=select_priceable_members(self.members,full,{"expected_members":"503","priced_members":"503"})
        self.assertFalse(missing)
        self.assertEqual(len(needed),504)

    def test_missing_spy_always_aborts(self):
        old=dict(self.old_prices);old.pop("SPY")
        with self.assertRaisesRegex(RuntimeError,"SPY benchmark"):
            select_priceable_members(self.members,old,self.baseline)

    def test_unexplained_missing_prior_aborts(self):
        prior=dict(self.old_prices)
        prior.pop("TICK000")
        with self.assertRaisesRegex(RuntimeError,"exceeds audited"):
            select_priceable_members(self.members,prior,self.baseline)

    def test_excessive_member_gaps_abort_even_if_audited(self):
        prior=dict(self.old_prices)
        prior.pop("TICK000")
        prior.pop("TICK001")
        with self.assertRaisesRegex(RuntimeError,"Too many"):
            select_priceable_members(self.members,prior,{"expected_members":"503","priced_members":"500"})


if __name__ == "__main__":
    unittest.main()
