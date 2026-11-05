"""Historical Market Data API only. Fixed host/path/feed, bounded safe retries."""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from urllib.request import Request,urlopen
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
import json
import re
import time
from .base import Batch,ProviderError
from ..themes.calculations import Bar,bar_map

URL='https://data.alpaca.markets/v2/stocks/bars'


def transport(params,headers):
    request=Request(URL+'?'+urlencode(params),headers=headers,method='GET')
    try:
        with urlopen(request,timeout=30) as response:
            return response.status,json.loads(response.read()),dict(response.headers)
    except HTTPError as error:
        # Never parse/print auth response bodies or request details.
        return error.code,{},dict(error.headers)

class AlpacaMarketDataProvider:
    identity='alpaca:v2:sip:1Day:split,spin-off:raw-volume'
    def __init__(self,key,secret,schedule,*,send=transport,sleep=time.sleep,limit=10000,retries=3):
        if not key or not secret:raise ProviderError('credentials_missing')
        if not 1<=limit<=10000 or not 0<=retries<=5:raise ValueError('Invalid request bounds')
        self._headers={'APCA-API-KEY-ID':key,'APCA-API-SECRET-KEY':secret}
        self.schedule=schedule;self.send=send;self.sleep=sleep;self.limit=limit;self.retries=retries

    def _page(self,params):
        for attempt in range(self.retries+1):
            try:status,payload,headers=self.send(params,self._headers)
            except (URLError,TimeoutError,OSError):status,payload,headers=503,{},{}
            except (ValueError,TypeError):raise ProviderError('malformed_payload') from None
            if status==200:return payload
            if status not in (429,500,502,503,504):
                raise ProviderError({401:'authentication_401',403:'sip_access_403',422:'request_or_subscription_422'}.get(status,'http_failure'))
            if attempt==self.retries:raise ProviderError('rate_limit_exhausted' if status==429 else 'transient_exhausted')
            delay=2**attempt
            try:delay=max(delay,min(30,float(headers.get('Retry-After',0))))
            except (ValueError,TypeError):pass
            self.sleep(delay)

    def _fetch(self,symbols,start,end,adjustment):
        params={'symbols':','.join(symbols),'start':start+'T00:00:00Z','end':min(datetime.fromisoformat(end+'T23:59:59+00:00'),self.schedule.now()-timedelta(minutes=20)).astimezone(timezone.utc).isoformat(),
                'feed':'sip','timeframe':'1Day','adjustment':adjustment,'limit':self.limit,'sort':'asc'}
        result={};tokens=set();pages=0
        while True:
            body=self._page(dict(params));pages+=1
            if not isinstance(body,dict) or not isinstance(body.get('bars'),dict):raise ProviderError('malformed_payload')
            for symbol,rows in body['bars'].items():
                if symbol not in symbols or not isinstance(rows,list):raise ProviderError('unexpected_symbol_or_rows')
                for row in rows:
                    try:
                        timestamp=datetime.fromisoformat(row['t'].replace('Z','+00:00'))
                        if timestamp.tzinfo is None:raise ValueError()
                        # US daily bar label belongs to New York regular-session date.
                        from zoneinfo import ZoneInfo
                        session=timestamp.astimezone(ZoneInfo('America/New_York')).date().isoformat()
                        if not start<=session<=end or session not in self.schedule.records:raise ValueError()
                        close=Decimal(str(row['c']));volume=Decimal(str(row['v']))
                        if not close.is_finite() or close<=0 or not volume.is_finite() or volume<0:raise ValueError()
                        key=(symbol,session)
                        if key in result:raise ValueError()
                        result[key]=(close,volume)
                    except (KeyError,ValueError,TypeError,ArithmeticError,AttributeError):
                        raise ProviderError('malformed_bar') from None
            token=body.get('next_page_token')
            if token is None or token=='':break
            if not isinstance(token,str) or token in tokens or pages>=10000:raise ProviderError('invalid_pagination')
            tokens.add(token);params['page_token']=token
        return result,pages

    def get_daily_bars(self,symbols,start,end):
        symbols=tuple(sorted(set(symbols)))
        if not symbols or any(not re.fullmatch(r'[A-Z][A-Z0-9.\-]{0,15}',s) for s in symbols):raise ProviderError('invalid_symbols')
        if date.fromisoformat(start).isoformat()!=start or date.fromisoformat(end).isoformat()!=end or start>end:raise ProviderError('invalid_range')
        self.schedule.require(end)
        # Adjusted volume must never replace actual traded volume for liquidity.
        adjusted,p1=self._fetch(symbols,start,end,'split,spin-off')
        raw,p2=self._fetch(symbols,start,end,'raw')
        if adjusted.keys()!=raw.keys():raise ProviderError('raw_adjusted_mismatch')
        bars=tuple(Bar(s,d,adjusted[s,d][0],raw[s,d][0],raw[s,d][1]) for s,d in sorted(raw))
        return Batch(self.identity,bars,p1+p2)

    def get_latest_completed_session(self):return self.schedule.latest()
    def health_check(self):
        session=self.schedule.latest()
        batch=self.get_daily_bars(('AAPL',),session,session)
        if not batch.bars or batch.bars[0].volume<=0:raise ProviderError('target_volume_missing')
        return {'provider':self.identity,'status':'ok','session':session}
