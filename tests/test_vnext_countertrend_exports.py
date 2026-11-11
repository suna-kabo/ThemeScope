"""Additive exports consume published bucket sets; Directional stays untouched."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import tempfile,unittest
from src.themescope.research.countertrend_exports import exports,attach,public_exports

ROOT=Path(__file__).resolve().parents[1]


def fixture(side='short'):
    buckets={
        'resilient':{'rows':[{'ticker':'B','theme_id':'two'},{'ticker':'A','theme_id':'one'},{'ticker':'B','theme_id':'one'}]},
        'snapback':{'rows':[{'ticker':'C','theme_id':'two'},{'ticker':'A','theme_id':'two'}]},
    }
    return {'exports':{'combined':'NYSE:D\n','assignments':{'D':{'assigned_section':'one'}}},
        'research':{'countertrend':{'available':True,'side':side,'buckets':buckets}},
        'relationships':[r for bucket in buckets.values() for r in bucket['rows']]}


def mapping():return {s:{'status':'verified','symbol':'TEST:'+s} for s in ('A','B','C')}


class CountertrendExportsTests(unittest.TestCase):
    def test_short_combined_dedup_and_buckets_preserve_supplied_order(self):
        result=exports(fixture(),mapping())
        self.assertEqual(result['files'],{'Countertrend.txt':'TEST:A\nTEST:B\nTEST:C\n',
            'Resilient.txt':'TEST:B\nTEST:A\n','Snapback.txt':'TEST:C\nTEST:A\n'})
        self.assertEqual(len(result['files']['Countertrend.txt'].splitlines()),3)
        self.assertNotIn('NYSE:D',result['files']['Countertrend.txt'])

    def test_long_filenames_keep_identical_membership_and_directional_unchanged(self):
        data=fixture('long');old=deepcopy(data);result=attach(data,mapping())
        self.assertEqual(set(result['research']['countertrend']['exports']['files']),{'Countertrend.txt','Strong-Leaders.txt','Relative-Weakness.txt'})
        self.assertEqual(result['exports'],old['exports']);self.assertEqual(data,old)
        self.assertNotIn('Resilient.txt',result['research']['countertrend']['exports']['files'])

    def test_deterministic_combined_and_repeatable_bucket_order(self):
        original=fixture();changed=deepcopy(original)
        changed['relationships'].reverse()
        self.assertEqual(exports(original,mapping()),exports(changed,dict(reversed(list(mapping().items())))))
        changed['research']['countertrend']['buckets']['resilient']['rows'].reverse()
        self.assertEqual(exports(original,mapping())['files']['Countertrend.txt'],exports(changed,mapping())['files']['Countertrend.txt'])

    def test_unresolved_unverified_invalid_or_colliding_identifiers_fail_closed(self):
        for bad in ({},dict(mapping(),A={'status':'proposed','symbol':'TEST:A'}),
                    dict(mapping(),A={'status':'verified','symbol':'A'}),
                    dict(mapping(),A={'status':'verified','symbol':'TEST:A\nTEST:BAD'}),
                    dict(mapping(),A={'status':'verified','symbol':'TEST:B'})):
            with self.subTest(mapping=bad),self.assertRaises(ValueError):exports(fixture(),bad)

    def test_dotted_symbols_kept_without_exchange_inference(self):
        data=fixture();data['relationships'][0]={'ticker':'BRK.B','theme_id':'two'}
        data['research']['countertrend']['buckets']['resilient']['rows'][0]=data['relationships'][0]
        result=exports(data,dict(mapping(),**{'BRK.B':{'status':'verified','symbol':'NYSE:BRK.B'}}))
        self.assertIn('NYSE:BRK.B\n',result['files']['Countertrend.txt'])

    def test_unavailable_or_empty_lens_never_invents_downloads(self):
        for side,available in ((None,False),('short',False),('unknown',True)):
            data=fixture(side);data['research']['countertrend']['available']=available
            self.assertEqual(exports(data,{})['files'],{})
        data=fixture()
        for bucket in data['research']['countertrend']['buckets'].values():bucket['rows']=[]
        self.assertFalse(exports(data,{})['available'])

    def test_unknown_relationship_rejected_not_silently_removed(self):
        data=fixture();data['relationships']=data['relationships'][1:]
        with self.assertRaisesRegex(ValueError,'relationship unavailable'):exports(data,mapping())

    def test_public_projection_strips_internal_lookup_and_checks_exact_sets(self):
        ct=attach(fixture(),mapping())['research']['countertrend'];expected=ct['exports']
        public=public_exports(ct)
        self.assertEqual(public['files'],expected['files']);self.assertNotIn('symbols',public)
        for mutation in ('extra','missing','changed','wrong_side','invalid','duplicate'):
            changed=deepcopy(ct);value=changed['exports']
            if mutation=='extra':value['files']['Other.txt']='TEST:A\n'
            if mutation=='missing':del value['files']['Resilient.txt']
            if mutation=='changed':value['files']['Snapback.txt']='TEST:B\n'
            if mutation=='wrong_side':value['side']='long'
            if mutation=='invalid':value['symbols']['A']='A'
            if mutation=='duplicate':value['symbols']['A']='TEST:B'
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):public_exports(changed)
        del ct['exports'];self.assertIsNone(public_exports(ct))

    def test_http_reads_one_snapshot_and_has_fixed_download_names(self):
        from fastapi.testclient import TestClient
        from src.themescope.local.app import create_app
        class Service:
            def __init__(self):self.current=attach(fixture(),mapping());self.reads=0
            def snapshot(self):self.reads+=1;return deepcopy(self.current)
        service=Service();client=TestClient(create_app(ROOT,service),base_url='http://127.0.0.1')
        for filename,text in service.current['research']['countertrend']['exports']['files'].items():
            before=service.reads;response=client.get('/api/exports/countertrend/'+filename)
            self.assertEqual(response.status_code,200);self.assertEqual(response.text,text)
            self.assertEqual(response.headers['content-disposition'],f'attachment; filename="{filename}"')
            self.assertEqual(service.reads,before+1)
        self.assertEqual(client.get('/api/exports/countertrend/Strong-Leaders.txt').status_code,404)
        self.assertEqual(client.get('/api/exports/combined.txt').text,'NYSE:D\n')
        service.current['research']['countertrend']['exports']['available']=False
        self.assertEqual(client.get('/api/exports/countertrend/Countertrend.txt').status_code,404)

    def test_real_service_mapping_failure_keeps_previous_publication(self):
        from vnext_prelaunch_fixture import PrelaunchFixture
        from src.themescope.research.exports import reviewed_mapping
        with tempfile.TemporaryDirectory() as folder,patch('src.themescope.local.service.optional_earnings',return_value={}):
            f=PrelaunchFixture(folder);first=f.service.refresh();self.assertIsNotNone(first,f.service.status())
            before=f.service.snapshot()
            exported=before['research']['countertrend']['exports']['symbols']
            ticker=next(s for s in exported if s not in before['exports']['assignments'])
            def missing(config,source):
                value=reviewed_mapping(config,source);value.pop(ticker,None);return value
            with patch('src.themescope.local.service.reviewed_mapping',side_effect=missing):
                self.assertIsNone(f.service.refresh())
            self.assertEqual(f.service.snapshot(),before)
            self.assertEqual(f.service.status()['state'],'failed')
