"""Validate actual generated exports against canonical memberships and manifest."""
import argparse,json,zipfile,copy,tempfile,sys,math
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def check(root):
    s=json.loads((root/'latest_snapshot.json').read_text());canonical=json.loads((root/'canonical_dashboard_data.json').read_text())
    assert s['daily_primary']==canonical['daily_primary']
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
    assert {r['tradingview_symbol'] for r in s['daily_primary']['candidates']}==primary
    for row in s['daily_primary']['candidates']:
        expected={t['id'] for t in s['themes'] if t['research_priority']['category']=='primary' and any(r['tradingview_symbol']==row['tradingview_symbol'] for r in t['selected'])}
        assert {c['theme_id'] for c in row['primary_contexts']}==expected
    data=[];focused=[];sections=0
    for item in s['export_manifest']:
        tokens=(root/item['file']).read_text().strip().split(',')
        assert sum(not t.startswith('###') for t in tokens)==item['instrument_count']<=s['export_configuration']['instrument_limit']
        assert sum(t.startswith('###') for t in tokens)==item['section_count']
        if item['role']=='configured_stock_daily_data':data+=tokens
        if item['role']=='daily_primary_scan':focused+=tokens
        if item['role']=='thematic_navigation':
            sections+=item['section_count']
            for i,token in enumerate(tokens):
                if token.startswith('###'):
                    theme=next(t for t in s['themes'] if token=='###'+t['name'].replace(',',' ')+' ('+t['anchor']+')')
                    expected=[theme['tradingview_symbol']]+[r['tradingview_symbol'] for r in theme['selected']]
                    assert tokens[i+1:i+1+len(expected)]==expected
    assert len(data)==len(set(data)) and set(data)==all_stocks
    assert len(focused)==len(set(focused)) and set(focused)==primary
    assert sections==len(s['themes'])
    with zipfile.ZipFile(root/'run_bundle.zip') as z:
        assert z.testzip() is None
        for item in s['export_manifest']:assert z.read(item['file'])==(root/item['file']).read_bytes()
    # Exercise the real writer with a synthetic lower limit, without changing real configuration/history.
    from scripts.generate_dashboard import _manual_csv_outputs
    synthetic=copy.deepcopy(s);synthetic['export_configuration']['instrument_limit']=100
    with tempfile.TemporaryDirectory() as temporary:
        stage=Path(temporary)
        _manual_csv_outputs(synthetic,{},stage)
        primary_files=[f['file'] for f in synthetic['export_manifest'] if f['role']=='daily_primary_scan']
        if len(primary)>100:
            assert len(primary_files)>1 and synthetic['export_archives']
            with zipfile.ZipFile(stage/synthetic['export_archives'][0]) as z:
                assert z.namelist()==primary_files
                split_tokens=[token for name in z.namelist() for token in z.read(name).decode().strip().split(',')]
                assert set(split_tokens)==primary and len(split_tokens)==len(primary)
        assert all(f['instrument_count']<=100 for f in synthetic['export_manifest'])
    print(json.dumps({'groups':len(s['export_configuration']['groups']),'sections':sections,'configured_unique_stocks':len(data),'primary_unique_stocks':len(focused),'manifest_agreement':True}))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);check(p.parse_args().output)
