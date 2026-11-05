"""Plan incremental fetches outside the writer lock, pin exact inputs on publish."""
from dataclasses import dataclass
import json
from .base import ProviderError
from ..themes.calculations import Bar,bar_map,calendar,usable

@dataclass(frozen=True)
class Prepared:
    identity: str
    bars: tuple
    fetched: int
    requests: int


def prepare(store,provider,symbols,sessions,*,repair_sessions=2,full_repair=False):
    sessions=calendar(sessions);symbols=tuple(sorted(set(symbols)))
    if not symbols or repair_sessions<1:raise ValueError('Symbols and positive repair window required')
    if sessions[-1]>provider.get_latest_completed_session():raise ProviderError('session_not_safely_completed')
    cached={}
    for symbol in symbols:
        rows=store.connection.execute('SELECT o.payload FROM bar_cache c JOIN observations o ON o.id=c.observation_id WHERE c.identity=? AND c.ticker=? AND c.session BETWEEN ? AND ?',
                                      (provider.identity,symbol,sessions[0],sessions[-1]))
        cached.update(bar_map(Bar(**json.loads(r[0])) for r in rows))
    result=dict(cached);requests=0;fetched=0
    # Group identical missing/repair ranges so large warm universes use batched calls.
    groups={}
    for symbol in symbols:
        missing=[s for s in sessions if (symbol,s) not in cached]
        needed=[i for i,s in enumerate(sessions) if full_repair or s in missing or i>=len(sessions)-repair_sessions]
        begin=previous=needed[0]
        for i in needed[1:]+[len(sessions)+1]:
            if i!=previous+1:
                groups.setdefault((sessions[begin],sessions[previous]),[]).append(symbol)
                begin=i
            previous=i
    for (start,end),names in groups.items():
        batch=provider.get_daily_bars(names,start,end);requests+=1;fetched+=len(batch.bars)
        if batch.identity!=provider.identity:raise ProviderError('provider_identity_mismatch')
        fresh=bar_map(batch.bars)
        if any(s not in names or not start<=d<=end for s,d in fresh):raise ProviderError('unexpected_batch_range')
        result={key:value for key,value in result.items() if not(key[0] in names and start<=key[1]<=end)}
        result.update(fresh)
    # A historical adjustment anchor detects cumulative split/spin-off revisions.
    anchors=[s for s in symbols if (s,sessions[0]) in cached and not full_repair]
    if anchors:
        batch=provider.get_daily_bars(anchors,sessions[0],sessions[0]);requests+=1;fetched+=len(batch.bars)
        anchor=bar_map(batch.bars)
        if any((s,sessions[0]) not in anchor for s in anchors):raise ProviderError('adjustment_anchor_missing')
        revised=[s for s in anchors if anchor[s,sessions[0]]!=cached[s,sessions[0]]]
        if revised:
            batch=provider.get_daily_bars(revised,sessions[0],sessions[-1]);requests+=1;fetched+=len(batch.bars)
            replacement=bar_map(batch.bars)
            if any((s,d) not in replacement for s in revised for d in sessions):
                raise ProviderError('adjustment_reseed_incomplete')
            for s in revised:
                for d in sessions:result[s,d]=replacement[s,d]
    rows=tuple(result[s,d] for s in symbols for d in sessions if (s,d) in result)
    if any(not usable(result.get((s,sessions[-1]))) or result[s,sessions[-1]].volume<=0 for s in symbols):
        raise ProviderError('required_target_session_missing_or_zero_volume')
    return Prepared(provider.identity,rows,fetched,requests)


def publish_prepared(store,prepared,session,methodology,config_hash,payload,required_symbols):
    """Atomic cache updates + pinned observation references + snapshot publication."""
    with store.refresh(session,methodology,config_hash) as run:
        run.bars(prepared.bars,identity=prepared.identity)
        run.publish(payload,required_symbols=required_symbols)
