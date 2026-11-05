import sqlite3
import tempfile
import unittest
from pathlib import Path
from src.themescope.storage import Store, SCHEMA_VERSION
from test_vnext_calculations import bar


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/'runtime.sqlite'
        self.store=Store(self.path)
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.store.close)

    def save(self, session, payload):
        with self.store.refresh(session,'themescope-vnext-1','fixture-config') as run:
            run.bars([bar('A',session)])
            run.theme('synthetic',{'score':'50'})
            run.stock('A','synthetic',{'w':'0.01'})
            run.publish(payload,required_symbols=['A'])

    def test_schema_reopen_and_multi_theme_preservation(self):
        self.assertEqual(self.store.connection.execute('PRAGMA user_version').fetchone()[0],SCHEMA_VERSION)
        with self.store.refresh('2024-01-03','themescope-vnext-1','fixture') as run:
            run.bars([bar('A','2024-01-03')])
            run.stock('A','one',{'w':'0.1'})
            run.stock('A','two',{'w':'0.2'})
            run.publish({'session':'2024-01-03'},required_symbols=['A'])
        other=Store(self.path)
        self.addCleanup(other.close)
        self.assertEqual(other.active(),{'session':'2024-01-03'})
        self.assertEqual(other.connection.execute('SELECT count(*) FROM stock_theme_snapshot').fetchone()[0],2)

    def test_incomplete_duplicate_and_exception_rollback_keep_prior_snapshot(self):
        self.save('2024-01-03',{'old':True})
        for failure in ('missing','duplicate','exception','unpublished'):
            with self.subTest(failure=failure), self.assertRaises((ValueError,sqlite3.IntegrityError,RuntimeError)):
                with self.store.refresh('2024-01-04','themescope-vnext-1','fixture') as run:
                    run.bars([bar('A','2024-01-04')])
                    run.theme('new',{})
                    if failure=='duplicate':run.bars([bar('A','2024-01-04')])
                    if failure=='exception':raise RuntimeError('fixture failure')
                    if failure=='missing':run.publish({},required_symbols=['A','B'])
            self.assertEqual(self.store.active(),{'old':True})
        db=self.store.connection
        self.assertEqual(db.execute('SELECT count(*) FROM theme_snapshot').fetchone()[0],1)
        self.assertEqual(db.execute("SELECT count(*) FROM refresh_run WHERE status='incomplete'").fetchone()[0],4)

    def test_replay_idempotence_and_writer_lock(self):
        self.save('2024-01-04',{'new':True})
        self.save('2024-01-03',{'old':True})
        self.assertEqual(self.store.active(),{'new':True})
        self.save('2024-01-04',{'new':True})
        other=Store(self.path)
        self.addCleanup(other.close)
        with self.store.refresh('2024-01-05','themescope-vnext-1','fixture') as run:
            with self.assertRaises(sqlite3.OperationalError):
                with other.refresh('2024-01-05','themescope-vnext-1','fixture'):pass
            self.assertEqual(other.active(),{'new':True})
            run.bars([bar('A','2024-01-05')])
            run.publish({'latest':True},required_symbols=['A'])
        self.assertEqual(other.active(),{'latest':True})

    def test_unknown_schema_and_legacy_namespace_rejected(self):
        with self.assertRaises(ValueError):
            with self.store.refresh('2024-01-03','manual-csv-2','fixture'):pass
        self.store.connection.execute('PRAGMA user_version=999')
        with self.assertRaises(ValueError):Store(self.path)

    def test_index_and_history_roundtrip_exact_session_namespace(self):
        from dataclasses import asdict
        from src.themescope.themes.history import ThemeHistory, transitions
        from src.themescope.themes.index import build_index
        from test_vnext_index import config, prices
        from test_vnext_calculations import SESSIONS
        points=build_index(config(),'test',prices(),SESSIONS,SESSIONS[0],SESSIONS[2])
        history=ThemeHistory(SESSIONS[2],'test','themescope-vnext-1','fixture','Mixed','Watch')
        with self.store.refresh(SESSIONS[2],'themescope-vnext-1','fixture') as run:
            run.bars([bar('A',SESSIONS[2])])
            for point in points:run.index('test',point.session,point)
            run.theme('test',{'history':asdict(history)})
            run.publish({'fixture':True},required_symbols=['A'])
        read=self.store.theme_at('test',SESSIONS[2],'themescope-vnext-1')
        self.assertEqual(ThemeHistory(**read['history']),history)
        self.assertIsNone(self.store.theme_at('test',SESSIONS[3],'themescope-vnext-1'))
        self.assertIsNone(self.store.theme_at('test',SESSIONS[2],'manual-csv-2'))
        self.assertEqual(self.store.connection.execute('SELECT count(*) FROM theme_index').fetchone()[0],3)
