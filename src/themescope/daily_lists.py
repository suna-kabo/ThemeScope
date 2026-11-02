"""Canonical browsing lists and bounded TradingView exports, with no market rules."""
from datetime import date, timedelta
import math
from .tradingview import heading, theme_symbols


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
            unknown.append({'ticker':row['ticker'],'symbol':row['tradingview_symbol'],'reason':'Past-only expected date' if expected else 'Expected date unavailable','expected_date':raw})
        elif expected <= start+timedelta(days=7):
            days=(expected-start).days
            upcoming.append({'ticker':row['ticker'],'symbol':row['tradingview_symbol'],'expected_date':raw,'days_away':days,'timing_label':'Today; timing unverified' if days==0 else f'{days} days away','contexts':row['primary_contexts']})
        else:
            later.append(row['tradingview_symbol'])
    return {'as_of':session,'through':(start+timedelta(days=7)).isoformat(),'upcoming':sorted(upcoming,key=lambda r:(r['expected_date'],r['symbol'])),'unknown':unknown,'later_count':len(later)}


def pack_sections(sections, limit):
    chunks=[];current=[];count=0
    for theme in sections:
        symbols=theme_symbols(theme)
        if len(symbols)>limit:
            raise ValueError(f'TradingView section {theme["id"]} requires {len(symbols)} instruments; configured limit is {limit}. Section cannot be split.')
        if current and count+len(symbols)>limit:
            chunks.append((current,count));current=[];count=0
        current.extend([heading(theme),*symbols]);count+=len(symbols)
    if current:chunks.append((current,count))
    return chunks


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
                primary[symbol]={**stock,'primary_contexts':[]}
            if not any(c['theme_id']==theme['id'] for c in primary[symbol]['primary_contexts']):
                primary[symbol]['primary_contexts'].append({'theme_id':theme['id'],'theme_name':theme['name'],'anchor':theme['anchor'],'membership_rationale':stock.get('membership_rationale'),'membership_tag':stock.get('membership_tag'),'anchor_performance_1m':stock['anchor_performance_1m'],'anchor_performance_3m':stock['anchor_performance_3m'],'excess21_pp':stock['excess21_pp'],'excess63_pp':stock['excess63_pp'],'rs_state':stock['rs_state']})
    candidates=[primary[k] for k in sorted(primary)]
    files={};manifest=[]
    def add(stem,chunks,role,group=None):
        for index,(tokens,count) in enumerate(chunks,1):
            name=stem+(f'_{index:02d}' if len(chunks)>1 else '')+'.txt'
            if name in files:raise ValueError('Duplicate export filename '+name)
            files[name]=','.join(tokens)+'\n'
            manifest.append({'file':name,'role':role,'group':group,'instrument_count':count,'section_count':sum(t.startswith('###') for t in tokens)})
    for group in config['groups']:
        add('tradingview_group_'+group['id'],pack_sections([themes[i] for i in group['theme_ids']],limit),'thematic_navigation',group['name'])
    add('tradingview_configured_stocks',flat_chunks(sorted(all_stocks),limit),'configured_stock_daily_data')
    add('tradingview_primary_stocks_'+snapshot['session_date'],flat_chunks(sorted(primary),limit),'daily_primary_scan')
    # Retain the old all-theme filename as an optional alternative, also bounded.
    add('tradingview_all_theme_stocks',pack_sections(list(themes.values()),limit),'legacy_all_themes')
    snapshot['daily_primary']={'candidates':candidates,'unique_count':len(candidates),'earnings':earnings_window(candidates,snapshot['session_date'])}
    snapshot['export_manifest']=manifest
    snapshot['export_archives']=['tradingview_primary_stocks_'+snapshot['session_date']+'.zip'] if sum(f['role']=='daily_primary_scan' for f in manifest)>1 else []
    snapshot['export_configuration']=config
    snapshot['manual_csv_audit']['daily_lists']={'configured_unique_stocks':len(all_stocks),'primary_unique_stocks':len(primary),'primary_market_cap_available':sum(r.get('market_cap_usd') is not None for r in candidates),'primary_missing_metrics':sum(r.get('metric_status')!='available' for r in candidates),'expected_earnings_in_window':len(snapshot['daily_primary']['earnings']['upcoming']),'earnings_unknown':len(snapshot['daily_primary']['earnings']['unknown']),'instrument_limit':limit,'files':manifest,'platform_import_tested':False}
    return files
