"""Real loopback pre-launch UI smoke; real config, fictional test bars, no credentials."""
from pathlib import Path
import json,shutil,socket,sys,tempfile,threading,time
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from vnext_prelaunch_fixture import PrelaunchFixture


def main():
    from src.themescope.local.app import create_app
    from playwright.sync_api import sync_playwright,expect
    import uvicorn
    with tempfile.TemporaryDirectory(prefix='themescope prelaunch UI ') as folder,patch('src.themescope.local.service.optional_earnings',return_value={}):
        fixture=PrelaunchFixture(folder);service=fixture.service
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(create_app(ROOT,service),log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+5
            while not server.started and time.monotonic()<deadline:threading.Event().wait(.01)
            assert server.started
            with sync_playwright() as p:
                options={'headless':True}
                if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];outside=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:outside.append(r.url) if not r.url.startswith((f'http://127.0.0.1:{port}','blob:')) else None)
                page.goto(f'http://127.0.0.1:{port}')
                page.get_by_role('button',name='Refresh Data',exact=True).click()
                expect(page.locator('#progress')).to_have_text('Refresh complete',timeout=30000)
                expect(page.locator('#theme-layer')).to_contain_text('Pre-launch research')
                expect(page.locator('#theme-layer')).to_contain_text('2026-11-05')
                expect(page.locator('#theme-layer')).to_contain_text('2026-11-06 close')
                expect(page.locator('#fixture-banner')).to_be_hidden()
                page.locator('[data-nav="themes"]').click()
                expect(page.locator('#theme-table')).to_contain_text('Trend')
                expect(page.locator('#theme-table')).to_contain_text('Bullish')
                page.locator('[data-nav="primary"]').click()
                assert page.locator('#candidates tbody tr').count()>0
                save=page.locator('#candidates [data-save]').first;ticker=save.get_attribute('data-save');save.click()
                page.locator('[data-nav="saved"]').click()
                expect(page.locator('#saved')).to_contain_text(ticker)
                page.locator('[data-nav="primary"]').click()
                with page.expect_download() as item:
                    page.get_by_role('link',name='Export all Primary').click()
                text=Path(item.value.path()).read_text();assert text and '###' in text
                identifiers=[line for line in text.splitlines() if not line.startswith('###')]
                assert len(identifiers)==len(set(identifiers))
                # Auto cutover uses the same server and never calls research history live.
                fixture.target='2026-11-06';page.get_by_role('button',name='Refresh Data',exact=True).click()
                expect(page.locator('#theme-layer')).to_contain_text('Launch close: index initialized at 100',timeout=30000)
                page.locator('[data-nav="themes"]').click()
                expect(page.locator('#theme-table')).to_contain_text('Trend')
                assert service.snapshot()['theme_layer']['official_live_history']
                page.set_viewport_size({'width':390,'height':844})
                assert page.locator('body').bounding_box()['width']<=390
                assert not errors,errors
                assert not outside,outside
                browser.close()
                print(json.dumps({'prelaunch_browser':'passed','banner':'passed','research_trend':'passed',
                    'primary_export':'passed','watchlist':'passed','fixture_banner_hidden':True,
                    'automatic_launch_cutover':'passed','external_requests':0,'page_errors':0}))
        finally:server.should_exit=True;worker.join(5);sock.close()

if __name__=='__main__':main()
