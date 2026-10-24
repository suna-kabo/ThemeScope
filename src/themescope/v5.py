"""v5 constituent universes, independent participation, and explicit score conventions."""
from datetime import date, datetime, timezone
import hashlib
import math
import os
import re
import time
import statistics
from .sources import _request, _TableParser, request_json, fetch_yahoo_chart, _YAHOO_BLOCKED_HOSTS
from .metrics import observation_map, return_metric, trend_metric
from .ranking import average_ranks

VERSION = 'themescope-v6.2'


def metric(value=None, reason=None, **details):
    return dict(value=value, status='valid' if value is not None and reason is None else 'unavailable', reason=reason, input_version=VERSION, **details)


def fetch_universes():
    now = datetime.now(timezone.utc).isoformat(timespec='seconds')
    url = 'https://www.sec.gov/files/company_tickers_exchange.json'
    raw = request_json(url)
    listings = {r['ticker']: r for r in (dict(zip(raw['fields'], row)) for row in raw['data'])}
    mapping = {'url': url, 'retrieved_at': now, 'listings': listings}
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    body = _request(url)
    parser = _TableParser(); parser.feed(body.decode('utf-8'))
    rows = []
    started = False
    for row in parser.rows:
        if row[:2] == ['Symbol', 'Security']:
            started = True
            continue
        if started:
            if len(row) != 8 or not row[6].isdigit():
                break
            rows.append({'ticker': row[0], 'company': row[1], 'sector': row[2], 'industry': row[3], 'company_id': str(int(row[6])), 'security_type': 'EQUITY'})
    if len(rows) < 450:
        raise ValueError('S&P 500 constituent parser returned an incomplete list')
    spy = {
        'as_of': now[:10], 'observation_date': now[:10], 'effective_date': None,
        'date_semantics': 'observation',
        'universe_label': 'Current observed S&P 500 constituent list',
        'asof_basis': 'Current constituent page observed at retrieval; not an official effective-date assertion',
        'url': url, 'retrieved_at': now, 'source_sha256': hashlib.sha256(body).hexdigest(), 'rows': rows,
    }
    url = 'https://api.nasdaq.com/api/quote/list-type/nasdaq100'
    data = request_json(url)['data']
    rows = [{'ticker': row['symbol'], 'company': row['companyName'], 'company_id': str(listings.get(row['symbol'], {}).get('cik') or row['symbol']), 'security_type': 'EQUITY'} for row in data['data']['rows']]
    if len(rows) != int(data['totalrecords']) or len(rows) < 90:
        raise ValueError('Nasdaq-100 constituent response incomplete')
    qqq_date = _nasdaq_effective_date(data.get('date'))
    qqq = {'as_of': qqq_date, 'observation_date': None, 'effective_date': qqq_date,
           'date_semantics': 'effective', 'universe_label': 'Nasdaq-100 constituent list',
           'asof_basis': 'Nasdaq response date', 'url': url, 'retrieved_at': now, 'rows': rows}
    return {'SPY': spy, 'QQQ': qqq}, mapping


def _nasdaq_effective_date(value):
    """Parse Nasdaq dates with or without its intraday response-time suffix."""
    match = re.search(r'([A-Za-z]{3,9}\s+\d{1,2},\s+\d{4})', str(value or ''))
    if not match:
        raise ValueError(f'Nasdaq-100 response date is missing or unrecognized: {value!r}')
    date_text = match.group(1)
    for form in ('%b %d, %Y', '%B %d, %Y'):
        try:
            return datetime.strptime(date_text, form).date().isoformat()
        except ValueError:
            pass
    raise ValueError(f'Nasdaq-100 response date is missing or unrecognized: {value!r}')


def map_universe(source, mapping, index=False):
    """Conservative mappings; unresolved equity stays in coverage denominator."""
    companies = {}
    excluded = list(source.get("excluded_rows", []))
    unresolved = []
    listings = mapping.get('listings', {})
    for row in source.get('rows', []):
        ticker = str(row.get('ticker') or '')
        security = str(row.get('security_type') or '').upper()
        if (security and security not in ('EQUITY', 'COMMON_SHARE', 'SPONSORED_ADS')) or re.search(r'\b(CASH|FUTURES?|TREASURY|ETF|MONEY MARKET FUND)\b', str(row.get('company', '')).upper()):
            excluded.append({**row, 'reason': 'Not common equity'})
            continue
        if ticker == '-' or re.fullmatch(r'\d+[A-Z]+', ticker):
            excluded.append({**row, 'reason': 'Unresolved non-equity/security placeholder; no listing mapping'})
            continue
        listing = listings.get(ticker) or listings.get(ticker.replace('.', '-'))
        country = row.get('country')
        sid = str(row.get('security_id') or '')
        domestic = not country or country == 'United States' or sid.startswith('US')
        mapped = listing is not None and (index or domestic)
        symbol = str(listing['ticker']).replace('.', '-') if mapped else None
        company_id = str(row.get('company_id') or (listing['cik'] if mapped else sid or ('unmapped:'+str(country)+':'+ticker)))
        if company_id not in companies:
            companies[company_id] = {'company_id': company_id, 'company': row.get('company'), 'symbols': [], 'source_tickers': [], 'sector': row.get('sector'), 'industry': row.get('industry')}
        group = companies[company_id]
        # Preserve the dated source classification for sector/industry browsing.
        # CIK deduplication still counts an issuer once.
        if not group.get('sector') and row.get('sector'):
            group['sector'] = row['sector']
        if not group.get('industry') and row.get('industry'):
            group['industry'] = row['industry']
        group['source_tickers'].append(ticker)
        if symbol and symbol not in group['symbols']:
            group['symbols'].append(symbol)
        if not mapped:
            unresolved.append({'ticker': ticker, 'reason': 'No verified SEC listing/country mapping; retained in equity coverage denominator'})
    for row in companies.values():
        row['symbols'].sort()
    return {'companies': list(companies.values()), 'excluded_rows': excluded, 'unresolved_mappings': unresolved, 'source_row_count': len(source.get('rows', []))}


