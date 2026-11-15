"""Product-contract oracles from actual bar endpoints, not edited calculated fields."""
from copy import deepcopy
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from src.themescope.domain import Configuration,Membership,Role,Theme,ThemeStatus
from src.themescope.research.comparison import reconstruct
from src.themescope.research.engine import calculate_session
from src.themescope.research.v2 import attach,policy,state
from src.themescope.research import queries
from src.themescope.storage import canonical
from src.themescope.themes.calculations import Bar,POLICY
from test_research_v2_comparison import DAYS


DIRECTIONS=('Long Bias','Selective Long','Neutral','Selective Short','Short Bias','Unclassified')


def fixture(direction,*,mirror=False,ties=False,target_index=98,missing=None):
    themes=tuple(Theme(k,k.upper(),'Synthetic',ThemeStatus.ACTIVE,'Manufactured business','Included','Excluded') for k in 'abcde')
    members=tuple(Membership(k.upper()+str(i),'Synthetic',k,Role.CORE,DAYS[0],None,DAYS[0],'synthetic_fixture') for k in 'abcde' for i in range(5))
    members+=(replace(members[15],theme_id='b',role=Role.ENABLER),)
    config=Configuration(themes,members,{},dict(POLICY,launch_rebalance_session=DAYS[0]),{'industry_rule_registry_status':'approved'})
    bars={(m.ticker,day):Bar(m.ticker,day,100,100,2000000) for m in members for day in DAYS}
    target=DAYS[target_index];previous=DAYS[target_index-5]
    for m in members:
        key=m.ticker[0].lower()
        for day,prices in ((previous,dict(a=180,b=190,c=170,d=150,e=160)),(target,dict(a=150,b=140,c=130,d=120,e=110))):
            if ties and day==target:prices['c']=prices['b']
            value=300-prices[key] if mirror else prices[key]
            bars[m.ticker,day]=replace(bars[m.ticker,day],close=D(value),adjusted_close=D(value))
    mapping={m.ticker:dict(status='verified',symbol='TEST:'+m.ticker) for m in members}
    if missing=='population':
        for m in members:
            if m.theme_id=='e':bars.pop((m.ticker,DAYS[target_index-5-21]),None)
    elif missing=='scores':
        for m in members:
            for day in (previous,target):bars.pop((m.ticker,day),None)
    current=calculate_session(config,bars,DAYS,target,direction,{}, {},mapping)
    previous,provenance=reconstruct(config,bars,DAYS,target,current=current)
    return attach(current,bars,DAYS,mapping,previous=previous,comparison_provenance=provenance)


class DirectionTests(unittest.TestCase):
    def test_six_directions_current_state_and_side_are_internally_consistent(self):
        for direction in DIRECTIONS:
            with self.subTest(direction=direction):
                data=fixture(direction);v=data['research_v2'];side=v['current_side']
                expected='long' if direction in ('Long Bias','Selective Long') else 'short' if direction in ('Short Bias','Selective Short') else None
                self.assertEqual(side,expected)
                for row in v['themes'].values():
                    self.assertNotIn('state',row)
                    self.assertEqual(row['current_state'],row['long_state'] if side=='long' else row['short_state'] if side=='short' else None)
                    self.assertEqual(row['current_side'],side)
                self.assertNotIn('Primary',data['today_plan'])
                if side is None:
                    self.assertEqual(v['theme_order'],list('abcde'))
                    self.assertFalse(any(row['researchable'] for row in v['themes'].values()))
                    self.assertEqual(v['list']['rows'],[]);self.assertEqual(data['exports']['combined'],'')
                    self.assertIsNone(v['themes']['a']['recent']['directional_score_change'])

    def test_selective_retains_same_set_and_deprioritizes_improving_for_both_sides(self):
        for full,selective in (('Long Bias','Selective Long'),('Short Bias','Selective Short')):
            a,b=fixture(full),fixture(selective)
            rows=lambda data:{(r['ticker'],r['theme_id']) for r in data['research_v2']['list']['rows']}
            self.assertEqual(rows(a),rows(b))
            order_a=a['research_v2']['theme_order'];order_b=b['research_v2']['theme_order']
            states=a['research_v2']['themes'];improving=next(k for k,r in states.items() if r['current_state']=='Improving')
            fading=next(k for k,r in states.items() if r['current_state']=='Fading')
            self.assertLess(order_a.index(improving),order_a.index(fading))
            self.assertLess(order_b.index(fading),order_b.index(improving))
            self.assertNotEqual(a['exports']['assignments']['D0']['assigned_section'],b['exports']['assignments']['D0']['assigned_section'])
            for data in (a,b):
                lines=data['exports']['combined'].splitlines()
                self.assertEqual(sum(line=='TEST:D0' for line in lines),1)

    def test_short_reasons_and_directional_changes_describe_weakness_not_raw_strength_gain(self):
        data=fixture('Short Bias')['research_v2']['themes']
        self.assertEqual(data['e']['current_state'],'Leading')
        self.assertIn('Lower structural strength',data['e']['reason'])
        self.assertEqual(data['b']['current_state'],'Improving')
        self.assertLess(data['b']['recent']['raw_score_change'],0)
        self.assertGreater(data['b']['recent']['directional_score_change'],0)
        self.assertIn('weakened',data['b']['reason'])
        self.assertEqual(data['d']['current_state'],'Fading');self.assertIn('recovered',data['d']['reason'])

    def test_mirrored_bar_paths_produce_symmetric_states_and_selective_order(self):
        for a,b in (('Long Bias','Short Bias'),('Selective Long','Selective Short')):
            long,short=fixture(a),fixture(b,mirror=True)
            self.assertEqual(long['research_v2']['theme_order'],short['research_v2']['theme_order'])
            for key in long['research_v2']['themes']:
                l,s=long['research_v2']['themes'][key],short['research_v2']['themes'][key]
                self.assertEqual(l['current_state'],s['current_state'])
                self.assertEqual(l['recent']['directional_score_change'],s['recent']['directional_score_change'])
                self.assertEqual(l['recent']['directional_rank_change'],s['recent']['directional_rank_change'])

    def test_five_session_rank_uses_correct_horizon_and_tie_policy_is_explicit(self):
        data=fixture('Long Bias')['research_v2']['themes']
        self.assertEqual(data['b']['strength_rank'],2)
        self.assertEqual(data['b']['recent']['raw_rank_change'],-1)
        self.assertEqual(data['b']['recent']['comparison_session'],DAYS[93])
        for side in ('long','short'):self.assertEqual(state(50,0,side,policy()),'Leading')
        self.assertIsNone(state(50,0,None,policy()))
        tied=fixture('Short Bias',ties=True)['research_v2']['themes']['b']['recent']
        self.assertEqual(tied['raw_rank_change'],-1)
        self.assertEqual(tied['directional_rank_change'],2)

    def test_queries_strip_legacy_priority_and_distinguish_unknown_from_empty(self):
        data=fixture('Neutral');theme=queries.get_theme(data,'a')
        for key in ('priority','transition','history'):self.assertNotIn(key,theme)
        self.assertIsNone(theme['research']['current_state'])
        self.assertIsNone(queries.get_theme_members(data,'missing'))
        data['themes'].append(dict(theme_id='watch',status='watch-only',score=None))
        self.assertEqual(queries.get_theme_members(data,'watch'),[])
        old=deepcopy(data);old['research_v2'].pop('contract_revision')
        self.assertIsNone(queries.get_research_list(old))
        self.assertIsNone(queries.get_theme_members(old,'a')[0]['qualifies'])


