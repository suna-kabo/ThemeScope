"""Real loopback routes + static publisher, manufactured input and fake Cloudflare.

No account credentials, live provider data, or actual deployment is involved.
"""
from copy import deepcopy
from datetime import datetime, timezone
from email.message import Message
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import patch
import contextlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import unittest

from scripts import update_public as daily
from scripts import publish_public_snapshot as publisher
from scripts import build_public_snapshot as builder
from public_snapshot_support import public_contract_fixture

ROOT=Path(__file__).resolve().parents[1]


class DailyIntegrationTests(unittest.TestCase):
    def test_existing_live_contract_api_refreshes_and_validated_main_upload_is_confirmed(self):
        import uvicorn
        from src.themescope.local.app import create_app
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);shutil.copytree(ROOT/'static',root/'static')
            (root/'.gitignore').write_text('dist/\nruntime/\n')
            def git(*args):return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.PIPE).decode().strip()
            git('init','-q','-b','main');git('add','.')
            git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Manufactured fixture')
            commit=git('rev-parse','HEAD')
            class Service:
                def __init__(self):
                    self.data=public_contract_fixture();self.state='idle';self.refreshes=0
                def snapshot(self):return deepcopy(self.data)
                def status(self):return {'mode':'live','state':self.state,'target_session':self.data['session'],
                    'last_successful_session':self.data['session'],'last_successful_refresh':self.data['refreshed_at'],
                    'completeness':self.data['completeness']}
                def start(self):
                    self.refreshes+=1;self.data['refreshed_at']=datetime.now(timezone.utc).isoformat();self.state='success'
            service=Service()
            sock=socket.socket();sock.bind(('127.0.0.1',0));origin='http://127.0.0.1:'+str(sock.getsockname()[1])
            server=uvicorn.Server(uvicorn.Config(create_app(root,service),log_level='error',access_log=False))
            worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
            deadline=time.monotonic()+5
            while not server.started and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(server.started)
            calls=[];uploaded=[False];output=StringIO()
            def wrangler(args,directory):
                calls.append(args)
                if args==['whoami','--json']:return json.dumps({'loggedIn':True,'accounts':[{'id':'a'*32}]})
                if args==['auth','token','--json']:return json.dumps({'type':'oauth','token':'CF_TEST_CANARY'})
                if args[:3]==['pages','project','list']:return '[{"Project Name":"themescope"}]'
                if args[:3]==['pages','deployment','list']:
                    old={'Id':'old','Branch':'refactor/themescope-vnext','Environment':'Production','Status':'1 hour ago','Source':'old'}
                    return json.dumps([{'Id':'new','Branch':'main','Environment':'Production','Status':'just now','Source':commit[:7]},old] if uploaded[0] else [old])
                self.assertEqual(args[:2],['pages','deploy'])
                self.assertIn('--branch=main',args);self.assertIn('--commit-hash='+commit,args)
                self.assertFalse(any('LOCAL_SECRET_CANARY' in arg for arg in args))
                builder.validate_output(Path(args[2]));uploaded[0]=True
                return 'Not proof by itself'
            response=BytesIO(json.dumps({'success':True,'result':{'name':'themescope','production_branch':'main',
                'source':{'config':{'production_deployments_enabled':False}}}}).encode())
            response.status=200;response.headers=Message();response.headers['Content-Type']='application/json'
            try:
                with patch.dict(os.environ,{'APCA_API_KEY_ID':'LOCAL_KEY_CANARY','APCA_API_SECRET_KEY':'LOCAL_SECRET_CANARY','CLOUDFLARE_ACCOUNT_ID':'a'*32}),patch.object(daily,'ORIGIN',origin),patch.object(builder,'API',origin+'/api/dashboard-data'),patch.object(publisher,'wrangler',side_effect=wrangler),patch.object(publisher,'build_opener') as cf,contextlib.redirect_stdout(output):
                    cf.return_value.open.return_value=response
                    self.assertEqual(daily.update(root=root),'2026-11-06')
                    self.assertEqual(cf.return_value.open.call_args.args[0].get_header('Authorization'),'Bearer CF_TEST_CANARY')
                self.assertTrue(uploaded[0]);self.assertEqual(service.refreshes,1)
                self.assertTrue(worker.is_alive(),'An existing server must remain running')
                self.assertIn('Public deployment: CONFIRMED',output.getvalue())
                self.assertNotIn('LOCAL_SECRET_CANARY',output.getvalue());self.assertNotIn('CF_TEST_CANARY',output.getvalue())
                self.assertEqual(git('status','--porcelain'),'')
            finally:
                server.should_exit=True;worker.join(10);sock.close()
