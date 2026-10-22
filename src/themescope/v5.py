"""v5 constituent universes, independent participation, and explicit score conventions."""
from datetime import date, datetime, timezone
import hashlib
import math
import re
import time
from .sources import _request, _TableParser, request_json, fetch_yahoo_chart, _YAHOO_BLOCKED_HOSTS
from .metrics import observation_map, trend_metric

VERSION = 'themescope-v5.0'


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
            rows.append({'ticker': row[0], 'company': row[1], 'company_id': str(int(row[6])), 'security_type': 'EQUITY'})
    if len(rows) < 450:
        raise ValueError('S&P 500 constituent parser returned an incomplete list')
    spy = {'as_of': now[:10], 'asof_basis': 'Current constituent page observed at retrieval; not an official effective-date assertion', 'url': url, 'retrieved_at': now, 'source_sha256': hashlib.sha256(body).hexdigest(), 'rows': rows}
    url = 'https://api.nasdaq.com/api/quote/list-type/nasdaq100'
    data = request_json(url)['data']
    rows = [{'ticker': row['symbol'], 'company': row['companyName'], 'company_id': str(listings.get(row['symbol'], {}).get('cik') or row['symbol']), 'security_type': 'EQUITY'} for row in data['data']['rows']]
    if len(rows) != int(data['totalrecords']) or len(rows) < 90:
        raise ValueError('Nasdaq-100 constituent response incomplete')
    qqq = {'as_of': datetime.strptime(data['date'], '%b %d, %Y').date().isoformat(), 'asof_basis': 'Nasdaq response date', 'url': url, 'retrieved_at': now, 'rows': rows}
    return {'SPY': spy, 'QQQ': qqq}, mapping


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
            companies[company_id] = {'company_id': company_id, 'company': row.get('company'), 'symbols': [], 'source_tickers': []}
        group = companies[company_id]
        group['source_tickers'].append(ticker)
        if symbol and symbol not in group['symbols']:
            group['symbols'].append(symbol)
        if not mapped:
            unresolved.append({'ticker': ticker, 'reason': 'No verified SEC listing/country mapping; retained in equity coverage denominator'})
    for row in companies.values():
        row['symbols'].sort()
    return {'companies': list(companies.values()), 'excluded_rows': excluded, 'unresolved_mappings': unresolved, 'source_row_count': len(source.get('rows', []))}


def collect_inputs(holdings, existing_charts, interval=1.5):
    universes, mapping = fetch_universes()
    mapped = {key: map_universe(value, mapping, index=True) for key, value in universes.items()}
    mapped.update({key: map_universe(value, mapping) for key, value in holdings.items()})
    symbols = sorted({symbol for universe in mapped.values() for row in universe['companies'] for symbol in row['symbols']} - set(existing_charts))
    print(f'v5 breadth: collecting {len(symbols)} additional unique histories; {interval}s pacing.', flush=True)
    charts, errors = {}, {}
    for i, symbol in enumerate(symbols):
        if len(_YAHOO_BLOCKED_HOSTS) == 2:
            raise RuntimeError('Both Yahoo chart hosts rate-limited. Breadth refresh stopped; prior dashboard preserved.')
        if i:
            time.sleep(interval)
        try:
            charts[symbol] = fetch_yahoo_chart(symbol)
        except Exception as exc:
            message = str(exc)
            if any(marker in message.lower() for marker in ('http error 403', 'http error 429', 'http 429', 'http error 500', 'http error 502', 'http error 503', 'http error 504', 'timed out', 'timeout', 'urlerror', 'circuit open')):
                raise RuntimeError(f'Constituent history transport failure for {symbol}; refresh rejected: {message}') from exc
            errors[symbol] = message
        if (i+1) % 50 == 0:
            print(f'v5 breadth histories: {i+1}/{len(symbols)} attempted, {len(errors)} unavailable.', flush=True)
    return {'index_universes': universes, 'security_mapping': mapping, 'mapped_universes': mapped, 'charts': charts, 'chart_errors': errors, 'holdings': holdings}


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
    try:
        age = (date.fromisoformat(run_date) - date.fromisoformat(source['as_of'])).days
        fresh = 0 <= age <= 35
    except (ValueError, KeyError, TypeError):
        fresh = False
    counts = {21: [0, 0], 50: [0, 0]}
    company_metrics = []
    for company in companies:
        values = {}
        # Deterministic primary share class, no choosing the best-performing share class.
        symbol = next(iter(company['symbols']), None)
        chart = charts.get(symbol)
        if chart and chart.get('meta', {}).get('instrumentType') == 'EQUITY':
            trend = trend_metric(chart, calendar, session, settings)
            price = observation_map(chart).get(session, {}).get('close')
            for period in (21, 50):
                ema = trend.get(f'ema{period}')
                if isinstance(price, (int,float)) and isinstance(ema, (int,float)) and math.isfinite(price) and math.isfinite(ema):
                    counts[period][1] += 1
                    above = price > ema
                    counts[period][0] += int(above)
                    values[str(period)] = above
        company_metrics.append({'company_id': company['company_id'], 'symbol': symbol, 'above_ema': values})
    output = {'eligible_count': n, 'holdings_asof': source.get('as_of'), 'excluded_count': len(universe.get('excluded_rows', [])) + len(instrument_exclusions), 'instrument_exclusions': instrument_exclusions, 'unresolved_mapping_count': len(universe.get('unresolved_mappings', [])), 'companies': company_metrics}
    for period, (above, valid) in counts.items():
        raw = 100 * above / valid if valid else None
        coverage = 100 * valid / n if n else None
        reason = ('Holdings/constituent date unavailable, future, or older than 35 days' if not fresh else 'No eligible equity companies' if not n else f'Only {valid} valid companies; at least 8 required' if valid < 8 else f'Price coverage {valid}/{n} below 80%' if valid/n < .8 else None)
        output[str(period)] = metric(raw, reason, above_count=above, valid_count=valid, eligible_count=n, coverage_pct=coverage, session_date=session, as_of=source.get('as_of'), observation_count=valid)
    return output


