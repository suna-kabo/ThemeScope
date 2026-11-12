"""Frozen public publishing tests use a mocked loopback API and fake Wrangler only."""
from contextlib import nullcontext
from email.message import Message
from io import BytesIO
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
import copy
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
import unittest

from scripts import build_public_snapshot as builder
from scripts import publish_public_snapshot as publisher
from public_snapshot_support import public_contract_fixture

from scripts.static_pages import copy_fonts
ROOT=Path(__file__).resolve().parents[1]


class PublicSnapshotTests(unittest.TestCase):
    def setUp(self):
        quiet=patch('builtins.print');quiet.start();self.addCleanup(quiet.stop)
        self.source=public_contract_fixture()
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        assets=self.root/'static/vnext';assets.mkdir(parents=True)
        for name in builder.ASSETS:shutil.copyfile(ROOT/'static/vnext'/name,assets/name)
        copy_fonts(ROOT,self.root/'static')

    def build(self,source=None,session='2026-11-06'):
        with patch.object(builder,'fetch_snapshot',return_value=source if source is not None else self.source):
            return builder.build(session,self.root)

    def test_real_contract_projection_preserves_metrics_and_ignores_private_internals(self):
        source=self.source
        source.update(performance={'private':'drop'},raw_payload={'secret':'drop'},
                      configuration_hash='internal',environment={'private':'drop'},account={'private':'drop'})
        source['provider_health']['identity']='internal-data-version'
        source['themes'][0]['index']['raw_payload']={'drop':True}
        source['relationships'][0]['relative']['private']='drop'
        source['completeness'].update(trading_target=20,terminal_target=1,historical_inputs=0)
        result=builder.project_snapshot(source,'2026-11-06')
        self.assertEqual(result['completeness'],source['completeness'])
        self.assertEqual(result['themes'][0]['score'],source['themes'][0]['score'])
        self.assertEqual(result['themes'][0]['returns'],source['themes'][0]['returns'])
        self.assertEqual(result['relationships'][0]['relative']['w'],source['relationships'][0]['relative']['w'])
        self.assertEqual(result['exports'],source['exports'])
        self.assertEqual(result['provider_health'],{'status':'Healthy'})
        encoded=json.dumps(result)
        for key in ('performance','raw_payload','configuration_hash','environment','account','history','internal-data-version','private'):
            self.assertNotIn('"'+key+'"',encoded)

    def test_countertrend_public_projection_both_sides_and_malformed_files(self):
        from src.themescope.research.countertrend_exports import attach
        mapping={ticker:{'status':'verified','symbol':symbol} for ticker,symbol in self.source['research']['countertrend']['exports']['symbols'].items()}
        for side,filenames in [('long',{'Countertrend.txt','Strong-Leaders.txt','Relative-Weakness.txt'}),('short',{'Countertrend.txt','Resilient.txt','Snapback.txt'})]:
            source=copy.deepcopy(self.source);source['research']['countertrend']['side']=side
            source=attach(source,mapping)
            result=builder.project_snapshot(source,'2026-11-06')
            self.assertEqual(result['exports'],source['exports'])
            published=result['research']['countertrend']['exports']
            self.assertEqual(set(published['files']),filenames)
            self.assertNotIn('symbols',published)
            self.assertEqual(published['files'],source['research']['countertrend']['exports']['files'])
            source['research']['countertrend']['exports']['files']['Countertrend.txt']='TEST:UNKNOWN\n'
            with self.assertRaisesRegex(builder.SnapshotError,'published lens'):builder.project_snapshot(source,'2026-11-06')

    def test_bundled_font_and_license_are_pinned(self):
        for name in ('InterVariable.woff2','Inter-LICENSE.txt'):
            with self.subTest(asset=name):
                path=self.root/'static'/name;original=path.read_bytes();path.write_bytes(original+b'unapproved')
                with self.assertRaises(ValueError):self.build()
                path.write_bytes(original)
        output=self.build();(output/'InterVariable.woff2').write_bytes(b'unknown binary')
        with self.assertRaisesRegex(builder.SnapshotError,'font/license'):builder.validate_output(output)

    def test_current_assets_determinism_safety_no_network_database_or_calculation(self):
        with patch('socket.socket',side_effect=AssertionError('No network')),patch.object(sqlite3,'connect',side_effect=AssertionError('No DB')),patch('scripts.build_cloudflare_demo.demo_snapshot',side_effect=AssertionError('No calculations')):
            output=self.build()
            first={p.name:p.read_bytes() for p in output.iterdir()}
            self.build()
        self.assertEqual(first,{p.name:p.read_bytes() for p in output.iterdir()})
        self.assertEqual(set(first),builder.FILES)
        for name in builder.ASSETS:self.assertEqual(first[name],(ROOT/'static/vnext'/name).read_bytes())
        # Windows write_text uses CRLF for the generated wrapper; the JSON and
        # all byte-for-byte rebuild/source-asset assertions remain unchanged.
        payload=json.loads(first['preview.js'].decode().replace('\r\n','\n').removeprefix('window.THEMESCOPE_STATIC_SOURCE = ').removesuffix(';\n'))
        self.assertEqual(payload['mode'],'public_snapshot')
        self.assertFalse(payload['snapshot']['synthetic_fixture'])
        self.assertIn(b'connect-src \'none\'',first['_headers'])
        self.assertIn(b'Cache-Control: no-store',first['_headers'])
        builder.validate_output(output)

    def test_unreachable_api_is_closed_and_no_output(self):
        with patch.object(builder,'build_opener') as factory:
            factory.return_value.open.side_effect=URLError('private error must not be echoed')
            with self.assertRaisesRegex(builder.SnapshotError,'Start ThemeScope'):builder.build('2026-11-06',self.root)
        self.assertFalse((self.root/'dist/cloudflare-public').exists())

    def test_strict_loopback_request_and_malformed_responses(self):
        def response(data,content='application/json',status=200):
            r=BytesIO(data);r.status=status;r.headers=Message();r.headers['Content-Type']=content;return r
        with patch.object(builder,'build_opener') as factory:
            factory.return_value.open.return_value=response(json.dumps(self.source).encode())
            self.assertEqual(builder.fetch_snapshot(),self.source)
            request=factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url,builder.API)
            self.assertEqual(request.header_items(),[('Accept','application/json')])
            self.assertEqual(factory.return_value.open.call_args.kwargs['timeout'],15)
        for data,content,status in [(b'','application/json',200),(b'{bad','application/json',200),
            (b'{}','text/html',200),(b'{}','application/json',503),(b'\xff','application/json',200),
            (b'{"x":1,"x":2}','application/json',200),(b'{"x":NaN}','application/json',200)]:
            with self.subTest(data=data),patch.object(builder,'build_opener') as factory:
                factory.return_value.open.return_value=response(data,content,status)
                with self.assertRaises(builder.SnapshotError):builder.fetch_snapshot()
        with patch.object(builder,'LIMIT',2),patch.object(builder,'build_opener') as factory:
            factory.return_value.open.return_value=response(b'123')
            with self.assertRaises(builder.SnapshotError):builder.fetch_snapshot()
        with self.assertRaises(builder.SnapshotError):builder.NoRedirect().redirect_request(None,None,None,None,None,None)

    def test_synthetic_incomplete_wrong_schema_session_and_malformed_refused(self):
        changes=[{'synthetic_fixture':True},{'synthetic_fixture':None},{'session':'2026-11-05'},
            {'schema':'legacy'},{'refreshed_at':None},{'refreshed_at':'2026-11-05T00:00:00Z'},
            {'provider_health':[]},{'completeness':None},{'completeness':{'complete':False}},
            {'completeness':{'complete':True,'required':2,'valid_target':1}},{'themes':[]},
            {'themes':[{'bad':'shape'}]},{'relationships':{}},{'earnings':[]},
            {'relationships':[self.source['relationships'][0]]*2}]
        for changeset in changes:
            with self.subTest(change=changeset):
                source=dict(self.source,**changeset)
                with self.assertRaises(builder.SnapshotError):self.build(source)
        for source in (None,[],{},''):
            with self.assertRaises(builder.SnapshotError):builder.project_snapshot(source,'2026-11-06')
        with self.assertRaises(builder.SnapshotError):self.build(session='bad-session')

    def test_failed_rebuild_preserves_prepared_output_and_cleans_staging(self):
        output=self.build();before=(output/'preview.js').read_bytes()
        self.source['today_plan']='APCA_API_KEY_ID=not-a-real-key-but-forbidden'
        with self.assertRaises(builder.SnapshotError):self.build()
        self.assertEqual((output/'preview.js').read_bytes(),before)
        self.assertFalse(list((self.root/'dist').glob('.public-build-*')))

    def test_known_public_fields_cannot_carry_secrets_paths_or_raw_data(self):
        for bad in ('APCA_API_KEY_ID','APCA_API_SECRET_KEY','ALPHAVANTAGE_API_KEY',
            'Bearer this_is_not_a_real_token','api_token=manufactured_for_test',
            '.env',r'C:\Users\tester\private',r'D:\ThemeScope\status.json',r'\\server\private',
            '/home/tester/private','/workspace/private','runtime/vnext','vnext.sqlite3',
            'http://127.0.0.1:8766/api/dashboard-data','http://localhost:8766/', '"bars": {}'):
            with self.subTest(bad=bad):
                source=copy.deepcopy(self.source);source['today_plan']=bad
                with self.assertRaises(builder.SnapshotError):self.build(source)
        source=copy.deepcopy(self.source);source['exports']['combined']='NASDAQ:DEMOA\nBearer secret\n'
        with self.assertRaises(builder.SnapshotError):self.build(source)

    def test_tampered_output_symlinks_and_extra_files_rejected(self):
        output=self.build();(output/'private.txt').write_text('unexpected')
        with self.assertRaises(builder.SnapshotError):builder.validate_output(output)
        (output/'private.txt').unlink();(output/'favicon.ico').write_bytes(b'not a favicon')
        with self.assertRaises(builder.SnapshotError):builder.validate_output(output)
        shutil.rmtree(output);output.symlink_to(self.root/'static',target_is_directory=True)
        with self.assertRaises(builder.SnapshotError):self.build()


