"""Local SIP roster compatibility diagnostic; never edits membership or cache."""
from pathlib import Path
import argparse,json,os,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.themescope.market.rosters import load,effective
from src.themescope.providers.base import Schedule,ProviderError
from src.themescope.providers.alpaca import AlpacaMarketDataProvider


def main(argv=None,*,root=ROOT,factory=AlpacaMarketDataProvider):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--roster-date',required=True)
    parser.add_argument('--session',help='Optional safely completed US session; defaults to latest')
    args=parser.parse_args(argv)
    try:
        rosters=load(root);selected={b:effective(rosters,b,args.roster_date) for b in ('SPY','QQQ')}
        if any(r is None for r in selected.values()):raise ProviderError('effective_roster_missing')
        records=json.loads((Path(root)/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
        schedule=Schedule(records);target=args.session or schedule.latest();schedule.require(target)
        provider=factory(os.environ.get('APCA_API_KEY_ID'),os.environ.get('APCA_API_SECRET_KEY'),schedule)
        symbols=sorted({s for r in selected.values() for s in r.tickers})
        usable=set();pages=0
        for offset in range(0,len(symbols),100):
            requested=symbols[offset:offset+100]
            try:batch=provider.get_daily_bars(requested,target,target)
            except ProviderError as error:
                print(json.dumps({'status':'failed','reason':str(error),'requested_symbols':requested,'session':target}))
                return 1
            pages+=batch.pages
            usable.update(b.ticker for b in batch.bars if b.session==target and b.volume>0 and b.completed and b.regular_session)
        result={benchmark:{'configured':len(roster.tickers),'missing_or_unusable':sorted(set(roster.tickers)-usable)}
                for benchmark,roster in selected.items()}
        success=all(not r['missing_or_unusable'] for r in result.values())
        print(json.dumps({'status':'passed' if success else 'failed','roster_date':args.roster_date,
                          'session':target,'feed':'sip','timeframe':'1Day','adjustment':'split,spin-off',
                          'raw_liquidity_request':True,'pages':pages,'benchmarks':result}))
        return 0 if success else 1
    except ProviderError as error:
        print(json.dumps({'status':'failed','reason':str(error)}));return 1
    except Exception:
        print(json.dumps({'status':'failed','reason':'local_validation_error'}));return 1

if __name__=='__main__':raise SystemExit(main())
