"""Manufactured test input only. Never fetches or contains a real publication.

False synthetic_fixture below exercises the local API's real-mode contract, not
an assertion that these fictional values came from an account or live refresh.
"""
from scripts.build_cloudflare_demo import demo_snapshot


def public_contract_fixture():
    snapshot = demo_snapshot()
    snapshot.update(synthetic_fixture=False, session='2026-11-06',
        refreshed_at='2026-11-07T01:00:00+00:00', provider_health={'status':'Healthy'},
        production_blockers=[], today_plan='Manufactured test research',
        theme_layer={'state':'initialized','research_session':'2026-11-06',
            'official_live_history':True,'launch_rebalance_session':'2026-11-06','first_earned_session':'2026-11-09'})
    for theme in snapshot['themes']:
        if 'session' in theme['index']:
            theme['index']['session']='2026-11-06'
    return snapshot
