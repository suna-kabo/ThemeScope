"""Rule diagnostics preserve symmetry and never infer missing liquidity."""
from decimal import Decimal as D
import unittest

from scripts.research_v2_simulation import average_dollar_volume, classify, diagnose
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

    def test_full_diagnostic_is_deterministic_and_breadth_veto_loses_no_more_than_selected_model(self):
        config, bars, sessions, target, _, _ = fixture()
        members = {theme.theme_id: config.members_on(theme.theme_id, target) for theme in config.themes}
        result = diagnose(config, bars, sessions, members, {'fixture': True})
        self.assertEqual(result, diagnose(config, bars, sessions, members, {'fixture': True}))
        self.assertEqual(len(result['state_candidates']), 12)
        self.assertEqual(len(result['liquidity_candidates']), 8)
        self.assertTrue(result['scope']['no_accounting_writes'])
        for row in result['state_candidates']:
            if not row['breadth_gate']:
                self.assertEqual(row['structural_leader_retention']['minimum'], 1)
        self.assertEqual(result['breadth_sample_sensitivity']['small']['selected_state_or_ranking_influence'], 0)


if __name__ == '__main__':
    unittest.main()
