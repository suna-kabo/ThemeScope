"""Active policy invariants, independent expectations and adjacent-session history."""
import copy
import itertools
import json
import tempfile
import unittest
from pathlib import Path
from src.themescope.research_policy import *
from src.themescope.local_history import apply,record
from src.themescope.daily_lists import primary_research,build

ROOT=Path(__file__).resolve().parents[1]

def snapshot(session='2026-07-06', price=11, score=20):
    return {'run_kind':'manual_csv','methodology_version':'manual-csv-1','session_date':session,'generated_at':'date',
        'score_methodology':{'theme_score_weights':{'current_strength':.6,'medium_strength':.4}},'ranking_configuration':{},'manual_csv_audit':{'percentile_method':'average'},
        'market_classification':{'direction':'Long bias'},'context':[{'ticker':i,'tradingview_symbol':'AMEX:'+i,'price_state':'Bullish','breadth_state':'Positive'} for i in ('SPY','QQQ','IWM')],
        'themes':[{'id':'a','name':'Alpha','anchor':'ETF','tradingview_symbol':'AMEX:ETF','price_close':price,'ema21':10,'ema50':10,'theme_score':score,'global_rank':1,'returns':{'21':{'value':.1},'63':{'value':.2}},'selected':[]}]}

class PolicyTests(unittest.TestCase):
    def test_complete_market_truth_table_independent_expected_and_symmetry(self):
        table=market_truth_table();self.assertEqual(len(table),64)
        for cell in table:
            a,b,c=cell['spy'],cell['qqq'],cell['breadth'];pair={a,b}
            expected='Unclassified'
            if a is not None and b is not None:
                if a==b=='Bullish':expected='Long bias'
                elif a==b=='Bearish':expected='Short bias'
                elif c is not None:
                    if pair=={'Bullish','Mixed'}:expected='Selective long' if c=='Positive' else 'Neutral'
                    elif pair=={'Bearish','Mixed'}:expected='Selective short' if c=='Negative' else 'Neutral'
                    else:expected={'Positive':'Selective long','Negative':'Selective short','Mixed':'Neutral'}[c]
            self.assertEqual(cell['direction'],expected,(a,b,c))
            self.assertEqual(market_direction(a,b,c),market_direction(b,a,c))
        self.assertEqual([market_rule('Bullish','Bullish',c)['breadth_qualifier'] for c in ('Positive','Mixed','Negative',None)],['Confirming','Mixed','Diverging','N/A'])
    def test_ema_equality_invalid_and_breadth_consensus(self):
        for args,result in [((11,10,9),'Bullish'),((8,9,10),'Bearish'),((10,10,9),'Mixed'),((10,11,9),'Mixed')]:self.assertEqual(ema_classification(*args),result)
        for bad in (None,True,0,-1,float('nan'),float('inf'),'10'):
            for index in range(3):
                values=[10,9,8];values[index]=bad;self.assertIsNone(ema_classification(*values))
        for a,b in itertools.product((*BREADTH_CLASSES,None),repeat=2):
            expected=None if None in (a,b) else a if a==b and a!='Mixed' else 'Mixed'
            self.assertEqual(breadth_consensus(a,b),expected)
        self.assertEqual(breadth_classification(50,50),'Positive');self.assertEqual(breadth_classification(49,49),'Negative')
        self.assertIsNone(breadth_classification(None,50))
        self.assertEqual([ema_relationship(10,v) for v in (9,10,11,None,0)],['Above','At','Below','N/A','N/A'])
    def test_priority_all_scores_classes_full_selective_equivalence(self):
        for side,full,selective in [('long','Long bias','Selective long'),('short','Short bias','Selective short')]:
            for score,ema in itertools.product((0,49.999,50,100,None,True,float('nan')),(*EMA_CLASSES,None)):
                expected='Watch'
                if number(score) and ema and ((side=='long' and score>=50 and ema in ('Bullish','Mixed')) or (side=='short' and score<50 and ema in ('Bearish','Mixed'))):expected='Primary '+side
                self.assertEqual(theme_priority(full,score,ema)['label'],expected)
                self.assertEqual(theme_priority(full,score,ema),theme_priority(selective,score,ema))
                for neutral in ('Neutral','Unclassified'):self.assertEqual(theme_priority(neutral,score,ema,'newly_bullish')['label'],'Watch')
        self.assertEqual(theme_priority('Long bias',20,'Bullish','newly_bullish')['label'],'Primary long')
        self.assertEqual(theme_priority('Short bias',80,'Bearish','newly_bearish')['label'],'Primary short')
        self.assertEqual(theme_priority('Long bias',None,'Bullish','newly_bullish')['label'],'Watch')
    def test_priority_changes_all_pairs(self):
        for old,new in itertools.product(PRIORITY_LABELS,repeat=2):
            expected='—' if old==new else 'New long' if new=='Primary long' else 'New short' if new=='Primary short' else 'Removed'
            self.assertEqual(priority_change(old,new),expected)
        self.assertEqual(priority_change('old policy','Primary long'),'N/A')
    def test_iwm_context_only_and_groups_match_all_primary_no_cap(self):
        s=snapshot();s['themes']=[dict(copy.deepcopy(s['themes'][0]),id=str(i),theme_score=80,priority_change='N/A') for i in range(12)]
        apply_policy(s);before=copy.deepcopy(s['decision']);s['context'][2].update(price_state='Bearish',breadth_state='Negative');apply_policy(s)
        self.assertEqual(s['decision']['market_classification'],before['market_classification'])
        self.assertEqual(len(s['decision']['primary_groups']['unavailable']),12)
        self.assertEqual(set(s['decision']['primary_groups']['unavailable']),{t['id'] for t in s['themes'] if t['research_priority']['category']=='primary'})
    def test_adjacent_session_holiday_transition_same_day_rerun_and_migration(self):
        with tempfile.TemporaryDirectory() as temporary:
            history=Path(temporary);calendar=ROOT/'config/calendars/xnys_2020_2035_v1.json'
            # July 3 2026 observed holiday: July 2 -> July 6 is genuinely adjacent.
            prior=snapshot('2026-07-02',price=9);apply_policy(prior);old=record(prior)
            (history/'2026-07-02.json').write_text(json.dumps(old))
            current=snapshot();result=apply(current,history,calendar)
            self.assertEqual(current['themes'][0]['ema_transition'],'newly_bullish')
            self.assertEqual(current['themes'][0]['priority_change'],'New long')
            (history/'2026-07-06.json').write_text(json.dumps(result))
            rerun=snapshot();self.assertEqual(apply(rerun,history,calendar),result)
            # Transition does not persist into July 7; low Score then returns to Watch.
            later=snapshot('2026-07-07');apply(later,history,calendar)
            self.assertIsNone(later['themes'][0]['ema_transition']);self.assertEqual(later['themes'][0]['priority_change'],'Removed')
            for mutation in ('missing','version','identity','invalid','priority_version'):
                changed=copy.deepcopy(old)
                if mutation=='version':changed['research_history']['ema_methodology']='old'
                if mutation=='identity':changed['themes'][0]['tradingview_symbol']='NYSE:OTHER'
                if mutation=='invalid':changed['themes'][0]['ema21']=None
                if mutation=='priority_version':changed['research_history']['priority_methodology']='old'
                path=history/'2026-07-02.json';path.write_text(json.dumps(changed))
                if mutation=='missing':path.unlink()
                fresh=snapshot();apply(fresh,history,calendar)
                self.assertEqual(fresh['themes'][0]['ema_transition'],'newly_bullish' if mutation=='priority_version' else None)
                self.assertEqual(fresh['themes'][0]['priority_change'],'N/A')
            # Old rank-only history stays rank-compatible but never infers an EMA transition.
            old.pop('research_history');(history/'2026-07-02.json').write_text(json.dumps(old))
            fresh=snapshot();apply(fresh,history,calendar)
            self.assertEqual(fresh['themes'][0]['rank_change_daily'],0);self.assertEqual(fresh['themes'][0]['priority_change'],'N/A')
            self.assertIsNone(fresh['themes'][0]['ema_transition'])
    def test_rank_fingerprint_retired_fields_do_not_change_score_compatibility(self):
        s=snapshot();apply_policy(s);old=copy.deepcopy(s);old['score_methodology']['state_threshold']=50;old['ranking_configuration']['state_boundary']=50
        self.assertEqual(record(s)['ranking_configuration_fingerprint'],record(old)['ranking_configuration_fingerprint'])

