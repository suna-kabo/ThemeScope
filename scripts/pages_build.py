"""Cloudflare Pages build: validate site/ only; never refresh or collect data."""
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.site_output import placeholder_site,validate_site


def main():
    site=ROOT/'site'
    if not site.exists():
        placeholder_site(site)
        print('No site snapshot committed. Prepared an empty placeholder; no market data was selected from repository archives.')
    result=validate_site(site)
    print(f'Pages output: site/ only; kind={result["kind"]}; session={result["session_date"]}; {len(result["files"])} assets.')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,KeyError,OSError) as error:
        print('PAGES BUILD FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
