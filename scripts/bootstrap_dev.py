"""Install the local vNext runtime into an isolated project environment."""
from pathlib import Path
import os
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 12):
        raise SystemExit('Python 3.12 or newer is required.')
    folder = ROOT / '.venv-vnext'
    python = folder / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not folder.exists():
        venv.EnvBuilder(with_pip=True).create(folder)
    if not python.is_file():
        raise SystemExit('Existing .venv-vnext is incomplete. Preserve it and repair explicitly.')
    subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(ROOT / 'requirements-vnext.txt')], check=True)
    subprocess.run([str(python), '-c', 'import fastapi,uvicorn,httpx; from zoneinfo import ZoneInfo; ZoneInfo("America/New_York")'], check=True)
    print('vNext runtime ready. Production membership remains gated; no data fetched.')


if __name__ == '__main__':
    main()
