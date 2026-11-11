"""Formula-independent daily market data contract and completed-session schedule."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

class ProviderError(ValueError):
    """Safe diagnostic codes only: never embed requests, headers or response bodies."""

@dataclass(frozen=True)
class Batch:
    identity: str
    bars: tuple
    pages: int = 0

class MarketDataProvider(Protocol):
    identity: str
    def get_daily_bars(self, symbols, start, end) -> Batch: ...
    def get_latest_completed_session(self) -> str: ...
    def health_check(self) -> dict: ...

class Schedule:
    def __init__(self, records, now=None, delay_minutes=20):
        self.records={r['session']:datetime.fromisoformat(r['close']) for r in records}
        self.now=now or (lambda:datetime.now(timezone.utc))
        self.delay=timedelta(minutes=delay_minutes)

    def require(self, session):
        close=self.records.get(session)
        if close is None or close+self.delay>self.now():
            raise ProviderError('session_not_safely_completed')

    def latest(self):
        valid=[s for s,c in self.records.items() if c+self.delay<=self.now()]
        if not valid:raise ProviderError('no_completed_session')
        return max(valid)

class FixtureProvider:
    identity='fixture:v1:split,spin-off:raw-volume'
    def __init__(self, bars, schedule):
        self.bars=tuple(bars);self.schedule=schedule;self.calls=[]
    def get_daily_bars(self,symbols,start,end):
        self.schedule.require(end)
        self.calls.append((tuple(symbols),start,end))
        return Batch(self.identity,tuple(b for b in self.bars if b.ticker in symbols and start<=b.session<=end))
    def get_latest_completed_session(self):return self.schedule.latest()
    def health_check(self):return {'provider':self.identity,'status':'fixture','session':self.schedule.latest()}
