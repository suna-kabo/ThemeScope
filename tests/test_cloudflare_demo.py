"""Static demo build: no service, account credentials or live-data inputs."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from scripts.build_cloudflare_demo import build, demo_snapshot, ASSETS
from scripts.build_inspection_bundle import safe_file

ROOT=Path(__file__).resolve().parents[1]


class CloudflareDemoTests(unittest.TestCase):
    def test_clean_source_tree_isolated_build_deterministic_and_safe(self):
        with tempfile.TemporaryDirectory() as d:
            clean=Path(d)/'clean';clean.mkdir()
            # Source plus the approved formula settings: no .env, memberships, tests, DB or runtime.
            for folder in ('src','scripts','static/vnext'):
                shutil.copytree(ROOT/folder,clean/folder,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
            policy=clean/'config/vnext';policy.mkdir(parents=True)
            for name in ('methodology.json','research_context.json'):
                shutil.copyfile(ROOT/'config/vnext'/name,policy/name)
            env=dict(os.environ,APCA_API_KEY_ID='synthetic_not_for_output',APCA_API_SECRET_KEY='synthetic_not_for_output',ALPHAVANTAGE_API_KEY='synthetic_not_for_output')
            subprocess.run([sys.executable,'-I',str(clean/'scripts/build_cloudflare_demo.py')],cwd=clean,env=env,check=True,capture_output=True)
            output=clean/'dist/cloudflare-pages'
            first={p.name:p.read_bytes() for p in output.iterdir()}
            self.assertEqual(set(first),{*ASSETS,'preview.js','_headers','favicon.ico'})
            for asset in ASSETS:self.assertEqual(first[asset],(ROOT/'static/vnext'/asset).read_bytes())
            (output/'stale.txt').write_text('stale artifact')
            subprocess.run([sys.executable,'-I',str(clean/'scripts/build_cloudflare_demo.py')],cwd=clean,env=env,check=True,capture_output=True)
            self.assertEqual(first,{p.name:p.read_bytes() for p in output.iterdir()})
            for name in (*ASSETS,'preview.js'):
                safe_file(output/name)
                self.assertNotIn('synthetic_not_for_output',first[name].decode())
                self.assertNotIn(str(clean),first[name].decode())
            self.assertNotIn('SQLite format 3',first['preview.js'].decode())
            self.assertIn("connect-src 'none'",first['_headers'].decode())
            snapshot=json.loads(first['preview.js'].decode().removeprefix('window.FIXTURE_SNAPSHOT = ').removesuffix(';\n'))
            self.assertTrue(snapshot['synthetic_fixture'])
            self.assertNotIn('bars',snapshot)
            self.assertTrue(all(r['ticker'].startswith(('DEMO','TURN')) for r in snapshot['relationships']))
            self.assertTrue(all(s.startswith('DEMO:') for s in snapshot['exports']['combined'].splitlines() if not s.startswith('###')))

    def test_offline_fixture_variety_and_no_sqlite_or_provider_use(self):
        with patch('socket.socket',side_effect=AssertionError('No network during build')), patch('sqlite3.connect',side_effect=AssertionError('No database during build')):
            snapshot=demo_snapshot()
        self.assertEqual({'Bullish','Bearish','Mixed','Unavailable'},{t['index']['trend'] for t in snapshot['themes']})
        self.assertTrue(any(t['breadth'][0]['value'] is None for t in snapshot['themes']))
        self.assertTrue(any(r['qualifies'] for r in snapshot['relationships']))
        self.assertTrue(any(r['also_qualifies_in'] for r in snapshot['relationships']))
        self.assertEqual({'Core','Enabler'},{r['role'] for r in snapshot['relationships']})
        self.assertTrue(any(float(r['relative']['w'])<0 for r in snapshot['relationships'] if r['relative']['w'] is not None))
        self.assertNotIn('breadth',snapshot['market']['context']['IWM'])
        self.assertEqual(snapshot,demo_snapshot())

    def test_output_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'dist').symlink_to(ROOT,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'symlink'):build(root)
