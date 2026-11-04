"""Public entry points enforce the same completed-session and publication guards."""
import copy
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time
import unittest
from unittest.mock import patch

from scripts.generate_dashboard import main,_run_manual_csv
from src.themescope.manual_csv import require_completed_session,build_release,CSVValidationError
from src.themescope.local_publication import relative
from test_research_policy import snapshot

ROOT=Path(__file__).resolve().parents[1]


class EntryGuardTests(unittest.TestCase):
    def test_no_implicit_network_collection_and_explicit_source_is_respected(self):
        for args in ([],['--source','live'],['--import-run','unused','--source=tradingview-csv']):
            with patch('scripts.generate_dashboard.build_snapshot') as collect:
                with self.assertRaises(SystemExit) as error:main(args)
                self.assertEqual(error.exception.code,2);collect.assert_not_called()

    def test_direct_manual_build_refuses_a_future_session_before_reading_inputs(self):
        paths={role:Path('not-read.csv') for role in ('stock','etf','spy','qqq','iwm')}
        with self.assertRaisesRegex(CSVValidationError,'has not closed'):
            build_release(ROOT,paths,'2030-01-02')

    def test_calendar_closes_cover_early_close_holiday_and_dst(self):
        # July 3 half day (17:00 UTC), then winter and summer regular closes.
        for session,before,closed in [('2024-07-03','2024-07-03T16:59:59+00:00','2024-07-03T17:00:00+00:00'),
                                      ('2024-03-08','2024-03-08T20:59:59+00:00','2024-03-08T21:00:00+00:00'),
                                      ('2024-03-11','2024-03-11T19:59:59+00:00','2024-03-11T20:00:00+00:00')]:
            with self.assertRaisesRegex(CSVValidationError,'has not closed'):require_completed_session(ROOT,session,datetime.fromisoformat(before))
            require_completed_session(ROOT,session,datetime.fromisoformat(closed))
        with self.assertRaisesRegex(CSVValidationError,'not a configured'):require_completed_session(ROOT,'2024-07-04',datetime(2024,7,5,tzinfo=timezone.utc))

    def test_direct_generator_cannot_bypass_previous_successful_input_hashes(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary);paths={role:output/(role+'.csv') for role in ('stock','etf','spy','qqq','iwm')}
            for path in paths.values():path.write_bytes(b'old CSV')
            previous={'session_date':'2026-07-02','manual_csv_audit':{'inputs':{role:{'sha256':hashlib.sha256(path.read_bytes()).hexdigest()} for role,path in paths.items()}}}
            (output/'latest_snapshot.json').write_text(json.dumps(previous));(output/'dashboard.html').write_bytes(b'previous HTML')
            candidate=snapshot();args=SimpleNamespace(as_of=candidate['session_date'],**{role+'_csv':path for role,path in paths.items()})
            with patch('src.themescope.manual_csv.build_release',return_value=(copy.deepcopy(candidate),{})):
                self.assertEqual(_run_manual_csv(args,output,time.perf_counter()),1)
            self.assertEqual((output/'dashboard.html').read_bytes(),b'previous HTML')
            self.assertEqual(json.loads((output/'latest_snapshot.json').read_text()),previous)
            self.assertIn('Inputs identical',json.loads((output/'failed_attempt_audit.json').read_text())['reason'])

    def test_publication_paths_reject_windows_drives_and_alternate_data_streams(self):
        for path in ('C:/outside.txt','C:outside.txt','file.txt:private','../outside.txt','/outside.txt','..\\outside.txt'):
            with self.assertRaisesRegex(ValueError,'Unsafe publication path'):relative(path)


if __name__=='__main__':unittest.main()
