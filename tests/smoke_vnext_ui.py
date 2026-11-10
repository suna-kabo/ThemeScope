"""Real loopback browser smoke, synthetic inputs only. Run explicitly at Gate D."""
from pathlib import Path
import json,shutil,socket,sys,tempfile,threading,time
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    from src.themescope.local.service import fixture_service
    from src.themescope.local.app import create_app
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
                if shutil.which('chromium'):options['executable_path']=shutil.which('chromium')
                browser=p.chromium.launch(**options)
                page=browser.new_page(viewport={'width':1440,'height':1000});errors=[];outside=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                page.on('request',lambda r:outside.append(r.url) if not r.url.startswith(f'http://127.0.0.1:{port}') and not r.url.startswith('blob:') else None)
                page.goto(f'http://127.0.0.1:{port}')
                page.get_by_role('button',name='Refresh Data',exact=True).click()
                expect(page.locator('#progress')).to_have_text('Refresh complete')
                page.locator('[data-nav="primary"]').click();page.locator('[data-candidate-lens="directional"]').click()
                expect(page.locator('#candidates')).to_contain_text('AAA')
                page.get_by_role('button',name='Grouped by theme',exact=True).click()
                assert page.locator('#candidates tbody tr').count()>=4
                page.locator('#candidates [data-save]').first.click()
                page.locator('[data-nav="saved"]').click()
                expect(page.locator('#saved')).to_contain_text('AAA')
                page.locator('[data-nav="primary"]').click();page.locator('[data-candidate-lens="directional"]').click()
                with page.expect_download() as download:
                    page.get_by_role('link',name='Export Directional').click()
                text=Path(download.value.path()).read_text()
                assert text.count('NASDAQ:AAA')==1 and text.count('NASDAQ:BBB')==1
                page.locator('#candidates [data-inspect-ticker]').first.click()
                expect(page.locator('#inspector-content')).to_contain_text('Other qualifying themes')
                page.keyboard.press('Escape')
                page.locator('[data-nav="overview"]').click()
                page.locator('[data-nav="methodology"]').click()
                assert page.url.endswith('#methodology')
                page.set_viewport_size({'width':390,'height':844})
                assert page.locator('body').bounding_box()['width']<=390
                assert not errors,errors
                assert not outside,outside
                print(json.dumps({'browser':'passed','refresh':True,'combined_download':True,'watchlist':True,'mobile_no_overflow':True,'external_requests':0,'page_errors':0,'performance':service.status().get('elapsed_seconds')}))
                static_preview=ROOT/'inspection/ui/index.html'
                if static_preview.exists():
                    from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
                    from functools import partial
                    class Quiet(SimpleHTTPRequestHandler):
                        def log_message(self,*args):pass
                    static_server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(static_preview.parent)))
                    static_thread=threading.Thread(target=static_server.serve_forever,daemon=True);static_thread.start()
                    try:
                        preview=browser.new_page();preview_errors=[];network=[]
                        static_origin='http://127.0.0.1:'+str(static_server.server_port)
                        preview.on('pageerror',lambda e:preview_errors.append(str(e)))
                        preview.on('request',lambda r:network.append(r.url) if r.url.startswith(('http:','https:')) and not r.url.startswith(static_origin) else None)
                        preview.goto(static_origin)
                        expect(preview.locator('#fixture-banner')).to_be_visible()
                        preview.get_by_role('button',name='Replay fixture').click()
                        expect(preview.locator('#candidates')).to_contain_text('AAA')
                        with preview.expect_download() as item:
                            preview.get_by_text('Download combined Primary TXT',exact=True).click()
                        assert Path(item.value.path()).read_text().count('NASDAQ:AAA')==1
                        assert not preview_errors,preview_errors
                        assert not network,network
                        print(json.dumps({'static_preview_over_loopback':'passed','external_requests':0,'page_errors':0}))
                    finally:
                        static_server.shutdown();static_server.server_close();static_thread.join(2)
                browser.close()
        finally:
            server.should_exit=True;worker.join(5);sock.close()
if __name__=='__main__':main()
