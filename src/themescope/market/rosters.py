"""Explicit manual roster updates. No automatic constituent discovery."""
from dataclasses import asdict
from datetime import date
from pathlib import Path
import json
import os
import tempfile
from ..domain import MarketRoster


def load(root):
    path=Path(root)/'config/market_universes/rosters.json'
    rows=json.loads(path.read_text(encoding='utf-8'))['rosters'] if path.exists() else []
    rosters=tuple(MarketRoster(**dict(r,tickers=tuple(r['tickers']))) for r in rows)
    for benchmark in ('SPY','QQQ'):
        ordered=sorted((r for r in rosters if r.benchmark==benchmark),key=lambda r:r.effective_from)
        for old,new in zip(ordered,ordered[1:]):
            if old.effective_to is None or old.effective_to>new.effective_from:raise ValueError('Overlapping roster intervals')
    return rosters


def effective(rosters,benchmark,session):
    if benchmark not in ('SPY','QQQ'):raise ValueError('Only SPY/QQQ have rosters')
    return next((r for r in rosters if r.benchmark==benchmark and r.effective_from<=session
                 and (r.effective_to is None or session<r.effective_to)),None)


def warnings(roster,session):
    if roster is None:return ['Roster unavailable: import an approved manual roster.']
    return ['Roster older than 90 calendar days; review its source.'] if (date.fromisoformat(session)-date.fromisoformat(roster.effective_from)).days>90 else []


def update(root,roster):
    from dataclasses import replace
    from ..local_refresh_lock import RefreshLock
    folder=Path(root)/'config/market_universes';folder.mkdir(parents=True,exist_ok=True)
    with RefreshLock(Path(root)/'runtime/refresh.lock'):
        rows=list(load(root))
        for i,old in enumerate(rows):
            if old.benchmark==roster.benchmark and old.effective_to is None:
                if roster.effective_from<=old.effective_from:raise ValueError('Roster updates must move forward')
                rows[i]=replace(old,effective_to=roster.effective_from)
        rows.append(roster)
        # Validate the complete ledger before replacing the source file.
        for old in rows[:-1]:
            if old.benchmark==roster.benchmark and (old.effective_to is None or old.effective_to>roster.effective_from):
                raise ValueError('Overlapping roster update')
        fd,name=tempfile.mkstemp(dir=folder,suffix='.tmp')
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as handle:
                json.dump({'schema':1,'rosters':[asdict(r) for r in rows]},handle,indent=2)
            os.replace(name,folder/'rosters.json')
        finally:
            if Path(name).exists():Path(name).unlink()
