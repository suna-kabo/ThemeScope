import unittest
from dataclasses import replace
from pathlib import Path
from src.themescope.domain import load_configuration, validate, Role, ThemeStatus, MarketRoster, effective_session_after_close

ROOT = Path(__file__).resolve().parents[1]


class DomainTests(unittest.TestCase):
    def setUp(self):
        self.config = load_configuration(ROOT)

    def test_launch_counts_and_pending_dates(self):
        c = self.config
        self.assertEqual(sum(t.status == ThemeStatus.ACTIVE for t in c.themes), 44)
        self.assertEqual(sum(t.status == ThemeStatus.WATCH for t in c.themes), 8)
        self.assertEqual(len(c.memberships), 726)
        self.assertEqual(len({m.ticker for m in c.memberships}), 668)
        self.assertEqual(len(c.universe['instruments']), 1525)
        self.assertTrue(all(m.effective_from is None for m in c.memberships))
        self.assertEqual(c.members_on('semiconductors', '2026-11-05'), ())
        self.assertTrue(c.production_blockers())

    def test_watch_only_never_calculates_and_related_excluded(self):
        c = self.config
        self.assertEqual(c.members_on('quantum-computing', '2026-11-05'), ())
        member = replace(c.memberships[0], role=Role.RELATED, effective_from='2026-11-06')
        self.assertFalse(member.calculation_eligible)
        self.assertFalse(member.active_on('2026-11-05'))
        self.assertTrue(member.active_on('2026-11-06'))
        member = replace(member, effective_to='2026-11-09')
        self.assertFalse(member.active_on('2026-11-09'))

    def test_duplicate_unknown_and_bad_intervals_rejected(self):
        c = self.config
        with self.assertRaisesRegex(ValueError, 'Duplicate/overlapping'):
            validate(c.themes, (*c.memberships, c.memberships[0]), c.universe)
        with self.assertRaisesRegex(ValueError, 'outside approved'):
            validate(c.themes, (replace(c.memberships[0], ticker='NOT_IN_REVIEW'),), c.universe)
        with self.assertRaisesRegex(ValueError, 'interval'):
            replace(c.memberships[0], effective_from='2026-11-06', effective_to='2026-11-06')
        with self.assertRaisesRegex(ValueError, '>=5'):
            validate(c.themes, (), c.universe)

    def test_nonoverlapping_history_intervals_allowed(self):
        c = self.config
        first = replace(c.memberships[0], effective_from='2026-11-06', effective_to='2026-11-09')
        second = replace(first, effective_from='2026-11-09', effective_to=None)
        validate(c.themes, (first, second), c.universe, launch=False)
        with self.assertRaises(ValueError):
            validate(c.themes, (first, replace(second, effective_from='2026-11-06')), c.universe, launch=False)

    def test_market_rosters_separate_and_no_iwm_vote(self):
        MarketRoster('SPY', '2026-11-06', ('AAA',), 'manual')
        MarketRoster('QQQ', '2026-11-06', ('BBB',), 'manual')
        with self.assertRaises(ValueError):
            MarketRoster('IWM', '2026-11-06', ('AAA',), 'manual')
        with self.assertRaises(ValueError):
            MarketRoster('SPY', '2026-11-06', ('AAA', 'AAA'), 'manual')

    def test_approval_close_preserves_old_session_and_starts_next_trading_session(self):
        sessions = ['2026-11-05', '2026-11-06', '2026-11-09']
        effective = effective_session_after_close('2026-11-06', sessions)
        self.assertEqual(effective, '2026-11-09')
        old = replace(self.config.memberships[0], effective_from='2026-11-05', effective_to=effective)
        new = replace(old, ticker='SYNTHETIC_NEW', effective_from=effective, effective_to=None)
        self.assertTrue(old.active_on('2026-11-06'))
        self.assertFalse(new.active_on('2026-11-06'))
        self.assertFalse(old.active_on('2026-11-09'))
        self.assertTrue(new.active_on('2026-11-09'))
        with self.assertRaises(ValueError):
            effective_session_after_close('2026-11-07', sessions)
