"""Pages staging is a local, locked transaction; no commit/push/deploy occurs."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.stage_site import stage_site
from src.themescope.local_publication import output_lock
from src.themescope.site_output import prepare_site,validate_site
import test_site_output as boundary_tests
ROOT=boundary_tests.ROOT


class SiteStagingTests(unittest.TestCase):
    def setUp(self):
        self.fixture=boundary_tests.SiteBoundaryTests();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.source=self.fixture.base/'source';self.source.mkdir();self.pages=self.fixture.base/'pages'
        self.git(self.source,'init','-q','-b','source')
        (self.source/'.gitignore').write_text('/site/\n/.site-publication.lock\n/.site-publication/\n/.themescope-site-*/\n')
        self.git(self.source,'add','.gitignore')
        self.git(self.source,'-c','user.name=Test','-c','user.email=test@example.invalid','commit','-qm','source fixture')
        self.git(self.source,'worktree','add','-q','-b','pages',str(self.pages))
        prepare_site(ROOT,self.fixture.source,self.source/'site','2026-11-02')

    def git(self,root,*args):return subprocess.check_output(['git','-C',str(root),*args],text=True,encoding='utf-8').strip()
    def hashes(self,root):return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}

    def test_same_repo_pages_staging_preserves_exact_site_and_creates_no_commit(self):
        previous=self.git(self.pages,'rev-parse','HEAD');stage_site(self.source,self.pages)
        self.assertEqual(self.hashes(self.pages/'site'),self.hashes(self.source/'site'))
        self.assertEqual(self.git(self.pages,'rev-parse','HEAD'),previous)
        validate_site(self.pages/'site')
        # No Git push/commit, and a retained lock does not break the next staging.
        stage_site(self.source,self.pages)

    def test_dirty_worktree_is_not_discarded(self):
        (self.pages/'personal.txt').write_text('preserve')
        with self.assertRaisesRegex(ValueError,'uncommitted'):stage_site(self.source,self.pages)
        self.assertEqual((self.pages/'personal.txt').read_text(),'preserve')
        self.assertFalse((self.pages/'site').exists())

    def test_concurrent_source_or_target_writer_blocks_staging(self):
        real=output_lock
        for folder in (self.source/'site',self.pages/'site'):
            with real(folder),patch('scripts.stage_site.output_lock',side_effect=lambda path,timeout:real(path,timeout=0)):
                with self.assertRaisesRegex(ValueError,'Another refresh'):stage_site(self.source,self.pages)
        self.assertFalse((self.pages/'site').exists())

    def test_copy_failure_preserves_the_previous_site(self):
        stage_site(self.source,self.pages);before=self.hashes(self.pages/'site')
        with patch('scripts.stage_site.shutil.copyfile',side_effect=OSError('simulated copy failure')):
            with self.assertRaisesRegex(OSError,'copy failure'):stage_site(self.source,self.pages)
        self.assertEqual(self.hashes(self.pages/'site'),before)


if __name__=='__main__':unittest.main()
