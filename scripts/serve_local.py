"""Loopback-only static preview of one explicit, completed ThemeScope output."""
import argparse
import errno
import hashlib
import http.server
import json
import mimetypes
import os
import socket
from pathlib import Path,PurePosixPath
import re
import sys
from urllib.parse import unquote,urlsplit,parse_qs
import webbrowser

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.local_publication import digest,output_lock,pending


def console(message):
    """A redirected Windows console may not encode every project-folder name."""
    try:print(message,flush=True)
    except UnicodeEncodeError:
        encoding=getattr(sys.stdout,'encoding',None) or 'utf-8'
        print(message.encode(encoding,errors='backslashreplace').decode(encoding),flush=True)


def snapshot_info(directory,site=False):
    directory=Path(directory).resolve()
    if pending(directory):raise ValueError('Publication is incomplete. Close locked files and run '+('prepare-site.cmd --recover' if site else 'refresh.cmd --recover')+' before previewing.')
    entry='index.html' if site else 'dashboard.html'
    text=(directory/entry).read_text(encoding='utf-8')
    match=re.search(r'<script id="snapshot-data"[^>]*>(.*?)</script>',text,re.S)
    if not match:raise ValueError('No dated snapshot in '+str(directory/entry)+'. '+('Run prepare-site.cmd for a successful session.' if site else 'Run refresh.cmd with all five CSVs.'))
    embedded=json.loads(match.group(1));session=embedded.get('session_date')
    metadata='snapshot_summary.json' if site else 'latest_snapshot.json'
    saved=json.loads((directory/metadata).read_text(encoding='utf-8'))
    if not session or session!=saved.get('session_date'):raise ValueError('HTML and snapshot metadata sessions differ; incomplete output will not be served. Recover or regenerate this folder.')
    manifest_name='site_manifest.json' if site else 'publication_manifest.json'
    manifest_path=directory/manifest_name
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
        if manifest.get('session_date')!=session:raise ValueError('Publication manifest/session mismatch; recover or regenerate before previewing.')
        files=manifest['files']
        if not isinstance(files,dict):raise ValueError('Invalid publication file manifest')
        for name in (entry,metadata):
            if files.get(name)!=digest(directory/name):raise ValueError('HTML/metadata do not match the completed publication; refresh or prepare again.')
        allowed=set(files)|{manifest_name}
    else:
        if site:raise ValueError('Prepared site manifest is missing; run prepare-site.cmd.')
        # Compatibility for an intact pre-update run; next refresh seals all files.
        files={};allowed={entry,metadata,'canonical_dashboard_data.json','refresh_status.json','run_audit.json','themes.csv','theme_stocks.csv','market.csv','latest_run.md','run_bundle.zip','Inter-LICENSE.txt','individual_theme_watchlists.zip'}
        allowed.update(row['file'] for row in saved.get('export_manifest',[]));allowed.update(saved.get('export_archives',[]))
        relationships=saved.get('daily_primary_research',{}).get('relationships_file')
        if relationships:allowed.add(relationships)
    if not site:
        status=json.loads((directory/'refresh_status.json').read_text(encoding='utf-8'))
        if status.get('status')!='success' or status.get('data_date')!=session:raise ValueError('Refresh status does not match the saved HTML session; no completed release was selected.')
    return {'directory':str(directory),'type':'prepared site' if site else 'dashboard output','session':session,'entry':entry,'metadata':metadata,'allowed':allowed,'files':files,'html_sha256':digest(directory/entry),'generated':embedded.get('dashboard_generated_at_hkt_display') or embedded.get('generated_at') or 'not recorded'}


def root_identity(directory,site):return hashlib.sha256((str(Path(directory).resolve())+'|'+str(site)).encode('utf-8')).hexdigest()[:16]


