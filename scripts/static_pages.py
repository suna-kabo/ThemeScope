"""Shared static presentation assets only; no financial or provider imports."""
from hashlib import sha256
from pathlib import Path
import struct
import zlib

ASSETS = ('index.html', 'app.css', 'workspace.js', 'app.js')
# Existing bundled Inter (SIL OFL 1.1), pinned so public builds cannot ship
# arbitrary binary payloads. No remote font fetch or new repository binary.
FONT_HASHES = {
    'InterVariable.woff2':'693b77d4f32ee9b8bfc995589b5fad5e99adf2832738661f5402f9978429a8e3',
    'Inter-LICENSE.txt':'262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a',
}


def validate_font(name, data):
    if name not in FONT_HASHES or sha256(data).hexdigest()!=FONT_HASHES[name]:
        raise ValueError('Unexpected bundled font/license payload')
    return data


def font_assets(root):
    result={}
    for name in FONT_HASHES:
        path=Path(root)/'static'/name
        if path.is_symlink():raise ValueError('Font assets cannot be symlinks')
        result[name]=validate_font(name,path.read_bytes())
    return result


def copy_fonts(source_root, target_static):
    target_static=Path(target_static);target_static.mkdir(parents=True,exist_ok=True)
    for name,data in font_assets(source_root).items():(target_static/name).write_bytes(data)

HEADERS = """/*
  Content-Security-Policy: default-src 'self'; connect-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
  X-Content-Type-Options: nosniff
  Referrer-Policy: no-referrer
  Permissions-Policy: camera=(), microphone=(), geolocation=()
"""


def favicon():
    """Original local 16px crescent; generated PNG-in-ICO, no third-party asset."""
    rows = bytearray()
    for y in range(16):
        rows.append(0)
        for x in range(16):
            lit = (x-7.5)**2+(y-7.5)**2<=49 and (x-10)**2+(y-5)**2>36
            rows.extend((206,187,255,255) if lit else (0,0,0,0))
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    png = b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',16,16,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(rows),9))+chunk(b'IEND',b'')
    return struct.pack('<HHH',0,1,1)+struct.pack('<BBBBHHII',16,16,0,0,1,32,len(png),22)+png