def normalize_price_symbol(value):
    """Normalize an issuer ETF ticker for Yahoo's US chart endpoint."""
    raw = str(value or '').strip().upper()
    symbol = re.sub(r'\s+', '-', raw).replace('.', '-')
    if not symbol or symbol in {'-', '--'} or not re.fullmatch(r'[A-Z][A-Z0-9-]{0,14}', symbol):
        return None
    return symbol


def _iwm_company_key(company_name):
    name = re.sub(r'\b(?:CLASS|CL)\s+[A-Z0-9]+\b', ' ', str(company_name or '').upper())
    name = re.sub(r'\b(?:INCORPORATED|INC|CORPORATION|CORP|COMPANY|CO|LIMITED|LTD|PLC|LP|LLC)\b', ' ', name)
    return re.sub(r'[^A-Z0-9]+', ' ', name).strip()


def map_iwm_universe(source, mapping):
    """Map current iShares IWM holdings using issuer symbols, with SEC as verification/fallback.

    The issuer's exchange ticker is sufficient to request a price series; a SEC ticker-map
    match supplies a CIK for deduplication but is not a price-download prerequisite.
    """
    listings = mapping.get('listings', {})
    listings_by_symbol = {}
    for listed_symbol, listing in listings.items():
        normalized = normalize_price_symbol(listed_symbol)
        if normalized:
            listings_by_symbol[normalized] = listing

    companies = {}
    excluded = list(source.get('excluded_rows', []))
    unverified = []
    eligible_rows = 0
    classified_equity_rows = 0
    description_exclusions = 0
    normalization_failures = []
    for row in source.get('rows', []):
        security = str(row.get('security_type') or '').strip().casefold()
        if security != 'equity':
            excluded.append({**row, 'reason': f"Holdings security type '{row.get('security_type') or 'missing'}' is not equity"})
            continue
        classified_equity_rows += 1
        ticker_raw = str(row.get('ticker') or '').strip()
        company = str(row.get('company') or '').strip()
        name_upper = company.upper()
        if re.search(r'(?:\bCONTINGENT VALUE RIGHTS?\b|\bCVR\s*$|\s-\sCVR\s*$|\bESCROW\b|\bCONTRA\b|\bVESTING\b|\bPRVT\b|\bPRIVATE\b|\bWARRANTS?\b|\bRIGHTS?\b)', name_upper):
            excluded.append({**row, 'reason': 'Issuer description identifies a contingent, escrow, private, or non-common security'})
            description_exclusions += 1
            continue
        ticker = normalize_price_symbol(ticker_raw)
        if not ticker or re.fullmatch(r'\d+[A-Z]+', ticker):
            excluded.append({**row, 'reason': 'No reliable exchange ticker is available for price lookup'})
            normalization_failures.append({'ticker': ticker_raw, 'company': company, 'reason': 'No reliable exchange ticker is available for price lookup'})
            continue

        eligible_rows += 1
        listing = listings_by_symbol.get(ticker)
        cik = str((listing or {}).get('cik') or '').strip()
        listed_ticker = normalize_price_symbol((listing or {}).get('ticker'))
        symbol = listed_ticker or ticker
        issuer_key = 'cik:' + cik if cik else 'name:' + _iwm_company_key(company)
        if issuer_key == 'name:':
            issuer_key = 'ticker:' + symbol
        if not cik:
            unverified.append({'ticker': ticker_raw, 'normalized_symbol': symbol, 'company': company, 'reason': 'No SEC listing match; retained using the official iShares ticker'})
        item = companies.setdefault(issuer_key, {
            'company_id': issuer_key,
            'company': company,
            'symbols': [],
            'source_tickers': [],
            'sector': row.get('sector'),
            'industry': None,
            'ticker_mapping': 'sec_cik' if cik else 'direct_issuer_ticker',
        })
        item['source_tickers'].append(ticker_raw)
        if symbol not in item['symbols']:
            item['symbols'].append(symbol)
        if listing and not item.get('cik'):
            item['cik'] = cik
            item['ticker_mapping'] = 'sec_cik'
        if not item.get('sector') and row.get('sector'):
            item['sector'] = row['sector']

    for company in companies.values():
        company['symbols'].sort()
        company['source_tickers'].sort()
    output = {
        'companies': list(companies.values()),
        'excluded_rows': excluded,
        'unresolved_mappings': [],
        'unverified_listing_mappings': unverified,
        'source_row_count': len(source.get('rows', [])),
        'classified_equity_rows': classified_equity_rows,
        'eligible_equity_rows': eligible_rows,
        'issuer_description_exclusions': description_exclusions,
        'normalization_failure_count': len(normalization_failures),
        'normalization_failures': normalization_failures,
        'normalized_symbol_count': len({symbol for company in companies.values() for symbol in company['symbols']}),
        'sec_verified_company_count': sum(company.get('ticker_mapping') == 'sec_cik' for company in companies.values()),
        'direct_ticker_company_count': sum(company.get('ticker_mapping') == 'direct_issuer_ticker' for company in companies.values()),
        'mapping_method': 'SEC CIK when available; otherwise official iShares ticker plus normalized issuer name for company/share-class deduplication.',
    }
    return output


