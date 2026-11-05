"""Effective-dated vNext research configuration; no legacy or provider behavior."""
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from pathlib import Path
import csv
import json


class ThemeStatus(StrEnum):
    ACTIVE = 'active'
    WATCH = 'watch-only'
    RETIRED = 'retired-merged'


class Role(StrEnum):
    CORE = 'Core'
    ENABLER = 'Enabler'
    RELATED = 'Related'


def iso_date(value):
    if not value:
        return None
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError('Dates must use YYYY-MM-DD')
    return value


def effective_session_after_close(approval_session, sessions):
    """User-approved convention: approval at t close first earns t+1's return."""
    if not iso_date(approval_session) or list(sessions) != sorted(set(sessions)):
        raise ValueError('A valid session and ordered unique trading calendar are required')
    try:
        index = sessions.index(approval_session)
    except ValueError:
        raise ValueError('Approval must name a configured US trading session') from None
    if index + 1 >= len(sessions):
        raise ValueError('Next trading session is outside the configured calendar')
    return sessions[index + 1]


@dataclass(frozen=True)
class Theme:
    theme_id: str
    name: str
    family: str
    status: ThemeStatus
    definition: str
    included_activities: str = ''
    excluded_activities: str = ''

    def __post_init__(self):
        if self.status not in tuple(ThemeStatus):
            raise ValueError('Invalid theme status')
        if not self.theme_id or any(c not in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in self.theme_id):
            raise ValueError('Invalid theme ID')
        if not self.name or not self.definition:
            raise ValueError('Theme charter requires a name and definition')
        if self.status == ThemeStatus.ACTIVE and not (self.included_activities and self.excluded_activities):
            raise ValueError('Active theme requires inclusion/exclusion rules')


@dataclass(frozen=True)
class Membership:
    ticker: str
    company: str
    theme_id: str
    role: Role
    effective_from: str | None
    effective_to: str | None
    review_snapshot: str
    evidence_status: str
    evidence_url: str = ''

    def __post_init__(self):
        if self.role not in tuple(Role):
            raise ValueError('Invalid membership role')
        start, end = iso_date(self.effective_from), iso_date(self.effective_to)
        if not iso_date(self.review_snapshot) or not self.evidence_status:
            raise ValueError('Membership requires review metadata')
        if end and (not start or end <= start):
            raise ValueError('Invalid membership interval: end must be after start')
        if not self.ticker or self.ticker != self.ticker.upper():
            raise ValueError('Ticker must be nonempty and uppercase')

    def active_on(self, session):
        if not iso_date(session):
            raise ValueError('Session required')
        return bool(self.effective_from and self.effective_from <= session
                    and (self.effective_to is None or session < self.effective_to))

    @property
    def calculation_eligible(self):
        return self.role in (Role.CORE, Role.ENABLER)


@dataclass(frozen=True)
class MarketRoster:
    benchmark: str
    effective_from: str
    tickers: tuple[str, ...]
    source: str
    effective_to: str | None = None

    def __post_init__(self):
        if self.benchmark not in ('SPY', 'QQQ'):
            raise ValueError('Only SPY and QQQ have constituent rosters')
        if not iso_date(self.effective_from) or not self.source or not self.tickers:
            raise ValueError('Roster requires date, source and constituents')
        if len(self.tickers) != len(set(self.tickers)) or any(not t for t in self.tickers):
            raise ValueError('Duplicate/empty roster symbol')
        if self.effective_to and iso_date(self.effective_to) <= self.effective_from:
            raise ValueError('Invalid roster interval')


