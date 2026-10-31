import sys,json,tempfile,time,copy,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from scripts.generate_dashboard import _run_manual_csv
from src.themescope.local_history import record
import argparse
parser=argparse.ArgumentParser(description='Real publication regression; synthetic history stays in temporary storage.')
parser.add_argument('snapshot',type=Path)
source=parser.parse_args().snapshot
saved=json.loads(source.read_text())
sessions=[r['session'] for r in json.loads((root/'config/calendars/xnys_2020_2035_v1.json').read_text())['sessions']]
prior_date=sessions[sessions.index(saved['session_date'])-1]
args=SimpleNamespace(as_of=saved['session_date'],**{role+'_csv':Path(a['path']) for role,a in saved['manual_csv_audit']['inputs'].items()})
with tempfile.TemporaryDirectory() as temp:
 output=Path(temp)/'run'
 assert _run_manual_csv(args,output,time.perf_counter())==0
 first=json.loads((output/'latest_snapshot.json').read_text())
 assert all(t['rank_change_daily'] is None for t in first['themes'])
 # Explicit synthetic prior session; never touches real local_history.
 prior=copy.deepcopy(first);prior['session_date']=prior_date
 prior['themes'][0]['global_rank'],prior['themes'][1]['global_rank']=prior['themes'][1]['global_rank'],prior['themes'][0]['global_rank']
 (output/'local_history'/(prior_date+'.json')).write_text(json.dumps(record(prior)))
 assert _run_manual_csv(args,output,time.perf_counter())==0
 second=json.loads((output/'latest_snapshot.json').read_text())
 assert second['themes'][0]['rank_change_daily']==prior['themes'][0]['global_rank']-first['themes'][0]['global_rank']
 for before,after in zip(first['themes'],second['themes']):
  for key in ('theme_score','theme_state','research_priority','global_rank'):assert before[key]==after[key]
 originals={p.relative_to(output):p.read_bytes() for p in output.rglob('*') if p.is_file()}
 real_replace=os.replace
 def fail_history(src,dst):
  if Path(src).name == 'dashboard.html' and 'stage-' in str(src):raise OSError('simulated dashboard publication failure after history')
  return real_replace(src,dst)
 with patch('scripts.generate_dashboard.os.replace',side_effect=fail_history):assert _run_manual_csv(args,output,time.perf_counter())==1
 for p,data in originals.items():assert (output/p).read_bytes()==data,str(p)
 print('PASS: real first run; synthetic two-session CLI comparison; Score/State/Priority invariant; injected history publication failure rolled back all output and history.')
