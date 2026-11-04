import csv
from pathlib import Path
import tempfile
import unittest
from src.themescope.review_universe import validate_review_csv, RULES, CURRENCIES, proposed_diff
from src.themescope.domain import load_configuration


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'review.csv'
        self.row = {'Symbol': 'SYNTH', 'Description': 'Synthetic', 'Exchange': 'NASDAQ',
                    'Price': '5', 'Market capitalization': '2000000000',
                    'Average volume, 10 days': '500001',
                    'Price × volume (turnover), 1 day': '10000000',
                    **{k: 'USD' for k in CURRENCIES}}

    def write(self, duplicate=False):
        with self.path.open('w', encoding='utf-8', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=list(self.row))
            writer.writeheader()
            writer.writerow(self.row)
            if duplicate:
                writer.writerow(self.row)

    def test_boundaries_and_explicit_security_attestation(self):
        self.write()
        with self.assertRaisesRegex(ValueError, 'attestation'):
            validate_review_csv(self.path)
        self.assertEqual(len(validate_review_csv(self.path, common_stock_attested=True)['instruments']), 1)
        self.row['Average volume, 10 days'] = '500000'
        self.write()
        with self.assertRaisesRegex(ValueError, 'fails review'):
            validate_review_csv(self.path, common_stock_attested=True)

    def test_invalid_filter_and_duplicate_fail(self):
        for field, value in [('Exchange', 'NYSE ARCA'), ('Price', 'NaN'),
                             ('Market capitalization', '1999999999'),
                             ('Price × volume (turnover), 1 day', '9999999'),
                             ('Security type', 'ETF'), ('Price - Currency', 'EUR')]:
            with self.subTest(field=field):
                before = self.row.copy()
                self.row[field] = value
                self.write()
                with self.assertRaises(ValueError):
                    validate_review_csv(self.path, common_stock_attested=True)
                self.row = before
        self.write(duplicate=True)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            validate_review_csv(self.path, common_stock_attested=True)

    def test_review_generates_proposal_without_activation(self):
        self.write()
        config = load_configuration(Path(__file__).resolve().parents[1])
        before = config.memberships
        diff = proposed_diff(config, validate_review_csv(self.path, common_stock_attested=True))
        self.assertIn('SYNTH', diff['newly_eligible'])
        self.assertEqual(len(diff['members_absent_from_review']), 671)
        self.assertFalse(diff['membership_modified'])
        self.assertEqual(config.memberships, before)
