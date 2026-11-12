"""Daily orchestration uses manufactured live-contract snapshots and fake publishing."""
from datetime import datetime, timezone
from email.message import Message
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import URLError, HTTPError
import contextlib
import os
import subprocess
import tempfile
import unittest

from scripts import update_public as daily
from scripts import publish_public_snapshot as publisher
from public_snapshot_support import public_contract_fixture


class DailyUpdateTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.commit='a'*40;self.now=datetime(2026,11,7,1,tzinfo=timezone.utc)
        self.snapshot=public_contract_fixture()
        self.initial={'state':'idle','mode':'live','last_successful_refresh':None}
        self.success={'state':'success','mode':'live','target_session':'2026-11-06',
            'last_successful_session':'2026-11-06','last_successful_refresh':self.snapshot['refreshed_at'],
            'completeness':self.snapshot['completeness']}
        self.polls=[];self.start_server=False;self.client=Mock();self.process=Mock();self.process.poll.return_value=None
        self.probes=0;self.output=StringIO();self.err=StringIO()
        def request(path,**kwargs):
            if path=='/api/status':
                self.probes+=1
                if self.start_server and self.probes==1:raise daily.ServerUnavailable('not running')
                return self.initial
            if path=='/api/refresh':
                self.assertTrue(kwargs['post']);return {'state':'running'}
            if path=='/api/refresh/status':return self.polls.pop(0) if self.polls else self.success
            self.assertEqual(path,'/api/dashboard-data');return self.snapshot
        self.client.request.side_effect=request
        for p in [patch.dict(os.environ,{'APCA_API_KEY_ID':'LOCAL_KEY_CANARY','APCA_API_SECRET_KEY':'LOCAL_SECRET_CANARY'},clear=True),
                  patch.object(daily,'LoopbackClient',return_value=self.client),
                  patch.object(publisher,'clean_checkout',return_value=self.commit),
                  patch.object(publisher,'publish'),patch.object(daily.subprocess,'Popen',return_value=self.process),
                  patch.object(daily,'datetime')]:
            value=p.start();self.addCleanup(p.stop)
            if getattr(p,'attribute',None)=='publish':self.publish=value
            elif getattr(p,'attribute',None)=='Popen':self.spawn=value
            elif getattr(p,'attribute',None)=='datetime':
                value.now.return_value=self.now;value.fromisoformat.side_effect=datetime.fromisoformat

    def run_update(self,**kwargs):
        with contextlib.redirect_stdout(self.output),contextlib.redirect_stderr(self.err):
            return daily.update(root=self.root,**kwargs)

    def rejected(self):
        with self.assertRaises(daily.SnapshotError):self.run_update()
        self.publish.assert_not_called()
        self.assertNotIn('CONFIRMED',self.output.getvalue())

    def test_success_selects_service_session_and_calls_existing_publisher(self):
        self.assertEqual(self.run_update(),'2026-11-06')
        self.publish.assert_called_once_with('2026-11-06','themescope',self.root)
        self.spawn.assert_not_called();self.process.terminate.assert_not_called()
        self.assertTrue(self.output.getvalue().endswith('Refresh: 2026-11-06 PASS\nCompleteness: PASS\nPublic deployment: CONFIRMED\n'))
        self.assertNotIn('LOCAL_SECRET_CANARY',self.output.getvalue())

    def test_refresh_failure_never_publishes_still_usable_prior_snapshot(self):
        self.success['state']='failed';self.success['error']='LOCAL_SECRET_CANARY'
        self.rejected();self.assertNotIn('LOCAL_SECRET_CANARY',self.err.getvalue())

    def test_incomplete_snapshot(self):
        self.snapshot['completeness']=dict(self.snapshot['completeness'],complete=False)
        self.rejected()

    def test_incomplete_status(self):
        self.success['completeness']={'complete':False};self.rejected()

    def test_session_mismatch(self):
        self.snapshot['session']='2026-11-05';self.rejected()

    def test_last_successful_session_mismatch(self):
        self.success['last_successful_session']='2026-11-05';self.rejected()

    def test_stale_prior_snapshot_same_session_does_not_count_as_refresh_success(self):
        self.snapshot['refreshed_at']='2026-11-07T00:59:59+00:00'
        self.success['last_successful_refresh']=self.snapshot['refreshed_at'];self.rejected()

    def test_snapshot_must_match_status_publication(self):
        self.success['last_successful_refresh']='2026-11-07T00:59:59+00:00';self.rejected()

    def test_fixture_server_and_fixture_snapshot_rejected(self):
        self.initial['mode']='fixture';self.rejected()
        self.initial['mode']='live';self.snapshot['synthetic_fixture']=True;self.rejected()

    def test_no_new_publication_since_prior_success_is_rejected(self):
        self.initial['last_successful_refresh']=self.snapshot['refreshed_at'];self.rejected()

    def test_missing_credentials_prevents_any_server_or_publisher_action(self):
        with patch.dict(os.environ,{},clear=True):self.rejected()
        self.client.request.assert_not_called();self.spawn.assert_not_called()

    def test_dirty_checkout_wrong_branch_and_mid_refresh_change_never_publish(self):
        for reason in ('Publish only from main.','Commit or resolve working-tree changes before publishing.'):
            with patch.object(publisher,'clean_checkout',side_effect=daily.SnapshotError(reason)):self.rejected()
        self.client.request.assert_not_called()
        with patch.object(publisher,'clean_checkout',side_effect=[self.commit,'b'*40]):self.rejected()

    def test_already_running_refresh_is_not_adopted_or_stopped(self):
        self.initial['state']='running';self.rejected();self.spawn.assert_not_called()
        self.assertFalse(any(c.args[0]=='/api/refresh' for c in self.client.request.call_args_list))

    def prepare_owned(self):
        self.start_server=True
        path=self.root/'.venv-vnext'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
        path.parent.mkdir(parents=True);path.touch()

    def test_owned_headless_server_uses_normal_runtime_and_only_its_process_is_stopped(self):
        self.prepare_owned();self.run_update()
        args=self.spawn.call_args.args[0]
        self.assertEqual(args[1:],[str(self.root/'scripts/run_vnext.py'),'--no-browser'])
        self.assertNotIn('--fixture',args)
        self.assertFalse(any('LOCAL_' in a for a in args))
        self.assertEqual(self.spawn.call_args.kwargs['env']['APCA_API_SECRET_KEY'],'LOCAL_SECRET_CANARY')
        self.process.terminate.assert_called_once();self.process.wait.assert_called_once_with(timeout=10)

    def test_owned_server_is_stopped_on_failure(self):
        self.prepare_owned();self.success['state']='failed';self.rejected()
        self.process.terminate.assert_called_once()

    def test_server_that_exits_during_startup_is_not_replaced(self):
        self.prepare_owned();self.process.poll.return_value=1;self.rejected()
        self.spawn.assert_called_once();self.process.terminate.assert_not_called()

    def test_missing_setup_fails_without_starting_other_python(self):
        self.start_server=True;self.rejected();self.spawn.assert_not_called()

    def test_refresh_polling_has_a_finite_deadline_and_does_not_kill_reused_server(self):
        self.success['state']='running';clock=[0.0]
        def wait(seconds):clock[0]+=seconds
        with patch.object(daily.time,'monotonic',side_effect=lambda:clock[0]),patch.object(daily.time,'sleep',side_effect=wait):
            with self.assertRaisesRegex(daily.SnapshotError,'timed out'):self.run_update(timeout=2)
        self.publish.assert_not_called();self.process.terminate.assert_not_called()

    def test_publisher_failure_never_prints_confirmation(self):
        self.publish.side_effect=daily.SnapshotError('Pages production confirmation failed.')
        with self.assertRaises(daily.SnapshotError):self.run_update()
        self.assertNotIn('CONFIRMED',self.output.getvalue())

    def test_invalid_timeout_and_project_fail_before_refresh(self):
        for kwargs in ({'timeout':0},{'timeout':float('inf')},{'timeout':601},{'project':'bad;project'}):
            with self.subTest(kwargs=kwargs),self.assertRaises(daily.SnapshotError):self.run_update(**kwargs)
        self.client.request.assert_not_called();self.publish.assert_not_called()

    def test_cli_returns_nonzero_without_relaying_secret_exception_data(self):
        with patch.object(daily,'update',side_effect=RuntimeError('LOCAL_SECRET_CANARY')),contextlib.redirect_stderr(self.err):
            self.assertEqual(daily.main([]),1)
        self.assertNotIn('LOCAL_SECRET_CANARY',self.err.getvalue())

    def test_owned_process_kill_is_bounded_if_graceful_termination_times_out(self):
        self.process.wait.side_effect=[subprocess.TimeoutExpired('owned',10),0]
        daily.stop_owned(self.process)
        self.process.kill.assert_called_once()
        self.assertEqual([c.kwargs for c in self.process.wait.call_args_list],[{'timeout':10},{'timeout':5}])


