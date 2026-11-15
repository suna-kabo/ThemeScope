"""Research v2 selection and deterministic export edge cases; synthetic data only."""
from dataclasses import replace
from decimal import Decimal as D, localcontext
from copy import deepcopy
import unittest

from src.themescope.domain import Role
from src.themescope.research.exports import Qualification as Q, exports
from src.themescope.research.v2 import attach, liquidity, policy, state
from src.themescope.research import queries
from src.themescope.themes.calculations import Bar
from scripts.vnext_fixture_report import fixture
from src.themescope.research.engine import calculate_session


class ExportTests(unittest.TestCase):
    def test_research_export_keeps_all_w_signs_and_uses_theme_priority(self):
        rows = [Q('A', 'later', Role.CORE, D(9)), Q('A', 'first', Role.ENABLER, D(-2)),
                Q('B', 'first', Role.CORE, D(0)), Q('C', 'first', Role.CORE, None),
                Q('D', 'first', Role.CORE, D(3))]
        mapping = {r.ticker: dict(status='verified', symbol='NASDAQ:'+r.ticker) for r in rows}
        long = exports(rows, 'long', mapping, theme_order=['first', 'later'])
        self.assertEqual(long['individual']['first'], 'NASDAQ:D\nNASDAQ:B\nNASDAQ:A\nNASDAQ:C\n')
        self.assertEqual(long['assignments']['A']['assigned_section'], 'first')
        self.assertEqual(long['combined'], '###first\nNASDAQ:D\nNASDAQ:B\nNASDAQ:A\nNASDAQ:C\n')
        self.assertEqual(exports(rows[::-1], 'long', mapping, theme_order=['first', 'later']), long)
        short = exports(rows, 'short', mapping, theme_order=['first', 'later'])
        self.assertEqual(short['individual']['first'], 'NASDAQ:A\nNASDAQ:B\nNASDAQ:D\nNASDAQ:C\n')
        with self.assertRaises(ValueError):
            exports([replace(rows[0], role=Role.RELATED)], 'long', mapping, theme_order=['first'])


