"""Copy a validated site into a separate pages worktree; never commit or push."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from src.themescope.site_output import replace_site,validate_site


def git(root,*args):
    result=subprocess.run(['git','-C',str(root),*args],capture_output=True,text=True,encoding="utf-8",check=True)
    return result.stdout.strip()


def stage_site(root,target):
    root,target=root.resolve(),target.resolve()
    if target==root:raise ValueError('Use the separate pages worktree, not your download source checkout')
    if Path(git(target,'rev-parse','--show-toplevel')).resolve()!=target:raise ValueError('Destination must be the pages worktree root')
    if git(target,'branch','--show-current')!='pages':raise ValueError('Destination branch must be pages')
    if git(root,'rev-parse','--path-format=absolute','--git-common-dir')!=git(target,'rev-parse','--path-format=absolute','--git-common-dir'):raise ValueError('Destination must be a worktree of this same repository')
    if git(target,'status','--porcelain'):raise ValueError('Pages worktree has uncommitted changes. Commit, back up or resolve them first; nothing was discarded.')
    source=root/'site';manifest=validate_site(source)
    if manifest['kind']!='snapshot':raise ValueError('Prepare a dated snapshot with prepare-site.cmd first')
    with tempfile.TemporaryDirectory(prefix='.themescope-site-',dir=target) as temporary:
        stage=Path(temporary)/'site';stage.mkdir()
        for name in [*manifest['files'],'site_manifest.json']:
            destination=stage/name;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(source/name,destination)
        validate_site(stage);replace_site(stage,target/'site')
    print(f'Staged site files for US session {manifest["session_date"]} in {target}/site. No Git commit or push was made.')


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('worktree',type=Path);args=parser.parse_args()
    destination=args.worktree if args.worktree.is_absolute() else ROOT/args.worktree
    stage_site(ROOT,destination)


if __name__=='__main__':
    try:main()
    except (ValueError,KeyError,OSError,subprocess.CalledProcessError) as error:
        print('SITE STAGING FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
