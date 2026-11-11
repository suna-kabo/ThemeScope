"""Audit provisional config and optionally compare its exact private source CSV."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.domain import load_configuration
from src.themescope.review_universe import validate_review_csv, proposed_diff


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review-csv', type=Path)
    parser.add_argument('--common-stock-attested', action='store_true')
    args = parser.parse_args()
    config = load_configuration(ROOT)
    report = {'provisional_configuration_valid': True, 'production_blockers': config.production_blockers()}
    if args.review_csv:
        reviewed = validate_review_csv(args.review_csv, common_stock_attested=args.common_stock_attested)
        matches = (reviewed['source_sha256'] == config.universe['source_sha256']
                   and reviewed['instruments'] == config.universe['instruments'])
        report.update(reviewed_tickers=len(reviewed['instruments']),
                      exact_launch_source_match=matches, proposed_diff=proposed_diff(config, reviewed))
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
