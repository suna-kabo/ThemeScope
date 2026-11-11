"""Offline structural, evidence-rule, source-task and launch-safety validation."""
from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src.themescope.domain import load_configuration
from src.themescope.membership_evidence import validate_evidence
if __name__=='__main__':
    config=load_configuration(ROOT)
    print(json.dumps(dict(validate_evidence(ROOT,config),production_blockers=config.production_blockers()),indent=2))
