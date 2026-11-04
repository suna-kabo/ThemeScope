import copy
import json
import tempfile
import unittest
from pathlib import Path
from src.themescope.local_history import apply, record

class LocalHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.history=self.root/'history';self.history.mkdir()
        self.calendar=self.root/'calendar.json';self.calendar.write_text(json.dumps({'sessions':[{'session':s} for s in ('2026-10-27','2026-10-28','2026-10-29','2026-10-30')]}))
        self.s={'session_date':'2026-10-30','methodology_version':'manual-csv-1','score_methodology':{'weights':[.6,.4],'state_threshold':50},'manual_csv_audit':{'percentile_method':'average'},'themes':[{'id':str(i),'anchor':'E'+str(i),'theme_score':50,'global_rank':rank,'theme_state':'Leading','research_priority':{'group':0},'returns':{'21':{'value':.1},'63':{'value':.2}}} for i,rank in enumerate((1.5,1.5,3))]}
    def save(self,s):
        r=record(s);(self.history/(s['session_date']+'.json')).write_text(json.dumps(r));return r
    def test_first_run_and_missing_intervening_session(self):
        prior=copy.deepcopy(self.s);prior['session_date']='2026-10-28';self.save(prior)
        apply(self.s,self.history,self.calendar)
        self.assertTrue(all(t['rank_change_daily'] is None for t in self.s['themes']))
    def test_two_sessions_ties_and_immutability(self):
        prior=copy.deepcopy(self.s);prior['session_date']='2026-10-29';prior['themes'][0]['global_rank']=3;prior['themes'][1]['global_rank']=1.5;prior['themes'][2]['global_rank']=1.5;self.save(prior)
        before=copy.deepcopy(self.s['themes']);apply(self.s,self.history,self.calendar)
        self.assertEqual([t['rank_change_daily'] for t in self.s['themes']],[1.5,0,-1.5])
        for old,new in zip(before,self.s['themes']):
            for key in old:self.assertEqual(old[key],new[key])
    def test_same_session_rerun_never_baseline(self):
        self.save(self.s);apply(self.s,self.history,self.calendar)
        self.assertIsNone(self.s['themes'][0]['rank_change_daily'])
    def test_config_universe_and_anchor_change(self):
        for key in ('anchor','theme_score'):
            with self.subTest(key=key):
                prior=copy.deepcopy(self.s);prior['session_date']='2026-10-29';prior['themes'][0][key]='other' if key=='anchor' else None;self.save(prior)
                apply(self.s,self.history,self.calendar);self.assertIsNone(self.s['themes'][0]['rank_change_daily'])
        prior=copy.deepcopy(self.s);prior['session_date']='2026-10-29';prior['score_methodology']['weights']=[.5,.5];self.save(prior)
        apply(self.s,self.history,self.calendar);self.assertIsNone(self.s['themes'][0]['rank_change_daily'])
    def test_corruption_preserved(self):
        path=self.history/'2026-10-29.json';path.write_text('broken')
        apply(self.s,self.history,self.calendar);self.assertIn('Malformed',self.s['local_history']['status']);self.assertEqual(path.read_text(),'broken')
        path=self.history/'2026-10-30.json';path.write_text('broken')
        with self.assertRaisesRegex(ValueError,'malformed'):apply(self.s,self.history,self.calendar)
        self.assertEqual(path.read_text(),'broken')
    def test_historical_record_does_not_change_future(self):
        future=self.history/'2026-11-02.json';future.write_text('unrelated newer data')
        apply(self.s,self.history,self.calendar);self.assertEqual(future.read_text(),'unrelated newer data')

class DisplayIsolationTests(unittest.TestCase):
    def test_compacting_dashboard_does_not_mutate_history_or_source_metadata(self):
        from scripts.generate_dashboard import _dashboard_snapshot
        from src.themescope.local_history import market_history_inputs
        snapshot={'themes':[],'context':[{'ticker':'SPY','index_breadth':{'21':{'value':80,'valid_count':8,'eligible_count':10,'coverage_pct':80}}}]}
        before=copy.deepcopy(snapshot);history=market_history_inputs(snapshot['context'])
        displayed=_dashboard_snapshot(snapshot)
        self.assertEqual(snapshot,before)
        self.assertNotIn('coverage_pct',displayed['context'][0]['index_breadth']['21'])
        self.assertNotIn('coverage_pct',history[0]['index_breadth']['21'])
        self.assertEqual(history[0]['index_breadth']['21']['value'],80)

class PrimaryCategoryTests(unittest.TestCase):
    def test_final_guard_controls_category_for_both_directions(self):
        from src.themescope.approved_rules import canonical_decision, priority
        for direction,state,good,bad in [('Long bias','Leading',11,9),('Short bias','Lagging',9,11)]:
            rows=[{'id':str(i),'theme_state':state,'theme_score':50,'research_priority':priority(direction,state,close,10)} for i,close in enumerate((good,bad))]
            canonical_decision('session','generated',[],rows,direction,'Mixed')
            self.assertEqual(rows[0]['research_priority']['category'],'primary')
            self.assertEqual(rows[1]['research_priority']['category'],'observation')