def index_category_views(universe, charts, calendar, session, settings, source):
    """Build descriptive S&P 500 sector/sub-industry views from retrieved constituents."""
    groups = {'sectors': {}, 'industries': {}}
    for company in universe.get('companies', []):
        sector = str(company.get('sector') or '').strip()
        industry = str(company.get('industry') or '').strip()
        for level, name, key in (('sectors', sector, 'sector'), ('industries', industry, 'industry')):
            if not name:
                continue
            group = groups[level].setdefault(name, {'name': name, 'level': 'Sector' if level == 'sectors' else 'Industry', 'sector': sector if level == 'industries' else None, 'members': []})
            group['members'].append(company)

    def summarize(group):
        eligible = len(group['members'])
        valid = {21: [], 50: []}
        above = {21: 0, 50: 0}
        returns = {21: [], 63: []}
        data_members = {21: 0, 50: 0}
        for company in group['members']:
            symbol = next(iter(company.get('symbols', [])), None)
            chart = charts.get(symbol) if symbol else None
            if not chart or (chart.get('meta', {}).get('instrumentType') not in (None, 'EQUITY')):
                continue
            prices = observation_map(chart)
            close = prices.get(session, {}).get('close') if session else None
            trend = trend_metric(chart, calendar, session, settings) if session else {}
            for period in settings.get('ema_periods', (21, 50)):
                ema_value = trend.get(f'ema{period}')
                if isinstance(close, (int, float)) and math.isfinite(close) and isinstance(ema_value, (int, float)) and math.isfinite(ema_value):
                    data_members[period] += 1
                    valid[period].append(close)
                    above[period] += int(close > ema_value)
            for window in (21, 63):
                metric_result = return_metric(chart, calendar, session, window) if session else {}
                value = metric_result.get('value') if metric_result.get('status') == 'valid' else None
                if isinstance(value, (int, float)) and math.isfinite(value):
                    returns[window].append(value)
        output = {
            'name': group['name'], 'level': group['level'],
            'sector': group.get('sector'),
            'company_count': eligible,
            'source': 'S&P 500 constituents classified by GICS Sector / GICS Sub-Industry',
            'session_date': session,
        }
        for period in settings.get('ema_periods', (21, 50)):
            count = data_members[period]
            output[f'valid_ema{period}_count'] = count
            output[f'above_ema{period}_count'] = above[period]
            output[f'breadth{period}_pct'] = 100 * above[period] / count if count else None
            output[f'coverage{period}_pct'] = 100 * count / eligible if eligible else None
        for window in (21, 63):
            values = returns[window]
            output[f'median_return{window}_pct'] = 100 * statistics.median(values) if values else None
            output[f'return{window}_valid_count'] = len(values)
            output[f'return{window}_coverage_pct'] = 100 * len(values) / eligible if eligible else None
        return output

    output = {key: sorted((summarize(row) for row in groups[key].values()), key=lambda row: row['name'].casefold()) for key in groups}
    output['source'] = {key: value for key, value in source.items() if key != 'rows'}
    output['membership_count'] = len(universe.get('companies', []))
    output['unclassified_count'] = sum(1 for row in universe.get('companies', []) if not row.get('sector') or not row.get('industry'))
    output['method'] = 'Equal-company descriptive aggregates. Return columns are medians of split-adjusted constituent returns; breadth is the share of constituents with retrieved prices that close above their own EMA. This is an S&P 500 subset, not whole-market industry breadth.'
    return output


def collect_inputs(holdings, existing_charts, context_holdings=None, interval=1.5, iwm_history_years=1, minimum_iwm_history_sessions=205):
    universes, mapping = fetch_universes()
    universes.update(context_holdings or {})
    mapped = {
        key: map_iwm_universe(value, mapping) if key == 'IWM' else map_universe(value, mapping, index=True)
        for key, value in universes.items()
    }
    mapped.setdefault('IWM', map_iwm_universe({'rows': []}, mapping))
    mapped.update({key: map_universe(value, mapping) for key, value in holdings.items()})
    iwm_universe = mapped.get('IWM', {'companies': []})
    iwm_symbols = {symbol for company in iwm_universe['companies'] for symbol in company['symbols']}
    non_iwm_symbols = {
        symbol
        for key, universe in mapped.items() if key != 'IWM'
        for row in universe['companies'] for symbol in row['symbols']
    }
    symbols = sorted(non_iwm_symbols - set(existing_charts))
    print(f'v5 breadth: collecting {len(symbols)} additional unique histories; {interval}s pacing.', flush=True)
    charts, errors = {}, {}
    for i, symbol in enumerate(symbols):
        if len(_YAHOO_BLOCKED_HOSTS) == 2:
            for pending in symbols[i:]:
                errors[pending] = 'Not requested: both Yahoo chart hosts were rate-limited during this breadth refresh.'
            break
        if i:
            time.sleep(interval)
        try:
            charts[symbol] = fetch_yahoo_chart(symbol)
        except Exception as exc:
            errors[symbol] = str(exc)
        if (i+1) % 50 == 0:
            print(f'v5 breadth histories: {i+1}/{len(symbols)} attempted, {len(errors)} unavailable.', flush=True)
    available = {**existing_charts, **charts}
    iwm_charts = {
        symbol: available[symbol]
        for symbol in sorted(iwm_symbols & set(available))
        if len(available[symbol].get('observations', [])) >= minimum_iwm_history_sessions
    }
    reused_count = len(iwm_charts)
    pending_iwm = sorted(iwm_symbols - set(iwm_charts))
    iwm_errors = {}
    history_shortfalls = {}
    iwm_interval = max(0.0, float(os.environ.get('THEMESCOPE_IWM_CHART_INTERVAL', interval)))
    print(
        f'IWM holdings prices: {len(iwm_symbols)} normalized company symbols; '
        f'{reused_count} existing histories reused; {len(pending_iwm)} requests at {iwm_interval:g}s pacing.',
        flush=True,
    )
    for index, symbol in enumerate(pending_iwm):
        if len(_YAHOO_BLOCKED_HOSTS) == 2:
            for pending in pending_iwm[index:]:
                iwm_errors[pending] = 'Not requested: both Yahoo chart hosts were rate-limited during this run.'
            break
        if index:
            time.sleep(iwm_interval)
        try:
            iwm_charts[symbol] = fetch_yahoo_chart(symbol, years=int(iwm_history_years))
            history_count = len(iwm_charts[symbol].get('observations', []))
            if history_count < minimum_iwm_history_sessions:
                history_shortfalls[symbol] = history_count
        except Exception as exc:
            iwm_errors[symbol] = str(exc)
        if (index + 1) % 25 == 0 or index + 1 == len(pending_iwm):
            print(
                f'IWM holdings price histories: {index + 1}/{len(pending_iwm)} requested, '
                f'{len(iwm_charts)}/{len(iwm_symbols)} retained, {len(iwm_errors)} unavailable.',
                flush=True,
            )
    mapped['IWM']['price_collection'] = {
        'history_years': int(iwm_history_years),
        'minimum_history_sessions': int(minimum_iwm_history_sessions),
        'normalized_company_symbols': len(iwm_symbols),
        'existing_history_reused': reused_count,
        'new_requests': len(pending_iwm),
        'downloaded_history_count': len(iwm_charts),
        'history_qualified_count': sum(len(chart.get('observations', [])) >= minimum_iwm_history_sessions for chart in iwm_charts.values()),
        'history_shortfall_count': len(history_shortfalls),
        'history_shortfall_details': history_shortfalls,
        'download_errors': len(iwm_errors),
        'download_error_details': iwm_errors,
    }
    return {
        'index_universes': universes,
        'security_mapping': mapping,
        'mapped_universes': mapped,
        'charts': charts,
        'chart_errors': errors,
        'holdings': holdings,
        'iwm_breadth_charts': iwm_charts,
        'iwm_breadth_errors': iwm_errors,
        'iwm_breadth_diagnostics': {
            'source_rows': iwm_universe.get('source_row_count'),
            'classified_equity_rows': iwm_universe.get('classified_equity_rows'),
            'eligible_equity_rows': iwm_universe.get('eligible_equity_rows'),
            'issuer_description_exclusions': iwm_universe.get('issuer_description_exclusions'),
            'normalization_failures': iwm_universe.get('normalization_failure_count'),
            'excluded_source_rows': len(iwm_universe.get('excluded_rows', [])),
            'normalized_symbols': iwm_universe.get('normalized_symbol_count'),
            'sec_verified_companies': iwm_universe.get('sec_verified_company_count'),
            'direct_ticker_companies': iwm_universe.get('direct_ticker_company_count'),
            'unverified_listing_mappings': len(iwm_universe.get('unverified_listing_mappings', [])),
            'history_years': int(iwm_history_years),
            'minimum_history_sessions': int(minimum_iwm_history_sessions),
            'reused_histories': reused_count,
            'new_requests': len(pending_iwm),
            'downloaded_histories': len(iwm_charts),
            'history_qualified': sum(len(chart.get('observations', [])) >= minimum_iwm_history_sessions for chart in iwm_charts.values()),
            'history_shortfalls': history_shortfalls,
            'download_errors': len(iwm_errors),
            'download_error_details': iwm_errors,
        },
    }


