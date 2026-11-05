"""Private loopback API. Exports and dashboard share one committed DB snapshot."""
from pathlib import Path
import json
from fastapi import FastAPI,Request,HTTPException
from fastapi.responses import Response,FileResponse,JSONResponse
from ..storage import canonical
from ..local_refresh_lock import RefreshBusy
from .service import RefreshService


def create_app(root,service=None):
    root=Path(root);service=service or RefreshService(root)
    app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
    @app.middleware('http')
    async def local_only(request:Request,call_next):
        if request.url.hostname not in ('127.0.0.1','localhost','::1'):
            return JSONResponse({'detail':'Local access required'},status_code=403)
        if request.method=='POST' and request.headers.get('origin')!=str(request.base_url).rstrip('/'):
            return JSONResponse({'detail':'Same-origin browser request required'},status_code=403)
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Content-Security-Policy']="default-src 'self'; connect-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'"
        return response
    @app.get('/')
    def home():return FileResponse(root/'static/vnext/index.html')
    @app.get('/app.js')
    def js():return FileResponse(root/'static/vnext/app.js',media_type='application/javascript')
    @app.get('/app.css')
    def css():return FileResponse(root/'static/vnext/app.css',media_type='text/css')
    @app.get('/preview.js')
    def preview():return Response('window.FIXTURE_SNAPSHOT=null;',media_type='application/javascript')
    @app.get('/api/status')
    @app.get('/api/refresh/status')
    def status():return service.status()
    @app.post('/api/refresh',status_code=202)
    def refresh():
        try:service.start()
        except RefreshBusy:raise HTTPException(409,'A refresh is already active') from None
        return {'state':'running'}
    @app.get('/api/dashboard-data')
    def data():return Response(canonical(service.snapshot()),media_type='application/json')
    @app.get('/api/exports/combined.txt')
    def combined():
        snapshot=service.snapshot()
        if not snapshot:raise HTTPException(404,'No successful snapshot')
        return Response(snapshot['exports']['combined'],media_type='text/plain',headers={'Content-Disposition':'attachment; filename="Primary.txt"'})
    @app.get('/api/exports/{theme_id}.txt')
    def individual(theme_id:str):
        snapshot=service.snapshot()
        text=(snapshot or {}).get('exports',{}).get('individual',{}).get(theme_id)
        if text is None:raise HTTPException(404,'No qualifying theme export')
        return Response(text,media_type='text/plain',headers={'Content-Disposition':'attachment; filename="Theme.txt"'})
    app.state.service=service
    return app
