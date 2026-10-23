"""v5 constituent universes, independent participation, and explicit score conventions."""
from datetime import date, datetime, timezone
import hashlib
import math
import re
import time
import statistics
from .sources import _request, _TableParser, request_json, fetch_yahoo_chart, _YAHOO_BLOCKED_HOSTS
from .metrics import observation_map, return_metric, trend_metric

VERSION = 'themescope-v6.1'


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
    spy = {'as_of': now[:10], 'asof_basis': 'Current constituent page observed at retrieval; not an official effective-date assertion', 'url': url, 'retrieved_at': now, 'source_sha256': hashlib.sha256(body).hexdigest(), 'rows': rows}
    url = 'https://api.nasdaq.com/api/quote/list-type/nasdaq100'
    data = request_json(url)['data']
    rows = [{'ticker': row['symbol'], 'company': row['companyName'], 'company_id': str(listings.get(row['symbol'], {}).get('cik') or row['symbol']), 'security_type': 'EQUITY'} for row in data['data']['rows']]
    if len(rows) != int(data['totalrecords']) or len(rows) < 90:
        raise ValueError('Nasdaq-100 constituent response incomplete')
    qqq = {'as_of': _nasdaq_effective_date(data.get('date')), 'asof_basis': 'Nasdaq response date', 'url': url, 'retrieved_at': now, 'rows': rows}
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


def collect_inputs(holdings, existing_charts, context_holdings=None, interval=1.5):
    universes, mapping = fetch_universes()
    universes.update(context_holdings or {})
    mapped = {key: map_universe(value, mapping, index=True) for key, value in universes.items()}
    mapped.update({key: map_universe(value, mapping) for key, value in holdings.items()})
    symbols = sorted({symbol for universe in mapped.values() for row in universe['companies'] for symbol in row['symbols']} - set(existing_charts))
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
    max_age = int(settings.get('maximum_holdings_age_days', 35))
    try:
        age = (date.fromisoformat(run_date) - date.fromisoformat(source['as_of'])).days
        fresh = 0 <= age <= max_age
    except (ValueError, KeyError, TypeError):
        fresh = False
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
    output = {'eligible_count': n, 'holdings_asof': source.get('as_of'), 'excluded_count': len(universe.get('excluded_rows', [])) + len(instrument_exclusions), 'instrument_exclusions': instrument_exclusions, 'unresolved_mapping_count': len(universe.get('unresolved_mappings', [])), 'companies': company_metrics}
    for period, (above, valid) in counts.items():
        raw = 100 * above / valid if valid else None
        coverage = 100 * valid / n if n else None
        reason = (f'Holdings/constituent date unavailable, future, or older than {max_age} days' if not fresh else 'No eligible equity companies' if not n else f'Only {valid} valid companies; at least {minimum_sample} required' if valid < minimum_sample else f'Price coverage {valid}/{n} below {minimum_coverage:.0%}' if valid/n < minimum_coverage else None)
        output[str(period)] = metric(raw, reason, above_count=above, valid_count=valid, eligible_count=n, coverage_pct=coverage, session_date=session, as_of=source.get('as_of'), observation_count=valid)
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


def apply(snapshot, raw):
    inputs = raw.get('v5', {})
    all_charts = {**raw.get('charts', {}), **inputs.get('charts', {})}
    snapshot['last_source_retrieved_at'] = max((c.get('retrieved_at', '') for c in all_charts.values()), default=None)
    mapped = inputs.get('mapped_universes', {})
    date_ = snapshot.get('session_date')
    freshness_reference = date_ if snapshot.get('requested_asof') else snapshot['run_date']
    common = (all_charts, raw.get('session_calendar', []), date_, snapshot['settings'], freshness_reference)
    for market in snapshot['context']:
        symbol = market['ticker']
        source = inputs.get('index_universes', {}).get(symbol, {})
        breadth = participation(mapped.get(symbol, {}), source, *common)
        market['index_breadth'] = breadth
        market['index_constituent_asof'] = source.get('as_of')
        market['index_source'] = {k:v for k,v in source.items() if k != 'rows'}
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
        source = raw.get('holdings', {}).get(theme['anchor'], {})
        breadth = participation(mapped.get(theme['anchor'], {}), source, *common)
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
        theme['score_method'] = weights.get('score_method', 'price_relative_strength_v6_1')
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
    snapshot.setdefault('sources', {})['constituent_history_errors'] = inputs.get('chart_errors', {})
    snapshot['sources']['partial'] = snapshot['sources'].get('partial', False) or bool(inputs.get('chart_errors'))
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
    snapshot['schema_version'] = '6.1'
    snapshot['methodology_version'] = '6.1'
    snapshot['score_methodology'] = {
        'current_strength_weights': current_weights,
        'medium_strength_weights': medium_weights,
        'theme_score_weights': final_weights,
        'minimum_peers': peer_minimum,
        'state_threshold': threshold,
        'score_method': weights.get('score_method', 'price_relative_strength_v6_1'),
        'purpose': 'Consistent relative-strength ranking for manual review; not a prediction or entry signal',
    }
    return snapshot
