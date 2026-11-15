"""Current research workflow and responsive release gate; synthetic observations only."""
from copy import deepcopy
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT/'tests')]
from professional_ui_fixture import make,research_states
from test_research_v2_adversarial import fixture as contract_fixture
from src.themescope.storage import canonical


def main():
    from playwright.sync_api import sync_playwright, expect
    from src.themescope.local.app import create_app
    from scripts.build_cloudflare_demo import build
    import uvicorn

    output = Path(os.environ.get('THEMESCOPE_UI_ARTIFACTS', ROOT/'runtime/ui-v3-qa'))
    output.mkdir(parents=True, exist_ok=True)
    axe = Path(os.environ.get('THEMESCOPE_AXE_SCRIPT', ROOT/'runtime/ui-v3-tools/node_modules/axe-core/axe.min.js'))
    if not axe.is_file():
        raise RuntimeError('Install local axe-core or set THEMESCOPE_AXE_SCRIPT before this release gate')
    result = dict(data='Synthetic full-universe fixtures; manufactured UI changes; no live validation claim',
                  passed=False, workflows=[], responsive=[], axe={}, screenshots=[], performance={})
    with tempfile.TemporaryDirectory() as folder, patch('src.themescope.local.service.optional_earnings', return_value={}):
        fixture, base, short = make(folder)
        cases=research_states(fixture,base)
        assert set(cases)=={'Long bias','Selective long','Neutral','Selective short','Short bias','Unclassified'}
        assert len([t for t in base['themes'] if t['status']=='active']) == 44
        assert base['research_v2']['list']['stock_count'] >= 100
        state = dict(snapshot=deepcopy(base), connected=True, hold=True, pending=[], status=fixture.service.status())
        service = fixture.service
        service.snapshot = lambda: deepcopy(state['snapshot'])
        service.status = lambda: deepcopy(state['status'])
        def start():
            state['status'].update(state='running', progress='Fetching missing sessions and repair window')
        service.start = start
        sock = socket.socket(); sock.bind(('127.0.0.1', 0))
        origin = 'http://127.0.0.1:'+str(sock.getsockname()[1])
        server = uvicorn.Server(uvicorn.Config(create_app(ROOT, service), log_level='error', access_log=False))
        worker = threading.Thread(target=server.run, kwargs={'sockets':[sock]}, daemon=True); worker.start()
        try:
            deadline = time.monotonic()+10
            while not server.started and time.monotonic()<deadline:
                threading.Event().wait(.01)
            assert server.started
            with sync_playwright() as playwright:
                options = dict(headless=True)
                if shutil.which('chromium'): options['executable_path']=shutil.which('chromium')
                browser = playwright.chromium.launch(**options)
                page = browser.new_page(viewport=dict(width=1440,height=1000), reduced_motion='reduce')
                errors=[]; outside=[]
                page.on('pageerror', lambda e: errors.append(str(e)))
                page.on('request', lambda r: outside.append(r.url) if not r.url.startswith((origin,'blob:','data:')) else None)
                def dashboard(route):
                    if not state['connected']: route.abort('failed')
                    elif state['hold']: state['pending'].append(route)
                    else: route.fulfill(json=state['snapshot'])
                page.route('**/api/dashboard-data', dashboard)
                page.route('**/api/status', lambda r:r.fulfill(json=state['status']) if state['connected'] else r.abort('failed'))
                def capture(label):
                    page.screenshot(path=str(output/(label+'.png')), full_page=False)
                    result['screenshots'].append(label+'.png')
                def width_ok(label):
                    overflow = page.evaluate("""()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,
                        offenders:[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length&&!e.closest('[hidden]')&&e.getBoundingClientRect().right>innerWidth+1)
                        .slice(0,8).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().right])})""")
                    assert overflow['scroll']<=overflow['width'], (label,overflow)
                    if page.locator('#candidate-sort').is_visible():
                        assert page.locator('#candidate-sort').evaluate("""e=>{const c=document.createElement('canvas').getContext('2d');
                            c.font=getComputedStyle(e).font;return c.measureText(e.selectedOptions[0].textContent).width+32<=e.clientWidth}"""), ('Clipped research sort',label)
                def audit(label):
                    page.evaluate(axe.read_text(encoding='utf-8'))
                    findings=page.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});
                        return r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))}""")
                    result['axe'][label]=findings
                    assert not [v for v in findings if v['impact'] in ('serious','critical')], (label,findings)
                def nav(name):
                    page.locator(f'[data-nav="{name}"]').click()
                def reset():
                    page.locator('#candidate-filters [data-reset]').click()
                def update(snapshot):
                    state['snapshot']=deepcopy(snapshot)
                    state['snapshot']['refreshed_at']='Synthetic UI revision '+str(time.monotonic())
                    page.wait_for_timeout(1700)
                def close_inspector():
                    page.keyboard.press('Escape')
                    expect(page.locator('#research-inspector')).not_to_be_visible()
                def screenshot_surfaces(width):
                    page.set_viewport_size(dict(width=width,height=900 if width>=768 else 844))
                    for name in ('overview','themes','primary','saved','methodology'):
                        nav(name); width_ok(f'{name}-{width}'); capture(f'{name}-{width}')
                        if width in (1440,390):audit(f'{name}-{width}')
                        if name=='overview' and width<=430:
                            expect(page.locator('#market-brief')).to_be_visible()
                            assert not page.locator('.benchmark-details').evaluate('e=>e.open')
                        if name=='themes' and width<=430:
                            page.locator('.theme-filter-menu>summary').click()
                            page.locator('#theme-family').select_option(index=1)
                            expect(page.locator('.theme-filter-menu>summary')).to_have_text('Filters (1)')
                            page.locator('.theme-filter-menu>summary').click()
                            page.locator('#theme-filters [data-reset]').click()
                    page.goto(origin+'/#themes/semiconductors')
                    expect(page.locator('#detail-title')).to_contain_text('Semiconductors')
                    width_ok(f'detail-{width}');capture(f'detail-{width}')
                    if width in (1440,390):audit(f'detail-{width}')
                    nav('themes');page.locator('#theme-search').fill('semiconductors')
                    page.locator('#theme-table [data-inspect-theme]').first.click()
                    width_ok(f'theme-inspector-{width}');capture(f'theme-inspector-{width}')
                    if width in (1440,390):audit(f'theme-inspector-{width}')
                    page.locator('#inspector-members [data-inspect-ticker]').first.click()
                    width_ok(f'ticker-inspector-{width}');capture(f'ticker-inspector-{width}')
                    if width in (1440,390):audit(f'ticker-inspector-{width}')
                    close_inspector();page.locator('#theme-search').fill('')
                    result['responsive'].append(width)

                page.goto(origin, wait_until='domcontentloaded')
                expect(page.locator('#workspace')).to_have_attribute('aria-busy','true')
                expect(page.locator('.skeleton-market')).to_be_visible()
                capture('loading-1440')
                state['hold']=False
                for pending in state['pending']:pending.fulfill(json=state['snapshot'])
                expect(page.locator('#workspace')).to_have_attribute('aria-busy','false')
                expect(page.locator('#theme-table tbody tr')).to_have_count(44)
                assert 'Countertrend' not in page.locator('body').inner_text()
                result['workflows'].append('Layout-preserving initial loading, no removed lens')

                nav('themes')
                ranks=page.locator('[data-theme-row]').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.dataset.themeRow,e.querySelector('.canonical-rank').textContent]))")
                page.locator('[data-theme-sort="name"]').click()
                assert page.locator('[data-theme-row]').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.dataset.themeRow,e.querySelector('.canonical-rank').textContent]))")==ranks
                page.locator('#theme-search').fill('semiconductors')
                opener=page.locator('#theme-table [data-inspect-theme]').first
                opener.focus();page.keyboard.press('Enter')
                expect(page.locator('#inspector-title')).to_be_focused()
                page.locator('#inspector-view').select_option('Core');page.locator('#inspector-search').fill('NVDA')
                ticker=page.locator('#inspector-members [data-inspect-ticker="NVDA"]')
                ticker.click();expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme','semiconductors')
                page.go_back();expect(page.locator('#inspector-search')).to_have_value('NVDA');expect(ticker).to_be_focused()
                page.go_forward();expect(page.locator('#inspector-title')).to_have_text('NVDA')
                expect(page.locator('#research-inspector')).to_be_visible()
                expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme','semiconductors')
                result['focus_after_forward']=page.evaluate("({id:document.activeElement.id,tag:document.activeElement.tagName,open:document.querySelector('dialog').open})")
                page.keyboard.press('Tab')
                result['focus_after_tab']=page.evaluate("({id:document.activeElement.id,tag:document.activeElement.tagName})")
                page.keyboard.press('Shift+Tab')
                result['focus_after_shift_tab']=page.evaluate("({id:document.activeElement.id,tag:document.activeElement.tagName})")
                assert page.evaluate("document.activeElement.closest('dialog')!==null"),result
                close_inspector();expect(opener).to_be_focused();page.locator('#theme-search').fill('')
                result['workflows'].append('Canonical ranks; keyboard open/focus; nested Back/Forward; dialog containment and return focus')

                nav('primary')
                expect(page.locator('#candidate-results')).to_contain_text(str(base['research_v2']['list']['stock_count']))
                assert page.locator('#candidates [data-ticker-row]').count()==base['research_v2']['list']['stock_count']
                # Every peer sign belongs in the list; compare the actual rendered row set.
                rendered=page.locator('#candidates [data-ticker-row]').evaluate_all('els=>els.map(e=>e.dataset.tickerRow)')
                expected=list(dict.fromkeys(r['ticker'] for r in base['research_v2']['list']['rows']))
                assert rendered==expected
                page.locator('[data-candidate-mode="relationships"]').click()
                assert page.locator('#candidates [data-ticker-row]').count()==base['research_v2']['list']['relationship_count']
                page.locator('[data-candidate-mode="unique"]').click()
                selection=base['research_v2']['list']['rows'][0]
                page.locator('#candidate-theme').select_option(selection['theme_id'])
                page.locator('#candidate-search').fill(selection['ticker'])
                selected_row=page.locator('#candidates [data-ticker-row]').first
                selected_row.locator('[data-save]').click()
                assert page.locator('dialog[open]').count()==0
                selected_row.locator('[data-inspect-ticker]').click()
                expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme',selection['theme_id'])
                close_inspector()
                page.locator('#export-menu>summary').click()
                with page.expect_download() as download:
                    page.get_by_role('link',name='Full research list',exact=True).click()
                item=download.value
                assert item.suggested_filename=='Research.txt'
                assert Path(item.path()).read_text()==base['exports']['combined']
                page.locator('#export-menu').evaluate('e=>e.open=false')
                reset();page.locator('#candidate-sort').select_option('ticker')
                tickers=page.locator('#candidates [data-ticker-row]').evaluate_all('els=>els.map(e=>e.dataset.tickerRow)')
                assert tickers==sorted(tickers)
                page.locator('#candidate-sort').select_option('priority')
                start_time=time.perf_counter();page.locator('#candidate-search').fill('NVDA')
                expect(page.locator('#candidates [data-ticker-row]')).to_have_count(1)
                result['performance']['hundreds_row_filter_ms']=round((time.perf_counter()-start_time)*1000)
                assert result['performance']['hundreds_row_filter_ms']<1500
                reset();nav('saved');expect(page.locator('#saved')).to_contain_text(selection['ticker'])
                page.reload();expect(page.locator('#saved')).to_contain_text(selection['ticker'])
                assert selection['ticker'] in page.evaluate('JSON.parse(localStorage.getItem("themescope-vnext-watchlist"))')
                result['workflows'].append('Hundreds of rows; all eligible peers; grouping/filter/search/sort; exact full-session export; Saved persistence')

                update(short);nav('primary')
                assert page.locator('#candidates [data-ticker-row]').count()==short['research_v2']['list']['stock_count']
                short_order=page.locator('#candidates [data-ticker-row]').evaluate_all('els=>els.map(e=>e.dataset.tickerRow)')
                assert short_order==list(dict.fromkeys(r['ticker'] for r in short['research_v2']['list']['rows']))
                result['workflows'].append('Short side uses authoritative symmetric selection and peer order')
                for direction,data in cases.items():
                    update(data);nav('overview')
                    side=data['research_v2']['current_side']
                    if 'Selective' in direction:expect(page.locator('#market-direction')).to_contain_text('Reduced conviction')
                    if side is None:
                        expect(page.locator('#market-direction')).to_contain_text('No directional research list')
                        expect(page.locator('#change-board')).to_contain_text('No directional theme states')
                    nav('primary')
                    rendered=page.locator('#candidates [data-ticker-row]').evaluate_all('els=>els.map(e=>e.dataset.tickerRow)')
                    assert rendered==list(dict.fromkeys(r['ticker'] for r in data['research_v2']['list']['rows']))
                    nav('themes')
                    expected=[key for key in data['research_v2']['theme_order'] if data['research_v2']['themes'][key]['structural_score'] is not None]
                    actual=page.locator('[data-theme-row]').evaluate_all('els=>els.map(e=>e.dataset.themeRow)')
                    assert actual==expected,(direction,actual,expected)
                    if side is None:
                        assert page.locator('#theme-table .theme-state').all_text_contents()==['Non-directional']*44
                        page.locator('#theme-search').fill('semiconductors');page.locator('#theme-table [data-inspect-theme]').first.click()
                        page.locator('#inspector-search').fill('');page.locator('#inspector-view').select_option('All')
                        tickers=page.locator('#inspector-members [data-inspect-ticker]').evaluate_all('els=>els.map(e=>e.dataset.inspectTicker)')
                        assert tickers==sorted(tickers)
                        assert 'Long-side' not in page.locator('#inspector-content').inner_text()
                        page.locator('#inspector-members [data-inspect-ticker]').first.click()
                        expect(page.locator('#inspector-content')).to_contain_text('No directional research list')
                        close_inspector();page.locator('#theme-search').fill('')
                    if side=='short':
                        improving=next((key for key,row in data['research_v2']['themes'].items() if row['current_state']=='Improving'),None)
                        if improving:
                            recent=data['research_v2']['themes'][improving]['recent']
                            assert float(recent['raw_score_change'])<0<float(recent['directional_score_change'])
                            nav('overview');expect(page.locator('#change-board')).to_contain_text('Improving for Short research')
                    if direction in ('Short bias','Neutral','Selective long'):
                        for width in (1440,390):
                            page.set_viewport_size(dict(width=width,height=900 if width==1440 else 844))
                            for surface in ('overview','themes'):
                                nav(surface);width_ok(direction+'-'+surface);capture(direction.lower().replace(' ','-')+'-'+surface+'-'+str(width))
                            page.locator('#theme-table [data-inspect-theme]').first.click()
                            width_ok(direction+'-inspector');capture(direction.lower().replace(' ','-')+'-inspector-'+str(width))
                            close_inspector()
                        page.set_viewport_size(dict(width=1440,height=1000))
                for options,label in ((dict(target_index=67),'Not enough completed history'),
                                      (dict(missing='population'),'Scored theme universe changed'),
                                      (dict(missing='scores'),'Structural strength unavailable')):
                    data=json.loads(canonical(contract_fixture('Long Bias',**options)))
                    data['market']=deepcopy(base['market']);data['market']['decision']['direction']='Long Bias'
                    update(data);nav('overview');expect(page.locator('#change-board')).to_contain_text(label)
                    expect(page.locator('#change-board')).to_contain_text('Five-session comparison unavailable')
                    nav('themes');expect(page.locator('#theme-table')).to_contain_text(label)
                    page.set_viewport_size(dict(width=390,height=844));width_ok(label)
                    capture('unavailable-'+data['research_v2']['comparison']['reason']+'-390')
                    page.set_viewport_size(dict(width=1440,height=1000))
                result['workflows'].append('Six coherent backend states; Selective priority; non-directional alphabetical context and empty list; Short directional change; unavailable reasons')
                update(base)

                for width in (1920,1440,1280,768,430,390,360,320):
                    screenshot_surfaces(width)
                page.set_viewport_size(dict(width=390,height=844));nav('primary')
                small=page.locator('button:visible,select:visible,input:visible,a.button:visible').evaluate_all("els=>els.map(e=>({name:e.textContent||e.getAttribute('aria-label'),w:e.getBoundingClientRect().width,h:e.getBoundingClientRect().height})).filter(r=>r.w<40||r.h<40)")
                result['touch_targets_below40']=small
                assert not small,small
                page.locator('#display-toggle').click()
                audit('display-390')
                page.locator('#display-contrast').check()
                audit('display-high-contrast-390')
                page.locator('#display-contrast').uncheck()
                for _ in range(4):page.locator('[data-text-step="25"]').click()
                expect(page.locator('#text-size')).to_have_text('200%');page.keyboard.press('Escape')
                for name in ('overview','themes','primary','saved','methodology'):
                    nav(name);width_ok('text200-'+name)
                # Enlarged text must keep every destination separate and actionable.
                assert page.locator('.main-nav a').evaluate_all("""es=>es.every((a,i)=>es.slice(i+1).every(b=>{
                    const x=a.getBoundingClientRect(),y=b.getBoundingClientRect();
                    return x.right<=y.left+1||y.right<=x.left+1||x.bottom<=y.top+1||y.bottom<=x.top+1;
                }))""")
                capture('text200-390');audit('text200-390')
                page.locator('#display-toggle').click()
                for _ in range(4):page.locator('[data-text-step="-25"]').click()
                page.keyboard.press('Escape')
                # A 1440px browser at 200% has a 720 CSS-pixel layout viewport.
                page.set_viewport_size(dict(width=720,height=500));nav('primary');width_ok('zoom200-layout')
                page.evaluate("document.documentElement.style.zoom='2'");width_ok('css-zoom200');capture('zoom200-720')
                page.evaluate("document.documentElement.style.zoom=''")
                result['workflows'].append('All device widths; touch targets;200% text;200% browser-layout/reflow and CSS zoom')

                page.set_viewport_size(dict(width=1440,height=1000));page.emulate_media(reduced_motion='no-preference')
                nav('overview');nav('primary')
                result['motion']=page.evaluate("({reduced:matchMedia('(prefers-reduced-motion: reduce)').matches,animationCount:document.getAnimations().length})")
                page.emulate_media(reduced_motion='reduce')
                nav('themes');assert page.evaluate("document.getAnimations().every(a=>a.playState!=='running')")
                result['workflows'].append('Normal and reduced motion keep navigation usable')
                nav('overview');page.locator('#refresh').click()
                expect(page.locator('#progress')).to_contain_text('Fetching missing sessions',timeout=6000)
                expect(page.locator('#refresh')).to_be_disabled()
                state['status'].update(state='success',progress='Refresh complete')
                expect(page.locator('#refresh')).to_be_enabled(timeout=6000)
                state['connected']=False
                expect(page.locator('#progress')).to_contain_text('Connection lost',timeout=6000)
                nav('themes');expect(page.locator('#theme-table tbody tr')).to_have_count(44)
                capture('connection-error-1440');state['connected']=True
                expect(page.locator('#progress')).not_to_contain_text('Connection lost',timeout=6000)
                neutral=cases['Neutral']
                update(neutral);nav('primary');expect(page.locator('#candidates [data-ticker-row]')).to_have_count(0)
                capture('empty-neutral-1440');audit('empty-neutral')
                update(base)
                result['workflows'].append('Real same-origin refresh action/progression; errors preserve completed snapshot; neutral empty list')
                assert not errors,errors
                assert not outside,outside
                result['page_errors']=errors;result['external_requests']=outside
                old=deepcopy(base);old.pop('research_v2')
                update(old);nav('primary')
                expect(page.locator('#research-version-notice')).to_be_visible()
                expect(page.locator('#candidates')).to_contain_text('Research update required')
                expect(page.locator('#candidate-results')).to_have_text('Current research list unavailable')
                nav('saved');expect(page.locator('#saved')).to_contain_text(selection['ticker'])
                nav('themes');expect(page.locator('#theme-table tbody tr')).to_have_count(44)
                update(base)
                result['workflows'].append('Previous-rules snapshot is explicitly unavailable for current selection; context and Saved retained')

                build(ROOT)
                class QuietHandler(SimpleHTTPRequestHandler):
                    def log_message(self,*args):pass
                static=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=str(ROOT/'dist/cloudflare-pages')))
                static_worker=threading.Thread(target=static.serve_forever,daemon=True);static_worker.start()
                try:
                    frozen=browser.new_page(viewport=dict(width=390,height=844));calls=[]
                    frozen.on('request',lambda r:calls.append(r.url) if '/api/' in r.url else None)
                    frozen.goto('http://127.0.0.1:'+str(static.server_port))
                    expect(frozen.locator('#workspace')).to_have_attribute('aria-busy','false')
                    expect(frozen.locator('#refresh')).to_contain_text('Replay fixture')
                    frozen.locator('#refresh').click()
                    frozen.locator('[data-nav="primary"]').click()
                    assert frozen.locator('#candidates [data-ticker-row]').count()>0
                    assert not calls,calls
                    frozen.screenshot(path=str(output/'static-readonly-390.png'))
                    result['workflows'].append('Synthetic static build uses identical UI without API requests or refresh')
                    frozen.close()
                    public=browser.new_page(viewport=dict(width=390,height=844));calls=[]
                    public.add_init_script('window.THEMESCOPE_STATIC_SOURCE='+json.dumps(dict(mode='public_snapshot',snapshot=base)))
                    public.on('request',lambda r:calls.append(r.url) if '/api/' in r.url else None)
                    public.goto('http://127.0.0.1:'+str(static.server_port))
                    expect(public.locator('#workspace')).to_have_attribute('aria-busy','false')
                    expect(public.locator('#refresh')).to_be_hidden()
                    assert not calls,calls
                    public.close()
                    result['workflows'].append('Frozen public mode hides refresh and makes no API request; fabricated fixture data only')
                finally:static.shutdown();static.server_close();static_worker.join(timeout=5)
                browser.close()
                result['passed']=True
        finally:
            server.should_exit=True;worker.join(timeout=10);sock.close()
            (output/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
