"""Verify official Nasdaq industry index comparison is not mislabeled breadth."""
import datetime as dt
import unittest
from nasdaq_sector_rotation import NAMES, build_sector_report, AuditError

class NasdaqIndexRotationTests(unittest.TestCase):
    def source(self,n=65,missing=False):
        cols=["Date","Advances","Declines","Unchanged"]+[k.capitalize() for k in NAMES]
        data=[",".join(cols)]
        start=dt.date(2026,7,1)
        for i in range(n):
            day=start+dt.timedelta(days=i)
            levels=[str(100+i*(1+idx*.1)) for idx,k in enumerate(NAMES)]
            if missing and i==n-1:
                levels[NAMES.keys().__iter__().__length_hint__()-1]=""
            data.append(f"{day.month}/{day.day}/{day.year} 0:00:00,2000,2000,50,"+",".join(levels))
        return "\n".join(data)

    def test_five_windows_and_relative_return(self):
        rep=build_sector_report(self.source(),dt.date(2026,9,30))
        self.assertFalse(rep["eligible_for_us_market_comp_breadth_publication"])
        self.assertEqual([x["sessions"] for x in rep["periods"]],[1,5,10,20,60])
        self.assertEqual(len(rep["periods"][-1]["indices"]),len(NAMES))
        comp=next(x for x in rep["periods"][0]["indices"] if x["index_id"]=="composite")
        self.assertAlmostEqual(comp["relative_to_composite_percentage_points"],0.0)

    def test_short_source_fails(self):
        with self.assertRaisesRegex(AuditError,"at least 61"):
            build_sector_report(self.source(n=60),dt.date(2026,9,30))

    def test_missing_sector_level_refused(self):
        raw=self.source()
        lines=raw.splitlines()
        split=lines[-1].split(",")
        split[-1]=""
        lines[-1]=",".join(split)
        with self.assertRaisesRegex(AuditError,"Missing computer index level"):
            build_sector_report("\n".join(lines),dt.date(2026,9,30))


if __name__=="__main__":
    unittest.main()
