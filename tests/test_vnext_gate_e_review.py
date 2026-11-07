"""Gate E publication invariants through the real service and HTTP endpoints."""
from pathlib import Path
from unittest.mock import patch
import sqlite3,tempfile,unittest
from fastapi.testclient import TestClient
from src.themescope.local.app import create_app
from src.themescope.local.service import fixture_service
from src.themescope.providers.base import FixtureProvider,ProviderError
from src.themescope.storage import Store,Refresh
from src.themescope.themes.calculations import Bar
ROOT=Path(__file__).resolve().parents[1]


class GateEReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.service=fixture_service(self.temp.name)
        self.client=TestClient(create_app(ROOT,self.service),base_url='http://127.0.0.1')

    def assert_active(self,expected):
        self.assertEqual(self.service.snapshot(),expected)
        self.assertEqual(self.service._committed_snapshot,expected)
        self.assertEqual(self.client.get('/api/dashboard-data').json(),expected)
        self.assertEqual(self.client.get('/api/exports/combined.txt').text,expected['exports']['combined'])
        for theme,text in expected['exports']['individual'].items():
            self.assertEqual(self.client.get('/api/exports/'+theme+'.txt').text,text)

    def test_provider_calculation_and_partial_publication_failure_preserve_http_results(self):
        self.assertIsNotNone(self.service.refresh());prior=self.service.snapshot()
        real_publish=Refresh.publish
        def fail_after_pointer_write(writer,*args,**kwargs):
            real_publish(writer,*args,**kwargs)
            # A second read connection still sees only the prior committed pointer.
            other=Store(self.service.db,read_only=True)
            try:self.assertEqual(other.active(),prior)
            finally:other.close()
            raise sqlite3.IntegrityError('Synthetic failure after candidate pointer write')
        failures=(
            patch.object(FixtureProvider,'get_daily_bars',side_effect=ProviderError('synthetic_provider_failure')),
            patch('src.themescope.local.service.calculate_session',side_effect=ValueError('Synthetic calculation failure')),
            patch.object(Refresh,'publish',fail_after_pointer_write))
        for failure in failures:
            with self.subTest(failure=failure),failure:
                self.assertIsNone(self.service.refresh())
            self.assertEqual(self.service.status()['state'],'failed')
            self.assert_active(prior)
        store=Store(self.service.db,read_only=True)
        try:self.assertEqual(store.connection.execute("SELECT count(*) FROM refresh_run WHERE status='success'").fetchone()[0],1)
        finally:store.close()

    def test_same_session_republish_and_older_replay_keep_newest_success(self):
        self.assertIsNotNone(self.service.refresh());first=self.service.snapshot()
        store=Store(self.service.db,read_only=True)
        try:version=store.active_publication()[0]
        finally:store.close()
        self.assertIsNotNone(self.service.refresh());second=self.service.snapshot()
        self.assertEqual(first['session'],second['session'])
        self.assertNotEqual(first['refreshed_at'],second['refreshed_at'])
        store=Store(self.service.db)
        try:
            self.assertGreater(store.active_publication()[0],version)
            old='2024-01-02'
            self.assertLess(old,second['session'])
            with store.refresh(old,'themescope-vnext-1','synthetic-review-replay') as run:
                run.bars([Bar('AAA',old,100,100,2000000)])
                run.publish({'never_active':True},required_symbols=('AAA',))
            self.assertEqual(store.active(),second)
            self.assertEqual(store.connection.execute('PRAGMA user_version').fetchone()[0],2)
        finally:store.close()
        self.assert_active(second)
        with patch('src.themescope.local.service.calculate_session',side_effect=ValueError('Synthetic same-session failure')):
            self.assertIsNone(self.service.refresh())
        self.assert_active(second)
