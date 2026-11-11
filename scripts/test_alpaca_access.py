"""Explicit local-only SIP PoC. Mocked in CI; never emits HTTP exception details."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.providers.base import Schedule,ProviderError
from src.themescope.providers.alpaca import AlpacaMarketDataProvider


def main(argv=None,*,factory=AlpacaMarketDataProvider):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',help='Optional completed US session YYYY-MM-DD')
    args=parser.parse_args(argv)
    provider=None
    try:
        records=json.loads((ROOT/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
        schedule=Schedule(records)
        target=args.session or schedule.latest();schedule.require(target)
        # Limit=1 deliberately forces real pagination for a three-symbol request.
        provider=factory(os.environ.get('APCA_API_KEY_ID'),os.environ.get('APCA_API_SECRET_KEY'),schedule,limit=1)
        batch=provider.get_daily_bars(('AAPL','MSFT','JPM'),target,target)
        by_symbol={b.ticker:b for b in batch.bars if b.session==target}
        if set(by_symbol)!=set(('AAPL','MSFT','JPM')) or any(b.volume<=0 for b in by_symbol.values()):
            raise ProviderError('required_target_session_missing_or_zero_volume')
        if batch.pages<=2:raise ProviderError('pagination_not_proven')
        print(json.dumps({'status':'passed','session':target,'symbols':3,'positive_raw_volume':True,
                          'pages':batch.pages,'feed':'sip','timeframe':'1Day','adjustment':'split,spin-off',
                          'raw_liquidity_request':True,'delay_minutes':20,'iex_fallback':False}))
        return 0
    except ProviderError as error:
        print(json.dumps({'status':'failed','reason':str(error)}));return 1
    except Exception:
        print(json.dumps({'status':'failed','reason':'local_validation_error'}));return 1

if __name__=='__main__':raise SystemExit(main())
