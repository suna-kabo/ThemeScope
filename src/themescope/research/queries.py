"""Read-only deterministic boundaries for the UI and future research agents."""
from copy import deepcopy


from .v2 import current_contract


def get_market_state(snapshot):
    return deepcopy((snapshot or {}).get('market'))


def get_market_changes(snapshot):
    return deepcopy(current_contract(snapshot).get('changes'))


def get_theme(snapshot, theme_id):
    row = next((t for t in (snapshot or {}).get('themes', ()) if t['theme_id'] == theme_id), None)
    if row is None:
        return None
    # Historical v1 priority/transition fields are not current research decisions.
    result={key:deepcopy(value) for key,value in row.items()
            if key not in ('priority','transition','history','research_member_signature','breadth_above')}
    result['research']=deepcopy(current_contract(snapshot).get('themes',{}).get(theme_id))
    result['selection_available']=bool(current_contract(snapshot))
    return result


def get_theme_history(snapshots, theme_id):
    return [dict(session=s['session'], theme=row) for s in sorted(snapshots, key=lambda s: s['session'])
            if (row := get_theme(s, theme_id)) is not None]


def _relationships(snapshot, rows):
    result=deepcopy(rows)
    if not current_contract(snapshot):
        for row in result:
            for key in ('qualifies','eligibility','assigned_section','also_qualifies_in'):row[key]=None
    return result


def get_theme_members(snapshot, theme_id):
    if not any(t['theme_id']==theme_id for t in (snapshot or {}).get('themes',())):return None
    return _relationships(snapshot,sorted((r for r in (snapshot or {}).get('relationships', ()) if r['theme_id'] == theme_id),key=lambda r:r['ticker']))


def get_stock(snapshot, ticker):
    rows = [r for r in (snapshot or {}).get('relationships', ()) if r['ticker'] == ticker]
    if not rows:
        return None
    return dict(ticker=ticker, company=snapshot.get('research', {}).get('companies', {}).get(ticker),
                relationships=_relationships(snapshot,rows),selection_available=bool(current_contract(snapshot)))


def get_research_list(snapshot):
    return deepcopy(current_contract(snapshot).get('list'))
