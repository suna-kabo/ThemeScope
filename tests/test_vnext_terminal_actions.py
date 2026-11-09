"""Generic terminal events and launch boundaries; all prices are manufactured."""
from dataclasses import replace, asdict
from datetime import datetime
from decimal import Decimal as D, localcontext, ROUND_DOWN, Inexact
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch
import csv,json,tempfile,unittest
from src.themescope.corporate_actions import (TerminalAction,CorporateActionError,load_actions,
    apply_membership_ends,validate_actions,resolve_values,action_audit)
from src.themescope.domain import Configuration,Theme,ThemeStatus,Membership,Role,MarketRoster,load_configuration
from src.themescope.local.service import RefreshService
from src.themescope.providers.base import FixtureProvider,Schedule,ProviderError
from src.themescope.providers.cache import prepare
from src.themescope.research.engine import calculate_session
from src.themescope.research.primary import qualifies
from src.themescope.storage import Store,canonical
from src.themescope.themes.calculations import POLICY,Bar,bar_map
from src.themescope.themes.index import build_index,IndexUnavailable

ROOT=Path(__file__).resolve().parents[1]
L='2026-11-06';E='2026-11-09';N='2026-11-10'
RECORDS=json.loads((ROOT/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
ALL=tuple(r['session'] for r in RECORDS)
DAYS=ALL[ALL.index(L)-253:ALL.index(N)+2]


def action(**changes):
    # TAKE/NEXT are fictional: no ticker-specific logic is exercised.
    values=dict(event_id='test-terminal',ticker='TAKE',event_type='acquisition',
        last_trading_session=L,valuation_session=E,membership_effective_to=N,
        cash_per_share='95.30',stock_ticker='NEXT',stock_ratio='0.9799',replacement_ticker=None,
        source='https://example.org/manufactured-test-notice',source_notice='Manufactured test',
        approval_status='approved',approval_reference='Explicit test approval',reviewed_on='2026-11-10')
    return TerminalAction(**dict(values,**changes))


def configuration(event):
    members=tuple(Membership(s,'Synthetic '+s,'test',Role.CORE,E,None,'2026-11-05','fixture') for s in ('TAKE',*'ABCDE'))
    config=Configuration((Theme('test','Manufactured','Fixture',ThemeStatus.ACTIVE,'Fixture only','Fixture','Other'),),
        members,{},dict(POLICY,launch_rebalance_session=L,production_enabled=True),{'industry_rule_registry_status':'approved'})
    if event.replacement_ticker:
        config=replace(config,memberships=config.memberships+(replace(members[0],ticker=event.replacement_ticker,
            company='Manufactured replacement',effective_from=N),))
    return apply_membership_ends(config,(event,),ALL)


def prices():
    rows=[]
    for s in ('TAKE','NEXT',*'ABCDE','SPY','QQQ','IWM'):
        for i,day in enumerate(DAYS):
            if s=='TAKE' and day>L:continue
            raw=100 if s!='NEXT' else 50
            if day>=N and s in 'ABCDE':raw=110
            if s in ('SPY','QQQ','IWM'):raw=100+D(i)/10
            if s=='NEXT' and day>=N:raw=500  # Must not revalue the retired holding later.
            adjusted=80 if s=='TAKE' else raw/2 if s=='NEXT' else raw
            rows.append(Bar(s,day,adjusted,raw,2000000))
    return bar_map(rows)


class TerminalActionTests(unittest.TestCase):
    def test_cash_stock_mixed_and_known_terminal_delisting_value(self):
        data=prices()
        for terms,expected in ((dict(cash_per_share='120',stock_ticker=None,stock_ratio='0'),D(120)),
            (dict(cash_per_share='0',stock_ratio='2'),D(100)),({},D('144.295')),
            (dict(event_type='delisting',cash_per_share='0',stock_ticker=None,stock_ratio='0'),D(0))):
            with self.subTest(terms=terms):
                event=action(**terms);value=resolve_values((event,),data,E)[0]
                self.assertEqual(value.value,expected)
                self.assertEqual(value.previous_raw_close,100)
                self.assertNotIn(('TAKE',E),data)
                point=build_index(configuration(event),'test',data,DAYS,L,E,terminal_values=(value,))[-1]
                expected=100*(D(5)+expected/D(100))/6
                self.assertAlmostEqual(point.level,expected,places=25)
        with localcontext() as ctx:
            ctx.prec=5;ctx.rounding=ROUND_DOWN;ctx.traps[Inexact]=True
            self.assertEqual(resolve_values((action(),),data,E)[0].value,D('144.295'))

    def test_malformed_unapproved_missing_and_duplicate_terms_fail_closed(self):
        for terms in (dict(cash_per_share='NaN'),dict(stock_ratio='-1'),dict(cash_per_share=95.3),
            dict(stock_ticker=None),dict(currency='EUR'),dict(approval_status='pending'),
            dict(approval_reference=''),dict(source='http://example.org'),dict(stock_ticker='TAKE'),
            dict(event_type='unknown'),dict(replacement_ticker='UNAPPROVED')):
            with self.subTest(terms=terms),self.assertRaises(CorporateActionError):action(**terms)
        with self.assertRaises(CorporateActionError):validate_actions((action(),action()))
        with self.assertRaises((ValueError,CorporateActionError)):validate_actions((action(valuation_session='2026-11-07'),),ALL)
        with tempfile.TemporaryDirectory() as d:
            folder=Path(d)/'config/vnext';folder.mkdir(parents=True)
            (folder/'corporate_actions.json').write_text('{"schema_version":1,"events":[{}]}')
            with self.assertRaises(CorporateActionError):load_actions(d)
            bad=dict(asdict(action()),cash_per_share='-1')
            (folder/'corporate_actions.json').write_text(json.dumps({'schema_version':1,'events':[bad]},default=str))
            with self.assertRaisesRegex(CorporateActionError,'invalid_terminal_action:TAKE'):load_actions(d)

    def test_independent_numerical_oracle_and_no_future_old_holding(self):
        event=action();config=configuration(event);data=prices()
        values=resolve_values((event,),data,N)
        points=build_index(config,'test',data,DAYS,L,N,terminal_values=values)
        # Independent rational oracle, raw successor=50, raw prior=100. Adjusted
        # prices deliberately differ (NEXT=25, TAKE=80) to catch unit mistakes.
        terminal=Fraction(9530,100)+Fraction(9799,10000)*50
        expected=100*(Fraction(5,6)+terminal/Fraction(600))
        oracle=D(expected.numerator)/D(expected.denominator)
        self.assertEqual(oracle,D('107.3825'))
        self.assertAlmostEqual(points[1].level,oracle,places=25)
        self.assertAlmostEqual(points[2].level,D('118.12075'),places=25)
        self.assertEqual((points[0].level,points[0].earned_symbols),(100,()))
        self.assertIn('TAKE',dict(points[0].weights))
        self.assertIn('TAKE',points[1].earned_symbols)
        self.assertNotIn('TAKE',dict(points[1].weights))
        self.assertNotIn('TAKE',points[2].earned_symbols)
        self.assertFalse(any(m.ticker=='TAKE' for m in config.members_on('test',N)))
        for invalid in ((replace(values[0],value=D(999)),), (values[0],values[0])):
            with self.assertRaises(ValueError):build_index(config,'test',data,DAYS,L,N,terminal_values=invalid)
        with self.assertRaises(ValueError):
            build_index(replace(config,corporate_actions=()),'test',data,DAYS,L,N,terminal_values=values)

    def test_research_and_primary_cannot_use_economic_value(self):
        event=action();config=configuration(event);data=prices()
        values=resolve_values((event,),data,E)
        index=build_index(config,'test',data,DAYS,L,E,terminal_values=values)
        snapshot=calculate_session(config,data,DAYS,E,'Long bias',{'test':index},{'test':'fixture'}, {})
        row=next(r for r in snapshot['relationships'] if r['ticker']=='TAKE')
        self.assertIsNone(row['relative'].w)
        self.assertIsNone(row['relative'].er1);self.assertIsNone(row['relative'].er3)
        self.assertFalse(row['eligibility'].available);self.assertFalse(row['eligibility'].eligible)
        self.assertIsNone(row['eligibility'].close);self.assertIsNone(row['eligibility'].average_volume)
        self.assertFalse(row['qualifies']);self.assertFalse(qualifies('Primary long',D(1),row['eligibility']))
        self.assertEqual(snapshot['themes'][0]['breadth'][0].valid,5)
        self.assertEqual(snapshot['themes'][0]['breadth'][0].configured,6)
        self.assertEqual(snapshot['exports']['combined'],'')
        with self.assertRaises(IndexUnavailable):build_index(config,'test',data,DAYS,L,E)

    def test_successor_missing_unusable_and_original_trading_conflict_fail(self):
        for kind in ('missing','zero_volume','incomplete'):
            data=prices()
            row=data.pop(('NEXT',E))
            if kind!='missing':data['NEXT',E]=replace(row,volume=0) if kind=='zero_volume' else replace(row,completed=False)
            with self.subTest(kind=kind),self.assertRaisesRegex(CorporateActionError,'terminal_successor_data_missing:NEXT'):
                resolve_values((action(),),data,E)
        data=prices();data['TAKE',E]=Bar('TAKE',E,100,100,1)
        with self.assertRaisesRegex(CorporateActionError,'terminal_trading_bar_conflict:TAKE'):resolve_values((action(),),data,E)

    def test_explicit_symbol_conversion_requires_approved_replacement_membership(self):
        event=action(event_type='symbol_conversion',cash_per_share='0',stock_ratio='2',replacement_ticker='NEXT')
        config=configuration(event);data=prices()
        points=build_index(config,'test',data,DAYS,L,E,terminal_values=resolve_values((event,),data,E))
        self.assertIn('NEXT',dict(points[-1].weights));self.assertNotIn('TAKE',dict(points[-1].weights))
        self.assertEqual({m.ticker for m in config.members_on('test',N)},{'NEXT',*'ABCDE'})
        with self.assertRaisesRegex(CorporateActionError,'approved_replacement_membership_missing'):
            apply_membership_ends(replace(config,memberships=tuple(m for m in config.memberships if m.ticker!='NEXT')),(event,),ALL)

    def test_terminal_exception_cannot_cover_a_later_required_session(self):
        with tempfile.TemporaryDirectory() as d:
            store=Store(Path(d)/'fixture.sqlite')
            try:
                schedule=Schedule(RECORDS,now=lambda:datetime.fromisoformat(N+'T23:00:00+00:00'))
                provider=FixtureProvider(tuple(prices().values()),schedule)
                with self.assertRaisesRegex(ProviderError,'required_target_session_missing_or_zero_volume:TAKE'):
                    prepare(store,provider,('TAKE',*'ABCDE'),DAYS[:DAYS.index(N)+1],terminal_actions=(action(),))
                self.assertIsNone(store.active())
            finally:store.close()

    def test_real_ledger_amends_future_interval_without_rewriting_launch_csv(self):
        config=load_configuration(ROOT);events=load_actions(ROOT)
        event=next(a for a in events if a.ticker=='ROKU')
        self.assertEqual((event.cash_per_share,event.stock_ticker,event.stock_ratio),(D('95.30'),'FOXA',D('0.9799')))
        self.assertEqual(event.source,'https://www.nasdaqtrader.com/TraderNews.aspx?id=eca2026-806')
        member=next(m for m in config.memberships if m.ticker=='ROKU')
        self.assertEqual((member.effective_from,member.effective_to),(E,N))
        self.assertTrue(member.active_on(E));self.assertFalse(member.active_on(N))
        with (ROOT/'config/vnext/memberships.csv').open(newline='',encoding='utf-8') as f:
            original=next(r for r in csv.DictReader(f) if r['ticker']=='ROKU')
        self.assertEqual(original['effective_to'],'');self.assertEqual(original['effective_from'],E)


class TerminalRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.target=L;self.data=prices();self.providers=[]
        self.event=action();self.config=configuration(self.event)
        folder=self.root/'config';folder.mkdir()
        (folder/'tradingview_symbols.json').write_text(json.dumps({'symbols':{s:{'status':'verified','symbol':'NASDAQ:'+s} for s in ('TAKE','NEXT',*'ABCDE')}}))
        def provider(_):
            schedule=Schedule(RECORDS,now=lambda:datetime.fromisoformat(self.target+'T23:00:00+00:00'))
            instance=FixtureProvider(tuple(self.data.values()),schedule);self.providers.append(instance);return instance
        rosters=tuple(MarketRoster(s,'2026-11-05',tuple('ABCDE'),'Manufactured fixture') for s in ('SPY','QQQ'))
        self.service=RefreshService(self.root,config_factory=lambda:self.config,provider_factory=provider,
            rosters_factory=lambda:rosters,records=RECORDS)
        self.env=patch.dict('os.environ',{'ALPHAVANTAGE_API_KEY':''});self.env.start();self.addCleanup(self.env.stop)

    def refresh(self,day):
        self.target=day;result=self.service.refresh()
        self.assertIsNotNone(result,self.service.status());return result

    def test_launch_merger_and_adjacent_live_transition_replay_and_pinned_audit(self):
        launch=self.refresh(L)
        store=Store(self.service.db)
        try:prior=[tuple(r) for r in store.connection.execute('SELECT * FROM theme_index ORDER BY run_id,session')]
        finally:store.close()
        first=self.refresh(E);theme=first['themes'][0]
        self.assertAlmostEqual(theme['index']['level'],D('107.3825'),places=25)
        self.assertTrue(all(v is None for v in theme['transition'].values()))
        self.assertFalse(launch['themes'][0]['history']['signal_eligible'])
        self.assertEqual(first['completeness'],{'required':9,'valid_target':9,'complete':True,'trading_target':8,'terminal_target':1,'historical_inputs':0})
        self.assertTrue(any(names==('NEXT',) and start==E and end==E for names,start,end in self.providers[-1].calls))
        second=self.refresh(N)
        self.assertNotIn('TAKE',{r['ticker'] for r in second['relationships']})
        self.assertIsNotNone(second['themes'][0]['transition']['priority_change'])
        self.assertIsNotNone(second['themes'][0]['transition']['newly_bullish'])
        self.assertEqual((second['completeness']['required'],second['completeness']['terminal_target'],second['completeness']['historical_inputs']),(8,0,1))
        self.assertFalse(any('TAKE' in names for names,start,end in self.providers[-1].calls))
        store=Store(self.service.db)
        try:
            for row in prior:
                self.assertEqual(tuple(store.connection.execute('SELECT * FROM theme_index WHERE run_id=? AND theme_id=? AND session=?',row[:3]).fetchone()),row)
            self.assertEqual(store.connection.execute('SELECT count(*) FROM daily_bars WHERE ticker=? AND session>?',('TAKE',L)).fetchone()[0],0)
            self.assertEqual(store.connection.execute('PRAGMA user_version').fetchone()[0],2)
            current=store.active()
            self.assertEqual(current['corporate_actions']['valuations'][0]['value'],'144.2950')
            self.assertTrue(store.connection.execute('SELECT observation_id FROM daily_bars WHERE ticker=? AND session=?',('NEXT',E)).fetchone())
        finally:store.close()
        self.assertIsNotNone(self.refresh(N))

    def test_missing_successor_or_unknown_event_preserves_previous_success(self):
        prior=self.refresh(L)
        self.target=E;del self.data['NEXT',E]
        self.assertIsNone(self.service.refresh())
        self.assertIn('NEXT',self.service.status()['error']);self.assertEqual(self.service.snapshot(),json.loads(canonical(prior)))
        self.data=prices();self.config=replace(self.config,corporate_actions=())
        self.assertIsNone(self.service.refresh())
        self.assertIn('TAKE',self.service.status()['error']);self.assertEqual(self.service.snapshot(),json.loads(canonical(prior)))
        self.config=configuration(self.event);self.data['TAKE',E]=Bar('TAKE',E,100,100,2000000)
        self.assertIsNone(self.service.refresh())
        self.assertIn('terminal_trading_bar_conflict:TAKE',self.service.status()['error'])
        self.assertEqual(self.service.snapshot(),json.loads(canonical(prior)))

    def test_storage_revalidates_economic_proof_and_cannot_bypass_unknown_symbol(self):
        store=Store(self.service.db)
        try:
            data=prices();schedule=Schedule(RECORDS,now=lambda:datetime.fromisoformat(E+'T23:00:00+00:00'))
            provider=FixtureProvider(tuple(data.values()),schedule)
            prepared=prepare(store,provider,('TAKE',*'ABCDE'),DAYS[:DAYS.index(E)+1],terminal_actions=(self.event,))
            audit=action_audit((self.event,),prepared.terminal_values,provider.identity)
            for required,events,payload in ((('TAKE','UNKNOWN'),(self.event,),{'corporate_actions':audit}),
                (('TAKE',),(),{'corporate_actions':audit}), (('TAKE',),(self.event,),{'corporate_actions':dict(audit,valuations=[])})):
                with self.subTest(required=required,events=events),self.assertRaises(ValueError):
                    with store.refresh(E,'themescope-vnext-1','fixture') as run:
                        run.bars(prepared.bars,identity=provider.identity);run.publish(payload,required_symbols=required,terminal_actions=events)
            self.assertIsNone(store.active())
            self.assertEqual(store.connection.execute('SELECT count(*) FROM observations').fetchone()[0],0)
        finally:store.close()