def participation(universe, source, charts, calendar, session, settings, run_date):
    companies = []
    instrument_exclusions = []
    for company in universe.get('companies', []):
        symbol = next(iter(company.get('symbols', [])), None)
        kind = charts.get(symbol, {}).get('meta', {}).get('instrumentType')
        if kind and kind != 'EQUITY':
            instrument_exclusions.append({'company_id':company['company_id'], 'symbol':symbol, 'reason':'Retrieved instrument type '+kind+' is not equity'})
        else:
            companies.append(company)
    n = len(companies)
    max_age = int(settings.get('maximum_holdings_age_days', 35))
    date_semantics = source.get('date_semantics')
    if not date_semantics:
        date_semantics = 'observation' if 'observed at retrieval' in str(source.get('asof_basis', '')).casefold() else 'effective'
    effective_date = source.get('effective_date') or (source.get('as_of') if date_semantics == 'effective' else None)
    observation_date = source.get('observation_date') or (source.get('as_of') if date_semantics == 'observation' else None)
    source_date = observation_date if date_semantics == 'observation' else effective_date
    freshness_reason = None
    age = None
    try:
        if date_semantics == 'observation':
            # The page observation may follow the latest completed market
            # session. Measure its age against retrieval time, not that session.
            retrieved_date = str(source.get('retrieved_at') or run_date)[:10]
            age = (date.fromisoformat(retrieved_date) - date.fromisoformat(observation_date)).days
        else:
            effective = date.fromisoformat(effective_date)
            metric_session = date.fromisoformat(session or run_date)
            age = (metric_session - effective).days
        if age < 0:
            freshness_reason = 'effective_future' if date_semantics == 'effective' else 'observation_future'
        elif age > max_age:
            freshness_reason = 'stale'
    except (ValueError, KeyError, TypeError):
        freshness_reason = 'date_missing'
    periods = tuple(int(period) for period in settings.get('ema_periods', (21, 50)))
    counts = {period: [0, 0] for period in periods}
    minimum_sample = int(settings.get('minimum_breadth_sample', 8))
    minimum_coverage = float(settings.get('minimum_breadth_coverage', .8))
    company_metrics = []
    for company in companies:
        values = {}
        # Deterministic primary share class, no choosing the best-performing share class.
        symbol = next(iter(company['symbols']), None)
        chart = charts.get(symbol)
        if chart and chart.get('meta', {}).get('instrumentType') == 'EQUITY':
            trend = trend_metric(chart, calendar, session, settings)
            price = observation_map(chart).get(session, {}).get('close')
            for period in periods:
                ema = trend.get(f'ema{period}')
                if isinstance(price, (int,float)) and isinstance(ema, (int,float)) and math.isfinite(price) and math.isfinite(ema):
                    counts[period][1] += 1
                    above = price > ema
                    counts[period][0] += int(above)
                    values[str(period)] = above
        company_metrics.append({'company_id': company['company_id'], 'symbol': symbol, 'above_ema': values})
    unresolved_count = len(universe.get('unresolved_mappings', []))
    output = {
        'eligible_count': n,
        'holdings_asof': source_date or source.get('as_of'),
        'observation_date': observation_date,
        'effective_date': effective_date,
        'date_semantics': date_semantics,
        'universe_label': source.get('universe_label'),
        'freshness_age_days': age,
        'excluded_count': len(universe.get('excluded_rows', [])) + len(instrument_exclusions),
        'instrument_exclusions': instrument_exclusions,
        'unresolved_mapping_count': unresolved_count,
        'source_diagnostic': source.get('_retrieval_error'),
        'companies': company_metrics,
    }
    for period, (above, valid) in counts.items():
        raw = 100 * above / valid if valid else None
        coverage = 100 * valid / n if n else None
        configured = source.get('_configured', bool(source.get('rows') or source.get('as_of') or source.get('observation_date') or source.get('effective_date')))
        unresolved_blocks_coverage = n > 0 and (n - unresolved_count) / n < minimum_coverage
        reason_code, reason = None, None
        if not configured:
            reason_code, reason = 'not_configured', 'Official holdings source is not configured for this ETF.'
        elif source.get('_retrieval_error'):
            reason_code, reason = 'retrieval_failed', 'Holdings source retrieval failed for this run.'
        elif freshness_reason == 'effective_future':
            reason_code, reason = 'effective_future', 'Holdings effective date is after the selected market session.'
        elif freshness_reason == 'stale':
            reason_code, reason = 'stale', 'Holdings are older than the configured freshness limit.'
        elif freshness_reason:
            reason_code, reason = 'date_missing', 'Holdings effective or observation date is unavailable or invalid.'
        elif not n:
            reason_code, reason = 'no_eligible_holdings', 'No eligible equity holdings were obtained from the configured source.'
        elif unresolved_blocks_coverage and valid == 0:
            reason_code, reason = 'ticker_mapping_unresolved', 'Too many holdings could not be mapped to verified price symbols.'
        elif valid < minimum_sample:
            reason_code, reason = 'too_few_valid_holdings', 'Fewer than the configured minimum number of holdings have usable price data.'
        elif coverage is not None and coverage / 100 < minimum_coverage:
            reason_code, reason = 'price_coverage_low', 'Usable holding-price coverage is below the configured threshold.'
        elif unresolved_blocks_coverage:
            reason_code, reason = 'ticker_mapping_unresolved', 'Too many holdings could not be mapped to verified price symbols.'
        output[str(period)] = metric(
            raw, reason,
            above_count=above, valid_count=valid, eligible_count=n, coverage_pct=coverage,
            minimum_sample=minimum_sample, minimum_coverage_pct=minimum_coverage * 100,
            session_date=session, as_of=source_date or source.get('as_of'),
            date_semantics=date_semantics, observation_count=valid, reason_code=reason_code,
            observation_date=observation_date, effective_date=effective_date, freshness_age_days=age,
        )
    return output


