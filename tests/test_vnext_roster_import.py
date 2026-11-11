import csv,hashlib,json,re,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from scripts.import_market_roster import read_symbols
from src.themescope.market.rosters import load,effective,warnings
ROOT=Path(__file__).resolve().parents[1]

class RosterImportTests(unittest.TestCase):
    def test_symbol_only_preserves_dots_and_ignores_every_other_column(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'synthetic.csv'
            path.write_text('Symbol,Price,EMA21,Volume,Earnings\nBF.B,invalid,ignored,ignored,invalid\nBRK.B,invalid,ignored,ignored,invalid\n')
            self.assertEqual(read_symbols(path,'Symbol'),('BF.B','BRK.B'))
            for text in ('Symbol,Price\nAAA,1\nAAA,2\n','Symbol\n""\n','Symbol\nBAD/SYMBOL\n',
                         'Symbol\n lower\n','Symbol\n.AAA\n','Symbol\nAAA..B\n','Symbol,Symbol\nA,B\n','Symbol\n'):
                path.write_text(text)
                with self.assertRaises(ValueError):read_symbols(path,'Symbol')
            path.write_text('ticker\nAAA\n')
            self.assertEqual(read_symbols(path),('AAA',))

    def test_approved_real_rosters_exact_counts_hashes_and_separate_effectivity(self):
        rows=load(ROOT)
        audit=json.loads((ROOT/'config/market_universes/import_audit_2026-11-05.json').read_text())
        self.assertEqual({r.benchmark for r in rows},{'SPY','QQQ'})
        for record in audit['imports']:
            benchmark=record['benchmark'];roster=effective(rows,benchmark,'2026-11-05')
            count={'SPY':501,'QQQ':101}[benchmark]
            self.assertEqual(len(roster.tickers),count)
            self.assertEqual(len(set(roster.tickers)),count)
            self.assertTrue(all(re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,15}',s) for s in roster.tickers))
            self.assertEqual(hashlib.sha256(('\n'.join(roster.tickers)+'\n').encode()).hexdigest(),record['symbols_sha256'])
            self.assertEqual(roster.source,f'TradingView {benchmark} constituent scanner export, user supplied 2026-11-05')
            self.assertIsNone(effective(rows,benchmark,'2026-11-04'))
            self.assertFalse(warnings(roster,'2026-11-05'))
            self.assertTrue(warnings(roster,'2027-03-01'))
            self.assertIsNone(roster.effective_to)
        spy=effective(rows,'SPY','2026-11-05');qqq=effective(rows,'QQQ','2026-11-05')
        self.assertNotEqual(set(spy.tickers),set(qqq.tickers))
        self.assertIn('BF.B',spy.tickers);self.assertIn('BRK.B',spy.tickers)
        with self.assertRaises(ValueError):effective(rows,'IWM','2026-11-05')
        payload=json.loads((ROOT/'config/market_universes/rosters.json').read_text())
        for row in payload['rosters']:
            self.assertEqual(set(row),{'benchmark','effective_from','tickers','source','effective_to'})

    def test_local_compatibility_diagnostic_reports_exact_missing_symbols(self):
        from scripts.check_roster_symbols import main
        from src.themescope.providers.base import Batch,ProviderError
        from src.themescope.themes.calculations import Bar
        class Fake:
            def __init__(self,*args):pass
            def get_daily_bars(self,symbols,start,end):
                return Batch('fixture',tuple(Bar(s,end,100,100,2000000) for s in symbols if s!='BRK.B'),2)
        with patch('builtins.print') as output:
            self.assertEqual(main(['--roster-date','2026-11-05','--session','2026-11-04'],factory=Fake),1)
            report=json.loads(output.call_args.args[0])
            self.assertEqual(report['benchmarks']['SPY']['missing_or_unusable'],['BRK.B'])
            self.assertEqual(report['benchmarks']['QQQ']['missing_or_unusable'],[])
        class All(Fake):
            def get_daily_bars(self,symbols,start,end):return Batch('fixture',tuple(Bar(s,end,100,100,2000000) for s in symbols),2)
        with patch('builtins.print'):
            self.assertEqual(main(['--roster-date','2026-11-05','--session','2026-11-04'],factory=All),0)
        with patch.dict('os.environ',{},clear=True),patch('builtins.print') as output:
            self.assertEqual(main(['--roster-date','2026-11-05','--session','2026-11-04']),1)
            self.assertEqual(json.loads(output.call_args.args[0])['reason'],'credentials_missing')
