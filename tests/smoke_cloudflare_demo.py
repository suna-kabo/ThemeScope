"""Current vNext Pages output over static HTTP only; no application backend."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import threading
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.build_cloudflare_demo import build, ASSETS
from scripts.static_pages import copy_fonts

from ui_smoke_helpers import open_exports,open_filters


def main(public=False):
    from playwright.sync_api import sync_playwright, expect
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);assets=root/'static/vnext';assets.mkdir(parents=True)
        for name in ASSETS:shutil.copyfile(ROOT/'static/vnext'/name,assets/name)
        copy_fonts(ROOT,root/'static')
        if public:
            from unittest.mock import patch
            from public_snapshot_support import public_contract_fixture
            from scripts import build_public_snapshot
            with patch.object(build_public_snapshot,'fetch_snapshot',return_value=public_contract_fixture()):
                output=build_public_snapshot.build('2026-11-06',root)
        else:
            output=build(root)
        headers=[line.strip().split(': ',1) for line in (output/'_headers').read_text().splitlines() if line.startswith('  ')]
        class Static(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
            def end_headers(self):
                for key,value in headers:self.send_header(key,value)
                super().end_headers()
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Static,directory=str(output)))
        worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
        origin=f'http://127.0.0.1:{server.server_port}'
        try:
            with sync_playwright() as p:
                options={'headless':True}
                if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                errors=[];external=[];api=[];failures=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
                page.on('response',lambda r:failures.append(r.url) if r.status>=400 else None)
                def request(r):
                    if not r.url.startswith((origin,'blob:')):external.append(r.url)
                    if r.url.startswith(origin+'/api/'):api.append(r.url)
                page.on('request',request)
                page.goto(origin)
                if public:
                    expect(page.locator('#public-banner')).to_have_text('Public snapshot · Completed US session 2026-11-06 · Market data fixed')
                    expect(page.locator('#public-banner')).to_be_visible()
                    expect(page.locator('#fixture-banner')).to_be_hidden()
                    expect(page.locator('#refresh')).to_be_hidden()
                    expect(page.locator('#progress')).to_have_text('Market data fixed')
                    assert 'Synthetic inspection fixture' not in page.locator('body').inner_text()
                    assert 'Replay fixture' not in page.locator('body').inner_text()
                else:
                    expect(page.locator('#fixture-banner')).to_be_visible()
                expect(page.locator('#overview-title')).to_be_visible()
                assert not page.locator('#theme-map-panel').evaluate('e=>e.open');page.locator('#theme-map-panel>summary').click()
                expect(page.locator('[data-map-theme]')).to_have_count(4)
                assert page.locator('.market-card.context .breadth-bar').count()==0
                before=page.locator('#market-cards').inner_text()
                if public:
                    # A programmatic click also cannot escape the static-mode guard.
                    page.locator('#refresh').evaluate('(button)=>button.click()')
                    expect(page.locator('#progress')).to_have_text('Market data fixed')
                else:
                    page.get_by_role('button',name='Replay fixture',exact=True).click()
                    expect(page.locator('#progress')).to_have_text('Synthetic fixture replayed')
                assert page.locator('#market-cards').inner_text()==before
                def nav(name):
                    page.locator(f'[data-nav="{name}"]').click()
                    if name=='primary':page.locator('[data-candidate-lens="directional"]').click()
                nav('themes');expect(page.locator('#theme-table tbody tr')).to_have_count(5)
                page.locator('#theme-search').fill('alpha');expect(page.locator('#theme-table tbody tr')).to_have_count(1)
                page.locator('#theme-table [data-inspect-theme]').first.click()
                expect(page.locator('#inspector-title')).to_contain_text('alpha')
                page.locator('#inspector-members [data-inspect-ticker]').first.click()
                expect(page.locator('#inspector-content')).to_contain_text('Other relationships')
                page.keyboard.press('Escape');expect(page.locator('#theme-search')).to_have_value('alpha')
                page.go_forward();expect(page.locator('#research-inspector')).to_be_visible();page.go_back()
                nav('primary');expect(page.locator('#candidates tbody tr')).to_have_count(2)
                ticker=page.locator('#candidates [data-save]').first.get_attribute('data-save')
                page.locator('#candidates [data-save]').first.click()
                page.get_by_role('button',name='Grouped by theme',exact=True).click();expect(page.locator('#candidates tbody tr')).to_have_count(4)
                page.locator('#candidate-sort').select_option('w-desc')
                open_exports(page)
                with page.expect_download() as item:page.get_by_role('link',name='Full Directional list',exact=False).click()
                export=Path(item.value.path()).read_text()
                assert 'DEMO:DEMO' in export and 'NASDAQ:' not in export
                # Static downloads use literal backend-published lens files, even with no visible rows.
                page.locator('[data-candidate-lens="countertrend"]').click()
                published=page.evaluate("(window.THEMESCOPE_STATIC_SOURCE?.snapshot||window.FIXTURE_SNAPSHOT).research.countertrend.exports")
                assert published['available'] and published['side']=='long'
                page.locator('#candidate-search').fill('no-matching-research-ticker')
                for label,filename in [('All Countertrend','Countertrend.txt'),('Strong leaders','Strong-Leaders.txt'),('Underperforming theme peers','Relative-Weakness.txt')]:
                    open_exports(page)
                    with page.expect_download() as item:page.get_by_role('link',name=label,exact=True).click()
                    assert item.value.suggested_filename==filename
                    assert Path(item.value.path()).read_text()==published['files'][filename]
                    page.keyboard.press('Escape')
                page.locator('#candidate-search').fill('')
                page.locator('[data-candidate-lens="directional"]').click()
                nav('saved');expect(page.locator('#saved')).to_contain_text(ticker)
                page.reload();expect(page.locator('#saved')).to_contain_text(ticker)
                nav('methodology');expect(page.locator('#methodology-title')).to_be_visible()
                page.locator('#display-toggle').click();page.locator('#display-contrast').check();page.keyboard.press('Escape')
                assert page.evaluate("JSON.parse(localStorage.getItem('themescope-vnext-display')).contrast")
                nav('overview');page.locator('#theme-map-panel').evaluate('e=>e.open=true');page.locator('#map-selection').select_option('mixed');expect(page.locator('#map-readout')).to_contain_text('Mixed')
                artifacts=os.environ.get('THEMESCOPE_DEMO_ARTIFACTS')
                def capture(name):
                    if artifacts:
                        directory=Path(artifacts);directory.mkdir(parents=True,exist_ok=True)
                        page.screenshot(path=str(directory/(name+'.png')),full_page=True)
                capture('public-snapshot-overview' if public else 'static-demo-overview')
                axe_path=os.environ.get('THEMESCOPE_AXE_SCRIPT');audits={}
                def audit(name):
                    if axe_path:
                        page.evaluate(Path(axe_path).read_text())
                        findings=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>({id:v.id,targets:v.nodes.map(n=>n.target)}))}")
                        assert not findings,(name,findings);audits[name]=findings
                for destination in ('overview','themes','primary','saved','methodology'):
                    nav(destination);audit(destination)
                nav('themes');page.locator('#theme-filters [data-reset]').click();page.locator('#theme-table [data-inspect-theme]').first.click();audit('theme-inspector')
                page.locator('#inspector-members [data-inspect-ticker]').first.click();audit('ticker-inspector');page.keyboard.press('Escape')
                page.set_viewport_size({'width':390,'height':844})
                for destination in ('overview','themes','primary','saved','methodology'):
                    nav(destination);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),destination
                    if destination=='primary':capture('public-snapshot-primary-mobile' if public else 'static-demo-primary-mobile')
                audit('mobile-methodology')
                # Poll interval would have fired repeatedly if preview mode accidentally fell through.
                page.wait_for_timeout(1800)
                assert not errors,errors
                assert not external,external
                assert not api,api
                assert not failures,failures
                print(json.dumps({'static_demo':'passed','mode':'public snapshot (manufactured test input)' if public else 'synthetic demo','current_ui':True,'replay':'hidden' if public else 'fixture only',
                    'exports':'Directional + all three Countertrend files; full scope under empty UI filters; DEMO identifiers only','saved':'persisted browser-local',
                    'axe':audits,'external_requests':external,'api_requests':api,'page_console_errors':errors,'http_errors':failures},indent=2))
                browser.close()
        finally:server.shutdown();server.server_close();worker.join(5)


if __name__=='__main__':main()
