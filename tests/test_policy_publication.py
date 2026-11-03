"""Failure rollback also covers migrated history backups and Primary downloads."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from test_research_policy import snapshot
from src.themescope.local_history import record
from src.themescope.research_policy import apply_policy
from scripts.generate_dashboard import _run_manual_csv
import os

class PolicyPublicationTests(unittest.TestCase):
    def test_failure_restores_dashboard_export_history_backup_and_site(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);out=root/'run';history=out/'local_history';history.mkdir(parents=True)
            s=snapshot();apply_policy(s)
            name='tradingview_daily_primary_'+s['session_date']+'.txt'
            s['export_manifest']=[{'file':name}];s['export_archives']=[]
            old=record(s);old.pop('research_history')
            (history/(s['session_date']+'.json')).write_text(json.dumps(old))
            (out/'dashboard.html').write_text('last successful dashboard')
            (out/'latest_snapshot.json').write_text(json.dumps({'session_date':s['session_date'],'export_manifest':[{'file':name}]}))
            (out/name).write_text('AMEX:OLD\n')
            site=root/'site';site.mkdir();(site/'index.html').write_text('last reviewed site')
            before={p.relative_to(root):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            args=SimpleNamespace(as_of=s['session_date'],**{role+'_csv':Path(role) for role in ('stock','etf','spy','qqq','iwm')})
            def write(snapshot,raw,stage):
                stage.mkdir(parents=True);(stage/name).write_text('AMEX:NEW\n')
            replace=os.replace
            def fail_dashboard(source,target):
                if Path(source).name=='dashboard.html' and 'stage-' in str(source):raise OSError('injected final dashboard replacement failure')
                return replace(source,target)
            with patch('src.themescope.manual_csv.build_release',return_value=(copy.deepcopy(s),{})),patch('scripts.generate_dashboard._manual_csv_outputs',side_effect=write),patch('scripts.generate_dashboard.os.replace',side_effect=fail_dashboard):
                self.assertEqual(_run_manual_csv(args,out,time.perf_counter()),1)
            for path,content in before.items():self.assertEqual((root/path).read_bytes(),content,str(path))
            self.assertFalse(list(history.glob('backups/*.json')))
            self.assertTrue(json.loads((out/'failed_attempt_audit.json').read_text())['dashboard_preserved'])

if __name__=='__main__':unittest.main()
