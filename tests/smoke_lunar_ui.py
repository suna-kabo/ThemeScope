"""Lunar Lounge acceptance: real loopback app, synthetic bars, browser state fixtures.

No account, market-data network calls, production DB or third-party runtime assets.
Optional THEMESCOPE_AXE_SCRIPT points to an already downloaded axe-core script.
Optional THEMESCOPE_UI_ARTIFACTS captures labeled fixture screenshots and results.
"""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json,os,shutil,socket,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
from vnext_prelaunch_fixture import PrelaunchFixture


def main():
    from src.themescope.local.app import create_app
    from playwright.sync_api import sync_playwright,expect
    import uvicorn
    out=Path(os.environ['THEMESCOPE_UI_ARTIFACTS']) if os.environ.get('THEMESCOPE_UI_ARTIFACTS') else None
    if out:out.mkdir(parents=True,exist_ok=True)
    results={'data':'Deterministic test bars; browser state fixtures are illustrative, not financial recommendations',
             'widths':{},'states':[],'axe':{},'interactions':[]}
    with tempfile.TemporaryDirectory(prefix='themescope Lunar test ') as folder,patch('src.themescope.local.service.optional_earnings',return_value={}):
        fixture=PrelaunchFixture(folder,full=True);service=fixture.service
        assert service.refresh() is not None,service.status()
        actual=service.snapshot();assert len([t for t in actual['themes'] if t['status']=='active'])==44
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        origin=f'http://127.0.0.1:{port}'
        server=uvicorn.Server(uvicorn.Config(create_app(ROOT,service),log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+5
            while not server.started and time.monotonic()<deadline:threading.Event().wait(.01)
            assert server.started
            with sync_playwright() as p:
                options={'headless':True}
                if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='reduce')
                errors=[];outside=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                console_errors=[]
                page.on('console',lambda m:console_errors.append({'text':m.text,'url':m.location.get('url','')}) if m.type=='error' else None)
                page.on('request',lambda r:outside.append(r.url) if not r.url.startswith((origin,'blob:')) else None)
                # A visual label is injected in the TEST browser only; never in product source.
                page.add_init_script("""addEventListener('DOMContentLoaded',()=>{const e=document.createElement('p');e.textContent='UI validation · deterministic test data · not live';e.setAttribute('data-test-stamp','');e.style.cssText='position:fixed;bottom:8px;right:12px;z-index:99;background:#171923;color:#f1f0f7;padding:5px 10px;border:1px solid #bcadff;border-radius:7px;font:11px system-ui;max-width:calc(100vw - 24px);pointer-events:none';document.body.append(e);});""")
                page.goto(origin)
                expect(page.locator('#theme-table tbody tr')).to_have_count(44)
                expect(page.locator('#overview-title')).to_be_visible()
                expect(page.locator('#theme-layer')).to_contain_text('Pre-launch research')
                results['states'].append('real configured pre-launch research')
                nav=lambda name:page.locator(f'[data-nav="{name}"]').click()
                def open_map():
                    if not page.locator('#theme-map-panel').evaluate('e=>e.open'):page.locator('#theme-map-panel > summary').click()
                expect(page.locator('#theme-map-panel')).to_have_attribute('open','')
                def capture(label):
                    if out:
                        page.evaluate('''()=>{const d=document.querySelector('dialog[open]');if(d&&!d.querySelector('[data-test-stamp]'))d.append(document.querySelector('[data-test-stamp]').cloneNode(true));}''')
                        page.screenshot(path=str(out/(label+'.png')))
                axe_path=os.environ.get('THEMESCOPE_AXE_SCRIPT')
                def audit(label):
                    if not axe_path:return
                    # Evaluate the locally supplied script; the browser never fetches a CDN.
                    page.evaluate(Path(axe_path).read_text())
                    findings=page.evaluate("""async()=>{const r=await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}});return {violations:r.violations.map(v=>({id:v.id,impact:v.impact,nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary,html:n.html}))})),incomplete:r.incomplete.map(v=>v.id)};}""")
                    results['axe'][label]=findings
                    assert not findings['violations'],(label,findings)
                # Dedicated destinations, real config, representative desktop widths.
                for width in (1440,1600,1920):
                    page.set_viewport_size({'width':width,'height':1000})
                    for destination in ('overview','themes','primary','saved','methodology'):
                        nav(destination);expect(page.locator('.view:visible')).to_have_count(1)
                        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,destination,page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1&&!e.closest('[hidden]')).slice(0,15).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().right])"))
                        capture(f'{destination}-{width}')
                        if width==1440:audit(destination)
                    nav('themes');table=page.locator('#theme-table')
                    geometry=table.evaluate('e=>({width:e.clientWidth,scroll:e.scrollWidth})')
                    assert geometry['scroll']<=geometry['width']+1,(width,geometry)
                    results['widths'][str(width)]=geometry
                # At 1440p height, density remains useful without small value text.
                page.set_viewport_size({'width':2560,'height':1440})
                results['visible_rows_1440p']={}
                for destination,selector in [('themes','#theme-table'),('primary','#candidates')]:
                    nav(destination)
                    visible=page.locator(selector+' tbody tr').evaluate_all('rows=>rows.filter(r=>r.getBoundingClientRect().top>=0&&r.getBoundingClientRect().bottom<=innerHeight).length')
                    assert visible>=(30 if destination=='themes' else 24),(destination,visible)
                    results['visible_rows_1440p'][destination]=visible
                    centered=page.locator(selector+' tbody tr').first.evaluate("row=>[...row.querySelectorAll('td > .theme-link,td > .ticker-link,td > .state,td > .priority,td > .save-button')].every(e=>{const p=e.parentElement.getBoundingClientRect(),b=e.getBoundingClientRect();return Math.abs((b.top-p.top)-(p.bottom-b.bottom))<2})")
                    assert centered,(destination,'interactive/state boxes centered between dividers')
                # Inspector scroll does not move the page and closure restores its origin.
                page.set_viewport_size({'width':1440,'height':1000});nav('themes')
                scroll_link=page.locator('#theme-table a').nth(24);scroll_link.scroll_into_view_if_needed()
                origin_scroll=page.evaluate('scrollY');scroll_link.click()
                page.locator('#research-inspector').evaluate('e=>e.scrollTop=e.scrollHeight')
                page.keyboard.press('Escape');expect(page.locator('#research-inspector')).not_to_be_visible()
                assert abs(page.evaluate('scrollY')-origin_scroll)<2
                expect(scroll_link).to_be_focused()
                # IWM shares typography, keeps only price/EMA context and has no breadth.
                for selector in ['.market-ticker','.market-price','.state','.market-emas']:
                    sizes=[page.locator('.market-card').nth(i).locator(selector).first.evaluate('e=>getComputedStyle(e).fontSize') for i in [0,1,2]]
                    assert len(set(sizes))==1,(selector,sizes)
                assert page.locator('.market-card.context .breadth-bar').count()==0
                expect(page.locator('.market-card.context')).to_contain_text('Context only')
                # Snapshot-only visuals: correct breadth lengths, raw axes and inspectable points.
                nav('overview');open_map()
                map_rows=[t for t in actual['themes'] if t['status']=='active' and t['returns'] and all(t['returns'][i]['value'] is not None for i in [0,1])]
                expect(page.locator('[data-map-theme]')).to_have_count(len(map_rows))
                expect(page.locator('#theme-map')).to_contain_text('Raw returns · linear axes')
                for i,ticker in enumerate(['SPY','QQQ']):
                    bars=page.locator('.market-card').nth(i).locator('.breadth-fill')
                    for j,field in enumerate(['above_ema21','above_ema50']):
                        assert abs(float(bars.nth(j).get_attribute('width'))-float(actual['market']['context'][ticker]['breadth'][field]))<1e-9
                point=page.locator('[data-map-theme="semiconductors"]');point.focus()
                expect(page.locator('#map-readout')).to_contain_text('Semiconductors')
                page.keyboard.press('ArrowRight');assert page.evaluate('document.activeElement.hasAttribute("data-map-theme")')
                page.locator('#map-selection').select_option('semiconductors')
                expect(point).to_have_class('map-point positive map-selected')
                capture('theme-map-1440');audit('theme-map')
                point.focus();page.keyboard.press('Enter');expect(page.locator('#inspector-title')).to_have_text('Semiconductors')
                page.keyboard.press('Escape');expect(point).to_be_focused()
                for width in (800,390,320):
                    page.set_viewport_size({'width':width,'height':844});page.wait_for_timeout(180)
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),('map',width)
                    if width==320:
                        page.locator('#theme-map').scroll_into_view_if_needed();capture('theme-map-320');audit('theme-map-320')
                page.set_viewport_size({'width':1440,'height':1000});page.locator('#theme-map-panel > summary').click()
                results['interactions'].append('raw-return map, exact breadth display, keyboard points/selection/inspector, narrow map')
                # Search, all filters, independent Watch-only universe, stable sorting.
                page.set_viewport_size({'width':1440,'height':1000});nav('themes')
                page.locator('#theme-search').fill('semiconductors');expect(page.locator('#theme-table tbody tr')).to_have_count(1)
                page.locator('#theme-priority').select_option('Watch');expect(page.locator('#theme-table')).to_contain_text('No themes match')
                page.get_by_role('button',name='Reset',exact=True).click();expect(page.locator('#theme-table tbody tr')).to_have_count(44)
                family=actual['themes'][0]['family'];page.locator('#theme-family').select_option(family)
                assert all(family in row.text_content() for row in page.locator('#theme-table tbody tr').all())
                page.locator('#theme-trend').select_option('Unavailable');expect(page.locator('#theme-table')).to_contain_text('No themes match')
                page.locator('#theme-filters [data-reset]').click()
                page.get_by_role('button',name='Watch-only',exact=False).click();expect(page.locator('#theme-table tbody tr')).to_have_count(8)
                page.get_by_role('button',name='Active',exact=False).click()
                page.locator('[data-theme-sort="score"]').click()
                scores=page.locator('#theme-table tbody tr td:nth-child(3)').all_text_contents();assert list(map(float,scores))==sorted(map(float,scores))
                assert page.locator('[aria-sort="ascending"]').count()==1
                results['interactions'].append('theme search, family/priority/trend filters, Watch-only, sort')
                # The page, not an inner results pane, owns vertical scrolling.
                assert page.locator('#theme-table').evaluate('e=>e.scrollHeight<=e.clientHeight+1')
                page.mouse.move(1100,600);page.mouse.wheel(0,400);page.wait_for_timeout(150)
                assert page.evaluate('scrollY')>0
                page.locator('#theme-search').fill('semiconductors')
                detail_link=page.locator('#theme-table a').first;detail_link.focus();detail_link.press('Enter')
                expect(page.locator('#inspector-title')).to_have_text('Semiconductors');expect(page.locator('#inspector-title')).to_be_focused()
                expect(page.locator('#research-inspector')).to_be_visible();expect(page.locator('#themes-title')).to_be_visible()
                expect(page.locator('#inspector-members')).to_contain_text('Not qualified')
                page.locator('[data-inspector-filter="Primary"]').click()
                expected_members=sum(r['qualifies'] for r in actual['relationships'] if r['theme_id']=='semiconductors')
                expect(page.locator('#inspector-members tbody tr')).to_have_count(expected_members)
                page.locator('[data-inspector-filter="All"]').click();page.locator('#inspector-search').fill('NVDA')
                expect(page.locator('#inspector-members tbody tr')).to_have_count(1)
                capture('theme-inspector-1440');audit('theme-inspector')
                page.locator('#inspector-members [data-inspect-ticker="NVDA"]').click()
                expect(page.locator('#inspector-title')).to_have_text('NVDA');expect(page.locator('dialog[open]')).to_have_count(1)
                expect(page.locator('#inspector-content')).to_contain_text('Other qualifying themes')
                assert 'Earnings' not in page.locator('#inspector-content').inner_text()
                assert 'Stock 1M' not in page.locator('#inspector-content').inner_text()
                capture('ticker-inspector-1440');audit('ticker-inspector')
                page.keyboard.press('Escape');expect(page.locator('#research-inspector')).not_to_be_visible()
                expect(page.locator('#theme-search')).to_have_value('semiconductors');expect(detail_link).to_be_focused()
                expect(page.locator('[data-theme-row="semiconductors"]')).to_have_class('selected-row')
                page.go_forward();expect(page.locator('#inspector-title')).to_have_text('NVDA')
                page.go_back();expect(page.locator('#research-inspector')).not_to_be_visible()
                detail_link.click();page.get_by_role('link',name='Open full theme',exact=False).click()
                expect(page.locator('#detail-title')).to_have_text('Semiconductors');expect(page.locator('#detail-title')).to_be_focused()
                page.locator('#member-search').fill('NVDA');expect(page.locator('#member-table tbody tr')).to_have_count(1)
                assert page.locator('#member-table summary').count()==0
                with page.expect_download() as item:page.get_by_role('link',name='Theme Primary TXT',exact=False).click()
                assert Path(item.value.path()).read_text()==actual['exports']['individual']['semiconductors']
                capture('theme-detail-1440');audit('theme-detail')
                page.get_by_role('link',name='Back to Themes',exact=False).click()
                expect(page.locator('#theme-search')).to_have_value('semiconductors');expect(detail_link).to_be_focused()
                results['interactions'].append('Theme/ticker inspector, native keyboard focus, one dialog, preserved filters, browser Back/Forward, optional full theme and canonical TXT')
                # Candidate unique vs independent relationships, unchanged canonical TXT.
                nav('primary');unique=len({r['ticker'] for r in actual['relationships'] if r['qualifies']});relationships=sum(r['qualifies'] for r in actual['relationships'])
                expect(page.locator('#candidates tbody tr')).to_have_count(unique)
                first=page.locator('#candidates [data-save]').first;ticker=first.get_attribute('data-save');key=first.get_attribute('data-focus-key')
                first.focus();first.press('Space');expect(first).to_have_attribute('aria-pressed','true')
                page.wait_for_timeout(1800);expect(page.locator(f'[data-focus-key="{key}"]')).to_be_focused()
                capture('primary-earnings-disabled-1440')
                page.get_by_role('button',name='By theme',exact=True).click();expect(page.locator('#candidates tbody tr')).to_have_count(relationships)
                page.locator('#candidate-search').fill(ticker)
                assert page.locator('#candidates tbody tr').count()>=1
                expect(page.locator('#candidate-earnings')).to_be_hidden()
                assert page.locator('#candidates th').all_text_contents()==['Ticker','Theme','Role','W · pp','Save']
                assert page.locator('#candidates td[data-label="Earnings"]').count()==0
                with page.expect_download() as item:page.get_by_role('link',name='Export all Primary',exact=False).click()
                text=Path(item.value.path()).read_text();assert text==actual['exports']['combined']
                identifiers=[s for s in text.splitlines() if s and not s.startswith('###')];assert len(identifiers)==len(set(identifiers))
                page.locator('#candidate-filters [data-reset]').click()
                page.locator('#candidate-role').select_option('Core');assert page.locator('#candidates tbody tr').count()>0
                page.locator('#candidate-w').select_option('negative');expect(page.locator('#candidates')).to_contain_text('No Primary stocks match')
                results['interactions'].append('multi-theme and unique candidate views, filters, stable poll focus, canonical combined TXT')
                nav('saved');expect(page.locator('#saved')).to_contain_text(ticker);capture('saved-populated-1440');audit('saved-populated')
                page.reload();expect(page.locator('#saved')).to_contain_text(ticker)
                page.get_by_role('button',name=f'Remove {ticker} from Saved').click();expect(page.locator('#saved')).to_contain_text('No Saved tickers');expect(page.locator('#saved-title')).to_be_focused()
                results['interactions'].append('existing local bookmark persistence, current relationship context, Remove focus')
                # Display choices use a different key and survive a browser reload.
                page.locator('#display-toggle').click();expect(page.locator('#display-panel')).to_be_visible()
                page.locator('button[data-density="comfortable"]').click()
                page.locator('#display-motion').check();page.locator('#display-contrast').check()
                page.locator('[data-text-step="25"]').click();expect(page.locator('#text-size')).to_have_text('125%')
                assert page.evaluate("JSON.parse(localStorage.getItem('themescope-vnext-display')).contrast")
                assert page.evaluate("JSON.parse(localStorage.getItem('themescope-vnext-watchlist')).length") == 0
                page.reload();page.locator('#display-toggle').click();expect(page.locator('#text-size')).to_have_text('125%')
                expect(page.locator('#display-motion')).to_be_checked();expect(page.locator('#display-contrast')).to_be_checked()
                audit('display-high-contrast');capture('display-high-contrast')
                page.locator('button[data-density="compact"]').click();page.locator('[data-text-step="-25"]').click()
                page.locator('#display-motion').uncheck();page.locator('#display-contrast').uncheck()
                page.keyboard.press('Escape');expect(page.locator('#display-toggle')).to_be_focused()
                results['interactions'].append('Display storage, density, text size, contrast, motion, keyboard dismissal')
                # Keyboard-only main navigation, skip link and reduced-motion semantics.
                page.locator('[data-nav="methodology"]').focus();page.keyboard.press('Enter');expect(page.locator('#methodology-title')).to_be_focused()
                page.locator('.method-item summary').first.focus();page.keyboard.press('Enter');expect(page.locator('.method-item').first).to_have_attribute('open','')
                page.locator('.skip-link').focus();page.keyboard.press('Enter');expect(page.locator('#workspace')).to_be_focused();assert page.url.endswith('#methodology')
                assert page.locator('#refresh').evaluate('e=>getComputedStyle(e).transitionDuration')=='0s'
                results['interactions'].append('keyboard navigation, disclosures, skip link, reduced motion')
                # Responsive reflow on every surface; actual financial tables stay locally scrollable.
                for width in (800,390,320):
                    page.set_viewport_size({'width':width,'height':844})
                    for destination in ('overview','themes','primary','saved','methodology'):
                        nav(destination);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,destination,page.evaluate("[...document.querySelectorAll('body *')].filter(e=>e.getBoundingClientRect().right>innerWidth+1&&!e.closest('[hidden]')).slice(0,15).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().right])"))
                        if width==390:capture(f'{destination}-390')
                    nav('themes');page.locator('#theme-filters [data-reset]').click();page.locator('#theme-mobile-sort').select_option('name:asc')
                    page.locator('#theme-table a[href="#themes/semiconductors"]').click();assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');capture(f'theme-inspector-{width}')
                    page.locator('#inspector-search').fill('NVDA');page.locator('#inspector-members [data-inspect-ticker]').first.click()
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');capture(f'ticker-inspector-{width}')
                    assert page.locator('#research-inspector').bounding_box()['x']>=0
                    if width==320:audit('ticker-inspector-320')
                    page.keyboard.press('Escape');expect(page.locator('#research-inspector')).not_to_be_visible()
                    results['widths'][str(width)]='all six surfaces: no document overflow'
                page.set_viewport_size({'width':1440,'height':1000})
                # 200% root text resize independently stresses layout. This is not native browser zoom.
                page.evaluate("document.documentElement.style.fontSize='200%'")
                for destination in ('overview','themes','primary','saved','methodology'):
                    nav(destination);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),('200% text',destination)
                capture('text-200-methodology')
                nav('themes');capture('text-200-themes');page.locator('#theme-filters [data-reset]').click();page.locator('#theme-table a').first.click()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                capture('text-200-inspector')
                page.keyboard.press('Escape');expect(page.locator('#research-inspector')).not_to_be_visible()
                results['widths']['200% text resize']='five destinations and inspector reflow without document overflow'
                nav('overview');open_map()
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.locator('#theme-map-panel > summary').click()
                page.evaluate("document.documentElement.style.fontSize=''")
                # Mock only API responses for presentation-state coverage; no calculations changed.
                state={'snapshot':deepcopy(actual),'status':service.status()}
                page.route('**/api/dashboard-data',lambda r:r.fulfill(body=json.dumps(state['snapshot']),content_type='application/json'))
                page.route('**/api/status',lambda r:r.fulfill(json=state['status']))
                def update(label):
                    state['snapshot']['refreshed_at']=label
                    expect(page.locator('#progress')).to_have_text(state['status']['progress'],timeout=6000)
                    page.wait_for_timeout(1600)
                    results['states'].append(label)
                nav('themes');page.locator('#theme-filters [data-reset]').click();page.locator('#theme-search').fill('semiconductors')
                page.locator('#theme-table a').first.click();page.locator('#inspector-search').fill('NVDA');page.locator('#inspector-search').focus()
                state['snapshot']['themes']=deepcopy(actual['themes'])
                revised=next(t for t in state['snapshot']['themes'] if t['theme_id']=='semiconductors');revised['score']='88.12'
                state['snapshot']['refreshed_at']='inspector refresh'
                expect(page.locator('#inspector-content')).to_contain_text('88.12',timeout=6000)
                expect(page.locator('#inspector-search')).to_be_focused();expect(page.locator('#inspector-search')).to_have_value('NVDA')
                retained=page.locator('#inspector-members').inner_text()
                state['status'].update(state='failed',progress='Refresh failed',error='synthetic_provider_failure')
                expect(page.locator('#inspector-status')).to_contain_text('previous successful snapshot retained',timeout=6000)
                assert page.locator('#inspector-members').inner_text()==retained
                assert state['snapshot']['exports']==actual['exports']
                page.go_back();expect(page.locator('#theme-search')).to_have_value('semiconductors')
                results['interactions'].append('changed snapshot preserves inspector/search/focus; refresh failure retains visible members and canonical exports')
                nav('overview')
                state['status'].update(state='running',progress='Calculating market, themes and peer comparisons');update('refresh running');expect(page.locator('#refresh')).to_be_disabled();expect(page.locator('#market-direction')).to_contain_text('Long bias')
                state['status'].update(state='failed',progress='Refresh failed',error='synthetic_provider_failure');update('refresh failure with previous snapshot');expect(page.locator('#error')).to_contain_text('Previous successful results');assert state['snapshot']['exports']==actual['exports']
                state['status'].update(state='success',progress='Refresh complete',error=None);update('refresh success');expect(page.locator('#error')).to_be_hidden()
                state['snapshot']['theme_layer'].update(state='initialized',official_live_history=True);update('initialized launch');expect(page.locator('#theme-layer')).to_be_hidden();expect(page.locator('#lifecycle-detail')).to_contain_text('Launch close: index initialized at 100')
                state['snapshot']['theme_layer'].update(state='live');update('normal live');expect(page.locator('#theme-layer')).to_be_hidden();expect(page.locator('#lifecycle-detail')).to_contain_text('Official theme history')
                # Alignment and EMA presentation use existing values; breadth state stays supplied.
                state['snapshot']['market']['context']['SPY'].update(close='735.29',ema21='759.99',ema50='762.65',price_state='Bearish')
                state['snapshot']['market']['context']['QQQ'].update(close='656.10',ema21='650.00',ema50='656.10',price_state='Mixed')
                state['snapshot']['market']['context']['SPY']['breadth']['state']='Negative'
                state['snapshot']['market']['context']['QQQ']['breadth']['state']='Positive'
                state['snapshot']['market_direction']='Short bias'
                update('market alignment presentation boundaries')
                expect(page.locator('.market-card').nth(0).locator('.ema-context.negative')).to_have_count(2)
                expect(page.locator('.market-card').nth(1).locator('.ema-context.positive')).to_have_count(1)
                expect(page.locator('.market-card').nth(1).locator('.ema-context.neutral')).to_contain_text('At EMA50')
                expect(page.locator('.market-card').nth(0).locator('.breadth-state')).to_have_class('breadth-state negative')
                expect(page.locator('.market-card').nth(1).locator('.breadth-state')).to_have_class('breadth-state positive')
                assert page.locator('#market-cards details').count()==0
                for width,height in [(2560,1440),(1920,1080),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height});nav('overview');open_map();page.evaluate('scrollTo(0,0)')
                    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                    if width>800:
                        for selector in ['.market-ticker','.market-price','.state','.market-emas','.market-breadth','.breadth-state']:
                            y=[page.locator('.market-card').nth(i).locator(selector).first.bounding_box()['y'] for i in [0,1]]
                            assert abs(y[0]-y[1])<1,(width,selector,y)
                    capture('market-overview-'+str(width))
                page.set_viewport_size({'width':1440,'height':1000})
                page.evaluate("document.documentElement.style.fontSize='200%'");capture('market-overview-text-200')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.evaluate("document.documentElement.style.fontSize=''")
                state['snapshot']['market']['context']['SPY'].update(close=None,ema21=None)
                update('missing market EMA inputs');expect(page.locator('.market-card').nth(0).locator('.ema-context.neutral').first).to_contain_text('Unavailable EMA21')
                # Motion is finite, and both user/OS reduction suppress it.
                page.emulate_media(reduced_motion='no-preference');nav('themes')
                assert page.locator('#themes-page').evaluate('e=>getComputedStyle(e).animationDuration')=='0.11s'
                page.locator('#display-toggle').click();page.locator('#display-motion').check();page.keyboard.press('Escape')
                nav('overview');assert page.locator('#overview-page').evaluate('e=>getComputedStyle(e).animationName')=='none'
                page.locator('#display-toggle').click();page.locator('#display-motion').uncheck();page.keyboard.press('Escape')
                page.emulate_media(reduced_motion='reduce');nav('themes')
                assert page.locator('#themes-page').evaluate('e=>getComputedStyle(e).animationName')=='none'
                nav('overview')
                results['interactions'].append('aligned market rows, Above/Below/At/missing EMA, supplied breadth, quiet lifecycle, default map and finite reduced motion')
                for label,direction in [('neutral','Neutral'),('short-biased','Short bias'),('unclassified','Unclassified')]:
                    state['snapshot']['market_direction']=direction;state['snapshot']['market']['decision']['direction']=direction
                    state['snapshot']['today_plan']='Illustrative browser state · not a live signal'
                    for t in state['snapshot']['themes']:t['priority']='Watch'
                    for r in state['snapshot']['relationships']:r['qualifies']=False
                    update(label);expect(page.locator('#market-direction')).to_contain_text(direction);expect(page.locator('#primary-themes')).to_contain_text('No Primary themes')
                    nav('primary');expect(page.locator('#candidates')).to_contain_text('No Primary stocks');nav('overview')
                # An explicit illustrative short qualification, not a recalculation of market rules.
                state['snapshot']=deepcopy(actual)
                short=next(r for r in state['snapshot']['relationships'] if r['relative']['w'] is not None and float(r['relative']['w'])<0)
                state['snapshot']['market_direction']='Short bias';state['snapshot']['market']['decision']['direction']='Short bias'
                for t in state['snapshot']['themes']:t['priority']='Primary short' if t['theme_id']==short['theme_id'] else 'Watch'
                for r in state['snapshot']['relationships']:r['qualifies']=r is short
                short['assigned_section']=short['theme_id'];short['also_qualifies_in']=[]
                state['snapshot']['earnings'][short['ticker']]={'status':'Available','dates':['2026-11-12']}
                update('illustrative short candidate and earnings date');nav('primary');page.locator('#candidate-filters [data-reset]').click();page.get_by_role('button',name='Unique tickers',exact=True).click()
                page.locator('#candidate-earnings').select_option('available');expect(page.locator('#candidates tbody tr')).to_have_count(1);expect(page.locator('#candidates')).to_contain_text('2026-11-12');capture('short-candidate-1440')
                # Explicit Available-without-date and an ambiguous failure remain distinct.
                state['snapshot']['earnings'][short['ticker']]={'status':'Available','dates':[]}
                update('enabled earnings without a reported date')
                expect(page.locator('#candidate-earnings')).to_be_visible()
                page.locator('#candidate-earnings').select_option('unavailable')
                expect(page.locator('#candidates')).to_contain_text('No reported date')
                page.locator('#candidates [data-inspect-ticker]').first.click()
                expect(page.locator('#inspector-content')).to_contain_text('No reported date')
                page.keyboard.press('Escape')
                other=next(r['ticker'] for r in state['snapshot']['relationships'] if r['ticker']!=short['ticker'])
                state['snapshot']['earnings'][other]={'status':'Available','dates':[]}
                state['snapshot']['earnings'][short['ticker']]={'status':'Unavailable','dates':[]}
                update('individual earnings unavailable with provider enabled')
                expect(page.locator('#candidates')).to_contain_text('Unavailable')
                state['snapshot']['earnings']={t:{'status':'Unavailable','dates':[]} for t in state['snapshot']['earnings']}
                update('earnings globally unavailable')
                expect(page.locator('#candidate-earnings')).to_be_hidden()
                expect(page.locator('#candidate-earnings')).to_have_value('')
                expect(page.locator('#candidates tbody tr')).to_have_count(1)
                page.locator('#candidates [data-inspect-ticker]').first.click()
                assert 'Earnings' not in page.locator('#inspector-content').inner_text()
                page.keyboard.press('Escape')
                assert state['snapshot']['exports']==actual['exports']
                # Unavailable breadth retains its compact dash and only supplied metadata.
                breadth_theme=state['snapshot']['themes'][0]
                breadth_theme['breadth'][0].update(value=None,valid=11,configured=15,coverage='0.7333333333333333')
                update('breadth unavailable coverage metadata');nav('themes');page.locator('#theme-search').fill(breadth_theme['name'])
                expect(page.locator('#theme-table [title="11/15 valid · 73.33% coverage"]')).to_contain_text('—')
                results['interactions'].append('earnings disabled/enabled/date/empty/failure transitions; IWM typography; unavailable breadth metadata')
                state['snapshot']=deepcopy(actual);state['snapshot']['themes'][0]['score']=None;state['snapshot']['themes'][0]['returns']=None;state['snapshot']['themes'][0]['index']['trend']='Unavailable';update('unavailable metrics');nav('themes')
                page.locator('#theme-search').fill(state['snapshot']['themes'][0]['name']);expect(page.locator('#theme-table')).to_contain_text('Unavailable');assert 'NaN' not in page.locator('#theme-table').inner_text()
                # Raw axes retain extreme values, negative/zero, ties and omit unavailable returns.
                state['snapshot']=deepcopy(actual)
                active=[t for t in state['snapshot']['themes'] if t['status']=='active']
                active[0]['returns'][0]['value']='12.0';active[0]['returns'][1]['value']='-0.4'
                active[1]['returns'][0]['value']='0';active[1]['returns'][1]['value']='0'
                active[2]['returns']=deepcopy(active[1]['returns']);active[3]['returns']=None
                state['snapshot']['refreshed_at']='map extremes and missing values'
                nav('overview');open_map()
                expect(page.locator('[data-map-theme]')).to_have_count(43,timeout=6000)
                page.wait_for_function("()=>Number(document.querySelector('#theme-map-svg')?.dataset.xmax)>12")
                svg=page.locator('#theme-map-svg');assert float(svg.get_attribute('data-xmax'))>12 and float(svg.get_attribute('data-ymin'))<-.4
                page.locator('#map-selection').select_option(active[0]['theme_id']);expect(page.locator('#map-readout')).to_contain_text('+1,200.00%')
                expect(page.locator('#map-readout')).to_contain_text('-40.00%')
                page.locator('#map-selection').select_option(active[1]['theme_id']);expect(page.locator('#map-readout')).to_contain_text('0.00%')
                assert page.locator('[data-map-theme]').evaluate_all("nodes=>nodes.every(n=>{const p=n.querySelector('.point-hit');return Number.isFinite(+p.getAttribute('cx'))&&Number.isFinite(+p.getAttribute('cy'))})")
                results['states'].append('raw map extremes, negative/zero, identical points and unavailable returns')
                # Loading/no prior snapshot must remain usable and honestly disabled.
                state['snapshot']=None;state['status'].update(state='idle',progress='Ready');page.reload();expect(page.locator('#progress')).to_have_text('Ready');nav('primary');expect(page.locator('#combined')).to_have_attribute('aria-disabled','true');capture('no-snapshot-1440');results['states'].append('loading / no prior snapshot')
                # Existing Saved schema, including a symbol absent from today's snapshot.
                page.evaluate("localStorage.setItem('themescope-vnext-watchlist',JSON.stringify(['LEGACY']))");page.reload();nav('saved');expect(page.locator('#saved')).to_contain_text('LEGACY');results['states'].append('existing Saved ticker retained without snapshot')
                page.locator('#saved [data-inspect-ticker="LEGACY"]').click();expect(page.locator('#inspector-content')).to_contain_text('No current relationship')
                page.keyboard.press('Escape')
                page.emulate_media(forced_colors='active');page.evaluate("document.querySelectorAll('[data-test-stamp]').forEach(e=>{e.style.color='CanvasText';e.style.background='Canvas'})");nav('methodology');audit('forced-colors');page.emulate_media(forced_colors='none')
                results['interactions'].append('absent Saved ticker inspector, forced colors')
                assert not errors,errors;assert not outside,outside
                known=[e for e in console_errors if e['url']==origin+'/favicon.ico' and '404 (Not Found)' in e['text']]
                unexpected=[e for e in console_errors if e not in known]
                assert not unexpected,unexpected
                results.update(page_errors=errors,console_errors=unexpected,known_browser_diagnostics=[{'resource':'/favicon.ico','status':404,'preexisting':True} for e in known],external_requests=outside,passed=True)
                browser.close()
        finally:server.should_exit=True;worker.join(5);sock.close()
    if out:(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
