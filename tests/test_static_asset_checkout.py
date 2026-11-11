"""Hash-pinned assets survive fresh Unix/Windows-style Git checkouts."""
from pathlib import Path
from unittest.mock import patch
from hashlib import sha256
import shutil,subprocess,tempfile,unittest
from scripts.static_pages import ASSETS,FONT_HASHES,font_assets
from scripts import build_public_snapshot as public
from public_snapshot_support import public_contract_fixture

ROOT=Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('git'),'Git is needed to simulate checkout normalization')
class StaticAssetCheckoutTests(unittest.TestCase):
    def git(self,*args,cwd):
        return subprocess.check_output(['git',*args],cwd=cwd,stderr=subprocess.PIPE).decode().strip()

    def test_pinned_bytes_and_explicit_checkout_attributes(self):
        self.assertNotIn(b'\r',(ROOT/'static/Inter-LICENSE.txt').read_bytes())
        self.assertEqual({name:sha256(value).hexdigest() for name,value in font_assets(ROOT).items()},FONT_HASHES)
        attrs=self.git('check-attr','text','eol','--','static/Inter-LICENSE.txt','static/InterVariable.woff2',cwd=ROOT)
        self.assertIn('static/Inter-LICENSE.txt: eol: lf',attrs)
        self.assertIn('static/InterVariable.woff2: text: unset',attrs)

    def test_fresh_autocrlf_checkouts_build_without_bypassing_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/'source';(source/'static/vnext').mkdir(parents=True)
            shutil.copyfile(ROOT/'.gitattributes',source/'.gitattributes')
            (source/'.gitignore').write_text('dist/\nruntime/\n')
            for name in FONT_HASHES:shutil.copyfile(ROOT/'static'/name,source/'static'/name)
            for name in ASSETS:shutil.copyfile(ROOT/'static/vnext'/name,source/'static/vnext'/name)
            self.git('init','-q',cwd=source)
            self.git('-c','core.autocrlf=false','add','.',cwd=source)
            self.git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Asset checkout fixture',cwd=source)
            built=[]
            for autocrlf,eol in [('true','crlf'),('false','lf')]:
                with self.subTest(autocrlf=autocrlf,eol=eol):
                    target=Path(folder)/autocrlf
                    self.git('clone','-q','--no-hardlinks','--config','core.autocrlf='+autocrlf,'--config','core.eol='+eol,str(source),str(target),cwd=source)
                    self.assertEqual(self.git('status','--porcelain',cwd=target),'')
                    self.assertEqual(font_assets(target),font_assets(ROOT))
                    with patch.object(public,'fetch_snapshot',return_value=public_contract_fixture()),patch('builtins.print'):
                        output=public.build('2026-11-06',target)
                    built.append({p.name:p.read_bytes() for p in output.iterdir()})
                    for name,expected in FONT_HASHES.items():self.assertEqual(sha256((output/name).read_bytes()).hexdigest(),expected)
                    self.assertEqual(self.git('status','--porcelain',cwd=target),'')
            self.assertEqual(built[0],built[1],'Public output differs across fresh checkout EOL settings')
