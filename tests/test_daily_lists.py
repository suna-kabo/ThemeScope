import copy
import unittest
import json
from pathlib import Path
from src.themescope.daily_lists import build, pack_sections, flat_chunks, earnings_window, rs_state


def stock(ticker, a=.02, b=-.01, earnings=None):
    return {'ticker':ticker,'tradingview_symbol':'NYSE:'+ticker,'metric_status':'available','earnings_date':earnings,'market_cap_usd':2e9,'returns':{'21':{'value':.1},'63':{'value':.2}},'excess_returns':{'21':{'value':a},'63':{'value':b}}}

def theme(id, members, category='primary'):
    return {'id':id,'name':id,'anchor':id.upper(),'tradingview_symbol':'AMEX:'+id.upper(),'research_priority':{'category':category},'returns':{'21':{'value':.08},'63':{'value':.21}},'selected':members}

class DailyListTests(unittest.TestCase):
    def snapshot(self, themes):return {'session_date':'2026-12-29','themes':themes,'manual_csv_audit':{}}
    def config(self, themes, limit=1000):return {'schema_version':1,'instrument_limit':limit,'groups':[{'id':'test','name':'Test','theme_ids':[t['id'] for t in themes]}]}
    def test_group_validation_and_boundary_splitting(self):
        themes=[theme('a',[stock('A')]),theme('b',[stock('B')]),theme('c',[])]
        chunks=pack_sections(themes,3)
        self.assertEqual([c[1] for c in chunks],[2,3])
        self.assertEqual(chunks[0][0],['###a (A)','AMEX:A','NYSE:A'])
        self.assertEqual(chunks[1][0][-2:],['###c (C)','AMEX:C'])
        with self.assertRaisesRegex(ValueError,'cannot be split'):pack_sections(themes,1)
        c=self.config(themes);c['groups'][0]['theme_ids'].append('a')
        with self.assertRaisesRegex(ValueError,'exactly once'):build(self.snapshot(themes),c)
        self.assertEqual([n for _,n in flat_chunks(['a','b','c'],2)],[2,1])
    def test_dedup_primary_context_units_and_no_mutation_of_rules(self):
        one=stock('SHARED',.02,-.01);two=stock('SHARED',-.03,.04)
        themes=[theme('one',[one,stock('MISS')]),theme('two',[two]),theme('secondary',[stock('ONLY_SECONDARY')],'secondary'),theme('guarded',[stock('GUARDED')],'observation')]
        themes[0]['selected'][1]['metric_status']='unavailable';themes[0]['selected'][1]['returns']={'21':{'value':None},'63':{'value':None}}
        original=copy.deepcopy([t['research_priority'] for t in themes]);s=self.snapshot(themes);files=build(s,self.config(themes))
        self.assertEqual([t['research_priority'] for t in themes],original)
        self.assertEqual(len(s['daily_primary']['candidates']),2)
        shared=next(r for r in s['daily_primary']['candidates'] if r['ticker']=='SHARED')
        self.assertEqual([c['excess21_pp'] for c in shared['primary_contexts']],[2,-3])
        self.assertEqual([c['excess63_pp'] for c in shared['primary_contexts']],[-1,4])
        data=files['tradingview_configured_stocks.txt'].strip().split(',')
        self.assertEqual(len(data),4);self.assertIn('NYSE:GUARDED',data)
        self.assertIn('NYSE:MISS',files['tradingview_primary_stocks_2026-12-29.txt'])
        self.assertNotIn('NYSE:ONLY_SECONDARY',files['tradingview_primary_stocks_2026-12-29.txt'])
    def test_rs_equality_and_missing(self):
        self.assertEqual(rs_state(0,1),'Mixed');self.assertEqual(rs_state(1,1),'Outperforming')
        self.assertEqual(rs_state(-1,-1),'Underperforming');self.assertEqual(rs_state(None,1),'Missing')
        self.assertEqual(rs_state(float('nan'),1),'Missing')
    def test_earnings_year_boundary_inclusive_same_day_missing_and_past(self):
        rows=[{**stock(str(i),earnings=e),'primary_contexts':[]} for i,e in enumerate(['2026-12-29','2027-01-05','2027-01-06',None,'2026-12-28','bad'])]
        result=earnings_window(rows,'2026-12-29')
        self.assertEqual([r['days_away'] for r in result['upcoming']],[0,7])
        self.assertEqual(result['upcoming'][0]['timing_label'],'Today; timing unverified')
        self.assertEqual(len(result['unknown']),3);self.assertEqual(result['later_count'],1)
        weekend=earnings_window([{**stock('W',earnings='2026-10-31'),'primary_contexts':[]}],'2026-10-30')
        self.assertEqual(weekend['upcoming'][0]['days_away'],1)
    def test_actual_group_configuration_covers_every_active_theme(self):
        root=Path(__file__).resolve().parents[1]
        config=json.loads((root/'config/watchlist_exports.json').read_text())
        active=json.loads((root/'config/active_anchors.json').read_text())['anchors']
        assigned=[i for g in config['groups'] for i in g['theme_ids']]
        self.assertEqual(len(config['groups']),5)
        self.assertEqual(config['instrument_limit'],1000)
        self.assertEqual(set(assigned),set(active))
        self.assertEqual(len(assigned),len(set(assigned)))

    def test_thousand_limit_counts_repeated_occurrences_and_anchors(self):
        themes=[theme('t'+str(i),[stock('S'+str(j)) for j in range(20)]) for i in range(50)]
        s=self.snapshot(themes);files=build(s,self.config(themes))
        groups=[f for f in s['export_manifest'] if f['role']=='thematic_navigation']
        self.assertEqual([f['instrument_count'] for f in groups],[987,63])
        self.assertEqual(sum(f['section_count'] for f in groups),50)
        self.assertEqual([n for _,n in flat_chunks(list(range(1001)),1000)],[1000,1])
        self.assertTrue(all(f['file'] in files for f in groups))

    def test_empty_primary_and_unresolved(self):
        themes=[theme('a',[stock('X')],'observation')];s=self.snapshot(themes);files=build(s,self.config(themes))
        self.assertEqual(s['daily_primary']['candidates'],[])
        self.assertFalse(any('primary_stocks' in f for f in files))
        themes[0]['selected'][0].pop('tradingview_symbol')
        with self.assertRaisesRegex(ValueError,'Unresolved'):build(self.snapshot(themes),self.config(themes))
