"""Create a repository-local runtime; no system/global configuration changes."""
from pathlib import Path
import os
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.version_info < (3, 12):
        raise ValueError('Python 3.12 or newer is required. Install Python 3.12, reopen PowerShell, and run setup.cmd.')
    environment = ROOT / '.venv'
    python = environment / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not environment.exists():
        print('Creating .venv in the ThemeScope folder...', flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    if not python.is_file():
        raise ValueError('Existing .venv is incomplete. Rename it as a backup, then run setup again; it was not deleted.')
    check = subprocess.run([str(python), '-c', 'import sys; assert sys.version_info >= (3,12); print(sys.executable)'], cwd=ROOT)
    if check.returncode:
        raise ValueError('Existing .venv uses an unsupported Python. Rename it as a backup and rerun setup.')
    installed = subprocess.run([str(python), '-c', 'from importlib.metadata import version; assert version("tzdata")=="2026.5"'], capture_output=True)
    if installed.returncode:
        subprocess.run([str(python), '-m', 'pip', 'install', '--disable-pip-version-check', '--only-binary=:all:', '--require-hashes', '-r', str(ROOT / 'requirements.txt')], cwd=ROOT, check=True)
    # Force the package fallback used by Windows, rather than relying on Linux tzfiles.
    subprocess.run([str(python), '-c', 'import zoneinfo; zoneinfo.reset_tzpath(()); zoneinfo.ZoneInfo.clear_cache(); zoneinfo.ZoneInfo("America/New_York"); zoneinfo.ZoneInfo("Asia/Hong_Kong"); import src.themescope.manual_csv; import scripts.generate_dashboard; print("Runtime imports and timezone package: OK")'], cwd=ROOT, check=True)
    subprocess.run([str(python), str(ROOT / 'scripts/export_collection_lists.py')], cwd=ROOT, check=True)
    print('Setup complete. No CSVs were collected and no dashboard was refreshed or published.')
    print('Put the five CSVs into inputs/US-SESSION-DATE, then run refresh.cmd.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print('SETUP FAILED: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
