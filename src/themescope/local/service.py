"""Full-lifecycle refresh mutual exclusion, incremental inputs and atomic results."""
from dataclasses import replace,asdict
from datetime import datetime,timezone
from pathlib import Path
import json,logging,os,sqlite3,tempfile,threading,time
from copy import deepcopy
from ..local_refresh_lock import RefreshLock,RefreshBusy
from ..storage import Store,canonical,is_busy
from ..domain import load_configuration
from ..corporate_actions import validate_actions,action_audit,apply_membership_ends
from ..market.rosters import load as load_rosters,effective
from ..market.layer import market_layer
from ..providers.base import Schedule,FixtureProvider
from ..providers.alpaca import AlpacaMarketDataProvider
from ..providers.cache import prepare
from ..providers.earnings import optional_earnings,AlphaVantageEarnings
from ..themes.calculations import bar_map,usable
from ..themes.index import build_index,IndexUnavailable
from ..themes.history import ThemeHistory
from ..research.engine import calculate_session
from ..research.context import enrich
from ..research.exports import reviewed_mapping
from ..research.universe import approved_launch_universe,approved_launch_close_membership,contiguous_suffix
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
        self._status_unpersisted=False
        self.state={'state':'idle','progress':'Ready','target_session':None,'provider_health':'Not checked','error':None}
        # Eager startup, before create_app/Uvicorn can accept browser polling.
        # SQLite serializes concurrent process initializers; no refresh lock is weakened.
        store=Store(self.db)
        try:self._publication_version,self._committed_snapshot=store.active_publication()
        finally:store.close()
        self._snapshot_busy=False

    def snapshot(self):
        # Readers cannot initialize, migrate, write or see an uncommitted pointer.
        store=None
        try:
            store=Store(self.db,read_only=True)
            version,snapshot=store.active_publication()
        except sqlite3.OperationalError as error:
            if not is_busy(error):
                raise  # I/O failures, corruption and SQL/schema errors stay visible.
            logging.getLogger(__name__).warning(
                'SQLite snapshot read remained busy after bounded wait; using last committed publication')
            with self.guard:
                self._snapshot_busy=True
                return deepcopy(self._committed_snapshot)
        finally:
            if store is not None:store.close()
        with self.guard:
            self._snapshot_busy=False
        return self._remember_committed(version,snapshot)

    def _remember_committed(self,version,snapshot):
        with self.guard:
            # A slower read finishing later must not replace a newer committed cache.
            if version>=self._publication_version:
                self._publication_version=version
                self._committed_snapshot=snapshot
            return deepcopy(self._committed_snapshot)

    def status(self):
        # A DB wait may span refresh completion: sample operational state afterward.
        snapshot=self.snapshot()
        with self.guard:
            state=dict(self.state)
            running=self.running
            # Never let an older recovery file hide an update that failed to persist.
            if not self._status_unpersisted:
                try:
                    persisted=json.loads((self.runtime/'status.json').read_text(encoding='utf-8'))
                    if (isinstance(persisted,dict) and persisted.get('state') in
                            ('idle','running','success','failed','interrupted') and
                            isinstance(persisted.get('progress'),str)):
                        state=persisted
                except (OSError,ValueError):pass
            state['snapshot_read']='busy_last_committed' if self._snapshot_busy and snapshot else 'busy_no_snapshot' if self._snapshot_busy else 'ready'
        state.update({'last_successful_session':snapshot.get('session') if snapshot else None,
                      'last_successful_refresh':snapshot.get('refreshed_at') if snapshot else None,
                      'completeness':snapshot.get('completeness') if snapshot else None,'mode':self.mode,
                      'theme_layer':snapshot.get('theme_layer') if snapshot else None})
        # An interrupted process leaves an honest recovery message, never a live lock.
        if state.get('state')=='running' and not running:
            try:
                with RefreshLock(self.lock_path):state.update(state='interrupted',progress='Previous refresh stopped; retry is available')
            except RefreshBusy:pass
        return state

    def _status(self,**updates):
        # Operational metadata is best-effort; SQLite publication is authoritative.
        # Serialize status writers under the guard so old retries cannot overwrite
        # a newer in-memory update. Retry waits total at most 70 ms per update.
        with self.guard:
            self.state.update(updates)
            self._status_unpersisted=True
            path=None
            try:
                with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',
                        prefix='status-',suffix='.tmp',dir=self.runtime,delete=False) as handle:
                    path=Path(handle.name)
                    json.dump(self.state,handle)
                # Close the temporary handle before Windows atomic replacement.
                delays=(.01,.02,.04)
                for attempt in range(len(delays)+1):
                    try:
                        os.replace(path,self.runtime/'status.json')
                        self._status_unpersisted=False
                        break
                    except OSError as error:
                        transient=isinstance(error,PermissionError) or getattr(error,'winerror',None) in (5,32,33)
                        if not transient or attempt==len(delays):break
                        time.sleep(delays[attempt])
            except (OSError,ValueError,TypeError):
                pass  # Missing/locked/unwritable metadata must never fail refresh.
            finally:
                if path is not None:
                    try:path.unlink(missing_ok=True)
                    except OSError:pass  # Sharing violations can also prevent cleanup.

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
            reached=tuple(a for a in config.corporate_actions if a.last_trading_session<=target)
            if reached:
                config=replace(apply_membership_ends(config,reached,days),corporate_actions=config.corporate_actions)
            start=max(0,end-config.methodology['bootstrap_sessions'])
            launch=config.methodology.get('launch_rebalance_session')
            if launch and launch in days and launch<=target:start=min(start,max(0,days.index(launch)-config.methodology['bootstrap_sessions']))
            sessions=tuple(days[start:end+1]);calendar=tuple(days[start:])
            rosters=self.rosters_factory()
            for benchmark in ('SPY','QQQ'):
                if effective(rosters,benchmark,target) is None:
                    blockers.append(f'Effective {benchmark} constituent roster missing for {target}')
            # Blocked production membership is never activated by this application.
            working=config if self.mode=='fixture' or not blockers else replace(config,memberships=())
            research=approved_launch_universe(config,target,days,activation_blockers=blockers) if self.mode!='fixture' else None
            launch_research=approved_launch_close_membership(config,target,days,activation_blockers=blockers) if self.mode!='fixture' else None
            init=sessions[0] if self.mode=='fixture' else launch
            initialization_members={}
            if init and init<=target and init in calendar:
                first_earned=calendar[calendar.index(init)+1]
                for theme in working.themes:
                    initialization_members[theme.theme_id]=working.members_on(theme.theme_id,first_earned)
            target_names={m.ticker for t in working.themes for m in working.members_on(t.theme_id,target)}
            next_target=calendar[calendar.index(target)+1]
            target_names.update(m.ticker for t in working.themes for m in working.members_on(t.theme_id,next_target))
            names=set(target_names)
            if research:
                target_names.update(m.ticker for m in research.relationships if m.calculation_eligible)
                names.update(target_names)
            # Launch inputs come from post-close holdings, not earned membership on L.
            names.update(m.ticker for members in initialization_members.values() for m in members)
            if initialization_members:
                next_target=calendar[calendar.index(target)+1]
                active_ids={t.theme_id for t in working.themes if t.status=='active'}
                names.update(m.ticker for m in working.memberships if m.theme_id in active_ids and m.calculation_eligible
                             and m.effective_from and m.effective_from<=next_target
                             and (not m.effective_to or m.effective_to>first_earned))
            for benchmark in ('SPY','QQQ'):
                roster=effective(rosters,benchmark,target)
                if roster:
                    names.update(roster.tickers);target_names.update(roster.tickers)
            names.update(('SPY','QQQ','IWM'));target_names.update(('SPY','QQQ','IWM'))
            actions=tuple(a for a in config.corporate_actions if a.ticker in names)
            validate_actions(tuple(a for a in actions if a.last_trading_session<=target),days)
            self._status(target_session=target,progress='Fetching missing sessions and repair window')
            store=Store(self.db)
            prepared=prepare(store,provider,names,sessions,terminal_actions=actions,target_symbols=target_names,ohlc_symbols=('SPY','QQQ'))
            bars=bar_map(prepared.bars)
            self._status(progress='Calculating market, themes and peer comparisons',provider_health='Healthy')
            market=market_layer(bars,sessions,rosters)
            market['rosters']=[asdict(r) for r in rosters]
            indices={};seeds={};series={};research_indices={}
            if research:
                for theme in working.themes:
                    members=research.members_for(theme.theme_id)
                    if not members:continue
                    seed_names=tuple(m.ticker for m in members)
                    recent=contiguous_suffix(sessions,lambda day:all(usable(bars.get((s,day))) for s in seed_names))
                    if not recent:continue
                    try:
                        research_indices[theme.theme_id]=build_index(working,theme.theme_id,bars,calendar,recent[0],target,
                                                                   bootstrap_symbols=seed_names)
                    except IndexUnavailable:pass  # Insufficient data leaves this trend unavailable.
            if init and init<=target and init in calendar:
                for theme in working.themes:
                    if theme.status!='active' or not initialization_members.get(theme.theme_id):continue
                    try:
                        indices[theme.theme_id]=build_index(working,theme.theme_id,bars,calendar,init,target,terminal_values=prepared.terminal_values)
                    except IndexUnavailable:
                        continue
                    series[theme.theme_id]=working.methodology['version']+':'+init
                    if init!=sessions[0]:
                        seed_names=tuple(m.ticker for m in initialization_members[theme.theme_id])
                        try:
                            seeds[theme.theme_id]=build_index(working,theme.theme_id,bars,calendar,sessions[0],init,bootstrap_symbols=seed_names)
                        except IndexUnavailable:
                            pass  # Incomplete bootstrap cannot erase a valid live launch point.
            previous={}
            if len(sessions)>1 and not research:
                for theme in working.themes:
                    row=store.theme_at(theme.theme_id,sessions[-2],working.methodology['version'])
                    if row and row.get('history'):previous[theme.theme_id]=ThemeHistory(**row['history'])
            if self.mode=='fixture':mapping={s:{'status':'verified','symbol':'NASDAQ:'+s} for s in names}
            else:
                has_members=bool(research or launch_research) or any(working.members_on(t.theme_id,target) for t in working.themes)
                mapping=reviewed_mapping(working,json.loads((self.root/'config/tradingview_symbols.json').read_text())['symbols']) if has_members else {}
            snapshot=calculate_session(working,bars,sessions,target,market['decision']['direction'],indices,series,mapping,
                                       previous=previous,bootstrap_seeds=seeds,
                                       research_universe=research,research_indices=research_indices,
                                       research_members_for=launch_research.members_for if launch_research else None)
            # Hash the actual source config, even while blocked calculations are empty.
            from hashlib import sha256
            snapshot['configuration_hash']=sha256(canonical({'themes':config,'rosters':rosters}).encode()).hexdigest()
            snapshot['production_blockers']=blockers
            snapshot['theme_layer']=research.metadata() if research else {
                'state':'activation_blocked' if blockers and self.mode!='fixture' else 'pre_launch' if launch and target<launch else 'initialized' if target==launch else 'live',
                'research_session':target,'membership_basis':'effective_membership',
                'official_live_history':bool(init and init<=target and indices),
                'launch_rebalance_session':launch,'first_earned_session':calendar[calendar.index(launch)+1] if launch in calendar else None}
            if launch_research:
                snapshot['research_membership_basis']='approved_launch_membership'
                snapshot['research_membership_basis_session']=launch_research.first_earned_session
            snapshot['market']=market;snapshot['synthetic_fixture']=self.mode=='fixture'
            snapshot['today_plan']=ACTION_SENTENCES[market['decision']['direction']]
            self._status(progress='Checking optional earnings')
            earnings=None if self.mode=='fixture' else AlphaVantageEarnings(os.environ.get('ALPHAVANTAGE_API_KEY'))
            snapshot['earnings']=optional_earnings(earnings,{r['ticker'] for r in snapshot['relationships']})
            previous_context=store.research_at(sessions[-2],config.methodology['version']) if len(sessions)>1 else None
            snapshot=enrich(snapshot,bars,sessions,previous_context,
                {m.ticker:m.company for m in config.memberships if m.company})
            snapshot['refreshed_at']=datetime.now(timezone.utc).isoformat()
            snapshot['completeness']={'required':len(target_names),'valid_target':len(target_names),'complete':True}
            if prepared.terminal_values:
                snapshot['corporate_actions']=action_audit(actions,prepared.terminal_values,prepared.identity)
                terminal_count=sum(v.valuation_session==target and v.ticker in target_names for v in prepared.terminal_values)
                snapshot['completeness'].update(trading_target=len(target_names)-terminal_count,
                    terminal_target=terminal_count,historical_inputs=len(names-target_names))
            snapshot['provider_health']={'identity':prepared.identity,'status':'Healthy'}
            snapshot['performance']={'fetched_observations':prepared.fetched,'batch_requests':prepared.requests}
            self._status(progress='Committing snapshot and exports')
            with store.refresh(target,snapshot['methodology'],snapshot['configuration_hash']) as run:
                run.bars(prepared.bars,identity=prepared.identity)
                for row in snapshot['themes']:run.theme(row['theme_id'],row)
                for row in snapshot['relationships']:run.stock(row['ticker'],row['theme_id'],row)
                for theme,points in seeds.items():
                    for point in points:
                        if point.session<init:run.index(theme,point.session,point)
                for theme,points in indices.items():
                    for point in points:run.index(theme,point.session,point)
                run.db.execute('INSERT INTO market_snapshot VALUES(?,?)',(run.run,canonical(market)))
                run.publish(snapshot,required_symbols=target_names,terminal_actions=actions)
                committed_candidate=store.active_publication()
            # Only visible after the refresh context's COMMIT has succeeded. On
            # rollback this is never cached; an older replay retains its true pointer.
            self._remember_committed(*committed_candidate)
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
    config=replace(config,methodology=dict(config.methodology,launch_rebalance_session=sessions[0]))
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
