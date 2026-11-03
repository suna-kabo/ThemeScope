"""Current UI acceptance: one drilldown, contributing inputs, grouped downloads."""
import argparse,copy,http.server,json,shutil,socketserver,threading,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('dashboard',type=Path);root=parser.parse_args().dashboard.resolve().parent
    snapshot=json.loads((root/'latest_snapshot.json').read_text(encoding='utf-8'));out=root/'terminal_checks';out.mkdir(exist_ok=True)
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=socketserver.TCPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(root),**kw));threading.Thread(target=server.serve_forever,daemon=True).start()
    errors=[];requests=[];screenshots=0
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':900})
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
            url=f'http://127.0.0.1:{server.server_address[1]}/dashboard.html';page.goto(url)
            assert 'initialization failed' not in page.locator('#status').inner_text()
            page.click('.side-nav [data-page="daily-plan"]')
            assert page.locator('#daily-plan-title').inner_text()=="Today's Plan: "+snapshot['decision']['market_classification']
            assert page.locator('#why-result,#divergence-context,#daily-methodology').count()==0
            for key,ids in snapshot['decision']['primary_groups'].items():
                group=page.locator('[data-priority-group="'+key+'"]')
                assert group.count()==bool(ids)
                if ids:assert group.locator('tr:not(.priority-group-heading) td:first-child [data-daily-theme]').evaluate_all('es=>es.map(e=>e.dataset.dailyTheme)')==ids
            assert page.locator('#decision-path .decision-row').count()==len(snapshot['decision']['decision_path'])
            assert 'IWM' not in page.locator('#decision-path').inner_text()
            if snapshot['decision']['matrix_rule_id'].startswith('unanimous-'):assert 'Breadth' not in page.locator('#decision-path').inner_text()
            assert page.locator('#qualification-summary a').count()==bool(snapshot['daily_primary_research']['combined_file'])
            if snapshot['daily_primary_research']['combined_file']:
                with page.expect_download() as info:page.click('#qualification-summary a')
                assert Path(info.value.path()).read_bytes()==(root/snapshot['daily_primary_research']['combined_file']).read_bytes()
                assert Path(info.value.path()).read_text(encoding='utf-8').startswith('###')
            assert page.locator('#expected-earnings-content [data-earnings-theme]').count()==0
            assert 'Primary themes' not in page.locator('#expected-earnings-content').inner_text()
            page.click('.side-nav [data-page="watchlist"]')
            assert page.locator('#stock-view').count()==0;assert page.locator('#rs-filter').input_value()=='All'
            assert page.locator('#stock-head th').count()==14
            for label in ['1W','1M vs ETF (pp)','3M vs ETF (pp)','Earnings']:assert label in page.locator('#stock-head').inner_text()
            for label in ['Avg $Vol30','Turnover 1D','Rel Vol']:assert label not in page.locator('#stock-head').inner_text()
            selected=next(t for t in snapshot['themes'] if t['id']==page.locator('#watchlist-theme-selector').input_value())
            first_id=selected['id'];member=next(r for r in selected['selected'] if r['price_close'] is not None)
            breadth=page.locator('#active-summary .summary-breadth').inner_text()
            page.select_option('#stock-sort','return21')
            rows=page.locator('#stock-body tr').evaluate_all('es=>es.map(e=>({ticker:e.querySelector(".col-ticker a,.col-ticker b").textContent,slot:e.querySelector(".col-rank").textContent}))')
            positions={r['ticker']:str(r['selection_slot']) for r in selected['selected']};assert all(positions[r['ticker']]==r['slot'] for r in rows)
            for classification in ['All','Outperforming','Underperforming','Flat','Unavailable']:
                page.select_option('#rs-filter',classification);page.fill('#stock-search',member['ticker']);page.select_option('#ema-filter','above21')
                expected=[r for r in selected['selected'] if (classification=='All' or r['weighted_vs_etf']==classification) and member['ticker'].lower() in (r['ticker']+' '+r.get('company','')).lower() and r.get('above_ema21') is True]
                assert page.locator('#stock-body tr[data-stock-symbol]').count()==len(expected)
                assert page.locator('#coverage').inner_text()==f'{len(expected)} of {len(selected["selected"])} stocks'
                assert page.locator('#active-summary .summary-breadth').inner_text()==breadth
            page.fill('#stock-search','');page.select_option('#ema-filter','all');page.select_option('#rs-filter','All')
            page.click('#next-theme');page.go_back();assert page.locator('#watchlist-theme-selector').input_value()==first_id
            assert page.locator('#stock-sort').input_value()=='return21'
            with page.expect_download() as info:page.click('#tv')
            assert Path(info.value.path()).read_text().strip().split(',')==[selected['tradingview_symbol']]+[r['tradingview_symbol'] for r in selected['selected']]
            page.click('.side-nav [data-page="methodology"]')
            assert page.locator('.market-matrix tbody tr').count()==64;assert page.locator('.market-matrix .active-cell').count()==1
            for heading in ['Market classification','Breadth calculation and validity','Theme Score','Primary research policy','Configured-stock selection','Stock versus ETF performance','Daily exports','History and missing data']:
                assert heading in page.locator('#methodology-content').inner_text()
            page.evaluate('window.scrollTo(0,450)');page.wait_for_timeout(150);y=page.evaluate('window.scrollY')
            page.click('.brand');assert page.locator('#market').is_visible();page.go_back();assert abs(page.evaluate('window.scrollY')-y)<3
            # Old view/filter settings retain route/selection but never acquire new semantics.
            for old_filter in ['Outperforming','Mixed','Missing']:
                context=browser.new_context();context.add_init_script("history.replaceState({themescope:true,index:0,view:"+json.dumps({'ui_schema':4,'session_date':snapshot['session_date'],'page':'watchlist','selected_theme_id':first_id,'stock_view':'relative','rs_filter':old_filter,'daily_methodology_open':True,'route_state':{'rsFilter':old_filter,'key':'adv30_usd','y':0}})+"},'',location.href)")
                trial=context.new_page();trial.on('pageerror',lambda e:errors.append(str(e)));trial.goto(url+'#watchlist')
                assert trial.locator('#rs-filter').input_value()=='All';assert trial.locator('#stock-view').count()==0
                assert trial.locator('#watchlist-theme-selector').input_value()==first_id;context.close()
            # Zero, one and many populated groups without fixed empty panels.
            from src.themescope.site_output import render_html
            repository=Path(__file__).resolve().parents[1]
            primary_ids=[t['id'] for t in snapshot['themes'] if t['research_priority']['category']=='primary']
            for label,groups in [('zero',{'new':[],'continuing':[],'unavailable':[]}),('one',{'new':[],'continuing':[],'unavailable':primary_ids[:1]}),('many',{'new':primary_ids[::3],'continuing':primary_ids[1::3],'unavailable':primary_ids[2::3]})]:
                fixture=copy.deepcopy(snapshot);fixture['decision']['primary_groups']=groups
                if label=='zero':fixture['daily_primary_research']['combined_file']=None
                filename='layout-fixture-'+label+'.html';(out/filename).write_text(render_html(fixture,repository),encoding='utf-8')
                page.goto(url.replace('dashboard.html','terminal_checks/'+filename)+'#daily-plan')
                assert page.locator('[data-priority-group]').count()==sum(bool(ids) for ids in groups.values())
                assert page.locator('.primary-plan-table tbody tr:not(.priority-group-heading)').count()==sum(map(len,groups.values()))
                if label=='zero':assert page.locator('#qualification-summary a').count()==0
            page.goto(url)
            for mode in ['dark','light']:
                if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
                for width,height in [(1366,768),(1440,900),(1920,1080),(390,844)]:
                    page.set_viewport_size({'width':width,'height':height})
                    for route in ['daily-plan','sectors-themes','watchlist','methodology']:
                        page.click('.side-nav [data-page="'+route+'"]');page.evaluate('window.scrollTo(0,0)')
                        assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
                        if route in ['sectors-themes','watchlist']:
                            prefix='theme' if route=='sectors-themes' else 'stock';count=15 if prefix=='theme' else 14
                            assert page.locator('#'+prefix+'-head th').count()==count
                            a=page.locator('#'+prefix+'-head th').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().x)')
                            b=page.locator('#'+prefix+'-body tr').first.locator('td').evaluate_all('es=>es.map(e=>e.getBoundingClientRect().x)')
                            assert len(a)==len(b) and all(abs(x-y)<.6 for x,y in zip(a,b))
                            header_classes=page.locator('#'+prefix+'-head th').evaluate_all('es=>es.map(e=>e.className)')
                            body_classes=page.locator('#'+prefix+'-body tr').first.locator('td').evaluate_all('es=>es.map(e=>e.className)')
                            assert header_classes==body_classes
                            if prefix=='theme':
                                assert page.locator('#theme-head [data-sort]').evaluate_all('es=>es.every(e=>e.scrollWidth<=e.clientWidth+1)')
                                assert page.locator('#theme-body td.col-return,#theme-body td.col-day-change').evaluate_all('es=>es.every(e=>e.scrollWidth<=e.clientWidth+1)')
                        if route=='sectors-themes':
                            assert '1W' not in page.locator('#theme-head').inner_text();assert page.locator('.optional-scan-exports').count()==0
                            assert page.locator('.collection-downloads a').count()==3
                        page.screenshot(path=str(out/f'{route}-{mode}-{width}.png'));screenshots+=1
            assert not errors,errors
            assert not [r for r in requests if r.startswith(('http:','https:')) and not r.startswith('http://127.0.0.1:')]
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'javascript_errors':errors,'automatic_external_requests':0,'screenshots':screenshots,'native_expanded_dropdown_visually_verified':False,'platform_import_tested':False,'migration_filters_downloads_scroll':'passed'}))

if __name__=='__main__':main()
