"""Real Chromium/CDP Network verification; run against an exported HTML path."""
import json
import re
import sys
import functools
import platform
import shutil
import threading
import zipfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright


path = Path(sys.argv[1]).resolve()
screenshots_dir = path.parent / 'screenshots' / 'after'
screenshots_dir.mkdir(parents=True, exist_ok=True)
layout_results=[]


def assert_table_layout(page, wrapper_selector, label, width):
    wrapper = page.locator(wrapper_selector)
    assert wrapper.is_visible(), f'{label} table is not visible at {width}px'
    result = wrapper.evaluate('(el) => ({clientWidth:el.clientWidth,scrollWidth:el.scrollWidth})')
    page_width = page.evaluate('document.documentElement.scrollWidth')
    assert page_width <= width + 1, f'page has horizontal overflow at {width}px: {page_width}px'
    if width <= 1024:
        assert result['scrollWidth'] > result['clientWidth'], f'{label} should scroll horizontally at {width}px: {result}'
    header = wrapper.locator('thead th').all()
    rows = wrapper.locator('tbody tr').all()
    assert header and rows, f'{label} table has no header or data row'
    for row in (rows[0], rows[-1]):
        cells = row.locator('td').all()
        assert len(cells) == len(header), f'{label} header/cell count differs at {width}px'
        for index, (th, td) in enumerate(zip(header, cells)):
            h, c = th.bounding_box(), td.bounding_box()
            assert abs(h['x']-c['x']) <= 1.5 and abs(h['width']-c['width']) <= 1.5, (label, width, index, h, c)
    layout_results.append({'table':label,'viewport_width':width,'wrapper_client_width':result['clientWidth'],'wrapper_scroll_width':result['scrollWidth'],'page_scroll_width':page_width,'headers_aligned':True})


