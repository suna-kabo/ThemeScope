"""Publication rollback, interrupted-process recovery and concurrent access."""
import json
import os
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch
from src.themescope.local_publication import output_lock,publish_tree,recover,pending,transaction_dir,digest

ROOT=Path(__file__).resolve().parents[1]

class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='publish space 香港 ');self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.output=self.root/'output';self.output.mkdir();self.stage=self.root/'stage';self.stage.mkdir()
        for name,value in [('dashboard.html','old'),('data.csv','old data'),('stale.txt','retire')]: (self.output/name).write_text(value,encoding='utf-8')
        for name,value in [('dashboard.html','new'),('data.csv','new data'),('extra.txt','new export')]: (self.stage/name).write_text(value,encoding='utf-8')
    def contents(self):return {p.name:p.read_bytes() for p in self.output.iterdir() if p.is_file()}
    def test_success_and_managed_retirement(self):
        with output_lock(self.output):publish_tree(self.stage,self.output,{'stale.txt'})
        self.assertEqual(self.contents(),{'dashboard.html':b'new','data.csv':b'new data','extra.txt':b'new export'})
        self.assertFalse(pending(self.output));self.assertFalse(transaction_dir(self.output).exists())
    def test_failure_after_replacements_restores_every_previous_byte(self):
        before=self.contents();replace=os.replace
        def fail(src,dst):
            if Path(src)==self.stage/'dashboard.html':raise PermissionError('simulated locked HTML')
            return replace(src,dst)
        with output_lock(self.output),patch('src.themescope.local_publication.os.replace',side_effect=fail):
            with self.assertRaisesRegex(PermissionError,'locked'):publish_tree(self.stage,self.output,{'stale.txt'})
        self.assertEqual(self.contents(),before);self.assertFalse(pending(self.output))
    def test_killed_publisher_keeps_durable_backups_and_recovers_after_move(self):
        before=self.contents()
        code='''import os,sys
from pathlib import Path
from src.themescope.local_publication import output_lock,publish_tree
stage,output=map(Path,sys.argv[1:]);replace=os.replace
def kill(src,dst):
 if Path(src)==stage/'dashboard.html':os._exit(29)
 return replace(src,dst)
os.replace=kill
with output_lock(output):publish_tree(stage,output,{'stale.txt'})
'''
        result=subprocess.run([sys.executable,'-c',code,str(self.stage),str(self.output)],cwd=ROOT)
        self.assertEqual(result.returncode,29);self.assertTrue(pending(self.output));self.assertNotEqual(self.contents(),before)
        moved=self.root/'moved copy 香港';moved.mkdir()
        journal=transaction_dir(self.output);shutil.move(str(self.output),str(moved/'output'));shutil.move(str(journal),str(moved/journal.name));self.output=moved/'output'
        with output_lock(self.output):self.assertTrue(recover(self.output))
        self.assertEqual(self.contents(),before);self.assertFalse(pending(self.output))
    def test_final_validation_failure_restores_previous_release(self):
        before=self.contents()
        with output_lock(self.output):
            with self.assertRaisesRegex(ValueError,'final validation'):
                publish_tree(self.stage,self.output,validate=lambda path:(_ for _ in ()).throw(ValueError('final validation failed')))
        self.assertEqual(self.contents(),before);self.assertFalse(pending(self.output))
    def test_other_process_cannot_publish_under_existing_lock(self):
        code="from src.themescope.local_publication import output_lock; import sys\nwith output_lock(sys.argv[1]): pass"
        with output_lock(self.output):result=subprocess.run([sys.executable,'-c',code,str(self.output)],cwd=ROOT,capture_output=True,text=True)
        self.assertNotEqual(result.returncode,0);self.assertIn('Another refresh/preparation',result.stderr)
    @unittest.skipUnless(os.name=='nt','Windows open-file replacement semantics')
    def test_actual_windows_open_output_file_fails_and_preserves_bytes(self):
        before=self.contents()
        with (self.output/'dashboard.html').open('rb'),output_lock(self.output):
            with self.assertRaises(PermissionError):publish_tree(self.stage,self.output,{'stale.txt'})
        self.assertEqual(self.contents(),before);self.assertFalse(pending(self.output))
    def test_unknown_or_tampered_recovery_is_not_guessed(self):
        folder=transaction_dir(self.output);folder.mkdir();(folder/'journal.json').write_text('{}')
        with self.assertRaisesRegex(ValueError,'Unrecognized'):recover(self.output)
        self.assertTrue(pending(self.output));self.assertTrue(folder.exists())

    def test_post_commit_backup_cleanup_failure_is_not_a_failed_publication(self):
        with output_lock(self.output),patch('src.themescope.local_publication.shutil.rmtree',side_effect=PermissionError('backup held open')):
            publish_tree(self.stage,self.output,{'stale.txt'})
        self.assertEqual(self.contents(),{'dashboard.html':b'new','data.csv':b'new data','extra.txt':b'new export'})
        self.assertFalse(pending(self.output));self.assertTrue(transaction_dir(self.output).exists())
        with output_lock(self.output):self.assertFalse(recover(self.output))
        self.assertFalse(transaction_dir(self.output).exists())

if __name__=='__main__':unittest.main()
