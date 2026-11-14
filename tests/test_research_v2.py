"""Research v2 selection and deterministic export edge cases; synthetic data only."""
from dataclasses import replace
from decimal import Decimal as D
import unittest

from src.themescope.domain import Role
from src.themescope.research.exports import Qualification as Q, exports


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


if __name__ == '__main__':
    unittest.main()
