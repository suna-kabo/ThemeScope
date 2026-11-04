"""Column-role geometry and actual weighted-filter behavior, over localhost."""
import argparse,copy,http.server,json,shutil,socketserver,sys,threading
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.themescope.relative_performance import weighted_excess
from src.themescope.site_output import render_html


def main():
    parser=argparse.ArgumentParser();parser.add_argument('dashboard',type=Path);args=parser.parse_args();run=args.dashboard.resolve().parent
    snapshot=json.loads((run/'latest_snapshot.json').read_text(encoding='utf-8'));out=run/'table_checks';out.mkdir(exist_ok=True)
    fixture=copy.deepcopy(snapshot);theme=next(t for t in fixture['themes'] if len(t['selected'])>=4)
    theme['name']='Long theme name for structural alignment and stable left edges'
    theme['returns']['21']['value']=0;theme['returns']['63']['value']=0;theme['selected']=theme['selected'][:4]
    for row,(one,three) in zip(theme['selected'],[(.02,-.01),(.01,-.03),(.02,-.03),(None,-.01)]):
        row['returns']['21']['value']=one;row['returns']['63']['value']=three;row['price_close']=20;row['ema21']=19;row['ema50']=18;row['above_ema21']=True;row['above_ema50']=True
        row['daily_change']=-.1234;row['market_cap_usd']=None if one is None else 2.5e9;row['atr14_pct']=None if one is None else 2.1
        row['excess21_pp']=None if one is None else one*100;row['excess63_pp']=three*100
        calculation=weighted_excess(row,theme);row.update(weighted_vs_etf=calculation['weighted_vs_etf'],weighted_excess_pp=calculation['weighted_excess_pp'])
    fixture['themes']=[theme];(out/'fixture.html').write_text(render_html(fixture,ROOT),encoding='utf-8')
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=socketserver.TCPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(run.parent),**kw));threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_address[1]}/';url=base+run.name+'/dashboard.html';errors=[];requests=[];screenshots=0;baseline_visibility=None
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=browser.new_page(viewport={'width':1440,'height':900})
            page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url))
            baseline=run.parent/'pre_table_alignment_backup/dashboard.html'
            if baseline.exists():
                page.goto(base+'pre_table_alignment_backup/dashboard.html#watchlist');baseline_visibility=page.locator('#rs-filter').is_visible();assert baseline_visibility
                assert page.locator('#rs-filter option').all_text_contents()==['All','Outperforming','Underperforming','Flat','Unavailable']
            page.goto(url+'#sectors-themes')
            for kind in ['Sector','Theme']:
                page.select_option('#theme-type',kind)
                assert page.locator('#theme-body tr[data-theme]').count()==sum((t['level']=='Sector')==(kind=='Sector') for t in snapshot['themes'])
            page.select_option('#theme-type','All');page.click('.side-nav [data-page="watchlist"]')
            assert page.locator('#rs-filter').is_visible();assert page.locator('#rs-filter').input_value()=='All'
            assert page.locator('#stock-sort option[value="weighted_excess_pp"],#stock-sort option[value="excess21_pp"],#stock-sort option[value="excess63_pp"]').count()==0
            assert page.locator('#stock-head .col-rs-diff [data-sort]').count()==0
            # Existing saved sort choices cannot restore removed table modes.
            context=browser.new_context();context.add_init_script("history.replaceState({themescope:true,index:0,view:"+json.dumps({'ui_schema':5,'session_date':snapshot['session_date'],'page':'sectors-themes','theme_sort_key':'rank_change_daily','stock_sort_key':'weighted_excess_pp','route_state':{'key':'weighted_excess_pp'}})+"},'',location.href)")
            trial=context.new_page();trial.goto(url);assert trial.locator('#theme-sort').input_value()=='theme_score';trial.click('.side-nav [data-page="watchlist"]');assert trial.locator('#stock-sort').input_value()=='return21';context.close()
            page.goto(base+run.name+'/table_checks/fixture.html#watchlist')
            breadth=page.locator('.summary-breadth').inner_text();first=theme['selected'][0]
            assert first['excess21_pp']>0 and first['excess63_pp']<0 and first['weighted_excess_pp']>0
            for classification,index in [('Outperforming',0),('Underperforming',1),('Flat',2),('Unavailable',3)]:
                page.select_option('#rs-filter',classification)
                assert page.locator('#stock-body tr[data-stock-symbol]').count()==1
                assert page.locator('#stock-body .col-ticker a').inner_text()==theme['selected'][index]['ticker']
                assert page.locator('#stock-body .col-rank').inner_text()==str(theme['selected'][index]['selection_slot'])
                assert page.locator('#coverage').inner_text()=='1 of 4 stocks';assert page.locator('.summary-breadth').inner_text()==breadth
            page.select_option('#rs-filter','Outperforming');page.fill('#stock-search',first['ticker']);page.select_option('#ema-filter','below21')
            assert page.locator('#coverage').inner_text()=='0 of 4 stocks';assert 'No stocks match' in page.locator('#stock-body').inner_text()
            page.select_option('#ema-filter','above21');assert page.locator('#coverage').inner_text()=='1 of 4 stocks'
            page.fill('#stock-search','NO_MATCH');assert page.locator('#coverage').inner_text()=='0 of 4 stocks'
            page.fill('#stock-search','');page.select_option('#rs-filter','All');page.select_option('#ema-filter','all')
            for mode in ['dark','light']:
                if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
                for width,height in [(1366,768),(1440,900),(1920,1080)]:
                    page.set_viewport_size({'width':width,'height':height})
                    for route,prefix in [('sectors-themes','theme'),('watchlist','stock')]:
                        page.click('.side-nav [data-page="'+route+'"]');page.evaluate('window.scrollTo(0,0)')
                        if prefix=='theme':
                            assert page.locator('#theme-body .type-tag,#theme-head .col-rank-daily').count()==0
                            assert page.locator('#theme-sort option[value="rank_change_daily"]').count()==0
                            assert page.locator('#theme-head .col-priority-change').count()==1
                        # Exercise both active sort arrows and info icons, not just default headers.
                        key='theme_score' if prefix=='theme' else 'market_cap_usd';page.click('#'+prefix+'-head [data-sort="'+key+'"]')
                        geometry=page.evaluate('''prefix=>{
                            const heads=[...document.querySelectorAll('#'+prefix+'-head th')],cells=[...document.querySelector('#'+prefix+'-body tr').children];
                            return heads.map((head,i)=>{
                                const cell=cells[i],label=head.querySelector('.header-label'),a=head.getBoundingClientRect(),b=cell.getBoundingClientRect(),l=label.getBoundingClientRect(),style=getComputedStyle(cell);
                                const textRange=document.createRange();textRange.selectNodeContents(label);const textWidth=textRange.getBoundingClientRect().width;
                                return {role:cell.className,headerRole:head.className,x:a.x,bodyX:b.x,w:a.width,bodyW:b.width,align:style.textAlign,headAlign:getComputedStyle(head).textAlign,labelAlign:getComputedStyle(label).textAlign,labelLeft:l.left,labelRight:l.right,labelCenter:(l.left+l.right)/2,valueLeft:b.left+parseFloat(style.paddingLeft),valueRight:b.right-parseFloat(style.paddingRight),valueCenter:(b.left+b.right)/2,padLeft:style.paddingLeft,padRight:style.paddingRight,tabular:style.fontVariantNumeric,font:parseFloat(style.fontSize),labelFits:textWidth<=l.width+.05};
                            });
                        }''',prefix)
                        assert len({g['padLeft'] for g in geometry})==len({g['padRight'] for g in geometry})==1
                        assert len({round(g['w']) for g in geometry})>4 # explicit content widths
                        for g in geometry:
                            assert g['role']==g['headerRole'] and abs(g['x']-g['bodyX'])<.6 and abs(g['w']-g['bodyW'])<.6,g
                            expected='left' if g['role'] in ['col-name','col-ticker','col-etf','col-priority','col-priority-change'] else 'center' if g['role']=='col-ema' else 'right'
                            assert g['align']==g['headAlign']==g['labelAlign']==expected,g
                            assert abs(g['labelLeft']-g['valueLeft'])<.6 if expected=='left' else abs(g['labelRight']-g['valueRight'])<.6 if expected=='right' else abs(g['labelCenter']-g['valueCenter'])<.6,g
                            assert g['labelFits'] and g['font']>=12 and 'tabular-nums' in g['tabular'],g
                        if prefix=='stock':
                            assert page.locator('.stock-table-wrap').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
                            gap=page.evaluate('''()=>{let r=document.querySelector('#stock-body tr'),cells=r.children,a=cells[9].querySelector('span').getBoundingClientRect(),b=cells[10].querySelector('span').getBoundingClientRect();return b.left-a.right;}''')
                            assert gap>=16,gap
                        else:
                            assert page.locator('#theme-body .theme-select').first.evaluate('e=>Math.abs(e.getBoundingClientRect().left-e.closest("td").getBoundingClientRect().left-8)<.6')
                        page.screenshot(path=str(out/f'{prefix}-{mode}-{width}.png'));screenshots+=1
            # ETF-only layouts also keep the filter visible.
            theme['selected']=[];(out/'empty.html').write_text(render_html(fixture,ROOT),encoding='utf-8');page.goto(base+run.name+'/table_checks/empty.html#watchlist')
            assert page.locator('#rs-filter').is_visible();assert page.locator('#coverage').inner_text()=='0 of 0 stocks'
            assert not errors,errors;assert not [r for r in requests if r.startswith(('http:','https:')) and not r.startswith(base)]
            browser.close()
    finally:server.shutdown();server.server_close()
    print(json.dumps({'previous_filter_visible_in_saved_baseline':baseline_visibility,'weighted_opposite_horizons':'passed','geometry_icons_arrows_na_negatives':'passed','viewports':[1366,1440,1920],'modes':['light','dark'],'screenshots':screenshots,'javascript_errors':errors,'automatic_external_requests':0}))

if __name__=='__main__':main()
