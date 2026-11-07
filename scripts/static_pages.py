"""Shared static presentation assets only; no financial or provider imports."""
import struct
import zlib

ASSETS = ('index.html', 'app.css', 'app.js')
HEADERS = """/*
  Content-Security-Policy: default-src 'self'; connect-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'
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
