"""Explicit, audited-by-code publication boundary for the static website.

Only display data and intentional exports cross this boundary. Raw inputs, local
history, run audits, paths and membership review records never enter the site.
"""
import base64
import copy
import csv
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import quote
import zipfile

SCHEMA='themescope-site-4'
LEGACY_SCHEMAS={'themescope-site-1','themescope-site-2','themescope-site-3'}
ROLES={'individual_research','configured_stock_daily_data','configured_etf_daily_data','daily_primary_research'}
LOCAL_ONLY_ROLES={'optional_broad_scan','individual_primary_research'}
SCALARS='ticker exchange instrument_type currency price_close daily_change ema21 ema50 above_ema21 above_ema50 price_state price_vs_ema21_pct price_vs_ema50_pct adv30_usd atr14_pct relative_volume_1d turnover_1d_usd'.split()
THEME_FIELDS='id name anchor level global_rank rank_current rank_change_daily rank_comparison_session theme_score current_strength_score medium_strength_score priority_change breadth_status_21 breadth_status_50 configured_watchlist_count watchlist_member_count has_watchlist stock_drilldown_status watchlist_status theme_breadth21_pct theme_breadth21_above theme_breadth21_valid theme_breadth50_pct theme_breadth50_above theme_breadth50_valid'.split()
STOCK_FIELDS='company theme_id theme_name anchor selection_slot market_cap_usd anchor_performance_1m anchor_performance_3m excess21_pp excess63_pp earnings_date weighted_excess_pp weighted_vs_etf metric_status session_date average_volume_10d_shares'.split()
METRIC_FIELDS='value status above_count valid_count eligible_count configured_count ema_period session_date'.split()
HEADERS="/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: no-referrer\n  X-Frame-Options: DENY\n  Cache-Control: no-cache\n"
PLACEHOLDER_HTML='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'"><title>ThemeScope — deployment prepared</title></head><body><h1>ThemeScope</h1><p>Deployment is prepared. No market snapshot has been published.</p></body></html>'''


def pick(value,keys):
    return {key:copy.deepcopy(value[key]) for key in keys if key in value}


def metric_periods(value):
    return {key:pick(row,METRIC_FIELDS) for key,row in value.items() if key in {'5','21','50','63'} and isinstance(row,dict)}


def safe_name(name):
    path=PurePosixPath(name)
    if '\\' in name or ':' in name or path.is_absolute() or '..' in path.parts or str(path)!=name:
        raise ValueError('Unsafe site asset path: '+name)
    return path


