"""Rule diagnostics preserve symmetry and never infer missing liquidity."""
from decimal import Decimal as D
import unittest

from scripts.research_v2_simulation import average_dollar_volume, classify, diagnose, transition_diagnostics
from scripts.vnext_fixture_report import fixture
from src.themescope.themes.calculations import Bar


class RuleSimulationTests(unittest.TestCase):
    def test_states_and_exact_boundaries(self):
        cases = [(70, 70, 'Leading'), (70, 80, 'Fading'), (40, 30, 'Improving'),
                 (40, 31, 'Lagging'), (50, 60, 'Fading'), (50, None, 'Leading'),
                 (49, None, 'Lagging'), (None, 30, 'Unavailable')]
        for score, old, expected in cases:
            with self.subTest(score=score, previous=old):
                self.assertEqual(classify(None if score is None else D(score),
                                          None if old is None else D(old), 'long', D(10)), expected)

    def test_mirrored_short_symmetry_and_fading_retention(self):
        for score in range(101):
            for old in (None, D(0), D(40), D(70), D(100)):
                long = classify(D(score), old, 'long', D(10))
                short = classify(D(100-score), None if old is None else 100-old, 'short', D(10))
                self.assertEqual(long, short)
        self.assertIn(classify(D(65), D(80), 'long', D(10)), ('Leading', 'Improving', 'Fading'))

    def test_liquidity_averages_daily_dollars_not_latest_price_times_average_volume(self):
        days = ('2026-11-09', '2026-11-10')
        bars = {('AAA', days[0]): Bar('AAA', days[0], D(10), D(10), D(100)),
                ('AAA', days[1]): Bar('AAA', days[1], D(20), D(20), D(300))}
        self.assertEqual(average_dollar_volume(bars, 'AAA', days, 1, 2), D(3500))
        self.assertIsNone(average_dollar_volume(bars, 'AAA', days, 0, 2))
        del bars['AAA', days[0]]
        self.assertIsNone(average_dollar_volume(bars, 'AAA', days, 1, 2))

    def test_uncompleted_or_nonregular_bars_are_not_liquidity(self):
        days = ('2026-11-09',)
        for field in ('completed', 'regular_session'):
            row = Bar('AAA', days[0], D(10), D(10), D(100), **{field: False})
            self.assertIsNone(average_dollar_volume({('AAA', days[0]): row}, 'AAA', days, 0, 1))

    def test_temporal_diagnostics_measure_observed_episodes_and_censor_incomplete_edges(self):
        states={'a':['Lagging','Improving','Improving','Leading','Fading','Fading','Lagging','Improving'],
                'b':['Improving','Leading','Fading','Leading','Leading','Lagging','Lagging','Lagging']}
        changes={key:[D(9),D(11),D(9),D(11),D(-9),D(-11),D(-9),D(11)] for key in states}
        strengths={key:[D(40)]*len(rows) for key,rows in states.items()}
        result=transition_diagnostics(states,changes,strengths,D(10))
        self.assertEqual(result['improving']['completed_episodes'],1)
        self.assertEqual(result['improving']['left_censored'],1)
        self.assertEqual(result['improving']['right_censored'],1)
        self.assertEqual(result['improving']['next_session_persistence'],round(1/3,6))
        self.assertEqual(result['improving']['sessions_to_direct_leading']['mean'],2)
        self.assertEqual(result['fading']['direct_to_lagging_rate'],.5)
        self.assertEqual(result['fading']['direct_to_leading_rate'],.5)
        self.assertEqual(result['threshold_neighborhood']['same_structural_zone_pairs'],14)

    def test_missing_state_censors_episodes_and_structural_crossings_do_not_count_threshold_churn(self):
        result=transition_diagnostics({'a':['Lagging','Improving','Unavailable','Fading','Leading']},
            {'a':[None,D(10),None,D(-10),D(-9)]},
            {'a':[D(40),D(40),None,D(60),D(40)]},D(10))
        self.assertEqual(result['improving']['right_censored'],1)
        self.assertEqual(result['fading']['left_censored'],1)
        self.assertEqual(result['improving']['completed_episodes'],0)
        self.assertEqual(result['threshold_neighborhood']['same_structural_zone_pairs'],0)
        edge=transition_diagnostics({'a':['Improving','Improving']},
            {'a':[D(10),D(10)]},{'a':[D(40),D(40)]},D(10))['improving']
        self.assertEqual((edge['left_censored'],edge['right_censored'],edge['completed_episodes']),(1,1,0))

    def test_full_diagnostic_is_deterministic_and_retention_is_explicitly_an_invariant(self):
        config, bars, sessions, target, _, _ = fixture()
        members = {theme.theme_id: config.members_on(theme.theme_id, target) for theme in config.themes}
        result = diagnose(config, bars, sessions, members, {'fixture': True})
        self.assertEqual(result, diagnose(config, bars, sessions, members, {'fixture': True}))
        self.assertEqual(len(result['state_candidates']), 12)
        self.assertEqual(len(result['liquidity_candidates']), 8)
        self.assertEqual(len(result['recent_change_diagnostics']),6)
        self.assertIn('definition invariant',result['retention_interpretation'])
        self.assertTrue(result['scope']['no_accounting_writes'])
        for row in result['state_candidates']:
            if not row['breadth_gate']:
                self.assertEqual(row['structural_leader_retention']['minimum'], 1)
        self.assertEqual(result['breadth_sample_sensitivity']['small']['selected_state_or_ranking_influence'], 0)

    def test_changed_horizon_population_censors_temporal_evidence_and_uses_structural_fallback(self):
        from test_research_v2_comparison import fixture, DAYS
        config, bars = fixture(third=True)
        # At t=68, C has no 63-session metric at either date, but its 1M
        # population changes. The combined scored population alone misses this.
        for member in config.memberships:
            if member.theme_id == 'c':
                for index in (0, 5, 47):
                    del bars[member.ticker, DAYS[index]]
        sessions = DAYS[:69]
        members = {theme.theme_id: config.members_on(theme.theme_id, sessions[-1]) for theme in config.themes}
        result = diagnose(config, bars, sessions, members, {'fixture': True})
        availability = result['comparison_availability']
        self.assertEqual(availability['eligible_five_session_pairs'], 1)
        self.assertEqual(availability['available_session_comparisons'], 0)
        self.assertEqual(availability['reason_counts'], {'insufficient_completed_history': 5, 'ranked_universe_changed': 1})
        for row in result['selected_session_counts']:
            self.assertFalse(row['comparison_available'])
            self.assertNotIn('Improving', row['states'])
            self.assertNotIn('Fading', row['states'])
        for model in result['state_candidates']:
            self.assertIsNone(model['state_changes_per_session'])
            self.assertEqual(model['state_churn_comparable_session_pairs'], 0)
        for model in result['recent_change_diagnostics']:
            self.assertEqual(model['improving']['completed_episodes'], 0)
            self.assertEqual(model['improving']['next_session_pairs'], 0)
            self.assertEqual(model['fading']['completed_episodes'], 0)
        longer = diagnose(config, bars, DAYS, members, {'fixture': True})
        available = [row['comparison_available'] for row in longer['selected_session_counts'] if row['side'] == 'long']
        self.assertTrue(any(available))
        self.assertTrue(any(not value for value in available))
        expected = sum(a and b for a, b in zip(available, available[1:]))
        self.assertTrue(all(model['state_churn_comparable_session_pairs'] == expected
                            for model in longer['state_candidates']))


if __name__ == '__main__':
    unittest.main()
