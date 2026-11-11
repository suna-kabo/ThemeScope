"""Local vNext application; fixture mode uses an isolated synthetic DB."""
from pathlib import Path
import argparse,sys,threading,webbrowser
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixture',action='store_true');parser.add_argument('--port',type=int,default=8766)
    parser.add_argument('--no-browser',action='store_true');args=parser.parse_args()
    from src.themescope.local.app import create_app
    from src.themescope.local.service import fixture_service,RefreshService
    import uvicorn
    service=fixture_service(ROOT) if args.fixture else RefreshService(ROOT)
    app=create_app(ROOT,service)
    if not args.no_browser:threading.Timer(1,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    uvicorn.run(app,host='127.0.0.1',port=args.port,access_log=False)
if __name__=='__main__':main()
