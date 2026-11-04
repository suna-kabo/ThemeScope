"""Actual generated CSV-v2 dashboard/site: liquidity must not become a UI filter."""
import argparse
import http.server
import json
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright,expect


def check(path):
    path=Path(path).resolve()
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(path.parent),**kw))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/';errors=[];external=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
            page=browser.new_page(viewport={'width':1440,'height':900})
            page.on('pageerror',lambda e:errors.append(str(e)))
            page.on('request',lambda r:external.append(r.url) if r.url.startswith(('http:','https:')) and not r.url.startswith(base) else None)
            page.goto(base+path.name)
            data=page.locator('#snapshot-data').evaluate('e=>JSON.parse(e.textContent)')
            theme,stock=next((t,s) for t in data['themes'] for s in t['selected'] if s['daily_stock_eligibility']['status']=='ineligible' and s['weighted_vs_etf']=='Outperforming')
            for mode in ('light','dark'):
                if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
                page.click('[data-page="watchlist"]');page.select_option('#watchlist-theme-selector',theme['id'])
                page.fill('#stock-search',stock['ticker']);page.select_option('#ema-filter','all');page.select_option('#rs-filter','Outperforming')
                row=page.locator('#stock-body tr[data-stock-symbol="'+stock['tradingview_symbol']+'"]');expect(row).to_be_visible()
                assert 'of '+str(len(theme['selected']))+' stocks' in page.locator('#coverage').inner_text()
                assert page.locator('#stock-head th').count()==14
                page.select_option('#rs-filter','Underperforming');assert page.locator('#stock-body tr[data-stock-symbol="'+stock['tradingview_symbol']+'"]').count()==0
                page.select_option('#rs-filter','Outperforming');expect(row).to_be_visible()
                page.click('[data-page="daily-plan"]');page.get_by_role('link',name='How this list is built',exact=True).click()
                text=page.locator('.primary-research-method').inner_text()
                assert 'BOTH' in text and '>= $10,000,000 USD' in text and '> 500,000 shares per trading session' in text
                assert 'including on measured ineligible rows' in text
            assert not errors,errors;assert not external,external
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'file':path.name,'measured_ineligible_outperformer_visible':'passed','vs_etf_independent_of_liquidity':'passed','watchlist_columns':14,'modes':['light','dark'],'javascript_errors':errors,'automatic_external_requests':len(external)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('files',nargs='+',type=Path)
    for path in parser.parse_args().files:check(path)
