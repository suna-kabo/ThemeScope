"""Private loopback API. Exports and dashboard share one committed DB snapshot."""
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import date
from hashlib import sha256
import json
import re
import unicodedata
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.concurrency import run_in_threadpool
from ..storage import canonical
from ..local_refresh_lock import RefreshBusy
from .service import RefreshService
from ..research import queries
from ..research.v2 import current_contract
from .credentials import app_data
from .saved import Saved


def local_identity(root, mode):
    return {'app': 'ThemeScope local', 'protocol': 1, 'mode': mode,
            'workspace': sha256(str(Path(root).resolve()).encode()).hexdigest()}


def export_response(snapshot, text, name):
    slug = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    slug = re.sub(r'[^A-Za-z0-9]+', '-', slug).strip('-')[:100].rstrip('-') or 'Theme-Watchlist'
    session = date.fromisoformat(snapshot['session']).isoformat()
    return Response(text, media_type='text/plain',
                    headers={'Content-Disposition': f'attachment; filename="{slug}-{session}.txt"'})


def create_app(root, service=None, *, automatic=False, personal_dir=None):
    root=Path(root);service=service or RefreshService(root)
    if personal_dir is None:
        personal_dir = service.runtime if service.mode == 'fixture' else app_data()
    saved = Saved(Path(personal_dir) / 'saved.json')

    @asynccontextmanager
    async def lifespan(app):
        if automatic:
            await run_in_threadpool(service.auto_refresh)
        yield

    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None,lifespan=lifespan)
    @app.middleware('http')
    async def local_only(request:Request,call_next):
        if (request.url.hostname not in ('127.0.0.1','localhost','::1') or
                (request.headers.get('sec-fetch-site') == 'cross-site' and request.url.path.startswith('/api/'))):
            return JSONResponse({'detail':'Local access required'},status_code=403)
        if request.method not in ('GET','HEAD','OPTIONS') and request.headers.get('origin')!=str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'Same-origin browser request required'},status_code=403)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; connect-src 'self'; style-src 'self'; font-src 'self'; script-src 'self'; frame-ancestors 'none'"
        return response
    @app.get('/')
    def home():return FileResponse(root/'static/vnext/index.html')
    @app.get('/app.js')
    def js():return FileResponse(root/'static/vnext/app.js',media_type='application/javascript')
    @app.get('/workspace.js')
    def workspace_js():return FileResponse(root/'static/vnext/workspace.js',media_type='application/javascript')
    @app.get('/app.css')
    def css():return FileResponse(root/'static/vnext/app.css',media_type='text/css')
    @app.get('/Research.woff2')
    def research_font():return FileResponse(root/'static/Research.woff2',media_type='font/woff2')
    @app.get('/Research-LICENSE.txt')
    def research_font_license():return FileResponse(root/'static/Research-LICENSE.txt',media_type='text/plain')
    @app.get('/api/local')
    def identity():return local_identity(root, service.mode)
    @app.post('/api/local/startup')
    def startup():return {'started': service.auto_refresh()}
    @app.get('/api/saved')
    def saved_list():
        try:
            return saved.read()
        except (OSError, ValueError):
            raise HTTPException(503, 'Saved research is unavailable') from None
    @app.post('/api/saved')
    async def save(request: Request):
        try:
            body = bytearray()
            async for chunk in request.stream():
                if len(body) + len(chunk) > 65536:
                    raise ValueError
                body.extend(chunk)
            data = json.loads(body)
            entries = data['entries']
            merge = data.get('merge', False)
            if not isinstance(entries, dict) or type(merge) is not bool or (merge and None in entries.values()):
                raise ValueError
            return await run_in_threadpool(saved.update, entries, merge=merge)
        except (ValueError, KeyError, TypeError, AttributeError):
            raise HTTPException(400, 'Invalid Saved research update') from None
        except (OSError, RefreshBusy):
            raise HTTPException(503, 'Saved research is unavailable') from None
    @app.get('/api/status')
    @app.get('/api/refresh/status')
    def status():return service.status()
    @app.post('/api/refresh',status_code=202)
    def refresh():
        try:service.start()
        except RefreshBusy:raise HTTPException(409,'A refresh is already active') from None
        return {'state':'running'}
    @app.get('/api/dashboard-data')
    def data():
        snapshot, version = service.snapshot(metadata_only=True)
        token = json.dumps([version, (snapshot or {}).get('refreshed_at')], separators=(',', ':'))
        return Response(canonical(snapshot), media_type='application/json',
                        headers={'X-ThemeScope-Snapshot': token})
    def query(name, *args):
        result=getattr(queries,name)(service.snapshot(),*args)
        if result is None:raise HTTPException(404,'Research unavailable')
        return Response(canonical(result),media_type='application/json')
    @app.get('/api/market')
    def market():return query('get_market_state')
    @app.get('/api/market/changes')
    def changes():return query('get_market_changes')
    @app.get('/api/research-list')
    def research_list():return query('get_research_list')
    @app.get('/api/themes/{theme_id}')
    def theme(theme_id:str):return query('get_theme',theme_id)
    @app.get('/api/themes/{theme_id}/members')
    def members(theme_id:str):return query('get_theme_members',theme_id)
    @app.get('/api/themes/{theme_id}/history')
    def theme_history(theme_id:str):
        result=service.theme_history(theme_id)
        if result is None:raise HTTPException(404,'Theme history unavailable')
        return Response(canonical(result),media_type='application/json')
    @app.get('/api/stocks/{ticker}')
    def stock(ticker:str):return query('get_stock',ticker)
    @app.get('/api/exports/combined.txt')
    def combined():
        snapshot=service.snapshot()
        if not current_contract(snapshot):
            raise HTTPException(404,'No current research export')
        return export_response(snapshot, snapshot['exports']['combined'], 'Primary-Research')

    @app.get('/api/exports/{theme_id}.txt')
    def individual(theme_id:str):
        snapshot=service.snapshot()
        if not current_contract(snapshot):
            raise HTTPException(404,'No current research export')
        text=snapshot['exports']['individual'].get(theme_id)
        theme=next((row for row in snapshot['themes'] if row['theme_id']==theme_id), None)
        if text is None or theme is None:
            raise HTTPException(404,'No qualifying theme export')
        return export_response(snapshot, text, theme.get('name') or theme_id)
    app.state.service=service
    return app
