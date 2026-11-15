"""Reviewed forward additions; the original launch evidence package stays immutable."""
from dataclasses import replace
from hashlib import sha256
import json
import re
from urllib.parse import urlparse

from ..domain import Membership, Role, iso_date, validate


def apply_review(configuration, review, sessions):
    """Apply inspected company relationships, never industry-scanner suggestions."""
    try:
        if (type(review['schema_version']) is not int or review['schema_version'] != 1
                or review['status'] != 'reviewed'
                or not isinstance(review['review_id'], str) or not review['review_id'].strip()
                or not isinstance(review['authorization_reference'], str)
                or not review['authorization_reference'].strip()):
            raise ValueError('Reviewed membership amendment required')
        reviewed_on = iso_date(review['reviewed_on'])
        sessions = tuple(sessions)
        if not reviewed_on or sessions != tuple(sorted(set(sessions))) or not sessions:
            raise ValueError('Ordered unique session calendar and review date required')
        if any(not iso_date(day) for day in sessions):
            raise ValueError('Nonempty ISO calendar sessions required')
        # Weekend reviews first earn the next trading session, never a past close.
        future = [day for day in sessions if day > reviewed_on]
        if not future or review['effective_from'] != future[0]:
            raise ValueError('Membership must begin on the first session after review')
        source = review['base_universe_source']
        if (not re.fullmatch(r'[0-9a-f]{64}', source['sha256'])
                or source['security_type_basis'] != 'user_scanner_attestation'
                or source['quantitative_policy_validated'] is not True):
            raise ValueError('Validated manual universe provenance required')
        themes = {theme.theme_id: theme for theme in configuration.themes}
        additions = review['additions']
        if not isinstance(additions, list) or not additions:
            raise ValueError('Nonempty reviewed additions required')
        instruments = {row['ticker']: dict(row) for row in configuration.universe['instruments']}
        members = list(configuration.memberships)
        seen = set()
        for row in additions:
            evidence = row['evidence']
            excerpt = evidence['supporting_excerpt']
            url = urlparse(evidence['source_url'])
            if (url.scheme != 'https' or not url.hostname or url.username or url.password
                    or evidence['reviewed_on'] != reviewed_on
                    or evidence['source_type'] != 'issuer_company_profile'
                    or evidence['source_hash_basis'] != 'sha256_utf8_supporting_excerpt'
                    or not excerpt.strip() or not evidence['support_summary'].strip()
                    or sha256(excerpt.encode('utf-8')).hexdigest() != evidence['source_sha256']):
                raise ValueError('Inspected HTTPS issuer evidence and matching excerpt hash required')
            theme_id = row['theme_id']
            if theme_id not in themes or themes[theme_id].status != 'active':
                raise ValueError('Reviewed addition must name an existing Active charter')
            if row['role'] not in ('Core', 'Enabler'):
                raise ValueError('Reviewed calculation role required')
            ticker = row['ticker']
            if (not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,19}', ticker)
                    or not isinstance(row['company'], str) or not row['company'].strip()):
                raise ValueError('Invalid reviewed ticker')
            key = ticker, theme_id
            if key in seen:
                raise ValueError('Duplicate reviewed addition')
            seen.add(key)
            instrument = row['instrument']
            if (set(instrument) != {'ticker', 'exchange', 'security_type', 'security_type_source'}
                    or instrument['ticker'] != ticker or instrument['exchange'] not in ('NYSE', 'NASDAQ')
                    or instrument['security_type'] != 'common_stock'
                    or instrument['security_type_source'] != 'user_scanner_attestation'):
                raise ValueError('Sanitized reviewed instrument identity required')
            if ticker in instruments and any(instruments[ticker][field] != instrument[field]
                                             for field in ('ticker', 'exchange', 'security_type')):
                raise ValueError('Cannot rewrite an existing reviewed instrument identity')
            instruments.setdefault(ticker, dict(instrument, source_sha256=source['sha256']))
            members.append(Membership(ticker, row['company'], theme_id, Role(row['role']),
                                      review['effective_from'], None, reviewed_on,
                                      'primary_source_verified_research_v2', evidence['source_url']))
        universe = dict(configuration.universe,
                        instruments=[instruments[key] for key in sorted(instruments)])
        universe['research_v2_review'] = {
            'review_id': review['review_id'], 'reviewed_on': reviewed_on,
            'effective_from': review['effective_from'], 'base_source_sha256': source['sha256'],
            'review_sha256': sha256(json.dumps(review, sort_keys=True, separators=(',', ':')).encode()).hexdigest()}
        validate(configuration.themes, tuple(members), universe, launch=False)
        return replace(configuration, memberships=tuple(members), universe=universe)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError('Incomplete reviewed membership amendment') from error
