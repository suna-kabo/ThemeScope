import unittest
from dataclasses import replace
from decimal import Decimal as D
from src.themescope.domain import Configuration, Theme, ThemeStatus, Membership, Role
from src.themescope.themes.calculations import POLICY, bar_map
from src.themescope.themes.index import build_index, indicators, ema, trend, IndexUnavailable
from src.themescope.themes.history import ThemeHistory, transitions
from test_vnext_calculations import SESSIONS, bar


def config(symbols='ABCDE', start=SESSIONS[1]):
    return Configuration((Theme('test','Synthetic test','Fixture',ThemeStatus.ACTIVE,'Synthetic only','Fixture','Other'),),
        tuple(Membership(s,'Synthetic '+s,'test',Role.CORE,start,None,SESSIONS[0],'fixture') for s in symbols),
        {},dict(POLICY),{})


def prices(symbols='ABCDE', sessions=SESSIONS):
    return bar_map(bar(s,d) for s in symbols for d in sessions)


class IndexTests(unittest.TestCase):
    def test_numerical_rebalance_boundary_old_t_new_t_plus_one(self):
        # Jan 5 Friday approval; Jan 8 Monday first earned session.
        sessions=('2024-01-04','2024-01-05','2024-01-08','2024-01-09')
        c=config('ABCDE',sessions[0])
        old=tuple(replace(m,effective_to=sessions[2]) for m in c.memberships)
        new=tuple(replace(m,ticker=n,effective_from=sessions[2]) for m,n in zip(c.memberships,'FGHIJ'))
        c=replace(c,memberships=old+new)
        data=prices('ABCDEFGHIJ',sessions)
        for s in 'ABCDE':
            data[s,sessions[1]]=bar(s,sessions[1],110)  # old earns +10% on approval t
            data[s,sessions[2]]=bar(s,sessions[2],55)   # old -50% must NOT affect t+1
        for s in 'FGHIJ':
            data[s,sessions[1]]=bar(s,sessions[1],200)  # new +100% on t must NOT count
            data[s,sessions[2]]=bar(s,sessions[2],240)  # new earns +20% on t+1
        result=build_index(c,'test',data,sessions,sessions[0],sessions[2])
        self.assertEqual([p.level for p in result],[D(100),D(110),D(132)])
        self.assertEqual(result[1].earned_symbols,tuple('ABCDE'))
        self.assertEqual(tuple(s for s,w in result[1].weights),tuple('FGHIJ'))
        self.assertEqual(result[2].earned_symbols,tuple('FGHIJ'))
        self.assertTrue(result[1].rebalanced)
        self.assertFalse(result[2].rebalanced)

    def test_drift_not_daily_equal_weight_and_formal_rebalance(self):
        c=config()
        data=prices()
        data['A',SESSIONS[1]]=bar('A',SESSIONS[1],200)
        data['A',SESSIONS[2]]=bar('A',SESSIONS[2],400)
        drift=build_index(c,'test',data,SESSIONS,SESSIONS[0],SESSIONS[2])
        reset=build_index(c,'test',data,SESSIONS,SESSIONS[0],SESSIONS[2],formal_rebalances=[SESSIONS[1]])
        self.assertAlmostEqual(drift[-1].level,D(160),places=25)
        self.assertEqual(reset[-1].level,D(144))
        self.assertFalse(drift[1].rebalanced)
        self.assertTrue(reset[1].rebalanced)

    def test_chain_link_no_membership_jump_and_adjusted_corporate_actions(self):
        c=config()
        old=replace(c.memberships[0],effective_to=SESSIONS[2])
        new=replace(old,ticker='F',effective_from=SESSIONS[2],effective_to=None)
        c=replace(c,memberships=(old,)+c.memberships[1:]+(new,))
        data=prices('ABCDEF')
        for session in SESSIONS:data['F',session]=bar('F',session,10000)
        data['B',SESSIONS[0]]=replace(bar('B',SESSIONS[0]),close=D(200))
        data['C',SESSIONS[0]]=replace(bar('C',SESSIONS[0]),close=D(125))
        points=build_index(c,'test',data,SESSIONS,SESSIONS[0],SESSIONS[3])
        self.assertEqual([p.level for p in points],[D(100)]*4)

    def test_fail_closed_missing_constituent_and_pending_watch_related(self):
        c=config()
        data=prices()
        del data['A',SESSIONS[1]]
        with self.assertRaises(IndexUnavailable):build_index(c,'test',data,SESSIONS,SESSIONS[0],SESSIONS[2])
        for modified in (replace(c,memberships=tuple(replace(m,effective_from=None) for m in c.memberships)),
                         replace(c,themes=(replace(c.themes[0],status=ThemeStatus.WATCH),)),
                         replace(c,memberships=(replace(c.memberships[0],role=Role.RELATED),)+c.memberships[1:])):
            with self.assertRaises(IndexUnavailable):build_index(modified,'test',prices(),SESSIONS,SESSIONS[0],SESSIONS[2])
        # A new constituent also needs its rebalance-close price, not merely t+1.
        c=replace(c,memberships=(replace(c.memberships[0],effective_to=SESSIONS[2]),)+c.memberships[1:]+
                  (replace(c.memberships[0],ticker='F',effective_from=SESSIONS[2]),))
        with self.assertRaises(IndexUnavailable):build_index(c,'test',prices(),SESSIONS,SESSIONS[0],SESSIONS[2])

    def test_ema_sma_seed_strict_trends_invalid_and_bootstrap(self):
        self.assertEqual(ema([D(1),D(2),D(3),D(4)],3),D(3))
        self.assertIsNone(ema([D(1),None,D(3)],3))
        self.assertIsNone(ema([D(1),D(2)],3))
        for close,e21,e50,expected in [(101,100,99,'Bullish'),(99,100,101,'Bearish'),
                                     (100,100,99,'Mixed'),(100,99,101,'Mixed'),(100,None,100,'Unavailable')]:
            self.assertEqual(trend(close,e21,e50),expected)
        c=config(start=SESSIONS[51]);data=prices()
        for s in 'ABCDE':
            for i,session in enumerate(SESSIONS):data[s,session]=bar(s,session,100+i)
        bootstrap=build_index(c,'test',data,SESSIONS,SESSIONS[0],SESSIONS[50],bootstrap_symbols='ABCDE')
        live=build_index(c,'test',data,SESSIONS,SESSIONS[50],SESSIONS[52])
        result=indicators(live,SESSIONS,bootstrap=bootstrap)
        self.assertTrue(all(p.bootstrap for p in bootstrap))
        self.assertTrue(all(not p['bootstrap'] for p in result))
        self.assertEqual(len(result),3)
        self.assertEqual(result[0]['level'],100)
        self.assertEqual(result[0]['trend'],'Bullish')
        self.assertEqual(indicators(live,SESSIONS)[0]['trend'],'Unavailable')
        with self.assertRaises(ValueError):indicators(live,SESSIONS,bootstrap=bootstrap[:-1])
        with self.assertRaises(ValueError):indicators((live[0],live[2]),SESSIONS)

    def test_compatible_history_only_adjacent_live_vnext(self):
        old=ThemeHistory('2024-01-05','test','themescope-vnext-1','fixture-series','Mixed','Watch')
        new=replace(old,session='2024-01-08',trend='Bullish',priority='Primary long')
        sessions=('2024-01-04','2024-01-05','2024-01-08','2024-01-09')
        self.assertEqual(transitions(old,new,sessions)['newly_bullish'],True)
        for previous in (None,replace(old,bootstrap=True),replace(old,methodology='manual-csv-2'),
                         replace(old,session='2024-01-04'),replace(old,series_id='other'),
                         replace(old,history_version='legacy'),replace(old,theme_id='other')):
            self.assertEqual(transitions(previous,new,sessions),{'newly_bullish':None,'newly_bearish':None,'priority_change':None})
        self.assertIsNone(transitions(old,replace(new,bootstrap=True),sessions)['newly_bullish'])
        self.assertFalse(transitions(replace(old,trend='Bullish'),new,sessions)['newly_bullish'])
        self.assertTrue(transitions(old,replace(new,trend='Bearish'),sessions)['newly_bearish'])
        self.assertIsNone(transitions(replace(old,trend='Unavailable'),new,sessions)['newly_bullish'])
