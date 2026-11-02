import copy
import unittest
import json
from pathlib import Path
from src.themescope.daily_lists import build, flat_chunks, earnings_window, rs_state


def stock(ticker, a=.02, b=-.01, earnings=None):
    return {'ticker':ticker,'tradingview_symbol':'NYSE:'+ticker,'metric_status':'available','earnings_date':earnings,'market_cap_usd':2e9,'returns':{'21':{'value':.1},'63':{'value':.2}},'excess_returns':{'21':{'value':a},'63':{'value':b}}}

def theme(id, members, category='primary'):
    return {'id':id,'name':id,'anchor':id.upper(),'tradingview_symbol':'AMEX:'+id.upper(),'research_priority':{'category':category},'returns':{'21':{'value':.08},'63':{'value':.21}},'selected':members}

class DailyListTests(unittest.TestCase):
    def snapshot(self, themes):return {'session_date':'2026-12-29','themes':themes,'manual_csv_audit':{}}
    def config(self, themes, limit=1000):return {'schema_version':1,'instrument_limit':limit,'groups':[{'id':'test','name':'Test','theme_ids':[t['id'] for t in themes]}]}
    def test_group_validation_and_boundary_splitting(self):
        themes=[theme('a',[stock('A')]),theme('b',[stock('B')]),theme('c',[])]
        snapshot=self.snapshot(themes);files=build(snapshot,self.config(themes,3))
        broad=[r for r in snapshot['export_manifest'] if r['role']=='optional_broad_scan' and r['group']=='Test']
        self.assertEqual([r['instrument_count'] for r in broad],[3,2])
        self.assertTrue(all(r['section_count']==0 for r in snapshot['export_manifest']))
        self.assertEqual(files['individual_watchlists/C_c.txt'],'AMEX:C\n')
        with self.assertRaisesRegex(ValueError,'exceeds instrument limit'):build(self.snapshot(themes),self.config(themes,1))
        c=self.config(themes);c['groups'][0]['theme_ids'].append('a')
        with self.assertRaisesRegex(ValueError,'exactly once'):build(self.snapshot(themes),c)
        self.assertEqual([n for _,n in flat_chunks(['a','b','c'],2)],[2,1])
    def test_independent_earnings_union_and_no_mutation_of_rules(self):
        one=stock('SHARED',.02,-.01,earnings='2027-01-01');two=stock('SHARED',-.03,.04,earnings='2027-01-01')
        themes=[theme('one',[one,stock('MISS')]),theme('two',[two]),theme('secondary',[stock('ONLY_SECONDARY')],'secondary'),theme('guarded',[stock('GUARDED')],'observation')]
        themes[0]['selected'][1]['metric_status']='unavailable';themes[0]['selected'][1]['returns']={'21':{'value':None},'63':{'value':None}}
        original=copy.deepcopy([t['research_priority'] for t in themes]);s=self.snapshot(themes);files=build(s,self.config(themes))
        self.assertEqual([t['research_priority'] for t in themes],original)
        self.assertNotIn('daily_primary',s)
        self.assertEqual(s['manual_csv_audit']['daily_lists']['earnings_scope_unique_stocks'],2)
        shared=s['expected_earnings']['upcoming'][0]
        self.assertEqual(shared['ticker'],'SHARED')
        self.assertEqual([c['theme_id'] for c in shared['contexts']],['one','two'])
        self.assertEqual([r['ticker'] for r in s['expected_earnings']['unknown']],['MISS'])
        self.assertEqual(s['expected_earnings']['unknown'][0]['contexts'][0]['theme_id'],'one')
        self.assertEqual([one['excess21_pp'],two['excess21_pp']],[2,-3])
        self.assertEqual([one['excess63_pp'],two['excess63_pp']],[-1,4])
        data=files['tradingview_configured_stocks.txt'].strip().split(',')
        self.assertEqual(len(data),4);self.assertIn('NYSE:GUARDED',data)
        self.assertIn('NYSE:MISS',data)
        self.assertFalse(any('primary_stocks' in f for f in files))
        self.assertEqual(s['export_archives'],['individual_theme_watchlists.zip'])
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

    def test_unique_broad_scan_splitting_and_overlap_in_individuals(self):
        themes=[theme('t'+str(i),[stock('S'+str(i)+'_'+str(j)) for j in range(20)]) for i in range(50)]
        s=self.snapshot(themes);files=build(s,self.config(themes))
        groups=[f for f in s['export_manifest'] if f['role']=='optional_broad_scan' and f['group']=='Test']
        self.assertEqual([f['instrument_count'] for f in groups],[1000,50])
        self.assertTrue(all(f['section_count']==0 for f in groups))
        themes=[theme('a',[stock('SHARED')]),theme('b',[stock('SHARED')])]
        s=self.snapshot(themes);files=build(s,self.config(themes))
        self.assertIn('NYSE:SHARED',files['individual_watchlists/A_a.txt'])
        self.assertIn('NYSE:SHARED',files['individual_watchlists/B_b.txt'])
        self.assertEqual(files['tradingview_group_test.txt'].count('NYSE:SHARED'),1)
        self.assertEqual(files['tradingview_configured_stocks.txt'],'NYSE:SHARED\n')

    def test_anchor_plus_twenty_and_unfiltered_daily_missing_rows(self):
        themes=[theme('a',[stock(str(i)) for i in range(20)])]
        themes[0]['selected'][0]['metric_status']='unavailable'
        s=self.snapshot(themes);files=build(s,self.config(themes))
        self.assertEqual(files['individual_watchlists/A_a.txt'].strip().split(','),['AMEX:A']+['NYSE:'+str(i) for i in range(20)])
        self.assertEqual(len(files['tradingview_configured_stocks.txt'].strip().split(',')),20)
        themes[0]['selected'].append(stock('EXTRA'))
        with self.assertRaisesRegex(ValueError,'more than 20'):build(self.snapshot(themes),self.config(themes))

    def test_empty_primary_and_unresolved(self):
        themes=[theme('a',[stock('X')],'observation')];s=self.snapshot(themes);files=build(s,self.config(themes))
        self.assertNotIn('daily_primary',s)
        self.assertEqual(s['expected_earnings']['upcoming'],[])
        self.assertEqual(s['expected_earnings']['unknown'],[])
        self.assertFalse(any('primary_stocks' in f for f in files))
        themes[0]['selected'][0].pop('tradingview_symbol')
        with self.assertRaisesRegex(ValueError,'Unresolved'):build(self.snapshot(themes),self.config(themes))
