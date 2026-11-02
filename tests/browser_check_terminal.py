"""Terminal workflow and visual acceptance against current locally generated output."""
import argparse,http.server,json,shutil,socketserver,threading
from pathlib import Path
from playwright.sync_api import sync_playwright

def main():
 p=argparse.ArgumentParser();p.add_argument('dashboard',type=Path);root=p.parse_args().dashboard.resolve().parent;s=json.loads((root/'latest_snapshot.json').read_text());out=root/'terminal_checks';out.mkdir(exist_ok=True)
 class Quiet(http.server.SimpleHTTPRequestHandler):
  def log_message(self,*a):pass
 server=socketserver.TCPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(root),**kw));threading.Thread(target=server.serve_forever,daemon=True).start()
 errors=[];requests=[]
 try:
  with sync_playwright() as p:
   b=p.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox']);page=b.new_page(viewport={'width':1536,'height':864},has_touch=True)
   page.on('pageerror',lambda e:errors.append(str(e)));page.on('request',lambda r:requests.append(r.url));url=f'http://127.0.0.1:{server.server_address[1]}/dashboard.html';page.goto(url)
   assert not errors,errors
   assert page.locator('#primary-body,#primary-export').count()==0
   page.click('[data-page="watchlist"]');assert page.locator('#stock-view').input_value()=='relative';assert page.locator('#stock-head th').count()==12
   page.select_option('#stock-view','performance');page.click('[data-page="market"]');page.click('[data-page="watchlist"]');assert page.locator('#stock-view').input_value()=='performance'
   page.click('[data-page="daily-plan"]');assert page.locator('#expected-earnings').evaluate('e=>e.tagName')=='SECTION'
   assert page.locator('#sectors-themes > details').count()==0
   for k,ids in s['decision']['priority_groups'].items():
    themes=[t for t in s['themes'] if t['id'] in ids]
    side=next((t['research_priority'].get('side') for t in themes if t['research_priority'].get('side')),None)
    order='asc' if k!='observation' and side=='short' else 'desc'
    select=page.locator('[data-priority-order="'+k+'"]')
    assert select.input_value()==order
    article=select.locator('xpath=ancestor::article')
    assert article.locator('[data-daily-theme]').count()==min(5,len(ids))
    assert f'{min(5,len(ids))} of {len(ids)} themes' in article.inner_text()
    expected=sorted(themes,key=lambda t:((1 if order=='asc' else -1)*t['theme_score'],t['id']))
    assert article.locator('[data-daily-theme]').evaluate_all('es=>es.map(e=>e.dataset.dailyTheme)')==[t['id'] for t in expected[:5]]
   key=next(k for k,v in s['decision']['priority_groups'].items() if len(v)>5)
   button=page.locator('[data-priority-expand="'+key+'"]');button.click();assert button.get_attribute('aria-expanded')=='true'
   group=page.locator('.priority-card').filter(has=page.locator('[data-priority-expand="'+key+'"]'))
   assert group.locator('[data-daily-theme]').count()==len(s['decision']['priority_groups'][key])
   page.select_option('[data-priority-order="'+key+'"]','desc')
   expected=sorted([t for t in s['themes'] if t['id'] in s['decision']['priority_groups'][key]],key=lambda t:(-t['theme_score'],t['id']))
   assert group.locator('[data-daily-theme]').first.get_attribute('data-daily-theme')==expected[0]['id']
   page.evaluate('window.scrollTo(0,500)');page.wait_for_timeout(180);before=page.evaluate('window.scrollY')
   page.click('[data-page="market"]');page.click('[data-page="daily-plan"]');assert abs(page.evaluate('window.scrollY')-before)<3
   assert page.locator('[data-priority-expand="'+key+'"]').get_attribute('aria-expanded')=='true'
   page.go_back();page.go_forward();assert abs(page.evaluate('window.scrollY')-before)<3
   # Theme/view-specific filters, sort and horizontal scroll, including browser history.
   page.click('[data-page="watchlist"]');page.select_option('#stock-view','relative')
   first=page.locator('#watchlist-theme-selector').input_value()
   canonical=next(t for t in s['themes'] if t['id']==first)
   positions={r['ticker']:str(r['selection_slot']) for r in canonical['selected']}
   page.select_option('#stock-sort','excess63_pp')
   actual=page.locator('#stock-body tr').evaluate_all("es=>es.map(e=>({ticker:e.querySelector('.col-ticker a,.col-ticker b').textContent,slot:e.querySelector('.col-rank').textContent}))")
   assert all(positions[r['ticker']]==r['slot'] for r in actual)
   page.set_viewport_size({'width':390,'height':844})
   page.locator('.stock-table-wrap').evaluate('e=>e.scrollLeft=240')
   page.wait_for_timeout(160)
   x=page.locator('.stock-table-wrap').evaluate('e=>e.scrollLeft')
   page.fill('#stock-search',canonical['selected'][0]['ticker'])
   page.select_option('#rs-filter','Mixed')
   page.click('#next-theme');assert page.locator('#stock-search').input_value()==''
   assert page.locator('#rs-filter').input_value()=='All'
   page.go_back();assert page.locator('#watchlist-theme-selector').input_value()==first
   assert page.locator('#stock-search').input_value()==canonical['selected'][0]['ticker']
   assert page.locator('#rs-filter').input_value()=='Mixed'
   assert page.locator('#stock-sort').input_value()=='excess63_pp'
   assert abs(page.locator('.stock-table-wrap').evaluate('e=>e.scrollLeft')-x)<2
   page.go_forward();page.go_back()
   page.fill('#stock-search','');page.select_option('#rs-filter','All')
   page.select_option('#stock-view','performance');page.select_option('#stock-view','relative')
   assert page.locator('#stock-sort').input_value()=='excess63_pp'
   # Corrupt and inaccessible persistence must leave navigation usable.
   for script in ("sessionStorage.setItem('themescope-terminal-v2:"+s['session_date']+"','{broken')",
                  "sessionStorage.setItem('themescope-terminal-v2:"+s['session_date']+"',JSON.stringify({schema:2,session:'"+s['session_date']+"',routes:{watchlist:null,market:{tables:[null],y:1e9}}}))",
                  "Object.defineProperty(window,'sessionStorage',{get(){throw Error('unavailable')}})"):
    context=b.new_context();context.add_init_script(script);trial=context.new_page();trial.on('pageerror',lambda e:errors.append(str(e)))
    trial.goto(url+'#watchlist');assert trial.locator('#stock-view').input_value()=='relative'
    trial.reload();trial.click('[data-page="market"]');trial.click('[data-page="watchlist"]');context.close()
   page.set_viewport_size({'width':1536,'height':864})
   for mode in ('dark','light'):
    page.set_viewport_size({'width':1536,'height':864})
    if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
    for w,h in ((1920,1080),(1536,864),(1366,768),(390,844)):
     page.set_viewport_size({'width':w,'height':h})
     for route in ('market','daily-plan','sectors-themes','watchlist'):
      page.click('[data-page="'+route+'"]');page.evaluate('window.scrollTo(0,0)')
      assert page.locator('#mode').is_visible()
      if route=='watchlist':
       for view,n in (('relative',12),('performance',15)):
        page.select_option('#stock-view',view)
        assert page.locator('#stock-head th').count()==n
        if w>=1536:
         assert page.locator('.stock-table-wrap').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
         a=page.locator('#stock-head th').evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))')
         c=page.locator('#stock-body tr').first.locator('td').evaluate_all('es=>es.map(e=>({x:e.getBoundingClientRect().x,w:e.getBoundingClientRect().width}))')
         assert len(a)==len(c) and all(abs(x['x']-y['x'])<.6 and abs(x['w']-y['w'])<.6 for x,y in zip(a,c))
        page.screenshot(path=str(out/f'watchlist-{view}-{mode}-{w}.png'))
      else:
       if route=='sectors-themes' and w>=1536:assert page.locator('.theme-table-wrap').evaluate('e=>e.scrollWidth<=e.clientWidth+1')
       page.screenshot(path=str(out/f'{route}-{mode}-{w}.png'))
      assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
   page.set_viewport_size({'width':1536,'height':864});page.click('[data-page="daily-plan"]')
   for mode in ('dark','light'):
    if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
    page.locator('#expected-earnings').scroll_into_view_if_needed();page.screenshot(path=str(out/f'earnings-{mode}.png'))
   page.set_viewport_size({'width':390,'height':844});page.locator('#daily-methodology > summary').click()
   assert '60% Current plus 40% Medium' in page.locator('#methodology-content').inner_text()
   assert page.evaluate('document.documentElement.scrollWidth<=document.documentElement.clientWidth+1')
   page.click('[data-page="market"]');page.click('[data-page="daily-plan"]')
   assert page.locator('#daily-methodology').get_attribute('open')==''
   page.locator('#expected-earnings-content > details > summary').click()
   unknown=page.locator('#expected-earnings-content > details [data-earnings-theme]').first
   expected_theme=unknown.get_attribute('data-earnings-theme');unknown.click()
   assert page.locator('#watchlist-theme-selector').input_value()==expected_theme
   assert not errors,errors
   assert not [r for r in requests if r.startswith(('http:','https:')) and not r.startswith('http://127.0.0.1:')]
   b.close()
 finally:server.shutdown();server.server_close()
 print(json.dumps({'errors':errors,'external_requests':0,'screenshots':42,'scroll_restoration':'passed'}))
if __name__=='__main__':main()
