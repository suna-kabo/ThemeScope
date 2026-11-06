"""Real approved configuration with wholly synthetic bars for pre-launch tests."""
from dataclasses import replace
from datetime import datetime
from decimal import Decimal as D
from pathlib import Path
import json
from src.themescope.domain import load_configuration,MarketRoster
from src.themescope.market.rosters import load as load_rosters
from src.themescope.local.service import RefreshService
from src.themescope.providers.base import FixtureProvider,Schedule
from src.themescope.themes.calculations import Bar

ROOT=Path(__file__).resolve().parents[1]
RECORDS=json.loads((ROOT/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']
DAYS=tuple(r['session'] for r in RECORDS)

class PrelaunchFixture:
    def __init__(self,root,*,full=False,missing_rosters=()):
        self.root=Path(root);self.target='2026-11-05';self.providers=[]
        self.config=load_configuration(ROOT)
        if not full:
            ids={'airlines','semiconductors'}
            self.config=replace(self.config,themes=tuple(t for t in self.config.themes if t.theme_id in ids),
                                memberships=tuple(m for m in self.config.memberships if m.theme_id in ids))
        rosters=load_rosters(ROOT) if full else (
            MarketRoster('SPY','2026-11-05',('SPY',),'Synthetic SPY breadth fixture'),
            MarketRoster('QQQ','2026-11-05',('QQQ',),'Synthetic QQQ breadth fixture'))
        self.rosters=tuple(r for r in rosters if r.benchmark not in missing_rosters)
        names={m.ticker for m in self.config.memberships if m.calculation_eligible}
        names.update(s for r in self.rosters for s in r.tickers);names.update(('SPY','QQQ','IWM'))
        begin=DAYS.index('2026-11-06')-253
        self.sessions=DAYS[begin:DAYS.index('2026-11-11')+1]
        data=[]
        for name in sorted(names):
            rate=D(1+sum((i+1)*ord(c) for i,c in enumerate(name))%200)/100
            for i,day in enumerate(self.sessions):
                price=D(100)+i*rate
                data.append(Bar(name,day,price,price,2000000))
        self.bars=tuple(data)
        folder=self.root/'config';folder.mkdir(parents=True)
        (folder/'tradingview_symbols.json').write_bytes((ROOT/'config/tradingview_symbols.json').read_bytes())
        def provider(_):
            schedule=Schedule(RECORDS,now=lambda:datetime.fromisoformat(self.target+'T23:00:00+00:00'))
            result=FixtureProvider(self.bars,schedule);self.providers.append(result);return result
        self.service=RefreshService(self.root,config_factory=lambda:self.config,provider_factory=provider,
                                    records=RECORDS,rosters_factory=lambda:self.rosters)
