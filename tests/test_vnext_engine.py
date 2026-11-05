import unittest
import tempfile
from dataclasses import replace
from decimal import Decimal as D, localcontext, Inexact
from pathlib import Path
from scripts.vnext_fixture_report import fixture, snapshots, report
from src.themescope.domain import load_configuration, Role
from src.themescope.research.engine import calculate_session,persist_fixture
from src.themescope.themes.history import ThemeHistory
from src.themescope.storage import Store,canonical


class EngineTests(unittest.TestCase):
    def test_formula_fixture_and_all_qualifications_retained(self):
        results=snapshots()
        long=results['Long bias']
        themes={t['theme_id']:t for t in long['themes']}
        self.assertEqual({t:r['score'] for t,r in themes.items()},{'alpha':D(100),'beta':D(50),'weak':D(0)})
        self.assertEqual(themes['alpha']['returns'][1].value,D('.07'))
        self.assertEqual(themes['beta']['returns'][1].value,D('.03'))
        self.assertEqual(themes['weak']['returns'][1].value,D('-.07'))
        # Independent rational oracle for AAA's Alpha LOO W, with known rates.
        from fractions import Fraction as F
        one=lambda rate:F(100+rate,1)/(100+F(rate*42,63))-1
        peer1=(one(6)+one(7))/2
        expected=F(3,5)*(one(20)-peer1)+F(2,5)*(F(20,100)-F(13,200))
        actual=next(r['relative'].w for r in long['relationships'] if r['ticker']=='AAA' and r['theme_id']=='alpha')
        with localcontext() as context:
            context.prec=34
            oracle=D(expected.numerator)/D(expected.denominator)
            self.assertLess(abs(actual-oracle),D('1e-30'))

        qualifying={(r['ticker'],r['theme_id']) for r in long['relationships'] if r['qualifies']}
        for ticker in ('AAA','BBB'):
            self.assertIn((ticker,'alpha'),qualifying)
            self.assertIn((ticker,'beta'),qualifying)
        self.assertEqual(long['exports']['assignments']['AAA'],{'assigned_section':'alpha','also_qualifies_in':['beta']})
        self.assertEqual(long['exports']['assignments']['BBB'],{'assigned_section':'beta','also_qualifies_in':['alpha']})
        self.assertTrue(all(r['relative'].w<0 for r in results['Short bias']['relationships'] if r['qualifies']))
        self.assertTrue(results['Short bias']['exports']['combined'])
        self.assertTrue(all(t['transition']['newly_bullish'] is None for t in long['themes']))
        expected=canonical(report())
        with localcontext() as context:
            context.prec=6
            context.traps[Inexact]=True
            self.assertEqual(canonical(report()),expected)

    def test_daily_failure_does_not_change_membership_benchmark_or_peer_denominator(self):
        c,bars,sessions,target,indices,mapping=fixture()
        before=calculate_session(c,bars,sessions,target,'Long bias',indices,{},mapping)
        changed=dict(bars)
        changed['AAA',target]=replace(changed['AAA',target],volume=D(1))
        after=calculate_session(c,changed,sessions,target,'Long bias',indices,{},mapping)
        self.assertEqual([t['returns'] for t in before['themes']],[t['returns'] for t in after['themes']])
        self.assertEqual([r['relative'] for r in before['relationships']],[r['relative'] for r in after['relationships']])
        self.assertFalse(any(r['qualifies'] for r in after['relationships'] if r['ticker']=='AAA'))
        self.assertEqual(len(after['relationships']),15)

    def test_live_history_compatibility_exception_not_from_bootstrap_or_gap(self):
        c,bars,sessions,target,indices,mapping=fixture()
        # Beta score50 with a Bullish trend would not qualify short, even on a transition.
        previous={t:ThemeHistory(sessions[62],t,c.methodology['version'],'fixture-'+t,'Mixed','Watch') for t in indices}
        series={t:'fixture-'+t for t in indices}
        result=calculate_session(c,bars,sessions,target,'Long bias',indices,series,mapping,previous=previous)
        self.assertTrue(next(t for t in result['themes'] if t['theme_id']=='alpha')['transition']['newly_bullish'])
        for old in (replace(previous['alpha'],bootstrap=True),replace(previous['alpha'],session=sessions[61])):
            result=calculate_session(c,bars,sessions,target,'Long bias',indices,series,mapping,previous={'alpha':old})
            self.assertIsNone(next(t for t in result['themes'] if t['theme_id']=='alpha')['transition']['newly_bullish'])
        invalid=dict(indices);invalid['alpha']=indices['alpha'][:-1]
        with self.assertRaises(ValueError):calculate_session(c,bars,sessions,target,'Long bias',invalid,series,mapping)

    def test_pending_launch_and_watch_related_never_qualify(self):
        c,bars,sessions,target,indices,mapping=fixture()
        launch=load_configuration(Path(__file__).resolve().parents[1])
        pending=calculate_session(launch,{},sessions,target,'Long bias',{}, {},{})
        self.assertEqual(pending['relationships'],[])
        self.assertEqual(pending['exports']['combined'],'')
        self.assertTrue(pending['production_blockers'])
        watch=replace(c,themes=tuple(replace(t,status='watch-only') for t in c.themes))
        self.assertEqual(calculate_session(watch,bars,sessions,target,'Long bias',{}, {},mapping)['relationships'],[])
        related=replace(c,memberships=tuple(replace(m,role=Role.RELATED) for m in c.memberships))
        self.assertEqual(calculate_session(related,bars,sessions,target,'Long bias',{}, {},mapping)['relationships'],[])

    def test_fixture_engine_storage_replay_and_failure_preservation(self):
        c,bars,sessions,target,indices,mapping=fixture()
        snapshot=snapshots()['Long bias']
        with tempfile.TemporaryDirectory() as folder:
            store=Store(Path(folder)/'runtime.sqlite')
            try:
                persist_fixture(store,snapshot,bars.values(),indices)
                first=store.active()
                self.assertEqual(first['exports']['assignments']['AAA']['also_qualifies_in'],['beta'])
                self.assertEqual(len(first['relationships']),15)
                persist_fixture(store,snapshot,bars.values(),indices)
                self.assertEqual(store.active(),first)
                missing=[b for b in bars.values() if not (b.ticker=='AAA' and b.session==target)]
                with self.assertRaises(ValueError):persist_fixture(store,snapshot,missing,indices)
                self.assertEqual(store.active(),first)
                with self.assertRaises(ValueError):persist_fixture(store,dict(snapshot,synthetic_fixture=False),bars.values(),indices)
            finally:store.close()