class WeightedExportTests(unittest.TestCase):
    def sample(self,side='long'):
        s=snapshot();s['market_classification']={'direction':'Long bias' if side=='long' else 'Short bias'}
        t=s['themes'][0];t['research_priority']=theme_priority(s['market_classification']['direction'],80 if side=='long' else 20,'Mixed')
        def stock(ticker,a,b):return {'ticker':ticker,'tradingview_symbol':'NASDAQ:'+ticker,'returns':{'21':{'value':a},'63':{'value':b}}}
        t['selected']=[stock('BEST',.3,.4),stock('TIE_Z',.2,.3),stock('TIE_A',.2,.3),stock('ZERO',.1,.2),stock('NEG',0,0),stock('MISS',None,.2)]
        return s
    def test_exact_pp_sign_sort_anchor_first_overlap_dedup_and_unchanged_collections(self):
        s=self.sample();other=copy.deepcopy(s['themes'][0]);other.update(id='b',anchor='OTHER',tradingview_symbol='AMEX:OTHER');other['returns']={'21':{'value':.4},'63':{'value':.5}};s['themes'].append(other)
        files,manifest=primary_research(s,1000);r=s['daily_primary_research']
        first=next(f for f in manifest if f.get('theme_id')=='a')
        self.assertEqual(files[first['file']].strip().split(','),['AMEX:ETF','NASDAQ:BEST','NASDAQ:TIE_A','NASDAQ:TIE_Z'])
        second=next(f for f in manifest if f.get('theme_id')=='b');self.assertEqual(files[second['file']],'AMEX:OTHER\n')
        row=next(r for r in r['evaluations'] if r['ticker']=='BEST' and r['theme_id']=='a');self.assertAlmostEqual(row['weighted_excess_pp'],20)
        self.assertTrue(any(row['reason']=='missing_or_invalid:stock_1m' for row in r['evaluations']))
        self.assertTrue(any(row['reason']=='zero_weighted_excess' for row in r['evaluations']))
        combined=files[r['combined_file']].strip().split(',');self.assertEqual(len(combined),len(set(combined)))
        config={'schema_version':1,'instrument_limit':1000,'groups':[{'id':'all','name':'All','theme_ids':['a','b']}]}
        # Builder also requires existing excess-return metadata and earnings; missing is handled.
        all_files=build(s,config)
        self.assertIn('NASDAQ:ZERO',all_files['tradingview_configured_stocks.txt']);self.assertIn('NASDAQ:MISS',all_files['tradingview_configured_stocks.txt'])
        self.assertEqual(len([r for r in s['export_manifest'] if r['role']=='individual_research']),2)
    def test_cross_horizon_exact_cancellation_and_independent_overlap(self):
        s=self.sample();t=s['themes'][0]
        t['returns']={'21':{'value':.1},'63':{'value':.2}}
        t['selected']=[{'ticker':'SHARED','tradingview_symbol':'NYSE:SHARED','returns':{'21':{'value':.12},'63':{'value':.17}}}]
        other=copy.deepcopy(t);other.update(id='b',anchor='OTHER',tradingview_symbol='AMEX:OTHER');other['returns']['63']['value']=.1
        s['themes'].append(other);files,manifest=primary_research(s,1000)
        self.assertEqual(s['daily_primary_research']['evaluations'][0]['reason'],'zero_weighted_excess')
        self.assertEqual(s['daily_primary_research']['evaluations'][1]['included'],True)
        self.assertEqual(sum(r['role']=='stock' for r in s['daily_primary_research']['relationships']),1)

    def test_overlap_relationships_preserved_when_combined_identifiers_deduplicate(self):
        s=self.sample();other=copy.deepcopy(s['themes'][0]);other.update(id='b',anchor='OTHER',tradingview_symbol='AMEX:OTHER');s['themes'].append(other)
        files,manifest=primary_research(s,1000);r=s['daily_primary_research']
        self.assertEqual(sum(row['symbol']=='NASDAQ:BEST' for row in r['relationships']),2)
        self.assertEqual(files[r['combined_file']].count('NASDAQ:BEST'),1)
        s=self.sample('short');s['themes'][0]['selected']=[{'ticker':t,'tradingview_symbol':'NYSE:'+t,'returns':{'21':{'value':v},'63':{'value':v}}} for t,v in [('LESS',.05),('MOST',-.2),('TIE',-.2)]]
        files,manifest=primary_research(s,1000)
        self.assertEqual(files[manifest[0]['file']],'AMEX:ETF,NYSE:MOST,NYSE:TIE,NYSE:LESS\n')

    def test_short_empty_invalid_and_no_arbitrary_five_stock_cap(self):
        s=self.sample('short');files,manifest=primary_research(s,1000)
        item=next(r for r in manifest if r['role']=='individual_primary_research');self.assertEqual(files[item['file']],'AMEX:ETF,NASDAQ:NEG\n')
        s['market_classification']['direction']='Neutral';files,manifest=primary_research(s,1000)
        self.assertEqual(files,{});self.assertEqual(manifest,[]);self.assertIsNone(s['daily_primary_research']['combined_file'])
        s=self.sample();s['themes'][0]['selected']=[{'ticker':f'S{i:02}','tradingview_symbol':f'NYSE:S{i:02}','returns':{'21':{'value':.5},'63':{'value':.5}}} for i in range(20)]
        files,manifest=primary_research(s,1000);self.assertEqual(manifest[0]['instrument_count'],21)
        s['themes'][0]['returns']['21']['value']=float('nan');primary_research(s,1000)
        self.assertTrue(all(r['reason']=='missing_or_invalid:etf_1m' for r in s['daily_primary_research']['evaluations']))

if __name__=='__main__':unittest.main()
