"""Forward membership review boundaries; all market inputs are manufactured."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import unittest

from src.themescope.domain import Configuration, Membership, Role, Theme, ThemeStatus
from src.themescope.research.membership_review import apply_review

ROOT = Path(__file__).resolve().parents[1]
SESSIONS = ('2026-11-12', '2026-11-13', '2026-11-16', '2026-11-17')


def configuration():
    return Configuration((Theme('test', 'Test', 'Test', ThemeStatus.ACTIVE, 'Test', 'Test', 'Other'),),
                         (Membership('OLD', 'Original', 'test', Role.CORE, '2026-11-09', None,
                                     '2026-11-05', 'reviewed', 'https://example.org/old'),),
                         {'instruments': [{'ticker': 'OLD', 'exchange': 'NYSE', 'security_type': 'common_stock'}],
                          'quantitative_policy_validated': True, 'source_sha256': 'a' * 64}, {}, {})


def review():
    excerpt = 'Manufactured water utility business description.'
    return {'schema_version': 1, 'status': 'reviewed', 'review_id': 'synthetic-review',
            'reviewed_on': '2026-11-14', 'effective_from': '2026-11-16',
            'authorization_reference': 'Explicit synthetic fixture authorization',
            'base_universe_source': {'sha256': 'b' * 64, 'security_type_basis': 'user_scanner_attestation',
                                     'quantitative_policy_validated': True},
            'additions': [{'ticker': 'NEW', 'company': 'New Company', 'theme_id': 'test', 'role': 'Core',
                           'instrument': {'ticker': 'NEW', 'exchange': 'NASDAQ', 'security_type': 'common_stock',
                                          'security_type_source': 'user_scanner_attestation'},
                           'evidence': {'source_url': 'https://example.org/issuer',
                                        'source_type': 'issuer_company_profile', 'reviewed_on': '2026-11-14',
                                        'supporting_excerpt': excerpt, 'support_summary': 'Manufactured Core business fact',
                                        'source_hash_basis': 'sha256_utf8_supporting_excerpt',
                                        'source_sha256': sha256(excerpt.encode()).hexdigest()}}]}


class MembershipReviewTests(unittest.TestCase):
    def test_weekend_review_is_forward_only_and_preserves_originals(self):
        original = configuration()
        amended = apply_review(original, review(), SESSIONS)
        self.assertEqual(original.memberships, amended.memberships[:1])
        self.assertEqual(len(original.memberships), 1)
        self.assertEqual(len(original.universe['instruments']), 1)
        self.assertEqual(len(amended.memberships), 2)
        self.assertEqual(len(amended.members_on('test', '2026-11-13')), 1)
        self.assertEqual(len(amended.members_on('test', '2026-11-16')), 2)
        self.assertEqual(amended.memberships[-1].review_snapshot, '2026-11-14')
        self.assertEqual(amended.universe['source_sha256'], original.universe['source_sha256'])
        self.assertEqual(amended.universe['research_v2_review']['effective_from'], '2026-11-16')

    def test_rejects_backdating_skipping_first_session_and_bad_calendar(self):
        for effective in ('2026-11-13', '2026-11-14', '2026-11-17'):
            data = review()
            data['effective_from'] = effective
            with self.subTest(effective=effective), self.assertRaises(ValueError):
                apply_review(configuration(), data, SESSIONS)
        for sessions in (SESSIONS[::-1], SESSIONS + (SESSIONS[-1],), SESSIONS[:2], (), ('',) + SESSIONS):
            with self.subTest(sessions=sessions), self.assertRaises(ValueError):
                apply_review(configuration(), review(), sessions)

    def test_rejects_bad_provenance_company_identity_and_roles(self):
        mutations = [lambda r: r.update(status='proposed'),
                     lambda r: r.update(schema_version=True),
                     lambda r: r.update(authorization_reference=''),
                     lambda r: r.update(authorization_reference=True),
                     lambda r: r.update(review_id=[]),
                     lambda r: r['base_universe_source'].update(sha256='bad'),
                     lambda r: r['base_universe_source'].update(quantitative_policy_validated=False),
                     lambda r: r['additions'][0].update(role='Related'),
                     lambda r: r['additions'][0].update(company=''),
                     lambda r: r['additions'][0].update(theme_id='missing'),
                     lambda r: r['additions'][0]['instrument'].update(ticker='OTHER'),
                     lambda r: r['additions'][0]['instrument'].update(exchange='OTC'),
                     lambda r: r['additions'][0]['instrument'].update(price=20),
                     lambda r: r['additions'][0]['evidence'].update(source_url='http://example.org'),
                     lambda r: r['additions'][0]['evidence'].update(source_url='https://u:p@example.org'),
                     lambda r: r['additions'][0]['evidence'].update(reviewed_on='2026-11-13'),
                     lambda r: r['additions'][0]['evidence'].update(source_sha256='0' * 64),
                     lambda r: r['additions'][0]['evidence'].update(support_summary=''),
                     lambda r: r.update(additions=[])]
        for index, mutate in enumerate(mutations):
            data = review()
            mutate(data)
            with self.subTest(index=index), self.assertRaises(ValueError):
                apply_review(configuration(), data, SESSIONS)

    def test_rejects_duplicate_overlap_and_rewritten_instrument(self):
        data = review()
        data['additions'].append(deepcopy(data['additions'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            apply_review(configuration(), data, SESSIONS)
        amended = apply_review(configuration(), review(), SESSIONS)
        with self.assertRaisesRegex(ValueError, 'overlapping'):
            apply_review(amended, review(), SESSIONS)
        config = configuration()
        config.universe['instruments'].append({'ticker': 'NEW', 'exchange': 'NYSE', 'security_type': 'common_stock'})
        with self.assertRaisesRegex(ValueError, 'rewrite'):
            apply_review(config, review(), SESSIONS)

    def test_existing_ended_interval_can_restart_without_rewriting_history(self):
        old = replace(configuration().memberships[0], ticker='NEW', effective_to='2026-11-13')
        config = replace(configuration(), memberships=(old,))
        amended = apply_review(config, review(), SESSIONS)
        self.assertEqual(amended.memberships[0], old)
        self.assertEqual(amended.memberships[-1].effective_from, '2026-11-16')

    def test_real_review_contains_seven_evidence_fingerprinted_additions(self):
        from src.themescope.domain import load_configuration
        from src.themescope.research.exports import reviewed_mapping
        data = json.loads((ROOT / 'config/vnext/research_v2_membership_review.json').read_text())
        self.assertEqual({r['ticker'] for r in data['additions']}, {'CCS', 'GRBK', 'NVR', 'MHO', 'AWR', 'CWT', 'MSEX'})
        for row in data['additions']:
            evidence = row['evidence']
            self.assertEqual(sha256(evidence['supporting_excerpt'].encode()).hexdigest(), evidence['source_sha256'])
            self.assertLessEqual(len(evidence['supporting_excerpt'].split()), 25)
        mapping=reviewed_mapping(load_configuration(ROOT),{})
        for row in data['additions']:
            self.assertEqual(mapping[row['ticker']]['source_sha256'],data['base_universe_source']['sha256'])


if __name__ == '__main__':
    unittest.main()