def public_payload(snapshot,root):
    from .tradingview import load_mapping,resolve
    from .daily_stock_policy import load_policy,verified_eligibility,SCHEMA_MODES
    policy=load_policy(root)
    if snapshot.get('daily_stock_policy')!=policy or snapshot.get('stock_csv_schema') not in SCHEMA_MODES.values():
        raise ValueError('Saved run predates or differs from the current Daily Stock policy. Existing historical HTML remains readable. Refresh with the new 10-day shares column, or explicitly use --stock-csv-schema legacy-v1 for unverified historical eligibility, before preparing a new site.')
    mapping=load_mapping(root)
    def instrument(row,ticker):
        result=pick(row,SCALARS)
        symbol=resolve(ticker,mapping)
        if row.get('tradingview_symbol')!=symbol:raise ValueError('Identifier/config changed; refresh before preparing the site: '+ticker)
        result['tradingview_symbol']=symbol
        result['chart_url']='https://www.tradingview.com/chart/?symbol='+quote(symbol,safe='')
        result['returns']=metric_periods(row.get('returns',{}))
        return result
    payload=pick(snapshot,['session_date','generated_at','dashboard_generated_at','dashboard_generated_at_hkt_display'])
    payload.update(daily_stock_policy=copy.deepcopy(policy),stock_csv_schema=snapshot['stock_csv_schema'])
    payload.update(schema_version=SCHEMA,run_kind='manual_csv',volatility_context=[])
    payload['score_methodology']=pick(snapshot['score_methodology'],['current','medium','method'])
    payload['score_methodology']['theme_score_weights']=pick(snapshot['score_methodology']['theme_score_weights'],['current_strength','medium_strength'])
    payload['ui_configuration']={'score_bands':[pick(b,['min','max','class']) for b in snapshot['ui_configuration']['score_bands']]}
    payload['context']=[]
    for row in snapshot['context']:
        clean=instrument(row,row['ticker']);clean.update(pick(row,['name','breadth_label','breadth_state']))
        clean['index_breadth']=metric_periods(row['index_breadth']);payload['context'].append(clean)
    payload['themes']=[]
    for row in snapshot['themes']:
        clean=instrument(row,row['anchor']);clean.update(pick(row,THEME_FIELDS))
        clean['research_priority']=pick(row['research_priority'],['label','group','side','category'])
        clean['theme_watchlist_breadth']=metric_periods(row.get('theme_watchlist_breadth',{}))
        clean['selected']=[]
        for stock in row.get('selected',[]):
            member=instrument(stock,stock['ticker']);member.update(pick(stock,STOCK_FIELDS))
            expected=verified_eligibility(stock,policy,snapshot['stock_csv_schema'])
            if stock.get('daily_stock_eligibility')!=expected:raise ValueError('Daily Stock eligibility differs from measured policy inputs: '+stock['ticker'])
            member['daily_stock_eligibility']=copy.deepcopy(expected)
            member['excess_returns']=metric_periods(stock.get('excess_returns',{}))
            clean['selected'].append(member)
        payload['themes'].append(clean)
    decision=snapshot['decision']
    payload['decision']=pick(decision,['session_date','generated_at_hkt','market_classification','action_sentence','matrix_rule_id','reason','spy_price_state','qqq_price_state','iwm_price_state','spy_breadth_state','qqq_breadth_state','breadth_consensus','breadth_qualifier','russell_2000_breadth_state','decision_path'])
    payload['decision']['primary_groups']={key:list(decision.get('primary_groups',{}).get(key,[])) for key in ('new','continuing','unavailable')}
    payload['decision']['market_matrix']=[pick(r,['spy','qqq','breadth','direction']) for r in decision.get('market_matrix',[])]
    payload['decision']['priority_policy']=pick(decision.get('priority_policy',{}),['priority_version','ema_version','input_semantics','score_boundary','weights','long_rule','short_rule','transition_rule','stock_rule','note'])
    payload['market_classification']=pick(snapshot['market_classification'],['direction','breadth_consensus','breadth_qualifier','reason','action_summary'])
    payload['display_methodology']=pick(snapshot.get('display_methodology',{}),['maintenance_thresholds','watchlist_capacity','breadth_minimum_coverage','theme_breadth_minimum_valid','liquidity_definition','membership_rules','maintenance_missing_data'])
    research=snapshot['daily_primary_research']
    payload['daily_primary_research']=pick(research,['session_date','side','theme_ids','combined_file','platform_import_tested','eligibility_policy_version','stock_csv_schema'])
    payload['local_history']={'comparison_session':snapshot.get('local_history',{}).get('comparison_session'),'status':'Compared with the immediately preceding US session.' if any(t.get('rank_change_daily') is not None for t in payload['themes']) else 'No comparable previous-session record.'}
    earnings=snapshot['expected_earnings']
    payload['expected_earnings']=pick(earnings,['as_of','through','later_count'])
    for group in ('upcoming','unknown'):
        payload['expected_earnings'][group]=[]
        for row in earnings[group]:
            clean=pick(row,['ticker','symbol','days_away','timing_label'])
            raw=row.get('expected_date');clean['expected_date']=raw if isinstance(raw,str) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',raw) else None
            if group=='unknown':clean['reason']='Past-only expected date' if row.get('reason')=='Past-only expected date' else 'Expected date unavailable'
            clean['contexts']=[pick(c,['theme_id','theme_name','anchor']) for c in row['contexts']]
            payload['expected_earnings'][group].append(clean)
    payload['export_manifest']=[]
    for row in snapshot['export_manifest']:
        if row['role'] in LOCAL_ONLY_ROLES:continue
        if row['role'] not in ROLES:raise ValueError('Unapproved website export role: '+row['role'])
        safe_name(row['file'])
        if not (re.fullmatch(r'tradingview_[A-Za-z0-9_-]+\.txt',row['file']) or re.fullmatch(r'(?:individual_watchlists|primary_watchlists/\d{4}-\d{2}-\d{2})/[A-Za-z0-9_.-]+\.txt',row['file'])):
            raise ValueError('Unapproved website export name: '+row['file'])
        payload['export_manifest'].append(pick(row,['file','role','theme_id','anchor','group','instrument_count','stock_count','section_count','eligibility_policy_version','stock_csv_schema']))
    return payload


