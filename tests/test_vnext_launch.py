"""Approved launch through the real refresh orchestration; all bars are synthetic."""
from collections import Counter
from dataclasses import replace
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path
import csv,json,shutil,tempfile,unittest
from src.themescope.domain import load_configuration,MarketRoster,effective_session_after_close
from src.themescope.local.service import RefreshService
from src.themescope.market.rosters import load as rosters
from src.themescope.providers.base import FixtureProvider,Schedule
from src.themescope.storage import Store
from src.themescope.themes.calculations import Bar

ROOT=Path(__file__).resolve().parents[1]
L='2026-11-06';E='2026-11-09'
RECORDS=json.loads((ROOT/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
DAYS=[r['session'] for r in RECORDS]

class LaunchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.config=load_configuration(ROOT)
        self.target='2026-11-05';self.providers=[]

    def service(self,config=None,*,full_rosters=False,missing=()):
        config=config or self.config
        names={m.ticker for m in config.memberships if m.calculation_eligible}
        rows=rosters(ROOT) if full_rosters else (
            MarketRoster('SPY','2026-11-05',('SPY',),'Synthetic SPY universe'),
            MarketRoster('QQQ','2026-11-05',('QQQ',),'Synthetic QQQ universe'))
        names.update(s for r in rows for s in r.tickers)
        names.update(('SPY','QQQ','IWM'))
        begin=DAYS.index(L)-253
        days=DAYS[begin:DAYS.index('2026-11-10')+1]
        data=[]
        for name in names:
            for day in days:
                # Airlines has five members: DAL doubles twice; the other four are flat.
                price=400 if name=='DAL' and day>='2026-11-10' else 200 if name=='DAL' and day>=E else 100
                data.append(Bar(name,day,price,price,2000000))
        folder=self.root/'config';folder.mkdir(exist_ok=True)
        # Explicit synthetic mappings, never an assertion about real venues.
        (folder/'tradingview_symbols.json').write_text(json.dumps({'symbols':{
            s:{'status':'verified','symbol':'NASDAQ:'+s} for s in names}}))
        def provider(_):
            schedule=Schedule(RECORDS,now=lambda:datetime.fromisoformat(self.target+'T23:00:00+00:00'))
            p=FixtureProvider(data,schedule);self.providers.append(p);return p
        return RefreshService(self.root,config_factory=lambda:config,provider_factory=provider,
                              records=RECORDS,rosters_factory=lambda:tuple(r for r in rows if r.benchmark not in missing))

    def refresh(self,service,day):
        self.target=day;snapshot=service.refresh()
        self.assertIsNotNone(snapshot,service.status())
        self.assertEqual(snapshot['session'],day)
        return snapshot

    def index_rows(self,service):
        store=Store(service.db)
        try:
            return [json.loads(r[0]) for r in store.connection.execute(
                'SELECT payload FROM theme_index WHERE run_id=(SELECT run_id FROM publication WHERE id=1)')]
        finally:store.close()

    def test_approved_configuration_counts_and_no_backdating(self):
        c=self.config
        self.assertEqual((c.methodology['launch_rebalance_session'],c.methodology['production_enabled']),(L,True))
        self.assertEqual(effective_session_after_close(L,DAYS),E)
        self.assertEqual(Counter(m.role for m in c.memberships),{'Core':659,'Enabler':62,'Related':5})
        self.assertEqual(len(c.memberships),726)
        self.assertTrue(all(m.effective_from==E and m.effective_to is None for m in c.memberships))
        self.assertTrue(all(not m.active_on('2026-11-05') and not m.active_on(L) and m.active_on(E) for m in c.memberships))
        self.assertEqual(c.production_blockers(),[])
        self.assertEqual([(r.benchmark,len(r.tickers)) for r in rosters(ROOT)],[('SPY',501),('QQQ',101)])

    def test_real_44_theme_prelaunch_and_launch_close_with_full_rosters(self):
        service=self.service(full_rosters=True)
        before=self.refresh(service,'2026-11-05')
        self.assertEqual(before['theme_layer']['state'],'pre_launch_research')
        self.assertTrue(before['relationships'])
        self.assertTrue(all(t['index']['bootstrap'] for t in before['themes']))
        self.assertTrue(all(t['score'] is not None for t in before['themes'] if t['status']=='active'))
        self.assertEqual(self.index_rows(service),[])
        self.assertIn('SPY',before['market']['context'])
        launched=self.refresh(service,L)
        self.assertEqual(launched['theme_layer']['state'],'initialized')
        self.assertEqual(launched['theme_layer']['first_earned_session'],E)
        self.assertEqual(launched['production_blockers'],[])
        self.assertEqual(launched['relationships'],[])
        active=[t for t in launched['themes'] if t['status']=='active']
        self.assertEqual(len(active),44)
        for theme in active:
            self.assertEqual(theme['index']['level'],100,theme['theme_id'])
            self.assertIsNotNone(theme['index']['ema21'])
            self.assertIsNotNone(theme['index']['ema50'])
            self.assertFalse(theme['history']['signal_eligible'])
            self.assertTrue(all(v is None for v in theme['transition'].values()))
        points=self.index_rows(service)
        live=[p for p in points if not p['bootstrap']]
        self.assertEqual(len(live),44)
        for point in live:
            self.assertEqual((point['session'],D(point['level']),point['earned_symbols']),(L,D(100),[]))
        self.assertTrue(any(p['bootstrap'] for p in points))
        self.assertTrue(all(p['session']<L for p in points if p['bootstrap']))
        # Audit each theme's holdings directly, including the five Related exclusions.
        store=Store(service.db)
        try:
            for row in store.connection.execute('SELECT theme_id,payload FROM theme_index WHERE session=?',(L,)):
                point=json.loads(row[1]);expected={m.ticker for m in self.config.members_on(row[0],E)}
                self.assertEqual({s for s,w in point['weights']},expected)
        finally:store.close()
        fetched={s for call in self.providers[-1].calls for s in call[0]}
        expected={m.ticker for m in self.config.memberships if m.calculation_eligible}
        expected.update(s for r in rosters(ROOT) for s in r.tickers);expected.update(('SPY','QQQ','IWM'))
        self.assertEqual(fetched,expected)

    def test_first_return_drift_related_and_live_transition_boundary(self):
        c=self.config
        # Actual five-member approved theme plus an explicitly Related synthetic row.
        c=replace(c,themes=tuple(t for t in c.themes if t.theme_id=='airlines'),
                  memberships=tuple(m for m in c.memberships if m.theme_id=='airlines'))
        self.assertEqual(len(c.memberships),5)
        c=replace(c,memberships=c.memberships+(replace(c.memberships[0],ticker='RELATED',role='Related'),))
        service=self.service(c)
        launch=self.refresh(service,L)
        first=self.refresh(service,E)
        second=self.refresh(service,'2026-11-10')
        self.assertEqual(launch['themes'][0]['index']['level'],100)
        self.assertAlmostEqual(D(str(first['themes'][0]['index']['level'])),D(120),places=25)
        self.assertAlmostEqual(D(str(second['themes'][0]['index']['level'])),D(160),places=25)
        self.assertNotEqual(D(str(second['themes'][0]['index']['level'])),D(144))
        self.assertEqual({r['ticker'] for r in first['relationships']},{m.ticker for m in c.memberships if m.calculation_eligible})
        self.assertTrue(first['themes'][0]['history']['signal_eligible'])
        self.assertTrue(all(v is None for v in first['themes'][0]['transition'].values()))
        self.assertIsNotNone(second['themes'][0]['transition']['priority_change'])
        live=[p for p in self.index_rows(service) if not p['bootstrap']]
        self.assertEqual([p['session'] for p in live],[L,E,'2026-11-10'])
        self.assertEqual(live[0]['earned_symbols'],[])
        self.assertEqual(set(live[1]['earned_symbols']),{m.ticker for m in c.members_on('airlines',E)})
        self.assertFalse(live[1]['rebalanced']);self.assertFalse(live[2]['rebalanced'])
        self.assertNotIn('RELATED',{s for p in live for s,w in p['weights']})
        self.assertNotIn('RELATED',{s for call in self.providers[-1].calls for s in call[0]})

    def test_missing_each_roster_still_blocks_launch_and_primary(self):
        c=replace(self.config,themes=tuple(t for t in self.config.themes if t.theme_id=='airlines'),
                  memberships=tuple(m for m in self.config.memberships if m.theme_id=='airlines'))
        for benchmark in ('SPY','QQQ'):
            with self.subTest(benchmark=benchmark):
                service=self.service(c,missing=(benchmark,))
                for day in (L,E):
                    snapshot=self.refresh(service,day)
                    self.assertEqual(snapshot['production_blockers'],[f'Effective {benchmark} constituent roster missing for {day}'])
                    self.assertEqual(snapshot['theme_layer']['state'],'activation_blocked')
                    self.assertEqual(snapshot['relationships'],[])
                    self.assertEqual(snapshot['exports']['combined'],'')
                    self.assertTrue(all(t['index']['level'] is None for t in snapshot['themes']))

    def test_approval_and_membership_tampering_rejected(self):
        shutil.copytree(ROOT/'config',self.root/'config')
        p=self.root/'config/vnext/launch_approval.json';original=p.read_text();approval=json.loads(original)
        approval['first_earned_session']=L;p.write_text(json.dumps(approval))
        with self.assertRaisesRegex(ValueError,'launch approval'):load_configuration(self.root)
        approval['first_earned_session']='2026-11-10';p.write_text(json.dumps(approval))
        with self.assertRaisesRegex(ValueError,'next XNYS'):load_configuration(self.root)
        p.write_text(original)
        p=self.root/'config/vnext/memberships.csv'
        with p.open(newline='') as f:r=csv.DictReader(f);fields=r.fieldnames;rows=list(r)
        rows[0]['effective_from']='2026-11-05'
        with p.open('w',newline='') as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
        with self.assertRaisesRegex(ValueError,'explicit launch approval'):load_configuration(self.root)

    def test_reviewed_identifiers_cover_launch_without_legacy_venue_guesses(self):
        from src.themescope.research.exports import reviewed_mapping
        from src.themescope.tradingview import resolve
        original=json.loads((ROOT/'config/tradingview_symbols.json').read_text())['symbols']
        mapping=reviewed_mapping(self.config,original)
        source={r['ticker']:r['exchange']+':'+r['ticker'] for r in self.config.universe['instruments']}
        for member in self.config.memberships:
            if member.calculation_eligible:self.assertEqual(resolve(member.ticker,mapping),source[member.ticker])
        self.assertNotIn('NOT_REVIEWED',mapping)
        self.assertIsNot(mapping,original)
        self.assertNotIn('AAL',original)
        with self.assertRaises(ValueError):resolve('NOT_REVIEWED',mapping)

    def test_default_launchers_use_vnext_and_legacy_readers_are_explicit(self):
        for name in ('refresh','open-dashboard'):
            content=(ROOT/(name+'.cmd')).read_text()
            self.assertIn('ThemeScope.cmd',content)
            self.assertNotIn('refresh_local.py',content)
            self.assertNotIn('serve_local.py',content)
        self.assertIn('bootstrap_dev.py',(ROOT/'setup.cmd').read_text())
        self.assertIn('run_vnext.py',(ROOT/'ThemeScope.cmd').read_text())
        for name in ('setup','refresh','open-dashboard'):
            self.assertTrue((ROOT/('legacy-'+name+'.cmd')).is_file())
        for path in ('scripts/serve_local.py','src/themescope/local_history.py','tests/fixtures/v1/latest_snapshot.json'):
            self.assertTrue((ROOT/path).is_file(),path)
