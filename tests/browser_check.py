"""Real Chromium/CDP Network verification; run against an exported HTML path."""
import json
import re
import zipfile
import sys
import functools
import threading
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
    assert page.locator('#theme-body tr').count()==6
    assert page.locator('#stock-body tr').count()>1
    assert 'Loading' not in page.inner_text('body')
    assert page.locator('.card').count()==2
    assert page.locator('html').get_attribute('data-mode')=='dark'
    page.screenshot(path='/tmp/themescope-dark.png',full_page=True)
    # Numeric sorting, stable ranks through filters, and missing-last are also unit tested.
    assert page.locator('#theme-sort').input_value()=='theme_score'
    page.select_option('#theme-sort','excess21')
    first=page.locator('#theme-body tr').first.inner_text()
    page.click('#theme-direction')
    assert page.locator('#theme-body tr').first.inner_text()!=first
    page.select_option('#level','Industry')
    assert page.locator('#theme-body tr[data-theme]').count()==3
    page.select_option('#level','All')
    page.fill('#theme-search','cloud')
    assert page.locator('#theme-body tr[data-theme]').count()==1
    page.click('#theme-body tr[data-theme]')
    assert 'Cloud' in page.inner_text('#active-name')
    page.fill('#theme-search','')
    page.select_option('#pool','20');page.select_option('#pool','all');page.select_option('#pool','15')
    page.select_option('#stock-trend','Downtrend');page.select_option('#stock-trend','All')
    page.select_option('#stock-relative','Outperforming');page.select_option('#stock-relative','All')
    page.fill('#stock-search','MSFT');page.fill('#stock-search','')
    page.select_option('#ema-filter','above21');page.select_option('#ema-filter','all')
    page.click('#stock-direction')
    assert page.locator('#stock-body a').first.get_attribute('href').startswith('https://www.tradingview.com/chart/?symbol=')
    for button in ['#csv','#tv','a[href="run_bundle.zip"]']:
        with page.expect_download() as download:
            page.click(button)
        assert Path(download.value.path()).stat().st_size>0
        if button.startswith('a['):
            with zipfile.ZipFile(download.value.path()) as bundle:
                assert 'dashboard.html' in bundle.namelist()
                assert len(bundle.namelist()) == 11
    page.click('#mode');assert page.locator('html').get_attribute('data-mode')=='light'
    page.screenshot(path='/tmp/themescope-light.png',full_page=True)
    page.reload();page.wait_for_timeout(400)
    assert page.locator('html').get_attribute('data-mode')=='light'
    # A supplied failed snapshot must show a concise failure, with no loading placeholders.
    bad = re.sub(r'(<script id="snapshot-data" type="application/json">).*?(</script>)', lambda m: m[1] + '{"session_date":null,"sources":{"source_errors":{"charts":{"SPY":"HTTP 429"}}}}' + m[2], path.read_text(encoding='utf-8'), flags=re.S)
    page.route(url, lambda route: route.fulfill(status=200, content_type='text/html', body=bad))
    page.reload()
    assert 'Market data unavailable' in page.inner_text('#status')
    assert 'HTTP 429' in page.inner_text('#status')
    assert 'Loading' not in page.inner_text('body')
    assert page.locator('section:visible').count()==0
    page.unroute(url)
    external=[u for u in requests if u.startswith(('http:','https:','ws:','wss:')) and not u.startswith(f'http://127.0.0.1:{server.server_port}/')]
    assert not external, external
    assert not errors, errors
    result={'file_scheme_note':'Managed Chromium policy blocks file://; exact exported bytes served on loopback for verification', 'method':'Chromium DevTools Protocol Network.requestWillBeSent (Network panel backend)','open_and_reload_external_requests':external,'requests':requests,'javascript_errors':errors,'interaction_checks':'passed'}
    Path('/tmp/themescope-browser-verification.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    browser.close()