def preview_handler(directory,site=False):
    directory=Path(directory).resolve();identity=root_identity(directory,site)
    class Preview(http.server.BaseHTTPRequestHandler):
        def do_HEAD(self):self.respond(False)
        def do_GET(self):self.respond(True)
        def respond(self,body):
            parsed=urlsplit(self.path)
            supplied=parse_qs(parsed.query).get('preview',[identity])[0]
            if supplied!=identity:
                self.reply(409,b'This URL belongs to another ThemeScope copy or preview type. Use the exact URL printed by the intended launcher.\n','text/plain; charset=utf-8',body);return
            requested=unquote(parsed.path).lstrip('/')
            pinned=None
            if requested.startswith('_preview/'):
                parts=requested.split('/',2)
                if len(parts)!=3 or not re.fullmatch('[0-9a-f]{64}',parts[1]):
                    self.reply(404,b'Invalid preview version.\n','text/plain; charset=utf-8',body);return
                pinned=parts[1];requested=parts[2]
            name=requested or ('index.html' if site else 'dashboard.html')
            path=PurePosixPath(name)
            if '\\' in name or '..' in path.parts or any(part.startswith('.') for part in path.parts) or str(path)!=name:
                self.reply(404,b'Not a completed preview asset.\n','text/plain; charset=utf-8',body);return
            try:
                with output_lock(directory,timeout=.5):
                    info=snapshot_info(directory,site)
                    signature=(info['session'],info['html_sha256'])
                    if getattr(self.server,'preview_signature',None)!=signature:
                        self.server.preview_signature=signature
                        current_url=f'http://127.0.0.1:{self.server.server_port}/_preview/{info["html_sha256"]}/{info["entry"]}?preview={identity}'
                        console('Preview updated: '+info['type']+'; session '+info['session']+'; directory '+str(directory)+'\nCurrent exact URL: '+current_url)
                    if name==info['entry'] and pinned!=info['html_sha256']:
                        self.send_response(307);self.send_header('Location','/_preview/'+info['html_sha256']+'/'+info['entry']+'?preview='+identity);self.send_header('Cache-Control','no-store');self.send_header('Content-Length','0');self.end_headers();return
                    if pinned and pinned!=info['html_sha256']:
                        self.reply(409,b'This tab belongs to an older preview run. Reload its dashboard before downloading. No files from another run were served.\n','text/plain; charset=utf-8',body,info);return
                    if name not in info['allowed']:
                        self.reply(404,b'Not a completed preview asset.\n','text/plain; charset=utf-8',body,info);return
                    target=directory/Path(*path.parts)
                    if target.is_symlink() or any(parent.is_symlink() for parent in target.parents):raise ValueError('Preview assets cannot be symlinks')
                    data=target.read_bytes()
                    expected=info['files'].get(name)
                    if expected and hashlib.sha256(data).hexdigest()!=expected:raise ValueError('Asset differs from completed publication; recover or regenerate before reloading.')
                media=mimetypes.guess_type(name)[0] or 'application/octet-stream'
                if media.startswith('text/') or media=='application/json':media+='; charset=utf-8'
                self.reply(200,data,media,body,info)
            except FileNotFoundError as error:self.reply(503,('Selected preview files are missing: '+str(error)+'\nRestart from the intended project folder after refresh/preparation.\n').encode('utf-8'),'text/plain; charset=utf-8',body)
            except (OSError,ValueError,KeyError,TypeError) as error:self.reply(503,('Preview temporarily unavailable: '+str(error)+'\nReload after refresh/preparation completes. No staging files were served.\n').encode('utf-8'),'text/plain; charset=utf-8',body)
        def reply(self,status,data,media,body,info=None):
            self.send_response(status);self.send_header('Content-Type',media);self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0');self.send_header('Pragma','no-cache');self.send_header('Expires','0')
            self.send_header('X-ThemeScope-Root-ID',identity);self.send_header('X-ThemeScope-Preview','site' if site else 'dashboard')
            if info:
                self.send_header('X-ThemeScope-Session',info['session']);self.send_header('X-ThemeScope-Run',info['html_sha256'])
                if media.startswith('text/html'):self.send_header('Content-Location','/_preview/'+info['html_sha256']+'/'+info['entry']+'?preview='+identity)
            if status==503:self.send_header('Retry-After','1')
            self.end_headers()
            if body:self.wfile.write(data)
    return Preview


class LoopbackHTTPServer(http.server.ThreadingHTTPServer):
    # Windows SO_REUSEADDR can share an active port; exclusive binding prevents
    # two copies from accepting requests for the same URL.
    allow_reuse_address=os.name!='nt'
    def server_bind(self):
        if os.name=='nt' and hasattr(socket,'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET,socket.SO_EXCLUSIVEADDRUSE,1)
        super().server_bind()


def create_server(root=ROOT,site=False,port=None):
    directory=Path(root).resolve()/('site' if site else 'output/manual_csv')
    entry=directory/('index.html' if site else 'dashboard.html')
    if not entry.is_file():raise ValueError('No saved '+str(entry)+'. Run '+('prepare-site.cmd' if site else 'refresh.cmd')+' first.')
    with output_lock(directory,timeout=.5):info=snapshot_info(directory,site)
    preferred=8001 if site else 8000
    requested=preferred if port is None else port
    if not 0<=requested<=65535:raise ValueError('--port must be between 0 and 65535')
    try:server=LoopbackHTTPServer(('127.0.0.1',requested),preview_handler(directory,site))
    except OSError as error:
        if error.errno not in {errno.EADDRINUSE,10048} and getattr(error,'winerror',None) not in {10048,10013}:raise
        if port is not None:raise ValueError(f'Port {requested} is occupied or unavailable. No browser was opened and no process was stopped. Intended folder: {directory}. Close the known old preview console with Ctrl+C, omit --port for automatic selection, or choose --port {requested+1 if requested<65535 else 8002}.') from error
        server=LoopbackHTTPServer(('127.0.0.1',0),preview_handler(directory,site))
    server.preview_signature=(info['session'],info['html_sha256'])
    url=f'http://127.0.0.1:{server.server_port}/_preview/{info["html_sha256"]}/{info["entry"]}?preview={root_identity(directory,site)}'
    return server,info,url


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site',action='store_true');parser.add_argument('--port',type=int,default=None);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args(argv)
    server,info,url=create_server(ROOT,args.site,args.port)
    with server:
        console('Preview type: '+info['type']+'\nServing directory: '+info['directory']+'\nActual snapshot session: '+info['session']+'\nGenerated: '+info['generated']+'\nHTML SHA256: '+info['html_sha256']+'\nExact URL: '+url+'\nLatest metadata URL: http://127.0.0.1:'+str(server.server_port)+'/'+info['metadata']+'?preview='+root_identity(info['directory'],args.site))
        print('Server bound successfully on loopback. Leave this console open; Ctrl+C stops it. Refresh and prepare-site are separate; reload this exact URL after updates. Old tabs/other project copies and Cloudflare do not update automatically.',flush=True)
        if not args.no_browser:
            try:
                if not webbrowser.open(url):print('Browser did not open automatically. Paste the exact URL above; the server remains running.',flush=True)
            except (webbrowser.Error,OSError):print('Browser launch failed. Paste the exact URL above; the server remains running.',flush=True)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError,KeyError) as error:
        print('PREVIEW FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
