"""Manufactured test input only. Never fetches or contains a real publication.

False synthetic_fixture below exercises the local API's real-mode contract, not
an assertion that these fictional values came from an account or live refresh.
"""
from scripts.build_cloudflare_demo import demo_snapshot
from scripts.vnext_fixture_report import fixture
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch
import json


def public_contract_fixture():
    config,bars,sessions,target,_,mapping=fixture()
    calendar=[r['session'] for r in json.loads((Path(__file__).resolve().parents[1]/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']]
    start=calendar.index('2026-11-06')-sessions.index(target)
    dated=tuple(calendar[start:start+len(sessions)]);dates=dict(zip(sessions,dated))
    config=replace(config,memberships=tuple(replace(m,effective_from=dates[m.effective_from],
        review_snapshot=dates[m.review_snapshot]) for m in config.memberships),
        methodology=dict(config.methodology,launch_rebalance_session=dated[0]))
    bars={(ticker,dates[day]):replace(bar,session=dates[day]) for (ticker,day),bar in bars.items()}
    with patch('scripts.build_cloudflare_demo.fixture',return_value=(config,bars,dated,dates[target],{},mapping)):
        snapshot=demo_snapshot()
    snapshot.update(synthetic_fixture=False,
        refreshed_at='2026-11-07T01:00:00+00:00', provider_health={'status':'Healthy'},
        production_blockers=[], today_plan='Manufactured test research',
        theme_layer={'state':'live','research_session':dates[target],
            'official_live_history':True,'launch_rebalance_session':dated[0],'first_earned_session':dated[1]})
    return snapshot
