"""Clean staged-tree install/launcher smoke test; synthetic CSVs stay temporary.

On Windows this executes setup.cmd, refresh.cmd and prepare-site.cmd from a
different working directory. Elsewhere it exercises their Python entry points.
It never touches the real output/history, commits, pushes or deploys anything.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
HEADER=['Symbol','Description','Price','Price change %, 1 day','Market capitalization','Performance %, 1 week','Performance %, 1 month','Performance %, 3 months','Industry','Sector','Exchange','Exponential moving average, 21, 1 day','Exponential moving average, 50, 1 day','Average true range %, 14, 1 day','Price × volume (turnover), 1 day','Price × average volume, 30 days','Relative volume, 1 day','Upcoming earnings date']


def hashes(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--browser',action='store_true');args=parser.parse_args()
    tree=subprocess.check_output(['git','write-tree'],cwd=ROOT,text=True).strip()
    source=subprocess.check_output(['git','archive','--format=zip',tree],cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='themescope clean test ') as temporary:
        base=Path(temporary);clone=base/'source with spaces';clone.mkdir()
        with zipfile.ZipFile(io.BytesIO(source)) as archive:archive.extractall(clone)
        if os.name=='nt':
            for file in clone.glob('*.cmd'):file.write_bytes(file.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        def run(script,args=(),success=True):
            if os.name=='nt':command=['cmd.exe','/d','/c','call',str(clone/(script+'.cmd')),*args]
            else:
                python=clone/'.venv/bin/python'
                command=[sys.executable if script=='setup' else str(python),str(clone/'scripts'/({'setup':'setup_local','refresh':'refresh_local','prepare-site':'prepare_site'}[script]+'.py')),*args]
            result=subprocess.run(command,cwd=base,input='\n',capture_output=True,text=True,encoding='utf-8',timeout=180)
            if (result.returncode==0)!=success:raise AssertionError(script+'\n'+result.stdout+'\n'+result.stderr)
            return result
        run('setup')
        active=json.loads((clone/'config/active_anchors.json').read_text(encoding='utf-8'))['anchors']
        lists=json.loads((clone/'config/theme_watchlists.json').read_text(encoding='utf-8'))['watchlists']
        members=sorted({m['ticker'] for t in lists if t['theme_id'] in active for m in t['members']})
        symbols={'Daily_Stock':members,'Daily_ETF':sorted(set(active.values())|{'SPY','QQQ','IWM'}),'SPY':['TESTSPY'+str(i) for i in range(500)],'QQQ':['TESTQQQ'+str(i) for i in range(100)],'IWM':['TESTIWM'+str(i) for i in range(2000)]}
        folder=base/'synthetic csv';folder.mkdir()
        def inputs(price):
            for stem,tickers in symbols.items():
                with (folder/(stem+'.csv')).open('w',encoding='utf-8',newline='') as handle:
                    writer=csv.writer(handle);writer.writerow(HEADER)
                    for ticker in tickers:writer.writerow([ticker,'Synthetic test only',price,1,3e9,2,3,4,'Test','Test','NASDAQ',90,80,2,3e7,3e7,1,None])
        inputs(100)
        options=['--session','2024-01-03','--input-dir',str(folder)]
        run('refresh',options);run('prepare-site',['--session','2024-01-03'])
        output=clone/'output/manual_csv';site=clone/'site'
        first_snapshot=json.loads((output/'latest_snapshot.json').read_text(encoding='utf-8'))
        assert all(t['priority_change']=='N/A' for t in first_snapshot['themes'])
        before=hashes(output);site_before=hashes(site)
        # A real invalid CSV must preserve every existing successful output/history.
        stock=folder/'Daily_Stock.csv'
        with stock.open(encoding='utf-8',newline='') as f:rows=list(csv.reader(f))
        with stock.open('w',encoding='utf-8',newline='') as f:writer=csv.writer(f);writer.writerows(rows+[rows[1]])
        run('refresh',options,success=False)
        after=hashes(output)
        for name,digest in before.items():assert after[name]==digest,name
        assert hashes(site)==site_before
        inputs(100);run('refresh',options)
        assert hashes(site)==site_before # Refresh is never a site build.
        # Reusing yesterday's exact CSVs under a new session is refused.
        run('refresh',['--session','2024-01-04','--input-dir',str(folder)],success=False)
        inputs(101);run('refresh',['--session','2024-01-04','--input-dir',str(folder)])
        snapshot=json.loads((output/'latest_snapshot.json').read_text(encoding='utf-8'))
        assert snapshot['local_history']['comparison_session']=='2024-01-03'
        assert all(t['rank_change_daily'] is not None for t in snapshot['themes'])
        assert all(t['priority_change']=='—' for t in snapshot['themes'])
        assert (output/'local_history/2024-01-03.json').exists()
        assert hashes(site)==site_before
        run('prepare-site',['--session','2024-01-04'])
        assert not (site/'raw_inputs.json').exists() and not (site/'run_audit.json').exists() and not (site/'local_history').exists()
        if args.browser:
            subprocess.run([sys.executable,str(ROOT/'tests/browser_check_site.py'),str(site)],cwd=ROOT,check=True,timeout=90)
            subprocess.run([sys.executable,str(ROOT/'tests/browser_check_tables.py'),str(output/'dashboard.html')],cwd=ROOT,check=True,timeout=90)
    print(json.dumps({'clean_staged_tree':tree,'platform':sys.platform,'native_cmd_launchers':os.name=='nt','setup_refresh_site':'passed','invalid_input_preservation':'passed','stale_input_refusal':'passed','two_session_history':'passed','synthetic_data':'temporary only'}))


if __name__=='__main__':main()