def percentiles(values, session):
    valid = sorted((float(v), k) for k,v in values.items() if isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v))
    n = len(valid)
    out = {k: metric(reason=f'Requires 10 valid ETF peers; {n} available' if n < 10 else 'Excess return unavailable', peer_count=n, session_date=session) for k in values}
    if n < 10:
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


def strength(percentile, breadth):
    if percentile.get('status') != 'valid' or breadth.get('status') != 'valid':
        return metric(reason='; '.join(str(m.get('reason')) for m in (percentile, breadth) if m.get('status') != 'valid'))
    return metric(.7 * percentile['value'] + .3 * breadth['value'])


def overall_score(current, medium):
    if current.get('status') != 'valid' or medium.get('status') != 'valid':
        return metric(reason='CurrentStrength and MediumStrength must both be valid')
    return metric(.6 * current['value'] + .4 * medium['value'])


def theme_state(current, medium):
    if current is None or medium is None:
        return 'Unavailable'
    return ('Leading' if medium >= 50 else 'Short-term strength only') if current >= 50 else ('Medium-term strength only' if medium >= 50 else 'Lagging')


def market_condition(price, ema, breadth, period):
    if price is None or ema is None or breadth.get('status') != 'valid':
        return metric(reason=breadth.get('reason') or 'Price or EMA unavailable')
    horizon = 'short-term' if period == 21 else 'medium-term'
    strong, broad = price > ema, breadth['value'] >= 50
    text = f'Broad {horizon} strength' if strong and broad else f'Narrow {horizon} strength' if strong else f'Internal strength, index below EMA{period}' if broad else f'Broad {horizon} weakness'
    return metric(text)


