#!/usr/bin/env python3
"""
Pipeline script to run different phases of the task allocation system
Usage: python run_pipeline.py <phase_number> [--input file] [--demo]
"""

import sys
import os
import json
import argparse
from pathlib import Path

# Add src to path - this is the key fix
current_dir = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

# Now import after path is set
try:
    from main import TaskAllocationScheduler
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current directory: {current_dir}")
    print(f"Src path: {src_path}")
    print(f"Python path: {sys.path}")
    sys.exit(1)

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

        print("INPUT DATA:")
        print(f"Tasks: {len(demo_data['tasks'])}")
        for task in demo_data['tasks']:
            print(f"  {task['id']}: CPU={task['cpu']}, RAM={task['ram']}, Deadline={task['deadline']}")

        print(f"\nNodes: {len(demo_data['nodes'])}")
        for node in demo_data['nodes']:
            print(f"  {node['id']}: CPU={node['cpu_capacity']}, RAM={node['ram_capacity']}")

        print("\nExecution Costs:")
        for task_id, costs in demo_data['exec_cost'].items():
            cost_str = ", ".join([f"{node}:{cost}" for node, cost in costs.items()])
            print(f"  {task_id}: {cost_str}")

        print(f"\nRUNNING PHASE 1...")
        # Run Phase 1
        result = scheduler.run_phase1(input_file)

        print("\nDETAILED ANALYSIS:")
        print("="*40)

        # Detailed analysis
        if result.valid:
            print("Valid solution found!")
            print(f"Total cost: {result.total_cost}")
            print(f"Tasks assigned: {len(result.assignments)}/{len(demo_data['tasks'])}")

            # Calculate node utilization
            node_usage = {}
            for node in demo_data['nodes']:
                node_usage[node['id']] = {'cpu': 0, 'ram': 0, 'tasks': []}

            for task_id, assignment in result.assignments.items():
                node_id = assignment['node']
                task = next(t for t in demo_data['tasks'] if t['id'] == task_id)
                node_usage[node_id]['cpu'] += task['cpu']
                node_usage[node_id]['ram'] += task['ram']
                node_usage[node_id]['tasks'].append(task_id)

            print("\nNODE UTILIZATION:")
            for node in demo_data['nodes']:
                usage = node_usage[node['id']]
                cpu_util = (usage['cpu'] / node['cpu_capacity']) * 100
                ram_util = (usage['ram'] / node['ram_capacity']) * 100
                print(f"  {node['id']}: CPU {usage['cpu']}/{node['cpu_capacity']} ({cpu_util:.1f}%), "
                      f"RAM {usage['ram']}/{node['ram_capacity']} ({ram_util:.1f}%)")
                if usage['tasks']:
                    print(f"    Tasks: {', '.join(usage['tasks'])}")
                else:
                    print(f"    Tasks: None")

            # Show cost breakdown
            print(f"\nCOST BREAKDOWN:")
            total_verification = 0
            for task_id, assignment in result.assignments.items():
                node_id = assignment['node']
                cost = demo_data['exec_cost'][task_id][node_id]
                total_verification += cost
                print(f"  {task_id} on {node_id}: {cost}")
            print(f"  Total: {total_verification} (verification: {"True" if abs(total_verification - result.total_cost) < 0.01 else "False"})")

        else:
            print("No valid solution found")
            print("This might indicate:")
            print("  - Insufficient node capacity")
            print("  - No feasible assignments exist")
            print("  - Algorithm failed to find solution")

    except Exception as e:
        print(f"Error running Phase 1: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if os.path.exists(input_file):
            os.remove(input_file)

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
            print("Demo mode currently only available for Phase 1")
    elif args.input:
        print(f"Running Phase {args.phase} with input file: {args.input}")
        # Add file-based execution here
    else:
        print("Please provide --input file or use --demo flag")
        print("Example: python run_pipeline.py 1 --demo")

if __name__ == "__main__":
    main()