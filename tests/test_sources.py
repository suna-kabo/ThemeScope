import unittest
from unittest.mock import patch
from src.themescope import sources


class SourceFallbackTests(unittest.TestCase):
    def tearDown(self):
        sources._YAHOO_BLOCKED_HOSTS.clear()

    def test_rate_limited_hosts_are_not_hammered_for_other_symbols(self):
        with patch.object(sources, 'request_json', side_effect=sources.RateLimited('HTTP 429')) as request:
            for ticker in ['SPY', 'QQQ', 'NVDA']:
                with self.assertRaises(RuntimeError):
                    sources.fetch_yahoo_chart(ticker)
            self.assertEqual(request.call_count, 2)

    def test_fallback_host_retains_adjustment_fields(self):
        response = {'chart': {'result': [{'meta': {'symbol': 'SPY'}, 'timestamp': [1700000000], 'indicators': {'quote': [{'close': [100], 'volume': [200]}], 'adjclose': [{'adjclose': [99]}]}, 'events': {'splits': {'x': {'numerator':2,'denominator':1}}}}]}}
        with patch.object(sources, 'request_json', side_effect=[sources.RateLimited('HTTP 429'), response]):
            chart = sources.fetch_yahoo_chart('SPY')
        self.assertIn('query2.finance.yahoo.com', chart['url'])
        self.assertEqual(chart['observations'][0]['adj_close'], 99)
        self.assertEqual(chart['observations'][0]['close'], 100)
        self.assertTrue(chart['events']['splits'])

if __name__ == '__main__':
    unittest.main()
