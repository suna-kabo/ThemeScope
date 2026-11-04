"""Clean staged-tree install/launcher smoke test; synthetic CSVs stay temporary.

On Windows this executes setup.cmd, refresh.cmd and prepare-site.cmd from a
different working directory. Elsewhere it exercises their Python entry points.
It never touches the real output/history, commits, pushes or deploys anything.
"""
import argparse
import csv
import hashlib
import io
import http.client
import threading
from urllib.parse import urlsplit,quote
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.serve_local import create_server
HEADER=['Symbol','Description','Price','Price change %, 1 day','Market capitalization','Performance %, 1 week','Performance %, 1 month','Performance %, 3 months','Industry','Sector','Exchange','Exponential moving average, 21, 1 day','Exponential moving average, 50, 1 day','Average true range %, 14, 1 day','Price × volume (turnover), 1 day','Price × average volume, 30 days','Relative volume, 1 day','Upcoming earnings date']


def hashes(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--browser',action='store_true');args=parser.parse_args()
    tree=subprocess.check_output(['git','write-tree'],cwd=ROOT,text=True).strip()
    source=subprocess.check_output(['git','archive','--format=zip',tree],cwd=ROOT)
    with tempfile.TemporaryDirectory(prefix='themescope clean test ') as temporary:
        base=Path(temporary);clone=base/'source with spaces 香港';clone.mkdir()
        with zipfile.ZipFile(io.BytesIO(source)) as archive:archive.extractall(clone)
        if os.name=='nt':
            for file in clone.glob('*.cmd'):file.write_bytes(file.read_bytes().replace(b'\r\n',b'\n').replace(b'\n',b'\r\n'))
        def run(script,args=(),success=True):
            if os.name=='nt':command=['cmd.exe','/d','/c','call',str(clone/(script+'.cmd')),*args]
            else:
                python=clone/'.venv/bin/python'
                command=[sys.executable if script=='setup' else str(python),str(clone/'scripts'/({'setup':'setup_local','refresh':'refresh_local','prepare-site':'prepare_site','open-dashboard':'serve_local','preview-site':'serve_local'}[script]+'.py')),*( ['--site'] if script=='preview-site' else []),*args]
            result=subprocess.run(command,cwd=base,input='\n',capture_output=True,text=True,encoding='utf-8',timeout=180)
            if (result.returncode==0)!=success:raise AssertionError(script+'\n'+result.stdout+'\n'+result.stderr)
            return result
        run('setup')
        active=json.loads((clone/'config/active_anchors.json').read_text(encoding='utf-8'))['anchors']
        lists=json.loads((clone/'config/theme_watchlists.json').read_text(encoding='utf-8'))['watchlists']
        members=sorted({m['ticker'] for t in lists if t['theme_id'] in active for m in t['members']})
        symbols={'Daily_Stock':members,'Daily_ETF':sorted(set(active.values())|{'SPY','QQQ','IWM'}),'SPY':['TESTSPY'+str(i) for i in range(500)],'QQQ':['TESTQQQ'+str(i) for i in range(100)],'IWM':['TESTIWM'+str(i) for i in range(2000)]}
        folder=clone/'inputs/2024-01-03';folder.mkdir(parents=True)
        newer_folder=clone/'inputs/2024-01-04';newer_folder.mkdir()
        def inputs(price,target=None):
            target=target or folder
            for stem,tickers in symbols.items():
                with (target/(stem+'.csv')).open('w',encoding='utf-8',newline='') as handle:
                    writer=csv.writer(handle);writer.writerow(HEADER)
                    for ticker in tickers:writer.writerow([ticker,'Synthetic test only',price,1,3e9,2,3,4,'Test','Test','NASDAQ',90,80,2,3e7,3e7,1,None])
        inputs(100)
        options=['--session','2024-01-03']
        run('refresh',options);run('prepare-site',['--session','2024-01-03'])
        output=clone/'output/manual_csv';site=clone/'site'
        first_snapshot=json.loads((output/'latest_snapshot.json').read_text(encoding='utf-8'))
        assert all(t['priority_change']=='N/A' for t in first_snapshot['themes'])
        before=hashes(output);site_before=hashes(site)
        # These are the real production preview handler and completed-file checks.
        dashboard_server,_,dashboard_url=create_server(clone,False,0)
        site_server,_,site_url=create_server(clone,True,0)
        for server in (dashboard_server,site_server):
            server.RequestHandlerClass.log_message=lambda *args:None
            threading.Thread(target=lambda selected=server:selected.serve_forever(poll_interval=.01),daemon=True).start()
        def get(url):
            parsed=urlsplit(url);connection=http.client.HTTPConnection(parsed.hostname,parsed.port,timeout=10)
            connection.request('GET',parsed.path+('?' +parsed.query if parsed.query else ''),headers={'If-Modified-Since':'Wed, 04 Nov 2037 00:00:00 GMT'})
            response=connection.getresponse();data=response.read();headers=dict(response.getheaders());connection.close()
            if response.status==307:return get('http://'+parsed.netloc+headers['Location'])
            assert response.status==200,(url,response.status,data[:300])
            assert 'no-store' in headers['Cache-Control']
            return data,headers
        def assert_preview(url,folder,day):
            data,headers=get(url);entry='index.html' if folder==site else 'dashboard.html'
            assert data==(folder/entry).read_bytes()
            assert headers['X-ThemeScope-Session']==day
            metadata='snapshot_summary.json' if folder==site else 'latest_snapshot.json'
            data,_=get('http://'+urlsplit(url).netloc+'/'+metadata)
            assert json.loads(data)['session_date']==day
        assert_preview(dashboard_url,output,'2024-01-03');assert_preview(site_url,site,'2024-01-03')
        run('open-dashboard',['--help']);run('preview-site',['--help'])
        for launcher in ('open-dashboard','preview-site'):
            result=run(launcher,['--port',str(dashboard_server.server_port)],success=False)
            assert 'occupied' in result.stderr
        # A second dated folder is expected; an incomplete newer day cannot fall back.
        (newer_folder/'Daily_Stock.csv').write_text('incomplete newer export',encoding='utf-8')
        run('refresh',['--session','2024-01-04'],success=False)
        assert (output/'dashboard.html').read_bytes()==get(dashboard_url)[0]

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
        inputs(100,newer_folder);run('refresh',['--session','2024-01-04'],success=False)
        inputs(101,newer_folder);run('refresh',['--session','2024-01-04'])
        snapshot=json.loads((output/'latest_snapshot.json').read_text(encoding='utf-8'))
        assert snapshot['local_history']['comparison_session']=='2024-01-03'
        assert all(t['rank_change_daily'] is not None for t in snapshot['themes'])
        assert all(t['priority_change']=='—' for t in snapshot['themes'])
        assert (output/'local_history/2024-01-03.json').exists()
        assert hashes(site)==site_before
        # An already-running preview reads the updated files, not cached HTML.
        assert_preview(dashboard_url,output,'2024-01-04');assert_preview(site_url,site,'2024-01-03')
        run('prepare-site',['--session','2024-01-03'],success=False)
        assert hashes(site)==site_before
        run('prepare-site',['--session','2024-01-04'])
        assert_preview(site_url,site,'2024-01-04')
        old_research=snapshot['daily_primary_research']
        old_paths=[row['file'] for row in snapshot['export_manifest'] if row['role'] in {'daily_primary_research','individual_primary_research'}]+[old_research['archive_file'],old_research['relationships_file']]
        # Same-session changes can remove Primary results; old dated files retire.
        inputs(85,newer_folder);run('refresh',['--session','2024-01-04'])
        empty=json.loads((output/'latest_snapshot.json').read_text(encoding='utf-8'))
        assert empty['market_classification']['direction']=='Neutral'
        assert all(not (output/name).exists() for name in old_paths if name)
        run('prepare-site',['--session','2024-01-04'])
        assert all(not (site/name).exists() for name in old_paths if name)
        # Restore original day 4, then replay day 3 without rewriting later history.
        inputs(101,newer_folder);run('refresh',['--session','2024-01-04'])
        fourth=(output/'local_history/2024-01-04.json').read_bytes()
        third=(output/'local_history/2024-01-03.json').read_bytes()
        run('refresh',options)
        assert (output/'local_history/2024-01-04.json').read_bytes()==fourth
        assert (output/'local_history/2024-01-03.json').read_bytes()==third
        assert_preview(dashboard_url,output,'2024-01-03')
        before_older=hashes(output);site_older=hashes(site)
        inputs(102);run('refresh',options,success=False)
        for name,value in before_older.items():assert hashes(output)[name]==value,name
        assert hashes(site)==site_older
        inputs(100);run('refresh',['--session','2024-01-04'])
        run('prepare-site',['--session','2024-01-04'])
        # Identical same-session reruns keep genuine comparison/transition records.
        run('refresh',['--session','2024-01-04'])
        assert (output/'local_history/2024-01-04.json').read_bytes()==fourth
        assert_preview(dashboard_url,output,'2024-01-04')
        current_headers=get(dashboard_url)[1]
        for item in snapshot['export_manifest']:
            data,_=get('http://'+urlsplit(dashboard_url).netloc+'/_preview/'+current_headers['X-ThemeScope-Run']+'/'+quote(item['file']))
            assert data==(output/item['file']).read_bytes()
        assert not (site/'raw_inputs.json').exists() and not (site/'run_audit.json').exists() and not (site/'local_history').exists()
        if args.browser:
            # Prove old browser history cannot render an old session over new HTML.
            from playwright.sync_api import sync_playwright
            import shutil
            with sync_playwright() as playwright:
                options={'headless':True,'args':['--no-sandbox']}
                if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                browser=playwright.chromium.launch(**options);context=browser.new_context()
                context.add_init_script("history.replaceState({themescope:true,index:0,view:{ui_schema:5,session_date:'2024-01-03',page:'watchlist'}},'',location.href)")
                page=context.new_page();page.goto(dashboard_url)
                assert page.locator('#snapshot-data').evaluate('e=>JSON.parse(e.textContent).session_date')=='2024-01-04'
                assert '4 Jan 2024' in page.locator('#date').inner_text()
                browser.close()
            subprocess.run([sys.executable,str(ROOT/'tests/browser_check_site.py'),str(site)],cwd=ROOT,check=True,timeout=90)
            subprocess.run([sys.executable,str(ROOT/'tests/browser_check_tables.py'),str(output/'dashboard.html')],cwd=ROOT,check=True,timeout=90)
            subprocess.run([sys.executable,str(ROOT/'tests/browser_check_methodology.py'),str(output/'dashboard.html'),str(site/'index.html')],cwd=ROOT,check=True,timeout=90)
        for server in (dashboard_server,site_server):server.shutdown();server.server_close()
    print(json.dumps({'multiple_dated_folders':'passed','running_production_previews_reload':'passed','older_replay_history':'passed','retired_downloads':'passed','non_ascii_path':True,'clean_staged_tree':tree,'platform':sys.platform,'native_cmd_launchers':os.name=='nt','setup_refresh_site':'passed','invalid_input_preservation':'passed','stale_input_refusal':'passed','two_session_history':'passed','synthetic_data':'temporary only'}))


if __name__=='__main__':main()
