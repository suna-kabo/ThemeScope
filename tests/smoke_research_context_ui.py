"""Additive research UX acceptance against loopback, with labeled synthetic state.

Run with system Python + Playwright. No credentials, external data, or deployment.
THEMESCOPE_UI_ARTIFACTS and THEMESCOPE_AXE_SCRIPT are optional local output/input.
"""
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch
import json, os, shutil, socket, sys, tempfile, threading, time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from vnext_prelaunch_fixture import PrelaunchFixture
from src.themescope.research.context import enrich
from src.themescope.storage import canonical

from ui_smoke_helpers import open_exports,open_filters


def main():
    from playwright.sync_api import sync_playwright,expect
    from src.themescope.local.app import create_app
    import uvicorn
    output=Path(os.environ.get('THEMESCOPE_UI_ARTIFACTS','/tmp/themescope-research-context'))
    output.mkdir(parents=True,exist_ok=True)
    result={'fixture':'Manufactured browser state from deterministic bars; not live validation','axe':{},'responsive':[],'interactions':[]}
    with tempfile.TemporaryDirectory() as folder,patch('src.themescope.local.service.optional_earnings',return_value={}):
        fixture=PrelaunchFixture(folder,full=True);fixture.target="2026-11-10";service=fixture.service
        assert service.refresh() is not None,service.status()
        base=service.snapshot();current=deepcopy(base)
        # Deliberate browser-only weak-theme state for the two research buckets.
        current['market_direction']='Short bias';current['session']='2026-11-10'
        current['market']['decision'].update(direction='Short bias',reason='Illustrative short-bias state for browser validation')
        current['theme_layer'].update(state='live')
        for t in current['themes']:
            t['history'].update(session=current['session'],bootstrap=False,signal_eligible=True)
            if t['status']=='active':
                t['index'].update(trend='Bearish',bootstrap=False,ema21=str(D(t['index']['level'])+1),ema50=str(D(t['index']['level'])+2))
                t['history']['trend']='Bearish'
        for ticker in ('SPY','QQQ'):
            close=D(current['market']['context'][ticker]['close'])
            current['market']['context'][ticker].update(ema21=str(close+8),ema50=str(close+10),price_state='Bearish')
        # Use the existing Directional engine for a coherent illustrative bias,
        # rather than leaving stale long qualifications in a short-bias screenshot.
        from src.themescope.research.primary import priority, qualifies, Eligibility
        from src.themescope.research.exports import exports, Qualification
        themes={t['theme_id']:t for t in current['themes']}
        selected=[]
        for t in current['themes']:
            t['priority']=priority(current['market_direction'],t['score'],t['index']['trend'],t['transition'])
            t['history']['priority']=t['priority']
        for r in current['relationships']:
            r['qualifies']=qualifies(themes[r['theme_id']]['priority'],r['relative']['w'],Eligibility(**r['eligibility']))
            if r['qualifies']:selected.append(Qualification(r['ticker'],r['theme_id'],r['role'],D(r['relative']['w'])))
        current['exports']=exports(selected,'short',{r.ticker:{'status':'verified','symbol':'FIXTURE:'+r.ticker} for r in selected})
        for r in current['relationships']:
            assignment=current['exports']['assignments'].get(r['ticker'],{})
            r['assigned_section']=assignment.get('assigned_section');r['also_qualifies_in']=assignment.get('also_qualifies_in',[])
        previous=deepcopy(current);previous['session']='2026-11-09'
        for t in previous['themes']:t['history']['session']=previous['session']
        for ticker in ('SPY','QQQ','IWM'):
            row=previous['market']['context'][ticker];row['ema21']=str(D(row['close'])-1)
        # Deliberate prior rank difference; no browser-side historical calculation.
        previous['themes'][0]['score']='100'
        bars={(b.ticker,b.session):b for b in fixture.bars}
        sessions=fixture.sessions[:fixture.sessions.index('2026-11-10')+1]
        from src.themescope.themes.history import ThemeHistory,transitions
        previous_themes={t['theme_id']:t for t in previous['themes']}
        for t in current['themes']:
            t['transition']=transitions(ThemeHistory(**previous_themes[t['theme_id']]['history']),ThemeHistory(**t['history']),sessions)
        data=json.loads(canonical(enrich(current,bars,sessions,previous,base['research']['companies'])))
        assert data['research']['extension']['state']=='Downside Extended'
        assert all(data['research']['countertrend']['buckets'][b]['stock_count']>0 for b in ('resilient','snapback'))
        state={'snapshot':data};status=service.status()
        # HTTP downloads also read this test snapshot, preserving contract coherence.
        service.snapshot=lambda:deepcopy(state['snapshot'])
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1];origin=f'http://127.0.0.1:{port}'
        server=uvicorn.Server(uvicorn.Config(create_app(ROOT,service),log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+5
            while not server.started and time.monotonic()<deadline:threading.Event().wait(.01)
            assert server.started
            with sync_playwright() as p:
                opts={'headless':True}
                if shutil.which('chromium'):opts['executable_path']=shutil.which('chromium')
                browser=p.chromium.launch(**opts);page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                errors=[];external=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:external.append(r.url) if not r.url.startswith((origin,'blob:')) else None)
                page.route('**/api/dashboard-data',lambda r:r.fulfill(json=state['snapshot']))
                page.route('**/api/status',lambda r:r.fulfill(json=status))
                page.add_init_script("""addEventListener('DOMContentLoaded',()=>{const e=document.createElement('p');e.textContent='UI validation · manufactured test state · not live';e.dataset.testStamp='';e.style.cssText='position:fixed;bottom:5px;right:6px;z-index:99;padding:4px 8px;background:#171923;color:#f1f0f7;border:1px solid #bcadff;font:11px system-ui;max-width:calc(100vw - 12px);pointer-events:none';document.body.append(e);});""")
                def capture(label):
                    page.evaluate("()=>{const d=document.querySelector('dialog[open]');if(d&&!d.querySelector('[data-test-stamp]'))d.append(document.querySelector('[data-test-stamp]').cloneNode(true));}")
                    page.screenshot(path=str(output/(label+'.png')),full_page=False)
                def audit(label):
                    axe=os.environ.get('THEMESCOPE_AXE_SCRIPT')
                    if axe:
                        page.evaluate(Path(axe).read_text())
                        violations=page.evaluate("async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return r.violations.map(v=>({id:v.id,nodes:v.nodes.map(n=>({target:n.target,html:n.html,summary:n.failureSummary}))}))}")
                        result['axe'][label]=violations;assert not violations,(label,violations)
                def nav(name):page.locator(f'[data-nav="{name}"]').click()
                def lens(name):page.locator(f'[data-candidate-lens="{name}"]').click()
                def no_overflow(label):
                    if not page.evaluate('document.documentElement.scrollWidth<=innerWidth'):
                        capture('overflow-'+str(label))
                        offenders=page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length&&!e.closest('[hidden]')&&e.getBoundingClientRect().right>innerWidth+.1).slice(0,30).map(e=>({tag:e.tagName,id:e.id,cls:e.className,right:e.getBoundingClientRect().right,text:e.innerText?.slice(0,100)}))")
                        overfull=page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getClientRects().length&&!e.closest('[hidden]')&&e.scrollWidth>e.clientWidth+1).slice(0,35).map(e=>({tag:e.tagName,id:e.id,cls:e.className,client:e.clientWidth,scroll:e.scrollWidth,right:e.getBoundingClientRect().right,text:e.innerText?.slice(0,100)}))")
                        raise AssertionError((label,page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})'),offenders,overfull))
                    for area in page.locator('.view:visible .table-wrap').all():
                        assert area.evaluate('e=>e.scrollHeight<=e.clientHeight+1'),label
                page.goto(origin)
                expect(page.locator('#market-direction')).to_contain_text('Downside Extended')
                expect(page.locator('#market-direction')).to_contain_text('Countertrend review')
                expect(page.locator('#market-direction')).to_contain_text('Prioritises short-side research. Entry evaluation remains separate.')
                expect(page.locator('.market-card').first).to_contain_text('Crossed below EMA21 on 2026-11-10')
                assert page.locator('.market-card.context .index-extension').count()==0
                assert not page.locator('#completeness').is_visible()
                capture('overview-1440');audit('overview')
                nav('primary');expect(page.locator('[data-candidate-lens="countertrend"]')).to_have_attribute('aria-selected','true')
                expect(page.locator('#candidates')).to_contain_text('Peer outperformers');expect(page.locator('#candidates')).to_contain_text('Weak-theme laggards')
                assert page.locator('#candidates [data-help="countertrend"]').count()==1
                expect(page.locator('#combined')).to_be_hidden()
                for key in ('resilient','snapback'):
                    expected=[r['ticker'] for r in data['research']['countertrend']['buckets'][key]['stocks']]
                    actual=page.locator(f'[data-countertrend="{key}"] [data-inspect-ticker]').evaluate_all('els=>els.map(e=>e.dataset.inspectTicker)')
                    assert actual==expected
                capture('candidates-countertrend-1440');audit('countertrend')
                first=page.locator('#candidates [data-save]').first;first.click()
                assert not page.locator('dialog').is_visible()
                lens('directional');open_exports(page);expect(page.locator('#combined')).to_be_visible()
                open_exports(page)
                with page.expect_download() as item:page.locator('#combined').click()
                assert Path(item.value.path()).read_text()==data['exports']['combined']
                page.locator('#candidates [data-save]').first.click()
                capture('candidates-directional-1440');audit('directional')
                # Changed poll must not override explicit lens, search, or Saved.
                page.locator('#candidate-search').fill('A')
                state['snapshot']=deepcopy(data);state['snapshot']['research']['focus']['preferred_mode']='countertrend';state['snapshot']['refreshed_at']='test revision'
                page.wait_for_timeout(1800)
                expect(page.locator('[data-candidate-lens="directional"]')).to_have_attribute('aria-selected','true')
                expect(page.locator('#candidate-search')).to_have_value('A')
                page.locator('#candidate-search').fill('')
                nav('themes');ranks=page.locator('[data-theme-row]').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.dataset.themeRow,e.cells[0].textContent]))")
                page.locator('[data-theme-sort="name"]').click()
                assert page.locator('[data-theme-row]').evaluate_all("els=>Object.fromEntries(els.map(e=>[e.dataset.themeRow,e.cells[0].textContent]))")==ranks
                page.locator('#theme-search').fill('airlines')
                assert page.locator('[data-theme-row="airlines"] td').first.inner_text()==ranks['airlines']
                page.locator('#theme-search').fill('');capture('themes-1440');audit('themes')
                page.locator('#theme-table [data-inspect-theme="semiconductors"]').first.click()
                page.locator('#inspector-search').fill('NVDA');ticker=page.locator('#inspector-members [data-inspect-ticker="NVDA"]');ticker.click()
                expect(page.locator('#inspector-content')).to_contain_text('1M return vs peers')
                expect(page.locator('[data-current-theme]')).to_have_attribute('data-current-theme','semiconductors')
                capture('ticker-inspector-1440');audit('ticker-inspector')
                page.go_back();expect(page.locator('#inspector-title')).to_have_text('Semiconductors')
                expect(page.locator('#inspector-search')).to_have_value('NVDA');expect(ticker).to_be_focused()
                page.get_by_role('link',name='Open full theme',exact=False).click();capture('theme-detail-1440');audit('full-theme')
                nav('themes');page.locator('#theme-priority').select_option('Primary long');page.locator('[data-universe="watch_only"]').click()
                expect(page.locator('#theme-priority')).to_have_value('');expect(page.locator('#theme-priority')).to_be_hidden()
                assert page.locator('#theme-table tbody tr').count()>0
                page.locator('#theme-table [data-inspect-theme]').first.click()
                expect(page.locator('#inspector-content')).to_contain_text('No active calculation basket')
                assert page.locator('#inspector-content .metric-block').count()==0
                assert page.locator('#inspector-content input').count()==0
                capture('untracked-concept-1440');audit('untracked')
                page.keyboard.press('Escape');nav('themes');page.locator('[data-universe="active"]').click()
                # Deep link, explicit close and focus work without a previous owned history entry.
                page.goto(origin+'/#themes?ticker=NVDA');expect(page.locator('#inspector-title')).to_have_text('NVDA')
                page.keyboard.press('Escape');expect(page.locator('dialog')).not_to_be_visible();assert page.url.endswith('#themes')
                result['interactions']=['extension/focus supplied state','explicit EMA transition','Countertrend bucket order/counts','Directional export unchanged','poll retains lens/search','canonical ranks survive sorting/search','nested Back and focus','direct deep link','minimal Untracked Concepts']
                # Test every requested width, both sizes and densities, both candidate lenses.
                for width in (1440,1024,768,480,320):
                    page.set_viewport_size({'width':width,'height':1000 if width>768 else 844})
                    for scale in (100,200):
                        for density in ('compact','comfortable'):
                            page.locator('#display-toggle').click()
                            page.locator(f'button[data-density="{density}"]').click()
                            while int(page.locator('#text-size').inner_text().rstrip('%'))!=scale:
                                page.locator('[data-text-step="'+('25' if scale==200 else '-25')+'"]').click()
                            page.locator('#display-motion').check();page.locator('#display-contrast').set_checked(density=='comfortable')
                            page.keyboard.press('Escape')
                            if width<=800:
                                brand=page.locator('.brand').bounding_box();display_button=page.locator('#display-toggle').bounding_box()
                                assert not (brand['x']<display_button['x']+display_button['width'] and brand['x']+brand['width']>display_button['x'] and brand['y']<display_button['y']+display_button['height'] and brand['y']+brand['height']>display_button['y']),(width,scale,density,'brand/Display overlap')
                            for destination in ('overview','themes','primary','saved','methodology'):
                                nav(destination)
                                if destination=='primary':
                                    for mode in ('directional','countertrend'):
                                        lens(mode);no_overflow((width,scale,density,mode))
                                        if density=='compact' and (width==320 or scale==200 and width==1440):capture(f'{mode}-{width}-text-{scale}')
                                else:no_overflow((width,scale,density,destination))
                                if density=='compact' and (width==320 or scale==200 and width==1440):capture(f'{destination}-{width}-text-{scale}')
                            nav('themes')
                            weak=next(r for r in data['relationships'] if r['qualifies'])
                            page.locator(f'#theme-table [data-inspect-theme="{weak["theme_id"]}"]').click()
                            dialog=page.locator('#research-inspector')
                            if not dialog.evaluate('e=>e.scrollWidth<=e.clientWidth'):
                                capture('overflow-theme-sheet')
                                raise AssertionError((width,scale,density,'theme sheet',dialog.evaluate("e=>({client:e.clientWidth,scroll:e.scrollWidth,items:[...e.querySelectorAll('*')].filter(n=>n.scrollWidth>n.clientWidth+1&&!n.closest('.inspector-table')&&!n.matches('.sr-only')).map(n=>({tag:n.tagName,cls:n.className,client:n.clientWidth,scroll:n.scrollWidth,text:n.innerText?.slice(0,100)})).slice(0,25)})")))
                            if density=='compact' and width==320:capture(f'theme-inspector-{width}-text-{scale}')
                            page.locator(f'#inspector-members [data-inspect-ticker="{weak["ticker"]}"]').click()
                            assert dialog.evaluate('e=>e.scrollWidth<=e.clientWidth'),(width,scale,density,'ticker sheet')
                            if density=='compact' and width==320:capture(f'ticker-inspector-{width}-text-{scale}')
                            if density=='comfortable':audit(f'{width}-{scale}-ticker-sheet')
                            page.keyboard.press('Escape');expect(dialog).not_to_be_visible()
                            if density=='comfortable':audit(f'{width}-{scale}-comfortable-high-contrast')
                            result['responsive'].append(dict(width=width,text=scale,density=density,overflow=False))
                assert not errors,errors
                assert not external,external
                result.update(page_errors=errors,external_requests=external,passed=True)
                (output/'results.json').write_text(json.dumps(result,indent=2))
                print(json.dumps(result,indent=2));browser.close()
        finally:server.should_exit=True;worker.join(5);sock.close()


if __name__=='__main__':main()