def percentiles(values, session, minimum_peers=10):
    valid = sorted((float(v), k) for k,v in values.items() if isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v))
    n = len(valid)
    out = {k: metric(reason=f'Requires {minimum_peers} valid ETF peers; {n} available' if n < minimum_peers else 'Excess return unavailable', peer_count=n, session_date=session) for k in values}
    if n < minimum_peers:
        return out
    i = 0
    while i < n:
        j = i + 1
        while j < n and valid[j][0] == valid[i][0]:
            j += 1
        value = 100 * (((i+1+j)/2)-1)/(n-1)
        for _, key in valid[i:j]:
            out[key] = metric(value, peer_count=n, session_date=session)
        i = j
    return out


def strength(percentile):
    """v6.1 Current/Medium are the ETF's price-relative percentile only."""
    if percentile.get('status') != 'valid':
        return metric(reason=percentile.get('reason') or 'ETF return percentile unavailable', peer_count=percentile.get('peer_count'))
    return metric(float(percentile['value']), peer_count=percentile.get('peer_count'))


def overall_score(current, medium, weights=(.6, .4)):
    if current.get('status') != 'valid' or medium.get('status') != 'valid':
        return metric(reason='Current and Medium must both be valid')
    return metric(weights[0] * current['value'] + weights[1] * medium['value'])


def theme_state(current, medium, threshold=50):
    if current is None or medium is None:
        return '—'
    return ('Leading' if medium >= threshold else 'Improving') if current >= threshold else ('Fading' if medium >= threshold else 'Lagging')


def market_condition(price, ema, breadth, period, threshold=50):
    if price is None or ema is None or breadth.get('status') != 'valid':
        return metric(reason=breadth.get('reason') or 'Price or EMA unavailable')
    horizon = 'short-term' if period == 21 else 'medium-term'
    strong, broad = price > ema, breadth['value'] >= threshold
    text = f'Broad {horizon} strength' if strong and broad else f'Narrow {horizon} strength' if strong else f'Internal strength, index below EMA{period}' if broad else f'Broad {horizon} weakness'
    return metric(text)


def breadth_change(current, earlier, current_session=None, earlier_session=None):
    if current.get('status') != 'valid' or earlier.get('status') != 'valid':
        reason = current.get('reason') if current.get('status') != 'valid' else 'The earlier breadth observation required for change is unavailable.'
        return metric(reason=reason or 'The earlier breadth observation required for change is unavailable.', reason_code=current.get('reason_code') if current.get('status') != 'valid' else 'historical_observation_missing', current_session=current_session, earlier_session=earlier_session, current_reason=current.get('reason'), earlier_reason=earlier.get('reason'))
    return metric(
        float(current['value'] - earlier['value']),
        current_session=current_session,
        earlier_session=earlier_session,
        method='Current breadth minus five-session-prior breadth, in percentage points, using one fixed current universe',
    )


def _five_sessions_before(calendar, session):
    try:
        index = calendar.index(session)
    except ValueError:
        return None
    return calendar[index - 5] if index >= 5 else None


