"""Emit six coherent backend-generated cases for JavaScript consumer tests."""
from pathlib import Path
import sys
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parent)]
from test_research_v2_adversarial import DIRECTIONS,fixture
from src.themescope.storage import canonical

if __name__=='__main__':
    print(canonical({direction:fixture(direction) for direction in DIRECTIONS}))
