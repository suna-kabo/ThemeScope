"""Plan incremental fetches outside the writer lock, pin exact inputs on publish."""
from dataclasses import dataclass
import json
from .base import ProviderError
from ..themes.calculations import Bar,bar_map,calendar,usable
from ..corporate_actions import validate_actions,resolve_values,diagnostic

@dataclass(frozen=True)
class Prepared:
    identity: str
    bars: tuple
    fetched: int
    requests: int
    target_symbols: tuple = ()
    terminal_actions: tuple = ()
    terminal_values: tuple = ()


def prepare(store,provider,symbols,sessions,*,repair_sessions=2,full_repair=False,
            terminal_actions=(),target_symbols=None):
    sessions=calendar(sessions);symbols=tuple(sorted(set(symbols)))
    required=tuple(sorted(set(symbols if target_symbols is None else target_symbols)))
    if not symbols or not required or not set(required)<=set(symbols) or repair_sessions<1:
        raise ValueError('Symbols, target requirements and positive repair window required')
    if sessions[-1]>provider.get_latest_completed_session():raise ProviderError('session_not_safely_completed')
    actions=tuple(a for a in validate_actions(terminal_actions) if a.ticker in symbols)
    by_symbol={a.ticker:a for a in actions}
    wanted={s:set(d for d in sessions if s not in by_symbol or d<=by_symbol[s].last_trading_session) for s in symbols}
    for action in actions:
        if action.valuation_session<=sessions[-1]:
            wanted[action.ticker].add(action.last_trading_session)
            if action.valuation_session==sessions[-1]:
                # Confirm the current missing bar rather than hiding a genuine
                # trade that contradicts the approved termination notice.
                wanted[action.ticker].add(action.valuation_session)
            if action.stock_ticker:
                wanted.setdefault(action.stock_ticker,set()).add(action.valuation_session)
    wanted={s:tuple(sorted(days)) for s,days in wanted.items() if days}
    cached={}
    for symbol,days in wanted.items():
        rows=store.connection.execute('SELECT o.payload FROM bar_cache c JOIN observations o ON o.id=c.observation_id WHERE c.identity=? AND c.ticker=? AND c.session BETWEEN ? AND ?',
                                      (provider.identity,symbol,days[0],days[-1]))
        day_set=set(days)
        cached.update({key:row for key,row in bar_map(Bar(**json.loads(r[0])) for r in rows).items() if key[1] in day_set})
    result=dict(cached);requests=0;fetched=0
    repair_window=set(sessions[-repair_sessions:])
    def fetch(names,start,end):
        nonlocal requests,fetched
        batch=provider.get_daily_bars(names,start,end);requests+=1;fetched+=len(batch.bars)
        if batch.identity!=provider.identity:raise ProviderError('provider_identity_mismatch')
        fresh=bar_map(batch.bars)
        if any(s not in names or not start<=d<=end for s,d in fresh):raise ProviderError('unexpected_batch_range')
        return fresh
    # Identical missing/repair ranges are batched, including valuation dependencies.
    groups={}
    for symbol,days in wanted.items():
        needed=[i for i,d in enumerate(days) if full_repair or (symbol,d) not in cached or d in repair_window]
        if not needed:continue
        begin=previous=needed[0]
        for i in needed[1:]+[len(days)+1]:
            if i!=previous+1:
                groups.setdefault((days[begin],days[previous]),[]).append(symbol)
                begin=i
            previous=i
    for (start,end),names in groups.items():
        fresh=fetch(names,start,end)
        result={key:value for key,value in result.items() if not(key[0] in names and start<=key[1]<=end)}
        result.update(fresh)
    # Preserve split/spin-off anchor detection and bounded whole-history repair.
    anchors={}
    for symbol,days in wanted.items():
        if (symbol,days[0]) in cached and not full_repair and days[-1]>=min(repair_window):
            anchors.setdefault(days[0],[]).append(symbol)
    revisions={}
    for day,names in anchors.items():
        anchor=fetch(names,day,day)
        if any((s,day) not in anchor for s in names):raise ProviderError('adjustment_anchor_missing')
        for symbol in names:
            if anchor[symbol,day]!=cached[symbol,day]:
                revisions.setdefault((wanted[symbol][0],wanted[symbol][-1]),[]).append(symbol)
    for (start,end),names in revisions.items():
        replacement=fetch(names,start,end)
        if any((s,d) not in replacement for s in names for d in wanted[s]):raise ProviderError('adjustment_reseed_incomplete')
        for s in names:
            for d in wanted[s]:result[s,d]=replacement[s,d]
    values=resolve_values(actions,result,sessions[-1])
    terminal={v.ticker for v in values if v.valuation_session==sessions[-1]}
    missing=[s for s in required if (not usable(result.get((s,sessions[-1]))) or result[s,sessions[-1]].volume<=0) and s not in terminal]
    if missing:
        raise ProviderError(';'.join(diagnostic('required_target_session_missing_or_zero_volume',s) for s in missing[:8]))
    rows=tuple(result[key] for key in sorted(result))
    return Prepared(provider.identity,rows,fetched,requests,required,actions,values)


def publish_prepared(store,prepared,session,methodology,config_hash,payload,required_symbols):
    """Atomic cache updates + pinned observation references + snapshot publication."""
    with store.refresh(session,methodology,config_hash) as run:
        run.bars(prepared.bars,identity=prepared.identity)
        run.publish(payload,required_symbols=required_symbols,terminal_actions=prepared.terminal_actions)
