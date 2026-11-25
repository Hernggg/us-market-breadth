"""No-network unit tests for the one-day, no-redistribution price feasibility probe."""
import datetime as dt
import unittest
from nasdaq_bulk_price_probe import candidate_tickers, match_counts, AuditError


class BulkProbeTests(unittest.TestCase):
    def test_candidate_membership_is_point_in_time(self):
        date=dt.date(2026,11,19)
        rows=[
            ("AAA",date,None,{"ticker":"AAA","name":"Example - Common Stock","etf":"N","test_issue":"N"}),
            ("OLD",dt.date(2026,8,1),date,{"ticker":"OLD","name":"Old - Common Stock","etf":"N","test_issue":"N"}),
            ("ETF",date,None,{"ticker":"ETF","name":"ETF - Exchange Traded Fund","etf":"Y","test_issue":"N"}),
            ("UNIT",date,None,{"ticker":"UNIT","name":"Example - Unit","etf":"N","test_issue":"N"}),
            ("UNRES",date,None,{"ticker":"UNRES","name":"Example - Depositary Shares","etf":"N","test_issue":"N"}),
        ]
        # Method enforces plausible directory size: fill with synthetic symbols.
        for k in range(2500):
            rows.append((f"X{k:04}",date,None,{"ticker":"X","name":"Example - Common Stock","etf":"N","test_issue":"N"}))
        eligible, unresolved=candidate_tickers(rows,date)
        self.assertIn("AAA",eligible)
        self.assertNotIn("OLD",eligible)
        self.assertNotIn("ETF",eligible)
        self.assertNotIn("UNIT",eligible)
        self.assertIn("UNRES",unresolved)

    def test_counts_no_prices_or_names_leak(self):
        audit=match_counts({"AAA","BRK.B","NOQUOTE"},{"UNRES"},[
            ("AAA",100.3,500),("BRK-B",200,400),("UNRES",12.1,100)
        ])
        self.assertEqual(audit["candidate_symbols_with_bulk_daily_quote"],2)
        self.assertEqual(audit["candidate_symbols_missing_bulk_daily_quote"],1)
        self.assertEqual(audit["unresolved_symbols_with_quote"],1)
        self.assertNotIn("AAA",str(audit))
        self.assertNotIn("100.3",str(audit))

    def test_duplicate_keys_fail_closed(self):
        with self.assertRaisesRegex(AuditError,"duplicate"):
            match_counts({"AAA"},set(),[("AAA",1,0),("AAA",2,0)])

    def test_bad_quote_counts_invalid(self):
        audit=match_counts({"AAA","BBB"},set(),[("AAA",None,1),("BBB",2,-1)])
        self.assertEqual(audit["invalid_price_or_volume_fields"],2)

    def test_overlap_classification_refused(self):
        with self.assertRaisesRegex(AuditError,"overlap"):
            match_counts({"X"},{"X"},[])


if __name__=="__main__":
    unittest.main()
