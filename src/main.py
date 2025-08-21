import json
import sys
from typing import Dict, Any
from pathlib import Path

from core.models import Task, Node, DynamicEvent, EventType
from phases.phase1_mcmf import Phase1MCMF
from phases.phase2_scheduling import Phase2Scheduling
from phases.phase3_dynamic import Phase3Dynamic
from phases.phase4_local_dp import Phase4LocalDP

class TaskAllocationScheduler:
    def __init__(self):
        self.phase1 = Phase1MCMF()
        self.phase2 = Phase2Scheduling()
        self.phase3 = Phase3Dynamic()
        self.phase4 = Phase4LocalDP()

    def load_input(self, filepath: str) -> Dict[str, Any]:
        """Load input from JSON file"""
        with open(filepath, 'r') as f:
            return json.load(f)

    def _normalize_time_keys_in_map(self, m: dict) -> dict:
        """Convert string numeric keys -> int for nested dicts like node_capacity_per_time."""
        out = {}
        for node, times in m.items():
            # times expected to be dict keys like "0","1",...
            out[node] = {int(k): v for k, v in times.items()}
        return out

    def parse_tasks(self, task_data: list) -> list:
        """Parse task data into Task objects"""
        tasks = []
        for t in task_data:
            tasks.append(Task(
                id=t['id'],
                cpu=t['cpu'],
                ram=t['ram'],
                deadline=t['deadline'],
                duration=t.get('duration', 1),
                dependencies=t.get('dependencies', [])
            ))
        return tasks

    def parse_nodes(self, node_data: list) -> list:
        """Parse node data into Node objects"""
        nodes = []
        for n in node_data:
            nodes.append(Node(
                id=n['id'],
                cpu_capacity=n['cpu_capacity'],
                ram_capacity=n['ram_capacity']
            ))
        return nodes

    def parse_events(self, event_data: list) -> list:
        """Parse dynamic events"""
        events = []
        for e in event_data:
            event_type = EventType(e['type'])
            events.append(DynamicEvent(
                type=event_type,
                time=e.get('time', 0),
                data=e.get('data', {})
            ))
        return events

    def run_phase1(self, input_file: str):
        """Execute Phase 1: Initial MCMF allocation"""
        print("=" * 50)
        print("PHASE 1: Initial Task Allocation using MCMF")
        print("=" * 50)

        data = self.load_input(input_file)
        if 'node_capacity_per_time' in data:
            data['node_capacity_per_time'] = {
                node: {int(t): cap for t, cap in times.items()}
                for node, times in data['node_capacity_per_time'].items()
            }
        tasks = self.parse_tasks(data['tasks'])
        nodes = self.parse_nodes(data['nodes'])
        exec_cost = data['exec_cost']

        result = self.phase1.run(tasks, nodes, exec_cost)

        print(f"Total tasks: {len(tasks)}")
        print(f"Total nodes: {len(nodes)}")
        print(f"Assignments made: {len(result.assignments)}")
        print(f"Total cost: {result.total_cost}")
        print(f"Valid solution: {result.valid}")
        print("\nAssignments:")
        for task_id, assignment in result.assignments.items():
            print(f"  {task_id} -> {assignment['node']}")

        return result

    def run_phase2(self, input_file: str, phase1_result=None):
        """Execute Phase 2: Time-aware scheduling"""
        print("\n" + "=" * 50)
        print("PHASE 2: Time-Aware Scheduling")
        print("=" * 50)

        data = self.load_input(input_file)
        if 'node_capacity_per_time' in data:
            data['node_capacity_per_time'] = {
                node: {int(t): cap for t, cap in times.items()}
                for node, times in data['node_capacity_per_time'].items()
            }
        tasks = self.parse_tasks(data['tasks'])
        nodes = self.parse_nodes(data['nodes'])
        exec_cost = data['exec_cost']
        time_slots = data.get('time_slots', list(range(10)))
        node_capacity_per_time = data.get('node_capacity_per_time', {})
        if node_capacity_per_time:
            node_capacity_per_time = self._normalize_time_keys_in_map(node_capacity_per_time)
        dependencies = [(d['before'], d['after']) for d in data.get('dependencies', [])]

        # Use Phase 1 assignments if available
        initial_assignments = None
        if phase1_result:
            initial_assignments = {
                task_id: assignment['node']
                for task_id, assignment in phase1_result.assignments.items()
            }

        result = self.phase2.run(
            tasks, nodes, exec_cost, time_slots,
            node_capacity_per_time, dependencies, initial_assignments
        )

        print(f"Scheduled tasks: {len(result.assignments)}")
        print(f"Total cost: {result.total_cost}")
        print(f"Valid schedule: {result.valid}")
        print("\nSchedule:")
        for task_id, assignment in result.assignments.items():
            print(f"  {task_id} -> Node: {assignment['node']}, Start: {assignment['start_time']}")

        return result

    def run_phase3(self, input_file: str, current_schedule):
        """Execute Phase 3: Dynamic reallocation"""
        print("\n" + "=" * 50)
        print("PHASE 3: Dynamic Reallocation")
        print("=" * 50)

        data = self.load_input(input_file)
        if 'node_capacity_per_time' in data:
            data['node_capacity_per_time'] = {
                node: {int(t): cap for t, cap in times.items()}
                for node, times in data['node_capacity_per_time'].items()
            }
        tasks = self.parse_tasks(data['tasks'])
        nodes = self.parse_nodes(data['nodes'])
        exec_cost = data['exec_cost']
        time_slots = data.get('time_slots', list(range(10)))
        node_capacity_per_time = data.get('node_capacity_per_time', {})
        if node_capacity_per_time:
            node_capacity_per_time = self._normalize_time_keys_in_map(node_capacity_per_time)
        dependencies = [(d['before'], d['after']) for d in data.get('dependencies', [])]

        # Parse events
        events = []
        if 'events' in data:
            for e in data['events']:
                event = DynamicEvent(
                    type=EventType(e['type']),
                    time=e.get('time', 0),
                    data=e
                )
                events.append(event)

        result = self.phase3.run(
            current_schedule, tasks, nodes, exec_cost,
            events, time_slots, node_capacity_per_time, dependencies
        )

        print(f"Reassigned tasks: {result['reassigned_tasks']}")
        print(f"Failed tasks: {result['failed_tasks']}")
        print(f"Total cost: {result['total_cost']}")
        print(f"Change penalty: {result['change_penalty']}")

        return result

    def run_phase4(self, input_file: str, assignments):
        """Execute Phase 4: Local DP scheduling"""
        print("\n" + "=" * 50)
        print("PHASE 4: Local DP Scheduling")
        print("=" * 50)

        data = self.load_input(input_file)
        if 'node_capacity_per_time' in data:
            data['node_capacity_per_time'] = {
                node: {int(t): cap for t, cap in times.items()}
                for node, times in data['node_capacity_per_time'].items()
            }
        tasks = self.parse_tasks(data.get('assigned_tasks', data['tasks']))
        nodes = self.parse_nodes(data['nodes'])
        time_slots = data.get('time_slots', list(range(10)))
        resource_per_time = data.get('resource_per_time', {})

        # If running standalone Phase 4
        if 'node' in data:
            node_id = data['node']
            result = self.phase4.run(
                node_id, tasks, resource_per_time, time_slots
            )

            print(f"Node: {node_id}")
            print(f"Tasks scheduled: {len(result.task_schedules)}")
            print(f"Total idle time: {result.total_idle_time}")
            print(f"Penalty cost: {result.penalty_cost}")
            print("\nTask Schedule:")
            for task_id, (start_time, meets_deadline) in result.task_schedules.items():
                status = "✓" if meets_deadline else "✗"
                print(f"  {task_id}: Start={start_time}, Meets deadline={status}")
        else:
            # Run for all nodes based on assignments
            all_resource_per_time = {
                node.id: resource_per_time for node in nodes
            }
            results = self.phase4.run_all_nodes(
                assignments, tasks, nodes, all_resource_per_time, time_slots
            )

            for node_id, result in results.items():
                print(f"\nNode {node_id}:")
                print(f"  Tasks: {len(result.task_schedules)}")
                print(f"  Idle time: {result.total_idle_time}")
                print(f"  Penalty: {result.penalty_cost}")

        return result

def main():
    scheduler = TaskAllocationScheduler()

    if len(sys.argv) < 2:
        print("Usage: python main.py <input_file> [phase]")
        print("Phases: 1, 2, 3, 4, or 'all' for all phases")
        sys.exit(1)

    input_file = sys.argv[1]
    phase = sys.argv[2] if len(sys.argv) > 2 else 'all'

    if phase == '1':
        scheduler.run_phase1(input_file)
    elif phase == '2':
        scheduler.run_phase2(input_file)
    elif phase == '3':
        # Need to load previous schedule
        print("Phase 3 requires a current schedule. Running phases 1-3...")
        phase1_result = scheduler.run_phase1(input_file)
        phase2_result = scheduler.run_phase2(input_file, phase1_result)
        scheduler.run_phase3(input_file, phase2_result)
    elif phase == '4':
        scheduler.run_phase4(input_file, {})

if __name__ == "__main__":
    main()