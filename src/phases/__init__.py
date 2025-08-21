"""Phase implementations for the multi-phase task allocation system"""
import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from phases.phase1_mcmf import Phase1MCMF
from phases.phase2_scheduling import Phase2Scheduling
from phases.phase3_dynamic import Phase3Dynamic
from phases.phase4_local_dp import Phase4LocalDP

__all__ = [
    'Phase1MCMF',
    'Phase2Scheduling',
    'Phase3Dynamic',
    'Phase4LocalDP'
]