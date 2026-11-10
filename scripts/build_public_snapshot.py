"""Freeze the committed loopback dashboard only; no database or calculation access."""
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from http.client import HTTPException
from pathlib import Path
import argparse
import json
import re
import shutil
import sys
import tempfile
from urllib.error import URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.build_inspection_bundle import safe_file
from scripts.static_pages import ASSETS, HEADERS, favicon
from src.themescope.local_refresh_lock import RefreshLock, RefreshBusy

API = 'http://127.0.0.1:8766/api/dashboard-data'
LIMIT = 25 * 1024 * 1024
FILES = {*ASSETS, 'preview.js', '_headers', 'favicon.ico'}
PUBLIC_HEADERS = HEADERS+'  Cache-Control: no-store\n'
IDENTIFIER = re.compile(r'[A-Z0-9_]+:[A-Z0-9_.-]+\Z')
SLUG = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*\Z')
SYMBOL = re.compile(r'[A-Z][A-Z0-9.-]*\Z')


class SnapshotError(ValueError):
    """Safe diagnostic; never include response bodies, headers or local paths."""


def iso_session(value):
    try:
        return isinstance(value, str) and date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def strict_json(text):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SnapshotError('Duplicate JSON keys are not accepted.')
            result[key] = value
        return result
    def nonfinite(_):
        raise SnapshotError('Non-finite JSON values are not accepted.')
    try:
        return json.loads(text, object_pairs_hook=pairs, parse_constant=nonfinite)
    except (ValueError, UnicodeError, RecursionError):
        raise SnapshotError('Invalid snapshot JSON.') from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise SnapshotError('Local snapshot API redirects are not accepted.')


def fetch_snapshot():
    # Explicit loopback only. Ignore HTTP proxies and never follow a redirect.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    try:
        request = Request(API, headers={'Accept': 'application/json'})
        with opener.open(request, timeout=15) as response:
            if response.status != 200 or response.headers.get_content_type() != 'application/json':
                raise SnapshotError('Local dashboard API did not return a JSON snapshot.')
            data = response.read(LIMIT + 1)
        if not data or len(data) > LIMIT:
            raise SnapshotError('Local snapshot is empty or exceeds the size limit.')
        return strict_json(data.decode('utf-8'))
    except (URLError, OSError, UnicodeError, HTTPException):
        raise SnapshotError('Cannot read local ThemeScope. Start ThemeScope and complete a real refresh first.') from None


# Explicit presentation contract: unknown fields are discarded at every level.
# This module validates/copies supplied metrics; it never computes financial values.
def text(value):
    if not isinstance(value, str):
        raise SnapshotError('Snapshot text field has an invalid type.')
    return value


def boolean(value):
    if type(value) is not bool:
        raise SnapshotError('Snapshot boolean field has an invalid type.')
    return value


def numeric(value):
    if value is None:
        return None
    try:
        if isinstance(value, bool) or not isinstance(value, (str, int, float)) or not Decimal(str(value)).is_finite():
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        raise SnapshotError('Snapshot metric is invalid.') from None
    return value


def fields(value, specification):
    if not isinstance(value, dict):
        raise SnapshotError('Snapshot object is invalid.')
    result = {}
    for key, rule in specification.items():
        optional = key.endswith('?'); key = key.removesuffix('?')
        if key not in value:
            if optional:
                continue
            raise SnapshotError('Snapshot is missing a required presentation field.')
        result[key] = rule(value[key])
    return result


def sequence(rule):
    def copy(value):
        if not isinstance(value, list):
            raise SnapshotError('Snapshot list is invalid.')
        return [rule(item) for item in value]
    return copy


def object_rule(specification):
    return lambda value: fields(value, specification)


def optional(rule):
    return lambda value: None if value is None else rule(value)


METRIC = object_rule(dict(value=numeric, valid=numeric, configured=numeric, coverage=numeric))
INDEX = object_rule(dict(level=numeric, ema21=numeric, ema50=numeric, trend=text, bootstrap=boolean, **{'session?':text}))
TRANSITION = object_rule(dict(newly_bullish=optional(boolean), newly_bearish=optional(boolean), priority_change=optional(text)))
THEME = object_rule(dict(theme_id=text, name=text, family=text, status=text, score=numeric,
                        returns=optional(sequence(METRIC)), index=INDEX, priority=text,
                        transition=TRANSITION, breadth=sequence(METRIC)))
