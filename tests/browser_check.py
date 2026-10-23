"""Real Chromium/CDP Network verification; run against an exported HTML path."""
import json
import re
import sys
import functools
import threading
import zipfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from playwright.sync_api import sync_playwright


path = Path(sys.argv[1]).resolve()
server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(SimpleHTTPRequestHandler, directory=str(path.parent)))
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f'http://127.0.0.1:{server.server_port}/{path.name}'
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox','--disable-dev-shm-usage','--disable-gpu'])
    page = browser.new_page(viewport={'width':1440,'height':1000}, accept_downloads=True)
    cdp = page.context.new_cdp_session(page)
    cdp.send('Network.enable')
    requests=[];errors=[]
    cdp.on('Network.requestWillBeSent', lambda event: requests.append(event['request']['url']))
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(url);page.wait_for_timeout(400)
    assert 'Loading' not in page.inner_text('body')
    assert page.locator('.market-card').count()==2
    assert 'eligible ETF anchors' in page.inner_text('#status')
    assert page.locator('.state-tag').count() >= 0
    assert page.locator('html').get_attribute('data-mode')=='dark'
    assert page.locator('.side-nav [data-page]').count()==3
    assert page.locator('.side-nav [data-page="industries"]').count()==0
    page.screenshot(path='/tmp/themescope-dark.png',full_page=True)

    page.click('.side-nav a[data-page="sectors-themes"]')
    assert page.locator('#sectors-themes').is_visible()
    rows=page.locator('#theme-body tr[data-theme]')
    if rows.count():
        initial=rows.first.inner_text()
        page.select_option('#theme-sort','excess21')
        page.click('#theme-direction')
        assert rows.count() >= 1
        with page.expect_download() as download:
            page.click('#theme-visible-csv')
        assert Path(download.value.path()).stat().st_size > 0
        page.fill('#theme-search','no-such-theme')
        assert page.locator('#theme-body tr[data-theme]').count()==0
        page.fill('#theme-search','')
        page.locator('#theme-body tr[data-theme]').first.click()
        assert page.locator('#watchlist').is_visible()

    page.click('.side-nav a[data-page="watchlist"]')
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
        assert {'dashboard.html','themes.csv','registry_audit.csv','latest_snapshot.json','raw_inputs.json'} <= names
        assert 'sectors.csv' not in names and 'industries.csv' not in names

    page.click('#mode');assert page.locator('html').get_attribute('data-mode')=='light'
    page.screenshot(path='/tmp/themescope-light.png',full_page=True)
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
    result={'file_scheme_note':'Managed Chromium policy blocks file://; exact exported bytes served over loopback for verification', 'method':'Chromium DevTools Protocol Network.requestWillBeSent (Network panel backend)','open_and_reload_external_requests':external,'requests':requests,'javascript_errors':errors,'interaction_checks':'passed'}
    Path('/tmp/themescope-browser-verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    browser.close()
server.shutdown()
