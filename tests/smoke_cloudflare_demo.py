"""Current static UI over HTTP with real security headers and manufactured data."""
from functools import partial
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from unittest.mock import patch
import json
import os
import shutil
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.build_cloudflare_demo import build, ASSETS
from scripts.static_pages import copy_fonts


def main(public=False):
    from playwright.sync_api import sync_playwright, expect
    with tempfile.TemporaryDirectory() as folder:
        root=Path(folder);assets=root/'static/vnext';assets.mkdir(parents=True)
        for name in ASSETS:shutil.copyfile(ROOT/'static/vnext'/name,assets/name)
        copy_fonts(ROOT,root/'static')
        if public:
            from public_snapshot_support import public_contract_fixture
            from scripts import build_public_snapshot
            source=public_contract_fixture()
            with patch.object(build_public_snapshot,'fetch_snapshot',return_value=source):
                output=build_public_snapshot.build(source['session'],root)
        else:output=build(root)
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
                options=dict(headless=True)
                if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport=dict(width=1440,height=1000),reduced_motion='reduce')
                errors=[];external=[];api=[];failures=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
                page.on('response',lambda r:failures.append(r.url) if r.status>=400 else None)
                def request(r):
                    if not r.url.startswith((origin,'blob:')):external.append(r.url)
                    if r.url.startswith(origin+'/api/'):api.append(r.url)
                page.on('request',request)
                page.goto(origin)
                expect(page.locator('#workspace')).to_have_attribute('aria-busy','false')
                source=page.evaluate('(window.THEMESCOPE_STATIC_SOURCE?.snapshot||window.FIXTURE_SNAPSHOT)')
                if public:
                    expect(page.locator('#public-banner')).to_contain_text(source['session'])
                    expect(page.locator('#fixture-banner')).to_be_hidden()
                    expect(page.locator('#refresh')).to_be_hidden()
                    expect(page.locator('#progress')).to_have_text('Market data fixed')
                    page.locator('#refresh').evaluate('button=>button.click()')
                else:
                    expect(page.locator('#fixture-banner')).to_be_visible()
                    page.get_by_label('Snapshot and refresh',exact=True).click()
                    page.locator('#refresh').click()
                    expect(page.locator('#progress')).to_have_text('Synthetic fixture replayed')
                    page.get_by_label('Snapshot and refresh',exact=True).click()
                def nav(name):page.locator(f'[data-nav="{name}"]').click()
                nav('themes');page.locator('#theme-search').fill('alpha')
                expect(page.locator('#theme-table [data-theme-row]')).to_have_count(1)
                page.locator('#theme-table [data-inspect-theme]').first.click()
                expect(page.locator('#inspector-kind')).to_have_text('Theme research')
                page.locator('#inspector-members [data-inspect-ticker]').first.click()
                expect(page.locator('#inspector-kind')).to_have_text('Ticker research')
                page.go_back();expect(page.locator('#inspector-kind')).to_have_text('Theme research')
                page.go_forward();expect(page.locator('#inspector-kind')).to_have_text('Ticker research')
                page.keyboard.press('Escape');expect(page.locator('#theme-search')).to_have_value('alpha')
                nav('primary')
                expect(page.locator('#candidates [data-ticker-row]')).to_have_count(source['research_v2']['list']['stock_count'])
                save=page.locator('#candidates [data-save]').first;ticker=save.get_attribute('data-save');save.click()
                page.locator('#candidate-search').fill('no-matching-ticker')
                expect(page.locator('#candidate-results')).to_have_text('0 stocks')
                page.locator('#export-menu>summary').click()
                with page.expect_download() as item:page.locator('#combined').click()
                assert Path(item.value.path()).read_text()==source['exports']['combined']
                page.locator('#candidate-search').fill('')
                page.locator('#export-menu>summary').click();page.locator('.theme-files>summary').click()
                for index,text in enumerate(source['exports']['individual'].values()):
                    if not page.locator('#export-menu').evaluate('e=>e.open'):page.locator('#export-menu>summary').click()
                    with page.expect_download() as item:page.locator('.theme-files [download]').nth(index).click()
                    assert Path(item.value.path()).read_text()==text
                nav('saved');expect(page.locator('#saved')).to_contain_text(ticker)
                page.reload();expect(page.locator('#saved')).to_contain_text(ticker)
                axe=Path(os.environ.get('THEMESCOPE_AXE_SCRIPT',ROOT/'runtime/ui-v3-tools/node_modules/axe-core/axe.min.js'))
                audits={}
                for width in (1440,390):
                    page.set_viewport_size(dict(width=width,height=1000 if width==1440 else 844))
                    for destination in ('overview','themes','primary','saved','methodology'):
                        nav(destination)
                        page.wait_for_function('document.documentElement.scrollWidth<=innerWidth')
                        if axe.is_file():
                            page.evaluate(axe.read_text(encoding='utf-8'))
                            findings=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>v.id)}")
                            assert not findings,(destination,width,findings)
                            audits[f'{destination}-{width}']=findings
                page.wait_for_timeout(1800)
                assert not errors,errors
                assert not external,external
                assert not api,api
                assert not failures,failures
                browser.close()
                print(json.dumps(dict(passed=True,mode='manufactured public contract' if public else 'synthetic demo',
                    exports='full combined scope and every theme file match',saved='persisted browser-local',
                    history='nested Back/Forward passed',axe=audits,external_requests=external,api_requests=api,
                    page_errors=errors,http_errors=failures),indent=2))
        finally:server.shutdown();server.server_close();worker.join(5)


if __name__=='__main__':main()
