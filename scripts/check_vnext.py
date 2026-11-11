"""Offline configuration and regression checks; never fetches provider data."""
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.themescope.domain import load_configuration


def main():
    config = load_configuration(ROOT)
    result = subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT)
    print(json.dumps({'methodology': config.methodology['version'],
                      'provisional_configuration_valid': True,
                      'production_blockers': config.production_blockers()}, indent=2))
    return result.returncode


if __name__ == '__main__':
    raise SystemExit(main())
