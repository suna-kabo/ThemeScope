"""Manufactured rows only; no private market data is needed by the suite."""
import csv
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest

from scripts.research_v2_universe_audit import REQUIRED, audit, markdown, read_base, review_completion
from src.themescope.domain import Configuration, Membership, Role, Theme, ThemeStatus


def theme(key, status=ThemeStatus.ACTIVE):
    return Theme(key, key.title(), 'Test', status, 'Test charter', 'Included', 'Excluded')


def member(ticker, key, role=Role.CORE, **changes):
    return Membership(ticker, ticker, key, role, '2026-11-09', None, '2026-11-05',
                      'test-reviewed', 'https://example.org/source', **changes)


def configuration():
    rows = (member('AAA', 'chips'), member('AAA', 'software', Role.ENABLER),
            member('REL', 'chips', Role.RELATED), member('WATCH', 'watch'),
            replace(member('OLD', 'chips'), effective_to='2026-11-10'),
            replace(member('FUTURE', 'chips'), effective_from='2026-11-16'))
    return Configuration((theme('chips'), theme('software'), theme('watch', ThemeStatus.WATCH)),
                         rows, {}, {}, {})


def base_row(ticker='AAA', industry='Semiconductors', **changes):
    return dict({'Symbol': ticker, 'Industry': industry, 'Sector': 'Test sector',
                 'Exchange': 'NASDAQ', 'Price': '6', 'Price - Currency': 'USD',
                 'Market capitalization': '1000000001',
                 'Market capitalization - Currency': 'USD'}, **changes)


