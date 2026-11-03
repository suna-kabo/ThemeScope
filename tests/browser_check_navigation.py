"""Real Chromium acceptance for individual exports, ETF 1D and offline navigation."""
import argparse
import copy
import http.server
import json
from pathlib import Path
import re
import shutil
import socketserver
import threading
import zipfile

from playwright.sync_api import sync_playwright, expect, Error


def check_local_files(browser, root):
    """The extracted bundle must work from file:// without a local server."""
    page=browser.new_page();errors=[];requests=[]
    page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
    try:page.goto((root/'dashboard.html').as_uri())
    except Error as error:
        page.close()
        if 'ERR_BLOCKED_BY_ADMINISTRATOR' in str(error):return 'blocked_by_managed_browser_policy'
        raise
    page.click('[data-page="watchlist"]')
    with page.expect_download() as info:page.click('#tv')
    selected=page.locator('#watchlist-theme-selector').input_value()
    snapshot=json.loads((root/'latest_snapshot.json').read_text(encoding='utf-8'))
    item=next(r for r in snapshot['export_manifest'] if r.get('theme_id')==selected)
    assert Path(info.value.path()).read_bytes()==(root/item['file']).read_bytes()
    page.click('[data-page="sectors-themes"]')
    with page.expect_download() as info:page.click('#all-individual-watchlists')
    assert Path(info.value.path()).read_bytes()==(root/'individual_theme_watchlists.zip').read_bytes()
    assert not errors,errors
    assert not [r for r in requests if r.startswith(('http:','https:'))]
    page.close()
    return 'passed'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('dashboard',type=Path)
    root=parser.parse_args().dashboard.resolve().parent
    snapshot=json.loads((root/'latest_snapshot.json').read_text(encoding='utf-8'))
    artifacts=root/'navigation_checks';artifacts.mkdir(exist_ok=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=socketserver.TCPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(root),**kw))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{server.server_address[1]}/dashboard.html'
    errors=[];requests=[];screenshots=0
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1536,'height':864},has_touch=True)
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
            page.goto(url);page.click('[data-page="sectors-themes"]')
            assert 'initialization failed' not in page.locator('#status').inner_text()
            expect(page.locator('#all-individual-watchlists')).to_be_visible()
            with page.expect_download() as info:page.click('#all-individual-watchlists')
            with zipfile.ZipFile(info.value.path()) as archive:
                assert len(archive.namelist())==len(snapshot['themes']) and archive.testzip() is None
            assert 'Download All Stocks' in page.locator('#daily-data-export-links').inner_text()
            assert page.locator('#theme-head .col-day-change .header-label').inner_text()=='1D %'
            page.click('#theme-head [data-sort="daily_change"]')
            ordered=sorted(snapshot['themes'],key=lambda t:(-t['daily_change'],t['id']))
            assert page.locator('#theme-body tr').first.get_attribute('data-theme')==ordered[0]['id']
            with page.expect_download() as info:page.click('#theme-visible-csv')
            import csv
            rows=list(csv.DictReader(Path(info.value.path()).open()))
            assert float(rows[0]['change_1d_pct'])==ordered[0]['daily_change']*100

            page.click('[data-page="watchlist"]')
            find=page.locator('#watchlist-theme-search')
            find.fill('LLY')
            options=page.locator('#navigation-results [data-navigation-kind="stock"][data-symbol="NYSE:LLY"]')
            expected=[t for t in snapshot['themes'] if any(r['ticker']=='LLY' for r in t['selected'])]
            assert options.count()==len(expected)>=2
            assert len(set(options.evaluate_all('es=>es.map(e=>e.dataset.themeId)')))==len(expected)
            assert find.get_attribute('aria-expanded')=='true'
            find.press('ArrowDown');active=find.get_attribute('aria-activedescendant')
            assert active and page.locator('#'+active).get_attribute('aria-selected')=='true'
            target_theme=page.locator('#'+active).get_attribute('data-theme-id')
            find.press('Enter')
            assert page.locator('#watchlist-theme-selector').input_value()==target_theme
            expect(page.locator('#stock-body .navigation-target')).to_be_visible()
            assert page.locator('#stock-view').count()==0
            assert page.locator('#stock-body tr').count()>1
            assert find.get_attribute('aria-expanded')=='false'

            # Same-theme target must reveal a hidden member while preserving Back state.
            selected=next(t for t in snapshot['themes'] if t['id']==target_theme)
            target=next(r for r in selected['selected'] if r['ticker']=='LLY')
            page.select_option('#stock-sort','return63')
            page.fill('#stock-search','NO_SUCH_STOCK')
            failing_ema='below21' if target['price_close']>target['ema21'] else 'above21'
            page.select_option('#ema-filter',failing_ema)
            failing_rs=next(r for r in ['Flat','Unavailable','Outperforming','Underperforming'] if r!=target['weighted_vs_etf'])
            page.select_option('#rs-filter',failing_rs)
            prior_y=page.evaluate('window.scrollY')
            find.fill('LLY')
            page.locator('#navigation-results [data-theme-id="'+target_theme+'"][data-navigation-kind="stock"]').click()
            assert page.locator('#stock-search').input_value()==''
            assert page.locator('#ema-filter').input_value()=='all'
            assert page.locator('#rs-filter').input_value()=='All'
            assert 'Filters adjusted to reveal LLY' in page.locator('#navigation-status').inner_text()
            expect(page.locator('#stock-body .navigation-target')).to_be_visible()
            assert page.locator('#stock-body tr').count()==len(selected['selected'])
            page.go_back()
            assert page.locator('#stock-search').input_value()=='NO_SUCH_STOCK'
            assert page.locator('#ema-filter').input_value()==failing_ema
            assert page.locator('#rs-filter').input_value()==failing_rs
            assert page.locator('#stock-sort').input_value()=='return63'
            assert abs(page.evaluate('window.scrollY')-prior_y)<3
            page.go_forward();assert page.locator('#stock-search').input_value()==''
            page.fill('#stock-search','LLY')
            find.fill('LLY');page.locator('#navigation-results [data-theme-id="'+target_theme+'"][data-navigation-kind="stock"]').click()
            assert page.locator('#stock-search').input_value()=='LLY' # Keep a filter that already reveals the target.
            page.fill('#stock-search','')

            # Unavailable daily rows remain navigable; view choice persists through touch selection.
            missing_theme,missing=next((t,r) for t in snapshot['themes'] for r in t['selected'] if r['metric_status']=='unavailable')
            find.fill(missing['ticker'])
            page.locator('#navigation-results [data-theme-id="'+missing_theme['id']+'"][data-symbol="'+missing['tradingview_symbol']+'"]').tap()
            assert page.locator('#stock-view').count()==0
            expect(page.locator('#stock-body .navigation-target')).to_be_visible()
            assert page.locator('#stock-body .navigation-target .col-ticker').inner_text().startswith(missing['ticker'])
            with page.expect_download() as info:page.click('#tv')
            item=next(i for i in snapshot['export_manifest'] if i.get('theme_id')==missing_theme['id'])
            assert info.value.suggested_filename==Path(item['file']).name
            assert Path(info.value.path()).read_bytes()==(root/item['file']).read_bytes()

            find.fill('ZZZZ_NOT_FOUND');assert 'No matching stocks or themes.' in page.locator('#navigation-popup').inner_text()
            find.press('Escape');assert find.get_attribute('aria-expanded')=='false'
            find.fill('stock');page.mouse.click(1500,180);assert find.get_attribute('aria-expanded')=='false'
            find.fill('a');old=page.locator('#navigation-results [role="option"]').count()
            more=page.locator('#navigation-more button').first
            assert more.count()==1;more.click()
            assert page.locator('#navigation-results [role="option"]').count()>old
            shown=page.locator('#navigation-results [role="option"]').count()
            find.press('Tab');assert page.evaluate('document.activeElement.hasAttribute("data-navigation-more")'),page.evaluate('document.activeElement.outerHTML.slice(0,300)')
            page.keyboard.press('Enter');assert page.locator('#navigation-results [role="option"]').count()>shown
            find.press('ArrowUp');assert find.get_attribute('aria-activedescendant')
            find.press('Escape')
            # Theme navigation preserves its own scroll without a fabricated stock target.
            find.fill(selected['anchor'])
            page.locator('#navigation-results [data-navigation-kind="theme"][data-theme-id="'+selected['id']+'"]').click()
            assert page.locator('#stock-body .navigation-target').count()==0
            find.fill('');page.select_option('#rs-filter','All')

            for mode in ('dark','light'):
                page.set_viewport_size({'width':1536,'height':864})
                if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
                for width,height in [(1920,1080),(1536,864),(1366,768),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height})
                    page.click('[data-page="sectors-themes"]');page.evaluate('window.scrollTo(0,0)')
                    if width>=1536:
                        assert page.locator('.theme-table-wrap').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                        a=page.locator('#theme-head th').evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))')
                        b=page.locator('#theme-body tr').first.locator('td').evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))')
                        assert len(a)==len(b)==15 and all(abs(x['x']-y['x'])<.6 and abs(x['w']-y['w'])<.6 for x,y in zip(a,b))
                    if width<1536:
                        page.locator('.theme-table-wrap').evaluate("e=>{e.style.scrollMarginTop='70px';e.scrollIntoView({block:'start'});if(innerWidth<760)e.scrollLeft=260;}")
                    page.screenshot(path=str(artifacts/f'etf-day-{mode}-{width}.png'));screenshots+=1
                    page.click('[data-page="watchlist"]');find.fill('')
                    assert find.bounding_box()['y']>=page.locator('.topbar').bounding_box()['y']+page.locator('.topbar').bounding_box()['height']
                    page.screenshot(path=str(artifacts/f'placeholder-{mode}-{width}.png'));screenshots+=1
                    find.fill('LLY')
                    if width>=1366:assert find.bounding_box()['width']>=260
                    box=page.locator('#navigation-popup').bounding_box()
                    assert box and box['x']>=0 and box['y']>=0 and box['x']+box['width']<=width+1 and box['y']+box['height']<=height+1
                    page.screenshot(path=str(artifacts/f'find-{mode}-{width}.png'));screenshots+=1
                    page.locator('#navigation-results [data-theme-id="'+target_theme+'"][data-navigation-kind="stock"]').click()
                    expect(page.locator('#stock-body .navigation-target')).to_be_visible()
                    page.screenshot(path=str(artifacts/f'target-{mode}-{width}.png'));screenshots+=1
                    assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
            # Synthetic presentation edges are confined to a routed test document.
            synthetic=copy.deepcopy(snapshot)
            synthetic['themes'][0]['daily_change']=0;synthetic['themes'][1]['daily_change']=None
            synthetic['themes'][0]['name']='Unsafe <img src=x onerror=alert(1)> text'
            html=(root/'dashboard.html').read_text(encoding='utf-8')
            html=re.sub(r'(<script id="snapshot-data"[^>]*>).*?(</script>)',lambda m:m[1]+json.dumps(synthetic).replace('</','<\\/')+m[2],html,flags=re.S)
            page.route('**/synthetic.html',lambda route:route.fulfill(body=html,content_type='text/html'))
            page.goto(url.replace('dashboard.html','synthetic.html'))
            page.click('[data-page="sectors-themes"]')
            zero=page.locator('#theme-body tr[data-theme="'+synthetic['themes'][0]['id']+'"] .col-day-change')
            assert zero.inner_text()=='0.00%'
            assert zero.evaluate('e=>getComputedStyle(e).color')==page.locator('.caption').first.evaluate('e=>getComputedStyle(e).color')
            assert page.locator('#theme-body tr[data-theme="'+synthetic['themes'][1]['id']+'"] .col-day-change').inner_text()=='N/A'
            page.click('[data-page="watchlist"]');page.locator('#watchlist-theme-search').fill('Unsafe')
            assert page.locator('#navigation-popup img').count()==0
            assert '<img src=x' in page.locator('#navigation-results').inner_text()
            assert not errors,errors
            assert not [u for u in requests if u.startswith(('https:','http:')) and not u.startswith('http://127.0.0.1:')]
            local_files=check_local_files(browser,root)
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'javascript_errors':errors,'external_requests':0,'screenshots':screenshots,'keyboard_mouse_touch':'passed','hidden_target_and_back':'passed','direct_file_url':local_files}))


if __name__=='__main__':main()
