"""Offline regression tests for the Nasdaq research-only candidate audit."""
import datetime as dt
import unittest

from nasdaq_comp_candidate import AuditError, audit, classification


class SecurityClassificationTests(unittest.TestCase):
    def item(self, name, etf="N", test_issue="N"):
        return {"name": name, "etf": etf, "test_issue": test_issue}

    def test_known_eligible_type(self):
        self.assertEqual(classification(self.item("Example - Class A Common Stock")), "LIKELY_ELIGIBLE_TYPE")
        self.assertEqual(classification(self.item("Example - American Depositary Shares")), "LIKELY_ELIGIBLE_TYPE")

    def test_etf_and_test_excluded(self):
        self.assertEqual(classification(self.item("Example Common Stock", "Y")), "EXCLUDED_ETF")
        self.assertEqual(classification(self.item("Example Common Stock", "N", "Y")), "EXCLUDED_TEST")

    def test_warrant_and_preferred_excluded(self):
        self.assertEqual(classification(self.item("Example - Warrants to purchase Common Stock")), "EXCLUDED_SECURITY_TYPE")
        self.assertEqual(classification(self.item("Example - Preferred Shares")), "EXCLUDED_SECURITY_TYPE")

    def test_unclear_type_not_silently_assumed(self):
        self.assertEqual(classification(self.item("Example Holdings")), "UNRESOLVED_TYPE")

    def test_spac_units_rights_and_notes_are_excluded(self):
        for name in ("Example Acquisition Corp. - Unit",
                     "Example Acquisition Corp. - Units",
                     "Example Acquisition Corp. - Right",
                     "Example Acquisition Corp. - Rights",
                     "Example Holdings - 6.75% Notes due 2028"):
            with self.subTest(name=name):
                self.assertEqual(classification(self.item(name)), "EXCLUDED_SECURITY_TYPE")

    def test_eligible_nonstandard_common_share_descriptions(self):
        for name in ("Example AG - Registered Shares",
                     "Example - Subordinate Voting Shares",
                     "Example - Class A Shares representing limited partner interests",
                     "Example - Non-Voting Shares"):
            with self.subTest(name=name):
                self.assertEqual(classification(self.item(name)), "LIKELY_ELIGIBLE_TYPE")

    def test_issuer_name_not_confused_with_type(self):
        self.assertEqual(
            classification(self.item("Rights Management Inc. - Common Stock")),
            "LIKELY_ELIGIBLE_TYPE"
        )


class HistoricalIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.calendar = [dt.date(2026, 8, 1) + dt.timedelta(days=i) for i in range(60)]
        self.meta = {"generated_at_utc": "2026-11-19T16:32:03Z"}
        self.rows = [
            (f"X{i:04d}", dt.date(2026, 7, 28), None,
             {"ticker": f"X{i:04d}", "name": "Example - Common Stock", "etf": "N", "test_issue": "N"})
            for i in range(1501)
        ]

    def test_research_report_cannot_be_published_as_composite(self):
        result = audit(self.calendar, self.rows, dt.date(2026, 7, 28), self.meta, "abc")
        self.assertFalse(result["eligible_for_us_market_publication"])
        self.assertEqual(result["sessions"], 60)
        self.assertEqual(result["daily"][-1]["likely_eligible_security_type"], 1501)
        self.assertEqual(result["daily"][-1]["new_directory_symbols"], 0)

    def test_archive_boundary_is_enforced(self):
        with self.assertRaisesRegex(AuditError, "cannot backfill"):
            audit(self.calendar, self.rows, dt.date(2026, 8, 2), self.meta, "abc")

    def test_overlap_refused(self):
        bad = self.rows + [self.rows[0]]
        with self.assertRaisesRegex(AuditError, "Overlapping"):
            audit(self.calendar, bad, dt.date(2026, 7, 28), self.meta, "abc")

    def test_stale_archive_refused(self):
        stale = {"generated_at_utc": "2026-08-01T00:00:00Z"}
        with self.assertRaisesRegex(AuditError, "predates"):
            audit(self.calendar, self.rows, dt.date(2026, 7, 28), stale, "abc")


if __name__ == "__main__":
    unittest.main()
