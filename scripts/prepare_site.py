"""Prepare the explicit website allowlist. Does not commit, push or deploy."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.site_output import prepare_site


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--session');parser.add_argument('--recover',action='store_true');args=parser.parse_args()
    if args.recover:
        from src.themescope.local_publication import output_lock,recover
        with output_lock(ROOT/'site',timeout=5):restored=recover(ROOT/'site')
        print('Interrupted site preparation restored.' if restored else 'No interrupted site preparation needs recovery.')
        return 0
    session=args.session
    if not session:
        if not sys.stdin.isatty():parser.error('--session is required')
        session=input('US session of the saved dashboard to prepare (YYYY-MM-DD): ').strip()
    result=prepare_site(ROOT,ROOT/'output/manual_csv',ROOT/'site',session)
    print(f'Prepared site/ for saved US session {session}: {len(result["files"])} assets plus site_manifest.json.')
    print('Private inputs, audit files, local history and run bundles are excluded. Nothing was pushed or deployed.')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,KeyError,OSError) as error:
        print('SITE PREPARATION FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
