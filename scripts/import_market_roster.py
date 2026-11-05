"""Import a periodic manual CSV (ticker column), never a daily data requirement."""
from pathlib import Path
import argparse,csv,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.themescope.domain import MarketRoster
from src.themescope.market.rosters import update

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark',choices=('SPY','QQQ'),required=True)
    p.add_argument('--effective-from',required=True);p.add_argument('--source',required=True)
    p.add_argument('--csv',type=Path,required=True);a=p.parse_args()
    with a.csv.open(encoding='utf-8-sig',newline='') as f:
        symbols=tuple(row['ticker'].strip() for row in csv.DictReader(f))
    if any(not s or s!=s.upper() or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-' for c in s) for s in symbols):raise ValueError('Invalid ticker')
    update(ROOT,MarketRoster(a.benchmark,a.effective_from,symbols,a.source))
    print('Manual roster recorded. Review and commit its versioned configuration separately.')
if __name__=='__main__':main()