def historical_rank_metrics(themes, charts, calendar, session, score_methodology, minimum_peers):
    """Recalculate relative-strength scores and ranks at the same session five days earlier."""
    earlier_session = _five_sessions_before(calendar, session) if session else None
    output = {theme.get('id'): {
        'rank_t_minus_5': None,
        'rank_t_minus_5_status': 'unavailable',
        'historical_rank_status': 'unavailable',
        'rank_t_minus_5_reason': 'Five-session-prior ranking session is unavailable' if not earlier_session else None,
        'historical_rank_peer_count': 0,
        'historical_rank_session': earlier_session,
    } for theme in themes}
    if not earlier_session:
        return output
    benchmark = {str(window): return_metric(charts.get('SPY', {}), calendar, earlier_session, window) for window in (21, 63)}
    candidates = {}
    for theme in themes:
        anchor = theme.get('anchor')
        chart = charts.get(anchor)
        if not chart:
            continue
        returns = {str(window): return_metric(chart, calendar, earlier_session, window) for window in (21, 63)}
        if any(returns[w].get('status') != 'valid' or benchmark[w].get('status') != 'valid' for w in ('21', '63')):
            continue
        candidates[theme['id']] = (
            returns['21']['value'] - benchmark['21']['value'],
            returns['63']['value'] - benchmark['63']['value'],
        )
    peer_count = len(candidates)
    for item in output.values():
        item['historical_rank_peer_count'] = peer_count
    if peer_count < minimum_peers:
        for item in output.values():
            item['rank_t_minus_5_reason'] = f'Requires {minimum_peers} valid historical ETF peers; {peer_count} available'
            item['historical_rank_reason'] = item['rank_t_minus_5_reason']
        return output

    p21 = percentiles({key: value[0] for key, value in candidates.items()}, earlier_session, minimum_peers)
    p63 = percentiles({key: value[1] for key, value in candidates.items()}, earlier_session, minimum_peers)
    weights = score_methodology.get('theme_score_weights', {})
    weight21 = float(weights.get('current_strength', 0.6))
    weight63 = float(weights.get('medium_strength', 0.4))
    scores = {
        key: weight21 * p21[key]['value'] + weight63 * p63[key]['value']
        for key in candidates
        if p21[key].get('status') == 'valid' and p63[key].get('status') == 'valid'
    }
    historical_ranks = average_ranks(scores)
    for key, average_rank in historical_ranks.items():
        if average_rank is not None:
            output[key] = {
                'rank_t_minus_5': average_rank,
                'rank_t_minus_5_status': 'valid',
                'historical_rank_status': 'valid',
                'rank_t_minus_5_reason': None,
                'historical_rank_reason': None,
                'historical_rank_peer_count': peer_count,
                'historical_rank_session': earlier_session,
                'historical_theme_score': scores[key],
            }
    for key, item in output.items():
        if key not in scores:
            item['rank_t_minus_5_reason'] = 'Historical ETF/SPY return endpoints are missing'
            item['historical_rank_reason'] = item['rank_t_minus_5_reason']
    return output


