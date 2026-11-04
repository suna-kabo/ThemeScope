"""Actual loopback HTTP, occupied ports, wrong copies and regeneration."""
import functools
import errno
import hashlib
import http.client
import http.server
import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from scripts.serve_local import create_server,main,root_identity,LoopbackHTTPServer
from src.themescope.local_publication import output_lock,publish_tree,transaction_dir,write_journal,digest


def fixture(root,day,site=False,marker='one',destination=None):
    folder=Path(destination) if destination else Path(root)/('site' if site else 'output/manual_csv');folder.mkdir(parents=True,exist_ok=True)
    entry='index.html' if site else 'dashboard.html';metadata='snapshot_summary.json' if site else 'latest_snapshot.json'
    value={'session_date':day,'marker':marker}
    (folder/entry).write_text('<!doctype html><script id="snapshot-data" type="application/json">'+json.dumps(value)+'</script>',encoding='utf-8')
    (folder/metadata).write_text(json.dumps(value),encoding='utf-8');(folder/'download.txt').write_text(marker,encoding='utf-8')
    if not site:(folder/'refresh_status.json').write_text(json.dumps({'status':'success','data_date':day}),encoding='utf-8')
    files={p.name:digest(p) for p in folder.iterdir() if p.is_file() and p.name not in {'site_manifest.json','publication_manifest.json'}}
    (folder/('site_manifest.json' if site else 'publication_manifest.json')).write_text(json.dumps({'session_date':day,'files':files}),encoding='utf-8')
    return folder


class PreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='preview copies 香港 ');self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.old=self.base/'old project';self.new=self.base/'new project 香港';fixture(self.old,'2026-11-02');fixture(self.new,'2026-11-03')
    def start(self,root,site=False,port=0):
        server,info,url=create_server(root,site,port);server.RequestHandlerClass.log_message=lambda *args:None
        threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return server,info,url
    def get(self,url,headers=None,method='GET'):
        parsed=urlsplit(url);connection=http.client.HTTPConnection(parsed.hostname,parsed.port,timeout=5)
        connection.request(method,parsed.path+('?' +parsed.query if parsed.query else ''),headers=headers or {})
        response=connection.getresponse();result=(response.status,dict(response.getheaders()),response.read());connection.close()
        if result[0]==307:return self.get('http://'+parsed.netloc+result[1]['Location'],headers,method)
        return result
    def test_wrong_copy_reproduces_old_html_and_explicit_port_never_opens_browser(self):
        old,_,old_url=self.start(self.old);port=old.server_port
        self.assertIn(b'2026-11-02',self.get(old_url)[2]);self.assertIn('2026-11-03',(self.new/'output/manual_csv/dashboard.html').read_text())
        with patch('scripts.serve_local.ROOT',self.new),patch('scripts.serve_local.webbrowser.open') as opened:
            with self.assertRaisesRegex(ValueError,'occupied.*No browser'):main(['--port',str(port)])
            opened.assert_not_called()
        # Old tab receives old HTML; rendering state is not necessary to explain this.
        self.assertIn(b'2026-11-02',self.get(old_url)[2])
        newer,info,url=self.start(self.new)
        self.assertNotEqual(newer.server_port,port);self.assertEqual(info['session'],'2026-11-03');self.assertIn(b'2026-11-03',self.get(url)[2])
    def test_default_collision_selects_bound_available_port(self):
        real=LoopbackHTTPServer;calls=[]
        def occupied(address,handler):
            calls.append(address)
            if address[1]==8000:raise OSError(errno.EADDRINUSE,'address in use')
            return real(address,handler)
        with patch('scripts.serve_local.LoopbackHTTPServer',side_effect=occupied):server,info,url=self.start(self.new,port=None)
        self.assertEqual(calls,[('127.0.0.1',8000),('127.0.0.1',0)])
        self.assertIn(str(server.server_port),url);self.assertEqual(self.get(url)[1]['X-ThemeScope-Session'],'2026-11-03')
    def test_dashboard_and_site_separate_defaults_and_explicit_conflict(self):
        fixture(self.new,'2026-11-02',site=True)
        dashboard,_,dashboard_url=self.start(self.new)
        with self.assertRaisesRegex(ValueError,'occupied'):create_server(self.new,True,dashboard.server_port)
        site,info,site_url=self.start(self.new,True)
        self.assertEqual(info['type'],'prepared site');self.assertEqual(info['session'],'2026-11-02')
        self.assertIn(b'2026-11-03',self.get(dashboard_url)[2]);self.assertIn(b'2026-11-02',self.get(site_url)[2])
    def test_old_identity_url_is_rejected_if_a_port_is_reused(self):
        _,_,url=self.start(self.new)
        wrong=url.split('?')[0]+'?preview='+root_identity(self.old/'output/manual_csv',False)
        self.assertEqual(self.get(wrong)[0],409);self.assertNotIn(b'<script',self.get(wrong)[2])
    def test_running_preview_reloads_new_publication_and_metadata_without_304(self):
        server,info,url=self.start(self.old);folder=Path(info['directory'])
        first=self.get(url);self.assertEqual(first[0],200);self.assertEqual(first[2],(folder/'dashboard.html').read_bytes())
        stage=self.base/'staging';fixture(self.old,'2026-11-03',marker='new publication',destination=stage)
        with output_lock(folder):publish_tree(stage,folder)
        status,headers,html=self.get(url,{'If-Modified-Since':'Wed, 04 Nov 2037 00:00:00 GMT','If-None-Match':'anything'})
        self.assertEqual(status,200);self.assertEqual(html,(folder/'dashboard.html').read_bytes());self.assertIn(b'2026-11-03',html)
        self.assertIn('no-store',headers['Cache-Control']);self.assertEqual(headers['X-ThemeScope-Session'],'2026-11-03')
        meta=self.get('http://'+urlsplit(url).netloc+'/latest_snapshot.json');self.assertEqual(json.loads(meta[2])['session_date'],'2026-11-03')
        self.assertIn('no-store',meta[1]['Cache-Control'])
    def test_old_tab_cannot_download_newer_run_files_until_html_reload(self):
        _,info,url=self.start(self.old);base=url.split('/dashboard.html')[0]
        self.assertEqual(self.get(base+'/download.txt')[2],b'one')
        stage=self.base/'staging';fixture(self.old,'2026-11-03',marker='new download',destination=stage)
        with output_lock(info['directory']):publish_tree(stage,info['directory'])
        self.assertEqual(self.get(base+'/download.txt')[0],409)
        current=self.get(url)
        self.assertIn(b'2026-11-03',current[2])
        new_base='http://'+urlsplit(url).netloc+'/_preview/'+current[1]['X-ThemeScope-Run']
        self.assertEqual(self.get(new_base+'/download.txt')[2],b'new download')
    def test_plain_old_server_can_return_304_for_rewritten_same_second_file(self):
        folder=self.old/'output/manual_csv';path=folder/'dashboard.html';stamp=1700000000;os.utime(path,(stamp,stamp))
        class Quiet(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(folder)))
        threading.Thread(target=lambda:server.serve_forever(poll_interval=.01),daemon=True).start();self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        url=f'http://127.0.0.1:{server.server_port}/dashboard.html';first=self.get(url)
        path.write_text('new HTML written within same HTTP modification second');os.utime(path,(stamp,stamp))
        self.assertEqual(self.get(url,{'If-Modified-Since':first[1]['Last-Modified']})[0],304)
    def test_partial_or_tampered_outputs_are_not_served_as_completed(self):
        _,info,url=self.start(self.new);folder=Path(info['directory'])
        folder.joinpath('dashboard.html').write_text('partial write')
        self.assertEqual(self.get(url)[0],503)
        fixture(self.new,'2026-11-03');journal=transaction_dir(folder);journal.mkdir()
        write_journal(journal,{'state':'pending'})
        self.assertEqual(self.get(url)[0],503)
    def test_staging_unknown_paths_and_traversal_are_not_served(self):
        _,info,url=self.start(self.new);folder=Path(info['directory']);(folder/'.secret').write_text('hidden');(folder/'unfinished.tmp').write_text('partial')
        base=url.split('/dashboard.html')[0]
        for name in ('.secret','unfinished.tmp','../other','local_history/2026-11-03.json'):
            self.assertEqual(self.get(base+'/'+name)[0],404,name)
        self.assertEqual(self.get(base+'/download.txt')[2],b'one')
    def test_moved_project_and_other_working_directory(self):
        moved=self.base/'moved folder 香港';shutil.move(str(self.new),str(moved))
        before=Path.cwd()
        try:
            os.chdir(self.old);_,info,url=self.start(moved);self.assertEqual(info['directory'],str((moved/'output/manual_csv').resolve()));self.assertIn(b'2026-11-03',self.get(url)[2])
        finally:os.chdir(before)
    def test_browser_opens_only_after_successful_bind_and_reports_root(self):
        from io import StringIO
        with patch('scripts.serve_local.ROOT',self.new),patch('scripts.serve_local.webbrowser.open') as opened,patch.object(http.server.ThreadingHTTPServer,'serve_forever',side_effect=KeyboardInterrupt),patch('sys.stdout',new_callable=StringIO) as output:
            self.assertEqual(main(['--port','0']),0);opened.assert_called_once()
            text=output.getvalue();self.assertIn(str(self.new/'output/manual_csv'),text);self.assertIn('Actual snapshot session: 2026-11-03',text);self.assertIn(opened.call_args.args[0],text)

if __name__=='__main__':unittest.main()
