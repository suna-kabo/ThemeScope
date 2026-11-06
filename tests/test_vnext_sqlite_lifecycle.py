"""SQLite startup, real commit locks and HTTP polling (also run natively on Windows).

All runtime files and bars are temporary/synthetic. No provider credentials needed.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from decimal import Decimal
from pathlib import Path
import json,sqlite3,subprocess,sys,tempfile,threading,time,unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from src.themescope import storage
from src.themescope.storage import Store,Refresh,canonical,BUSY_TIMEOUT_SECONDS,is_busy
from src.themescope.storage import observations
from src.themescope.local import service as local
from src.themescope.local.service import fixture_service
from src.themescope.local.app import create_app
from src.themescope.local_refresh_lock import RefreshBusy
from test_vnext_calculations import bar

ROOT=Path(__file__).resolve().parents[1]

class SQLiteLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='ThemeScope SQLite # ')
        self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)

    def valid_schema(self,path):
        db=sqlite3.connect(path,timeout=5)
        try:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],2)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(),[('ok',)])
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('SELECT version FROM schema_version ORDER BY version').fetchall(),[(1,),(2,)])
            tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            self.assertEqual(tables,{'schema_version','refresh_run','instruments','daily_bars',
                                    'membership_reviews','market_roster','theme_index','theme_snapshot',
                                    'stock_theme_snapshot','market_snapshot','earnings_event','publication',
                                    'observations','bar_cache'})
        finally:db.close()

    def test_fresh_database_initialization_race_before_polling(self):
        created=threading.Event();release=threading.Event();ready=threading.Barrier(8)
        competing=threading.Event();lock=threading.Lock();attempts=[];creates=[]
        connect=sqlite3.connect
        class InitializerConnection(sqlite3.Connection):
            def execute(db,sql,*args):
                if sql=='BEGIN IMMEDIATE':
                    with lock:
                        attempts.append(1)
                        if len(attempts)>=2:competing.set()
                return super().execute(sql,*args)
        def observed(*args,**kwargs):return connect(*args,**kwargs,factory=InitializerConnection)
        create=storage._create_schema1
        def paused(db):
            creates.append(1);create(db);created.set()
            self.assertTrue(release.wait(4),'initializer release timed out')
        def open_and_poll():
            ready.wait(4)
            service=fixture_service(self.root)
            # Constructor must finish before any HTTP/status caller can obtain service.
            self.assertEqual(service.status()['state'],'idle')
            self.assertIsNone(service.snapshot())
            return service
        with patch.object(storage.sqlite3,'connect',observed),patch.object(storage,'_create_schema1',paused),ThreadPoolExecutor(max_workers=8) as pool:
            futures=[pool.submit(open_and_poll) for _ in range(8)]
            try:
                self.assertTrue(created.wait(4));self.assertTrue(competing.wait(3))
                self.assertTrue(all(not f.done() for f in futures))
            finally:release.set()
            services=[f.result(6) for f in futures]
        self.assertEqual(creates,[1])
        self.valid_schema(services[0].db)
        self.assertTrue(all(s.status()['last_successful_session'] is None for s in services))

    def schema1_service(self):
        # Preserve the exact original schema-1 DDL and seed a committed publication.
        with patch.object(observations,'migrate'):
            service=fixture_service(self.root)
        db=sqlite3.connect(service.db,isolation_level=None)
        payload={'session':'2024-01-03','exports':{'combined':'SYNTHETIC:OLD\n','individual':{}}}
        try:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],1)
            db.execute("INSERT INTO refresh_run VALUES(1,'2024-01-03','themescope-vnext-1','fixture','success',NULL)")
            db.execute('INSERT INTO daily_bars VALUES(?,?,?,?)',(1,'A','2024-01-03',canonical(bar('A','2024-01-03'))))
            db.execute('INSERT INTO publication VALUES(1,1,?)',(canonical(payload),))
        finally:db.close()
        self.assertEqual(service.snapshot(),payload)
        return service,payload

    def test_schema1_migration_race_with_existing_reader_and_second_initializer(self):
        service,prior=self.schema1_service()
        migrated=threading.Event();release=threading.Event();attempt=threading.Event();calls=[]
        begins=[];guard=threading.Lock();connect=sqlite3.connect
        class MigrationConnection(sqlite3.Connection):
            def execute(db,sql,*args):
                if sql=='BEGIN IMMEDIATE':
                    with guard:
                        begins.append(1)
                        if len(begins)==2:attempt.set()
                return super().execute(sql,*args)
        def observed(*args,**kwargs):return connect(*args,**kwargs,factory=MigrationConnection)
        migrate=observations.migrate
        def paused(db,convert):
            calls.append(1);migrate(db,convert);migrated.set()
            self.assertTrue(release.wait(4))
        def open_and_poll():
            other=fixture_service(self.root)
            return other.status(),other.snapshot()
        def migrate_store():
            store=Store(service.db)
            try:return store.active()
            finally:store.close()
        with patch.object(storage.sqlite3,'connect',observed),patch.object(observations,'migrate',paused),ThreadPoolExecutor(max_workers=2) as pool:
            first=pool.submit(migrate_store)
            second=None
            try:
                self.assertTrue(migrated.wait(4))
                second=pool.submit(open_and_poll);self.assertTrue(attempt.wait(2))
                # Schema DDL and rewritten bars are uncommitted; publication stays old.
                for _ in range(3):
                    self.assertEqual(service.status()['last_successful_session'],prior['session'])
                    self.assertEqual(service.snapshot(),prior)
            finally:release.set()
            self.assertEqual(first.result(6),prior)
            state,snapshot=second.result(6)
        self.assertEqual(snapshot,prior);self.assertEqual(state['last_successful_session'],prior['session'])
        self.assertEqual(calls,[1]);self.valid_schema(service.db)
        db=Store(service.db)
        try:
            self.assertEqual(db.connection.execute('SELECT count(*) FROM daily_bars').fetchone()[0],1)
            self.assertEqual(db.connection.execute('SELECT count(*) FROM observations').fetchone()[0],1)
            self.assertIn('unknown-source',db.connection.execute('SELECT identity FROM observations').fetchone()[0])
        finally:db.close()

    def test_initialization_migration_failure_rolls_back_and_can_retry(self):
        for fresh in (True,False):
            with self.subTest(fresh=fresh):
                path=self.root/('fresh.sqlite' if fresh else 'old.sqlite')
                if not fresh:
                    with patch.object(observations,'migrate'):
                        store=Store(path);store.close()
                def broken(db,convert):
                    db.execute('ALTER TABLE daily_bars RENAME TO partially_migrated')
                    raise RuntimeError('Synthetic migration interruption')
                with patch.object(observations,'migrate',broken):
                    with self.assertRaisesRegex(RuntimeError,'interruption'):Store(path)
                db=sqlite3.connect(path)
                try:
                    self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],0 if fresh else 1)
                    self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE name='partially_migrated'").fetchall(),[])
                    if fresh:self.assertEqual(db.execute("SELECT name FROM sqlite_master").fetchall(),[])
                    else:self.assertTrue(db.execute("SELECT name FROM sqlite_master WHERE name='daily_bars'").fetchone())
                finally:db.close()
                store=Store(path);store.close();self.valid_schema(path)

    def test_default_busy_timeout_and_read_only_path_without_schema_work(self):
        service=fixture_service(self.root)
        self.assertEqual(BUSY_TIMEOUT_SECONDS,5.0)
        with patch.object(Store,'_initialize',side_effect=AssertionError('reader attempted schema work')):
            for _ in range(3):
                self.assertEqual(service.status()['state'],'idle');self.assertIsNone(service.snapshot())
            store=Store(service.db,read_only=True)
            try:
                self.assertEqual(store.connection.execute('PRAGMA busy_timeout').fetchone()[0],5000)
                self.assertEqual(store.connection.execute('PRAGMA journal_mode').fetchone()[0],'delete')
                with self.assertRaises(sqlite3.OperationalError) as result:
                    store.connection.execute('INSERT INTO schema_version VALUES(99)')
                self.assertEqual(result.exception.sqlite_errorcode,sqlite3.SQLITE_READONLY)
            finally:store.close()

    def client(self,service):
        client=TestClient(create_app(ROOT,service),base_url='http://127.0.0.1')
        self.addCleanup(client.close);return client

    def assert_endpoints(self,client,expected):
        for path in ('/api/status','/api/refresh/status'):
            response=client.get(path);self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['last_successful_session'],expected['session'] if expected else None)
        data=client.get('/api/dashboard-data');self.assertEqual(data.status_code,200)
        self.assertEqual(data.json(),expected)
        combined=client.get('/api/exports/combined.txt')
        self.assertEqual(combined.status_code,200 if expected else 404)
        if expected:self.assertEqual(combined.text,expected['exports']['combined'])
        theme=next(iter(expected['exports']['individual'])) if expected else 'alpha'
        individual=client.get('/api/exports/'+theme+'.txt')
        self.assertEqual(individual.status_code,200 if expected else 404)
        if expected:self.assertEqual(individual.text,expected['exports']['individual'][theme])

    def slow_refresh(self,with_prior):
        service=fixture_service(self.root);prior=None
        if with_prior:
            self.assertIsNotNone(service.refresh());prior=service.snapshot()
            self.assertIn('NASDAQ:AAA',prior['exports']['combined'])
        client=self.client(service)
        provider_in=threading.Event();provider_out=threading.Event()
        calculate_in=threading.Event();calculate_out=threading.Event()
        published_in=threading.Event();published_out=threading.Event()
        commit_in=threading.Event();read_in=threading.Event()
        factory=service.provider_factory;calculate=local.calculate_session;publish=Refresh.publish
        connect=sqlite3.connect
        def provider(schedule):
            result=factory(schedule);fetch=result.get_daily_bars
            if with_prior:
                result.bars=tuple(replace(b,volume=Decimal(1)) if b.ticker=='AAA' and b.session==result.get_latest_completed_session() else b for b in result.bars)
            def paused(*args):
                provider_in.set();self.assertTrue(provider_out.wait(4));return fetch(*args)
            result.get_daily_bars=paused;return result
        def calculation(*args,**kwargs):
            calculate_in.set();self.assertTrue(calculate_out.wait(4));return calculate(*args,**kwargs)
        def publication(writer,*args,**kwargs):
            publish(writer,*args,**kwargs)  # Pointer really changed inside uncommitted transaction.
            published_in.set();self.assertTrue(published_out.wait(4))
        class ObservedConnection(sqlite3.Connection):
            def commit(db):
                commit_in.set();return super().commit()
            def execute(db,sql,*args):
                if sql.startswith('SELECT run_id,payload FROM publication'):read_in.set()
                return super().execute(sql,*args)
        def observed(*args,**kwargs):return connect(*args,**kwargs,factory=ObservedConnection)
        held=None
        with patch.object(storage.sqlite3,'connect',observed),patch.object(local,'calculate_session',calculation),patch.object(Refresh,'publish',publication),ThreadPoolExecutor(max_workers=1) as pool:
            service.provider_factory=provider;service.start()
            try:
                self.assertTrue(provider_in.wait(4));self.assert_endpoints(client,prior)
                with self.assertRaises(RefreshBusy):service.refresh()
                with self.assertRaises(RefreshBusy):fixture_service(self.root).refresh()
                provider_out.set()
                self.assertTrue(calculate_in.wait(4));self.assert_endpoints(client,prior)
                calculate_out.set()
                self.assertTrue(published_in.wait(4));self.assert_endpoints(client,prior)
                # A real SHARED reader makes COMMIT wait for EXCLUSIVE access.
                held=connect(service.db,timeout=5,isolation_level=None)
                held.execute('BEGIN');held.execute('SELECT payload FROM publication').fetchall()
                published_out.set();self.assertTrue(commit_in.wait(3))
                # Prove the writer reached PENDING: zero-wait new reads now fail.
                probe=connect(service.db,timeout=0,isolation_level=None)
                try:
                    deadline=time.monotonic()+2
                    while True:
                        try:probe.execute('SELECT payload FROM publication').fetchall()
                        except sqlite3.OperationalError as error:
                            self.assertTrue(is_busy(error));break
                        if time.monotonic()>deadline:self.fail('writer did not enter commit lock')
                        threading.Event().wait(.001)
                finally:probe.close()
                read_in.clear();poll=pool.submit(service.status)
                self.assertTrue(read_in.wait(2));threading.Event().wait(.05)
                self.assertFalse(poll.done())
                held.rollback();held.close();held=None
                polled=poll.result(4)
                self.assertEqual(polled['snapshot_read'],'ready')
                self.assertIn(polled['state'],('running','success'))
            finally:
                provider_out.set();calculate_out.set();published_out.set()
                if held is not None:held.rollback();held.close()
                deadline=time.monotonic()+5
                while service.running and time.monotonic()<deadline:threading.Event().wait(.005)
            self.assertFalse(service.running)
        self.assertEqual(service.status()['state'],'success')
        final=service.snapshot();self.assertIsNotNone(final)
        self.assert_endpoints(client,final)
        if prior:
            self.assertNotEqual(final,prior)
            self.assertNotIn('NASDAQ:AAA',final['exports']['combined'])
        # Even failure after an attempted publication-pointer write preserves success.
        def failure(writer,*args,**kwargs):
            publish(writer,*args,**kwargs);raise RuntimeError('Synthetic failure after pointer write')
        with patch.object(Refresh,'publish',failure):self.assertIsNone(service.refresh())
        self.assertEqual(service.status()['state'],'failed')
        self.assert_endpoints(client,final);self.valid_schema(service.db)

    def test_status_dashboard_exports_during_fetch_calculation_publication_and_commit(self):
        self.slow_refresh(with_prior=True)

    def test_first_refresh_polling_has_no_fabricated_publication(self):
        self.slow_refresh(with_prior=False)

    def test_busy_deadline_returns_only_committed_cache_or_no_snapshot(self):
        for with_prior in (False,True):
            with self.subTest(with_prior=with_prior):
                service=fixture_service(self.root/str(with_prior));expected=None
                if with_prior:
                    published=service.refresh();self.assertIsNotNone(published)
                    expected=json.loads(canonical(published))  # Commit itself warms the cache, without a prior API read.
                client=self.client(service)
                writer=sqlite3.connect(service.db,isolation_level=None)
                writer.execute('BEGIN EXCLUSIVE')
                def short_store(path,**kwargs):return Store(path,timeout=.02,**kwargs)
                try:
                    # Exercise real busy errors cheaply; production default verified above.
                    with patch.object(local,'Store',short_store),self.assertLogs(local.__name__,level='WARNING'):
                        self.assert_endpoints(client,expected)
                        state=service.status()
                        self.assertEqual(state['snapshot_read'],'busy_last_committed' if with_prior else 'busy_no_snapshot')
                        if expected:
                            borrowed=service.snapshot();borrowed['exports']['combined']='MUTATED'
                            self.assertEqual(service.snapshot(),expected)
                        self.assertNotEqual(state['state'],'failed')
                finally:writer.rollback();writer.close()
                self.assertEqual(service.status()['snapshot_read'],'ready')
                self.assertEqual(service.snapshot(),expected)

    def test_non_busy_database_failures_are_not_swallowed(self):
        service=fixture_service(self.root)
        for code in (sqlite3.SQLITE_ERROR,sqlite3.SQLITE_IOERR,sqlite3.SQLITE_CORRUPT):
            error=sqlite3.OperationalError('Synthetic non-busy failure');error.sqlite_errorcode=code
            with self.subTest(code=code),patch.object(Store,'active_publication',side_effect=error):
                with self.assertRaises(sqlite3.OperationalError):service.status()

    def test_simultaneous_process_initializers(self):
        path=self.root/'process.sqlite';start=self.root/'start.txt'
        code="""from pathlib import Path
