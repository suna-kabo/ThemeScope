"""Validate actual generated exports against canonical memberships and manifest."""
import argparse,json,zipfile,copy,tempfile,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def check(root):
    s=json.loads((root/'latest_snapshot.json').read_text());canonical=json.loads((root/'canonical_dashboard_data.json').read_text())
    assert s['expected_earnings']==canonical['expected_earnings']
    assert 'daily_primary' not in s and 'daily_primary' not in canonical
    assert s['export_manifest']==canonical['export_manifest']
    for theme in s['themes']:
        for stock in theme['selected']:
            for period in ('21','63'):
                a=stock['returns'][period]['value'];b=theme['returns'][period]['value']
                actual=stock['excess'+period+'_pp']
                if a is None or b is None:assert actual is None
                else:assert math.isclose(actual,100*(a-b),abs_tol=1e-10)
    all_stocks={r['tradingview_symbol'] for t in s['themes'] for r in t['selected']}
    primary={r['tradingview_symbol'] for t in s['themes'] if t['research_priority']['category']=='primary' for r in t['selected']}
    earnings=s['expected_earnings']
    known={r['symbol'] for r in earnings['upcoming']+earnings['unknown']}
    assert known <= primary and len(known)+earnings['later_count']==len(primary)
    for row in earnings['upcoming']:
        expected={t['id'] for t in s['themes'] if t['research_priority']['category']=='primary' and any(r['tradingview_symbol']==row['symbol'] for r in t['selected'])}
        assert {c['theme_id'] for c in row['contexts']}==expected
    assert not list(root.glob('tradingview_primary_stocks*'))
    assert s['export_archives'][0]=='individual_theme_watchlists.zip'
    data=[];individuals=[]
    for item in s['export_manifest']:
        tokens=(root/item['file']).read_text().strip().split(',')
        assert sum(not t.startswith('###') for t in tokens)==item['instrument_count']<=s['export_configuration']['instrument_limit']
        assert sum(t.startswith('###') for t in tokens)==item['section_count']
        if item['role']=='configured_stock_daily_data':data+=tokens
        assert item['role']!='daily_primary_scan'
        assert item['section_count']==0 and len(tokens)==len(set(tokens))
        if item['role']=='individual_research':
            individuals.append(item)
            theme=next(t for t in s['themes'] if t['id']==item['theme_id'])
            assert tokens==[theme['tradingview_symbol']]+[r['tradingview_symbol'] for r in theme['selected']]
            assert Path(item['file']).name.startswith(theme['anchor']+'_')
        if item['role']=='optional_broad_scan':
            assert not any(t.startswith('###') for t in tokens)
    assert len(data)==len(set(data)) and set(data)==all_stocks
    assert len(individuals)==len(s['themes'])
    archive_index=json.loads((root/'individual_theme_watchlists.json').read_text())
    with zipfile.ZipFile(root/'individual_theme_watchlists.zip') as z:
        assert z.testzip() is None and len(z.namelist())==len(individuals)
        for item in individuals:
            assert z.read(Path(item['file']).name)==(root/item['file']).read_bytes()
            assert archive_index[item['theme_id']]['file']==item['file']
    with zipfile.ZipFile(root/'run_bundle.zip') as z:
        assert z.testzip() is None
        for item in s['export_manifest']:assert z.read(item['file'])==(root/item['file']).read_bytes()
    # Recompute filtered lists from endpoints, preserving per-anchor overlap relationships.
    from src.themescope.daily_lists import primary_research
    check_snapshot=copy.deepcopy(s);files,manifest=primary_research(check_snapshot,s['export_configuration']['instrument_limit'])
    assert check_snapshot['daily_primary_research']==s['daily_primary_research']
    for name,content in files.items():assert (root/name).read_text()==content
    research=s['daily_primary_research']
    if research['archive_file']:
        with zipfile.ZipFile(root/research['archive_file']) as archive:
            expected=[r for r in manifest if r['role']=='individual_primary_research']
            assert len(archive.namelist())==len(expected)
            for item in expected:assert archive.read(Path(item['file']).name)==(root/item['file']).read_bytes()
    print(json.dumps({'groups':len(s['export_configuration']['groups']),'individuals':len(individuals),'configured_unique_stocks':len(data),'earnings_scope_unique_stocks':len(primary),'manifest_agreement':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);check(p.parse_args().output)
