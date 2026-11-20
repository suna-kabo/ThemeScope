"""Local startup, credential protection, personal state and backup regressions."""
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import socket
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from scripts.local_tools import backup
from scripts.run_vnext import main, open_dashboard
from src.themescope.local import credentials
from src.themescope.local.app import create_app, local_identity
from src.themescope.local.freshness import CALENDAR
from src.themescope.local.service import fixture_service
from src.themescope.providers.base import ProviderError, Schedule
from src.themescope.storage import Store
from vnext_prelaunch_fixture import PrelaunchFixture

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'http://127.0.0.1:8766'


class LocalFirstTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)

    def finish(self, service):
        deadline = time.monotonic() + 20
        while service.running and time.monotonic() < deadline:
            threading.Event().wait(.02)
        self.assertFalse(service.running)

    def test_automatic_once_current_and_config_changed_then_failure_preserves_snapshot(self):
        fixture = PrelaunchFixture(self.root)
        service = fixture.service
        # Use the same calendar for startup and the injected market-data provider.
        calendar = self.root / 'config' / CALENDAR
        calendar.parent.mkdir()
        calendar.write_text(json.dumps({'sessions': service.records}))
        service.records = None
        clock = datetime.fromisoformat('2026-11-05T21:19:59+00:00')
        schedule_patch = patch('src.themescope.local.freshness.Schedule',
                               side_effect=lambda records: Schedule(records, now=lambda: clock))
        self.addCleanup(schedule_patch.stop)
        schedule_patch.start()
        self.assertEqual(service.status()['latest_completed_session'], '2026-11-04')
        clock = datetime.fromisoformat('2026-11-05T21:20:00+00:00')
        self.assertEqual(service.status()['latest_completed_session'], '2026-11-05')
        with patch('src.themescope.local.service.optional_earnings', return_value={}):
            self.assertTrue(service.auto_refresh())
            self.finish(service)
        status = service.status()
        self.assertEqual(status['state'], 'success', status)
        self.assertEqual(status['freshness'], 'current')
        self.assertFalse(service.auto_refresh())
        previous = service.snapshot()
        self.assertEqual(previous['session'], '2026-11-05')

        roster = self.root / 'config/market_universes/rosters.json'
        roster.parent.mkdir()
        roster.write_text('{"rosters":[]}')
        service.freshness.check(force=True)
        clock = datetime.fromisoformat('2026-11-05T23:00:00+00:00')
        self.assertEqual(service.status()['freshness'], 'configuration_changed')
        self.assertFalse(service.auto_refresh())
        self.assertEqual(service.snapshot(), previous)

        def unavailable(_):
            raise ProviderError('private provider body that must never be returned')

        service.provider_factory = unavailable
        clock = datetime.fromisoformat('2026-11-06T23:00:00+00:00')
        self.assertTrue(service.auto_refresh())
        self.finish(service)
        self.assertEqual(service.status()['error'], 'provider_unavailable')
        self.assertEqual(service.snapshot(), previous)
        self.assertEqual(service.status()['snapshot_version'], status['snapshot_version'])
        self.assertFalse(service.auto_refresh())
        restarted=type(service)(self.root,provider_factory=unavailable)
        self.assertFalse(restarted.auto_refresh())
        service.start()
        self.finish(service)
        self.assertEqual(service.snapshot(), previous)

    def test_fixture_is_isolated_and_status_avoids_loading_snapshot_payload(self):
        fixture = fixture_service(self.root)
        self.assertFalse(fixture.auto_refresh())
        self.assertFalse((self.root / 'runtime/vnext').exists())
        fixture.refresh()
        with patch.object(Store, 'active_publication', side_effect=AssertionError('Full snapshot read')):
            for _ in range(3):
                self.assertGreater(fixture.status()['snapshot_version'], 0)

    def test_saved_cross_port_migration_and_loopback_boundaries(self):
        service = fixture_service(self.root)
        personal = self.root / 'personal'
        with TestClient(create_app(ROOT, service, personal_dir=personal), base_url=ORIGIN) as app:
            data = {'entries': {'AAPL': 'consumer-hardware'}}
            self.assertEqual(app.post('/api/saved', json=data).status_code, 403)
            self.assertEqual(app.post('/api/saved', json=data, headers={'Origin': 'http://evil.test'}).status_code, 403)
            self.assertEqual(app.post('/api/saved', json=data, headers={'Origin': ORIGIN}).json(), data['entries'])
            self.assertEqual(app.get('/api/saved', headers={'Host': 'evil.test'}).status_code, 403)
            self.assertEqual(app.get('/api/saved', headers={'Sec-Fetch-Site': 'cross-site'}).status_code, 403)
            self.assertEqual(app.get('/api/local').json(), local_identity(ROOT, 'fixture'))
        other_port = 'http://127.0.0.1:8767'
        with TestClient(create_app(ROOT, service, personal_dir=personal), base_url=other_port) as app:
            self.assertEqual(app.get('/api/saved').json(), data['entries'])
            result = app.post('/api/saved', headers={'Origin': other_port},
                              json={'merge': True, 'entries': {'AAPL': 'other', 'MSFT': 'software'}})
            self.assertEqual(result.json(), {'AAPL': 'consumer-hardware', 'MSFT': 'software'})
            result = app.post('/api/saved', headers={'Origin': other_port}, json={'entries': {'AAPL': None}})
            self.assertEqual(result.json(), {'MSFT': 'software'})

    def test_exports_and_older_contract_history(self):
        service = fixture_service(self.root)
        service.refresh()
        with TestClient(create_app(ROOT, service), base_url=ORIGIN) as app:
            snapshot = app.get('/api/dashboard-data').json()
            session = snapshot['session']
            self.assertEqual(snapshot['research_v2']['contract_revision'], 4)
            response = app.get('/api/exports/combined.txt')
            self.assertEqual(response.headers['Content-Disposition'],
                             f'attachment; filename="Primary-Research-{session}.txt"')
            self.assertEqual(response.text, snapshot['exports']['combined'])
            theme, text = next(iter(snapshot['exports']['individual'].items()))
            response = app.get(f'/api/exports/{theme}.txt')
            self.assertRegex(response.headers['Content-Disposition'], f'filename="[A-Z][A-Za-z-]+-{session}\\.txt"')
            self.assertEqual(response.text, text)
            self.assertEqual(app.get('/api/exports/countertrend/all.txt').status_code, 404)
            snapshot['research_v2']['contract_revision'] = 3
            with patch.object(service, 'snapshot', side_effect=lambda **kw: (snapshot, 1) if kw else snapshot):
                self.assertEqual(app.get('/api/status').json()['freshness'], 'previous_rules')
                self.assertEqual(app.get('/api/research-list').status_code, 404)
                self.assertEqual(app.get('/api/exports/combined.txt').status_code, 404)
                self.assertEqual(app.get('/api/dashboard-data').json()['research_v2']['contract_revision'], 3)
                self.assertTrue(app.get(f'/api/themes/{theme}/history').json()['observations'])

    def test_launcher_reuses_only_recognized_owner(self):
        expected = local_identity(ROOT, 'fixture')
        with patch('scripts.run_vnext.request_local', side_effect=[expected, {'started': False}]) as request:
            self.assertTrue(open_dashboard(8766, expected, True, reused=True, attempts=1))
            request.assert_called_with(8766, '/api/local/startup', 'POST')
        with socket.socket() as owner:
            if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
                owner.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            owner.bind(('127.0.0.1', 0))
            owner.listen()
            port = owner.getsockname()[1]
            with patch('scripts.run_vnext.request_local', return_value={'app': 'Other'}), patch('scripts.run_vnext.time.sleep'):
                self.assertEqual(main(['--fixture', '--port', str(port), '--no-browser']), 1)
            self.assertEqual(owner.getsockname()[1], port)

    def test_sqlite_online_backup_excludes_other_files(self):
        service = fixture_service(self.root)
        service.refresh()
        with closing(sqlite3.connect(service.db)) as original:
            original.execute('PRAGMA journal_mode=WAL')
            original.execute('CREATE TABLE pending (private TEXT)')
            original.execute("INSERT INTO pending VALUES ('uncommitted')")
            path = backup(service.db, self.root / 'backups')
            with closing(sqlite3.connect(path)) as saved:
                self.assertEqual(saved.execute('SELECT * FROM pending').fetchall(), [])
                self.assertEqual(saved.execute('SELECT COUNT(*) FROM publication').fetchone(), (1,))
        self.assertEqual(list(path.parent.iterdir()), [path])

    @unittest.skipUnless(os.name == 'nt', 'Windows DPAPI')
    def test_native_dpapi_fake_keys_environment_override_and_browser_exclusion(self):
        personal = self.root / 'personal'
        values = ['synthetic-key', 'synthetic-secret', '']
        with (patch.object(credentials, 'app_data', return_value=personal),
              patch.object(credentials, 'getpass', side_effect=values),
              patch.dict(os.environ, {}, clear=True)):
            credentials.configure()
            cipher = (personal / 'provider.dpapi').read_bytes()
            self.assertNotIn(b'synthetic-secret', cipher)
            self.assertEqual(credentials.values()['APCA_API_SECRET_KEY'], 'synthetic-secret')
            os.environ['APCA_API_KEY_ID'] = 'injected-override'
            self.assertEqual(credentials.values()['APCA_API_KEY_ID'], 'injected-override')
            service = fixture_service(self.root)
            with TestClient(create_app(ROOT, service), base_url=ORIGIN) as app:
                for url in ('/', '/app.js', '/workspace.js', '/api/local', '/api/status',
                            '/api/dashboard-data', '/api/saved'):
                    response = app.get(url)
                    self.assertEqual(response.status_code, 200)
                    for value in ('synthetic-secret', 'synthetic-key', 'injected-override'):
                        self.assertNotIn(value, response.text)
