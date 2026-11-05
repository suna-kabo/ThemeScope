"""Optional earnings calendar. Failure never blocks a market refresh."""
from typing import Protocol
from urllib.request import urlopen
from urllib.parse import urlencode
from datetime import date
import csv,io

class EarningsProvider(Protocol):
    def events(self,symbols): ...

class AlphaVantageEarnings:
    def __init__(self,key,*,fetch=None):self.key=key;self.fetch=fetch or self._fetch
    def _fetch(self):
        with urlopen('https://www.alphavantage.co/query?'+urlencode({'function':'EARNINGS_CALENDAR','horizon':'3month','apikey':self.key}),timeout=10) as response:
            return response.read().decode('utf-8-sig')
    def events(self,symbols):
        if not self.key:return {}
        reader=csv.DictReader(io.StringIO(self.fetch()))
        if not reader.fieldnames or not {'symbol','reportDate'}<=set(reader.fieldnames):raise ValueError('Earnings unavailable')
        result={}
        for row in reader:
            if row['symbol'] not in symbols:continue
            day=row['reportDate']
            if date.fromisoformat(day).isoformat()!=day:raise ValueError('Invalid reported event')
            result.setdefault(row['symbol'],[]).append(day)
        return {symbol:sorted(set(days)) for symbol,days in result.items()}


def optional_earnings(provider,symbols):
    symbols=tuple(sorted(set(symbols)))
    unavailable={s:{'status':'Unavailable','dates':[]} for s in symbols}
    if provider is None:return unavailable
    try:
        events=provider.events(symbols)
        for symbol,days in events.items():
            if symbol not in unavailable:continue
            if not isinstance(days,list) or any(date.fromisoformat(d).isoformat()!=d for d in days):raise ValueError()
            if days:unavailable[symbol]={'status':'Available','dates':sorted(set(days))}
        return unavailable
    except Exception:
        return {s:{'status':'Unavailable','dates':[]} for s in symbols}