def public_artifact_purposes(payload):
    """Every deployed file has a visitor-facing link or an explicit site purpose."""
    purposes={'index.html':'Website with inline script, CSS, font and display data',
              '_headers':'Hosting security/cache headers','Inter-LICENSE.txt':'Bundled font license',
              'themes.csv':'Full ranking CSV link','theme_stocks.csv':'Configured stock CSV link',
              'snapshot_summary.json':'Snapshot summary links and local preview metadata',
              'individual_theme_watchlists.zip':'Download Individual Watchlists'}
    for row in payload['export_manifest']:
        if row['role'] not in ROLES:raise ValueError('Unapproved website export role: '+row['role'])
        safe_name(row['file'])
        if row['file'] in purposes:raise ValueError('Duplicate website artifact: '+row['file'])
        purposes[row['file']]={'individual_research':'Full selected Watchlist download and ZIP member',
                              'configured_stock_daily_data':'Download All Stocks',
                              'configured_etf_daily_data':'Download All Themes',
                              'daily_primary_research':"Today’s grouped Primary Research Watchlist"}[row['role']]
    return purposes


def render_html(payload,root):
    template=(root/'static/dashboard_template.html').read_text(encoding='utf-8')
    template=template.replace('href="registry_audit.csv"','href="snapshot_summary.json"').replace('Registry audit CSV','Snapshot summary')
    template=template.replace('href="stock_diagnostics.csv"','href="theme_stocks.csv"').replace('Stock eligibility audit','Configured stock CSV')
    template,count=re.subn(r'<footer>.*?</footer>','<footer><a href="snapshot_summary.json" download>Snapshot summary</a> · Local history and private audits are not part of this site.</footer>',template,flags=re.S)
    if count!=1:raise ValueError('Website footer changed; review the public export boundary before building.')
    css=(root/'static/dashboard.css').read_text(encoding='utf-8')
    css=css.replace('{{FONT_DATA}}',base64.b64encode((root/'static/InterVariable.woff2').read_bytes()).decode('ascii'))
    data=json.dumps(payload,ensure_ascii=False,separators=(',',':'),allow_nan=False).replace('</','<\\/').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    return template.replace('{{STYLE}}',css).replace('{{SCRIPT}}',(root/'static/dashboard.js').read_text(encoding='utf-8')).replace('{{SNAPSHOT_JSON}}',data)