class LoopbackRequestTests(unittest.TestCase):
    def test_post_has_exact_loopback_origin_no_proxy_no_credentials_and_bounded_json(self):
        response=BytesIO(b'{"state":"running"}');response.status=202;response.headers=Message();response.headers['Content-Type']='application/json'
        with patch.object(daily,'build_opener') as factory:
            factory.return_value.open.return_value=response
            self.assertEqual(daily.LoopbackClient().request('/api/refresh',post=True),{'state':'running'})
            handlers=factory.call_args.args
            self.assertEqual(handlers[0].proxies,{})
            request=factory.return_value.open.call_args.args[0]
            self.assertEqual(request.full_url,daily.ORIGIN+'/api/refresh')
            self.assertEqual(request.get_header('Origin'),daily.ORIGIN)
            self.assertEqual(request.get_method(),'POST')
            self.assertNotIn('Authorization',dict(request.header_items()))
            self.assertEqual(factory.return_value.open.call_args.kwargs['timeout'],15)

    def test_only_connection_refusal_can_start_a_server_other_failures_are_closed(self):
        for error,expected in [(URLError(ConnectionRefusedError()),daily.ServerUnavailable),
                               (URLError(TimeoutError()),daily.SnapshotError),
                               (HTTPError(daily.ORIGIN,409,'private-response',{},None),daily.SnapshotError)]:
            with self.subTest(error=type(error).__name__),patch.object(daily,'build_opener') as factory:
                factory.return_value.open.side_effect=error
                with self.assertRaises(expected) as caught:daily.LoopbackClient().request('/api/status')
                self.assertNotIn('private-response',str(caught.exception))

    def test_malformed_wrong_content_oversized_and_unknown_endpoint_fail_closed(self):
        for payload,status,content in [(b'not-json',200,'application/json'),(b'{}',200,'text/html'),(b'{}',503,'application/json')]:
            response=BytesIO(payload);response.status=status;response.headers=Message();response.headers['Content-Type']=content
            with self.subTest(payload=payload),patch.object(daily,'build_opener') as factory:
                factory.return_value.open.return_value=response
                with self.assertRaises(daily.SnapshotError):daily.LoopbackClient().request('/api/status')
        with self.assertRaises(daily.SnapshotError):daily.LoopbackClient().request('/api/orders')
