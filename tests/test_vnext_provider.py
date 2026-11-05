import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime,timezone
from dataclasses import replace
from unittest.mock import patch
from src.themescope.providers.base import Schedule,FixtureProvider,ProviderError
from src.themescope.providers.alpaca import AlpacaMarketDataProvider,URL
from src.themescope.providers.cache import prepare,publish_prepared
from src.themescope.storage import Store
from test_vnext_calculations import bar

DATES=('2024-01-02','2024-01-03','2024-01-04','2024-01-05')
def schedule():return Schedule([{'session':s,'close':s+'T21:00:00+00:00'} for s in DATES],now=lambda:datetime(2024,1,6,tzinfo=timezone.utc))
def row(s='2024-01-05',c=100):return {'t':s+'T05:00:00Z','c':c,'v':2000000}

class ProviderTests(unittest.TestCase):
    def test_sip_raw_pair_pagination_and_volume(self):
        calls=[]
        def send(p,h):
            calls.append(p)
            if 'page_token' not in p:return 200,{'bars':{'A':[row(c=50 if p['adjustment']!='raw' else 100)]},'next_page_token':'next'},{}
            return 200,{'bars':{'B':[row()]},'next_page_token':None},{}
        p=AlpacaMarketDataProvider('fake','fake',schedule(),send=send)
        batch=p.get_daily_bars(('A','B'),DATES[-1],DATES[-1])
        self.assertEqual(batch.pages,4)
        self.assertEqual((batch.bars[0].adjusted_close,batch.bars[0].close,batch.bars[0].volume),(50,100,2000000))
        self.assertTrue(all(x['feed']=='sip' and x['timeframe']=='1Day' for x in calls))
        self.assertEqual({x['adjustment'] for x in calls},{'split,spin-off','raw'})
        self.assertEqual(URL,'https://data.alpaca.markets/v2/stocks/bars')

    def test_auth_subscription_errors_never_retry_or_leak(self):
        for status,code in [(401,'authentication_401'),(403,'sip_access_403'),(422,'request_or_subscription_422')]:
            calls=[]
            def send(p,h):calls.append(p);return status,{'secret':'never print'},{}
            p=AlpacaMarketDataProvider('fake','fake',schedule(),send=send)
            with self.assertRaisesRegex(ProviderError,code):p.get_daily_bars(('A',),DATES[-1],DATES[-1])
            self.assertEqual(len(calls),1)

    def test_rate_transient_retry_bounds_and_malformed_failures(self):
        delays=[];statuses=iter([429,503,200,200])
        def send(p,h):return next(statuses),{'bars':{'A':[row()]}},{'Retry-After':'3'}
        p=AlpacaMarketDataProvider('fake','fake',schedule(),send=send,sleep=delays.append)
        self.assertEqual(len(p.get_daily_bars(('A',),DATES[-1],DATES[-1]).bars),1)
        self.assertEqual(delays,[3,3])
        for payload in ({}, {'bars':[]},{'bars':{'A':[{'bad':True}]}},{'bars':{'BAD':[row()]}},
                        {'bars':{'A':[row(),row()]}},{'bars':{'A':[row(c='NaN')]}}):
            p=AlpacaMarketDataProvider('fake','fake',schedule(),send=lambda p,h:(200,payload,{}))
            with self.assertRaises(ProviderError):p.get_daily_bars(('A',),DATES[-1],DATES[-1])
        p=AlpacaMarketDataProvider('fake','fake',schedule(),send=lambda p,h:(429,{},{}),sleep=lambda s:None,retries=1)
        with self.assertRaisesRegex(ProviderError,'rate_limit_exhausted'):p.get_daily_bars(('A',),DATES[-1],DATES[-1])
        p=AlpacaMarketDataProvider('fake','fake',schedule(),send=lambda p,h:(200,{'bars':{},'next_page_token':'repeat'},{}))
        with self.assertRaisesRegex(ProviderError,'pagination'):p.get_daily_bars(('A',),DATES[-1],DATES[-1])

    def test_delay_half_day_and_weekend(self):
        s=Schedule([{'session':'2024-11-29','close':'2024-11-29T18:00:00+00:00'}],now=lambda:datetime(2024,11,29,18,19,tzinfo=timezone.utc))
        with self.assertRaises(ProviderError):s.require('2024-11-29')
        s.now=lambda:datetime(2024,11,29,18,20,tzinfo=timezone.utc)
        self.assertEqual(s.latest(),'2024-11-29')
        with self.assertRaises(ProviderError):s.require('2024-11-30')

    def test_local_poc_mocked_no_credentials_required(self):
        from scripts.test_alpaca_access import main
        from src.themescope.providers.base import Batch
        class Fake:
            def __init__(self,*a,**kw):pass
            def get_daily_bars(self,symbols,start,end):return Batch('fixture',tuple(bar(s,end) for s in symbols),6)
        with patch('builtins.print') as output:
            self.assertEqual(main(['--session','2024-01-05'],factory=Fake),0)
            self.assertIn('"feed": "sip"',output.call_args[0][0])

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=Store(Path(self.temp.name)/'cache.sqlite');self.addCleanup(self.store.close)
        self.provider=FixtureProvider([bar(s,d) for s in ('A','B') for d in DATES],schedule())
    def save(self,plan,day):publish_prepared(self.store,plan,day,'themescope-vnext-1','fixture',{'session':day},('A','B'))

    def test_cold_warm_no_duplicate_observations_replay_and_provenance(self):
        cold=prepare(self.store,self.provider,('A','B'),DATES[:3]);self.save(cold,DATES[2])
        self.assertEqual((cold.requests,cold.fetched),(1,6))
        warm=prepare(self.store,self.provider,('A','B'),DATES,repair_sessions=1);self.save(warm,DATES[3])
        self.assertEqual((warm.requests,warm.fetched),(2,4))
        self.assertEqual(self.store.connection.execute('SELECT count(*) FROM observations').fetchone()[0],8)
        again=prepare(self.store,self.provider,('A','B'),DATES,repair_sessions=1);self.save(again,DATES[3])
        self.assertEqual(self.store.connection.execute('SELECT count(*) FROM observations').fetchone()[0],8)
        replay=prepare(self.store,self.provider,('A','B'),DATES[:3]);self.save(replay,DATES[2])
        self.assertEqual(self.store.active(),{'session':DATES[3]})
        self.assertTrue(self.store.connection.execute('SELECT observation_id FROM daily_bars LIMIT 1').fetchone()[0])
        self.store.connection.execute('DELETE FROM bar_cache WHERE ticker=? AND session=?',('A',DATES[1]))
        self.provider.calls.clear()
        prepare(self.store,self.provider,('A','B'),DATES,repair_sessions=1)
        self.assertIn((('A',),DATES[1],DATES[1]),self.provider.calls)
        self.assertNotIn((('A',),DATES[1],DATES[-1]),self.provider.calls)


    def test_adjustment_reseed_versions_and_missing_target_preserve_state(self):
        self.save(prepare(self.store,self.provider,('A','B'),DATES),DATES[-1])
        original=self.store.connection.execute('SELECT observation_id FROM daily_bars WHERE ticker="A" LIMIT 1').fetchone()[0]
        self.provider.bars=tuple(replace(b,adjusted_close=b.adjusted_close/2) if b.ticker=='A' else b for b in self.provider.bars)
        repaired=prepare(self.store,self.provider,('A','B'),DATES,repair_sessions=1)
        self.assertEqual(repaired.requests,3);self.save(repaired,DATES[-1])
        self.assertEqual(self.store.connection.execute('SELECT count(*) FROM observations').fetchone()[0],12)
        self.assertIsNotNone(self.store.connection.execute('SELECT id FROM observations WHERE id=?',(original,)).fetchone())
        self.provider.bars=tuple(b for b in self.provider.bars if not(b.ticker=='A' and b.session==DATES[-1]))
        # Current target must be fetched, never silently substituted by its cached value.
        with self.assertRaises(ProviderError):prepare(self.store,self.provider,('A','B'),DATES,full_repair=True)
        self.assertEqual(self.store.active(),{'session':DATES[-1]})

    def test_schema1_migration_preserves_old_runs_and_deduplicates(self):
        from src.themescope.storage import canonical
        path=Path(self.temp.name)/'old.sqlite'
        # The initializer still creates exactly the schema1 DDL before migration.
        with patch('src.themescope.storage.observations.migrate'):
            old=Store(path)
        db=old.connection
        for i,day in enumerate(DATES[:2],1):
            db.execute("INSERT INTO refresh_run VALUES(?,?,?,?,?,?)",(i,day,'themescope-vnext-1','fixture','success',None))
            for d in DATES[:i]:db.execute('INSERT INTO daily_bars VALUES(?,?,?,?)',(i,'A',d,canonical(bar('A',d))))
        db.execute('INSERT INTO publication VALUES(1,?,?)',(2,canonical({'session':DATES[1]})))
        old.close()
        new=Store(path)
        try:
            self.assertEqual(new.connection.execute('PRAGMA user_version').fetchone()[0],2)
            self.assertEqual(new.connection.execute('SELECT count(*) FROM observations').fetchone()[0],2)
            self.assertEqual(new.connection.execute('SELECT count(*) FROM daily_bars').fetchone()[0],3)
            self.assertEqual(new.active(),{'session':DATES[1]})
            self.assertIn('unknown-source',new.connection.execute('SELECT identity FROM observations LIMIT 1').fetchone()[0])
        finally:new.close()

    def test_failure_after_cache_write_rolls_back_observations(self):
        plan=prepare(self.store,self.provider,('A','B'),DATES)
        with self.assertRaises(ValueError):
            publish_prepared(self.store,plan,DATES[-1],'themescope-vnext-1','fixture',{},('A','B','MISSING'))
        self.assertEqual(self.store.connection.execute('SELECT count(*) FROM observations').fetchone()[0],0)
        self.assertIsNone(self.store.active())

