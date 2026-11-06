"""Research membership is explicit and never becomes official earned history."""
from dataclasses import replace
from decimal import Decimal as D,localcontext
from fractions import Fraction as F
from statistics import median
from unittest.mock import patch
from pathlib import Path
import json,tempfile,unittest
from src.themescope.research.universe import approved_launch_universe,approved_launch_close_membership
from src.themescope.research.engine import calculate_session
from src.themescope.research.primary import priority
from src.themescope.themes.calculations import bar_map
from src.themescope.themes.index import build_index
from src.themescope.themes.history import ThemeHistory,transitions
from src.themescope.storage import Store
from vnext_prelaunch_fixture import PrelaunchFixture,DAYS

T='2026-11-05';L='2026-11-06';E='2026-11-09'

class PrelaunchResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        earnings=patch('src.themescope.local.service.optional_earnings',return_value={})
        earnings.start();self.addCleanup(earnings.stop)

    def refresh(self,fixture,day=T):
        fixture.target=day;snapshot=fixture.service.refresh()
        self.assertIsNotNone(snapshot,fixture.service.status())
        return snapshot

    def test_real_44_themes_produce_scores_trends_peers_and_primary_without_live_history(self):
        fixture=PrelaunchFixture(self.root,full=True);config=fixture.config
        before=config.memberships;snapshot=self.refresh(fixture)
        layer=snapshot['theme_layer']
        self.assertEqual(layer,{'state':'pre_launch_research','research_session':T,
            'membership_basis':'approved_launch_membership','membership_basis_session':E,
            'launch_rebalance_session':L,'first_earned_session':E,'official_live_history':False,
            'approved_relationships':726,'calculation_relationships':721})
        self.assertFalse(snapshot['synthetic_fixture'])
        self.assertEqual(snapshot['production_blockers'],[])
        self.assertEqual(config.memberships,before)
        self.assertTrue(all(m.effective_from==E and not m.active_on(T) for m in before))
        self.assertTrue(all(not config.members_on(t.theme_id,T) for t in config.themes))
        active=[t for t in snapshot['themes'] if t['status']=='active']
        self.assertEqual(len(active),44)
        self.assertEqual(snapshot['market_direction'],'Long bias')
        self.assertTrue(all(t['score'] is not None and t['index']['trend']=='Bullish' for t in active))
        self.assertTrue(all(t['index']['ema21'] is not None and t['index']['ema50'] is not None for t in active))
        self.assertTrue(all(all(m.value==100 for m in t['breadth']) for t in active))
        for theme in snapshot['themes']:
            self.assertTrue(theme['index']['bootstrap'])
            self.assertTrue(theme['history']['bootstrap']);self.assertFalse(theme['history']['signal_eligible'])
            self.assertIn(':pre-launch-research:',theme['history']['series_id'])
            self.assertTrue(all(v is None for v in theme['transition'].values()))
            self.assertEqual(theme['priority'],priority(snapshot['market_direction'],theme['score'],theme['index']['trend'],theme['transition']))
        expected={(m.ticker,m.theme_id) for m in before if m.calculation_eligible}
        self.assertEqual({(r['ticker'],r['theme_id']) for r in snapshot['relationships']},expected)
        self.assertEqual(len(snapshot['relationships']),721)
        self.assertTrue(all(r['relative'].w is not None for r in snapshot['relationships']))
        selected=[r for r in snapshot['relationships'] if r['qualifies']]
        self.assertTrue(selected);self.assertTrue(snapshot['exports']['individual'])
        self.assertTrue(snapshot['exports']['combined'])
        identifiers=[line for line in snapshot['exports']['combined'].splitlines() if not line.startswith('###')]
        self.assertEqual(len(identifiers),len({r['ticker'] for r in selected}))
        self.assertEqual(len(identifiers),len(set(identifiers)))
        self.assertTrue(all(end<=T for provider in fixture.providers for symbols,start,end in provider.calls))
        store=Store(fixture.service.db)
        try:
            self.assertEqual(store.connection.execute('SELECT count(*) FROM theme_index').fetchone()[0],0)
            self.assertEqual(store.connection.execute('SELECT max(session) FROM observations').fetchone()[0],T)
            self.assertEqual(store.active()['theme_layer'],layer)
            for row in store.connection.execute('SELECT payload FROM theme_snapshot'):
                history=json.loads(row[0])['history']
                self.assertTrue(history['bootstrap']);self.assertFalse(history['signal_eligible'])
        finally:store.close()
        # Independent rational oracle: median endpoint returns and average-tie ranks.
        bars=bar_map(fixture.bars);end=DAYS.index(T);returns=[]
        for horizon in (21,63):
            returns.append({s:F(bars[s,T].adjusted_close)/F(bars[s,DAYS[end-horizon]].adjusted_close)-1
                            for s in {m.ticker for m in before if m.calculation_eligible}})
        medians=[{t['theme_id']:median(values[m.ticker] for m in before if m.theme_id==t['theme_id'] and m.calculation_eligible)
                  for t in active} for values in returns]
        def percentile(values,key):
            value=values[key];less=sum(v<value for v in values.values());ties=sum(v==value for v in values.values())
            return (F(2*less+ties+1,2)-1)/F(len(values)-1)*100
        with localcontext() as context:
            context.prec=34
            dec=lambda value:D(value.numerator)/D(value.denominator)
            for theme in active:
                key=theme['theme_id']
                for i in (0,1):self.assertLess(abs(theme['returns'][i].value-dec(medians[i][key])),D('1e-30'))
                score=F(3,5)*percentile(medians[0],key)+F(2,5)*percentile(medians[1],key)
                self.assertLess(abs(theme['score']-dec(score)),D('1e-29'))
            row=selected[0];peers=[m.ticker for m in before if m.theme_id==row['theme_id'] and m.calculation_eligible and m.ticker!=row['ticker']]
            w=sum(weight*(values[row['ticker']]-median(values[s] for s in peers)) for weight,values in zip((F(3,5),F(2,5)),returns))
            self.assertLess(abs(row['relative'].w-dec(w)),D('1e-30'))

    def test_research_stops_at_launch_and_cannot_supply_live_transitions(self):
        fixture=PrelaunchFixture(self.root)
        before=self.refresh(fixture);launch=self.refresh(fixture,L);earned=self.refresh(fixture,E)
        self.assertEqual(launch['theme_layer']['state'],'initialized')
        self.assertTrue(launch['theme_layer']['official_live_history'])
        self.assertEqual(earned['theme_layer']['state'],'live')
        self.assertTrue(all(t['index']['level']==100 for t in launch['themes']))
        bars=bar_map(fixture.bars)
        for theme in earned['themes']:
            names=[m.ticker for m in fixture.config.members_on(theme['theme_id'],E)]
            with localcontext() as context:
                context.prec=34
                expected=D(100)*sum(bars[s,E].adjusted_close/bars[s,L].adjusted_close for s in names)/len(names)
            self.assertLess(abs(theme['index']['level']-expected),D('1e-29'))
            self.assertTrue(all(v is None for v in theme['transition'].values()))
            self.assertNotIn('pre-launch-research',theme['history']['series_id'])
            self.assertFalse(theme['history']['bootstrap'])
        for current in (launch,earned):
            for old,new in zip(before['themes'],current['themes']):
                self.assertTrue(all(v is None for v in transitions(ThemeHistory(**old['history']),ThemeHistory(**new['history']),DAYS).values()))
        store=Store(fixture.service.db)
        try:
            points=[json.loads(r[0]) for r in store.connection.execute('SELECT payload FROM theme_index')]
            self.assertFalse(any(p['session']==T and not p['bootstrap'] for p in points))
            starts=[p for p in points if p['session']==L and not p['bootstrap']]
            self.assertTrue(starts)
            self.assertTrue(all(D(p['level'])==100 and p['earned_symbols']==[] for p in starts))
        finally:store.close()

    def test_launch_close_research_candidates_and_complete_earned_lifecycle(self):
        fixture=PrelaunchFixture(self.root)
        before=self.refresh(fixture,T)
        launch=self.refresh(fixture,L)
        first=self.refresh(fixture,E)
        second=self.refresh(fixture,'2026-11-10')
        expected={(m.ticker,m.theme_id) for m in fixture.config.memberships if m.calculation_eligible}
        for current in (before,launch,first,second):
            self.assertEqual({(r['ticker'],r['theme_id']) for r in current['relationships']},expected)
            self.assertTrue(all(t['score'] is not None for t in current['themes']))
            self.assertTrue(all(r['relative'].w is not None and r['eligibility'].available for r in current['relationships']))
        self.assertEqual(launch['theme_layer']['state'],'initialized')
        self.assertTrue(launch['theme_layer']['official_live_history'])
        self.assertTrue(any(r['qualifies'] for r in launch['relationships']))
        self.assertTrue(launch['exports']['combined']);self.assertTrue(launch['exports']['individual'])
        self.assertTrue(all(t['index']['level']==100 and not t['history']['signal_eligible'] for t in launch['themes']))
        self.assertTrue(all(not t['history']['bootstrap'] and ':pre-launch-research:' not in t['history']['series_id'] for t in launch['themes']))
        self.assertTrue(all(all(v is None for v in t['transition'].values()) for current in (launch,first) for t in current['themes']))
        self.assertTrue(all(t['history']['signal_eligible'] for current in (first,second) for t in current['themes']))
        self.assertTrue(all(t['transition']['priority_change'] is not None for t in second['themes']))
        store=Store(fixture.service.db)
        try:
            points=[json.loads(r[0]) for r in store.connection.execute('SELECT payload FROM theme_index')]
            self.assertTrue(all(p['session']>=L for p in points if not p['bootstrap']))
            starts=[p for p in points if p['session']==L and not p['bootstrap']]
            self.assertTrue(starts)
            self.assertTrue(all(D(p['level'])==100 and p['earned_symbols']==[] for p in starts))
        finally:store.close()

    def test_selector_is_general_and_preserves_membership_objects(self):
        fixture=PrelaunchFixture(self.root);config=fixture.config
        launch='2026-11-12';earned='2026-11-13';target='2026-11-11'
        config=replace(config,methodology=dict(config.methodology,launch_rebalance_session=launch),
                       memberships=tuple(replace(m,effective_from=earned) for m in config.memberships))
        selection=approved_launch_universe(config,target,DAYS)
        self.assertEqual(selection.research_session,target);self.assertEqual(selection.first_earned_session,earned)
        self.assertEqual(selection.relationships,config.memberships)
        self.assertIs(selection.relationships[0],config.memberships[0])
        self.assertTrue(all(not m.active_on(target) for m in selection.relationships))
        self.assertIsNone(approved_launch_universe(config,launch,DAYS))
        close=approved_launch_close_membership(config,launch,DAYS)
        self.assertEqual(close.first_earned_session,earned)
        self.assertEqual(close.relationships,config.memberships)
        self.assertIsNone(approved_launch_close_membership(config,target,DAYS))
        self.assertIsNone(approved_launch_close_membership(config,earned,DAYS))
        self.assertIsNone(approved_launch_close_membership(config,launch,DAYS,activation_blockers=['missing roster']))
        blocked=replace(config,methodology=dict(config.methodology,production_enabled=False))
        self.assertIsNone(approved_launch_close_membership(blocked,launch,DAYS))
        self.assertIsNone(approved_launch_universe(config,earned,DAYS))

    def test_config_and_each_roster_blocker_still_fail_closed(self):
        fixture=PrelaunchFixture(self.root);c=fixture.config
        for altered in (replace(c,methodology=dict(c.methodology,production_enabled=False)),
                        replace(c,evidence_gate=dict(c.evidence_gate,industry_rule_registry_status='pending')),
                        replace(c,memberships=(replace(c.memberships[0],evidence_status='primary_source_refresh_required'),)+c.memberships[1:]),
                        replace(c,memberships=(replace(c.memberships[0],effective_from=None),)+c.memberships[1:])):
            self.assertIsNone(approved_launch_universe(altered,T,DAYS))
        for benchmark in ('SPY','QQQ'):
            other=PrelaunchFixture(self.root/benchmark,missing_rosters=(benchmark,))
            snapshot=self.refresh(other)
            self.assertEqual(snapshot['theme_layer']['state'],'activation_blocked')
            self.assertEqual(snapshot['relationships'],[])
            self.assertEqual(snapshot['exports']['combined'],'')
            self.assertEqual(snapshot['production_blockers'],[f'Effective {benchmark} constituent roster missing for {T}'])

    def test_insufficient_bootstrap_does_not_invalidate_endpoint_theme_score(self):
        fixture=PrelaunchFixture(self.root)
        ticker=next(m.ticker for m in fixture.config.memberships if m.theme_id=='airlines')
        missing=DAYS[DAYS.index(T)-20]
        fixture.bars=tuple(b for b in fixture.bars if not(b.ticker==ticker and b.session==missing))
        snapshot=self.refresh(fixture)
        theme=next(t for t in snapshot['themes'] if t['theme_id']=='airlines')
        self.assertIsNotNone(theme['score'])
        self.assertEqual(theme['index']['trend'],'Unavailable')
        self.assertEqual(theme['priority'],'Watch')
        self.assertTrue(all(v is None for v in theme['transition'].values()))

    def test_daily_liquidity_does_not_change_research_membership_or_peer_calculations(self):
        fixture=PrelaunchFixture(self.root)
        first=self.refresh(fixture)
        selected=next(r for r in first['relationships'] if r['qualifies'])
        fixture.bars=tuple(replace(b,volume=D(1)) if b.ticker==selected['ticker'] and b.session==T else b for b in fixture.bars)
        after=self.refresh(fixture)
        self.assertEqual([t['score'] for t in first['themes']],[t['score'] for t in after['themes']])
        self.assertEqual(len(first['relationships']),len(after['relationships']))
        changed=next(r for r in after['relationships'] if (r['ticker'],r['theme_id'])==(selected['ticker'],selected['theme_id']))
        self.assertEqual(changed['relative'],selected['relative']);self.assertFalse(changed['qualifies'])

    def test_engine_rejects_mixed_live_and_research_series(self):
        fixture=PrelaunchFixture(self.root);config=fixture.config
        selection=approved_launch_universe(config,T,DAYS)
        sessions=tuple(s for s in fixture.sessions if s<=T);bars=bar_map(fixture.bars)
        theme=config.themes[0].theme_id
        points=build_index(config,theme,bars,DAYS,sessions[0],T,
                           bootstrap_symbols=tuple(m.ticker for m in selection.members_for(theme)))
        def calculate(**kwargs):return calculate_session(config,bars,sessions,T,'Long bias',{}, {},{},**kwargs)
        with self.assertRaisesRegex(ValueError,'Explicit research universe'):
            calculate(research_indices={theme:points})
        with self.assertRaisesRegex(ValueError,'bootstrap-only'):
            calculate(research_universe=selection,research_indices={theme:(replace(points[-1],bootstrap=False),)})
        with self.assertRaisesRegex(ValueError,'remain separate'):
            calculate_session(config,bars,sessions,T,'Long bias',{theme:points},{},{},research_universe=selection)

    def test_older_gap_or_recent_listing_can_still_supply_contiguous_emas(self):
        fixture=PrelaunchFixture(self.root)
        ticker=next(m.ticker for m in fixture.config.memberships if m.theme_id=='airlines')
        # A recent listing has 64 contiguous sessions: enough for 63-return and EMA50.
        earliest=DAYS[DAYS.index(T)-63]
        fixture.bars=tuple(b for b in fixture.bars if b.ticker!=ticker or b.session>=earliest)
        snapshot=self.refresh(fixture)
        theme=next(t for t in snapshot['themes'] if t['theme_id']=='airlines')
        self.assertIsNotNone(theme['score'])
        self.assertEqual(theme['index']['trend'],'Bullish')
        self.assertTrue(all(m.value==100 for m in theme['breadth']))
        self.assertTrue(all(v is None for v in theme['transition'].values()))