class SelectionTests(unittest.TestCase):
    def setUp(self):
        self.rules = policy()
        self.config, self.bars, self.days, self.target, self.indices, self.mapping = fixture()

    def snapshot(self, direction='Long bias'):
        return calculate_session(self.config,self.bars,self.days,self.target,direction,self.indices,
                                 {key:'fixture-'+key for key in self.indices},self.mapping)

    def test_states_are_exact_symmetric_and_keep_fading_leaders(self):
        from scripts.research_v2_simulation import classify
        for score in range(101):
            for change in (None,D(-10),D('-9.999'),D(0),D(10)):
                self.assertEqual(state(score,change,'long',self.rules),
                                 state(100-score,None if change is None else -change,'short',self.rules))
                self.assertEqual(state(score,change,'long',self.rules),
                                 classify(D(score),None if change is None else D(score)-change,'long',D(10)))
        self.assertEqual(state(70,-10,'long',self.rules),'Fading')
        self.assertEqual(state(40,10,'long',self.rules),'Improving')
        self.assertEqual(state(40,D('9.999'),'long',self.rules),'Lagging')
        for invalid in (None,'NaN',-1,101):
            self.assertEqual(state(invalid,10,'long',self.rules),'Unavailable')
        with localcontext() as context:
            context.prec=4
            self.assertEqual(state('50.0000000000000000000000001',None,'short',self.rules),'Lagging')

    def test_liquidity_uses_raw_daily_dollars_and_no_single_day_veto(self):
        rules=dict(self.rules,liquidity_sessions=2,average_dollar_volume_floor=100)
        days=self.days[:3]
        bars={('A',days[0]):Bar('A',days[0],D(1),D(10),D(20)),
              ('A',days[1]):Bar('A',days[1],D(1),D(20),D(0)),
              ('A',days[2]):Bar('A',days[2],D(1),D(20),D(999999))}
        row=liquidity(bars,'A',days,days[1],rules)
        self.assertTrue(row['eligible']);self.assertEqual(row['average_dollar_volume'],100)
        self.assertEqual(row['turnover'],0)
        bars['A',days[1]]=replace(bars['A',days[1]],close=D(5))
        self.assertIn('price_not_above_floor',liquidity(bars,'A',days,days[1],rules)['reasons'])
        for mutation in ('missing','completed','regular_session'):
            changed=dict(bars)
            if mutation=='missing':del changed['A',days[0]]
            else:changed['A',days[0]]=replace(changed['A',days[0]],**{mutation:False})
            self.assertFalse(liquidity(changed,'A',days,days[1],rules)['available'])

    def test_attach_keeps_zero_opposite_missing_w_and_preserves_calculations(self):
        before=self.snapshot();original=deepcopy(before)
        names=[r for r in before['relationships'] if r['theme_id']=='alpha']
        for row,w in zip(names,(D(-1),D(0),None,D(1),D(2))):
            row['relative']=replace(row['relative'],w=w)
        result=attach(before,self.bars,self.days,self.mapping)
        selected=[r for r in result['research_v2']['list']['rows'] if r['theme_id']=='alpha']
        self.assertEqual({r['ticker'] for r in selected},{r['ticker'] for r in names})
        self.assertEqual([r['w'] for r in selected],[D(2),D(1),D(0),D(-1),None])
        self.assertEqual([t['returns'] for t in result['themes']],[t['returns'] for t in original['themes']])
        self.assertEqual([t['score'] for t in result['themes']],[t['score'] for t in original['themes']])
        self.assertNotIn('research_v2',before)
        self.assertEqual(result['research_v2']['themes']['alpha']['breadth']['above'],5)
        self.assertTrue(result['research_v2']['themes']['alpha']['breadth']['small_sample'])
    def test_saved_snapshot_alone_is_not_five_session_comparison_provenance(self):
        current=self.snapshot();old=deepcopy(current);old['session']=self.days[58]
        result=attach(current,self.bars,self.days,self.mapping,previous=old)
        self.assertFalse(result['research_v2']['themes']['alpha']['recent']['available'])
        self.assertEqual(result['research_v2']['themes']['alpha']['recent']['reason'],'no_compatible_prior_basis')

    def test_queries_are_independent_copies(self):
        result=attach(self.snapshot(),self.bars,self.days,self.mapping)
        listed=queries.get_research_list(result);listed['rows'].clear()
        self.assertTrue(result['research_v2']['list']['rows'])
        self.assertIsNotNone(queries.get_theme(result,'alpha'))
        self.assertIsNone(queries.get_theme(result,'missing'))
        ticker=result['relationships'][0]['ticker']
        self.assertTrue(queries.get_stock(result,ticker)['relationships'])
        self.assertEqual(len(queries.get_theme_history([result],'alpha')),1)

    def test_read_only_api_queries_share_committed_selection(self):
        from fastapi.testclient import TestClient
        from types import SimpleNamespace
        from pathlib import Path
        from src.themescope.local.app import create_app
        from src.themescope.storage import canonical
        import json
        data=attach(self.snapshot(),self.bars,self.days,self.mapping)
        data['market']={'decision':{'direction':'Long bias'}}
        with TestClient(create_app(Path('.'),SimpleNamespace(snapshot=lambda:data)),base_url='http://127.0.0.1') as client:
            self.assertEqual(client.get('/api/research-list').json(),json.loads(canonical(data['research_v2']['list'])))
            self.assertEqual(client.get('/api/themes/alpha').status_code,200)
            self.assertEqual(client.get('/api/themes/alpha/members').status_code,200)
            self.assertEqual(client.get('/api/stocks/'+data['relationships'][0]['ticker']).status_code,200)
            self.assertEqual(client.get('/api/market').status_code,200)
            self.assertEqual(client.get('/api/market/changes').status_code,200)
            self.assertEqual(client.get('/api/stocks/UNKNOWN').status_code,404)
            self.assertEqual(client.post('/api/research-list').status_code,403)


class PublicTests(unittest.TestCase):
    def test_v2_public_projection_allowlists_fields_and_checks_references(self):
        from scripts.build_cloudflare_demo import demo_snapshot
        from scripts.build_public_snapshot import project_snapshot,SnapshotError
        data=demo_snapshot();data['synthetic_fixture']=False;data['provider_health']={'status':'Healthy'}
        data['research_v2']['private']='discard'
        result=project_snapshot(data,data['session'])
        self.assertNotIn('private',result['research_v2'])
        self.assertEqual(result['research_v2']['list'],data['research_v2']['list'])
        self.assertNotIn('countertrend',result['research'])
        data['research_v2']['list']['rows'][0]['ticker']='UNKNOWN'
        with self.assertRaises(SnapshotError):project_snapshot(data,data['session'])


if __name__ == '__main__':
    unittest.main()
