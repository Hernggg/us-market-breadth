"""Strict offline tests for Nasdaq listing sample rolling breadth engine."""
from __future__ import annotations
import datetime as dt
import unittest
from nasdaq_listing_breadth_lab import (
    stat_day, summarize, parse_adjusted_ohlc, choose_breadth_cohort, AuditError
)


class DailyBreadthTests(unittest.TestCase):
    def setUp(self):
        start=dt.date(2025,1,1)
        self.sessions=[start+dt.timedelta(days=i) for i in range(312)]

    def bars(self, old, new, oldhigh=None, oldlow=None, newhigh=None, newlow=None):
        out={}
        for day in self.sessions[:-1]:
            out[day]={"close":float(old),"high":float(oldhigh or old+1),"low":float(oldlow or old-1)}
        out[self.sessions[-1]]={"close":float(new),"high":float(newhigh or new+1),"low":float(newlow or new-1)}
        return out

    def test_ad_ma_and_actual_intraday_high_low(self):
        first=self.bars(100,105,oldhigh=101,oldlow=99,newhigh=108,newlow=103)
        second=self.bars(200,190,oldhigh=201,oldlow=198,newhigh=191,newlow=180)
        day=stat_day(self.sessions[-1],self.sessions,{"UP":first,"DOWN":second},{"UP","DOWN"})
        self.assertEqual((day["advances"],day["declines"],day["unchanged"]),(1,1,0))
        self.assertEqual(day["ad_eligible"],2)
        self.assertEqual((day["ma50_above"],day["ma200_above"]),(1,1))
        self.assertEqual((day["new_highs"],day["new_lows"]),(1,1))
        self.assertEqual((day["ma50_pct"],day["ma200_pct"]),(50.0,50.0))
        self.assertEqual(day["ad_ratio"],1)

    def test_missing_daily_bar_and_short_ipo_history_are_not_filled(self):
        growing={d:{"close":float(i+11),"high":float(i+12),"low":float(i+10)}
                 for i,d in enumerate(self.sessions[-10:])}
        existing=self.bars(100,100)
        observed=stat_day(self.sessions[-1],self.sessions,{
            "OLD":existing, "IPO":growing, "MISSING":{},
        },{"OLD","IPO","MISSING"})
        self.assertEqual(observed["expected_sample_members"],3)
        self.assertEqual(observed["priced_members"],2)
        self.assertEqual(observed["missing_today_prices"],1)
        self.assertEqual(observed["ad_eligible"],2)
        self.assertEqual(observed["ma50_eligible"],1)
        self.assertEqual(observed["ma200_eligible"],1)
        self.assertEqual(observed["hilo_eligible"],1)
        self.assertEqual(observed["unchanged"],1)
        self.assertEqual(observed["advances"],1)

    def test_no_false_breakout_from_equal_prior_high(self):
        unchanged=self.bars(100,100,oldhigh=104,oldlow=96,newhigh=104,newlow=96)
        obs=stat_day(self.sessions[-1],self.sessions,{"S":unchanged},{"S"})
        self.assertEqual(obs["new_highs"],0)
        self.assertEqual(obs["new_lows"],0)

    def test_52week_uses_high_low_not_close(self):
        outside=self.bars(100,100,oldhigh=101,oldlow=99,newhigh=110,newlow=98)
        obs=stat_day(self.sessions[-1],self.sessions,{"S":outside},{"S"})
        self.assertEqual(obs["advances"],0)
        self.assertEqual(obs["unchanged"],1)
        self.assertEqual(obs["new_highs"],1)
        self.assertEqual(obs["new_lows"],1)

    def test_calendar_requires_251_preceding_sessions(self):
        with self.assertRaisesRegex(AuditError,"251 earlier"):
            stat_day(self.sessions[250],self.sessions,{},set())

    def test_ohlc_adjustment_by_adjusted_close_ratio(self):
        from zoneinfo import ZoneInfo
        epoch=int(dt.datetime(2026,11,19,16,tzinfo=ZoneInfo("America/New_York")).timestamp())
        sample={"timestamp":[epoch],"indicators":{
            "quote":[{"close":[100.0],"high":[110.0],"low":[90.0]}],
            "adjclose":[{"adjclose":[50.0]}]
        }}
        parsed=parse_adjusted_ohlc(sample)
        row=parsed[dt.date(2026,11,19)]
        self.assertEqual(row,{"close":50.0,"high":55.0,"low":45.0})

    def test_incomplete_ohlc_keeps_close_without_fabricating_extremes(self):
        from zoneinfo import ZoneInfo
        epoch=int(dt.datetime(2026,11,19,16,tzinfo=ZoneInfo("America/New_York")).timestamp())
        sample={"timestamp":[epoch],"indicators":{
            "quote":[{"close":[100.0],"high":[None],"low":[90.0]}],
            "adjclose":[{"adjclose":[50.0]}]
        }}
        self.assertEqual(parse_adjusted_ohlc(sample)[dt.date(2026,11,19)],
                         {"close":50.0,"high":None,"low":None})