def apply(snapshot, raw):
    inputs = raw.get('v5', {})
    all_charts = {**raw.get('charts', {}), **inputs.get('charts', {}), **inputs.get('iwm_breadth_charts', {})}
    snapshot['last_source_retrieved_at'] = max((c.get('retrieved_at', '') for c in all_charts.values()), default=None)
    mapped = inputs.get('mapped_universes', {})
    date_ = snapshot.get('session_date')
    freshness_reference = date_ if snapshot.get('requested_asof') else snapshot['run_date']
    common = (all_charts, raw.get('session_calendar', []), date_, snapshot['settings'], freshness_reference)
    for market in snapshot['context']:
        symbol = market['ticker']
        source = dict(inputs.get('index_universes', {}).get(symbol) or raw.get('context_holdings', {}).get(symbol, {}))
        source['_configured'] = symbol in inputs.get('index_universes', {}) or symbol in raw.get('context_holdings', {})
        source['_retrieval_error'] = raw.get('errors', {}).get('holdings', {}).get(symbol) or inputs.get('index_errors', {}).get(symbol)
        breadth = participation(mapped.get(symbol, {}), source, *common)
        market['index_breadth'] = breadth
        market['index_constituent_asof'] = source.get('as_of')
        market['index_source'] = {k: v for k, v in source.items() if k != 'rows' and not str(k).startswith('_')}
        market['index_eligible_count'] = breadth['eligible_count']
        market['field_status'] = {}
        market_chart = raw.get('charts', {}).get(symbol)
        trend = trend_metric(market_chart, raw['session_calendar'], date_, snapshot['settings']) if market_chart else {
            'state': 'Unavailable', 'status': 'unavailable', 'reason': raw.get('errors', {}).get('charts', {}).get(symbol, 'Price source unavailable'),
            'ema21': None, 'ema50': None,
        }
        market['ema21'] = trend.get('ema21')
        market['ema50'] = trend.get('ema50')
        market['ema21_distance'] = (market.get('price_close') / market['ema21'] - 1) if market.get('price_close') is not None and market.get('ema21') else None
        market['ema50_distance'] = (market.get('price_close') / market['ema50'] - 1) if market.get('price_close') is not None and market.get('ema50') else None
        market['price_vs_ema21_pct'] = market['ema21_distance'] * 100 if market['ema21_distance'] is not None else None
        market['price_vs_ema50_pct'] = market['ema50_distance'] * 100 if market['ema50_distance'] is not None else None
        for period in snapshot['settings'].get('ema_periods', (21, 50)):
            item = breadth[str(period)]
            market[f'index_valid_ema{period}_count'] = item['valid_count']
            market[f'index_breadth{period}_pct'] = item['value']
            market[f'index_coverage{period}_pct'] = item['coverage_pct']
            condition = market_condition(market.get('price_close'), trend.get(f'ema{period}'), item, period, float(snapshot['settings'].get('market_breadth_threshold', 50)))
            market[f'market_condition{period}'] = condition['value'] or 'Unavailable'
            market[f'above_ema{period}'] = market['price_close'] > trend[f'ema{period}'] if market.get('price_close') is not None and trend.get(f'ema{period}') is not None else None
            market['field_status'][f'index_breadth{period}_pct'] = item
            market['field_status'][f'market_condition{period}'] = condition
        earlier_session = _five_sessions_before(raw.get('session_calendar', []), date_)
        earlier_breadth = participation(mapped.get(symbol, {}), source, all_charts, raw.get('session_calendar', []), earlier_session, snapshot['settings'], freshness_reference) if earlier_session else {}
        for period in snapshot['settings'].get('ema_periods', (21, 50)):
            prior = earlier_breadth.get(str(period), metric(reason='Five-session-prior market breadth is unavailable'))
            current = breadth[str(period)]
            change = breadth_change(current, prior, date_, earlier_session)
            market[f'breadth{period}_t_minus_5'] = prior.get('value') if prior.get('status') == 'valid' else None
            market[f'breadth{period}_change_5_pp'] = change.get('value')
            market['field_status'][f'breadth{period}_t_minus_5'] = prior
            market['field_status'][f'breadth{period}_change_5_pp'] = change
    snapshot['classification_catalog'] = index_category_views(
        mapped.get('SPY', {}), all_charts, raw.get('session_calendar', []), date_,
        snapshot['settings'], inputs.get('index_universes', {}).get('SPY', {}),
    )
    peer_minimum = int(snapshot['settings']['minimum_percentile_peers'])
    def eligible_peer(theme):
        # The cross-sectional universe is the complete dated set of primary
        # eligible sector/theme ETF anchors. Holdings and stock review are
        # intentionally outside this eligibility and score dependency graph.
        if not theme.get('anchor_screen', {}).get('anchor_screen_valid', False):
            return False
        return all(theme.get('returns', {}).get(window, {}).get('status') == 'valid' for window in ('21', '63'))
    p21 = percentiles({t['id']: t['excess_returns']['21']['value'] if eligible_peer(t) and t['excess_returns']['21'].get('status') == 'valid' else None for t in snapshot['themes']}, date_, peer_minimum)
    p63 = percentiles({t['id']: t['excess_returns']['63']['value'] if eligible_peer(t) and t['excess_returns']['63'].get('status') == 'valid' else None for t in snapshot['themes']}, date_, peer_minimum)
    weights = snapshot.get('score_methodology', {})
    current_weights = weights.get('current_strength_weights', {})
    medium_weights = weights.get('medium_strength_weights', {})
    final_weights = weights.get('theme_score_weights', {})
    if current_weights != {'excess21_percentile': 1.0} or medium_weights != {'excess63_percentile': 1.0} or not final_weights or 'state_threshold' not in weights:
        raise ValueError('Configured score_methodology is required to calculate v6.1 scores')
    threshold = float(weights['state_threshold'])
    for theme in snapshot['themes']:
        source = dict(raw.get('holdings', {}).get(theme['anchor'], {}))
        configured_source = theme.get('holdings_source') or {}
        source['_configured'] = bool(configured_source.get('provider') or configured_source.get('url') or theme['anchor'] in raw.get('holdings', {}))
        source['_retrieval_error'] = raw.get('errors', {}).get('holdings', {}).get(theme['anchor'])
        breadth = participation(mapped.get(theme['anchor'], {}), source, *common)
        earlier_session = _five_sessions_before(raw.get('session_calendar', []), date_)
        earlier_breadth = participation(mapped.get(theme['anchor'], {}), source, all_charts, raw.get('session_calendar', []), earlier_session, snapshot['settings'], freshness_reference) if earlier_session else {}
        theme['holdings_breadth'] = breadth
        theme['holdings_asof'] = source.get('as_of')
        theme['breadth_eligible_equity_count'] = breadth['eligible_count']
        theme['field_status'] = {}
        for period in snapshot['settings'].get('ema_periods', (21, 50)):
            item = breadth[str(period)]
            theme[f'breadth_valid_ema{period}_count'] = item['valid_count']
            theme[f'etf_breadth{period}_pct'] = item['value']
            theme[f'breadth_coverage{period}_pct'] = item['coverage_pct']
            theme['field_status'][f'etf_breadth{period}_pct'] = item
            prior = earlier_breadth.get(str(period), metric(reason='Five-session-prior holdings breadth is unavailable'))
            change = breadth_change(item, prior, date_, earlier_session)
            theme[f'breadth{period}_t_minus_5'] = prior.get('value') if prior.get('status') == 'valid' else None
            theme[f'breadth{period}_change_5_pp'] = change.get('value')
            theme['field_status'][f'breadth{period}_t_minus_5'] = prior
            theme['field_status'][f'breadth{period}_change_5_pp'] = change
            distance = theme.get(f'ema{period}_distance')
            theme[f'above_ema{period}'] = distance > 0 if distance is not None else None
        current = strength(p21[theme['id']])
        medium = strength(p63[theme['id']])
        score = overall_score(current, medium, (float(final_weights['current_strength']), float(final_weights['medium_strength'])))
        for field,item in [('percentile_excess21',p21[theme['id']]),('percentile_excess63',p63[theme['id']]),('current_strength_score',current),('medium_strength_score',medium),('theme_score',score)]:
            item['session_date'] = date_
            theme[field] = item['value'] if item['status'] == 'valid' else None
            theme['field_status'][field] = item
        theme['theme_state'] = theme_state(current['value'], medium['value'], threshold)
        theme['score_method'] = weights.get('score_method', 'price_relative_strength_v6_2')
        theme['score_peer_count_21'] = p21[theme['id']].get('peer_count')
        theme['score_peer_count_63'] = p63[theme['id']].get('peer_count')
        theme['score_unavailable_reason'] = score.get('reason')
        theme['breadth_status_21'] = breadth['21']['status']
        theme['breadth_status_50'] = breadth['50']['status']
        theme['breadth_unavailable_reason_21'] = breadth['21'].get('reason')
        theme['breadth_unavailable_reason_50'] = breadth['50'].get('reason')
        theme['has_curated_watchlist'] = bool(theme.get('selected'))
        theme['curated_watchlist_count'] = len(theme.get('selected', []))
        theme['ranking_universe_date'] = date_
        theme['ranking_peer_count21'] = p21[theme['id']]['peer_count']
        theme['ranking_peer_count63'] = p63[theme['id']]['peer_count']
        theme['stock_scope'] = 'Curated watchlist' if theme['selected'] else 'ETF-only'
        exchange = str(raw.get('charts', {}).get(theme['anchor'], {}).get('meta', {}).get('fullExchangeName', '')).upper()
        prefix = 'NASDAQ' if 'NASDAQ' in exchange else 'AMEX' if 'ARCA' in exchange or 'AMEX' in exchange or 'AMERICAN' in exchange else 'NYSE' if exchange == 'NYSE' else None
        theme['chart_url'] = f"https://www.tradingview.com/chart/?symbol={prefix}:{theme['anchor']}" if prefix else None
    for theme in snapshot['themes']:
        if 'breadth' in theme:
            theme['curated_subset_breadth_diagnostic'] = theme.pop('breadth')
    snapshot.setdefault('sources', {})['constituent_history_errors'] = {
        **inputs.get('chart_errors', {}),
        **{'IWM:' + key: value for key, value in inputs.get('iwm_breadth_errors', {}).items()},
    }
    snapshot['sources']['partial'] = snapshot['sources'].get('partial', False) or bool(inputs.get('chart_errors')) or bool(inputs.get('iwm_breadth_errors')) or bool(inputs.get('iwm_breadth_diagnostics', {}).get('history_shortfalls'))
    snapshot['sources']['evidence_freshness_provider'] = 'SEC annual submissions only for membership records explicitly requiring deeper filing review'
    snapshot['limitations'] = [
        f"{len(snapshot['themes'])} dated primary ETF anchors are included across {sum(1 for t in snapshot['themes'] if t.get('level') == 'Sector')} standard sectors and curated industry/theme exposures. Current and Medium are price-return percentiles among eligible anchors; breadth and curated stock lists are independent evidence layers.",
        'S&P 500 list is a reproducible current Wikipedia table, not an official point-in-time membership feed. Its as-of is the retrieval observation date.',
        'Sector and industry summaries are equal-company descriptions of currently listed S&P 500 constituents, not whole-market rankings or validated trading scores. Industry names are the source table’s GICS Sub-Industry labels.',
        'ETF holdings breadth is equal-company participation of the official equity holdings universe, not whole-industry breadth. Incomplete foreign listing mappings reduce breadth coverage but do not affect ETF score or eligibility.',
        'IWM holdings breadth uses the current official iShares IWM ETF holdings file as a practical Russell 2000 proxy; it is not official Russell 2000 constituent breadth.',
        'VIX is a separate volatility context series with no constituent breadth or ETF score/state dependency.',
        'Yahoo adjusted close and split conventions are vendor definitions; there is no guaranteed availability or publication delay.',
        'Nasdaq does not supply a separate market-cap field timestamp; stock eligibility is provisional.',
        'Curated company-theme classifications use recorded Core/Related rationale and source; non-anchor members are allowed. Holdings are not a membership gate.',
        'Scores are fixed ranking conventions, not validated entry signals, predictions or portfolio allocations.'
    ]
    snapshot['score_methodology'] = {
        'current_strength_weights': current_weights,
        'medium_strength_weights': medium_weights,
        'theme_score_weights': final_weights,
        'minimum_peers': peer_minimum,
        'state_threshold': threshold,
        'score_method': weights.get('score_method', 'price_relative_strength_v6_2'),
        'purpose': 'Consistent relative-strength ranking for manual review; not a prediction or entry signal',
    }
    snapshot['schema_version'] = '6.2'
    snapshot['methodology_version'] = '6.2'
    return snapshot


