"""Exercise the publication boundary with real retained inputs and simulated failures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.generate_dashboard import ROOT, main
from src.themescope.presentation import enrich, validate


class RefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = json.loads((ROOT / 'tests/fixtures/v1/latest_snapshot.json').read_text(encoding='utf-8'))
        cls.raw = json.loads((ROOT / 'tests/fixtures/v1/raw_inputs.json').read_text(encoding='utf-8'))

    def test_failure_preserves_all_prior_outputs_and_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            with patch('scripts.generate_dashboard.build_snapshot', return_value=(copy.deepcopy(self.snapshot), self.raw)):
                self.assertEqual(main(['--output-dir', str(out)]), 0)
            before = {p.name: p.read_bytes() for p in out.iterdir() if p.name != 'refresh_status.json'}
            with patch('scripts.generate_dashboard.build_snapshot', side_effect=RuntimeError('HTTP 429')):
                self.assertEqual(main(['--output-dir', str(out)]), 1)
            for name, content in before.items():
                self.assertEqual((out / name).read_bytes(), content)
            self.assertEqual(json.loads((out / 'refresh_status.json').read_text())['status'], 'failed')

    def test_publication_failure_rolls_back_and_keeps_unrelated_files(self):
        import os
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            with patch('scripts.generate_dashboard.build_snapshot', return_value=(copy.deepcopy(self.snapshot), self.raw)):
                self.assertEqual(main(['--output-dir', str(out)]), 0)
            (out / 'personal.txt').write_text('keep me')
            before = (out / 'dashboard.html').read_bytes()
            original_replace = os.replace
            failed = False
            def fail_once(source, target):
                nonlocal failed
                if Path(source).name == 'dashboard.html' and not failed:
                    failed = True
                    raise OSError('simulated publication failure')
                return original_replace(source, target)
            with patch('scripts.generate_dashboard.build_snapshot', return_value=(copy.deepcopy(self.snapshot), self.raw)), patch('scripts.generate_dashboard.os.replace', side_effect=fail_once):
                self.assertEqual(main(['--output-dir', str(out)]), 1)
            self.assertEqual((out / 'dashboard.html').read_bytes(), before)
            self.assertEqual((out / 'personal.txt').read_text(), 'keep me')

    def test_preexisting_failed_html_is_not_treated_as_last_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            out.mkdir()
            (out / 'dashboard.html').write_text('failed empty dashboard')
            with patch('scripts.generate_dashboard.build_snapshot', return_value=({}, {})):
                self.assertEqual(main(['--output-dir', str(out)]), 1)
            self.assertFalse((out / 'dashboard.html').exists())
            self.assertTrue((out / 'rejected_dashboard.html').exists())

    def test_empty_run_is_not_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / 'run'
            with patch('scripts.generate_dashboard.build_snapshot', return_value=({}, {})):
                self.assertEqual(main(['--output-dir', str(out)]), 1)
            self.assertFalse((out / 'dashboard.html').exists())

    def test_failed_current_holdings_request_cannot_reuse_retained_payload(self):
        raw = copy.deepcopy(self.raw)
        raw['errors']['holdings']['SMH'] = 'HTTP 503'
        from src.themescope.v6 import _candidate_status
        registry = json.loads((ROOT / 'config/themes.json').read_text(encoding='utf-8'))
        record = next(row for row in registry['themes'] if row.get('anchor') == 'SMH')
        audit = _candidate_status(record, 'SMH', raw, self.snapshot, registry['settings'])
        self.assertEqual(audit['status'], 'eligible')
        self.assertTrue(any('Official holdings refresh failed: HTTP 503' in reason for reason in audit['breadth_reasons']))
        self.assertIsNone(audit['holdings_effective_date'])

    def test_run_zip_import_and_export_values_match_snapshot(self):
        import csv
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / 'first', Path(tmp) / 'second'
            with patch('scripts.generate_dashboard.build_snapshot', return_value=(copy.deepcopy(self.snapshot), self.raw)):
                self.assertEqual(main(['--output-dir', str(first)]), 0)
            with patch('scripts.generate_dashboard.build_snapshot', side_effect=AssertionError('Must not collect')):
                self.assertEqual(main(['--import-run',str(first/'run_bundle.zip'),'--output-dir',str(second)]),0)
            snapshot = json.loads((second/'latest_snapshot.json').read_text())
            with (second/'themes.csv').open(encoding='utf-8-sig') as handle:
                rows = list(csv.DictReader(handle))
            by_id = {t['id']:t for t in snapshot['themes']}
            for row in rows:
                self.assertEqual(row['session_date'],snapshot['session_date'])
                self.assertAlmostEqual(float(row['return21_pct']),100*by_id[row['id']]['returns']['21']['value'])
                self.assertEqual(row['theme_score'],'')
                self.assertEqual(row['theme_score_status'],'unavailable')

    def test_misaligned_metrics_fail_validation(self):
        snapshot = enrich(copy.deepcopy(self.snapshot), self.raw)
        snapshot['context'][0]['returns']['21']['session_date'] = '1999-01-01'
        with self.assertRaisesRegex(ValueError, 'misaligned'):
            validate(snapshot, self.raw)

    def test_import_is_offline_and_preserves_date(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch('scripts.generate_dashboard.build_snapshot', side_effect=AssertionError('Must not collect')):
                self.assertEqual(main(['--import-run', str(ROOT / 'tests/fixtures/v1'), '--output-dir', str(Path(tmp) / 'run')]), 0)
            imported = json.loads((Path(tmp) / 'run/latest_snapshot.json').read_text())
            self.assertEqual(imported['session_date'], self.snapshot['session_date'])
            self.assertEqual(imported['generated_at'], self.snapshot['generated_at'])

if __name__ == '__main__':
    unittest.main()
