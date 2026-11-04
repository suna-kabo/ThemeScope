"""HTTP checks of the Primary guide, deep link and unchanged complete matrix."""
import argparse
from collections import Counter
import copy
import http.server
import json
from pathlib import Path
import re
import shutil
import sys
import threading

from playwright.sync_api import sync_playwright,expect

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.research_policy import market_truth_table,methodology


def check(path):
    path=Path(path).resolve();html=path.read_text(encoding='utf-8')
    match=re.search(r'(<script id="snapshot-data"[^>]*>)(.*?)(</script>)',html,re.S)
    original=json.loads(match.group(2))
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self,*args):pass
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),lambda *a,**kw:Quiet(*a,directory=str(path.parent),**kw))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}/';url=base+path.name
    errors=[];external=[];screens=ROOT/'output/methodology_browser';screens.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(headless=True,executable_path=shutil.which('chromium'),args=['--no-sandbox'])
            for variant in ('saved','no-primary','unclassified'):
                payload=copy.deepcopy(original)
                if variant!='saved':
                    payload['daily_primary_research']['combined_file']=None
                    payload['decision'].update(spy_price_state=None if variant=='unclassified' else 'Mixed',qqq_price_state='Mixed',breadth_consensus='Mixed',market_classification='Unclassified' if variant=='unclassified' else 'Neutral',primary_groups={'new':[],'continuing':[],'unavailable':[]})
                rendered=html[:match.start(2)]+json.dumps(payload,ensure_ascii=False).replace('</','<\\/')+html[match.end(2):]
                context=browser.new_context(viewport={'width':1440,'height':900})
                context.route(url,lambda route:route.fulfill(status=200,content_type='text/html; charset=utf-8',body=rendered))
                page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda request:external.append(request.url) if request.url.startswith(('http:','https:')) and not request.url.startswith(base) else None)
                page.goto(url)
                for mode in ('light','dark'):
                    if page.locator('html').get_attribute('data-mode')!=mode:page.click('#mode')
                    page.click('[data-page="daily-plan"]')
                    help_link=page.get_by_role('link',name='How this list is built',exact=True)
                    expect(help_link).to_be_visible()
                    assert page.locator('.primary-download').count()==bool(payload['daily_primary_research']['combined_file'])
                    page.evaluate('window.scrollTo(0,Math.min(160,document.documentElement.scrollHeight-innerHeight))');page.wait_for_timeout(160)
                    old_y=page.evaluate('scrollY')
                    help_link.focus();page.keyboard.press('Enter')
                    expect(page.locator('#methodology')).to_be_visible()
                    heading=page.locator('#primary-research-watchlist');expect(heading).to_be_focused()
                    assert len(context.pages)==1
                    assert page.url.endswith('#methodology/primary-research-watchlist')
                    assert 0<=heading.bounding_box()['y']<180
                    text=page.locator('.primary-research-method').inner_text();policy=methodology()
                    for name in ('long_rule','short_rule','transition_rule'):assert policy[name] in text,name
                    for text_part in ('0.60 × ER1M + 0.40 × ER3M','+1.2 pp','Exactly zero','missing required returns','do not need the same sign','cross-sectional ETF percentiles','first qualifying section','ETF-only','Browser search and filters'):
                        assert text_part in text,text_part
                    # Every authoritative input case appears exactly once, with unchanged result.
                    expected=Counter((r['spy'] or 'Unavailable',r['qqq'] or 'Unavailable',r['breadth'] or 'Unavailable',r['direction']) for r in market_truth_table())
                    rows=page.locator('.market-matrix tbody tr').evaluate_all('es=>es.map(e=>Array.from(e.cells,c=>c.textContent.replace(" · Today", "")))')
                    assert Counter(tuple(row) for row in rows)==expected
                    assert page.locator('[data-matrix-result]').evaluate_all('es=>es.map(e=>e.dataset.matrixResult)')==['Long bias','Selective long','Neutral','Selective short','Short bias','Unclassified']
                    active=page.locator('.market-matrix .active-cell');assert active.count()==1
                    assert active.locator('td').all_text_contents()[:3]==[payload['decision'][k] or 'Unavailable' for k in ('spy_price_state','qqq_price_state','breadth_consensus')]
                    group=page.locator('.matrix-group-current');assert group.count()==1
                    assert group.get_attribute('data-matrix-result')==payload['decision']['market_classification']
                    page.screenshot(path=str(screens/f'{path.stem}-{variant}-{mode}.png'))
                    page.evaluate('window.scrollBy(0,250)');page.wait_for_timeout(160);method_y=page.evaluate('scrollY')
                    page.go_back();expect(page.locator('#daily-plan')).to_be_visible()
                    assert abs(page.evaluate('scrollY')-old_y)<3
                    page.go_forward();expect(page.locator('#methodology')).to_be_visible()
                    assert abs(page.evaluate('scrollY')-method_y)<3
                    expect(page.locator('#primary-research-watchlist')).to_be_focused()
                    page.click('[data-page="market"]');page.click('[data-page="methodology"]')
                    assert abs(page.evaluate('scrollY')-method_y)<3
                context.close()
            # A fresh deep link also opens and focuses the section, without history state.
            context=browser.new_context();page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
            page.goto(url+'#methodology/primary-research-watchlist')
            expect(page.locator('#primary-research-watchlist')).to_be_focused()
            expect(page.locator('#methodology')).to_be_visible()
            assert 0<=page.locator('#primary-research-watchlist').bounding_box()['y']<180
            browser.close()
    finally:server.shutdown();server.server_close()
    assert not errors,errors
    assert not external,external
    print(json.dumps({'file':path.name,'variants':['saved','no-primary','unclassified'],'matrix_cases':64,'formulas_and_policy':'passed','deep_link_focus_back_scroll':'passed','modes':['light','dark'],'javascript_errors':errors,'automatic_external_requests':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('files',nargs='+',type=Path)
    for file in parser.parse_args().files:check(file)
