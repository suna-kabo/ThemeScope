"""Nonblocking OS-held refresh lock, shared across threads/processes and imports.

The OS releases it on process death. The persistent lock file is never unlinked:
unlinking would allow two processes to lock different inodes at the same path.
"""
from pathlib import Path
import os

class RefreshBusy(RuntimeError):pass

class RefreshLock:
    def __init__(self,path):self.path=Path(path);self.handle=None
    def __enter__(self):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        self.handle=os.fdopen(os.open(self.path,os.O_RDWR|os.O_CREAT,0o600),'r+b')
        try:
            if os.name=='nt':
                import msvcrt
                if os.fstat(self.handle.fileno()).st_size==0:
                    self.handle.seek(0);self.handle.write(b'0');self.handle.flush()
                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.handle.close();self.handle=None
            raise RefreshBusy('A refresh or roster update is already active') from None
        return self
    def __exit__(self,*args):
        if self.handle:
            if os.name=='nt':
                import msvcrt
                self.handle.seek(0);msvcrt.locking(self.handle.fileno(),msvcrt.LK_UNLCK,1)
            else:
                import fcntl
                fcntl.flock(self.handle.fileno(),fcntl.LOCK_UN)
            self.handle.close();self.handle=None