RELATIONSHIP = object_rule(dict(ticker=text, theme_id=text, role=text, qualifies=boolean,
    assigned_section=optional(text), also_qualifies_in=sequence(text),
    relative=object_rule(dict(w=numeric, er1=numeric, er3=numeric, peer1=METRIC, peer3=METRIC)),
    eligibility=object_rule(dict(available=boolean, eligible=boolean, close=numeric,
                                average_volume=numeric, turnover=numeric, reasons=sequence(text)))))
BREADTH = object_rule(dict(above_ema21=numeric, above_ema50=numeric, valid=numeric,
                          configured=numeric, coverage=numeric, state=text))
CONTEXT = dict(close=numeric, ema21=numeric, ema50=numeric, price_state=text)
CONTEXT_BREADTH = dict(CONTEXT, breadth=BREADTH, roster_warnings=sequence(text),
                      roster_source=optional(text), roster_effective_from=optional(text))
MARKET = object_rule(dict(context=object_rule(dict(SPY=object_rule(CONTEXT_BREADTH),
    QQQ=object_rule(CONTEXT_BREADTH), IWM=object_rule(CONTEXT))), breadth_consensus=text,
    decision=object_rule(dict(direction=text, reason=text, rule_id=text, breadth_qualifier=optional(text)))))
LAYER = object_rule({key+'?':rule for key,rule in dict(state=text, research_session=text,
    launch_rebalance_session=optional(text), first_earned_session=optional(text), official_live_history=boolean).items()})



def keyed(rule, pattern):
    def copy(value):
        if not isinstance(value, dict) or any(not isinstance(key, str) or not pattern.fullmatch(key) for key in value):
            raise SnapshotError('Research map identifiers are invalid.')
        return {key: rule(row) for key, row in value.items()}
    return copy


EXTENSION_INDEX = object_rule(dict(atr20=numeric, distance=numeric, state=text, side=optional(text), magnitude=optional(text)))
EMA_CHANGE = object_rule(dict(relation=text, previous_relation=text, changed=optional(boolean), message=optional(text), previous_session=optional(text)))
RANK_ROW = object_rule(dict(rank=numeric, previous_rank=numeric, change=numeric, reason=text, previous_session=optional(text)))
POINTER = object_rule(dict(ticker=text, theme_id=text))
BUCKET = object_rule(dict(label=text, rows=sequence(POINTER), stocks=sequence(POINTER), stock_count=numeric, relationship_count=numeric))
RESEARCH = object_rule(dict(schema=text, policy_version=text, policy_hash=text,
    extension=object_rule(dict(state=text, indices=object_rule(dict(SPY=EXTENSION_INDEX, QQQ=EXTENSION_INDEX)), history_start=optional(text), atr_period=numeric)),
    focus=object_rule(dict(label=text, preferred_mode=text)),
    ema_transitions=object_rule({ticker:object_rule(dict(ema21=EMA_CHANGE, ema50=EMA_CHANGE)) for ticker in ('SPY','QQQ','IWM')}),
    ranks=object_rule(dict(method=text, ranked_total=numeric, active_universe=sequence(text), themes=keyed(RANK_ROW,SLUG))),
    countertrend=object_rule(dict(available=boolean, side=optional(text), buckets=object_rule(dict(resilient=BUCKET,snapback=BUCKET)), stock_count=numeric, relationship_count=numeric, ordering_note=text)),
    companies=keyed(text,SYMBOL)))