def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def write_public_csvs(folder,payload):
    """Derive downloads from the same sanitized display data, never private CSVs."""
    from .research_policy import ema_relationship
    themes=[];stocks=[]
    def percent(value):return value*100 if isinstance(value,(int,float)) else None
    def returns(row):return {'performance_'+label+'_pct':percent(row.get('returns',{}).get(period,{}).get('value')) for period,label in [('5','1w'),('21','1m'),('63','3m')]}
    for theme in sorted(payload['themes'],key=lambda t:(t.get('global_rank') is None,t.get('global_rank') or float('inf'),t['id'])):
        themes.append({'rank':theme.get('global_rank'),'type':theme.get('level'),'theme_id':theme['id'],'name':theme['name'],'anchor':theme['anchor'],'change_1d_pct':percent(theme.get('daily_change')),'rank_change_daily':theme.get('rank_change_daily'),'rank_comparison_session':theme.get('rank_comparison_session'),'priority_change':theme.get('priority_change'),'vs_ema21':ema_relationship(theme.get('price_close'),theme.get('ema21')),'vs_ema50':ema_relationship(theme.get('price_close'),theme.get('ema50')),'research_priority':theme['research_priority'].get('label'),'theme_score':theme.get('theme_score'),'current':theme.get('current_strength_score'),'medium':theme.get('medium_strength_score'),**returns(theme),'price':theme.get('price_close'),'ema21':theme.get('ema21'),'ema50':theme.get('ema50'),'theme_breadth21_pct':theme.get('theme_breadth21_pct'),'theme_breadth50_pct':theme.get('theme_breadth50_pct'),'configured_stock_count':len(theme['selected']),'session_date':payload['session_date']})
        for stock in theme['selected']:
            stocks.append({'theme_id':theme['id'],'theme':theme['name'],'anchor':theme['anchor'],**pick(stock,['ticker','company','exchange','market_cap_usd','metric_status','ema21','ema50','atr14_pct','adv30_usd','turnover_1d_usd','average_volume_10d_shares','relative_volume_1d']),'daily_stock_eligibility':stock['daily_stock_eligibility']['status'],'daily_stock_policy_version':stock['daily_stock_eligibility']['policy_version'],'stock_csv_schema':payload['stock_csv_schema'],'excess_1m_pp':stock.get('excess21_pp'),'excess_3m_pp':stock.get('excess63_pp'),'price':stock.get('price_close'),'change_1d_pct':percent(stock.get('daily_change')),**returns(stock),'upcoming_earnings_date':stock.get('earnings_date'),'session_date':payload['session_date']})
    for name,rows in [('themes.csv',themes),('theme_stocks.csv',stocks)]:
        fields=list(dict.fromkeys(key for row in rows for key in row)) or ['theme_id','ticker','metric_status']
        with (folder/name).open('w',encoding='utf-8',newline='') as handle:
            writer=csv.DictWriter(handle,fieldnames=fields);writer.writeheader();writer.writerows(rows)


def seal_site(folder,kind,session):
    files={str(p.relative_to(folder)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.rglob('*')) if p.is_file() and p.name!='site_manifest.json'}
    write_json(folder/'site_manifest.json',{'schema':SCHEMA,'kind':kind,'session_date':session,'files':files})