server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=str(path.parent)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/{path.name}'
with sync_playwright() as p:
    launch_options = {'headless': True, 'args': ['--no-sandbox','--disable-dev-shm-usage','--disable-gpu']}
    system_chromium = shutil.which('chromium') or shutil.which('chromium-browser')
    if system_chromium:
        launch_options['executable_path'] = system_chromium
    browser = p.chromium.launch(**launch_options)
    page = browser.new_page(viewport={'width':1440,'height':1000}, accept_downloads=True)
    cdp = page.context.new_cdp_session(page)
    cdp.send('Network.enable')
    requests=[];errors=[]
    cdp.on('Network.requestWillBeSent', lambda event: requests.append(event['request']['url']))
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url);page.wait_for_timeout(400)
    assert 'Loading' not in page.inner_text('body')
    assert page.locator('#cards .market-card').count()==3
    assert page.locator('#volatility-card .market-card').count()==1
    assert 'IWM' in page.inner_text('#cards') and 'IWM HOLDINGS BREADTH' in page.inner_text('#cards')
    assert 'Constituents above EMA21' in page.inner_text('#cards')
    assert 'Price vs EMA21' in page.inner_text('#cards')
    assert page.locator('#cards .ema-pill').count()==0
    assert page.locator('#cards .condition-box').count()==6
    assert 'VIX' in page.inner_text('#volatility-card')
    assert 'Source status: available' not in page.inner_text('#volatility-card')
    assert 'HKT' in page.inner_text('#generated-hkt')
    assert page.locator('#status').inner_text() == '' or 'breadth unavailable' in page.locator('#status').inner_text()
    assert page.evaluate('document.fonts.check(\'15px "Inter Variable"\')')
    assert 'font-src data:' in page.content()
    assert page.locator('.state-tag').count() >= 0
    assert page.locator('html').get_attribute('data-mode')=='dark'
    assert page.locator('.side-nav [data-page]').count()==3
    assert page.locator('.side-nav [data-page="industries"]').count()==0
    page.click('.side-nav a[data-page="sectors-themes"]')
    assert page.locator('#sectors-themes').is_visible()
    snapshot_data=json.loads(page.locator('#snapshot-data').text_content())
    spy=next((row for row in snapshot_data.get('context',[]) if row.get('ticker')=='SPY'),{})
    if spy.get('index_source',{}).get('date_semantics')=='observation':
        assert all(spy.get('index_breadth',{}).get(str(period),{}).get('status')=='valid' for period in (21,50))
        assert 'not an official point-in-time universe' in page.locator('#cards').text_content()
    for exposure in snapshot_data.get('themes',[]):
        selected_count=len(exposure.get('selected') or [])
        assert exposure.get('curated_watchlist_count')==selected_count
        assert exposure.get('has_curated_watchlist') is (selected_count>0)
        assert exposure.get('stock_scope')==('Curated watchlist' if selected_count else 'ETF-only')
        if exposure.get('anchor')=='ICLN':
            metric=exposure.get('holdings_breadth',{}).get('21',{})
            if metric.get('reason_code')=='price_coverage_low':
                cell=page.locator(f'#theme-body tr[data-theme="{exposure["id"]}"] .col-breadth').first
                assert f'{metric["valid_count"]}/{metric["eligible_count"]}' in cell.inner_text()
                assert metric['reason'] in cell.locator('span').get_attribute('title')
    page.set_viewport_size({'width':1600,'height':1000})
    page.screenshot(path=str(screenshots_dir/'themes-1600-dark.png'))
    icln_exposure=next((row for row in snapshot_data.get('themes',[]) if row.get('anchor')=='ICLN'),None)
    if icln_exposure:
        icln_row=page.locator(f'#theme-body tr[data-theme="{icln_exposure["id"]}"]')
        icln_row.scroll_into_view_if_needed()
        page.screenshot(path=str(screenshots_dir/'themes-icln-1600-dark.png'))
        page.evaluate('window.scrollTo(0, 0)')
    page.locator('.theme-table-wrap').evaluate('(el) => el.scrollLeft = el.scrollWidth')
    page.screenshot(path=str(screenshots_dir/'themes-1600-dark-right.png'))
    page.locator('.theme-table-wrap').evaluate('(el) => el.scrollLeft = 0')
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(screenshots_dir/'themes-390-dark.png'))
    page.set_viewport_size({'width':1600,'height':1000})
    info=page.locator('#theme-head .info-button').first
    assert info.count()==1
    info.focus()
    tooltip=page.locator('#themescope-tooltip')
    page.wait_for_timeout(40)
    assert tooltip.is_visible() and tooltip.inner_text().strip()
    assert info.get_attribute('aria-describedby')=='themescope-tooltip'
    assert info.get_attribute('aria-expanded')=='true'
    page.keyboard.press('Escape')
    page.wait_for_timeout(140)
    assert not tooltip.is_visible() and info.get_attribute('aria-expanded')=='false'
    info.click()
    page.wait_for_timeout(40)
    assert info.get_attribute('aria-expanded')=='true' and tooltip.is_visible()
    page.mouse.move(5,5)
    assert tooltip.is_visible(), 'click should pin the field tooltip'
    info.click()
    page.wait_for_timeout(140)
    assert not tooltip.is_visible(), 'second click should unpin and dismiss the tooltip'
    assert info.get_attribute('aria-describedby') is None
    page.mouse.move(4,4)
    page.wait_for_timeout(140)
    for info_index, button in enumerate(page.locator('#theme-head .info-button').all()):
        button.hover()
        page.wait_for_timeout(140)
        assert tooltip.is_visible() and tooltip.inner_text().strip(), (info_index, button.get_attribute('id'), tooltip.get_attribute('class'), button.get_attribute('aria-expanded'), tooltip.evaluate('(e)=>({text:e.textContent,visibility:getComputedStyle(e).visibility,opacity:getComputedStyle(e).opacity,rect:e.getBoundingClientRect().toJSON(),aria:e.getAttribute("aria-hidden")})'))
        assert button.get_attribute('aria-describedby')=='themescope-tooltip'
        assert button.get_attribute('title')==tooltip.inner_text()
        box=tooltip.bounding_box()
        assert box['x'] >= 0 and box['y'] >= 0 and box['x']+box['width'] <= page.viewport_size['width']+1 and box['y']+box['height'] <= page.viewport_size['height']+1, box
        assert page.evaluate("el => el.parentElement === document.body && getComputedStyle(el).position === 'fixed'",tooltip.element_handle())
        page.mouse.move(4,4)
        page.wait_for_timeout(140)
        assert not tooltip.is_visible()
    info.focus()
    page.locator('#theme-direction').focus()
    assert not tooltip.is_visible(), 'moving focus out of the info button should close the tooltip'
    edge_buttons=[page.locator('#theme-head th.col-rank .info-button'),page.locator('#theme-head th.col-facts .info-button')]
    for index, edge in enumerate(edge_buttons):
        if index==1:
            page.locator('.theme-table-wrap').evaluate('(el) => el.scrollLeft = el.scrollWidth')
        edge.hover()
        page.wait_for_timeout(140)
        assert tooltip.is_visible()
        box=tooltip.bounding_box()
        assert box['x'] >= 0 and box['x']+box['width'] <= page.viewport_size['width']+1 and box['y'] >= 0 and box['y']+box['height'] <= page.viewport_size['height']+1, box
        assert page.evaluate("el => el.parentElement === document.body",tooltip.element_handle())
        page.mouse.move(4,4)
        page.wait_for_timeout(140)
        assert not tooltip.is_visible()
    for width in (1920,1600,1440,1280,1024,390):
        page.set_viewport_size({'width':width,'height':1000 if width>600 else 844})
        page.locator('.theme-table-wrap').evaluate('(el) => el.scrollLeft = 0')
        assert_table_layout(page,'.theme-table-wrap','themes',width)
    page.set_viewport_size({'width':1600,'height':1000})
    page.click('#mode')
    assert page.locator('html').get_attribute('data-mode')=='light'
    page.screenshot(path=str(screenshots_dir/'themes-1600-light.png'))
    page.click('#mode')
    rows=page.locator('#theme-body tr[data-theme]')
    if rows.count():
        page.select_option('#theme-sort','theme_score')
        page.click('#theme-direction')
        assert rows.count() >= 1
        assert '1M' in page.locator('#theme-head').inner_text()
        assert 'Rk−5D' in page.locator('#theme-head').inner_text()
        assert page.locator('#theme-body .score-chip').count() > 0
        assert not page.locator('#watchlist-navigation #back-to-themes').count()
        with page.expect_download() as download:
            page.click('#theme-visible-csv')
        assert Path(download.value.path()).stat().st_size > 0
        page.fill('#theme-search','no-such-theme')
        assert page.locator('#theme-body tr[data-theme]').count()==0
        page.fill('#theme-search','')
        page.locator('#theme-body tr[data-theme]').first.click()
        assert page.locator('#watchlist').is_visible()
        assert not page.locator('#active-name').inner_text().startswith('Watchlist ·')
        assert page.locator('#app-back').inner_text() == 'Back'
        assert page.locator('#previous-theme').inner_text() == 'Previous'
        assert page.locator('#next-theme').inner_text() == 'Next'
        assert page.locator('#app-back svg, #previous-theme svg, #next-theme svg').count() == 0
        assert not page.locator('#app-back').is_disabled()
        page.click('#app-back')
        assert page.locator('#sectors-themes').is_visible()
        assert page.locator('#theme-sort').input_value()=='theme_score'
        assert page.locator('#theme-direction').inner_text().startswith('Ascending')
        page.go_forward()
        assert page.locator('#watchlist').is_visible()
        assert page.locator('#watchlist-theme-selector optgroup[label="Sectors"]').count()==1
        assert page.locator('#watchlist-theme-selector optgroup[label="Themes"]').count()==1
        assert page.locator('#active-summary .rs-spark-row').count()==1
        current=page.locator('#active-name').inner_text()
        options=page.locator('#watchlist-theme-selector option:not([disabled])')
        if options.count()>1:
            page.select_option('#watchlist-theme-selector',options.nth(1).get_attribute('value'))
            assert page.locator('#active-name').inner_text()!=current
            page.click('#next-theme')
            assert page.locator('#active-name').inner_text()
        assert '20-stock capacity and 15-row default' not in page.inner_text('body')
        assert page.locator('#watchlist-message').inner_text() in ('ETF-only exposure. No stock drilldown is configured.', 'No reviewed companies passed the current stock eligibility rules.', 'Stock drilldown unavailable this run because the configured company list could not be retrieved.', '')

    page.click('.side-nav a[data-page="watchlist"]')
    selected_watchlist=next((row for row in snapshot_data.get('themes',[]) if row.get('selected')),None)
    assert selected_watchlist, 'browser fixture needs a populated watchlist to verify its table geometry'
    page.select_option('#watchlist-theme-selector',selected_watchlist['id'])
    assert page.locator('#stock-table-wrap').is_visible()
    page.set_viewport_size({'width':1600,'height':1000})
    page.screenshot(path=str(screenshots_dir/'watchlist-1600-dark.png'))
    for width in (1920,1600,1440,1280,1024,390):
        page.set_viewport_size({'width':width,'height':1000 if width>600 else 844})
        page.locator('#stock-table-wrap').evaluate('(el) => el.scrollLeft = 0')
        assert_table_layout(page,'#stock-table-wrap','watchlist',width)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(screenshots_dir/'watchlist-390-dark.png'))
    page.set_viewport_size({'width':1600,'height':1000})
    page.click('#mode');assert page.locator('html').get_attribute('data-mode')=='light'
    page.screenshot(path=str(screenshots_dir/'watchlist-1600-light.png'))
    page.click('#mode');assert page.locator('html').get_attribute('data-mode')=='dark'

    no_membership=next((row for row in snapshot_data.get('themes',[]) if not row.get('selected') and row.get('stock_drilldown_status')=='not_configured'),None)
    if no_membership:
        page.select_option('#watchlist-theme-selector',no_membership['id'])
        assert page.locator('#watchlist-message').inner_text()=='ETF-only exposure. No stock drilldown is configured.'
        assert page.locator('#stock-table-wrap').is_hidden(), 'an unconfigured list must not render unavailable placeholder rows'
        assert page.locator('#active-summary .summary-scores').count()==1
        assert page.locator('#active-summary .summary-returns').count()==1
    no_eligible=next((row for row in snapshot_data.get('themes',[]) if not row.get('selected') and row.get('stock_drilldown_status')=='no_eligible'),None)
    if no_eligible:
        page.select_option('#watchlist-theme-selector',no_eligible['id'])
        assert page.locator('#watchlist-message').inner_text()=='No reviewed companies passed the current stock eligibility rules.'
        assert page.locator('#stock-table-wrap').is_hidden()
    page.select_option('#watchlist-theme-selector',selected_watchlist['id'])
    page.set_viewport_size({'width':390,'height':844})
    assert page.locator('#previous-theme').is_visible()
    assert page.locator('#next-theme').is_visible()
    for control in ('#app-back','#previous-theme','#next-theme'):
        assert page.locator(control).bounding_box()['width'] > 0
        assert page.evaluate('(selector) => getComputedStyle(document.querySelector(selector)).fontFamily', control) == page.evaluate('getComputedStyle(document.body).fontFamily')
    if not page.locator('#stock-table-wrap').is_hidden():
        page.select_option('#pool','20');page.select_option('#pool','15')
        page.select_option('#ema-filter','above21');page.select_option('#ema-filter','all')
        page.fill('#stock-search','MSFT');page.fill('#stock-search','')
        page.click('#stock-direction')
        with page.expect_download() as download:
            page.click('#csv')
        assert Path(download.value.path()).stat().st_size > 0
        with page.expect_download() as download:
            page.click('#tv')
        assert Path(download.value.path()).stat().st_size > 0

    with page.expect_download() as download:
        page.click('a[href="run_bundle.zip"]')
    with zipfile.ZipFile(download.value.path()) as bundle:
        names=set(bundle.namelist())
        assert {'dashboard.html','themes.csv','registry_audit.csv','latest_snapshot.json','raw_inputs.json','iwm_breadth_prices.csv.gz','Inter-LICENSE.txt'} <= names
        assert 'sectors.csv' not in names and 'industries.csv' not in names

    page.set_viewport_size({'width':1600,'height':1000})
    page.click('#mode');assert page.locator('html').get_attribute('data-mode')=='light'
    page.screenshot(path=str(screenshots_dir/'watchlist-1600-light-reload.png'))
    page.reload();page.wait_for_timeout(400)
    assert page.locator('html').get_attribute('data-mode')=='light'
    bad = re.sub(r'(<script id="snapshot-data" type="application/json">).*?(</script>)', lambda m: m[1] + '{"session_date":null,"sources":{"source_errors":{"charts":{"SPY":"HTTP 429"}}}}' + m[2], path.read_text(encoding='utf-8'), flags=re.S)
    page.route(url, lambda route: route.fulfill(status=200, content_type='text/html', body=bad))
    page.reload()
    assert 'Market data unavailable' in page.inner_text('#status')
    assert 'Loading' not in page.inner_text('body')
    assert page.locator('section:visible').count()==0
    page.unroute(url)
    external=[u for u in requests if u.startswith(('http:','https:','ws:','wss:')) and not u.startswith(f'http://127.0.0.1:{server.server_port}/')]
    assert not external, external
    assert not errors, errors
    request_summary=[]
    for request_url in requests:
        if request_url.startswith('data:font/woff2;base64,'):
            summary='data:font/woff2 (embedded)'
        elif request_url.startswith(f'http://127.0.0.1:{server.server_port}/'):
            summary=Path(request_url.split('?',1)[0]).name + ' (local loopback)'
        else:
            summary=request_url
        request_summary.append(summary)
    result={'file_scheme_note':'Managed Chromium policy blocks file://; exact exported bytes served over loopback for verification', 'method':'Chromium DevTools Protocol Network.requestWillBeSent (Network panel backend)','runtime_environment':platform.platform(),'browser':'Chromium '+browser.version,'windows_chrome_verified':False,'embedded_font_loaded':True,'responsive_table_checks':layout_results,'open_and_reload_external_requests':external,'requests':request_summary,'javascript_errors':errors,'interaction_checks':'passed'}
    Path('/tmp/themescope-browser-verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    browser.close()
server.shutdown()