class UniverseAuditTests(unittest.TestCase):
    def read(self, rows, fields=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'base.csv'
            with path.open('w', newline='', encoding='utf-8-sig') as handle:
                writer = csv.DictWriter(handle, fieldnames=fields or sorted(REQUIRED))
                writer.writeheader()
                writer.writerows(rows)
            return read_base(path)

    def test_base_scope_is_strict_and_independent_of_daily_liquidity(self):
        fields = sorted(REQUIRED) + ['Average volume, 10 days']
        row = base_row(**{'Average volume, 10 days': '0'})
        self.assertEqual(list(self.read([row], fields)), ['AAA'])
        for changes in ({'Price': '5'}, {'Price': 'NaN'}, {'Price': ''},
                        {'Market capitalization': '1000000000'},
                        {'Market capitalization': 'Infinity'}, {'Exchange': 'AMEX'},
                        {'Price - Currency': 'HKD'}, {'Symbol': ' aapl'}, {'Industry': ''}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.read([base_row(**changes)])

    def test_duplicates_missing_columns_and_empty_input_fail(self):
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.read([base_row(), base_row()])
        with self.assertRaisesRegex(ValueError, 'empty'):
            self.read([])
        with self.assertRaisesRegex(ValueError, 'required columns'):
            self.read([{'Symbol': 'AAA'}], ['Symbol'])

    def test_related_watch_and_effective_dates_are_distinct(self):
        base = {key: base_row(key) for key in ('AAA', 'REL', 'WATCH', 'OLD', 'FUTURE')}
        result = audit(base, configuration(), [], '2026-11-14')
        self.assertEqual(result['counts']['all_effective_theme_members'], 3)
        self.assertEqual(result['counts']['active_calculation_theme_members'], 1)
        self.assertEqual(result['counts']['effective_relationships'], 4)
        self.assertEqual(result['counts']['mapped_base'], 3)
        self.assertEqual(result['counts']['unmapped_base'], 2)
        self.assertEqual(result['roles'], {'Core': 2, 'Enabler': 1, 'Related': 1})
        self.assertEqual(result['multi_theme_stocks'], {'AAA': ['chips', 'software']})
        self.assertEqual(result['ended_relationships'][0]['ticker'], 'OLD')
        self.assertEqual(result['coverage_by_sector'][0]['base'], 5)
        self.assertEqual(result['coverage_by_sector'][0]['research_members'], 1)
        old = audit(base, configuration(), [], '2026-11-09')
        self.assertEqual(old['counts']['mapped_base'], 4)
        self.assertEqual(configuration().memberships[4].effective_to, '2026-11-10')

    def test_registry_matches_propose_without_extending_an_allowlist(self):
        rules = [dict(rule_id='chip-rule', theme_id='chips', role='Core',
                      industry_snapshot='Semiconductors', type='exact_industry',
                      decision='keep', rationale='Reviewed charter match'),
                 dict(rule_id='software-rule', theme_id='software', role='Enabler',
                      industry_snapshot='Packaged software', type='explicit_allowlist',
                      tickers=['ALLOWED'], decision='keep', rationale='Reviewed exception')]
        base = {key: base_row(key, industry) for key, industry in
                [('NEW', 'Semiconductors'), ('ALLOWED', 'Packaged software'),
                 ('NOTALLOWED', 'Packaged software'), ('BANK', 'Major banks'),
                 ('PRINT', 'Commercial printing/Forms')]}
        result = audit(base, configuration(), rules, '2026-11-14')
        proposals = result['membership_review']
        self.assertEqual({row['ticker'] for row in proposals}, {'NEW', 'ALLOWED'})
        self.assertTrue(all(row['applied'] is False and row['effective_from'] is None for row in proposals))
        self.assertEqual(result['unmapped_categories'], {'ambiguous_insufficient_evidence': 1,
                         'likely_existing_theme': 2, 'outside_current_coverage': 1,
                         'potential_missing_theme': 1})
        self.assertEqual(result['counts']['members_absent_base'], 3)
        serialized = json.dumps(result)
        for private_field in ('Price', 'Market capitalization', 'Average volume', '1000000001'):
            self.assertNotIn(private_field, serialized)
        self.assertIn('Unmapped', markdown(result))

    def test_mapped_stock_can_have_an_additional_legitimate_relationship(self):
        rule = dict(rule_id='second', theme_id='software', role='Core',
                    industry_snapshot='Semiconductors', type='exact_industry',
                    decision='keep', rationale='Reviewed hypothetical rule')
        config = replace(configuration(), memberships=(member('AAA', 'chips'),))
        result = audit({'AAA': base_row()}, config, [rule], '2026-11-14')
        self.assertEqual(result['unmapped_review'], [])
        self.assertEqual(result['membership_review'][0]['theme_id'], 'software')

    def test_changed_industry_flags_review_without_removing_the_membership(self):
        config = configuration()
        config = replace(config, memberships=(replace(config.memberships[0], evidence_status='industry_rule_accepted'),))
        result = audit({'AAA': base_row(industry='Different industry')}, config, [], '2026-11-14')
        self.assertEqual(result['counts']['active_calculation_theme_members'], 1)
        self.assertEqual(result['current_membership_industry_reviews'][0]['ticker'], 'AAA')
        self.assertEqual(result['current_membership_industry_reviews'][0]['decision'], 'retain_pending_company_evidence_review')

    def test_screening_and_cohort_triage_never_claim_company_review_for_every_candidate(self):
        result={'membership_review':[dict(ticker='NEW',theme_id='chips',rule_id='chip'),
                                      dict(ticker='OTHER',theme_id='chips',rule_id='chip')]}
        amendment=dict(reviewed_on='2026-11-14',effective_from='2026-11-16',
            additions=[dict(ticker='NEW',theme_id='chips',evidence=dict(source_url='https://example.org/issuer',support_summary='Reviewed fixture business'))])
        scope=review_completion(result,configuration(),amendment)
        self.assertEqual(scope['machine_candidates'],2)
        self.assertEqual(scope['not_company_evidence_reviewed'],1)
        self.assertEqual(len(scope['cohort_triage']),1)
        self.assertEqual(scope['company_decisions'][0]['decision'],'approved_forward_amendment')
        self.assertFalse(scope['exhaustive_company_review_complete'])
        self.assertTrue(scope['screening_never_applies_membership'])

    def test_permanent_membership_authorization_is_a_committed_document_reference(self):
        root=Path(__file__).resolve().parents[1]
        review=json.loads((root/'config/vnext/research_v2_membership_review.json').read_text(encoding='utf-8'))
        reference=review['authorization_reference'].split('#')[0]
        self.assertEqual(reference,'docs/operations/research-v2-membership-authorization.md')
        self.assertTrue((root/reference).is_file())
        self.assertNotIn('THEMESCOPE_CODEX_MASTER.md',review['authorization_reference'])


if __name__ == '__main__':
    unittest.main()
