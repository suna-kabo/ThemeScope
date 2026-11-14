"""Manufactured UI contexts, never live chronological evidence."""
from copy import deepcopy
from decimal import Decimal as D
import json
from vnext_prelaunch_fixture import PrelaunchFixture
from src.themescope.research.context import enrich
from src.themescope.research.v2 import attach
from src.themescope.storage import canonical


def make(folder):
    fixture=PrelaunchFixture(folder,full=True);fixture.target='2026-11-10'
    base=fixture.service.refresh()
    assert base is not None,fixture.service.status()
    base=fixture.service.snapshot()
    sessions=fixture.sessions[:fixture.sessions.index(base['session'])+1]
    bars={(b.ticker,b.session):b for b in fixture.bars}
    mapping={r['ticker']:{'status':'verified','symbol':'FIXTURE:'+r['ticker']} for r in base['relationships']}
    previous_day=deepcopy(base);previous_day['session']=sessions[-2]
    previous_five=deepcopy(base);previous_five['session']=sessions[-6]
    for index,theme in enumerate(previous_five['themes']):
        theme['history']['session']=previous_five['session']
        if theme['score'] is not None:
            theme['score']=str(max(D(0),min(D(100),D(theme['score'])+(D(15) if index%2 else D(-15)))))
    base=json.loads(canonical(attach(base,bars,sessions,mapping,previous=previous_five,previous_day=previous_day)))
    short=deepcopy(base)
    short['market_direction']='Short bias';short['market']['decision'].update(direction='Short bias',reason='Manufactured UI comparison state')
    for ticker in ('SPY','QQQ'):
        row=short['market']['context'][ticker];row.update(ema21=str(D(row['close'])+8),ema50=str(D(row['close'])+10),price_state='Bearish')
    for t in short['themes']:
        if t['status']=='active':
            t['index'].update(trend='Bearish',ema21=str(D(t['index']['level'])+1),ema50=str(D(t['index']['level'])+2))
            t['history']['trend']='Bearish'
    previous=deepcopy(previous_day)
    for ticker in ('SPY','QQQ','IWM'):
        row=previous['market']['context'][ticker];row['ema21']=str(D(row['close'])-1)
    short=enrich(short,bars,sessions,previous,base['research']['companies'])
    short=json.loads(canonical(attach(short,bars,sessions,mapping,previous=previous_five,previous_day=previous)))
    return fixture,base,short
