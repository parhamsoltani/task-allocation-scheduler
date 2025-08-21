#!/usr/bin/env python3
"""
Pipeline script to run different phases of the task allocation system
Usage: python run_pipeline.py <phase_number> [input_file]
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from main import TaskAllocationScheduler

def create_demo_data():
    """Create demonstration data for Phase 1"""
    return {
        "tasks": [
            {"id": "T1", "cpu": 2, "ram": 4, "deadline": 3, "duration": 1},
            {"id": "T2", "cpu": 1, "ram": 2, "deadline": 4, "duration": 1},
            {"id": "T3", "cpu": 3, "ram": 3, "deadline": 5, "duration": 2},
            {"id": "T4", "cpu": 1, "ram": 1, "deadline": 4, "duration": 1}
        ],
        "nodes": [
            {"id": "N1", "cpu_capacity": 5, "ram_capacity": 6},
            {"id": "N2", "cpu_capacity": 4, "ram_capacity": 5},
            {"id": "N3", "cpu_capacity": 3, "ram_capacity": 3}
        ],
        "exec_cost": {
            "T1": {"N1": 4, "N2": 6, "N3": 8},
            "T2": {"N1": 3, "N2": 2, "N3": 4},
            "T3": {"N1": 5, "N2": 7, "N3": 9},
            "T4": {"N1": 1, "N2": 2, "N3": 1}
        }
    }

def save_temp_input(data, filename="temp_input.json"):
    """Save data to temporary input file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    return filename

def run_phase1_demo():
    """Run Phase 1 demonstration"""
    print("="*60)
    print("PHASE 1 DEMONSTRATION: MCMF Task Allocation")
    print("="*60)
    
    # Create demo data
    demo_data = create_demo_data()
    input_file = save_temp_input(demo_data)
    
    try:
        scheduler = TaskAllocationScheduler()
        
        print("Input Data:")
        print(f"- Tasks: {len(demo_data['tasks'])}")
        for task in demo_data['tasks']:
            print(f"  {task['id']}: CPU={task['cpu']}, RAM={task['ram']}, Deadline={task['deadline']}")
        
        print(f"\n- Nodes: {len(demo_data['nodes'])}")
        for node in demo_data['nodes']:
            print(f"  {node['id']}: CPU={node['cpu_capacity']}, RAM={node['ram_capacity']}")
        
        print("\n- Execution Costs:")
        for task_id, costs in demo_data['exec_cost'].items():
            cost_str = ", ".join([f"{node}:{cost}" for node, cost in costs.items()])
            print(f"  {task_id}: {cost_str}")
        
        # Run Phase 1
        result = scheduler.run_phase1(input_file)
        
        print("\n" + "="*40)
        print("RESULTS ANALYSIS:")
        print("="*40)
        
        # Detailed analysis
        if result.valid:
            print("Valid solution found!")
            print(f"Total cost: {result.total_cost}")
            print(f"Tasks assigned: {len(result.assignments)}/{len(demo_data['tasks'])}")
            
            # Node utilization
            node_usage = {}
            for node in demo_data['nodes']:
                node_usage[node['id']] = {'cpu': 0, 'ram': 0, 'tasks': []}
            
            for task_id, assignment in result.assignments.items():
                node_id = assignment['node']
                task = next(t for t in demo_data['tasks'] if t['id'] == task_id)
                node_usage[node_id]['cpu'] += task['cpu']
                node_usage[node_id]['ram'] += task['ram']
                node_usage[node_id]['tasks'].append(task_id)
            
            print("\nNode Utilization:")
            for node in demo_data['nodes']:
                usage = node_usage[node['id']]
                cpu_util = (usage['cpu'] / node['cpu_capacity']) * 100
                ram_util = (usage['ram'] / node['ram_capacity']) * 100
                print(f"  {node['id']}: CPU {usage['cpu']}/{node['cpu_capacity']} ({cpu_util:.1f}%), "
                      f"RAM {usage['ram']}/{node['ram_capacity']} ({ram_util:.1f}%)")
                if usage['tasks']:
                    print(f"    Tasks: {', '.join(usage['tasks'])}")
        else:
            print("No valid solution found")
        
    finally:
        # Cleanup
        if os.path.exists(input_file):
            os.remove(input_file)

def run_phase_from_file(phase, input_file):
    """Run specific phase with input file"""
    scheduler = TaskAllocationScheduler()
    
    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found")
        return
    
    if phase == 1:
        scheduler.run_phase1(input_file)
    elif phase == 2:
        phase1_result = scheduler.run_phase1(input_file)
        scheduler.run_phase2(input_file, phase1_result)
    elif phase == 3:
        phase1_result = scheduler.run_phase1(input_file)
        phase2_result = scheduler.run_phase2(input_file, phase1_result)
        scheduler.run_phase3(input_file, phase2_result)
    elif phase == 4:
        scheduler.run_phase4(input_file, {})
    else:
        print("Error: Phase must be 1, 2, 3, or 4")

def main():
    parser = argparse.ArgumentParser(description="Run task allocation pipeline")
    parser.add_argument("phase", type=int, choices=[1, 2, 3, 4], 
                       help="Phase number to run (1-4)")
    parser.add_argument("--input", type=str, 
                       help="Input JSON file (optional, uses demo data if not provided)")
    parser.add_argument("--demo", action="store_true",
                       help="Run demonstration with built-in data")
    
    args = parser.parse_args()
    
    if args.demo or (args.phase == 1 and not args.input):
        if args.phase == 1:
            run_phase1_demo()
        else:
            print("Demo mode only available for Phase 1")
    elif args.input:
        run_phase_from_file(args.phase, args.input)
    else:
        print("Please provide --input file or use --demo flag")

if __name__ == "__main__":
    main()