def validate_site(folder,*,allow_legacy=False):
    if folder.is_symlink():raise ValueError('Site folder must not be a symlink')
    manifest=json.loads((folder/'site_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') not in {SCHEMA,*LEGACY_SCHEMAS} or manifest.get('kind') not in {'snapshot','placeholder'}:raise ValueError('Unknown site manifest')
    if manifest['schema']!=SCHEMA and not allow_legacy:raise ValueError('Legacy site must be re-prepared with the current allowlist before deployment.')
    files=manifest['files']
    if not isinstance(files,dict):raise ValueError('Invalid site file manifest')
    actual=set()
    for path in folder.rglob('*'):
        if path.is_symlink():raise ValueError('Site assets must not be symlinks')
        if path.is_file():actual.add(path.relative_to(folder).as_posix())
    if actual!=set(files)|{'site_manifest.json'}:raise ValueError('Site contains missing or unlisted files; no directory-wide publication is allowed')
    base={'index.html','_headers','themes.csv','theme_stocks.csv','snapshot_summary.json','individual_theme_watchlists.zip','Inter-LICENSE.txt'}
    for name,digest in files.items():
        safe_name(name)
        if name not in base and not re.fullmatch(r'(?:(?:tradingview_[A-Za-z0-9_-]+|individual_watchlists/[A-Za-z0-9_.-]+|primary_watchlists/\d{4}-\d{2}-\d{2}/[A-Za-z0-9_.-]+)\.txt|daily_primary_watchlists_\d{4}-\d{2}-\d{2}\.zip|daily_primary_relationships_\d{4}-\d{2}-\d{2}\.csv)',name):raise ValueError('Forbidden site artifact: '+name)
        path=folder/name
        if path.stat().st_size>25*1024*1024:raise ValueError('Site file exceeds the Pages 25 MiB file limit: '+name)
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Site artifact changed after preparation: '+name)
    if not {'index.html','_headers'}<=set(files):raise ValueError('Site entry point or headers missing')
    text=(folder/'index.html').read_text(encoding='utf-8')
    if manifest['kind']=='placeholder' and (set(files)!={'index.html','_headers'} or text!=PLACEHOLDER_HTML):raise ValueError('Placeholder must contain only the known empty page and hosting headers')
    if "connect-src 'none'" not in text:raise ValueError('Offline CSP missing')
    # Fail closed even if a modified template reintroduces a private download.
    class Links(HTMLParser):
        def __init__(self):super().__init__();self.links=[]
        def handle_starttag(self,tag,attrs):
            self.links.extend(value for key,value in attrs if key in {'href','src'} and value)
    links=Links();links.feed(text)
    for href in links.links:
        if href.startswith('#') or href.startswith('https://www.tradingview.com/'):continue
        if href not in files:raise ValueError('Website link points outside the allowed assets: '+href)
    if manifest['kind']=='snapshot':
        match=re.search(r'<script id="snapshot-data"[^>]*>(.*?)</script>',text,re.S)
        if not match:raise ValueError('Snapshot payload missing')
        payload=json.loads(match.group(1))
        if payload.get('schema_version')!=manifest['schema'] or payload.get('session_date')!=manifest['session_date']:raise ValueError('Public payload/manifest session mismatch')
        forbidden={'manual_csv_audit','raw_inputs','inputs','source_matrix','fingerprint','maintenance','reviewed_date','reason_source_url','source_url','membership_rationale','ranking_configuration_fingerprint','candidate_metrics'}
        if manifest['schema'] in {SCHEMA,'themescope-site-2','themescope-site-3'}:forbidden.update({'theme_state','theme_states','state_threshold','state_boundary','priority_matrix','priority_definitions','guard_failures'})
        def check(value):
            if isinstance(value,dict):
                if forbidden&set(value):raise ValueError('Private metadata found in public payload')
                for item in value.values():check(item)
            elif isinstance(value,list):
                for item in value:check(item)
        check(payload)
        for row in payload['export_manifest']:
            if row['file'] not in files:raise ValueError('A dynamic website download is missing')
        if manifest['schema'] in {SCHEMA,'themescope-site-2','themescope-site-3'}:
            for field in ('combined_file','archive_file','relationships_file'):
                name=payload['daily_primary_research'].get(field)
                if name and name not in files:raise ValueError('A Daily Primary website download is missing')
        if manifest['schema']==SCHEMA:
            research=payload['daily_primary_research']
            if set(research)-{'session_date','side','theme_ids','combined_file','platform_import_tested','eligibility_policy_version','stock_csv_schema'}:
                raise ValueError('Internal Primary relationship/archive metadata found in website payload')
            from .daily_stock_policy import load_policy,verified_eligibility,SCHEMA_MODES
            policy=load_policy(Path(__file__).resolve().parents[2]);schema=payload.get('stock_csv_schema')
            if payload.get('daily_stock_policy')!=policy or schema not in SCHEMA_MODES.values():raise ValueError('Website Daily Stock schema/policy is missing or incompatible')
            for theme in payload['themes']:
                for stock in theme['selected']:
                    if stock.get('daily_stock_eligibility')!=verified_eligibility(stock,policy,schema):raise ValueError('Website daily eligibility disagrees with measured inputs')
            if research.get('eligibility_policy_version')!=policy['version'] or research.get('stock_csv_schema')!=schema:raise ValueError('Primary eligibility policy version mismatch')
            from .daily_lists import primary_research
            proof=copy.deepcopy(payload)
            export_limit=json.loads((Path(__file__).resolve().parents[2]/'config/watchlist_exports.json').read_text(encoding='utf-8'))['instrument_limit']
            expected_primary,_=primary_research(proof,export_limit)
            name=research.get('combined_file')
            if name!=proof['daily_primary_research']['combined_file']:raise ValueError('Primary file presence differs from current qualification')
            if name and (folder/name).read_text(encoding='utf-8').replace('\r\n','\n')!=expected_primary[name]:raise ValueError('Website Primary instruments differ from daily eligibility and weighted qualification')
            purposes=public_artifact_purposes(payload)
            if set(files)!=set(purposes):raise ValueError('Website includes unlinked/obsolete artifacts or is missing an approved asset')
            primary=[r['file'] for r in payload['export_manifest'] if r['role']=='daily_primary_research']
            if primary!=([research['combined_file']] if research.get('combined_file') else []):raise ValueError('Primary link and website manifest disagree')
            individuals=[r['file'] for r in payload['export_manifest'] if r['role']=='individual_research']
            expected={Path(name).name:(folder/name).read_bytes() for name in individuals}
            with zipfile.ZipFile(folder/'individual_theme_watchlists.zip') as archive:
                if len(archive.namelist())!=len(expected) or set(archive.namelist())!=set(expected):raise ValueError('Individual ZIP contains unexpected/duplicate members')
                if sum(row.file_size for row in archive.infolist())>25*1024*1024:raise ValueError('Individual ZIP uncompressed content exceeds site limit')
                if any(archive.read(name)!=content for name,content in expected.items()):raise ValueError('Individual ZIP and selected downloads differ')
    return manifest


def replace_site(stage,destination):
    """Replace only a previously sealed generated site, with rollback on failure."""
    if destination.exists():validate_site(destination,allow_legacy=True)
    from .local_publication import publish_tree
    previous={p.relative_to(destination).as_posix() for p in destination.rglob('*') if p.is_file()} if destination.exists() else set()
    current={p.relative_to(stage).as_posix() for p in stage.rglob('*') if p.is_file()}
    publish_tree(stage,destination,previous-current,validate_site)
    # Publication retires managed files; remove only now-empty generated folders.
    for folder in sorted((p for p in destination.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        try:folder.rmdir()
        except OSError:pass


def _prepare_site(root,source,destination,session):
    root,source,destination=root.resolve(),source.resolve(),destination.resolve()
    if destination==root or destination==source or destination in source.parents or source in destination.parents:
        raise ValueError('Site must be separate from repository root and private run output')
    snapshot=json.loads((source/'latest_snapshot.json').read_text(encoding='utf-8'))
    if snapshot.get('session_date')!=session:raise ValueError('Requested site session does not match the last successful run. Refresh first; no old session was relabeled.')
    if snapshot.get('run_kind')!='manual_csv' or not snapshot.get('manual_csv_audit',{}).get('publication_pass'):raise ValueError('Only a successful manual CSV run can become a site')
    payload=public_payload(snapshot,root)
    destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.themescope-site-',dir=destination.parent) as temporary:
        stage=Path(temporary)/'site';stage.mkdir()
        (stage/'index.html').write_text(render_html(payload,root),encoding='utf-8')
        (stage/'_headers').write_text(HEADERS,encoding='utf-8')
        (stage/'Inter-LICENSE.txt').write_bytes((root/'static/Inter-LICENSE.txt').read_bytes())
        stock_symbols={s['tradingview_symbol'] for t in payload['themes'] for s in t['selected']}
        all_symbols=stock_symbols|{t['tradingview_symbol'] for t in payload['themes']+payload['context']}
        from .daily_lists import primary_research
        expected_research=copy.deepcopy(snapshot)
        expected_files,expected_manifest=primary_research(expected_research,snapshot['export_configuration']['instrument_limit'])
        if snapshot['daily_primary_research']!=expected_research['daily_primary_research']:raise ValueError('Primary research relationships differ from current returns/policy')
        actual_manifest=[r for r in payload['export_manifest'] if r['role']=='daily_primary_research']
        if actual_manifest!=[r for r in expected_manifest if r['role']=='daily_primary_research']:raise ValueError('Primary research manifest differs from current qualification')
        daily_symbols=[];etf_symbols=[]
        for item in payload['export_manifest']:
            path=source/item['file']
            if path.is_symlink():raise ValueError('Export source must not be a symlink')
            content=path.read_bytes();tokens=content.decode('utf-8').strip().split(',')
            instruments=[token for token in tokens if not token.startswith('###')]
            headings=[token for token in tokens if token.startswith('###')]
            if headings and item['role']!='daily_primary_research':raise ValueError('Unexpected section in ordinary export')
            if len(headings)!=item['section_count'] or len(instruments)!=len(set(instruments)) or len(instruments)!=item['instrument_count'] or not set(instruments)<=all_symbols:raise ValueError('Website TXT contains unexpected instruments: '+item['file'])
            if item['role'] in {'individual_primary_research','daily_primary_research'} and content.decode('utf-8').replace('\r\n','\n')!=expected_files[item['file']]:raise ValueError('Primary export differs from weighted per-anchor qualification')
            if item['role']=='configured_etf_daily_data':etf_symbols+=tokens
            if item['role']=='individual_research':
                theme=next(t for t in payload['themes'] if t['id']==item['theme_id'])
                if tokens!=[theme['tradingview_symbol']]+[s['tradingview_symbol'] for s in theme['selected']]:raise ValueError('Individual website export differs from configured membership')
            if item['role']=='configured_stock_daily_data':daily_symbols+=tokens
            target=stage/item['file'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
        if any(i['role']=='configured_stock_daily_data' for i in payload['export_manifest']) and daily_symbols!=sorted(stock_symbols):raise ValueError('Daily Data Stocks differs from configured stock universe')
        if any(i['role']=='configured_etf_daily_data' for i in payload['export_manifest']) and etf_symbols!=list(dict.fromkeys(r['tradingview_symbol'] for r in payload['themes']+payload['context'])):raise ValueError('ETF collection list differs from complete configured universe')
        individuals=[r for r in payload['export_manifest'] if r['role']=='individual_research']
        with zipfile.ZipFile(stage/'individual_theme_watchlists.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
            for item in individuals:archive.write(stage/item['file'],arcname=Path(item['file']).name)
        write_public_csvs(stage,payload)
        stocks={r['tradingview_symbol']:r for t in payload['themes'] for r in t['selected']}
        write_json(stage/'snapshot_summary.json',{'session_date':session,'generated_at_hkt':payload['dashboard_generated_at_hkt_display'],'source':'User-supplied TradingView CSV exports','configured_themes':len(payload['themes']),'configured_unique_stocks':len(stocks),'missing_daily_stocks':sum(s['metric_status']!='available' for s in stocks.values()),'rank_comparison_session':payload['local_history']['comparison_session'],'stock_csv_schema':payload['stock_csv_schema'],'daily_stock_policy_version':payload['daily_stock_policy']['version'],'daily_stock_eligibility_counts':{status:sum(s['daily_stock_eligibility']['status']==status for s in stocks.values()) for status in ('eligible','ineligible','unavailable','legacy_unverified')}})
        seal_site(stage,'snapshot',session);validate_site(stage);replace_site(stage,destination)
    return validate_site(destination)


def prepare_site(root,source,destination,session):
    from .local_publication import output_lock,recover,validate_published_files
    root,source,destination=Path(root).resolve(),Path(source).resolve(),Path(destination).resolve()
    if destination==root or destination==source or destination in source.parents or source in destination.parents:raise ValueError('Site must be separate from repository root and private run output')
    with output_lock(source,timeout=5),output_lock(destination,timeout=5):
        recover(source);recover(destination);validate_published_files(source)
        return _prepare_site(root,source,destination,session)


def placeholder_site(destination):
    destination.mkdir(parents=True,exist_ok=False)
    (destination/'index.html').write_text(PLACEHOLDER_HTML,encoding='utf-8')
    (destination/'_headers').write_text(HEADERS,encoding='utf-8')
    seal_site(destination,'placeholder',None)
    return validate_site(destination)
