"""Offline verification for full-universe DuckDB rolling-breadth batch engine."""
from __future__ import annotations
import datetime as dt
import unittest

from nasdaq_bulk_breadth_engine import (
    create_synthetic_fixture, calculate_daily, aggregate, verify_input,
    InvalidMarketData
)
from nasdaq_listing_breadth_lab import stat_day


class BulkBreadthEngineTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.con=duckdb.connect(":memory:")
        create_synthetic_fixture(self.con, 120)

    def tearDown(self):
        self.con.close()

    def test_full_60_session_series_and_five_windows(self):
        daily,window=aggregate(calculate_daily(self.con))
        self.assertEqual(len(daily),60)
        self.assertEqual([w["sessions"] for w in window],[1,5,10,20,60])
        self.assertEqual([x["session_id"] for x in daily],list(range(251,311)))
        self.assertEqual(daily[-1]["expected_members"],
                         self.con.execute("SELECT COUNT(*) FROM members WHERE session_id=310").fetchone()[0])
        self.assertGreater(window[-1]["ma200_memberday_coverage"],0)
        self.assertLessEqual(window[-1]["ma200_memberday_coverage"],1)
        self.assertFalse(any(x["advances"]+x["declines"]+x["unchanged"] != x["ad_eligible"]
                             for x in daily))

    def test_missing_candle_does_not_disguise_as_200day_history(self):
        daily,_=aggregate(calculate_daily(self.con))
        before=next(x for x in daily if x["session_id"]==299)
        gap=next(x for x in daily if x["session_id"]==300)
        after=next(x for x in daily if x["session_id"]==301)
        self.assertLess(gap["priced_members"],gap["expected_members"])
        # Member security_id S000103 loses its 200DMA eligibility
        # even on 301, despite that later date having a price again.
        self.assertLess(after["ma200_eligible"],after["expected_members"])
        self.assertLess(after["hilo_eligible"],after["expected_members"])
        self.assertLessEqual(gap["ad_eligible"],gap["priced_members"])

    def test_matches_existing_python_reference_for_one_security(self):
        self.con.execute("DELETE FROM members WHERE security_id!='S000001'")
        raw=self.con.execute("""SELECT c.trade_date, p.adj_close,p.adj_high,p.adj_low
            FROM calendar c LEFT JOIN prices p ON p.security_id='S000001'
            AND p.session_id=c.session_id ORDER BY c.session_id""").fetchall()
        days=[r[0] for r in raw]
        prices={row[0]:{"close":row[1],"high":row[2],"low":row[3]} for row in raw
                if row[1] is not None}
        ref=stat_day(days[-1],days,{"S000001":prices},{"S000001"})
        daily,_=aggregate(calculate_daily(self.con))
        last=daily[-1]
        for attr in ("advances","declines","unchanged","ad_eligible","ma50_eligible",
                     "ma50_above","ma200_eligible","ma200_above","hilo_eligible","new_highs","new_lows"):
            self.assertEqual(last[attr],ref[attr],attr)

    def test_duplicate_price_row_fails_closed(self):
        self.con.execute("INSERT INTO prices SELECT * FROM prices LIMIT 1")
        with self.assertRaisesRegex(InvalidMarketData,"Duplicated price"):
            verify_input(self.con)

    def test_duplicate_pit_membership_fails_closed(self):
        self.con.execute("INSERT INTO members SELECT * FROM members LIMIT 1")
        with self.assertRaisesRegex(InvalidMarketData,"Duplicated member"):
            verify_input(self.con)

    def test_invalid_high_low_fails_closed(self):
        self.con.execute("UPDATE prices SET adj_high=-1 WHERE security_id='S000001' AND session_id=310")
        with self.assertRaisesRegex(InvalidMarketData,"impossible adjusted OHLC"):
            verify_input(self.con)

    def test_missing_membership_date_fails_closed(self):
        self.con.execute("DELETE FROM members WHERE session_id=275")
        with self.assertRaisesRegex(InvalidMarketData,"60 member-universe dates"):
            verify_input(self.con)


if __name__=="__main__":
    unittest.main()