def project_snapshot(source, expected):
    if not iso_session(expected):
        raise SnapshotError('Use an explicit ISO session: --session YYYY-MM-DD.')
    if not isinstance(source, dict) or source.get('schema') != 'themescope-vnext-snapshot-1':
        raise SnapshotError('A committed vNext dashboard snapshot is required.')
    if source.get('synthetic_fixture') is not False:
        raise SnapshotError('Synthetic or unmarked snapshots cannot be published as real.')
    session = source.get('session')
    if not iso_session(session):
        raise SnapshotError('Snapshot session is invalid.')
    print('Detected completed US session: ' + session)
    if session != expected:
        raise SnapshotError('Session mismatch. Nothing was built or deployed.')
    completeness = source.get('completeness', {})
    if not isinstance(completeness, dict) or not isinstance(source.get('provider_health'), dict):
        raise SnapshotError('Successful publication metadata is malformed.')
    required = completeness.get('required')
    if (completeness.get('complete') is not True or type(required) is not int or required <= 0
            or completeness.get('valid_target') != required or type(completeness.get('valid_target')) is not int
            or source.get('provider_health', {}).get('status') != 'Healthy'):
        raise SnapshotError('A complete successful real publication is required.')
    refreshed = source.get('refreshed_at')
    try:
        stamp = datetime.fromisoformat(refreshed.replace('Z', '+00:00'))
        if stamp.tzinfo is None or stamp.date() < date.fromisoformat(session):
            raise ValueError
    except (AttributeError, TypeError, ValueError):
        raise SnapshotError('Successful publication timestamp is missing or invalid.') from None
    result = fields(source, dict(schema=text, methodology=text, session=text, synthetic_fixture=boolean,
        market_direction=text, market=MARKET, themes=sequence(THEME), relationships=sequence(RELATIONSHIP),
        theme_layer=LAYER, today_plan=text, refreshed_at=text, production_blockers=sequence(text),
        completeness=object_rule(dict(complete=boolean, required=numeric, valid_target=numeric,
            **{'trading_target?':numeric,'terminal_target?':numeric,'historical_inputs?':numeric})),
        provider_health=object_rule(dict(status=text)), **{'research?':RESEARCH}))
    if not re.fullmatch(r'themescope-vnext-\d+', result['methodology']) or not result['themes']:
        raise SnapshotError('A supported vNext methodology and theme list are required.')
    themes = [t['theme_id'] for t in result['themes']]
    if len(set(themes)) != len(themes) or any(not SLUG.fullmatch(t) for t in themes):
        raise SnapshotError('Invalid or duplicate theme identifiers.')
    if 'research' in result and result['research']['schema'] != 'themescope-research-1':
        raise SnapshotError('Unsupported research context contract.')
    pairs = [(r['ticker'], r['theme_id']) for r in result['relationships']]
    if len(set(pairs)) != len(pairs) or any(not SYMBOL.fullmatch(s) or t not in themes for s,t in pairs):
        raise SnapshotError('Invalid or duplicate theme relationships.')
    research = result.get('research')
    if research and (any(t not in themes for t in research['ranks']['themes']) or any((r['ticker'],r['theme_id']) not in pairs for bucket in research['countertrend']['buckets'].values() for r in [*bucket['rows'],*bucket['stocks']])):
        raise SnapshotError('Research references an unknown theme relationship.')
    exported = source.get('exports')
    if not isinstance(exported, dict) or not isinstance(exported.get('individual'), dict) or not isinstance(exported.get('assignments'), dict):
        raise SnapshotError('Published exports are missing or malformed.')
    def txt(value, combined=False):
        text(value)
        for line in value.splitlines():
            if not (IDENTIFIER.fullmatch(line) or combined and line.startswith('###') and line[3:] in themes):
                raise SnapshotError('Export contains more than public identifiers/grouping.')
        return value
    if any(t not in themes for t in exported['individual']):
        raise SnapshotError('Export theme is unknown.')
    assignments = {}
    symbols = {r['ticker'] for r in result['relationships']}
    for symbol, assignment in exported['assignments'].items():
        row = fields(assignment, dict(assigned_section=text, also_qualifies_in=sequence(text)))
        if symbol not in symbols or any(t not in themes for t in [row['assigned_section'],*row['also_qualifies_in']]):
            raise SnapshotError('Export assignment is invalid.')
        assignments[symbol] = row
    result['exports'] = dict(combined=txt(exported.get('combined'), True),
        individual={t:txt(value) for t,value in exported['individual'].items()}, assignments=assignments)
    earnings = source.get('earnings', {})
    if not isinstance(earnings, dict):
        raise SnapshotError('Earnings presentation is malformed.')
    result['earnings'] = {}
    for symbol, entry in earnings.items():
        if symbol not in symbols:
            raise SnapshotError('Earnings symbol is unknown.')
        row = fields(entry, dict(status=text, dates=sequence(text)))
        if any(not iso_session(day) for day in row['dates']):
            raise SnapshotError('Earnings date is invalid.')
        result['earnings'][symbol] = row
    return result


