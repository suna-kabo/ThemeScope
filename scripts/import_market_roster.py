"""Import a periodic manual CSV (ticker column), never a daily data requirement."""
from pathlib import Path
import argparse,csv,re,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.themescope.domain import MarketRoster
from src.themescope.market.rosters import update

def read_symbols(path,column='ticker'):
    """Read exactly one chosen identifier column; all market-data columns are ignored."""
    with Path(path).open(encoding='utf-8-sig',newline='') as handle:
        reader=csv.DictReader(handle)
        if not reader.fieldnames or reader.fieldnames.count(column)!=1:
            raise ValueError('Exactly one '+column+' column is required')
        symbols=tuple(row[column] for row in reader)
    if not symbols or any(s is None or len(s)>16 or not re.fullmatch(r'[A-Z][A-Z0-9]*(?:[.-][A-Z0-9]+)*',s) for s in symbols):
        raise ValueError('Blank or invalid ticker')
    if len(set(symbols))!=len(symbols):raise ValueError('Duplicate ticker')
    return symbols


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--benchmark',choices=('SPY','QQQ'),required=True)
    p.add_argument('--effective-from',required=True);p.add_argument('--source',required=True)
    p.add_argument('--csv',type=Path,required=True)
    p.add_argument('--symbol-column',choices=('ticker','Symbol'),default='ticker')
    a=p.parse_args()
    symbols=read_symbols(a.csv,a.symbol_column)
    update(ROOT,MarketRoster(a.benchmark,a.effective_from,symbols,a.source))
    print('Manual roster recorded. Review and commit its versioned configuration separately.')
if __name__=='__main__':main()