class WranglerListingTests(unittest.TestCase):
    def listing(self, output):
        with patch.object(publisher,'wrangler',return_value=output):
            return publisher.listing(['pages','project','list','--json'],ROOT)

    def test_pure_json_array(self):
        self.assertEqual(self.listing('[{"Project Name":"themescope"}]'),[{'Project Name':'themescope'}])
        self.assertEqual(self.listing(' \n[]\n '),[])

    def test_utf8_informational_prefix(self):
        row=[{'Project Name':'themescope','Note':'本機登入'}]
        payload=json.dumps(row,ensure_ascii=False)
        for prefix in ('⛅ Wrangler · 已登入\n','npm notice 更新資訊: ', '[INFO] Wrangler 資訊\n'):
            with self.subTest(prefix=prefix):
                self.assertEqual(self.listing(prefix+payload),row)

    def test_informational_suffix(self):
        row=[{'Environment':'Production','Branch':publisher.BRANCH,'Source':'abcdef0'}]
        for suffix in ('\nnpm notice 新版本可用\n','\n[NOTICE] Metadata complete', ' Wrangler finished.'):
            with self.subTest(suffix=suffix):
                self.assertEqual(self.listing('Wrangler metadata:\n'+json.dumps(row)+suffix),row)

    def test_malformed_or_missing_json_rejected_without_raw_output(self):
        for output in ('private-output-canary', '[{"broken":', '[{"inner":[{}]} garbage]',
                       '{"inner":[{}]', '[{}]\n[{broken}]', '[{}]]', '[{}]\n[{}]',
                       '[{"duplicate":1,"duplicate":2}]', '[{"value":NaN}]'):
            with self.subTest(output=output),self.assertRaises(builder.SnapshotError) as error:
                self.listing(output)
            self.assertEqual(str(error.exception),'Wrangler returned unexpected JSON; nothing further will be deployed.')
            self.assertNotIn('private-output-canary',str(error.exception))

    def test_wrong_json_top_level_or_row_type_rejected(self):
        for output in ('{"projects":[{}]}','"[{}]"','null','true','42','[1]','[[]]','[null]'):
            with self.subTest(output=output),self.assertRaises(builder.SnapshotError):
                self.listing(output)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        quiet=patch('builtins.print');quiet.start();self.addCleanup(quiet.stop)
        self.commit='a'*40
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);assets=self.root/'static/vnext';assets.mkdir(parents=True)
        for name in builder.ASSETS:shutil.copyfile(ROOT/'static/vnext'/name,assets/name)
        copy_fonts(ROOT,self.root/'static')
        with patch.object(builder,'fetch_snapshot',return_value=public_contract_fixture()):
            self.output=builder.build('2026-11-06',self.root)
        self.before=[{'Id':'old','Environment':'Production','Branch':publisher.BRANCH,'Source':'previous','Status':'1 minute ago'}]
        self.after=[{'Id':'new','Environment':'Production','Branch':publisher.BRANCH,'Source':self.commit[:7],'Status':'just now'}]+self.before

    def run_publish(self,projects=None,before=None,after=None,deploy_error=False,noisy=False):
        calls=[]
        def metadata(value):
            payload=json.dumps(value)
            return '⛅ Wrangler · 本機資訊\n'+payload+'\nnpm notice 更新可用' if noisy else payload
        def fake(arguments,directory):
            calls.append(arguments)
            if arguments[:3]==['pages','project','list']:return metadata([{'Project Name':'themescope'}] if projects is None else projects)
            if arguments[:3]==['pages','deployment','list']:
                n=sum(c[:3]==['pages','deployment','list'] for c in calls)
                return metadata((self.before if before is None else before) if n==1 else (self.after if after is None else after))
            self.assertEqual(arguments[:2],['pages','deploy'])
            self.assertEqual(arguments[3:5],['--project-name=themescope','--branch='+publisher.BRANCH])
            builder.validate_output(Path(arguments[2]))
            if deploy_error:raise builder.SnapshotError('Wrangler failed')
            return 'not used as proof of production'
        with patch.object(publisher,'clean_checkout',return_value=self.commit),patch.object(publisher,'build_locked',return_value=self.output),patch.object(publisher,'production_project') as settings,patch.object(publisher,'publication_lock',return_value=nullcontext()),patch.object(publisher,'wrangler',side_effect=fake),patch.object(publisher.time,'sleep'):
            publisher.publish('2026-11-06','themescope',self.root)
            settings.assert_called_once()
        return calls

    def test_existing_production_verified_and_upload_is_exact_static_allowlist(self):
        for noisy in (False,True):
            with self.subTest(noisy=noisy):
                calls=self.run_publish(noisy=noisy)
                self.assertEqual(sum(c[:2]==['pages','deploy'] for c in calls),1)
                self.assertFalse(any('create' in c for c in calls))

    def test_missing_project_wrong_production_preview_and_pending_fail_closed(self):
        for kwargs in (dict(projects=[]),dict(before=[]),dict(before=[dict(self.before[0],Environment='Preview')]),
                       dict(after=self.before),dict(after=[dict(self.after[0],Environment='Preview')]),
                       dict(after=[dict(self.after[0],Branch='refactor/themescope-vnext')]),
                       dict(after=[dict(self.after[0],Status='Active')]),dict(after=[dict(self.after[0],Status='Failure')]),
                       dict(after=[dict(self.after[0],Status='unknown')]),dict(after=[dict(self.after[0],Source='b'*7)]),dict(deploy_error=True)):
            with self.subTest(kwargs=kwargs),self.assertRaises(builder.SnapshotError):self.run_publish(**kwargs)

    def test_branch_dirty_tree_and_tracked_artifacts_guard(self):
        self.assertEqual(publisher.BRANCH,'main')
        for results in (['refactor/themescope-vnext'],[publisher.BRANCH,' M changed'],[publisher.BRANCH,'','dist/private']):
            with patch.object(publisher,'git',side_effect=results),self.assertRaises(builder.SnapshotError):publisher.clean_checkout(self.root)
        with patch.object(publisher,'git',side_effect=[publisher.BRANCH,'','',self.commit]):self.assertEqual(publisher.clean_checkout(self.root),self.commit)
        with self.assertRaises(builder.SnapshotError):publisher.publish('2026-11-06','bad;project',self.root)

    def test_wrangler_uses_local_auth_sanitized_environment_no_shell_no_raw_errors(self):
        env={'APCA_API_KEY_ID':'manufactured-private','APCA_API_SECRET_KEY':'manufactured-private','ALPHAVANTAGE_API_KEY':'manufactured-private','PATH':os.environ.get('PATH','')}
        with patch.dict(os.environ,env,clear=True),patch.object(shutil,'which',return_value='npx'),patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],0,'[]','')) as run:
            self.assertEqual(publisher.wrangler(['pages','project','list','--json'],self.root),'[]')
            options=run.call_args.kwargs
            self.assertEqual(options['cwd'],self.root)
            self.assertFalse(any('API_KEY' in k or 'API_SECRET' in k for k in options['env']))
            self.assertEqual(options['env']['CI'],'true')
            self.assertEqual(options['encoding'],'utf-8')
            self.assertEqual(options['errors'],'strict')
            self.assertNotIn('shell',options)
        with patch.object(shutil,'which',return_value='npx'),patch.object(subprocess,'run',return_value=subprocess.CompletedProcess([],1,'private token','private path')):
            with self.assertRaisesRegex(builder.SnapshotError,'login'):publisher.wrangler([],self.root)

    def test_first_main_upload_accepts_old_deployment_only_after_actual_settings_check(self):
        calls=self.run_publish(before=[dict(self.before[0],Branch='refactor/themescope-vnext')])
        self.assertEqual(sum(c[:2]==['pages','deploy'] for c in calls),1)


