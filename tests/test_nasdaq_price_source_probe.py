"""Offline invariants for Nasdaq research-only historical price probe."""
import datetime as dt
import unittest

from nasdaq_price_source_probe import choose_sample, session_coverage, AuditError


def record(ticker, kind="Common Stock"):
    return {"ticker": ticker, "name": "Example - " + kind,
            "test_issue": "N", "etf": "N"}


class PriceProbeTests(unittest.TestCase):
    def test_complete_311_sessions_supports_60_day_52w_calculation(self):
        start = dt.date(2025, 1, 1)
        sessions = [start + dt.timedelta(days=i) for i in range(311)]
        price = {d: 10.0 for d in sessions}
        status = session_coverage(price, sessions)
        self.assertEqual(len(status), 60)
        self.assertTrue(all(all(row[k] for k in ("priced", "ad", "ma50", "ma200", "hilo"))
                            for row in status))

    def test_missing_price_is_not_forward_filled(self):
        sessions = [dt.date(2025, 1, 1) + dt.timedelta(days=i) for i in range(311)]
        price = {d: 10.0 for d in sessions}
        del price[sessions[260]]
        status = session_coverage(price, sessions)
        self.assertFalse(status[9]["priced"])  # j=260 corresponds to 10th latest session
        self.assertFalse(status[10]["ad"])
        self.assertFalse(status[10]["hilo"])
        self.assertFalse(status[10]["ma50"])
        self.assertTrue(status[0]["ma50"])

    def test_too_short_calendar_is_rejected(self):
        sessions = [dt.date(2025, 1, 1) + dt.timedelta(days=i) for i in range(310)]
        with self.assertRaisesRegex(AuditError, "311"):
            session_coverage({}, sessions)

    def test_sample_keeps_removed_symbols_and_unresolved(self):
        first = dt.date(2026, 8, 27)
        last = dt.date(2026, 11, 19)
        rows = [
            ("AAPL", first, None, record("AAPL")),
            ("OLD", first, last, record("OLD")),
            ("UNKNOWN", first, None, record("UNKNOWN", "Holdings")),
            ("BETA", first, None, record("BETA")),
        ]
        sample = choose_sample(rows, first, last, 4)
        self.assertIn(("OLD", "FORMER_LISTED"), sample)
        self.assertIn(("UNKNOWN", "CURRENT_UNRESOLVED"), sample)
        self.assertEqual(len(sample), len(set(t for t, _ in sample)))


if __name__ == "__main__":
    unittest.main()
