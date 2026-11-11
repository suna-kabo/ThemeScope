"""Manufactured UI contexts, never live chronological evidence."""
from copy import deepcopy
from decimal import Decimal as D
import json
from vnext_prelaunch_fixture import PrelaunchFixture
from src.themescope.research.context import enrich
from src.themescope.research.countertrend_exports import attach
from src.themescope.research.primary import priority,qualifies,Eligibility
from src.themescope.research.exports import exports,Qualification
from src.themescope.themes.history import ThemeHistory,transitions
from src.themescope.storage import canonical


def make(folder):
    fixture=PrelaunchFixture(folder,full=True);fixture.target='2026-11-10'
    base=fixture.service.refresh()
    assert base is not None,fixture.service.status()
    base=fixture.service.snapshot();short=deepcopy(base)
    short['market_direction']='Short bias';short['market']['decision'].update(direction='Short bias',reason='Manufactured UI comparison state')
    for ticker in ('SPY','QQQ'):
        row=short['market']['context'][ticker];row.update(ema21=str(D(row['close'])+8),ema50=str(D(row['close'])+10),price_state='Bearish')
    for t in short['themes']:
        if t['status']=='active':
            t['index'].update(trend='Bearish',ema21=str(D(t['index']['level'])+1),ema50=str(D(t['index']['level'])+2))
            t['history']['trend']='Bearish'
        t['priority']=priority('Short bias',t['score'],t['index']['trend'],t['transition']);t['history']['priority']=t['priority']
    themes={t['theme_id']:t for t in short['themes']};selected=[]
    mapping={r['ticker']:{'status':'verified','symbol':'FIXTURE:'+r['ticker']} for r in short['relationships']}
    for r in short['relationships']:
        r['qualifies']=qualifies(themes[r['theme_id']]['priority'],r['relative']['w'],Eligibility(**r['eligibility']))
        if r['qualifies']:selected.append(Qualification(r['ticker'],r['theme_id'],r['role'],D(r['relative']['w'])))
    short['exports']=exports(selected,'short',mapping)
    for r in short['relationships']:
        a=short['exports']['assignments'].get(r['ticker'],{});r['assigned_section']=a.get('assigned_section');r['also_qualifies_in']=a.get('also_qualifies_in',[])
    previous=deepcopy(short);previous['session']='2026-11-09'
    for t in previous['themes']:t['history']['session']=previous['session']
    previous['themes'][0]['score']='100'
    for ticker in ('SPY','QQQ','IWM'):
        row=previous['market']['context'][ticker];row['ema21']=str(D(row['close'])-1)
    sessions=fixture.sessions[:fixture.sessions.index(short['session'])+1]
    old={t['theme_id']:t for t in previous['themes']}
    for t in short['themes']:t['transition']=transitions(ThemeHistory(**old[t['theme_id']]['history']),ThemeHistory(**t['history']),sessions)
    short=enrich(short,{(b.ticker,b.session):b for b in fixture.bars},sessions,previous,base['research']['companies'])
    short=json.loads(canonical(attach(short,mapping)))
    return fixture,base,short