class ProductionProjectTests(unittest.TestCase):
    def setUp(self):
        self.account='a'*32
        self.identity={'loggedIn':True,'accounts':[{'id':self.account}]}
        self.auth={'type':'oauth','token':'manufactured-cloudflare-token'}
        self.settings={'name':'themescope','production_branch':'main',
                       'source':{'config':{'production_deployments_enabled':False}}}

    def verify(self,*,settings=None,identity=None,auth=None,raw=None,status=200,content='application/json'):
        response=BytesIO(raw if raw is not None else json.dumps({'success':True,'result':self.settings if settings is None else settings}).encode())
        response.status=status;response.headers=Message();response.headers['Content-Type']=content
        def wrangler(args,directory):
            if args==['whoami','--json']:return json.dumps(self.identity if identity is None else identity)
            self.assertEqual(args,['auth','token','--json'])
            return json.dumps(self.auth if auth is None else auth)
        with patch.dict(os.environ,{},clear=True),patch.object(publisher,'wrangler',side_effect=wrangler),patch.object(publisher,'build_opener') as factory:
            factory.return_value.open.return_value=response
            publisher.production_project('themescope',ROOT)
            return factory.return_value.open.call_args.args[0]

    def test_configured_main_branch_and_disabled_git_builds_are_verified_with_secret_safe_auth(self):
        request=self.verify()
        self.assertEqual(request.full_url,'https://api.cloudflare.com/client/v4/accounts/'+self.account+'/pages/projects/themescope')
        self.assertEqual(request.get_method(),'GET')
        self.assertEqual(request.get_header('Authorization'),'Bearer '+self.auth['token'])
        self.assertFalse(any('APCA' in k.upper() or 'ALPHAVANTAGE' in k.upper() for k,v in request.header_items()))
        self.verify(settings=dict(self.settings,source=None)) # Direct upload has no Git source.
        self.verify(auth={'type':'api_key','key':'manufactured-key','email':'fixture@example.invalid'})

    def test_wrong_project_branch_or_automatic_git_builds_cannot_upload(self):
        for settings in (dict(self.settings,production_branch='refactor/themescope-vnext'),dict(self.settings,name='another'),
                         dict(self.settings,source={}),dict(self.settings,source={'config':{'production_deployments_enabled':True}})):
            with self.subTest(settings=settings),self.assertRaises(builder.SnapshotError):self.verify(settings=settings)

    def test_missing_ambiguous_account_and_auth_fail_closed(self):
        for identity in ({},{'loggedIn':False,'accounts':[]},{'loggedIn':True,'accounts':[{'id':'bad'}]},
                         {'loggedIn':True,'accounts':[{'id':'a'*32},{'id':'b'*32}]}):
            with self.subTest(identity=identity),self.assertRaises(builder.SnapshotError):self.verify(identity=identity)
        with self.assertRaises(builder.SnapshotError):self.verify(auth={})

    def test_malformed_failure_redirects_and_nonjson_responses_are_sanitized(self):
        for kwargs in ({'raw':b'private-payload-canary'},{'raw':b'{"success":true,"success":false}'},
                       {'raw':b'{"success":false}'},{'status':403},{'content':'text/html'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(builder.SnapshotError) as caught:self.verify(**kwargs)
            self.assertNotIn('private-payload-canary',str(caught.exception))
        with self.assertRaises(builder.SnapshotError):publisher.NoCloudflareRedirect().redirect_request(None,None,None,None,None,None)
