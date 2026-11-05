import json,tempfile,threading,time,unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.themescope.local.service import fixture_service,RefreshService
from src.themescope.local.app import create_app
from src.themescope.local_refresh_lock import RefreshBusy
from src.themescope.providers.base import ProviderError
from src.themescope.storage import Store
ROOT=Path(__file__).resolve().parents[1]

class LocalTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=fixture_service(self.temp.name)
    def test_full_fixture_cold_warm_and_failed_refresh_preserves_dashboard_exports(self):
        first=self.service.refresh();self.assertIsNotNone(first)
        second=self.service.refresh();self.assertIsNotNone(second)
        self.assertLess(second['performance']['fetched_observations'],first['performance']['fetched_observations'])
        prior=self.service.snapshot()
        class Broken:
            identity='fixture'
            def get_latest_completed_session(self):raise ProviderError('test_unavailable')
        self.service.provider_factory=lambda _:Broken()
        self.assertIsNone(self.service.refresh())
        self.assertEqual(self.service.snapshot(),prior)
        self.assertEqual(self.service.status()['state'],'failed')
        self.assertEqual(self.service.snapshot()['exports'],prior['exports'])

    def test_two_refreshes_cannot_prepare_or_publish_and_network_has_no_sqlite_write_lock(self):
        entered=threading.Event();release=threading.Event();factory=self.service.provider_factory
        calls=[]
        def factory_block(schedule):
            p=factory(schedule);original=p.get_daily_bars
            def fetch(*args):
                calls.append(1);entered.set();release.wait(5)
                return original(*args)
            p.get_daily_bars=fetch;return p
        self.service.provider_factory=factory_block
        worker=threading.Thread(target=self.service.refresh);worker.start()
        try:
            self.assertTrue(entered.wait(3))
            other=fixture_service(self.temp.name)
            with self.assertRaises(RefreshBusy):other.refresh()
            self.assertEqual(len(calls),1)
            store=Store(self.service.db)
            try:
                store.connection.execute('BEGIN IMMEDIATE');store.connection.rollback()
                self.assertIsNone(store.active())
            finally:store.close()
        finally:release.set();worker.join(5)
        self.assertFalse(worker.is_alive())
        self.assertIsNotNone(self.service.snapshot())
        self.assertIsNotNone(fixture_service(self.temp.name).refresh())

    def test_lock_covers_calculations_too(self):
        from src.themescope.local import service as module
        original=module.calculate_session;entered=threading.Event();release=threading.Event()
        def calculate(*a,**kw):entered.set();release.wait(5);return original(*a,**kw)
        with patch.object(module,'calculate_session',calculate):
            worker=threading.Thread(target=self.service.refresh);worker.start()
            try:
                self.assertTrue(entered.wait(3))
                with self.assertRaises(RefreshBusy):fixture_service(self.temp.name).refresh()
            finally:release.set();worker.join(5)
        self.assertIsNotNone(self.service.snapshot())

    def test_earnings_failure_does_not_fail_refresh_and_pending_launch_never_activates(self):
        def broken(*a):raise TimeoutError()
        # Adapter failures are absorbed by optional_earnings; main refresh remains successful.
        from src.themescope.providers.earnings import AlphaVantageEarnings
        p=AlphaVantageEarnings('fake',fetch=broken)
        from src.themescope.providers.earnings import optional_earnings
        with patch('src.themescope.local.service.optional_earnings',lambda _,symbols:optional_earnings(p,symbols)):
            self.assertIsNotNone(self.service.refresh())
        self.assertTrue(all(e['status']=='Unavailable' for e in self.service.snapshot()['earnings'].values()))
        from src.themescope.domain import load_configuration
        self.service.mode='live';self.service.config_factory=lambda:load_configuration(ROOT)
        # Fixture provider keeps this entirely offline; real configuration has pending launch dates.
        result=self.service.refresh()
        self.assertIsNotNone(result)
        self.assertEqual(result['relationships'],[])
        self.assertEqual(result['exports']['combined'],'')
        self.assertTrue(result['production_blockers'])

    def test_fastapi_routes_downloads_origin_guards_and_concurrent_post(self):
        client=TestClient(create_app(ROOT,self.service),base_url='http://127.0.0.1')
        self.assertEqual(client.get('/').status_code,200)
        self.assertEqual(client.get('/api/exports/combined.txt').status_code,404)
        self.assertEqual(client.post('/api/refresh',headers={'Origin':'https://evil.example'}).status_code,403)
        self.assertEqual(client.get('/api/status',headers={'Host':'evil.example'}).status_code,403)
        with patch.object(self.service,'start',side_effect=RefreshBusy()):
            self.assertEqual(client.post('/api/refresh',headers={'Origin':'http://127.0.0.1'}).status_code,409)
        self.assertIsNotNone(self.service.refresh())
        data=client.get('/api/dashboard-data').json()
        self.assertEqual(client.get('/api/exports/combined.txt').text,data['exports']['combined'])
        theme=next(iter(data['exports']['individual']))
        self.assertEqual(client.get('/api/exports/'+theme+'.txt').text,data['exports']['individual'][theme])
        self.assertEqual(client.get('/api/exports/missing.txt').status_code,404)
        self.assertIn('no-store',client.get('/api/status').headers['cache-control'])
        self.assertEqual(client.get('/app.js').status_code,200)
        self.assertEqual(client.get('/app.css').status_code,200)
        self.assertEqual(client.get('/preview.js').status_code,200)
        self.assertEqual(client.get('/api/refresh/status').status_code,200)
        self.assertEqual(client.get('/api/status').json()['completeness']['complete'],True)

    def test_real_background_refresh_and_status(self):
        client=TestClient(create_app(ROOT,self.service),base_url='http://127.0.0.1')
        self.assertEqual(client.post('/api/refresh',headers={'Origin':'http://127.0.0.1'}).status_code,202)
        deadline=time.monotonic()+3
        while self.service.running and time.monotonic()<deadline:time.sleep(.01)
        self.assertFalse(self.service.running)
        self.assertEqual(client.get('/api/status').json()['state'],'success')

    def ready_live_configuration(self):
        from dataclasses import replace
        from scripts.vnext_fixture_report import fixture
        config,_,sessions,_,_,mapping=fixture()
        # Synthetic dates only; no launch/evidence fields in repository config change.
        config=replace(config,methodology=dict(config.methodology,production_enabled=True,
                        launch_rebalance_session=sessions[0]),
                       evidence_gate={'industry_rule_registry_status':'approved'})
        self.assertEqual(config.production_blockers(),[])
        self.service.mode='live';self.service.config_factory=lambda:config
        folder=Path(self.temp.name)/'config';folder.mkdir()
        (folder/'tradingview_symbols.json').write_text(json.dumps({'symbols':mapping}))
        return config

    def test_ready_live_configuration_requires_each_effective_spy_qqq_roster(self):
        from dataclasses import replace
        config=self.ready_live_configuration()
        spy,qqq=self.service.rosters_factory()
        for rosters,missing in (((),('SPY','QQQ')),((spy,),('QQQ',)),((qqq,),('SPY',)),
                                ((replace(spy,effective_from='2025-01-01'),qqq),('SPY',)),
                                ((spy,replace(qqq,effective_to='2024-02-01')),('QQQ',))):
            with self.subTest(missing=missing,rosters=rosters):
                self.service.rosters_factory=lambda:rosters
                snapshot=self.service.refresh()
                self.assertIsNotNone(snapshot)
                expected=[f'Effective {s} constituent roster missing for {snapshot["session"]}' for s in missing]
                self.assertEqual(snapshot['production_blockers'],expected)
                self.assertEqual(self.service.snapshot()['production_blockers'],expected)
                self.assertEqual(snapshot['relationships'],[])
                self.assertTrue(all(t['priority']=='Watch' for t in snapshot['themes']))
                self.assertEqual(snapshot['exports']['combined'],'')
                self.assertEqual(snapshot['exports']['individual'],{})
                self.assertEqual(config.production_blockers(),[])
                self.assertEqual(len(config.memberships),15)

    def test_stale_effective_rosters_advisory_and_iwm_roster_never_required(self):
        from dataclasses import replace
        self.ready_live_configuration()
        rosters=tuple(replace(r,effective_from='2023-01-01') for r in self.service.rosters_factory())
        self.service.rosters_factory=lambda:rosters
        snapshot=self.service.refresh()
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot['production_blockers'],[])
        self.assertTrue(snapshot['relationships'])
        self.assertTrue(snapshot['exports']['combined'])
        for benchmark in ('SPY','QQQ'):
            self.assertTrue(snapshot['market']['context'][benchmark]['roster_warnings'])
        self.assertNotIn('breadth',snapshot['market']['context']['IWM'])
