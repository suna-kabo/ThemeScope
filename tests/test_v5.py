"""Hand-calculated v5 fixtures. Synthetic values are confined to tests."""
import copy
import unittest
from unittest.mock import patch
from src.themescope.v5 import metric, percentiles, strength, overall_score, theme_state, market_condition, participation, map_universe, index_category_views, apply, _nasdaq_effective_date


class V5CalculationTests(unittest.TestCase):
    def test_nasdaq_index_date_accepts_timestamp_suffix(self):
        self.assertEqual(_nasdaq_effective_date('Oct 23, 2026 12:04 PM'), '2026-10-23')
        self.assertEqual(_nasdaq_effective_date('October 23, 2026'), '2026-10-23')
        with self.assertRaisesRegex(ValueError, 'unrecognized'):
            _nasdaq_effective_date('no date')

    def test_percentile_endpoints_ties_and_minimum(self):
        values = {str(i):i for i in range(10)}
        p=percentiles(values,'2026-10-22')
        self.assertEqual(p['0']['value'],0)
        self.assertEqual(p['9']['value'],100)
        values['1']=0
        p=percentiles(values,'2026-10-22')
        self.assertAlmostEqual(p['0']['value'],100*.5/9)
        self.assertEqual(p['0']['value'],p['1']['value'])
        self.assertTrue(all(m['value']==50 for m in percentiles({str(i):1 for i in range(10)},'date').values()))
        self.assertTrue(all(m['status']=='unavailable' for m in percentiles({str(i):i for i in range(9)},'date').values()))

    def test_scores_and_missing_no_reweighting(self):
        current=strength(metric(80),metric(60))
        medium=strength(metric(40),metric(70))
        self.assertEqual(current['value'],74)
        self.assertEqual(medium['value'],49)
        self.assertEqual(overall_score(current,medium)['value'],64)
        self.assertIsNone(overall_score(current,metric(reason='missing'))['value'])
        self.assertIsNone(strength(metric(80),metric(60,'Insufficient coverage'))['value'])
        self.assertIsNone(strength(metric(reason='Nine peers'),metric(60))['value'])

    def test_four_states_unrounded_thresholds(self):
        for c,m,want in [(50,50,'Leading'),(50,49.9999,'Improving'),(49.9999,50,'Fading'),(0,0,'Lagging'),(None,50,'—'),(50,None,'—')]:
            self.assertEqual(theme_state(c,m),want)

    def test_market_conditions_both_indices_both_periods(self):
        for index in ('SPY','QQQ'):
            for period,horizon in [(21,'short-term'),(50,'medium-term')]:
                for price,breadth,want in [(101,50,f'Broad {horizon} strength'),(101,49.9999,f'Narrow {horizon} strength'),(100,50,f'Internal strength, index below EMA{period}'),(100,49.9999,f'Broad {horizon} weakness')]:
                    with self.subTest(index=index,period=period,price=price,breadth=breadth):
                        self.assertEqual(market_condition(price,100,metric(breadth),period)['value'],want)
                self.assertEqual(market_condition(101,100,metric(60,'Insufficient data'),period)['status'],'unavailable')

    def test_breadth_validity_missing_counts_equality(self):
        def run(n,valid,as_of='2026-10-22'):
            universe={'companies':[{'company_id':str(i),'symbols':[str(i)]} for i in range(n)]}
            charts={str(i):{'meta':{'instrumentType':'EQUITY'},'observations':[{'date':'2026-10-22','close':100 if i<4 else 101}]} for i in range(valid)}
            with patch('src.themescope.v5.trend_metric',return_value={'ema21':100,'ema50':100}):
                return participation(universe,{'as_of':as_of},charts,['2026-10-22'],'2026-10-22',{},'2026-10-22')['21']
        m=run(10,8)
        self.assertEqual((m['value'],m['above_count'],m['valid_count'],m['coverage_pct'],m['status']),(50,4,8,80,'valid'))
        self.assertEqual(run(11,8)['status'],'unavailable')
        self.assertEqual(run(10,7)['status'],'unavailable')
        self.assertIsNone(run(0,0)['value'])
        self.assertEqual(run(10,10,'2026-08-01')['status'],'unavailable')

    def test_share_class_mapping_and_foreign_collision(self):
        listings={'GOOG':{'ticker':'GOOG','cik':1},'GOOGL':{'ticker':'GOOGL','cik':1},'ABC':{'ticker':'ABC','cik':2}}
        source={'rows':[{'ticker':'GOOG'},{'ticker':'GOOGL'},{'ticker':'ABC','country':'United Kingdom'},{'ticker':'USD','security_type':'CASH'}]}
        u=map_universe(source,{'listings':listings})
        self.assertEqual(len(u['companies']),2)
        self.assertEqual(u['companies'][0]['symbols'],['GOOG','GOOGL'])
        self.assertEqual(u['companies'][1]['symbols'],[])
        self.assertEqual(len(u['excluded_rows']),1)

    def test_standard_sector_anchors_are_complete_and_unique(self):
        from scripts.generate_dashboard import ROOT
        import json
        config=json.loads((ROOT/'config/themes.json').read_text())
        sectors=[t for t in config['themes'] if t.get('level')=='Sector']
        self.assertEqual(len(sectors),11)
        self.assertEqual(len({t['anchor'] for t in sectors}),11)
        self.assertEqual({t['anchor'] for t in sectors},{'XLB','XLC','XLE','XLF','XLI','XLK','XLP','XLRE','XLU','XLV','XLY'})
        self.assertTrue(all(t['holdings_source']['provider']=='State Street SPDR' for t in sectors))

    def test_index_classifications_and_group_metrics_use_constituent_observations(self):
        companies=[
            {'company_id':'1','symbols':['AAA'],'sector':'Technology','industry':'Software'},
            {'company_id':'2','symbols':['BBB'],'sector':'Technology','industry':'Software'},
            {'company_id':'3','symbols':['CCC'],'sector':'Health','industry':'Biotech'},
        ]
        universe={'companies':companies}
        charts={
            symbol:{'meta':{'instrumentType':'EQUITY','symbol':symbol},'observations':[{'date':'2026-10-22','close':close}]}
            for symbol,close in [('AAA',101),('BBB',99),('CCC',105)]
        }
        def fake_trend(chart,calendar,session,settings):
            return {'ema21':100,'ema50':100}
        def fake_return(chart,calendar,session,window):
            values={'AAA':.10,'BBB':-.02,'CCC':.04}
            return {'status':'valid','value':values[chart['meta']['symbol']]}
        with patch('src.themescope.v5.trend_metric',side_effect=fake_trend), patch('src.themescope.v5.return_metric',side_effect=fake_return):
            result=index_category_views(universe,charts,['2026-10-22'],'2026-10-22',{}, {'url':'https://example.test/source','as_of':'2026-10-22'})
        tech=next(row for row in result['sectors'] if row['name']=='Technology')
        software=next(row for row in result['industries'] if row['name']=='Software')
        self.assertEqual((tech['company_count'],tech['above_ema21_count'],tech['valid_ema21_count'],tech['breadth21_pct']),(2,1,2,50))
        self.assertEqual(tech['median_return21_pct'],4.0)
        self.assertEqual((software['company_count'],software['coverage21_pct'],software['median_return21_pct']),(2,100.0,4.0))

    def test_full_score_path_and_prohibited_inputs(self):
        from scripts.generate_dashboard import ROOT
        from src.themescope.presentation import enrich
        import json
        snapshot=json.loads((ROOT/'data/latest_snapshot.json').read_text())
        snapshot['score_methodology']=json.loads((ROOT/'config/themes.json').read_text())['score_methodology']
        raw=json.loads((ROOT/'data/raw_inputs.json').read_text())
        enrich(snapshot,raw)
        original=snapshot['themes'][0]
        snapshot['themes']=[]
        for i in range(11):
            t=copy.deepcopy(original);t['id']=str(i)
            t['excess_returns']['21']['value']=i/100
            t['excess_returns']['63']['value']=(4 if i==8 else 8 if i==4 else i)/100
            snapshot['themes'].append(t)
        broad={'eligible_count':10,'21':metric(60,above_count=6,valid_count=10,coverage_pct=100),'50':metric(70,above_count=7,valid_count=10,coverage_pct=100)}
        with patch('src.themescope.v5.participation',return_value=broad):
            a=apply(copy.deepcopy(snapshot),raw)
            changed=copy.deepcopy(snapshot)
            for t in changed['themes']:
                t['returns']['5']['value']=99;t['returns']['126']['value']=-99
                t['index_breadth21_pct']=0;t['top5_holding_weight_pct']=100;t['vix']=99;t['sentiment']=0
            b=apply(changed,raw)
        target=a['themes'][8]
        self.assertEqual((target['current_strength_score'],target['medium_strength_score'],target['theme_score']),(74,49,64))
        self.assertEqual([t['theme_score'] for t in a['themes']],[t['theme_score'] for t in b['themes']])

    def test_transport_failure_aborts_but_missing_symbol_is_reported(self):
        from src.themescope.v5 import collect_inputs
        universes={'SPY':{'rows':[{'ticker':'AAA'}]},'QQQ':{'rows':[{'ticker':'AAA'}]}}
        mapping={'listings':{'AAA':{'ticker':'AAA','cik':1}}}
        with patch('src.themescope.v5.fetch_universes',return_value=(universes,mapping)):
            with patch('src.themescope.v5.fetch_yahoo_chart',side_effect=RuntimeError('HTTP Error 503: unavailable')):
                with self.assertRaisesRegex(RuntimeError,'transport failure'):
                    collect_inputs({}, {}, interval=0)
            with patch('src.themescope.v5.fetch_yahoo_chart',side_effect=RuntimeError('HTTP Error 404: no symbol data')):
                result=collect_inputs({}, {}, interval=0)
                self.assertIn('AAA',result['chart_errors'])

    def test_non_anchor_related_membership_is_eligible_without_filing_gate(self):
        import json
        from scripts.generate_dashboard import ROOT
        from src.themescope.collect import _stock_row
        raw=json.loads((ROOT/'data/raw_inputs.json').read_text())
        config=json.loads((ROOT/'config/themes.json').read_text())
        member=copy.deepcopy(json.loads((ROOT/'config/evidence_reviews.json').read_text())['members'][0])
        member['membership_tag']='Related';member['requires_filing_review']=False
        stock=_stock_row(config['themes'][0],member,{'company':member['company'],'weight_pct':None,'_is_anchor_holding':False},raw['charts']['NVDA'],raw['quotes']['NVDA'],raw['charts']['SMH'],{},raw['session_calendar'],raw['run_session'],config['settings'],None)
        self.assertEqual(stock['eligibility'],'eligible_provisional')
        self.assertEqual(stock['membership_tag'],'Related')
        self.assertFalse(stock['is_anchor_holding'])
        self.assertIsNone(stock['etf_weight_pct'])
        member['membership_source']=None
        stock=_stock_row(config['themes'][0],member,{},raw['charts']['NVDA'],raw['quotes']['NVDA'],raw['charts']['SMH'],{},raw['session_calendar'],raw['run_session'],config['settings'],None)
        self.assertNotEqual(stock['eligibility'],'eligible_provisional')

    def test_scores_ignore_unapproved_inputs_and_etf_only(self):
        from scripts.generate_dashboard import ROOT
        from src.themescope.presentation import enrich,validate
        import json
        snapshot=json.loads((ROOT/'data/latest_snapshot.json').read_text())
        snapshot['score_methodology']=json.loads((ROOT/'config/themes.json').read_text())['score_methodology']
        raw=json.loads((ROOT/'data/raw_inputs.json').read_text())
        enrich(snapshot,raw)
        for t in snapshot['themes']:
            t['selected']=[]
        validate(snapshot,raw)  # ETF-only is valid.
        a=apply(copy.deepcopy(snapshot),raw)
        changed=copy.deepcopy(snapshot)
        for t in changed['themes']:
            t['returns']['5']['value']=99
            t['returns']['126']['value']=-99
            t['top5_holding_weight_pct']=100
            t['vix']=99
        b=apply(changed,raw)
        self.assertEqual([(t['current_strength_score'],t['medium_strength_score'],t['theme_score']) for t in a['themes']],[(t['current_strength_score'],t['medium_strength_score'],t['theme_score']) for t in b['themes']])
        self.assertTrue(all(t['field_status']['percentile_excess21']['peer_count']==6 for t in a['themes']))

if __name__ == '__main__':
    unittest.main()
