import unittest
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal as D, localcontext, Inexact, ROUND_DOWN
from pathlib import Path
from src.themescope.domain import load_configuration
from src.themescope.themes.calculations import (Bar, bar_map, price_return, aggregate, median,
    percentiles, theme_scores, relative, breadth, benchmarks)

# Explicit synthetic completed-session calendar; no dependency on wall clock.
SESSIONS = tuple((date(2024, 1, 1)+timedelta(days=i)).isoformat() for i in range(100)
                 if (date(2024, 1, 1)+timedelta(days=i)).weekday() < 5)


def bar(symbol, session, price=100, volume=2000000, **kwargs):
    return Bar(symbol, session, D(str(price)), D(str(price)), D(str(volume)), **kwargs)


class CalculationTests(unittest.TestCase):
    def test_exact_return_endpoints_missing_does_not_compress_calendar(self):
        data = bar_map([bar('A', SESSIONS[i], 100+i) for i in range(64) if i != 5])
        self.assertEqual(price_return(data, 'A', SESSIONS, SESSIONS[63], 21), D('0.147887323943661971830985915492958'))
        self.assertEqual(price_return(data, 'A', SESSIONS, SESSIONS[63], 63), D('.63'))
        self.assertIsNone(price_return(data, 'A', SESSIONS, SESSIONS[26], 21))
        self.assertIsNone(price_return(data, 'A', SESSIONS, SESSIONS[20], 21))
        self.assertIsNone(price_return(data, 'A', SESSIONS, SESSIONS[64], 21))

    def test_adjusted_split_and_spinoff_no_total_return(self):
        # 2:1 split: actual pre-event close 100; adjusted 50 -> 51 means +2%, not -49%.
        for adjusted, raw, end, expected in [(50, 100, 51, '.02'), (80, 100, 82, '.025')]:
            data = bar_map([Bar('A', SESSIONS[0], adjusted, raw, 2000000), bar('A', SESSIONS[21], end)])
            self.assertEqual(price_return(data, 'A', SESSIONS, SESSIONS[21], 21), D(expected))
        with self.assertRaises(ValueError):
            bar('A', SESSIONS[0], adjustment='all')
        # Cash-dividend ex-date price decline remains a price decline.
        data = bar_map([bar('A', SESSIONS[0], 100), bar('A', SESSIONS[21], 99)])
        self.assertEqual(price_return(data, 'A', SESSIONS, SESSIONS[21], 21), D('-.01'))

    def test_invalid_duplicate_and_incomplete_bars(self):
        for value in (0, -1, 'NaN', 'Infinity', True):
            with self.assertRaises(ValueError):
                Bar('A', SESSIONS[0], value, 100, 100)
        with self.assertRaises(ValueError):
            bar_map([bar('A', SESSIONS[0])]*2)
        data = bar_map([bar('A', SESSIONS[0]), bar('A', SESSIONS[21], completed=False)])
        self.assertIsNone(price_return(data, 'A', SESSIONS, SESSIONS[21], 21))
        with self.assertRaises(ValueError):
            price_return(data, 'A', SESSIONS[::-1], SESSIONS[21], 21)

    def test_median_and_exact_coverage_boundaries(self):
        self.assertEqual(median([D(3), D(1), D(2)]), 2)
        self.assertEqual(median([D(4), D(1), D(3), D(2)]), D('2.5'))
        names = tuple('ABCDEFGHIJ')
        values = {s: D(i) for i,s in enumerate(names[:8])}
        result = aggregate(names, values)
        self.assertEqual((result.value, result.valid, result.coverage), (D('3.5'), 8, D('.8')))
        self.assertIsNone(aggregate(names, {s:v for s,v in values.items() if s!='A'}).value)
        self.assertEqual(aggregate(names[:5], values).value, 2)
        self.assertIsNone(aggregate(names[:5], {s:1 for s in names[:4]}).value)
        self.assertEqual(aggregate(names[:6], {s:1 for s in names[:5]}).value, 1)
        with self.assertRaises(ValueError):
            aggregate(('A','A'), {'A':1})

    def test_tied_percentiles_singleton_and_per_horizon_scores(self):
        self.assertEqual(percentiles({'a':1,'b':2,'c':2,'d':3,'e':None}),
                         {'a':D(0),'b':D(50),'c':D(50),'d':D(100),'e':None})
        self.assertEqual(percentiles({'b':1,'a':1}), {'a':D(50),'b':D(50)})
        self.assertEqual(percentiles({'a':1,'b':None}), {'a':None,'b':None})
        metric = lambda x: aggregate('ABCDE', dict.fromkeys('ABCDE', x))
        # A missing 3M does not remove its valid 1M from that horizon's cross-section.
        metrics = {'a':(metric(1),metric(3)), 'b':(metric(2),metric(1)), 'c':(metric(3),metric(None))}
        self.assertEqual(theme_scores(metrics), {'a':D(40),'b':D(30),'c':None})

    def test_loo_four_peers_coverage_zero_w_and_independent_memberships(self):
        r = dict(zip('ABCDEF', map(D, ('10','1','2','3','4','5'))))
        result = relative('A', 'ABCDE', r, r)
        self.assertEqual((result.peer1.value, result.w), (D('2.5'),D('7.5')))
        self.assertEqual(relative('A','ABCDEF',{k:v for k,v in r.items() if k!='F'},r).peer1.coverage,D('.8'))
        self.assertIsNone(relative('A','ABCDE',{k:v for k,v in r.items() if k!='E'},r).w)
        self.assertIsNone(relative('A','ABCDEFG',{k:v for k,v in r.items() if k!='F'},r).w)
        equal=dict.fromkeys('ABCDE',D(1))
        self.assertEqual(relative('A','ABCDE',equal,equal).w,0)
        negative = dict(equal,A=D(0))
        self.assertLess(relative('A','ABCDE',negative,negative).w,0)
        self.assertNotEqual(relative('A','ABCDE',r,r).w,relative('A','ACDEF',r,r).w)
        self.assertIsNone(relative('A','ABCDE',dict(equal,A=None),equal).w)
        with self.assertRaises(ValueError):
            relative('A','AABCDE',r,r)

    def test_context_independence_breadth_and_pending_memberships(self):
        values = {'a':1,'b':2,'c':3,'d':4}
        expected=percentiles(values)
        with localcontext() as context:
            context.prec=6
            context.rounding=ROUND_DOWN
            context.traps[Inexact]=True
            self.assertEqual(percentiles(values),expected)
        self.assertEqual(breadth('ABCDE',dict.fromkeys('ABCDE',100),dict.fromkeys('ABCDE',99)).value,100)
        self.assertIsNone(breadth('ABCDEF',dict.fromkeys('ABCD',100),dict.fromkeys('ABCD',99)).value)
        config=load_configuration(Path(__file__).resolve().parents[1])
        metrics,scores,returns=benchmarks(config,{},SESSIONS,SESSIONS[63])
        self.assertTrue(all(v is None for v in scores.values()))
        self.assertTrue(all(m[0].configured==0 for m in metrics.values()))
