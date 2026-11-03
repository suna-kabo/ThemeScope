"""Export fixed collection identities from config, without any market inputs."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.tradingview import load_mapping, resolve


def write_lists(root=ROOT):
    active=json.loads((root/'config/active_anchors.json').read_text(encoding='utf-8'))['anchors']
    records=json.loads((root/'config/theme_watchlists.json').read_text(encoding='utf-8'))['watchlists']
    configured={r['theme_id']:r for r in records}
    if set(active)-set(configured):raise ValueError('Active exposure is missing a configured stock list')
    mapping=load_mapping(root)
    stocks=sorted({resolve(s['ticker'],mapping) for theme_id in active for s in configured[theme_id]['members']})
    etfs=sorted({resolve(t,mapping) for t in [*active.values(),'SPY','QQQ','IWM']})
    destination=root/'inputs/_lists';destination.mkdir(parents=True,exist_ok=True)
    for name, symbols in [('Daily_Data_Stocks.txt',stocks),('Daily_ETFs.txt',etfs)]:
        (destination/name).write_text(','.join(symbols)+'\n',encoding='utf-8')
    print(f'Collection lists: {destination} ({len(stocks)} stocks; {len(etfs)} ETFs/benchmarks).')
    return destination


if __name__=='__main__':
    try:write_lists()
    except (ValueError,KeyError,OSError) as error:
        print('COLLECTION LIST EXPORT FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
