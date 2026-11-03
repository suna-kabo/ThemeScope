"""Canonical browsing lists and bounded TradingView exports, with no market rules."""
from datetime import date, timedelta
from decimal import Decimal, localcontext
import math
from .tradingview import individual_filenames, theme_symbols
from .research_policy import number, market_side, priority_sort_key, CURRENT_WEIGHT, MEDIUM_WEIGHT


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


def primary_research(snapshot, limit):
    """Evaluate each membership against its own anchor; never refill membership."""
    side=market_side(snapshot.get('market_classification',{}).get('direction'))
    themes=sorted((t for t in snapshot['themes'] if side and t.get('research_priority',{}).get('label')=='Primary '+side),key=priority_sort_key)
    session=snapshot['session_date'];files={};manifest=[];relationships=[];evaluations=[];combined=[]
    filenames=individual_filenames(themes)
    for theme in themes:
        anchor=theme_symbols(theme)[0]  # Strict identifier resolution, even ETF-only.
        qualifying=[]
        for stock in theme.get('selected',[]):
            endpoints={name:row.get('returns',{}).get(period,{}).get('value') for name,row,period in
                [('stock_1m',stock,'21'),('stock_3m',stock,'63'),('etf_1m',theme,'21'),('etf_3m',theme,'63')]}
            invalid=[key for key,value in endpoints.items() if not number(value)]
            row={'theme_id':theme['id'],'anchor':theme['anchor'],'ticker':stock['ticker'],'symbol':stock['tradingview_symbol'],**endpoints}
            if invalid:row.update(included=False,reason='missing_or_invalid:'+','.join(invalid))
            else:
                # Decimal arithmetic avoids giving a zero cross-horizon result
                # an artificial sign through binary cancellation. No rounding.
                with localcontext() as context:
                    context.prec=40
                    values={key:Decimal(str(value)) for key,value in endpoints.items()}
                    er1=100*(values['stock_1m']-values['etf_1m']);er3=100*(values['stock_3m']-values['etf_3m'])
                    weighted=Decimal(str(CURRENT_WEIGHT))*er1+Decimal(str(MEDIUM_WEIGHT))*er3
                included=weighted>0 if side=='long' else weighted<0
                row.update(er1m_pp=float(er1),er3m_pp=float(er3),weighted_excess_pp=float(weighted),included=included,reason='included' if included else 'zero_weighted_excess' if weighted==0 else 'opposite_sign')
                if included:qualifying.append(row)
            evaluations.append(row)
        qualifying.sort(key=lambda r:((-r['weighted_excess_pp'] if side=='long' else r['weighted_excess_pp']),r['ticker'],r['symbol']))
        tokens=[anchor]+[r['symbol'] for r in qualifying]
        if len(tokens)>limit:raise ValueError('Primary theme exceeds TradingView instrument limit: '+theme['id'])
        name='primary_watchlists/'+session+'/'+filenames[theme['id']][:-4]+'_Primary_'+side+'.txt'
        files[name]=','.join(tokens)+'\n'
        manifest.append({'file':name,'role':'individual_primary_research','theme_id':theme['id'],'anchor':theme['anchor'],'instrument_count':len(tokens),'stock_count':len(qualifying),'section_count':0})
        relationships.append({'theme_id':theme['id'],'theme_name':theme['name'],'anchor':theme['anchor'],'symbol':anchor,'ticker':theme['anchor'],'role':'anchor','weighted_excess_pp':None,'er1m_pp':None,'er3m_pp':None})
        relationships.extend({key:r.get(key) for key in ('theme_id','anchor','symbol','ticker','weighted_excess_pp','er1m_pp','er3m_pp')}|{'theme_name':theme['name'],'role':'stock'} for r in qualifying)
        combined.extend(tokens)
    combined=list(dict.fromkeys(combined))
    combined_name='tradingview_daily_primary_'+session+'.txt' if themes else None
    if combined_name:
        if len(combined)>limit:raise ValueError('Combined Daily Primary exceeds TradingView instrument limit; no list was truncated')
        files[combined_name]=','.join(combined)+'\n'
        manifest.append({'file':combined_name,'role':'daily_primary_research','instrument_count':len(combined),'section_count':0})
    snapshot['daily_primary_research']={'session_date':session,'side':side,'theme_ids':[t['id'] for t in themes],'combined_file':combined_name,
        'archive_file':'daily_primary_watchlists_'+session+'.zip' if themes else None,'relationships_file':'daily_primary_relationships_'+session+'.csv' if themes else None,
        'relationships':relationships,'evaluations':evaluations,'platform_import_tested':False}
    snapshot.setdefault('manual_csv_audit',{})['daily_primary_research']={'qualifying_themes':len(themes),'qualifying_stock_memberships':sum(r['included'] for r in evaluations),'excluded_stock_memberships':sum(not r['included'] for r in evaluations),'combined_unique_instruments':len(combined),'platform_import_tested':False}
    return files,manifest


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
    # Collection ETFs include all anchors and the three index contexts.
    etfs=list(dict.fromkeys(r['tradingview_symbol'] for r in snapshot['themes']+snapshot.get('context',[])))
    add('tradingview_sector_theme_etfs',flat_chunks(etfs,limit),'configured_etf_daily_data')
    primary_files,primary_manifest=primary_research(snapshot,limit)
    files.update(primary_files);manifest.extend(primary_manifest)
    snapshot['export_manifest']=manifest
    snapshot['export_archives']=['individual_theme_watchlists.zip']+([snapshot['daily_primary_research']['archive_file']] if snapshot['daily_primary_research']['archive_file'] else [])
    snapshot['export_configuration']=config
    snapshot['manual_csv_audit']['daily_lists']={'configured_unique_stocks':len(all_stocks),'earnings_scope_unique_stocks':len(primary),'expected_earnings_in_window':len(snapshot['expected_earnings']['upcoming']),'earnings_unknown':len(snapshot['expected_earnings']['unknown']),'instrument_limit':limit,'files':manifest,'platform_import_tested':False}
    return files
