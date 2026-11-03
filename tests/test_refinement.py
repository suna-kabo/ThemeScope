"""Frozen policies, weighted browsing, and grouped research export invariants."""
import copy
import json
from pathlib import Path
import re
import unittest
from test_research_policy import snapshot
from src.themescope.research_policy import decision_path,market_rule
from src.themescope.relative_performance import weighted_excess
from src.themescope.daily_lists import build,primary_research,earnings_window
from src.themescope.tradingview import section_heading


def returns(a,b):return {'returns':{'21':{'value':a},'63':{'value':b}}}

def stock(ticker,a=.3,b=.4,symbol=None):return {'ticker':ticker,'tradingview_symbol':symbol or 'NASDAQ:'+ticker,**returns(a,b)}

class RefinementTests(unittest.TestCase):
    def test_contributing_inputs_only_and_missing_required_evidence(self):
        for price in ('Bullish','Bearish'):
            for breadth in ('Positive','Negative','Mixed',None):
                path=decision_path(price,price,breadth)
                self.assertEqual([r['label'] for r in path],['SPY price','QQQ price','Price consensus rule'])
                self.assertNotIn('IWM',json.dumps(path));self.assertNotIn('breadth',json.dumps(path).lower())
        self.assertEqual([r['label'] for r in decision_path('Bullish','Mixed','Positive')],['SPY price','QQQ price','SPY/QQQ Breadth Consensus','Matched rule'])
        self.assertEqual(decision_path(None,'Mixed','Positive'),[{'label':'SPY price','value':'Unavailable','kind':'missing'}])
        self.assertEqual(decision_path('Bearish','Mixed',None)[2]['kind'],'missing')
    def test_weighted_classification_not_both_horizons_and_zero_cancellation(self):
        anchor=returns(.1,.2)
        for a,b,classification,weighted in [(.12,.19,'Outperforming',.8),(.11,.17,'Underperforming',-.6),(.12,.17,'Flat',0)]:
            result=weighted_excess(returns(a,b),anchor)
            self.assertEqual(result['weighted_vs_etf'],classification);self.assertAlmostEqual(result['weighted_excess_pp'],weighted)
        for key,period in [('stock','21'),('stock','63'),('etf','21'),('etf','63')]:
            inputs={'stock':returns(.12,.17),'etf':returns(.1,.2)};inputs[key]['returns'][period]['value']=None
            result=weighted_excess(inputs['stock'],inputs['etf']);self.assertEqual(result['weighted_vs_etf'],'Unavailable');self.assertIsNone(result['weighted_excess_pp'])
        # Same stock, different selected anchors, opposite classifications.
        self.assertEqual(weighted_excess(returns(.2,.3),returns(.1,.2))['weighted_vs_etf'],'Outperforming')
        self.assertEqual(weighted_excess(returns(.2,.3),returns(.3,.4))['weighted_vs_etf'],'Underperforming')
    def test_earnings_strict_dates_and_original_facts_retained(self):
        dates=['2026-11-02','2026-11-03','2026-11-09','2026-11-01','20261102','2026-02-30',None]
        candidates=[dict(stock(str(i)),earnings_date=value,primary_contexts=[]) for i,value in enumerate(dates)]
        result=earnings_window(candidates,'2026-11-02')
        self.assertEqual([r['timing_label'] for r in result['upcoming']],['Today','In 1 day','In 7 days'])
        self.assertEqual([r['expected_date'] for r in result['unknown']],dates[3:])

    def test_grouped_sections_reserved_anchors_overlap_and_ordinary_files(self):
        s=snapshot();t=s['themes'][0];t.update(anchor='A',tradingview_symbol='AMEX:A',theme_score=80,research_priority={'label':'Primary long','category':'primary','side':'long','group':0})
        t['selected']=[stock('B',symbol='AMEX:B'),stock('SHARED'),stock('UNQUALIFIED',-.1,-.1)]
        second=copy.deepcopy(t);second.update(id='b',name='Beta, Fund',anchor='B',tradingview_symbol='AMEX:B');second['selected']=[stock('SHARED')]
        third=copy.deepcopy(t);third.update(id='c',name='ETF only',anchor='C',tradingview_symbol='AMEX:C');third['selected']=[]
        s['themes']=[t,second,third]
        config={'schema_version':1,'instrument_limit':1000,'groups':[{'id':'all','name':'All','theme_ids':['a','b','c']}]}
        before=copy.deepcopy(s['themes']);files=build(s,config);research=s['daily_primary_research'];tokens=files[research['combined_file']].strip().split(',')
        self.assertEqual(tokens,[section_heading(t),'AMEX:A','NASDAQ:SHARED',section_heading(second),'AMEX:B',section_heading(third),'AMEX:C'])
        self.assertEqual(len(research['sections']),3)
        item=next(r for r in s['export_manifest'] if r['role']=='daily_primary_research')
        self.assertEqual((item['section_count'],item['instrument_count']),(3,4))
        for old,new in zip(before,s['themes']):
            self.assertEqual([r['ticker'] for r in old['selected']],[r['ticker'] for r in new['selected']])
            ordinary=next(r for r in s['export_manifest'] if r['role']=='individual_research' and r['theme_id']==new['id'])
            self.assertEqual(files[ordinary['file']].strip().split(','),[old['tradingview_symbol']]+[r['tradingview_symbol'] for r in old['selected']])
        self.assertIn('NASDAQ:UNQUALIFIED',files['tradingview_configured_stocks.txt'])
        self.assertEqual(sum(r['symbol']=='NASDAQ:SHARED' for r in research['relationships']),2)
        self.assertEqual(tokens.count('NASDAQ:SHARED'),1)
        for i,token in enumerate(tokens):
            if token.startswith('###'):self.assertTrue(tokens[i+1].startswith('AMEX:'))
        # Zero Primary does not create an importable prose file or stale link.
        s['market_classification']['direction']='Neutral';new_files,manifest=primary_research(s,1000)
        self.assertEqual(new_files,{});self.assertEqual(manifest,[]);self.assertEqual(s['daily_primary_research']['sections'],[])

if __name__=='__main__':unittest.main()
