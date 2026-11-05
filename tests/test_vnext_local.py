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

    def test_status_transient_sharing_failures_retry_closed_unique_temp_files(self):
        from src.themescope.local import service as module
        original_replace=module.os.replace
        original_temp=module.tempfile.NamedTemporaryFile
        handles=[];sources=[];delays=[]
        def temporary(*args,**kwargs):
            handle=original_temp(*args,**kwargs);handles.append(handle);return handle
        def replace(source,destination):
            self.assertTrue(handles[-1].closed)
            self.assertEqual(Path(source).parent,self.service.runtime)
            self.assertNotEqual(Path(source).name,'status.tmp')
            sources.append(Path(source))
            if len(sources)<=2:raise PermissionError('Windows sharing violation')
            return original_replace(source,destination)
        with patch.object(module.tempfile,'NamedTemporaryFile',temporary),patch.object(module.os,'replace',replace),patch.object(module.time,'sleep',delays.append):
            self.service._status(state='running',progress='Calculating market, themes and peer comparisons')
            self.assertEqual(delays,[.01,.02])
            self.assertEqual(len(sources),3)
            self.assertEqual(len(set(sources)),1)
            self.service._status(state='success',progress='Refresh complete')
        self.assertEqual(len(set(sources)),2)
        self.assertEqual(json.loads((self.service.runtime/'status.json').read_text())['state'],'success')
        self.assertEqual(self.service.status()['state'],'success')
        self.assertFalse(list(self.service.runtime.glob('status-*.tmp')))

    def test_permanent_status_replace_failure_does_not_abort_background_refresh_or_error_path(self):
        from src.themescope.local import service as module
        self.assertIsNotNone(self.service.refresh())
        old=self.service.snapshot()
        persisted=(self.service.runtime/'status.json').read_bytes()
        def finish():
            deadline=time.monotonic()+3
            while self.service.running and time.monotonic()<deadline:threading.Event().wait(.01)
            self.assertFalse(self.service.running)
        class Broken:
            def get_latest_completed_session(self):raise ProviderError('test_actual_provider_failure')
        with patch.object(module.os,'replace',side_effect=PermissionError('WinError 5')) as replace,patch.object(module.time,'sleep') as sleep,patch('threading.excepthook') as uncaught:
            self.service.start();finish()
            current=self.service.snapshot()
            self.assertNotEqual(current['refreshed_at'],old['refreshed_at'])
            self.assertEqual(self.service.status()['state'],'success')
            self.assertEqual(self.service.status()['progress'],'Refresh complete')
            store=Store(self.service.db)
            try:self.assertEqual(store.connection.execute("SELECT count(*) FROM refresh_run WHERE status='success'").fetchone()[0],2)
            finally:store.close()
            self.assertEqual((self.service.runtime/'status.json').read_bytes(),persisted)
            self.assertFalse(list(self.service.runtime.glob('status-*.tmp')))
            # A real later refresh failure must still preserve the committed snapshot.
            self.service.provider_factory=lambda _:Broken()
            self.service.start();finish()
            self.assertEqual(self.service.snapshot(),current)
            self.assertEqual(self.service.snapshot()['exports'],current['exports'])
            self.assertEqual(self.service.status()['state'],'failed')
            self.assertEqual(self.service.status()['error'],'test_actual_provider_failure')
            uncaught.assert_not_called()
            self.assertGreater(replace.call_count,0)
            self.assertEqual(replace.call_count%4,0)
            self.assertLess(replace.call_count,100)
            self.assertEqual(sleep.call_count,replace.call_count//4*3)
        self.assertFalse(list(self.service.runtime.glob('status-*.tmp')))

    def test_status_temp_creation_and_write_failures_are_nonfatal(self):
        from src.themescope.local import service as module
        with patch.object(module.tempfile,'NamedTemporaryFile',side_effect=PermissionError('directory inaccessible')):
            self.assertIsNotNone(self.service.refresh())
            self.assertEqual(self.service.status()['state'],'success')
        with patch.object(module.json,'dump',side_effect=OSError('disk full')):
            self.assertIsNotNone(self.service.refresh())
            self.assertEqual(self.service.status()['state'],'success')
        self.assertFalse(list(self.service.runtime.glob('status-*.tmp')))

    def test_status_read_falls_back_on_missing_inaccessible_and_malformed_files(self):
        self.assertEqual(self.service.status()['state'],'idle')
        path=self.service.runtime/'status.json'
        for text in ('{','[]','null','42','{}','{"state":"unknown","progress":"invalid"}',
                     '{"state":"running","progress":[]}'):
            path.write_text(text)
            self.assertEqual(self.service.status()['state'],'idle')
        path.write_text('{"state":"success","progress":"Recovered last refresh"}')
        self.assertEqual(self.service.status()['progress'],'Recovered last refresh')
        with patch.object(Path,'read_text',side_effect=PermissionError('sharing violation')):
            self.assertEqual(self.service.status()['state'],'idle')

    def test_persisted_running_status_recovers_as_interrupted_after_process_exit(self):
        path=self.service.runtime/'status.json'
        path.write_text('{"state":"running","progress":"Calculating market, themes and peer comparisons"}')
        self.assertEqual(self.service.status()['state'],'interrupted')
        from src.themescope.local_refresh_lock import RefreshLock
        with RefreshLock(self.service.lock_path):
            self.assertEqual(self.service.status()['state'],'running')

    def test_status_nontransient_replace_and_cleanup_errors_remain_auxiliary(self):
        from src.themescope.local import service as module
        with patch.object(module.os,'replace',side_effect=OSError('disk error')) as replace,patch.object(module.time,'sleep') as sleep:
            self.service._status(state='failed',progress='Actual refresh failed')
            self.assertEqual(replace.call_count,1)
            sleep.assert_not_called()
        with patch.object(module.os,'replace',side_effect=PermissionError()),patch.object(module.time,'sleep'),patch.object(Path,'unlink',side_effect=PermissionError('temp still locked')):
            self.service._status(state='success',progress='Snapshot committed')
        self.assertEqual(self.service.status()['state'],'success')
        for path in self.service.runtime.glob('status-*.tmp'):path.unlink()