def scan_text(path):
    try:
        if path.name == '_headers':
            # The inspection scanner accepts suffixes; Pages requires this exact
            # extensionless name. Verify the constant before the extra scan.
            data = path.read_text(encoding='utf-8')
            if data != PUBLIC_HEADERS:
                raise ValueError
        else:
            data = safe_file(path)
    except ValueError:
        raise SnapshotError('Public output failed secret/path/raw-payload safety validation.') from None
    patterns = (r'(?i)APCA_API_KEY_ID|APCA_API_SECRET_KEY|ALPHAVANTAGE_API_KEY|CLOUDFLARE_API_TOKEN',
                r'(?i)\bbearer\s+\S+', r'(?i)\.env\b', r'(?i)https?://(?:localhost|127\.0\.0\.1|\[::1\])',
                r'(?i)\bruntime[\\/]|[\w.-]+\.(?:sqlite3?|db)\b',
                r'(?i)\b[A-Z]:[\\/]|\\\\[A-Za-z0-9.-]+\\',
                r'(?i)"(?:bars|observations|daily_bars|quoteResponse)"\s*:',
                r'(?i)\b(?:api[_-]?token|token|password|authorization)["\x27]?\s*[:=]\s*["\x27]?[^\s,"\x27}]{8,}')
    if any(re.search(pattern, data.replace(r'\"','"')) for pattern in patterns):
        raise SnapshotError('Public output failed secret/path/runtime safety validation.')
    return data


def validate_output(output):
    if output.is_symlink() or {p.name for p in output.iterdir()} != FILES:
        raise SnapshotError('Public output must contain only the static file allowlist.')
    for path in output.iterdir():
        if not path.is_file() or path.is_symlink():
            raise SnapshotError('Public output must contain regular files only.')
        if path.name != 'favicon.ico':
            scan_text(path)
    if (output/'favicon.ico').read_bytes() != favicon():
        raise SnapshotError('Unexpected favicon payload.')


@contextmanager
def publication_lock(root=ROOT):
    root = Path(root).resolve()
    if (root/'dist').is_symlink():
        raise SnapshotError('Public output parent must not be a symlink.')
    lock = root/'dist/.public-snapshot.lock'
    if lock.is_symlink():
        raise SnapshotError('Public lock must not be a symlink.')
    try:
        with RefreshLock(lock):
            yield
    except RefreshBusy:
        raise SnapshotError('Another public snapshot build/publish is running.') from None


def build_locked(expected, root=ROOT):
    """Caller holds publication_lock until any deployment finishes."""
    if not iso_session(expected):
        raise SnapshotError('Use an explicit ISO session: --session YYYY-MM-DD.')
    root = Path(root).resolve()
    output = root/'dist/cloudflare-public'
    if output.is_symlink():
        raise SnapshotError('Public output must not be a symlink.')
    snapshot = project_snapshot(fetch_snapshot(), expected)
    payload = json.dumps({'mode':'public_snapshot','snapshot':snapshot}, sort_keys=True, separators=(',',':'), allow_nan=False)
    payload = payload.replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    # Stage and scan everything before replacing the previous prepared directory.
    with tempfile.TemporaryDirectory(dir=root/'dist', prefix='.public-build-') as temporary:
        stage = Path(temporary)/'site';stage.mkdir()
        for name in ASSETS:
            shutil.copyfile(root/'static/vnext'/name, stage/name)
        (stage/'preview.js').write_text('window.THEMESCOPE_STATIC_SOURCE = '+payload+';\n', encoding='utf-8')
        (stage/'_headers').write_text(PUBLIC_HEADERS, encoding='utf-8')
        (stage/'favicon.ico').write_bytes(favicon())
        validate_output(stage)
        if output.exists():
            shutil.rmtree(output)
        stage.rename(output)
    print('Prepared read-only public snapshot: ' + expected + ' (dist/cloudflare-public).')
    return output


def build(expected, root=ROOT):
    with publication_lock(root):
        return build_locked(expected, root)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True)
    args = parser.parse_args()
    try:
        build(args.session)
    except SnapshotError as error:
        print('Public build aborted: '+str(error), file=sys.stderr)
        return 1
    except OSError:
        # Do not echo arbitrary filesystem paths or service/payload exception text.
        print('Public build aborted. Check the explicit session, committed real snapshot and output safety.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