import sys,time
from src.themescope.storage import Store
while not Path(sys.argv[2]).exists():time.sleep(.005)
s=Store(sys.argv[1]);assert s.active() is None;s.close()
"""
        children=[subprocess.Popen([sys.executable,'-c',code,str(path),str(start)],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for _ in range(4)]
        try:
            start.write_text('start')
            for child in children:
                out,err=child.communicate(timeout=10)
                self.assertEqual(child.returncode,0,(out,err))
        finally:
            for child in children:
                if child.poll() is None:child.kill();child.communicate()
        self.valid_schema(path)

    def test_late_reader_cannot_regress_cache_after_new_commit(self):
        service=fixture_service(self.root)
        self.assertIsNotNone(service.refresh());prior=service.snapshot()
        read=Store.active_publication;entered=threading.Event();release=threading.Event()
        def paused(store):
            value=read(store)
            if threading.current_thread().name.startswith('old-reader'):
                entered.set();self.assertTrue(release.wait(4))
            return value
        with patch.object(Store,'active_publication',paused),ThreadPoolExecutor(max_workers=1,thread_name_prefix='old-reader') as pool:
            old=pool.submit(service.snapshot)
            try:
                self.assertTrue(entered.wait(3))
                self.assertIsNotNone(service.refresh());new=service.snapshot()
                self.assertNotEqual(new['refreshed_at'],prior['refreshed_at'])
            finally:release.set()
            self.assertEqual(old.result(4),new)
        self.assertEqual(service.snapshot(),new)

    def test_commit_failure_never_caches_uncommitted_candidate(self):
        service=fixture_service(self.root)
        self.assertIsNotNone(service.refresh());prior=service.snapshot()
        connect=sqlite3.connect
        class FailedCommit(sqlite3.Connection):
            def commit(db):
                raise sqlite3.OperationalError('Synthetic commit failure')
        def failing(*args,**kwargs):return connect(*args,**kwargs,factory=FailedCommit)
        with patch.object(storage.sqlite3,'connect',failing):
            self.assertIsNone(service.refresh())
        self.assertEqual(service.status()['state'],'failed')
        self.assertEqual(service._committed_snapshot,prior)
        self.assert_endpoints(self.client(service),prior)
        self.valid_schema(service.db)
