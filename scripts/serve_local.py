"""Loopback-only static file preview; no API or collection service."""
import argparse
import functools
import http.server
from pathlib import Path
import sys
import webbrowser

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--site',action='store_true');parser.add_argument('--port',type=int,default=8000);parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    directory=ROOT/'site' if args.site else ROOT/'output/manual_csv'
    entry='index.html' if args.site else 'dashboard.html'
    if not (directory/entry).is_file():raise ValueError('No '+entry+' in '+str(directory)+'. Run prepare-site.cmd first.' if args.site else 'No dashboard yet. Run refresh.cmd with your five CSVs first.')
    handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(directory))
    with http.server.ThreadingHTTPServer(('127.0.0.1',args.port),handler) as server:
        url=f'http://127.0.0.1:{server.server_port}/{entry}'
        print(url+'\nThis serves only the selected output folder on your own PC. Leave this window open. Ctrl+C stops it.',flush=True)
        if not args.no_browser:webbrowser.open(url)
        try:server.serve_forever()
        except KeyboardInterrupt:pass
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (OSError,ValueError) as error:
        print('PREVIEW FAILED: '+str(error)+'\nIf port 8000 is busy, use --port 8001.',file=sys.stderr);raise SystemExit(1)
