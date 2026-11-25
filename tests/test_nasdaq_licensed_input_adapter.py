"""Offline licensed-input Parquet adapter tests; use synthetic fixture only."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from nasdaq_bulk_breadth_engine import (
    create_synthetic_fixture, calculate_daily, aggregate, InvalidMarketData
)
from nasdaq_licensed_input_adapter import (
    require_rights, import_authorized_parquet
)


class AuthorizedParquetAdapterTests(unittest.TestCase):
    def setUp(self):
        import duckdb
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.original=duckdb.connect(":memory:")
        create_synthetic_fixture(self.original, 120)
        for name in ("calendar","members","prices"):
            p=self.root/(name+".parquet")
            if name=="calendar":
                sql="SELECT trade_date FROM calendar"
            else:
                sql=f"SELECT t.security_id,c.trade_date" + (
                    ",t.adj_close,t.adj_high,t.adj_low" if name=="prices" else ""
                )+f" FROM {name} t JOIN calendar c USING(session_id)"
            self.original.execute(
                f"COPY ({sql}) TO '{p.as_posix()}' (FORMAT PARQUET)"
            )
        self.imported=duckdb.connect(":memory:")

    def tearDown(self):
        self.original.close()
        self.imported.close()
        self.tmp.cleanup()

    def files(self):
        return tuple(self.root/(name+".parquet") for name in ("calendar","members","prices"))

    def test_requires_both_membership_and_price_entitlements(self):
        for membership, price in ((False,False),(True,False),(False,True)):
            with self.subTest(membership=membership,price=price):
                with self.assertRaisesRegex(InvalidMarketData,"permissions required"):
                    require_rights(membership,price)

    def test_no_data_sources_accessed_without_rights(self):
        with self.assertRaisesRegex(InvalidMarketData,"permissions required"):
            import_authorized_parquet(self.imported,*self.files())
        self.assertEqual(self.imported.execute("SELECT count(*) FROM duckdb_tables()").fetchone()[0],0)

    def test_private_parquet_roundtrip_matches_reference(self):
        report=import_authorized_parquet(
            self.imported,*self.files(), membership_rights=True,price_rights=True)
        expected_daily,expected_windows=aggregate(calculate_daily(self.original))
        actual_daily,actual_windows=aggregate(calculate_daily(self.imported))
        self.assertEqual(expected_daily,actual_daily)
        self.assertEqual(expected_windows,actual_windows)
        self.assertEqual(report["calendar_days"],311)
        self.assertGreater(report["private_price_rows"],30000)

    def test_out_of_calendar_price_rejected(self):
        self.original.execute("""INSERT INTO prices
            VALUES ('S000005',400,50,50.5,49.5)""")
        extra=self.root/"prices_with_extra.parquet"
        self.original.execute(
            f"COPY (SELECT p.security_id, COALESCE(c.trade_date, DATE '2027-01-01') trade_date,"
            f" p.adj_close,p.adj_high,p.adj_low FROM prices p"
            f" LEFT JOIN calendar c USING(session_id)) TO '{extra.as_posix()}' (FORMAT PARQUET)"
        )
        calendar,members,_=self.files()
        with self.assertRaisesRegex(InvalidMarketData,"outside the 311-day calendar"):
            import_authorized_parquet(self.imported,calendar,members,extra,
                                      membership_rights=True,price_rights=True)

    def test_source_must_be_local_parquet(self):
        calendar,members,prices=self.files()
        with self.assertRaisesRegex(InvalidMarketData,"existing local"):
            import_authorized_parquet(self.imported,calendar,members,
                  self.root/"missing.parquet",membership_rights=True,price_rights=True)


if __name__=="__main__":
    unittest.main()
