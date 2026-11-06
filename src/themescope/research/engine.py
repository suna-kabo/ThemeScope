"""Offline vNext session orchestration; legacy runtime remains untouched.

Consumes explicit completed sessions, typed price data and index histories. No
provider, launch-date selection, evidence approval, or Market Matrix calculation.
"""
from dataclasses import asdict, replace
from hashlib import sha256
from ..storage import canonical
from ..themes.calculations import benchmarks, breadth, calendar, relative, usable
from ..themes.index import ema, indicators
from ..themes.history import ThemeHistory, transitions, HISTORY_VERSION
from .primary import daily_eligibility, priority, qualifies, side
from .exports import Qualification, exports
from .universe import contiguous_suffix

SNAPSHOT_VERSION='themescope-vnext-snapshot-1'


def calculate_session(configuration, bars, sessions, target, market_direction, index_histories,
                      series_ids, symbol_mapping, *, previous=None, bootstrap_seeds=None,
                      research_universe=None, research_indices=None):
    sessions=calendar(sessions)
    end=sessions.index(target)
    previous=previous or {}
    bootstrap_seeds=bootstrap_seeds or {}
    research_indices=research_indices or {}
    if research_universe:
        if (research_universe.research_session!=target
                or research_universe.launch_rebalance_session!=configuration.methodology.get('launch_rebalance_session')
                or target>=research_universe.launch_rebalance_session or configuration.production_blockers()):
            raise ValueError('Approved pre-launch research selection required')
        if index_histories or series_ids or bootstrap_seeds:
            raise ValueError('Research and official index histories must remain separate')
    elif research_indices:
        raise ValueError('Explicit research universe required for research indices')
    members_for=research_universe.members_for if research_universe else lambda theme_id:configuration.members_on(theme_id,target)
    metrics,scores,returns=benchmarks(configuration,bars,sessions,target,members_for=members_for)
    symbols=sorted({m.ticker for t in configuration.themes for m in members_for(t.theme_id)})
    eligibility={s:daily_eligibility(bars,s,sessions,target,configuration.methodology) for s in symbols}
    stock_emas={}
    closes={}
    for symbol in symbols:
        rows=[bars.get((symbol,session)) for session in sessions[:end+1]]
        prices=[r.adjusted_close if usable(r) else None for r in rows]
        if research_universe:prices=contiguous_suffix(prices,lambda value:value is not None)
        stock_emas[symbol]=tuple(ema(prices,n) for n in configuration.methodology['ema_periods'])
        closes[symbol]=prices[-1]
    themes=[]
    relationships=[]
    qualified=[]
    for theme in sorted(configuration.themes,key=lambda t:t.theme_id):
        members=members_for(theme.theme_id)
        names=[m.ticker for m in members]
        observation={'trend':'Unavailable','ema21':None,'ema50':None,'level':None,'bootstrap':False}
        if theme.status=='active' and theme.theme_id in index_histories:
            points=tuple(index_histories[theme.theme_id])
            if not points or points[-1].session!=target or any(p.bootstrap for p in points):
                raise ValueError('Target-session live index history required')
            observation=indicators(points,sessions,bootstrap=bootstrap_seeds.get(theme.theme_id,()),
                                   policy=configuration.methodology)[-1]
        if research_universe:
            points=tuple(research_indices.get(theme.theme_id,()))
            if points:
                if points[-1].session!=target or any(not p.bootstrap for p in points):
                    raise ValueError('Target-session bootstrap-only research history required')
                observation=indicators(points,sessions,policy=configuration.methodology)[-1]
            observation['bootstrap']=True
        series=research_universe.series_id if research_universe else series_ids.get(theme.theme_id,'')
        earned=index_histories.get(theme.theme_id,())
        current=ThemeHistory(target,theme.theme_id,configuration.methodology['version'],series,observation['trend'],'Watch',
                             bootstrap=bool(research_universe),
                             signal_eligible=not research_universe and bool(earned and earned[-1].earned_symbols))
        transition=transitions(previous.get(theme.theme_id),current,sessions)
        score=scores.get(theme.theme_id)
        label=priority(market_direction,score,observation['trend'],transition,configuration.methodology) if theme.status=='active' else 'Watch'
        current=replace(current,priority=label)
        transition=transitions(previous.get(theme.theme_id),current,sessions)
        themes.append({'theme_id':theme.theme_id,'name':theme.name,'family':theme.family,'status':theme.status,'score':score,
                       'returns':metrics.get(theme.theme_id),'index':observation,'priority':label,
                       'transition':transition,'history':asdict(current),
                       'breadth':tuple(breadth(names,closes,{s:stock_emas[s][i] for s in names},configuration.methodology)
                                       for i in (0,1))})
        for member in sorted(members,key=lambda m:m.ticker):
            performance=relative(member.ticker,names,*returns,policy=configuration.methodology)
            selected=qualifies(label,performance.w,eligibility[member.ticker])
            relationships.append({'ticker':member.ticker,'theme_id':theme.theme_id,'role':member.role,
                                  'relative':performance,'eligibility':eligibility[member.ticker], 'qualifies':selected})
            if selected:qualified.append(Qualification(member.ticker,theme.theme_id,member.role,performance.w))
    exported=exports(qualified,side(market_direction),symbol_mapping)
    for relationship in relationships:
        assignment=exported['assignments'].get(relationship['ticker'])
        relationship['assigned_section']=assignment['assigned_section'] if assignment else None
        relationship['also_qualifies_in']=assignment['also_qualifies_in'] if assignment else []
    return {'schema':SNAPSHOT_VERSION,'history_schema':HISTORY_VERSION,
            'methodology':configuration.methodology['version'],'session':target,
            'configuration_hash':sha256(canonical(configuration).encode()).hexdigest(),
            'market_direction':market_direction,'production_blockers':configuration.production_blockers(),
            'themes':themes,'relationships':relationships,'exports':exported}


def persist_fixture(store, snapshot, bars, index_histories):
    """Exercise storage only for explicitly labeled synthetic Gate B fixtures.

    Production refresh wiring and provider completeness belong to later gates.
    """
    if snapshot.get('synthetic_fixture') is not True:
        raise ValueError('Gate B persistence requires an explicit synthetic fixture')
    required={r['ticker'] for r in snapshot['relationships']}
    with store.refresh(snapshot['session'],snapshot['methodology'],snapshot['configuration_hash']) as run:
        run.bars(bars)
        for row in snapshot['themes']:run.theme(row['theme_id'],row)
        for row in snapshot['relationships']:run.stock(row['ticker'],row['theme_id'],row)
        for theme,points in index_histories.items():
            for point in points:run.index(theme,point.session,point)
        run.publish(snapshot,required_symbols=required)