def apply_historical_ranks(snapshot, raw):
    """Attach recomputed t-5 ranks after runtime eligibility defines today's peer set."""
    inputs = raw.get('v5', {})
    charts = {**raw.get('charts', {}), **inputs.get('charts', {}), **inputs.get('iwm_breadth_charts', {})}
    weights = snapshot.get('score_methodology', {})
    peer_minimum = int(weights.get('minimum_peers', snapshot.get('settings', {}).get('minimum_percentile_peers', 10)))
    metrics = historical_rank_metrics(
        snapshot.get('themes', []), charts, raw.get('session_calendar', []),
        snapshot.get('session_date'), weights, peer_minimum,
    )
    snapshot['historical_rank_method'] = 'Recomputed ETF/SPY 21- and 63-session excess-return percentile score at t-5; same current runtime-eligible ETF peer set; average percentile ties and average rank ties.'
    for theme in snapshot.get('themes', []):
        hist = metrics.get(theme.get('id'), {})
        current_rank = theme.get('global_rank')
        prior_rank = hist.get('rank_t_minus_5')
        theme.update({
            'rank_current': current_rank,
            'rank_t_minus_5': prior_rank,
            'rank_change_5': prior_rank - current_rank if prior_rank is not None and current_rank is not None else None,
            'historical_rank_peer_count': hist.get('historical_rank_peer_count', 0),
            'historical_rank_status': hist.get('historical_rank_status', hist.get('rank_t_minus_5_status', 'unavailable')),
            'historical_rank_reason': hist.get('historical_rank_reason') or hist.get('rank_t_minus_5_reason'),
            'historical_rank_session': hist.get('historical_rank_session'),
        })
        theme.setdefault('field_status', {})['rank_t_minus_5'] = metric(
            prior_rank,
            reason=theme['historical_rank_reason'] if prior_rank is None else None,
            peer_count=theme['historical_rank_peer_count'],
            session_date=theme.get('historical_rank_session'),
        )
        theme['field_status']['rank_change_5'] = metric(
            theme['rank_change_5'],
            reason=theme['historical_rank_reason'] if theme['rank_change_5'] is None else None,
            peer_count=theme['historical_rank_peer_count'],
            session_date=snapshot.get('session_date'),
        )
        theme.setdefault('fields', {}).update({
            'rank_current': {'value': current_rank, 'status': 'valid' if current_rank is not None else 'unavailable', 'observation_date': snapshot.get('session_date'), 'unavailable_reason': None if current_rank is not None else 'Current eligible ranking is unavailable'},
            'rank_t_minus_5': {'value': prior_rank, 'status': theme['historical_rank_status'], 'observation_date': theme.get('historical_rank_session'), 'unavailable_reason': theme['historical_rank_reason']},
            'rank_change_5': {'value': theme['rank_change_5'], 'status': 'valid' if theme['rank_change_5'] is not None else 'unavailable', 'observation_date': snapshot.get('session_date'), 'unavailable_reason': theme['historical_rank_reason']},
            'historical_rank_peer_count': {'value': theme['historical_rank_peer_count'], 'status': 'valid', 'observation_date': theme.get('historical_rank_session'), 'unavailable_reason': None},
        })
    snapshot['historical_rank_metrics'] = metrics
    return snapshot
