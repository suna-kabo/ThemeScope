"""Full-lifecycle refresh mutual exclusion, incremental inputs and atomic results."""
from dataclasses import replace,asdict
from datetime import datetime,timezone
from pathlib import Path
import json,os,threading,time
from ..local_refresh_lock import RefreshLock,RefreshBusy
from ..storage import Store,canonical
from ..domain import load_configuration
from ..market.rosters import load as load_rosters,effective
from ..market.layer import market_layer
from ..providers.base import Schedule,FixtureProvider
from ..providers.alpaca import AlpacaMarketDataProvider
from ..providers.cache import prepare
from ..providers.earnings import optional_earnings,AlphaVantageEarnings
from ..themes.calculations import bar_map
from ..themes.index import build_index,IndexUnavailable
from ..themes.history import ThemeHistory
from ..research.engine import calculate_session
from ..research_policy import ACTION_SENTENCES

class RefreshService:
    def __init__(self,root,*,mode='live',provider_factory=None,config_factory=None,records=None,rosters_factory=None):
        self.root=Path(root);self.mode=mode
        self.runtime=self.root/'runtime'/('vnext-fixture' if mode=='fixture' else 'vnext')
        self.runtime.mkdir(parents=True,exist_ok=True)
        self.db=self.runtime/'runtime.sqlite'
        self.lock_path=self.root/'runtime/refresh.lock'
        self.guard=threading.Lock();self.running=False
        self.provider_factory=provider_factory;self.config_factory=config_factory or (lambda:load_configuration(self.root))
        self.records=records;self.rosters_factory=rosters_factory or (lambda:load_rosters(self.root))
        self.state={'state':'idle','progress':'Ready','target_session':None,'provider_health':'Not checked','error':None}

    def snapshot(self):
        store=Store(self.db)
        try:return store.active()
        finally:store.close()

    def status(self):
        with self.guard:state=dict(self.state)
        path=self.runtime/'status.json'
        if path.exists():
            try:state=json.loads(path.read_text())
            except (ValueError,OSError):pass
        snapshot=self.snapshot()
        state.update({'last_successful_session':snapshot.get('session') if snapshot else None,
                      'last_successful_refresh':snapshot.get('refreshed_at') if snapshot else None,
                      'completeness':snapshot.get('completeness') if snapshot else None,'mode':self.mode})
        # An interrupted process leaves an honest recovery message, never a live lock.
        if state.get('state')=='running' and not self.running:
            try:
                with RefreshLock(self.lock_path):state.update(state='interrupted',progress='Previous refresh stopped; retry is available')
            except RefreshBusy:pass
        return state

    def _status(self,**updates):
        with self.guard:
            self.state.update(updates)
            path=self.runtime/'status.tmp'
            path.write_text(json.dumps(self.state),encoding='utf-8');os.replace(path,self.runtime/'status.json')

    def _reserve(self):
        with self.guard:
            if self.running:raise RefreshBusy('Refresh already active')
            lock=RefreshLock(self.lock_path);lock.__enter__();self.running=True
            return lock

    def start(self):
        lock=self._reserve()
        try:
            self._status(state='running',progress='Starting',error=None)
            threading.Thread(target=self._execute,args=(lock,),daemon=True).start()
        except BaseException:
            lock.__exit__();self.running=False;raise

    def refresh(self):
        lock=self._reserve()
        return self._execute(lock)

    def _execute(self,lock):
        started=time.perf_counter();store=None
        try:
            self._status(state='running',progress='Preparing provider and configuration',error=None)
            config=self.config_factory();blockers=config.production_blockers()
            records=self.records or json.loads((self.root/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
            schedule=Schedule(records)
            provider=self.provider_factory(schedule) if self.provider_factory else AlpacaMarketDataProvider(
                os.environ.get('APCA_API_KEY_ID'),os.environ.get('APCA_API_SECRET_KEY'),schedule)
            target=provider.get_latest_completed_session()
            days=sorted(r['session'] for r in records);end=days.index(target)
            start=max(0,end-config.methodology['bootstrap_sessions'])
            launch=config.methodology.get('launch_rebalance_session')
            if launch and launch in days and launch<=target:start=min(start,max(0,days.index(launch)-config.methodology['bootstrap_sessions']))
            sessions=tuple(days[start:end+1]);calendar=tuple(days[start:])
            rosters=self.rosters_factory()
            # Blocked production membership is never activated by this application.
            working=config if self.mode=='fixture' or not blockers else replace(config,memberships=())
            names={m.ticker for t in working.themes for m in working.members_on(t.theme_id,target)}
            for benchmark in ('SPY','QQQ'):
                roster=effective(rosters,benchmark,target)
                if roster:names.update(roster.tickers)
            names.update(('SPY','QQQ','IWM'))
            self._status(target_session=target,progress='Fetching missing sessions and repair window')
            store=Store(self.db)
            prepared=prepare(store,provider,names,sessions)
            bars=bar_map(prepared.bars)
            self._status(progress='Calculating market, themes and peer comparisons',provider_health='Healthy')
            market=market_layer(bars,sessions,rosters)
            market['rosters']=[asdict(r) for r in rosters]
            indices={};seeds={};series={}
            init=sessions[0] if self.mode=='fixture' else launch
            if init and init<=target and init in calendar:
                for theme in working.themes:
                    if theme.status!='active' or not working.members_on(theme.theme_id,target):continue
                    try:
                        indices[theme.theme_id]=build_index(working,theme.theme_id,bars,calendar,init,target)
                        series[theme.theme_id]=working.methodology['version']+':'+init
                        if init!=sessions[0]:
                            next_session=calendar[calendar.index(init)+1]
                            seed_names=tuple(m.ticker for m in working.members_on(theme.theme_id,next_session))
                            seeds[theme.theme_id]=build_index(working,theme.theme_id,bars,calendar,sessions[0],init,bootstrap_symbols=seed_names)
                    except IndexUnavailable:
                        indices.pop(theme.theme_id,None)
                        seeds.pop(theme.theme_id,None)
            previous={}
            if len(sessions)>1:
                for theme in working.themes:
                    row=store.theme_at(theme.theme_id,sessions[-2],working.methodology['version'])
                    if row and row.get('history'):previous[theme.theme_id]=ThemeHistory(**row['history'])
            if self.mode=='fixture':mapping={s:{'status':'verified','symbol':'NASDAQ:'+s} for s in names}
            else:
                has_members=any(working.members_on(t.theme_id,target) for t in working.themes)
                mapping=json.loads((self.root/'config/tradingview_symbols.json').read_text())['symbols'] if has_members else {}
            snapshot=calculate_session(working,bars,sessions,target,market['decision']['direction'],indices,series,mapping,
                                       previous=previous,bootstrap_seeds=seeds)
            # Hash the actual source config, even while blocked calculations are empty.
            from hashlib import sha256
            snapshot['configuration_hash']=sha256(canonical({'themes':config,'rosters':rosters}).encode()).hexdigest()
            snapshot['production_blockers']=blockers
            snapshot['market']=market;snapshot['synthetic_fixture']=self.mode=='fixture'
            snapshot['today_plan']=ACTION_SENTENCES[market['decision']['direction']]
            self._status(progress='Checking optional earnings')
            earnings=None if self.mode=='fixture' else AlphaVantageEarnings(os.environ.get('ALPHAVANTAGE_API_KEY'))
            snapshot['earnings']=optional_earnings(earnings,{r['ticker'] for r in snapshot['relationships']})
            snapshot['refreshed_at']=datetime.now(timezone.utc).isoformat()
            snapshot['completeness']={'required':len(names),'valid_target':len(names),'complete':True}
            snapshot['provider_health']={'identity':prepared.identity,'status':'Healthy'}
            snapshot['performance']={'fetched_observations':prepared.fetched,'batch_requests':prepared.requests}
            self._status(progress='Committing snapshot and exports')
            with store.refresh(target,snapshot['methodology'],snapshot['configuration_hash']) as run:
                run.bars(prepared.bars,identity=prepared.identity)
                for row in snapshot['themes']:run.theme(row['theme_id'],row)
                for row in snapshot['relationships']:run.stock(row['ticker'],row['theme_id'],row)
                for theme,points in indices.items():
                    for point in points:run.index(theme,point.session,point)
                run.db.execute('INSERT INTO market_snapshot VALUES(?,?)',(run.run,canonical(market)))
                run.publish(snapshot,required_symbols=names)
            self._status(state='success',progress='Refresh complete',elapsed_seconds=round(time.perf_counter()-started,3))
            return snapshot
        except Exception as error:
            from ..providers.base import ProviderError
            code=str(error) if isinstance(error,ProviderError) else 'refresh_failed'
            self._status(state='failed',progress='Refresh failed; previous successful dashboard and exports preserved',error=code,provider_health='Unavailable')
            return None
        finally:
            if store:store.close()
            lock.__exit__()
            with self.guard:self.running=False


def fixture_service(root):
    from scripts.vnext_fixture_report import fixture
    config,bars,sessions,target,indices,mapping=fixture()
    # Keep one subsequent calendar session available for earned-session timing.
    records=[{'session':s,'close':s+'T21:00:00+00:00'} for s in sessions]
    schedule=Schedule(records,now=lambda:datetime.fromisoformat(target+'T23:00:00+00:00'))
    extra=[]
    from ..themes.calculations import Bar
    from decimal import Decimal
    for symbol in ('SPY','QQQ','IWM'):
        for i,day in enumerate(sessions):extra.append(Bar(symbol,day,100+i,100+i,2000000))
    from ..domain import MarketRoster
    rosters=(MarketRoster('SPY',sessions[0],('AAA','BBB','AAC','AAD','AAE'),'Synthetic fixture'),
             MarketRoster('QQQ',sessions[0],('AAA','BBB','BBC','BBD','BBE'),'Synthetic fixture'))
    return RefreshService(root,mode='fixture',config_factory=lambda:config,records=records,
                          rosters_factory=lambda:rosters,provider_factory=lambda _:FixtureProvider(tuple(bars.values())+tuple(extra),schedule))
