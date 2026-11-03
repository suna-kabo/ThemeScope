"""HTTP verification of the deployable allowlist, not the private run folder."""
import argparse
import http.server
import json
from pathlib import Path
import shutil
import socketserver
import sys
import threading
from urllib.parse import urlparse
import zipfile

from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.site_output import validate_site


def main():
    parser=argparse.ArgumentParser();parser.add_argument('site',type=Path);args=parser.parse_args()
    site=args.site.resolve();manifest=validate_site(site)
    if manifest['kind']!='snapshot':raise ValueError('This browser check expects a prepared dated snapshot')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=socketserver.TCPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(site),**kw));threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_address[1]}/';errors=[];requests=[]
    artifacts=ROOT/'output/site_browser';artifacts.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1536,'height':864},has_touch=True)
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
            response=page.goto(url);assert response.status==200
            payload=page.locator('#snapshot-data').evaluate('e=>JSON.parse(e.textContent)')
            assert payload['session_date']==manifest['session_date']
            assert 'initialization failed' not in page.locator('#status').inner_text()
            for private in ['run_audit.json','raw_inputs.json','latest_snapshot.json','canonical_dashboard_data.json','run_bundle.zip','local_history/'+manifest['session_date']+'.json','.git/config']:
                assert page.request.get(url+private).status==404,private
            for name in manifest['files']:
                assert page.request.get(url+name).status==200,name
            for route in ['market','daily-plan','sectors-themes','watchlist','methodology']:
                page.click('[data-page="'+route+'"]')
                expect(page.locator('#'+route)).to_be_visible()
                for link in page.locator('#'+route+' a[href]').evaluate_all('es=>es.map(e=>e.getAttribute("href"))'):
                    if not link.startswith(('#','https://','blob:')):assert link in manifest['files'],link
            page.click('[data-page="daily-plan"]')
            expected_ids=[t['id'] for t in payload['themes'] if t['research_priority']['category']=='primary']
            actual_ids=page.locator('#daily-priorities tr:not(.priority-group-heading) td:first-child [data-daily-theme]').evaluate_all('es=>es.map(e=>e.dataset.dailyTheme)')
            assert sorted(actual_ids)==sorted(expected_ids)
            page.click('[data-page="methodology"]')
            assert page.locator('#methodology-content .market-matrix tbody tr').count()==64
            assert page.locator('#methodology-content tr.active-cell').count()==1
            for key,ids in payload['decision']['primary_groups'].items():
                assert page.locator('[data-priority-group="'+key+'"] tr:not(.priority-group-heading)').evaluate_all('es=>es.map(e=>e.querySelector("[data-daily-theme]").dataset.dailyTheme)')==ids
            page.click('[data-page="sectors-themes"]')
            for theme in payload['themes']:
                row=page.locator('#theme-body tr[data-theme="'+theme['id']+'"]')
                assert row.locator('.col-priority').inner_text()==theme['research_priority']['label']
                assert row.locator('.col-priority-change').inner_text()==theme['priority_change']
            assert page.locator('#theme-body .col-priority [title]').count()==0
            for label in ('Leading','Improving','Fading','Lagging','Secondary'):
                assert label not in page.locator('body').inner_text()
            research=payload['daily_primary_research']
            if research['combined_file']:
                page.click('[data-page="daily-plan"]')
                with page.expect_download() as info:page.locator('a[href="'+research['combined_file']+'"]').click()
                assert Path(info.value.path()).read_bytes()==(site/research['combined_file']).read_bytes()
            page.click('[data-page="watchlist"]')
            assert page.locator('#stock-view').count()==0
            assert page.locator('#stock-head th').count()==14
            page.click('[data-page="daily-plan"]');page.evaluate('window.scrollTo(0,400)');page.wait_for_timeout(160);y=page.evaluate('window.scrollY')
            page.click('[data-page="market"]');page.go_back()
            assert abs(page.evaluate('window.scrollY')-y)<3
            page.click('[data-page="watchlist"]');assert page.locator('#stock-view').count()==0
            stock=next(s for t in payload['themes'] for s in t['selected'])
            find=page.locator('#watchlist-theme-search');find.fill(stock['ticker']);find.press('ArrowDown');find.press('Enter')
            expect(page.locator('#stock-body .navigation-target')).to_be_visible()
            current=next(t for t in payload['themes'] if t['id']==page.locator('#watchlist-theme-selector').input_value())
            with page.expect_download() as info:page.click('#tv')
            assert Path(info.value.path()).read_text().strip().split(',')==[current['tradingview_symbol']]+[s['tradingview_symbol'] for s in current['selected']]
            page.click('[data-page="sectors-themes"]')
            with page.expect_download() as info:page.click('#all-individual-watchlists')
            with zipfile.ZipFile(info.value.path()) as archive:assert len(archive.namelist())==len(payload['themes']) and archive.testzip() is None
            for mode in ['dark','light']:
                if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
                page.click('[data-page="market"]');page.evaluate('window.scrollTo(0,0)')
                page.screenshot(path=str(artifacts/f'site-market-{mode}.png'))
            assert not errors,errors
            assert not [r for r in requests if urlparse(r).scheme in {'http','https'} and not r.startswith(url)]
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'session':manifest['session_date'],'allowlisted_assets':len(manifest['files']),'http_links_downloads':'passed','navigation_history':'passed','private_urls':'404','javascript_errors':errors,'automatic_external_requests':0,'screenshots':2}))


if __name__=='__main__':main()
