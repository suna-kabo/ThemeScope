"""Workflow, context, export and responsive acceptance over fixture-only loopback."""
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch
import json,os,shutil,socket,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from professional_ui_fixture import make


def main():
    from playwright.sync_api import sync_playwright,expect
    from src.themescope.local.app import create_app
    import uvicorn
    output=Path(os.environ.get('THEMESCOPE_UI_ARTIFACTS','/tmp/themescope-professional-review'));output.mkdir(parents=True,exist_ok=True)
    result={'data':'Deterministic fixtures and manufactured UI states, not live Gate E evidence','workflows':[],'axe':{},'responsive':[]}
    with tempfile.TemporaryDirectory() as folder,patch('src.themescope.local.service.optional_earnings',return_value={}):
        fixture,base,short=make(folder);service=fixture.service
        state={'snapshot':deepcopy(base),'connected':True,'hold':True,'pending':[]}
        status=service.status();service.snapshot=lambda:deepcopy(state['snapshot'])
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];origin=f'http://127.0.0.1:{port}'
        server=uvicorn.Server(uvicorn.Config(create_app(ROOT,service),log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+5
            while not server.started and time.monotonic()<deadline:threading.Event().wait(.01)
            assert server.started
            with sync_playwright() as p:
                options={'headless':True}
                if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                browser=p.chromium.launch(**options);page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                errors=[];outside=[];http=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:outside.append(r.url) if not r.url.startswith((origin,'blob:')) else None)
                page.on('response',lambda r:http.append(r.url) if r.status>=400 and not r.url.endswith('/favicon.ico') else None)
                def dashboard(route):
                    if not state['connected']:route.abort('failed')
                    elif state['hold']:state['pending'].append(route)
                    else:route.fulfill(json=state['snapshot'])
                page.route('**/api/dashboard-data',dashboard)
                page.route('**/api/status',lambda r:r.fulfill(json=status) if state['connected'] else r.abort('failed'))
                page.add_init_script("""addEventListener('DOMContentLoaded',()=>{const e=document.createElement('p');e.textContent='UI review · deterministic fixture · not live';e.dataset.testStamp='';e.style.cssText='position:fixed;right:8px;bottom:6px;z-index:99;background:#191724;color:#eee;padding:4px 8px;border:1px solid #8a7e98;font:11px system-ui;max-width:calc(100vw - 16px);pointer-events:none';document.body.append(e);});""")
                def capture(label):
                    page.evaluate("()=>{const d=document.querySelector('dialog[open]');if(d&&!d.querySelector('[data-test-stamp]'))d.append(document.querySelector('[data-test-stamp]').cloneNode(true));}")
                    page.screenshot(path=str(output/(label+'.png')),full_page=False)
                def audit(label):
                    source=os.environ.get('THEMESCOPE_AXE_SCRIPT')
                    if source:
                        page.evaluate(Path(source).read_text())
                        rows=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))}")
                        result['axe'][label]=rows;assert not rows,(label,rows)
                def nav(name):page.locator(f'[data-nav="{name}"]').click()
                def lens(name):page.locator(f'[data-candidate-lens="{name}"]').click()
                def menu():
                    if not page.locator('#export-menu').evaluate('e=>e.open'):page.locator('#export-menu>summary').click()
                def download(label,expected,filename):
                    menu()
                    with page.expect_download() as event:page.get_by_role('link',name=label,exact=True).click()
                    item=event.value;assert item.suggested_filename==filename
                    assert Path(item.path()).read_text()==expected
                    page.locator('#export-menu').evaluate('e=>e.open=false')
                def update(data):
                    state['snapshot']=deepcopy(data);state['snapshot']['refreshed_at']='UI fixture revision '+str(time.monotonic());page.wait_for_timeout(1700)
                def width_ok(label):
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(label,page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length&&!e.closest('[hidden]')&&e.getBoundingClientRect().right>innerWidth+1).slice(0,12).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().right])"))
                page.goto(origin,wait_until='domcontentloaded')
                expect(page.locator('#workspace')).to_have_attribute('aria-busy','true')
                expect(page.locator('#candidates')).to_contain_text('Loading candidates')
                assert 'No Directional stocks' not in page.locator('body').inner_text()
                state['hold']=False
                for pending in state['pending']:pending.fulfill(json=state['snapshot'])
                expect(page.locator('#workspace')).to_have_attribute('aria-busy','false')
                expect(page.locator('#theme-table tbody tr')).to_have_count(44)
                page.evaluate('document.fonts.ready');assert page.evaluate('document.fonts.check(\'14px "ThemeScope Inter"\')')
                assert page.locator('#primary-count').count()==0
                capture('overview-1440');audit('overview')
                nav('themes');capture('themes-1440');audit('themes')
                assert page.locator('#theme-table table').evaluate('e=>getComputedStyle(e).display')=='table'
                ranks=page.locator('[data-theme-row]').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.dataset.themeRow,e.cells[0].innerText]))")
                page.locator('[data-theme-sort="name"]').click()
                assert page.locator('[data-theme-row]').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.dataset.themeRow,e.cells[0].innerText]))")==ranks
                result['workflows'].append('A: context to cross-theme comparison, canonical ranks stable')
                page.locator('#theme-search').fill('semiconductors');opener=page.locator('#theme-table [data-inspect-theme]').first;opener.click()
                page.locator('#inspector-view').select_option('Core');page.locator('#inspector-search').fill('NVDA');capture('theme-inspector');audit('theme-inspector')
                page.locator('#inspector-members [data-inspect-ticker="NVDA"]').click();expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme','semiconductors')
                capture('ticker-inspector');audit('ticker-inspector')
                page.go_back();expect(page.locator('#inspector-view')).to_have_value('Core');expect(page.locator('#inspector-search')).to_have_value('NVDA');expect(page.locator('#inspector-members [data-inspect-ticker="NVDA"]')).to_be_focused()
                page.keyboard.press('Escape');expect(opener).to_be_focused();page.locator('#theme-search').fill('')
                result['workflows'].append('B: nested Back preserves theme, view/search/scroll/focus')
                # Selected-theme display must replace a different export representative.
                nav('primary');lens('directional');capture('directional-1440');audit('directional')
                choices=[r for r in base['relationships'] if r['qualifies'] and r['assigned_section']!=r['theme_id']]
                assert choices,'fixture needs independently qualifying multi-theme rows'
                row=next((r for r in choices if any(other['ticker']==r['ticker'] and other['qualifies'] and other['role']!=r['role'] for other in base['relationships'])),choices[0])
                page.locator('#candidate-theme').select_option(row['theme_id']);page.locator('#candidate-sort').select_option('w-desc')
                visible=page.locator('#candidates tr').filter(has=page.locator(f'[data-inspect-ticker="{row["ticker"]}"]'))
                expect(visible.locator('[data-inspect-theme]')).to_have_attribute('data-inspect-theme',row['theme_id'])
                expect(visible.locator('td[data-label="Role"]')).to_have_text('Core business' if row['role']=='Core' else 'Supporting business')
                expect(visible.locator('td[data-label="W"]')).to_have_text(f'{D(row["relative"]["w"])*100:+.2f} pp')
                w=page.locator('#candidates td[data-label="W"]').all_text_contents();numbers=[float(v.replace(' pp','').replace(',','')) for v in w];assert numbers==sorted(numbers,reverse=True)
                capture('selected-theme-context');audit('selected-theme-context')
                visible.locator('[data-save]').click();assert page.locator('dialog[open]').count()==0
                visible.locator('[data-inspect-ticker]').click();expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme',row['theme_id']);expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-w',row['relative']['w'])
                page.keyboard.press('Escape');download('Full Directional list',base['exports']['combined'],'Primary.txt')
                result['workflows'].extend(['C: selected Theme/Role/W and W ordering match relationship; inspector starts there','E/H: Directional bytes unchanged under filters'])
                nav('saved');expect(page.locator('#saved')).to_contain_text(row['ticker']);expect(page.locator('#saved')).to_contain_text(next(t['name'] for t in base['themes'] if t['theme_id']==row['theme_id']));capture('saved');audit('saved')
                page.reload();expect(page.locator('#saved')).to_contain_text(row['ticker']);assert page.evaluate('JSON.parse(localStorage.getItem("themescope-vnext-watchlist")).length')==1
                result['workflows'].append('I: original Saved key/persistence plus selected relationship context')
                update(short);nav('primary');lens('countertrend');page.locator('#candidate-filters [data-reset]').click()
                expect(page.locator('#candidates')).to_contain_text('Peer outperformers');expect(page.locator('#candidates')).to_contain_text('Weak-theme laggards')
                capture('countertrend-1440');audit('countertrend')
                menu();capture('countertrend-export-menu');audit('export-menu');page.keyboard.press('Escape')
                files=short['research']['countertrend']['exports']['files']
                for label,file in [('All Countertrend','Countertrend.txt'),('Peer outperformers','Resilient.txt'),('Weak-theme laggards','Snapback.txt')]:download(label,files[file],file)
                assert len(files['Countertrend.txt'].splitlines())==len(set(files['Countertrend.txt'].splitlines()))
                ct=short['research']['countertrend'];chosen=None
                for bucket in ct['buckets'].values():
                    reps={r['ticker']:r['theme_id'] for r in bucket['stocks']}
                    chosen=next((r for r in bucket['rows'] if reps[r['ticker']]!=r['theme_id']),None)
                    if chosen:break
                assert chosen
                page.locator('#candidate-theme').select_option(chosen['theme_id'])
                rows=page.locator('#candidates tr').filter(has=page.locator(f'[data-inspect-ticker="{chosen["ticker"]}"]'))
                for current in rows.all():expect(current.locator('[data-inspect-theme]')).to_have_attribute('data-inspect-theme',chosen['theme_id'])
                rows.first.locator('[data-inspect-ticker]').click();expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme',chosen['theme_id']);page.keyboard.press('Escape')
                page.locator('#candidate-search').fill(chosen['ticker']);download('All Countertrend',files['Countertrend.txt'],'Countertrend.txt')
                page.locator('#candidate-filters [data-reset]').click();page.locator('[data-candidate-mode="relationships"]').click();assert page.locator('.qualification-group').count()>1
                page.locator('[data-countertrend-jump="snapback"]').click();capture('countertrend-laggards');page.locator('[data-candidate-mode="unique"]').click()
                result['workflows'].extend(['D: both Countertrend groups and relationship view','F/G/H: combined/bucket exact sets, dedup and full-lens export under filters','C-countertrend: selected theme replaces a different representative'])
                # Keyboard help links are real navigation, with stable methodology anchors.
                page.locator('#candidates [data-help="w"]').first.focus();page.keyboard.press('Enter');expect(page.locator('#metric-tooltip')).to_be_visible();expect(page.locator('#metric-tooltip')).to_be_focused();audit('metric-help')
                page.keyboard.press('Tab');expect(page.locator('#metric-tooltip a')).to_be_focused();page.keyboard.press('Enter');expect(page.locator('#method-w')).to_have_attribute('open','');capture('methodology');audit('methodology')
                nav('themes');state['connected']=False;expect(page.locator('#progress')).to_have_text('Connection lost · showing completed session '+short['session'],timeout=6000);expect(page.locator('#theme-table tbody tr')).to_have_count(44);capture('connection-lost');state['connected']=True;expect(page.locator('#progress')).to_have_text('Refresh complete',timeout=6000)
                result['workflows'].append('J: connection loss retains last completed session and all research')
                nav('overview');page.locator('#theme-map-panel>summary').click();expect(page.locator('[data-map-theme][tabindex="0"]')).to_have_count(1)
                point=page.locator('[data-map-theme]').first;point.focus();page.keyboard.press('ArrowRight');expect(page.locator('[data-map-theme][tabindex="0"]')).to_have_count(1);page.keyboard.press('Enter');assert page.locator('dialog[open]').count()==0
                page.locator('#map-readout [data-inspect-theme]').click();expect(page.locator('dialog[open]')).to_have_count(1);page.keyboard.press('Escape');page.locator('#theme-map-panel>summary').click()
                result['workflows'].append('Map: readable ticks, roving point focus, selection separate from research')
                # Both lens file sets are available on their proper published side.
                update(base);nav('primary');lens('countertrend')
                for label,file in [('All Countertrend','Countertrend.txt'),('Strong leaders','Strong-Leaders.txt'),('Underperforming theme peers','Relative-Weakness.txt')]:download(label,base['research']['countertrend']['exports']['files'][file],file)
                capture('long-countertrend');result['workflows'].append('Long-bias filenames and observational labels')
                # Native tabs retain arrow-key semantics; only explicit state changes animate.
                page.emulate_media(reduced_motion='no-preference')
                page.locator('#display-toggle').click();page.locator('#display-motion').uncheck();page.keyboard.press('Escape')
                page.locator('#directional-tab').focus();page.keyboard.press('ArrowRight');expect(page.locator('#countertrend-tab')).to_be_focused()
                page.keyboard.press('Home');expect(page.locator('#directional-tab')).to_be_focused();expect(page.locator('#directional-tab')).to_have_attribute('aria-selected','true')
                page.locator('#countertrend-tab').click()
                page.wait_for_function("document.querySelector('.research-tabs .selection-indicator').getAnimations().some(a=>a.effect.getTiming().duration===200)",polling='raf')
                assert page.evaluate("()=>{document.querySelector('#directional-tab').click();return document.querySelector('#candidate-panel').getAnimations().some(a=>a.effect.getTiming().duration===200)}")
                page.locator('#display-toggle').click();page.locator('#display-motion').check();page.keyboard.press('Escape')
                assert page.evaluate("document.getAnimations().every(a=>a.playState!=='running')")
                page.emulate_media(reduced_motion='reduce')
                ids=page.locator('[id]').evaluate_all('nodes=>nodes.map(e=>e.id)');assert len(ids)==len(set(ids))
                result['workflows'].append('Keyboard lens tabs, 200ms plane/200ms sweep, reduced-motion cancellation, unique anchors')
                if not os.environ.get('THEMESCOPE_QUICK_UI'):
                    for width in (1440,1024,768,480,320):
                        page.set_viewport_size({'width':width,'height':1000 if width>=768 else 844})
                        for scale in (100,200):
                            for density in ('compact','comfortable'):
                                page.locator('#display-toggle').click();page.locator(f'button[data-density="{density}"]').click()
                                while int(page.locator('#text-size').inner_text().rstrip('%'))!=scale:page.locator('[data-text-step="'+('25' if scale==200 else '-25')+'"]').click()
                                page.locator('#display-motion').check();page.locator('#display-contrast').set_checked(density=='comfortable');page.keyboard.press('Escape')
                                for destination in ('overview','themes','primary','saved','methodology'):
                                    nav(destination);width_ok((width,scale,density,destination))
                                    if destination=='themes' and scale==100 and width>=768:assert page.locator('#theme-table table').evaluate('e=>getComputedStyle(e).display')=='table'
                                    if destination=='primary':
                                        for selected in ('directional','countertrend'):lens(selected);width_ok((width,scale,density,selected))
                                    if density=='compact' and (width in (1024,768,480,320) or scale==200):capture(f'{destination}-{width}-text-{scale}')
                                if density=='comfortable':audit(f'{width}-{scale}-high-contrast')
                                nav('themes');page.locator('#theme-table [data-inspect-theme]').first.click();assert page.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth'),(width,scale,'theme inspector')
                                page.locator('#inspector-members [data-inspect-ticker]').first.click();assert page.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth'),(width,scale,'ticker inspector');page.keyboard.press('Escape')
                                result['responsive'].append({'width':width,'text':scale,'density':density,'passed':True})
                assert not errors,errors;assert not outside,outside;assert not http,http
                result.update(passed=True,page_errors=errors,external_requests=outside,http_errors=http)
                (output/'results.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));browser.close()
        finally:server.should_exit=True;worker.join(5);sock.close()


if __name__=='__main__':main()
