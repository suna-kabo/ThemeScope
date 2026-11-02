"""Canonical browsing lists and bounded TradingView exports, with no market rules."""
from datetime import date, timedelta
import math
from .tradingview import individual_filenames, theme_symbols


def rs_state(a, b):
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in (a,b)):
        return 'Missing'
    return 'Outperforming' if a > 0 and b > 0 else 'Underperforming' if a < 0 and b < 0 else 'Mixed'


def earnings_window(candidates, session):
    start=date.fromisoformat(session)
    upcoming=[];unknown=[];later=[]
    for row in candidates:
        raw=row.get('earnings_date')
        try:
            expected=date.fromisoformat(raw) if isinstance(raw,str) else None
        except ValueError:
            expected=None
        if expected is None or expected < start:
            unknown.append({'ticker':row['ticker'],'symbol':row['tradingview_symbol'],'reason':'Past-only expected date' if expected else 'Expected date unavailable','expected_date':raw,'contexts':row['primary_contexts']})
        elif expected <= start+timedelta(days=7):
            days=(expected-start).days
            upcoming.append({'ticker':row['ticker'],'symbol':row['tradingview_symbol'],'expected_date':raw,'days_away':days,'timing_label':'Today; timing unverified' if days==0 else f'{days} days away','contexts':row['primary_contexts']})
        else:
            later.append(row['tradingview_symbol'])
    return {'as_of':session,'through':(start+timedelta(days=7)).isoformat(),'upcoming':sorted(upcoming,key=lambda r:(r['expected_date'],r['symbol'])),'unknown':unknown,'later_count':len(later)}


def flat_chunks(symbols, limit):
    return [(symbols[i:i+limit],len(symbols[i:i+limit])) for i in range(0,len(symbols),limit)]


def build(snapshot, config):
    if config.get('schema_version')!=1:raise ValueError('Unsupported watchlist export schema')
    limit=config.get('instrument_limit')
    if isinstance(limit,bool) or not isinstance(limit,int) or limit<1:raise ValueError('Instrument limit must be a positive integer')
    themes={t['id']:t for t in snapshot['themes']}
    assigned=[i for g in config['groups'] for i in g['theme_ids']]
    group_ids=[g['id'] for g in config['groups']]
    if len(set(assigned))!=len(assigned) or set(assigned)!=set(themes):raise ValueError('Every active theme must be assigned exactly once to an export group')
    if len(set(group_ids))!=len(group_ids) or any(not i or not all(c.isalnum() or c=='-' for c in i) for i in group_ids):raise ValueError('Export group IDs must be unique safe slugs')
    all_stocks={};primary={}
    for theme in snapshot['themes']:
        for stock in theme.get('selected',[]):
            symbol=stock.get('tradingview_symbol')
            if not symbol:raise ValueError('Unresolved stock identifier: '+stock['ticker'])
            cap=stock.get('market_cap_usd')
            if not isinstance(cap,(int,float)) or isinstance(cap,bool) or not math.isfinite(cap) or cap<=0:stock['market_cap_usd']=None
            all_stocks.setdefault(symbol,stock)
            stock['anchor_performance_1m']=theme['returns']['21']['value']
            stock['anchor_performance_3m']=theme['returns']['63']['value']
            excess=stock.get('excess_returns',{})
            for period in ('21','63'):
                value=excess.get(period,{}).get('value')
                stock['excess'+period+'_pp']=100*value if value is not None else None
            stock['rs_state']=rs_state(stock['excess21_pp'],stock['excess63_pp'])
            if theme.get('research_priority',{}).get('category')!='primary':continue
            if symbol not in primary:
                primary[symbol]={'ticker':stock['ticker'],'tradingview_symbol':symbol,'earnings_date':stock.get('earnings_date'),'primary_contexts':[]}
            if not any(c['theme_id']==theme['id'] for c in primary[symbol]['primary_contexts']):
                primary[symbol]['primary_contexts'].append({'theme_id':theme['id'],'theme_name':theme['name'],'anchor':theme['anchor']})
    earnings_members=[primary[k] for k in sorted(primary)]
    files={};manifest=[]
    def add(stem,chunks,role,group=None):
        for index,(tokens,count) in enumerate(chunks,1):
            name=stem+(f'_{index:02d}' if len(chunks)>1 else '')+'.txt'
            if name in files:raise ValueError('Duplicate export filename '+name)
            files[name]=','.join(tokens)+'\n'
            manifest.append({'file':name,'role':role,'group':group,'instrument_count':count,'section_count':sum(t.startswith('###') for t in tokens)})
    filenames=individual_filenames(snapshot['themes'])
    for theme in snapshot['themes']:
        symbols=theme_symbols(theme)
        if len(symbols)>limit:raise ValueError(f"Individual watchlist {theme['id']} exceeds instrument limit {limit}")
        name='individual_watchlists/'+filenames[theme['id']]
        files[name]=','.join(symbols)+'\n'
        manifest.append({'file':name,'role':'individual_research','theme_id':theme['id'],'anchor':theme['anchor'],'instrument_count':len(symbols),'stock_count':len(theme.get('selected',[])),'section_count':0})
    for group in config['groups']:
        unique=list(dict.fromkeys(symbol for i in group['theme_ids'] for symbol in theme_symbols(themes[i])))
        add('tradingview_group_'+group['id'],flat_chunks(unique,limit),'optional_broad_scan',group['name'])
    add('tradingview_configured_stocks',flat_chunks(sorted(all_stocks),limit),'configured_stock_daily_data')
    # Optional flat broad scan; per-theme membership belongs to separate files.
    unique=list(dict.fromkeys(symbol for theme in themes.values() for symbol in theme_symbols(theme)))
    add('tradingview_all_theme_stocks',flat_chunks(unique,limit),'optional_broad_scan','All configured exposures')
    snapshot['expected_earnings']=earnings_window(earnings_members,snapshot['session_date'])
    snapshot.pop('daily_primary',None)
    snapshot['export_manifest']=manifest
    snapshot['export_archives']=['individual_theme_watchlists.zip']
    snapshot['export_configuration']=config
    snapshot['manual_csv_audit']['daily_lists']={'configured_unique_stocks':len(all_stocks),'earnings_scope_unique_stocks':len(primary),'expected_earnings_in_window':len(snapshot['expected_earnings']['upcoming']),'earnings_unknown':len(snapshot['expected_earnings']['unknown']),'instrument_limit':limit,'files':manifest,'platform_import_tested':False}
    return files
