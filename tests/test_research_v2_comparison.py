"""Independent endpoint and population oracles for read-only current-basket change."""
from copy import deepcopy
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D
from unittest.mock import patch
import unittest

from src.themescope.domain import Configuration, Membership, Role, Theme, ThemeStatus
from src.themescope.research.comparison import reconstruct
from src.themescope.research.engine import calculate_session
from src.themescope.themes.calculations import POLICY, Bar, benchmarks


DAYS = tuple((date(2026, 7, 1)+timedelta(days=index)).isoformat() for index in range(140)
             if (date(2026, 7, 1)+timedelta(days=index)).weekday()<5)


def fixture(*, third=False):
    themes=tuple(Theme(key,key.upper(),'Synthetic',ThemeStatus.ACTIVE,
                       'Manufactured company basket','Included','Excluded')
                 for key in ('a','b','c') if third or key!='c')
    members=tuple(Membership(key.upper()+str(i),'Synthetic',key,Role.CORE,DAYS[0],None,
                            DAYS[0],'synthetic_fixture') for key in (t.theme_id for t in themes) for i in range(5))
    config=Configuration(themes,members,{},dict(POLICY),{})
    bars={(m.ticker,day):Bar(m.ticker,day,D(100),D(100),D(2000000)) for m in members for day in DAYS}
    return config,bars


def set_price(bars, ticker, day, price):
    bars[ticker,day]=replace(bars[ticker,day],adjusted_close=D(price),close=D(price))


def snapshot(config,bars,target):
    return calculate_session(config,bars,DAYS,target,'Long Bias',{}, {}, {})


