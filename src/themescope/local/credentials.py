"""Per-user provider credentials protected with Windows DPAPI."""
import ctypes
from ctypes import wintypes
from getpass import getpass, GetPassWarning
import json
import os
from pathlib import Path
import tempfile
import warnings

REQUIRED = ('APCA_API_KEY_ID', 'APCA_API_SECRET_KEY')
OPTIONAL = ('ALPHAVANTAGE_API_KEY',)


def app_data():
    base = os.environ.get('LOCALAPPDATA') if os.name == 'nt' else os.environ.get('XDG_DATA_HOME')
    return (Path(base) if base else Path.home() / '.local/share') / 'ThemeScope'


def atomic_write(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temp = Path(handle.name)
        try:
            handle.write(payload)
            handle.close()
            os.replace(temp, path)
        finally:
            handle.close()
            temp.unlink(missing_ok=True)


class Blob(ctypes.Structure):
    _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def dpapi(payload, protect):
    if os.name != 'nt':
        raise OSError('Windows is required for encrypted credential storage')
    crypt = ctypes.WinDLL('crypt32', use_last_error=True)
    free = ctypes.WinDLL('kernel32').LocalFree
    free.argtypes = (ctypes.c_void_p,)
    free.restype = ctypes.c_void_p
    operation = crypt.CryptProtectData if protect else crypt.CryptUnprotectData
    operation.argtypes = (ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p,
                          ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob))
    operation.restype = wintypes.BOOL
    buffer = ctypes.create_string_buffer(payload)
    source = Blob(len(payload), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = Blob()
    if not operation(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(result)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        ctypes.memset(result.data, 0, result.size)
        free(result.data)


def values():
    credentials = {key: os.environ.get(key) for key in REQUIRED + OPTIONAL}
    if os.name == 'nt' and not all(credentials.values()):
        try:
            payload = (app_data() / 'provider.dpapi').read_bytes()
            stored = json.loads(dpapi(payload, False))
            for key, value in credentials.items():
                if not value and isinstance(stored.get(key), str):
                    credentials[key] = stored[key]
        except (OSError, ValueError, AttributeError, RuntimeError):
            pass
    return credentials


def configure(only_if_missing=False):
    if only_if_missing and all(values().get(key) for key in REQUIRED):
        return
    if os.name != 'nt':
        if only_if_missing:
            return
        raise OSError('Use environment overrides on this platform')
    with warnings.catch_warnings():
        warnings.simplefilter('error', GetPassWarning)
        key = getpass('Alpaca API key ID: ').strip()
        secret = getpass('Alpaca API secret: ').strip()
        earnings = getpass('Alpha Vantage key (optional, Enter to skip): ').strip()
    if not key or not secret:
        raise ValueError('Both Alpaca values are required')
    payload = json.dumps(dict(zip(REQUIRED + OPTIONAL, (key, secret, earnings)))).encode()
    atomic_write(app_data() / 'provider.dpapi', dpapi(payload, True))
    print('Encrypted provider credentials saved for this Windows user.')
