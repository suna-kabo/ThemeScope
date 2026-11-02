"""Real-browser acceptance for the focused scanning release."""
import argparse,http.server,json,shutil,socketserver,threading
from pathlib import Path
from playwright.sync_api import sync_playwright


def main():
    parser=argparse.ArgumentParser();parser.add_argument('dashboard',type=Path);args=parser.parse_args()
    dashboard=args.dashboard.resolve();root=dashboard.parent;s=json.loads((root/'latest_snapshot.json').read_text())
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=socketserver.TCPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(root),**kw));threading.Thread(target=server.serve_forever,daemon=True).start()
    errors=[];requests=[];artifacts=root/'scanning_checks';artifacts.mkdir(exist_ok=True)
    try:
        with sync_playwright() as p:
            b=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1536,'height':864},has_touch=True)
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));page.goto(f'http://127.0.0.1:{server.server_address[1]}/dashboard.html')
            page.click('[data-page="daily-plan"]')
            assert page.locator('#primary-body tr[data-primary-symbol]').count()==s['daily_primary']['unique_count']
            multi=next(r for r in s['daily_primary']['candidates'] if len(r['primary_contexts'])>1)
            row=page.locator('#primary-body tr[data-primary-symbol="'+multi['tradingview_symbol']+'"]')
            selected=multi['primary_contexts'][-1];row.locator('select').select_option(selected['theme_id'])
            cell=page.locator('#primary-body tr[data-primary-symbol="'+multi['tradingview_symbol']+'"] td').nth(7)
            assert cell.inner_text()==('+' if selected['excess21_pp']>0 else '')+f'{selected["excess21_pp"]:.2f} pp'
            page.fill('#primary-search',multi['ticker'])
            assert page.locator('#primary-body tr[data-primary-symbol]').count()>=1
            with page.expect_download() as info:page.click('#primary-export')
            tokens=Path(info.value.path()).read_text().strip().split(',')
            assert tokens==[r['tradingview_symbol'] for r in s['daily_primary']['candidates']]
            page.fill('#primary-search','');page.select_option('#primary-context',selected['theme_id'])
            expected=sum(any(c['theme_id']==selected['theme_id'] for c in r['primary_contexts']) for r in s['daily_primary']['candidates'])
            assert page.locator('#primary-body tr[data-primary-symbol]').count()==expected
            page.select_option('#primary-context','All')
            link=page.locator('[data-primary-theme]').first;theme_id=link.get_attribute('data-primary-theme');link.click()
            assert page.locator('#watchlist-theme-selector').input_value()==theme_id
            assert page.locator('#watchlist').is_visible()
            page.fill('#stock-search','a');page.select_option('#stock-view','relative');assert page.locator('#stock-head th').count()==11
            page.select_option('#rs-filter','Missing');page.select_option('#rs-filter','All');page.fill('#stock-search','')
            selected_theme=next(t for t in s['themes'] if t['id']==theme_id)
            assert page.locator('#stock-body tr').count()==len(selected_theme['selected'])
            page.select_option('#stock-sort','excess63_pp');page.select_option('#stock-view','performance');page.select_option('#stock-view','relative')
            assert page.locator('#stock-sort').input_value()=='excess63_pp'
            page.go_back();assert page.locator('#daily-plan').is_visible();page.go_forward();assert page.locator('#watchlist').is_visible()
            for mode in ('dark','light'):
                page.set_viewport_size({'width':1536,'height':864})
                if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
                for w,h in ((1920,1080),(1536,864),(1366,768),(390,844)):
                    page.set_viewport_size({'width':w,'height':h})
                    page.click('[data-page="watchlist"]')
                    for view,cols in (('performance',15),('relative',11)):
                        page.select_option('#stock-view',view)
                        assert page.locator('#stock-head th').count()==cols
                        if w>=1536:
                            assert page.locator('.stock-table-wrap').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                            a=page.locator('#stock-head th').evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))')
                            c=page.locator('#stock-body tr').first.locator('td').evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))')
                            assert len(a)==len(c) and all(abs(x['x']-y['x'])<.6 and abs(x['w']-y['w'])<.6 for x,y in zip(a,c))
                        page.screenshot(path=str(artifacts/f'{view}-{mode}-{w}.png'))
                    page.click('[data-page="daily-plan"]');page.locator('#primary-candidates-title').scroll_into_view_if_needed()
                    if w>=1536:
                        assert page.locator('.candidate-table-wrap').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                        hb=page.locator('#primary-head th').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().x)')
                        rb=page.locator('#primary-body tr').first.locator('td').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().x)')
                        assert len(hb)==len(rb)==9 and all(abs(x-y)<.6 for x,y in zip(hb,rb))
                    page.screenshot(path=str(artifacts/f'primary-{mode}-{w}.png'))
                    page.locator('#expected-earnings').scroll_into_view_if_needed()
                    if not page.locator('#expected-earnings').get_attribute('open')=='':
                        page.locator('#expected-earnings > summary').click()
                    page.locator('#expected-earnings').scroll_into_view_if_needed()
                    assert 'Verify dates' in page.locator('#expected-earnings-content').inner_text()
                    page.screenshot(path=str(artifacts/f'earnings-{mode}-{w}.png'))
                    assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
            assert not errors,errors
            assert not [r for r in requests if r.startswith(('http:','https:')) and not r.startswith('http://127.0.0.1:')]
            b.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'javascript_errors':errors,'automatic_external_requests':0,'screenshots':32,'primary_count':s['daily_primary']['unique_count']}))

if __name__=='__main__':main()