class ComparisonTests(unittest.TestCase):
    def test_exact_five_completed_sessions_uses_each_horizon_endpoints(self):
        config,bars=fixture();target=DAYS[68];prior=DAYS[63]
        for member in config.memberships:
            if member.theme_id=='a':set_price(bars,member.ticker,target,150)
            else:
                set_price(bars,member.ticker,prior,125)
                set_price(bars,member.ticker,target,110)
        before,provenance=reconstruct(config,bars,DAYS,target,current=snapshot(config,bars,target))
        rows={row['theme_id']:row for row in before['themes']}
        self.assertEqual(provenance['previous_session'],prior)
        self.assertEqual((rows['a']['score'],rows['b']['score']),(D(0),D(100)))
        self.assertEqual([m.value for m in rows['b']['returns']],[D('.25'),D('.25')])
        self.assertEqual(provenance['change_sessions'],5)
        self.assertEqual(provenance['basis_session'],target)
        self.assertFalse(provenance['official_history'])
        self.assertNotIn('history',rows['a'])

    def test_fresh_install_skipped_refreshes_and_v1_upgrade_need_only_available_bars(self):
        config,bars=fixture();target=DAYS[68]
        original_config=deepcopy(config);original_bars=deepcopy(bars)
        current=snapshot(config,bars,target)
        self.assertNotIn('research_v2',current)
        # No saved-refresh/store API is an input, even for the first v2 calculation.
        with patch('sqlite3.connect',side_effect=AssertionError('Research comparison cannot access history storage')):
            first=reconstruct(config,bars,DAYS,target,current=current)
            skipped=reconstruct(config,bars,DAYS,target,current=current)
        self.assertTrue(first[1]['available'])
        self.assertEqual(first,skipped)
        self.assertEqual(config,original_config)
        self.assertEqual(bars,original_bars)
        self.assertNotIn('research_v2',current)

    def test_insufficient_completed_history_is_not_missing_refresh_history(self):
        config,bars=fixture()
        for index in (4,63,67):
            before,metadata=reconstruct(config,bars,DAYS,DAYS[index])
            self.assertIsNone(before)
            self.assertEqual(metadata['reason'],'insufficient_completed_history')
        self.assertTrue(reconstruct(config,bars,DAYS,DAYS[68])[1]['available'])

    def test_november_16_amendment_compares_current_basket_without_rewriting_november_9(self):
        config,bars=fixture();target='2026-11-16';prior='2026-11-09'
        new=Membership('NEW','Synthetic new member','a',Role.CORE,target,None,'2026-11-14','synthetic_review')
        config=replace(config,memberships=config.memberships+(new,))
        for day in DAYS:bars['NEW',day]=Bar('NEW',day,D(100),D(100),D(2000000))
        for day in (prior,target):
            for member in config.memberships:
                price=50 if member.ticker=='NEW' else 175 if member.theme_id=='b' else 200 if member.ticker in ('A2','A3','A4') else 100
                set_price(bars,member.ticker,day,price)
        old_official_score=benchmarks(config,bars,DAYS,prior)[1]['a']
        before,metadata=reconstruct(config,bars,DAYS,target,current=snapshot(config,bars,target))
        rows={row['theme_id']:row for row in before['themes']}
        self.assertEqual(old_official_score,D(100))
        self.assertEqual(rows['a']['score'],D(0))
        self.assertEqual(rows['a']['returns'][1].value,D('.5'))
        self.assertEqual(metadata['basis'],'current_reviewed_membership')
        self.assertTrue(metadata['available'])
        self.assertEqual(metadata['previous_session'],prior)
        self.assertNotIn('NEW',{member.ticker for member in config.members_on('a',prior)})
        self.assertEqual(benchmarks(config,bars,DAYS,prior)[1]['a'],old_official_score)
        earlier=reconstruct(config,bars,DAYS,'2026-11-13')[1]
        self.assertNotEqual(earlier['membership_hash'],metadata['membership_hash'])

    def test_each_percentile_population_is_global_even_when_combined_population_is_unchanged(self):
        config,bars=fixture(third=True);target=DAYS[68]
        for member in config.memberships:
            if member.theme_id=='c':
                for index in (0,5,47):del bars[member.ticker,DAYS[index]]
        before,metadata=reconstruct(config,bars,DAYS,target,current=snapshot(config,bars,target))
        self.assertIsNone(before)
        self.assertEqual(metadata['reason'],'ranked_universe_changed')
        self.assertEqual(metadata['ranked_population'],['a','b'])
        self.assertEqual(metadata['horizon_populations']['21'],dict(current=['a','b'],previous=['a','b','c']))
        self.assertEqual(metadata['horizon_populations']['63'],dict(current=['a','b'],previous=['a','b']))

    def test_missing_score_population_is_not_reported_as_valid_change(self):
        config,bars=fixture()
        for member in config.memberships:
            del bars[member.ticker,DAYS[68]]
        before,metadata=reconstruct(config,bars,DAYS,DAYS[68])
        self.assertIsNone(before)
        self.assertEqual(metadata['reason'],'ranked_universe_changed')
        with self.assertRaises(ValueError):reconstruct(config,bars,DAYS,DAYS[68],change_sessions=0)

    def test_mismatched_current_metrics_or_membership_fail_closed(self):
        config,bars=fixture();current=snapshot(config,bars,DAYS[68])
        for defect in ('score','return','methodology','membership'):
            changed=deepcopy(current)
            if defect=='score':changed['themes'][0]['score']=D(99)
            elif defect=='return':changed['themes'][0]['returns']=(replace(changed['themes'][0]['returns'][0],value=D(9)),changed['themes'][0]['returns'][1])
            elif defect=='methodology':changed['methodology']='old-methodology'
            else:changed['relationships'].pop()
            before,metadata=reconstruct(config,bars,DAYS,DAYS[68],current=changed)
            self.assertIsNone(before)
            self.assertEqual(metadata['reason'],'current_basis_mismatch')

    def test_explicit_approved_research_selection_is_frozen_for_both_dates(self):
        config,bars=fixture()
        future=replace(config.memberships[0],effective_from='2027-01-01')
        config=replace(config,memberships=(future,)+config.memberships[1:])
        approved=lambda key:tuple(m for m in config.memberships if m.theme_id==key)
        current=calculate_session(config,bars,DAYS,DAYS[68],'Long Bias',{}, {}, {},research_members_for=approved)
        before,metadata=reconstruct(config,bars,DAYS,DAYS[68],members_for=approved,current=current)
        self.assertTrue(metadata['available'])
        self.assertEqual(next(row for row in before['themes'] if row['theme_id']=='a')['returns'][0].configured,5)
        self.assertFalse(any(m.ticker==future.ticker for m in config.members_on('a',DAYS[68])))


if __name__=='__main__':unittest.main()