class ProjectionTests(unittest.TestCase):
    def test_normalized_public_contract_rejects_semantic_and_export_tampering(self):
        from scripts.build_cloudflare_demo import demo_snapshot
        from scripts.build_public_snapshot import project_snapshot,SnapshotError
        data=demo_snapshot();data['synthetic_fixture']=False;data['provider_health']={'status':'Healthy'}
        self.assertEqual(project_snapshot(data,data['session'])['research_v2']['contract_revision'],2)
        def wrong_side(v):v['research_v2']['current_side']='short'
        def wrong_state(v):next(iter(v['research_v2']['themes'].values()))['current_state']='Fading'
        def wrong_order(v):v['research_v2']['theme_order'].reverse()
        def wrong_w(v):v['research_v2']['list']['rows'][0]['w']='999'
        def wrong_role(v):v['research_v2']['list']['rows'][0]['role']='Related'
        def wrong_export(v):v['exports']['combined']+='TEST:EXTRA\n'
        def wrong_opposite_state(v):v['research_v2']['themes']['alpha']['short_state']='Leading'
        def wrong_membership_hash(v):v['research_v2']['comparison']['membership_hash']='0'*64
        def wrong_liquidity(v):v['relationships'][0]['eligibility']['average_dollar_volume']='0'
        def wrong_placement(v):v['relationships'][0]['assigned_section']='wrong'
        for mutate in (wrong_side,wrong_state,wrong_order,wrong_w,wrong_role,wrong_export,
                       wrong_opposite_state,wrong_membership_hash,wrong_liquidity,wrong_placement):
            changed=deepcopy(data);mutate(changed)
            with self.subTest(mutate=mutate.__name__),self.assertRaises(SnapshotError):project_snapshot(changed,changed['session'])

    def test_official_history_http_is_read_only_and_does_not_expose_legacy_selection(self):
        from fastapi.testclient import TestClient
        from src.themescope.local.app import create_app
        from src.themescope.local.service import fixture_service
        from hashlib import sha256
        with tempfile.TemporaryDirectory() as directory:
            service=fixture_service(directory);self.assertIsNotNone(service.refresh())
            before=sha256(service.db.read_bytes()).hexdigest()
            with TestClient(create_app(Path('.'),service),base_url='http://127.0.0.1') as client:
                response=client.get('/api/themes/alpha/history');self.assertEqual(response.status_code,200)
                data=response.json();self.assertEqual(data['basis'],'official_session_observations')
                self.assertFalse(data['reconstructed'])
                self.assertNotIn('priority',data['observations'][0]['theme'])
                self.assertEqual(client.get('/api/themes/missing/history').status_code,404)
                self.assertEqual(client.post('/api/themes/alpha/history').status_code,403)
            self.assertEqual(before,sha256(service.db.read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
