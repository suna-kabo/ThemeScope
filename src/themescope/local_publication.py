"""Durable local file publication, shared by refresh and site preparation.

The journal and backups live beside (never inside) the served directory. Readers
refuse pending transactions. Recovery is explicit/under a process lock; no PID
is killed, no input/history directory is swept, and no trading rules live here.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import shutil
import time


def transaction_dir(destination):
    destination=Path(destination).resolve()
    return destination.parent/('.'+destination.name+'-publication')


def pending(destination):
    journal=transaction_dir(destination)/'journal.json'
    if not journal.exists():return False
    try:return json.loads(journal.read_text(encoding='utf-8')).get('state')!='committed'
    except (ValueError,OSError):return True


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def relative(name):
    path=PurePosixPath(name)
    if not name or '\\' in name or path.is_absolute() or '..' in path.parts or str(path)!=name:raise ValueError('Unsafe publication path: '+name)
    return Path(*path.parts)


def target_path(destination,name):
    path=Path(destination)/relative(name)
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):raise ValueError('Publication paths must not be symlinks')
    return path


@contextmanager
def output_lock(destination,timeout=0):
    destination=Path(destination).resolve();destination.parent.mkdir(parents=True,exist_ok=True)
    lock=destination.parent/('.'+destination.name+'-publication.lock')
    with lock.open('a+b') as handle:
        handle.seek(0,2)
        if not handle.tell():handle.write(b'0');handle.flush()
        handle.seek(0)
        deadline=time.monotonic()+timeout
        while True:
            try:
                handle.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except OSError as error:
                if time.monotonic()>=deadline:raise ValueError('Another refresh/preparation/preview is using '+str(destination)+'. Wait for its console to finish; no process was stopped.') from error
                time.sleep(.02)
        try:yield
        finally:
            handle.seek(0)
            if os.name=='nt':msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
            else:fcntl.flock(handle.fileno(),fcntl.LOCK_UN)


def write_journal(folder,value):
    path=folder/'journal.tmp'
    with path.open('w',encoding='utf-8',newline='\n') as handle:
        json.dump(value,handle,ensure_ascii=False);handle.flush();os.fsync(handle.fileno())
    os.replace(path,folder/'journal.json')


def recover(destination):
    """Call while holding output_lock. Keep backups if restoration is blocked."""
    destination=Path(destination).resolve();folder=transaction_dir(destination);journal=folder/'journal.json'
    if folder.is_symlink():raise ValueError('Recovery directory must not be a symlink')
    if not journal.exists():
        if folder.exists():shutil.rmtree(folder) # Unpublished backup preparation only.
        return False
    value=json.loads(journal.read_text(encoding='utf-8'))
    if value.get('schema')!='themescope-publication-1' or Path(value.get('destination','')).name!=destination.name:raise ValueError('Unrecognized publication recovery journal: '+str(journal))
    if value['state']!='committed':
        for action in reversed(value['actions']):
            target=target_path(destination,action['file'])
            if action['previous_sha256'] is not None:
                backup=target_path(folder/'previous',action['file'])
                if not backup.is_file() or digest(backup)!=action['previous_sha256']:raise ValueError('Recovery backup missing/changed: '+str(backup))
                if target.is_file() and digest(target)==action['previous_sha256']:continue
                target.parent.mkdir(parents=True,exist_ok=True)
                temporary=target.with_name('.'+target.name+'.restore.tmp')
                shutil.copy2(backup,temporary)
                try:os.replace(temporary,target)
                finally:temporary.unlink(missing_ok=True)
            else:target.unlink(missing_ok=True)
    shutil.rmtree(folder)
    return value['state']!='committed'


def validate_published_files(destination):
    """Validate a sealed dashboard source before preparing another artifact."""
    destination=Path(destination);path=destination/'publication_manifest.json'
    if not path.exists():return # Backward-compatible pre-update successful output.
    value=json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema')!='themescope-local-publication-1':raise ValueError('Unknown dashboard publication manifest')
    for name,sha in value['files'].items():
        if digest(target_path(destination,name))!=sha:raise ValueError('Saved output differs from its successful publication: '+name+'. Recover or refresh before preparing site.')


def publish_tree(stage,destination,obsolete=(),validate=None):
    """Caller holds output_lock; all backups exist before the first replacement."""
    stage,destination=Path(stage),Path(destination).resolve();recover(destination)
    files={p.relative_to(stage).as_posix():p for p in stage.rglob('*') if p.is_file()}
    expected={name:digest(path) for name,path in files.items()}
    names=sorted(set(files)|set(obsolete),key=lambda name:(Path(name).name in {'dashboard.html','index.html'},name))
    folder=transaction_dir(destination);folder.mkdir(parents=True,exist_ok=False);actions=[]
    try:
        for name in names:
            target=target_path(destination,name);previous=None
            if target.exists():
                if not target.is_file():raise ValueError('Output path is not a file: '+str(target))
                backup=folder/'previous'/relative(name);backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup);previous=digest(backup)
            actions.append({'file':name,'previous_sha256':previous})
        value={'schema':'themescope-publication-1','destination':str(destination),'state':'pending','actions':actions}
        write_journal(folder,value)
        for action in actions:
            name=action['file'];target=target_path(destination,name)
            if name in files:
                target.parent.mkdir(parents=True,exist_ok=True);os.replace(files[name],target)
            else:target.unlink(missing_ok=True)
        for name,sha in expected.items():
            if digest(target_path(destination,name))!=sha:raise ValueError('Published file verification failed: '+name)
        if validate:validate(destination)
        value['state']='committed';write_journal(folder,value)
    except BaseException:
        try:recover(destination)
        except (OSError,ValueError) as error:
            raise OSError('Publication interrupted; preview is blocked until recovery succeeds. Close files open in Excel/editors, then run refresh.cmd --recover (and prepare-site.cmd --recover for site). Backups retained at '+str(folder)) from error
        raise
    recover(destination) # Remove committed backups. A killed process can do this later.
