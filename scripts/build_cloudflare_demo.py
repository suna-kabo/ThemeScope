"""Build the current vNext UI with deterministic synthetic data; stdlib only.

Only approved formula settings and fabricated fixture inputs are read; no service,
database, provider, environment credential or production membership/roster is read. The build is deliberately independent of local market-data state.
"""
from dataclasses import replace
from decimal import Decimal as D
from pathlib import Path
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.vnext_fixture_report import fixture
from scripts.build_inspection_bundle import safe_file
from src.themescope.domain import MarketRoster, ThemeStatus
from src.themescope.market.layer import market_layer
from src.themescope.research.engine import calculate_session
from src.themescope.research.context import enrich
from src.themescope.research.countertrend_exports import attach as attach_countertrend_exports
from src.themescope.storage import canonical
from src.themescope.themes.calculations import Bar, deterministic
from src.themescope.themes.index import build_index

from scripts.static_pages import ASSETS, HEADERS, favicon, font_assets

@deterministic
def demo_snapshot():
    config, original, sessions, target, _, _ = fixture()
    rename = {s: 'DEMO' + chr(65+i) for i, s in enumerate(sorted({s for s, _ in original}))}
    bars = {(rename[s], day): replace(bar, ticker=rename[s]) for (s, day), bar in original.items()}
    memberships = [replace(m, ticker=rename[m.ticker], company='Fictional ' + rename[m.ticker]) for m in config.memberships]
    weak = [m for m in config.memberships if m.theme_id == 'weak']
    for i, member in enumerate(weak):
        ticker = 'TURN' + chr(65+i)
        memberships.append(replace(member, ticker=ticker, company='Fictional ' + ticker, theme_id='mixed'))
        for j, day in enumerate(sessions):
            bar = original[member.ticker, day]
            bounce = D('.6') * max(0, j-59)
            bars[ticker, day] = replace(bar, ticker=ticker, adjusted_close=bar.adjusted_close+bounce, close=bar.close+bounce)
    alpha = [m for m in memberships if m.theme_id == 'alpha']
    memberships.extend(replace(m, theme_id='limited') for m in alpha[:4])
    template = config.themes[0]
    themes = tuple(config.themes) + (
        replace(template, theme_id='mixed', name='Synthetic Turnaround'),
        replace(template, theme_id='limited', name='Synthetic Limited Coverage'),
        replace(template, theme_id='watch', name='Synthetic Watch Concept', status=ThemeStatus.WATCH),
    )
    config = replace(config, themes=themes, memberships=tuple(memberships))
    indices = {t.theme_id: build_index(config,t.theme_id,bars,sessions,sessions[0],target)
               for t in themes if t.status == 'active' and t.theme_id != 'limited'}
    # Fabricated benchmark paths; ETF tickers here are display identifiers only.
    for ticker, rate in [('SPY',D('.5')), ('QQQ',D('.35')), ('IWM',D('-.25'))]:
        for i, day in enumerate(sessions):
            price = D(100)+i*rate
            bars[ticker, day] = Bar(ticker,day,price,price,D(2000000),adjusted_high=price+1,adjusted_low=price-1)
    market = market_layer(bars,sessions[:sessions.index(target)+1],(
        MarketRoster('SPY',sessions[0],tuple(m.ticker for m in alpha),'Synthetic demo roster'),
        MarketRoster('QQQ',sessions[0],tuple(rename[m.ticker] for m in weak),'Synthetic demo roster'),
    ))
    names = {m.ticker for m in memberships}
    mapping = {s:{'status':'verified','symbol':'DEMO:'+s} for s in names}
    snapshot = calculate_session(config,bars,sessions,target,market['decision']['direction'],indices,
                                 {t:'synthetic-demo-'+t for t in indices},mapping)
    snapshot.update(synthetic_fixture=True, market=market,
                    production_blockers=['Synthetic demo only; not a live activation configuration.'],
                    theme_layer={'state':'synthetic_demo','official_live_history':False},
                    today_plan='Synthetic fixture session', refreshed_at=target+'T23:00:00+00:00',
                    provider_health={'status':'Synthetic fixture'},
                    completeness={'required':len(names)+3,'valid_target':len(names)+3,'complete':True},
                    earnings={s:{'status':'Unavailable','dates':[]} for s in sorted(names)})
    snapshot['earnings'][sorted(names)[0]]={'status':'Available','dates':['2024-04-15']}
    snapshot=enrich(snapshot,bars,sessions[:sessions.index(target)+1],companies={m.ticker:m.company for m in memberships})
    snapshot=attach_countertrend_exports(snapshot,mapping)
    return json.loads(canonical(snapshot))


def build(root=ROOT):
    root = Path(root).resolve()
    output = root/'dist/cloudflare-pages'
    if any(p.is_symlink() for p in (root/'dist',output)):
        raise ValueError('Demo output must not be a symlink')
    assets = {name:(root/'static/vnext'/name).read_bytes() for name in ASSETS}
    assets.update(font_assets(root))
    payload = canonical(demo_snapshot()).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    assets.update({'preview.js':('window.FIXTURE_SNAPSHOT = '+payload+';\n').encode('utf-8'),
                   '_headers':HEADERS.encode('utf-8'), 'favicon.ico':favicon()})
    if output.exists():shutil.rmtree(output)
    output.mkdir(parents=True)
    try:
        for name, data in assets.items():(output/name).write_bytes(data)
        for name in (*ASSETS,'preview.js'):safe_file(output/name)
    except Exception:
        shutil.rmtree(output)
        raise
    return output


if __name__ == '__main__':
    build()
    print('Synthetic current-vNext demo built: dist/cloudflare-pages (no secrets required).')