class WindowBreadthTests(unittest.TestCase):
    def test_average_of_daily_percentages_not_pooled_member_weights(self):
        baseline={
            "expected_sample_members":2,"priced_members":2,"ad_eligible":2,
            "advances":1,"declines":1,"unchanged":0,"ma50_eligible":2,"ma50_above":1,
            "ma200_eligible":2,"ma200_above":1,"hilo_eligible":2,
            "new_highs":0,"new_lows":0,"ma50_pct":50.0,"ma200_pct":50.0
        }
        rows=[]
        start=dt.date(2026,8,1)
        for i in range(60):
            row=dict(baseline,date=(start+dt.timedelta(days=i)).isoformat())
            if i==0:
                row.update(ma50_eligible=1,ma50_above=1,ma50_pct=100.0)
            rows.append(row)
        stats=summarize(rows)
        self.assertEqual([x["sessions"] for x in stats],[1,5,10,20,60])
        self.assertEqual(stats[-1]["daily_averages"]["mean_50dma_pct"],round((100+59*50)/60,4))
        self.assertEqual(stats[-1]["window_total_A_over_D"],1.0)
        self.assertEqual(stats[-1]["priced_member_day_coverage"],1.0)
        self.assertEqual(stats[-1]["daily_averages"]["new_highs"],0)

    def test_zero_eligible_denominator_stays_null(self):
        rows=[]
        start=dt.date(2026,8,1)
        for i in range(60):
            rows.append({
                "date":(start+dt.timedelta(days=i)).isoformat(),
                "expected_sample_members":1,"priced_members":0,
                "ad_eligible":0,"advances":0,"declines":0,"unchanged":0,
                "ma50_eligible":0,"ma50_above":0,"ma200_eligible":0,"ma200_above":0,
                "hilo_eligible":0,"new_highs":0,"new_lows":0,
                "ma50_pct":None,"ma200_pct":None
            })
        stats=summarize(rows)
        self.assertIsNone(stats[0]["window_total_A_over_D"])
        self.assertIsNone(stats[0]["daily_averages"]["mean_50dma_pct"])
        self.assertEqual(stats[0]["hilo_member_day_coverage"],0)
        self.assertEqual(stats[0]["priced_member_day_coverage"],0)


class CohortSelectionTests(unittest.TestCase):
    def test_diverse_cohort_and_no_duplicates(self):
        first=dt.date(2026,8,27)
        last=dt.date(2026,11,19)
        def r(t,start,end=None):
            return (t,start,end,{"ticker":t,"name":"Example - Common Stock",
                                 "etf":"N","test_issue":"N"})
        fixed=["AAPL","MSFT","NVDA","AMZN","GOOGL","META","TSLA","AMD"]
        rows=[r(t,first) for t in fixed]
        rows.extend(r("FORMER"+str(i),first,last) for i in range(6))
        rows.extend(r("NEW"+str(i),first+dt.timedelta(days=8)) for i in range(6))
        rows.extend(r("CURR"+str(i),first) for i in range(50))
        cohort=choose_breadth_cohort(rows,first,last,24)
        categories=dict((t,b) for t,b in cohort)
        self.assertEqual(len(cohort),24)
        self.assertEqual(len(set(categories)),24)
        self.assertEqual(sum(b=="FORMER_LISTED" for t,b in cohort),2)
        self.assertEqual(sum(b=="NEWLY_LISTED" for t,b in cohort),2)
        self.assertEqual(sum(b=="LIQUID_CONTROL" for t,b in cohort),8)
        self.assertGreaterEqual(sum(b=="CURRENT" for t,b in cohort),12)
        self.assertEqual(cohort,choose_breadth_cohort(list(reversed(rows)),first,last,24))

    def test_no_unresolved_in_selected_cohort(self):
        first=dt.date(2026,8,27)
        last=dt.date(2026,11,19)
        rows=[("BAD",first,None,{"ticker":"BAD","name":"Example - Depositary Shares","etf":"N","test_issue":"N"})]
        rows.extend((f"VALID{i}",first,None,{"ticker":f"VALID{i}",
             "name":"Example - Common Stock","etf":"N","test_issue":"N"}) for i in range(30))
        chosen=choose_breadth_cohort(rows,first,last,18)
        self.assertNotIn("BAD",[t for t,_ in chosen])


if __name__=="__main__":
    unittest.main()
