import unittest
from src.themescope.providers.earnings import AlphaVantageEarnings,optional_earnings

class EarningsTests(unittest.TestCase):
    def test_reported_only_and_missing_event(self):
        provider=AlphaVantageEarnings('fake',fetch=lambda:'symbol,reportDate\nAAA,2026-11-10\nOTHER,2026-11-20\n')
        result=optional_earnings(provider,('AAA','BBB'))
        self.assertEqual(result['AAA']['dates'],['2026-11-10'])
        self.assertEqual(result['BBB'],{'status':'Unavailable','dates':[]})
    def test_missing_key_quota_malformed_and_provider_failure_are_unavailable(self):
        def fail():raise TimeoutError('secret should not surface')
        for p in (None,AlphaVantageEarnings(None,fetch=fail),AlphaVantageEarnings('fake',fetch=fail),
                  AlphaVantageEarnings('fake',fetch=lambda:'{"Information":"quota exceeded"}'),
                  AlphaVantageEarnings('fake',fetch=lambda:'symbol,reportDate\nAAA,not-a-date\n')):
            self.assertEqual(optional_earnings(p,('AAA',)),{'AAA':{'status':'Unavailable','dates':[]}})
