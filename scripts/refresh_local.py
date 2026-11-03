"""Explicit five-file daily refresh. Never selects the newest file or pushes Git."""
import argparse
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
STEMS={'stock':'Daily_Stock','etf':'Daily_ETF','spy':'SPY','qqq':'QQQ','iwm':'IWM'}


def input_paths(root, session, folder=None, now=None):
    try:day=date.fromisoformat(session)
    except ValueError:raise ValueError('Use the US session in YYYY-MM-DD form, for example 2026-11-02.') from None
    if day.isoformat()!=session:raise ValueError('Session must use YYYY-MM-DD form.')
    calendar=json.loads((root/'config/calendars/xnys_2020_2035_v1.json').read_text(encoding='utf-8'))['sessions']
    record=next((r for r in calendar if r['session']==session),None)
    if not record:raise ValueError(f'{session} is not a configured US trading session (weekend/holiday or outside calendar range).')
    if datetime.fromisoformat(record['close']) > (now or datetime.now(timezone.utc)):
        raise ValueError(f'{session} has not closed yet. Export after the US close; no future session will be labeled current.')
    folder=Path(folder) if folder else Path('inputs')/session
    if not folder.is_absolute():folder=root/folder
    folder=folder.resolve()
    if not folder.is_dir():raise ValueError(f'Input folder is missing: {folder}. Create it and place all five CSVs there.')
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}',folder.name) and folder.name!=session:
        raise ValueError('The dated input folder must match the declared US session, even if the filenames use the following Hong Kong date.')
    result={}
    for role,stem in STEMS.items():
        pattern=re.compile(re.escape(stem)+r'(?:_(\d{4}-\d{2}-\d{2}))?(?: \(\d+\))?\.csv',re.I)
        candidates=[p for p in folder.iterdir() if p.is_file() and pattern.fullmatch(p.name)]
        if len(candidates)!=1:
            raise ValueError(f'{role}: expected exactly one {stem}.csv or {stem}_YYYY-MM-DD.csv in {folder}; found {len(candidates)}. Remove duplicate exports or provide the missing file.')
        file=candidates[0];stamp=pattern.fullmatch(file.name).group(1)
        if stamp and stamp not in {session,(day+timedelta(days=1)).isoformat()}:
            raise ValueError(f'{role}: filename date {stamp} disagrees with US session {session} and its next-day Hong Kong export date.')
        result[role]=file
    previous=root/'output/manual_csv/latest_snapshot.json'
    if previous.exists():
        saved=json.loads(previous.read_text(encoding='utf-8'))
        if saved['session_date']!=session:
            old=saved.get('manual_csv_audit',{}).get('inputs',{})
            reused=[role for role,p in result.items() if hashlib.sha256(p.read_bytes()).hexdigest()==old.get(role,{}).get('sha256')]
            if reused:raise ValueError('Inputs identical to the previous successful session: '+', '.join(reused)+'. Export fresh CSVs; old files were not reused.')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',help='Declared completed US session, YYYY-MM-DD; never inferred from filenames')
    parser.add_argument('--input-dir',help='Defaults to inputs/SESSION; relative paths are based on the repository, not the shell')
    args=parser.parse_args()
    session=args.session
    if not session:
        if not sys.stdin.isatty():parser.error('--session is required when not running interactively')
        session=input('US session date you exported (YYYY-MM-DD; HK filenames may be the next day): ').strip()
    paths=input_paths(ROOT,session,args.input_dir)
    print(f'Declared US session: {session}. CSV rows have no reliable session timestamp: confirm you exported after that close.',flush=True)
    command=[sys.executable,str(ROOT/'scripts/generate_dashboard.py'),'--source','tradingview-csv','--as-of',session,'--output-dir',str(ROOT/'output/manual_csv')]
    for role,path in paths.items():command+=['--'+role+'-csv',str(path)]
    result=subprocess.run(command,cwd=ROOT)
    if result.returncode:return result.returncode
    print('Refresh complete. Run open-dashboard.cmd and check Data through before using the dashboard.')
    print('site/ was not changed. Nothing was committed, pushed or deployed.')
    return 0


if __name__=='__main__':
    try:raise SystemExit(main())
    except (ValueError,KeyError,OSError,EOFError) as error:
        print('REFRESH FAILED: '+str(error)+'\nPrevious successful outputs/history were not replaced.',file=sys.stderr);raise SystemExit(1)
