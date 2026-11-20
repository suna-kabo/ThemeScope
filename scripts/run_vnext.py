"""Launch the private loopback application or reopen the same running workspace."""
import argparse
from http.client import HTTPConnection, HTTPException
import json
from pathlib import Path
import socket
import sys
import threading
import time
import webbrowser

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def request_local(port, path, method='GET'):
    connection = HTTPConnection('127.0.0.1', port, timeout=1)
    try:
        connection.request(method, path, headers={'Origin': f'http://127.0.0.1:{port}'})
        response = connection.getresponse()
        if response.status == 200:
            return json.loads(response.read(8192))
    except (OSError, HTTPException, ValueError):
        return None
    finally:
        connection.close()


def open_dashboard(port, expected, no_browser, *, reused=False, attempts=30):
    for _ in range(attempts):
        if request_local(port, '/api/local') == expected:
            if reused:
                request_local(port, '/api/local/startup', 'POST')
            url = f'http://127.0.0.1:{port}'
            print(f'ThemeScope is ready at {url}', flush=True)
            if not no_browser:
                try:
                    if not webbrowser.open(url):
                        print(f'Open {url} in your browser.', flush=True)
                except (webbrowser.Error, OSError):
                    print(f'Open {url} in your browser.', flush=True)
            return True
        time.sleep(0.1)
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture', action='store_true')
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')
    from src.themescope.local.app import create_app, local_identity
    from src.themescope.local.service import fixture_service, RefreshService
    import uvicorn

    expected = local_identity(ROOT, 'fixture' if args.fixture else 'live')
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        try:
            listener.bind(('127.0.0.1', args.port))
        except OSError:
            if open_dashboard(args.port, expected, args.no_browser, reused=True, attempts=12):
                return 0
            print(f'Port {args.port} is unavailable or belongs to another application or ThemeScope version. '
                  'Close its console if you recognize it, or launch with --port and an unused port.', file=sys.stderr)
            return 1
        service = fixture_service(ROOT) if args.fixture else RefreshService(ROOT)
        app = create_app(ROOT, service, automatic=not args.fixture)
        config = uvicorn.Config(app, host='127.0.0.1', port=args.port, access_log=False, proxy_headers=False)
        threading.Thread(target=open_dashboard, args=(args.port, expected, args.no_browser), daemon=True).start()
        uvicorn.Server(config).run(sockets=[listener])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