def apply(snapshot, raw):
    inputs = raw.get('v5', {})
    all_charts = {**raw.get('charts', {}), **inputs.get('charts', {})}
    snapshot['last_source_retrieved_at'] = max((c.get('retrieved_at', '') for c in all_charts.values()), default=None)
    mapped = inputs.get('mapped_universes', {})
    date_ = snapshot.get('session_date')
    common = (all_charts, raw.get('session_calendar', []), date_, snapshot['settings'], snapshot['run_date'])
    for market in snapshot['context']:
        symbol = market['ticker']
        source = inputs.get('index_universes', {}).get(symbol, {})
        breadth = participation(mapped.get(symbol, {}), source, *common)
        market['index_breadth'] = breadth
        market['index_constituent_asof'] = source.get('as_of')
        market['index_source'] = {k:v for k,v in source.items() if k != 'rows'}
        market['index_eligible_count'] = breadth['eligible_count']
        market['field_status'] = {}
        trend = trend_metric(raw['charts'][symbol], raw['session_calendar'], date_, snapshot['settings'])
        for period in (21, 50):
            item = breadth[str(period)]
            market[f'index_valid_ema{period}_count'] = item['valid_count']
            market[f'index_breadth{period}_pct'] = item['value']
            market[f'index_coverage{period}_pct'] = item['coverage_pct']
            condition = market_condition(market.get('price_close'), trend.get(f'ema{period}'), item, period)
            market[f'market_condition{period}'] = condition['value'] or 'Unavailable'
            market[f'above_ema{period}'] = market['price_close'] > trend[f'ema{period}'] if market.get('price_close') is not None and trend.get(f'ema{period}') is not None else None
            market['field_status'][f'index_breadth{period}_pct'] = item
            market['field_status'][f'market_condition{period}'] = condition
    p21 = percentiles({t['id']: t['excess_returns']['21']['value'] if t.get('anchor_screen', {}).get('anchor_screen_valid', False) and t['excess_returns']['21'].get('status') == 'valid' else None for t in snapshot['themes']}, date_)
    p63 = percentiles({t['id']: t['excess_returns']['63']['value'] if t.get('anchor_screen', {}).get('anchor_screen_valid', False) and t['excess_returns']['63'].get('status') == 'valid' else None for t in snapshot['themes']}, date_)
    for theme in snapshot['themes']:
        source = raw.get('holdings', {}).get(theme['anchor'], {})
        breadth = participation(mapped.get(theme['anchor'], {}), source, *common)
        theme['holdings_breadth'] = breadth
        theme['holdings_asof'] = source.get('as_of')
        theme['breadth_eligible_equity_count'] = breadth['eligible_count']
        theme['field_status'] = {}
        for period in (21, 50):
            item = breadth[str(period)]
            theme[f'breadth_valid_ema{period}_count'] = item['valid_count']
            theme[f'etf_breadth{period}_pct'] = item['value']
            theme[f'breadth_coverage{period}_pct'] = item['coverage_pct']
            theme['field_status'][f'etf_breadth{period}_pct'] = item
            distance = theme.get(f'ema{period}_distance')
            theme[f'above_ema{period}'] = distance > 0 if distance is not None else None
        current = strength(p21[theme['id']], breadth['21'])
        medium = strength(p63[theme['id']], breadth['50'])
        score = overall_score(current, medium)
        for field,item in [('percentile_excess21',p21[theme['id']]),('percentile_excess63',p63[theme['id']]),('current_strength_score',current),('medium_strength_score',medium),('theme_score',score)]:
            item['session_date'] = date_
            theme[field] = item['value'] if item['status'] == 'valid' else None
            theme['field_status'][field] = item
        theme['theme_state'] = theme_state(current['value'], medium['value'])
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
    snapshot.setdefault('sources', {})['constituent_history_errors'] = inputs.get('chart_errors', {})
    snapshot['sources']['partial'] = snapshot['sources'].get('partial', False) or bool(inputs.get('chart_errors'))
    snapshot['sources']['evidence_freshness_provider'] = 'SEC annual submissions only for membership records explicitly requiring deeper filing review'
    snapshot['limitations'] = [
        'Six primary ETFs are retained. Percentiles require ten valid peers; scores remain unavailable without imputing or reweighting.',
        'S&P 500 list is a reproducible current Wikipedia table, not an official point-in-time membership feed. Its as-of is the retrieval observation date.',
        'Anchor breadth is equal-company participation of official equity holdings, not whole-industry breadth. Incomplete foreign listing mappings reduce price coverage.',
        'Yahoo adjusted close and split conventions are vendor definitions; there is no guaranteed availability or publication delay.',
        'Nasdaq does not supply a separate market-cap field timestamp; stock eligibility is provisional.',
        'Curated company-theme classifications use recorded Core/Related rationale and source; non-anchor members are allowed. Holdings are not a membership gate.',
        'Scores are fixed ranking conventions, not validated entry signals, predictions or portfolio allocations.'
    ]
    snapshot['schema_version'] = '5.0' 
    snapshot['score_methodology'] = {'current_weights': [0.7,0.3], 'medium_weights': [0.7,0.3], 'overall_weights': [0.6,0.4], 'minimum_peers':10, 'purpose':'Fixed ranking conventions, not optimized or validated predictive signals'}
    return snapshot
