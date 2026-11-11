import json
from pathlib import Path
import shutil
import tempfile
import unittest
from scripts.build_inspection_bundle import build, safe_file

ROOT = Path(__file__).resolve().parents[1]


class InspectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/'config/calendars',self.root/'config/calendars')

    def test_reject_private_assets_and_secrets(self):
        for name, content in [('.env', 'x'), ('data.sqlite3', 'x'),
                              ('raw_inputs.json', '{}'), ('cache.json', '{}'),
                              ('secret.txt', 'api_key=synthetic_secret_canary_123456'),
                              ('header.json', '{"APCA-API-KEY-ID":"synthetic_canary_123456"}'),
                              ('renamed.txt', 'SQLite format 3\x00not_a_real_database'),
                              ('private.txt', '-----BEGIN RSA PRIVATE KEY-----'),
                              ('path.txt', '/Users/synthetic-person/project'),
                              ('junk.bin', 'x'), ('provider.json', '{"observations":[]}'),
                              ('snapshot.json', '{"bars":{}}')]:
            with self.subTest(name=name):
                path = self.root / name
                path.write_text(content)
                with self.assertRaises(ValueError):
                    safe_file(path)

    def test_build_contains_config_and_no_live_data(self):
        shutil.copytree(ROOT / 'config/vnext', self.root / 'config/vnext')
        shutil.copytree(ROOT / 'docs', self.root / 'docs')
        report_path = self.root / 'passed.txt'
        report_path.write_text('Synthetic inspection test; not a certification of a real gate.\n')
        report = build(self.root, test_report=report_path)
        self.assertEqual(report['active_themes'], 44)
        self.assertEqual(report['unique_tickers'], 668)
        self.assertEqual(report['production_blockers'],[])
        paths = list((self.root / 'inspection').iterdir())
        self.assertEqual(len(paths), 5)
        for path in paths:
            safe_file(path)
        before = (self.root / 'inspection/index.html').read_bytes()
        (self.root / 'inspection/unrelated.txt').write_text('Preserve me')
        with self.assertRaisesRegex(ValueError, 'unrelated'):
            build(self.root)
        self.assertEqual((self.root / 'inspection/index.html').read_bytes(), before)

    def test_symlink_asset_rejected(self):
        target = self.root / 'target.txt'
        target.write_text('Synthetic safe content')
        link = self.root / 'linked.txt'
        try:
            link.symlink_to(target)
        except OSError:
            self.skipTest('Symlink creation not supported on this platform')
        with self.assertRaisesRegex(ValueError, 'Symlinks'):
            safe_file(link)

    def test_legacy_archive_fixtures_are_synthetic(self):
        raw = json.loads((ROOT / 'tests/fixtures/v1/raw_inputs.json').read_text())
        snapshot = json.loads((ROOT / 'tests/fixtures/v1/latest_snapshot.json').read_text())
        self.assertTrue(raw['synthetic'])
        self.assertTrue(snapshot['synthetic'])
        for symbol, chart in raw['charts'].items():
            self.assertTrue(chart['synthetic'])
            self.assertTrue(chart['url'].startswith('fixture://'))
            self.assertTrue(all(r['volume'] == 2000000 for r in chart['observations']))
        for quote in raw['quotes'].values():
            self.assertTrue(quote['synthetic'])
            self.assertEqual(quote['market_cap_usd'], 3000000000)

    def test_engine_report_must_be_synthetic_and_safe(self):
        shutil.copytree(ROOT / 'config/vnext', self.root / 'config/vnext')
        shutil.copytree(ROOT / 'docs', self.root / 'docs')
        report=self.root/'engine.json'
        report.write_text('{"synthetic_fixture":false}')
        with self.assertRaisesRegex(ValueError,'explicitly synthetic'):build(self.root,engine_report=report)
        report.write_text('{"synthetic_fixture":true,"bars":{}}')
        with self.assertRaisesRegex(ValueError,'Raw provider'):build(self.root,engine_report=report)
        from scripts.vnext_fixture_report import report as fixture_report
        report.write_text(json.dumps(fixture_report()))
        build(self.root,engine_report=report,provider_report=ROOT/'docs/vnext_provider.md')
        self.assertEqual(len(list((self.root/'inspection').iterdir())),7)
        preview=(self.root/'inspection/index.html').read_text()
        self.assertIn('NASDAQ:AAA',preview)
        self.assertIn('also qualifies in:',preview)
        for path in (self.root/'inspection').iterdir():safe_file(path)

    def test_ui_preview_is_synthetic_and_rejects_unrelated_assets(self):
        shutil.copytree(ROOT/'config/vnext',self.root/'config/vnext')
        shutil.copytree(ROOT/'docs',self.root/'docs')
        shutil.copytree(ROOT/'static/vnext',self.root/'static/vnext')
        snapshot=self.root/'snapshot.json'
        snapshot.write_text('{"synthetic_fixture":false}')
        with self.assertRaisesRegex(ValueError,'must be synthetic'):build(self.root,ui_snapshot=snapshot)
        snapshot.write_text('{"synthetic_fixture":true}')
        build(self.root,ui_snapshot=snapshot)
        self.assertTrue((self.root/'inspection/ui/index.html').is_file())
        self.assertIn('FIXTURE_SNAPSHOT',(self.root/'inspection/ui/preview.js').read_text())
        for path in (self.root/'inspection').rglob('*'):
            if path.is_file():safe_file(path)
        (self.root/'inspection/ui/unrelated.txt').write_text('preserve this')
        with self.assertRaisesRegex(ValueError,'unrelated'):build(self.root,ui_snapshot=snapshot)
