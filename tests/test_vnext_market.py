import unittest,tempfile,subprocess,sys
from pathlib import Path
from src.themescope.domain import MarketRoster
from src.themescope.market.rosters import load,update,effective,warnings
from src.themescope.market.layer import market_layer,index_breadth
from src.themescope.local_refresh_lock import RefreshLock,RefreshBusy
from src.themescope.themes.calculations import bar_map
from test_vnext_calculations import bar,SESSIONS

class MarketTests(unittest.TestCase):
    def test_separate_rosters_same_valid_set_coverage_and_iwm_context(self):
        names='ABCDE';sessions=SESSIONS[:60]
        bars=bar_map(bar(s,d,100+i) for s in (*names,'Z','SPY','QQQ','IWM') for i,d in enumerate(sessions))
        spy=MarketRoster('SPY',sessions[0],tuple(names),'fixture')
        qqq=MarketRoster('QQQ',sessions[0],('Z',),'fixture')
        del bars['E',sessions[5]]
        result=market_layer(bars,sessions,(spy,qqq))
        self.assertEqual(result['context']['SPY']['breadth']['valid'],4)
        self.assertEqual(result['context']['SPY']['breadth']['coverage'],__import__('decimal').Decimal('.8'))
        self.assertEqual(result['context']['QQQ']['breadth']['configured'],1)
        self.assertNotIn('breadth',result['context']['IWM'])
        del bars['D',sessions[5]]
        self.assertEqual(index_breadth(spy,bars,sessions)['state'],'Unavailable')
        self.assertEqual(market_layer({},sessions,())['context']['SPY']['price_state'],'Unavailable')

    def test_manual_effective_dates_source_staleness_and_no_overlap(self):
        with tempfile.TemporaryDirectory() as root:
            update(root,MarketRoster('SPY','2024-01-02',('AAA',),'manual source'))
            update(root,MarketRoster('SPY','2024-02-01',('BBB',),'new source'))
            rows=load(root)
            self.assertEqual(effective(rows,'SPY','2024-01-31').tickers,('AAA',))
            self.assertEqual(effective(rows,'SPY','2024-02-01').tickers,('BBB',))
            self.assertTrue(warnings(rows[-1],'2024-12-01'))
            with self.assertRaises(ValueError):update(root,MarketRoster('SPY','2024-01-15',('CCC',),'bad'))
            with self.assertRaises(ValueError):effective(rows,'IWM','2024-02-01')

    def test_cross_process_lock_and_release(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'refresh.lock'
            with RefreshLock(path):
                with self.assertRaises(RefreshBusy):
                    with RefreshLock(path):pass
                code='from src.themescope.local_refresh_lock import RefreshLock,RefreshBusy\nimport sys\ntry:\n with RefreshLock(sys.argv[1]):pass\nexcept RefreshBusy:sys.exit(9)'
                result=subprocess.run([sys.executable,'-c',code,str(path)])
                self.assertEqual(result.returncode,9)
            with RefreshLock(path):pass

    def test_windows_byte_zero_lock_initialization_does_not_grow_file(self):
        import os
        from types import SimpleNamespace
        from unittest.mock import patch
        from src.themescope import local_refresh_lock as module
        held=set();calls=[]
        def locking(fd,operation,length):
            self.assertEqual(os.lseek(fd,0,os.SEEK_CUR),0)
            self.assertEqual(length,1)
            calls.append(operation)
            if operation==1:
                if held:raise OSError('busy')
                held.add(fd)
            else:held.remove(fd)
        windows=SimpleNamespace(name='nt',open=os.open,fdopen=os.fdopen,
                                O_RDWR=os.O_RDWR,O_CREAT=os.O_CREAT,fstat=os.fstat)
        msvcrt=SimpleNamespace(locking=locking,LK_NBLCK=1,LK_UNLCK=2)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'refresh.lock'
            with patch.object(module,'os',windows),patch.dict(sys.modules,{'msvcrt':msvcrt}):
                for _ in range(20):
                    with RefreshLock(path):
                        self.assertEqual(path.stat().st_size,1)
                        with self.assertRaises(RefreshBusy):
                            with RefreshLock(path):pass
                    self.assertEqual(path.stat().st_size,1)
                # Preserve an existing file; do not append or truncate it.
                path.write_bytes(b'previous')
                with RefreshLock(path):pass
                self.assertEqual(path.read_bytes(),b'previous')
        self.assertFalse(held)
        self.assertEqual(calls.count(1),41)
        self.assertEqual(calls.count(2),21)

    @unittest.skipUnless(sys.platform=='win32','Native Windows byte-lock regression')
    def test_native_windows_repeated_acquisition_keeps_one_byte(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'refresh.lock'
            for _ in range(20):
                with RefreshLock(path):
                    self.assertEqual(path.stat().st_size,1)
                self.assertEqual(path.stat().st_size,1)
