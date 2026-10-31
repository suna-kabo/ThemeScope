"""Production-path regressions for the final manual release audit."""
import unittest
from pathlib import Path
from src.themescope.manual_csv import breadth
from src.themescope.tradingview import attach, load_mapping, resolve, theme_symbols
from src.themescope.approved_rules import canonical_decision

ROOT = Path(__file__).resolve().parents[1]

class ExportTests(unittest.TestCase):
    def test_evidenced_instrument_prefixes(self):
        m = load_mapping(ROOT)
        self.assertEqual(resolve('SPY', m), 'AMEX:SPY')
        self.assertEqual(resolve('XLC', m), 'AMEX:XLC')
        self.assertEqual(resolve('AAPL', m), 'NASDAQ:AAPL')
        self.assertEqual(resolve('JPM', m), 'NYSE:JPM')
        self.assertEqual(resolve('ARKG', m), 'CBOE:ARKG')
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            resolve('UNKNOWN', m)

    def test_anchor_twenty_stocks_and_etf_only(self):
        t = {'id':'t','name':'Test','anchor':'ETF','tradingview_symbol':'AMEX:ETF','selected':[
            {'ticker':str(i),'tradingview_symbol':'NYSE:'+str(i)} for i in range(20)]}
        self.assertEqual(len(theme_symbols(t)), 21)
        self.assertEqual(theme_symbols(t)[0], 'AMEX:ETF')
        self.assertEqual(theme_symbols({**t,'selected':[]}), ['AMEX:ETF'])
        with self.assertRaises(ValueError): theme_symbols({**t,'selected':[{}]})

    def test_punctuation_exception_chart_export_consistency(self):
        mapping={'BRK-B':{'status':'verified','symbol':'NYSE:BRK.B'},'ETF':{'status':'verified','symbol':'AMEX:ETF'}}
        t={'id':'x','anchor':'ETF','selected':[{'ticker':'BRK-B'}]}
        attach({'themes':[t],'context':[]},mapping)
        self.assertEqual(theme_symbols(t), ['AMEX:ETF','NYSE:BRK.B'])
        self.assertTrue(t['selected'][0]['chart_url'].endswith('NYSE%3ABRK.B'))

    def test_missing_member_stays_denominator(self):
        rows=[{'symbol':str(i),'price':2,'ema21':1,'ema50':1} for i in range(8)]
        self.assertEqual(breadth(rows+[{},{}],minimum=8)['21']['value'],100)
        self.assertIsNone(breadth(rows+[{},{},{}],minimum=8)['21']['value'])

    def test_mixed_prices_missing_breadth_explanation(self):
        d=canonical_decision('s','t',[{'ticker':t,'price_state':'Mixed'} for t in ('SPY','QQQ')],[],'Unclassified',None)
        self.assertEqual(d['matrix_rule_id'],'required-input-unavailable')
        self.assertIn('Combined Breadth State is unavailable',d['reason'])
