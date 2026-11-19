"""Real loopback browser smoke, synthetic inputs only. Run explicitly at Gate D."""
from pathlib import Path
import json,os,shutil,socket,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ui_smoke_helpers import open_exports,open_filters,open_refresh


def main():
    from src.themescope.local.service import fixture_service
    from src.themescope.local.app import create_app
    from src.themescope.providers.base import ProviderError
    import uvicorn
    from playwright.sync_api import sync_playwright,expect
    with tempfile.TemporaryDirectory() as folder:
        service=fixture_service(folder)
        sock=socket.socket();sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        server=uvicorn.Server(uvicorn.Config(create_app(ROOT,service),log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+5
            while not server.started and time.monotonic()<deadline:time.sleep(.01)
            assert server.started
            with sync_playwright() as p:
                options={'headless':True}
                if os.environ.get('THEMESCOPE_BROWSER') or shutil.which('chromium'):
                    options['executable_path']=os.environ.get('THEMESCOPE_BROWSER') or shutil.which('chromium')
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];outside=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:outside.append(r.url) if not r.url.startswith(f'http://127.0.0.1:{port}') and not r.url.startswith('blob:') else None)
                counts = {'status': 0, 'dashboard-data': 0}
                def record(request):
                    key = request.url.rsplit('/', 1)[-1]
                    if key in counts:counts[key] += 1
                page.on('request',record)
                page.goto(f'http://127.0.0.1:{port}')
                expect(page.locator('#workspace')).to_have_attribute('aria-busy','false')
                assert counts['dashboard-data'] == 1
                open_refresh(page).click()
                expect(page.locator('#progress')).to_have_text('Current')
                assert counts['dashboard-data'] == 2
                status_polls=counts['status']
                page.wait_for_timeout(10500)
                assert counts['status'] >= status_polls + 2 and counts['dashboard-data'] == 2, counts
                page.locator('[data-nav="primary"]').click()
                expect(page.locator('#candidates')).to_contain_text('AAA')
                open_filters(page)
                page.get_by_role('button',name='By theme',exact=True).click()
                assert page.locator('#candidates [data-ticker-row]').count()>=4
                page.locator('#candidates [data-save]').first.click()
                page.locator('[data-nav="saved"]').click()
                expect(page.locator('#saved')).to_contain_text('AAA')
                page.locator('[data-nav="primary"]').click()
                open_exports(page)
                with page.expect_download() as download:
                    page.get_by_role('link',name='Full research list').click()
                committed=service.snapshot()
                assert download.value.suggested_filename=='Primary-Research-'+committed['session']+'.txt'
                text=Path(download.value.path()).read_text()
                assert text.count('NASDAQ:AAA')==1 and text.count('NASDAQ:BBB')==1
                page.locator('#candidates [data-inspect-ticker]').first.click()
                expect(page.locator('#inspector-content')).to_contain_text('Other relationships')
                page.keyboard.press('Escape')
                page.locator('[data-nav="overview"]').click()
                page.locator('[data-nav="methodology"]').click()
                assert page.url.endswith('#methodology')
                page.set_viewport_size({'width':390,'height':844})
                assert page.locator('body').bounding_box()['width']<=390
                def failed_provider(_):
                    raise ProviderError('private fixture diagnostic')
                service.provider_factory=failed_provider
                open_refresh(page).click()
                expect(page.locator('#progress')).to_have_text('Refresh failed, previous snapshot retained')
                expect(page.locator('#error')).to_contain_text('The market-data provider was unavailable')
                assert 'private fixture diagnostic' not in page.locator('#error').inner_text()
                page.locator('[data-nav="primary"]').click()
                expect(page.locator('#candidates')).to_contain_text('AAA')
                assert counts['dashboard-data'] == 2, counts
                assert service.snapshot() == committed
                assert not errors,errors
                assert not outside,outside
                print(json.dumps({'browser':'passed','refresh':True,'combined_download':True,'watchlist':True,'mobile_no_overflow':True,'external_requests':0,'page_errors':0,'performance':service.status().get('elapsed_seconds')}))
                browser.close()
        finally:
            server.should_exit=True;worker.join(5);sock.close()
if __name__=='__main__':main()
