"""Validate an explicit scanner review export. This never writes membership."""
import csv
import hashlib
from decimal import Decimal, InvalidOperation
from pathlib import Path

RULES = {'Price': (Decimal('5'), False),
         'Market capitalization': (Decimal('2000000000'), False),
         'Average volume, 10 days': (Decimal('500000'), True),
         'Price × volume (turnover), 1 day': (Decimal('10000000'), False)}
CURRENCIES = ('Price - Currency', 'Market capitalization - Currency',
              'Price × volume (turnover), 1 day - Currency')


def validate_review_csv(path, *, common_stock_attested=False):
    path = Path(path)
    instruments = []
    seen = set()
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        required = {'Symbol', 'Description', 'Exchange', *RULES, *CURRENCIES}
        if not reader.fieldnames or not required <= set(reader.fieldnames):
            raise ValueError('Missing review fields: ' + ', '.join(sorted(required - set(reader.fieldnames or []))))
        has_type = 'Security type' in reader.fieldnames
        if not has_type and not common_stock_attested:
            raise ValueError('Security type absent: explicit Common Stock scanner attestation required')
        for line, row in enumerate(reader, 2):
            symbol = (row['Symbol'] or '').strip()
            if not symbol or symbol != symbol.upper() or symbol in seen:
                raise ValueError(f'Line {line}: duplicate/invalid ticker {symbol}')
            seen.add(symbol)
            if row['Exchange'] not in ('NYSE', 'NASDAQ'):
                raise ValueError(f'{symbol}: exchange must be NYSE or NASDAQ')
            if has_type and row['Security type'].strip().casefold() != 'common stock':
                raise ValueError(f'{symbol}: security type must be Common Stock')
            if any(row[key] != 'USD' for key in CURRENCIES):
                raise ValueError(f'{symbol}: review monetary fields must be USD')
            for key, (floor, strict) in RULES.items():
                try:
                    value = Decimal(row[key])
                except (InvalidOperation, TypeError):
                    raise ValueError(f'{symbol}: invalid {key}') from None
                if not value.is_finite() or (value <= floor if strict else value < floor):
                    raise ValueError(f'{symbol}: {key} fails review policy')
            instruments.append({'ticker': symbol, 'exchange': row['Exchange'],
                                'security_type': 'common_stock',
                                'security_type_source': 'csv' if has_type else 'user_scanner_attestation'})
    if not instruments:
        raise ValueError('Empty review universe')
    return {'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'instruments': sorted(instruments, key=lambda r: r['ticker']),
            'quantitative_policy_validated': True}


def proposed_diff(configuration, reviewed):
    """Proposal only. Absent members remain in approved configuration/history."""
    candidates = {r['ticker'] for r in reviewed['instruments']}
    existing = {m.ticker for m in configuration.memberships if not m.effective_to}
    original = {r['ticker'] for r in configuration.universe['instruments']}
    return {'newly_eligible': sorted(candidates - original),
            'members_absent_from_review': sorted(existing - candidates),
            'unassigned_review_candidates': sorted(candidates - existing),
            'membership_modified': False, 'approval_required_to_apply': True,
            'classification_changes': 'Requires evidence review; scanner does not classify themes.'}
