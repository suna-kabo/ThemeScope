"""Read-only deterministic boundaries for the UI and future research agents."""
from copy import deepcopy


def get_market_state(snapshot):
    return deepcopy((snapshot or {}).get('market'))


def get_market_changes(snapshot):
    return deepcopy((snapshot or {}).get('research_v2', {}).get('changes'))


def get_theme(snapshot, theme_id):
    row = next((t for t in (snapshot or {}).get('themes', ()) if t['theme_id'] == theme_id), None)
    if row is None:
        return None
    return dict(deepcopy(row), research=deepcopy(snapshot.get('research_v2', {}).get('themes', {}).get(theme_id)))


def get_theme_history(snapshots, theme_id):
    return [dict(session=s['session'], theme=row) for s in sorted(snapshots, key=lambda s: s['session'])
            if (row := get_theme(s, theme_id)) is not None]


def get_theme_members(snapshot, theme_id):
    return deepcopy([r for r in (snapshot or {}).get('relationships', ()) if r['theme_id'] == theme_id])


def get_stock(snapshot, ticker):
    rows = [r for r in (snapshot or {}).get('relationships', ()) if r['ticker'] == ticker]
    if not rows:
        return None
    return dict(ticker=ticker, company=snapshot.get('research', {}).get('companies', {}).get(ticker),
                relationships=deepcopy(rows))


def get_research_list(snapshot):
    return deepcopy((snapshot or {}).get('research_v2', {}).get('list'))