@dataclass(frozen=True)
class Configuration:
    themes: tuple[Theme, ...]
    memberships: tuple[Membership, ...]
    universe: dict
    methodology: dict
    evidence_gate: dict

    def members_on(self, theme_id, session):
        theme = next(t for t in self.themes if t.theme_id == theme_id)
        if theme.status != ThemeStatus.ACTIVE:
            return ()
        return tuple(m for m in self.memberships if m.theme_id == theme_id
                     and m.calculation_eligible and m.active_on(session))

    def production_blockers(self):
        result = []
        pending = sum(m.evidence_status == 'primary_source_refresh_required' for m in self.memberships)
        if pending:
            result.append(f'{pending} primary-source reviews pending')
        if self.evidence_gate.get('findings'):
            result.append(f"{len(self.evidence_gate['findings'])} inherited-evidence findings pending")
        if self.evidence_gate.get('industry_rule_registry_status') != 'approved':
            result.append('Deterministic industry-rule registry is not documented/approved')
        if any(not m.effective_from for m in self.memberships):
            result.append('Launch effective dates pending')
        if not self.methodology.get('launch_rebalance_session'):
            result.append('Launch rebalance session not approved')
        if not self.methodology.get('production_enabled'):
            result.append('Production cutover not enabled')
        return result


def validate(themes, memberships, universe, *, launch=True):
    ids = {t.theme_id for t in themes}
    if len(ids) != len(themes):
        raise ValueError('Duplicate theme')
    instruments = {r['ticker'] for r in universe['instruments']}
    if len(instruments) != len(universe['instruments']):
        raise ValueError('Duplicate review-universe ticker')
    if not universe.get('quantitative_policy_validated') or not universe.get('source_sha256'):
        raise ValueError('Review-universe provenance/validation missing')
    for instrument in universe['instruments']:
        if instrument.get('exchange') not in ('NYSE', 'NASDAQ') or instrument.get('security_type') != 'common_stock':
            raise ValueError('Invalid reviewed instrument')
    intervals = {}
    for m in memberships:
        if m.theme_id not in ids or m.ticker not in instruments:
            raise ValueError('Unknown theme or ticker outside approved review universe: ' + m.ticker)
        key = (m.theme_id, m.ticker)
        for old in intervals.setdefault(key, []):
            if not old.effective_from or not m.effective_from or (
                (not old.effective_to or m.effective_from < old.effective_to)
                and (not m.effective_to or old.effective_from < m.effective_to)
            ):
                raise ValueError('Duplicate/overlapping membership relationship: ' + str(key))
        intervals[key].append(m)
    if launch:
        for theme in themes:
            count = len({m.ticker for m in memberships if m.theme_id == theme.theme_id
                         and m.calculation_eligible and not m.effective_to})
            if theme.status == ThemeStatus.ACTIVE and count < 5:
                raise ValueError('Active launch theme requires >=5 members: ' + theme.theme_id)


def load_configuration(root):
    folder = Path(root) / 'config/vnext'
    with (folder / 'themes.csv').open(encoding='utf-8', newline='') as handle:
        themes = tuple(Theme(**{k: r[k] for k in ('theme_id', 'name', 'family', 'definition',
                      'included_activities', 'excluded_activities')}, status=ThemeStatus(r['status']))
                       for r in csv.DictReader(handle))
    with (folder / 'memberships.csv').open(encoding='utf-8', newline='') as handle:
        memberships = tuple(Membership(**{k: r[k] for k in ('ticker', 'company', 'theme_id',
                            'review_snapshot', 'evidence_status', 'evidence_url')},
                            role=Role(r['role']), effective_from=r['effective_from'] or None,
                            effective_to=r['effective_to'] or None) for r in csv.DictReader(handle))
    universe = json.loads((folder / 'review_universe.json').read_text())
    validate(themes, memberships, universe)
    configuration = Configuration(themes, memberships, universe,
                         json.loads((folder / 'methodology.json').read_text()),
                         json.loads((folder / 'evidence_gate.json').read_text()))
    if configuration.evidence_gate.get('membership_review_package') or (folder / 'membership_master_review.json').exists():
        from .membership_evidence import validate_evidence
        validate_evidence(root, configuration)
    return configuration
