import random
import unittest
from dataclasses import replace
from decimal import Decimal as D
from src.themescope.domain import Role
from src.themescope.research.primary import daily_eligibility,priority,qualifies,Eligibility
from src.themescope.research.exports import Qualification as Q,exports
from src.themescope.themes.calculations import bar_map
from test_vnext_calculations import SESSIONS,bar


class PrimaryTests(unittest.TestCase):
    def test_liquidity_exact_three_boundaries_and_raw_units(self):
        target=SESSIONS[9]
        data=bar_map(bar('A',s,5,2000000) for s in SESSIONS[:10])
        ok=daily_eligibility(data,'A',SESSIONS,target)
        self.assertEqual((ok.eligible,ok.close,ok.turnover),(True,D(5),D(10000000)))
        data['A',target]=replace(data['A',target],close=D('4.9999'))
        self.assertFalse(daily_eligibility(data,'A',SESSIONS,target).eligible)
        data=bar_map(bar('A',s,100,500000) for s in SESSIONS[:10])
        exact=daily_eligibility(data,'A',SESSIONS,target)
        self.assertFalse(exact.eligible)
        self.assertEqual(exact.reasons,('average_volume_not_above_floor',))
        data['A',target]=replace(data['A',target],volume=D(500001),adjusted_close=D(1))
        self.assertTrue(daily_eligibility(data,'A',SESSIONS,target).eligible)
        data=bar_map(bar('A',s,5,2000000) for s in SESSIONS[:10])
        data['A',target]=replace(data['A',target],volume=D(1999999))
        self.assertEqual(daily_eligibility(data,'A',SESSIONS,target).reasons,('turnover_below_floor',))

    def test_ten_latest_completed_regular_sessions_no_skipping_or_future(self):
        data=bar_map(bar('A',s,10,1000000) for s in SESSIONS[:12])
        data['A',SESSIONS[0]]=bar('A',SESSIONS[0],10,1)
        data['A',SESSIONS[11]]=bar('A',SESSIONS[11],10,999999999)
        self.assertEqual(daily_eligibility(data,'A',SESSIONS,SESSIONS[10]).average_volume,1000000)
        for mutation in ('missing','incomplete','extended'):
            modified=dict(data)
            if mutation=='missing':del modified['A',SESSIONS[5]]
            else:modified['A',SESSIONS[5]]=replace(modified['A',SESSIONS[5]],**({'completed':False} if mutation=='incomplete' else {'regular_session':False}))
            self.assertFalse(daily_eligibility(modified,'A',SESSIONS,SESSIONS[10]).available)
        self.assertFalse(daily_eligibility(data,'A',SESSIONS,SESSIONS[8]).available)

    def test_primary_score_trend_direction_boundaries_and_one_session_exception(self):
        for market in ('Long bias','Selective long'):
            self.assertEqual(priority(market,50,'Mixed',{}),'Primary long')
            self.assertEqual(priority(market,D('49.999'),'Bullish',{}),'Watch')
            self.assertEqual(priority(market,20,'Bullish',{'newly_bullish':True}),'Primary long')
            self.assertEqual(priority(market,20,'Bullish',{'newly_bullish':False}),'Watch')
            self.assertEqual(priority(market,100,'Bearish',{}),'Watch')
        for market in ('Short bias','Selective short'):
            self.assertEqual(priority(market,D('49.999'),'Mixed',{}),'Primary short')
            self.assertEqual(priority(market,50,'Bearish',{}),'Watch')
            self.assertEqual(priority(market,80,'Bearish',{'newly_bearish':True}),'Primary short')
        for market in ('Neutral','Unclassified',None):
            self.assertEqual(priority(market,100,'Bullish',{'newly_bullish':True}),'Watch')
        for score in (None,'NaN',-1,101):self.assertEqual(priority('Long bias',score,'Bullish',{'newly_bullish':True}),'Watch')
        self.assertEqual(priority('Long bias',100,'Unavailable',{}),'Watch')
        good=Eligibility(True,True,10,1000000,10000000,())
        for w in (None,D(0),'NaN'):self.assertFalse(qualifies('Primary long',w,good))
        self.assertTrue(qualifies('Primary long',D('.000001'),good))
        self.assertTrue(qualifies('Primary short',D('-.000001'),good))
        self.assertFalse(qualifies('Primary long',D(-1),good))
        self.assertFalse(qualifies('Primary short',D(1),good))
        self.assertFalse(qualifies('Primary long',D(1),replace(good,eligible=False)))

    def test_multi_theme_all_tiebreaks_long_short_and_order_independence(self):
        mapping={s:{'status':'verified','symbol':'NASDAQ:'+s} for s in 'ABC'}
        for direction,sign in [('long',D(1)),('short',D(-1))]:
            rows=[Q('A','alpha',Role.CORE,sign),Q('A','beta',Role.ENABLER,10*sign),
                  Q('B','alpha',Role.CORE,sign),Q('B','beta',Role.CORE,2*sign),
                  Q('C','alpha',Role.CORE,sign),Q('C','beta',Role.CORE,sign)]
            expected=exports(rows,direction,mapping)
            self.assertEqual({k:v['assigned_section'] for k,v in expected['assignments'].items()}, {'A':'alpha','B':'beta','C':'alpha'})
            for s in 'ABC':self.assertEqual(expected['combined'].count('NASDAQ:'+s),1)
            for theme in ('alpha','beta'):
                for s in 'ABC':self.assertIn('NASDAQ:'+s,expected['individual'][theme])
            for seed in range(10):
                random.Random(seed).shuffle(rows)
                self.assertEqual(exports(rows,direction,mapping),expected)

    def test_export_errors_no_silent_symbol_guessing_or_20_stock_cap(self):
        rows=[Q('S'+str(i),'alpha',Role.CORE,D(1)) for i in range(25)]
        mapping={r.ticker:{'status':'verified','symbol':'NASDAQ:'+r.ticker} for r in rows}
        self.assertEqual(len(exports(rows,'long',mapping)['assignments']),25)
        with self.assertRaises(ValueError):exports(rows+[rows[0]],'long',mapping)
        with self.assertRaisesRegex(ValueError,'unresolved'):exports(rows,'long',{})
        with self.assertRaises(ValueError):exports([replace(rows[0],role=Role.RELATED)],'long',mapping)
        with self.assertRaises(ValueError):exports([replace(rows[0],w=D(0))],'long',mapping)
        with self.assertRaises(ValueError):exports([replace(rows[0],theme_id='../unsafe')],'long',mapping)
        self.assertEqual(exports([],None,{}),{'individual':{},'combined':'','assignments':{}})

    def test_theme_priority_matches_unchanged_legacy_policy(self):
        from src.themescope.research_policy import theme_priority
        for direction in ('Long bias','Selective long','Short bias','Selective short','Neutral','Unclassified'):
            for score in (0,49.99,50,100,None):
                for trend in ('Bullish','Mixed','Bearish','Unavailable'):
                    for transition in (None,'newly_bullish','newly_bearish'):
                        flags={'newly_bullish':transition=='newly_bullish','newly_bearish':transition=='newly_bearish'}
                        self.assertEqual(priority(direction,score,trend,flags),theme_priority(direction,score,trend,transition)['label'])