class AdditionalProviderTests(unittest.TestCase):
    def test_network_exhaustion_and_raw_adjusted_mismatch(self):
        def broken(p,h):raise TimeoutError('must never echo secret details')
        p=AlpacaMarketDataProvider('fake','fake',schedule(),send=broken,sleep=lambda s:None,retries=1)
        with self.assertRaisesRegex(ProviderError,'^transient_exhausted$'):p.get_daily_bars(('A',),DATES[-1],DATES[-1])
        def mismatch(p,h):return 200,{'bars':{'A':[row()]} if p['adjustment']=='raw' else {}},{}
        p=AlpacaMarketDataProvider('fake','fake',schedule(),send=mismatch)
        with self.assertRaisesRegex(ProviderError,'raw_adjusted_mismatch'):p.get_daily_bars(('A',),DATES[-1],DATES[-1])

    def test_request_end_is_delayed_and_poc_failure_safe(self):
        from scripts.test_alpaca_access import main
        calls=[]
        p=AlpacaMarketDataProvider('fake','fake',schedule(),send=lambda p,h:(calls.append(p) or (200,{'bars':{'A':[row()]}},{})))
        p.get_daily_bars(('A',),DATES[-1],DATES[-1])
        self.assertLessEqual(datetime.fromisoformat(calls[0]['end']),datetime(2024,1,5,23,40,tzinfo=timezone.utc))
        with patch.dict('os.environ',{},clear=True),patch('builtins.print') as output:
            self.assertEqual(main(['--session','2024-01-05']),1)
            self.assertIn('credentials_missing',output.call_args[0][0])
