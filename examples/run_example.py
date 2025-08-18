#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import TaskAllocationScheduler
from pathlib import Path

def create_example_inputs():
    """Create example input files for testing"""
    
    # Phase 1 & 2 combined input
    phase12_input = {
        "tasks": [
            {"id": "T1", "cpu": 2, "ram": 4, "deadline": 3, "duration": 1},
            {"id": "T2", "cpu": 1, "ram": 2, "deadline": 3, "duration": 1},
            {"id": "T3", "cpu": 3, "ram": 3, "deadline": 5, "duration": 2},
            {"id": "T4", "cpu": 1, "ram": 1, "deadline": 4, "duration": 1}
        ],
        "nodes": [
            {"id": "N1", "cpu_capacity": 4, "ram_capacity": 6},
            {"id": "N2", "cpu_capacity": 4, "ram_capacity": 4},
            {"id": "N3", "cpu_capacity": 2, "ram_capacity": 2}
        ],
        "exec_cost": {
            "T1": {"N1": 4, "N2": 2, "N3": 999},
            "T2": {"N1": 3, "N2": 4, "N3": 2},
            "T3": {"N1": 2, "N2": 3, "N3": 999},
            "T4": {"N1": 1, "N2": 2, "N3": 1}
        },
        "time_slots": [0, 1, 2, 3, 4],
        "node_capacity_per_time": {
            "N1": {"0": 4, "1": 4, "2": 4, "3": 4, "4": 4},
            "N2": {"0": 4, "1": 4, "2": 4, "3": 4, "4": 4},
            "N3": {"0": 2, "1": 2, "2": 2, "3": 2, "4": 2}
        },
        "dependencies": [
            {"before": "T1", "after": "T3"},
            {"before": "T2", "after": "T3"}
        ]
    }
    
    # Phase 3 input (with events)
    phase3_input = phase12_input.copy()
    phase3_input["events"] = [
        {
            "type": "node_failure",
            "node": "N2",
            "time": 2
        },
        {
            "type": "new_task",
            "time": 1,
            "task": {
                "id": "T5",
                "cpu": 2,
                "ram": 2,
                "deadline": 5,
                "duration": 1,
                "exec_cost": {"N1": 3, "N3": 4}
            }
        }
    ]
    
    # Phase 4 input (single node)
    phase4_input = {
        "node": "N1",
        "assigned_tasks": [
            {"id": "T1", "cpu": 2, "ram": 2, "duration": 1, "deadline": 2},
            {"id": "T3", "cpu": 2, "ram": 1, "duration": 2, "deadline": 4},
            {"id": "T4", "cpu": 1, "ram": 1, "duration": 1, "deadline": 3}
        ],
        "resource_per_time": {
            "0": {"cpu": 3, "ram": 4},
            "1": {"cpu": 3, "ram": 4},
            "2": {"cpu": 3, "ram": 4},
            "3": {"cpu": 3, "ram": 4}
        },
        "time_slots": [0, 1, 2, 3]
    }
    
    return phase12_input, phase3_input, phase4_input

def main():
    print("Task Allocation and Scheduling System - Example Run")
    print("=" * 60)
    
    scheduler = TaskAllocationScheduler()
    
    # Create example inputs
    phase12_input, phase3_input, phase4_input = create_example_inputs()
    
    # Save to temp files
    import json
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(phase12_input, f, indent=2)
        phase12_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(phase3_input, f, indent=2)
        phase3_file = f.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(phase4_input, f, indent=2)
        phase4_file = f.name
    
    try:
        # Run Phase 1
        print("\n" + "="*60)
        print("PHASE 1: Initial Allocation")
        print("="*60)
        phase1_result = scheduler.run_phase1(phase12_file)
        
        # Run Phase 2
        print("\n" + "="*60)
        print("PHASE 2: Time-Aware Scheduling")
        print("="*60)
        phase2_result = scheduler.run_phase2(phase12_file, phase1_result)
        
        # Run Phase 3
        print("\n" + "="*60)
        print("PHASE 3: Dynamic Reallocation")
        print("="*60)
        phase3_result = scheduler.run_phase3(phase3_file, phase2_result)
        
        # Run Phase 4
        print("\n" + "="*60)
        print("PHASE 4: Local DP Scheduling")
        print("="*60)
        phase4_result = scheduler.run_phase4(phase4_file, {})
        
    finally:
        # Clean up temp files
        import os
        os.unlink(phase12_file)
        os.unlink(phase3_file)
        os.unlink(phase4_file)
    
    print("\n" + "="*60)
    print("Example run completed successfully!")

if __name__ == "__main__":
    main()