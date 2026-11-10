"""Tidal Vector: column anchors, grouped context, spatial motion and detail reflow.

Deterministic fixture bars only; no live chronology or deployment evidence.
"""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json,os,shutil,socket,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from professional_ui_fixture import make

@contextmanager
def fixture_app():
    from src.themescope.local.app import create_app
    import uvicorn
    with tempfile.TemporaryDirectory() as folder,patch('src.themescope.local.service.optional_earnings',return_value={}):
        f,base,short=make(folder);state={'data':base};f.service.snapshot=lambda:deepcopy(state['data'])
        sock=socket.socket();sock.bind(('127.0.0.1',0));origin='http://127.0.0.1:'+str(sock.getsockname()[1])
        server=uvicorn.Server(uvicorn.Config(create_app(ROOT,f.service),log_level='error',access_log=False))
        thread=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);thread.start()
        try:
            limit=time.monotonic()+5
            while not server.started and time.monotonic()<limit:threading.Event().wait(.01)
            assert server.started
            yield origin,state,base,short
        finally:server.should_exit=True;thread.join(5);sock.close()


def main():
    from playwright.sync_api import sync_playwright,expect
    out=Path(os.environ.get('THEMESCOPE_UI_ARTIFACTS','/tmp/themescope-identity-review'));out.mkdir(parents=True,exist_ok=True)
    result={'fixture':'Deterministic test input, not live data or Gate E evidence','axe':{},'responsive':[],'interactions':[]}
    with fixture_app() as (origin,state,base,short),sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True)
        page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='no-preference')
        errors=[];outside=[];page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('request',lambda r:outside.append(r.url) if not r.url.startswith((origin,'blob:')) else None)
        page.add_init_script("""addEventListener('DOMContentLoaded',()=>{const s=document.createElement('p');s.dataset.testStamp='';s.textContent='Tidal Vector review · deterministic fixtures · not live';s.style.cssText='position:fixed;bottom:8px;right:12px;max-width:calc(100vw - 24px);font:11px system-ui;background:#07111f;color:#afc3d5;padding:4px 8px;z-index:99;pointer-events:none';document.body.append(s)})""")
        def capture(name):
            page.evaluate("()=>{const d=document.querySelector('dialog[open]');if(d&&!d.querySelector('[data-test-stamp]'))d.append(document.querySelector('[data-test-stamp]').cloneNode(true));}")
            page.screenshot(path=str(out/(name+'.png')))
        def audit(name):
            script=os.environ.get('THEMESCOPE_AXE_SCRIPT')
            if script:
                page.evaluate(Path(script).read_text());violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,why:n.failureSummary}))}))}")
                result['axe'][name]=violations;assert not violations,(name,violations)
        def nav(name):page.locator('[data-nav="'+name+'"]').click()
        def settle():page.wait_for_timeout(270)
        def fit(label):assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),label
        def anchors(selector):
            data=page.locator(selector).evaluate("t=>{const h=[...t.querySelectorAll('th')].filter(e=>e.getClientRects().length);return [...t.querySelectorAll('tbody tr')].slice(0,12).every(row=>{const c=[...row.cells].filter(e=>e.getClientRects().length);return c.length===h.length&&c.every((e,i)=>{const a=e.getBoundingClientRect(),b=h[i].getBoundingClientRect();return Math.abs(a.left-b.left)<1&&Math.abs(a.right-b.right)<1})})}")
            assert data,selector
        page.goto(origin);expect(page.locator('#workspace')).to_have_attribute('aria-busy','false');page.evaluate('document.fonts.ready');capture('overview');audit('overview')
        # Selection travel must survive repeated observer callbacks and settle to the latest destination.
        page.evaluate("document.querySelector('[data-nav=themes]').click()")
        page.wait_for_function("document.querySelector('.main-nav>.selection-indicator').getAnimations().some(a=>a.playState==='running')",polling='raf')
        page.wait_for_timeout(45);assert page.locator('.main-nav>.selection-indicator').evaluate("e=>e.getAnimations().some(a=>a.playState==='running')");capture('navigation-travel')
        page.evaluate("document.querySelector('[data-nav=saved]').click();document.querySelector('[data-nav=themes]').click()")
        settle();expect(page.locator('[data-nav=themes]')).to_have_attribute('aria-current','page')
        assert page.locator('.main-nav>.selection-indicator').evaluate("e=>{const a=e.getBoundingClientRect(),b=document.querySelector('[aria-current=page]').getBoundingClientRect();return Math.abs(a.top-b.top)<1&&Math.abs(a.height-b.height)<1}")
        capture('themes');audit('themes');anchors('#theme-table table')
        # Normal numbers are secondary, selected identities primary.
        colors=page.evaluate("()=>{const r=getComputedStyle(document.documentElement);return ['--text','--secondary','--muted','--unavailable'].map(k=>r.getPropertyValue(k).trim())}");assert len(set(colors))==4
        page.locator('#theme-table [data-inspect-theme=semiconductors]').click();settle();capture('theme-inspector');audit('theme-inspector')
        expect(page.locator('#inspector-back')).to_be_hidden()
        page.locator('#inspector-search').fill('NVDA');page.locator('#inspector-members [data-inspect-ticker=NVDA]').click();settle();capture('ticker-inspector');audit('ticker-inspector')
        expect(page.locator('#inspector-back')).to_be_visible();page.locator('#inspector-back').click();expect(page.locator('#inspector-search')).to_have_value('NVDA');expect(page.locator('#inspector-members [data-inspect-ticker=NVDA]')).to_be_focused()
        page.get_by_role('link',name='Open full theme',exact=True).click();settle();capture('theme-detail');audit('theme-detail')
        expect(page.locator('.detail-primary .metric-block')).to_have_count(4);expect(page.locator('.detail-summary .metric-block')).to_have_count(4)
        for width in (1440,1024,768):
            page.set_viewport_size({'width':width,'height':1000});nav('themes');settle();anchors('#theme-table table');fit(('themes',width))
            assert page.locator('#theme-table table').evaluate('e=>getComputedStyle(e).display')=='table'
        page.set_viewport_size({'width':1440,'height':1000});nav('primary');page.locator('#directional-tab').click();settle();capture('directional');audit('directional');anchors('#candidates table')
        # Grouping removes only redundant cells, never relationships/context/exports.
        page.locator('[data-candidate-mode=relationships]').click();settle();capture('grouped-directional');audit('grouped-directional')
        assert page.locator('#candidates .col-theme').count()==0
        assert page.locator('#candidates tbody tr').count()==sum(r['qualifies'] for r in base['relationships'])
        candidate=page.locator('#candidates [data-inspect-ticker]').first;context=candidate.get_attribute('data-context-theme');candidate.click();expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme',context);page.keyboard.press('Escape')
        # Market context continues to say Short while the explicitly labelled lens is Countertrend.
        state['data']=short;page.reload();page.locator('#countertrend-tab').click();settle();capture('countertrend');audit('countertrend')
        expect(page.locator('#primary-context')).to_contain_text('Market Short bias');expect(page.locator('.lens-controls')).to_contain_text('Research lens');expect(page.locator('#countertrend-tab')).to_have_attribute('aria-selected','true')
        page.locator('[data-candidate-mode=relationships]').click();settle();capture('grouped-countertrend');audit('grouped-countertrend');assert page.locator('#candidates .col-theme').count()==0
        page.locator('#candidates [data-save]').first.click();nav('saved');settle();capture('saved');audit('saved')
        nav('primary');page.locator('#export-menu>summary').click();settle();capture('export-menu');audit('export-menu');page.keyboard.press('Escape')
        nav('overview');page.locator('#theme-map-panel>summary').click();page.locator('#theme-map-panel').scroll_into_view_if_needed();page.locator('#map-selection').select_option('semiconductors');settle();capture('map-selected');audit('map-selected')
        expect(page.locator('[data-map-theme][tabindex="0"]')).to_have_count(1)
        nav('methodology');page.locator('#method-w>summary').click();settle();capture('methodology');audit('methodology')
        page.locator('#display-toggle').click();capture('display');page.locator('#display-contrast').check();page.keyboard.press('Escape');nav('themes');settle();capture('high-contrast');audit('high-contrast')
        # OS and explicit user motion preferences remove spatial work rather than shorten it.
        page.emulate_media(reduced_motion='reduce');nav('primary');page.locator('#directional-tab').click();assert not page.locator('#candidate-panel').evaluate('e=>e.getAnimations().some(a=>a.playState==="running")');capture('reduced-motion')
        page.emulate_media(reduced_motion='no-preference');page.locator('#display-toggle').click();page.locator('#display-motion').check();page.locator('#display-contrast').uncheck();page.keyboard.press('Escape')
        for width in (1440,1024,768,480,320):
            page.set_viewport_size({'width':width,'height':1000 if width>=768 else 844})
            for scale in (100,200):
                page.locator('#display-toggle').click()
                while int(page.locator('#text-size').inner_text().strip('%'))!=scale:page.locator('[data-text-step="'+('25' if scale==200 else '-25')+'"]').click()
                page.keyboard.press('Escape')
                nav('themes');page.locator('#theme-table [data-inspect-theme=semiconductors]').click();page.get_by_role('link',name='Open full theme',exact=True).click();fit(('detail',width,scale));capture(f'detail-{width}-{scale}')
                if width<=480 or scale==200:
                    page.locator('.detail-primary').scroll_into_view_if_needed();capture(f'detail-metrics-{width}-{scale}')
                nav('primary');page.locator('#countertrend-tab').click();page.locator('[data-candidate-mode=relationships]').click();fit(('grouped',width,scale));capture(f'grouped-{width}-{scale}')
                if width<=480 or scale==200:
                    page.locator('#candidates .group-heading').first.scroll_into_view_if_needed();capture(f'grouped-results-{width}-{scale}')
                if width in (768,320):audit(f'grouped-{width}-{scale}')
                result['responsive'].append({'width':width,'text':scale,'detail_and_grouped':'pass'})
        assert not errors,errors;assert not outside,outside
        result.update(passed=True,page_errors=errors,external_requests=outside,interactions=['persistent selected plane and interruption','column anchors and four tone levels','nested Back control/focus','four primary/four secondary detail metrics','grouped context/counts retained without Theme cells','market regime distinct from research lens','OS/user reduced motion','single map tab stop'])
        (out/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));browser.close()

if __name__=='__main__':main()
