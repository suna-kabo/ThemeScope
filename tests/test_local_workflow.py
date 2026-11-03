import hashlib
import json
from datetime import datetime,timezone
from pathlib import Path
import tempfile
import unittest

from scripts.refresh_local import input_paths,STEMS


class InputSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'config/calendars').mkdir(parents=True)
        (self.root/'config/calendars/xnys_2020_2035_v1.json').write_text(json.dumps({'sessions':[{'session':'2026-11-02','close':'2026-11-02T16:00:00-05:00'},{'session':'2026-11-03','close':'2026-11-03T16:00:00-05:00'}]}))
        self.folder=self.root/'inputs/2026-11-02';self.folder.mkdir(parents=True)
        for stem in STEMS.values():(self.folder/(stem+'_2026-11-03.csv')).write_text('test data')
        self.now=datetime(2026,11,3,0,tzinfo=timezone.utc)

    def paths(self,session='2026-11-02',folder=None):return input_paths(self.root,session,folder,now=self.now)

    def test_exact_five_hong_kong_names_and_root_relative_paths(self):
        self.assertEqual(set(self.paths()),set(STEMS))
        self.assertEqual(self.paths(folder='inputs/2026-11-02')['stock'].parent,self.folder)

    def test_missing_duplicate_and_stale_dates_fail_without_fallback(self):
        p=self.folder/'SPY_2026-11-03.csv';p.rename(self.folder/'SPY_2026-10-31.csv')
        with self.assertRaisesRegex(ValueError,'filename date'):self.paths()
        (self.folder/'SPY_2026-10-31.csv').rename(p)
        (self.folder/'SPY.csv').write_text('other')
        with self.assertRaisesRegex(ValueError,'found 2'):self.paths()
        p.unlink();(self.folder/'SPY.csv').unlink()
        with self.assertRaisesRegex(ValueError,'found 0'):self.paths()

    def test_closed_session_calendar_and_folder_are_explicit(self):
        with self.assertRaisesRegex(ValueError,'not a configured'):self.paths('2026-11-01')
        with self.assertRaisesRegex(ValueError,'not closed'):self.paths('2026-11-03')
        other=self.root/'inputs/2026-10-30';other.mkdir()
        with self.assertRaisesRegex(ValueError,'dated input folder'):self.paths(folder=other)

    def test_unchanged_previous_session_input_is_not_silently_reused(self):
        out=self.root/'output/manual_csv';out.mkdir(parents=True)
        value={'session_date':'2026-10-30','manual_csv_audit':{'inputs':{'spy':{'sha256':hashlib.sha256(b'test data').hexdigest()}}}}
        (out/'latest_snapshot.json').write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError,'identical to the previous'):self.paths()
        value['session_date']='2026-11-02';(out/'latest_snapshot.json').write_text(json.dumps(value))
        self.assertEqual(len(self.paths()),5) # Explicit rerun of the same session is allowed.
