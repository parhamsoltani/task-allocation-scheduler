#!/usr/bin/env python3
"""
Complete pipeline script with all components defined inline to avoid import issues
Usage: python run_pipeline.py <phase_number> [--input file] [--demo]
"""

import sys
import os
import json
import argparse
import networkx as nx
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import copy

# ============================================================================
# CORE MODELS
# ============================================================================

class EventType(Enum):
    NODE_FAILURE = "node_failure"
    NEW_TASK = "new_task"
    CAPACITY_CHANGE = "capacity_change"

@dataclass
class Task:
    id: str
    cpu: int
    ram: int
    deadline: int
    duration: int = 1
    dependencies: List[str] = field(default_factory=list)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Task):
            return self.id == other.id
        return False

@dataclass
class Node:
    id: str
    cpu_capacity: int
    ram_capacity: int

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Node):
            return self.id == other.id
        return False

@dataclass
class Assignment:
    task_id: str
    node_id: str
    start_time: Optional[int] = None

@dataclass
class Schedule:
    assignments: Dict[str, Dict]
    total_cost: float
    valid: bool = True

@dataclass
class DynamicEvent:
    type: EventType
    time: int
    data: Dict

@dataclass
class NodeSchedule:
    node_id: str
    task_schedules: Dict[str, Tuple[int, bool]]
    total_idle_time: int
    penalty_cost: float

# ============================================================================
# ALGORITHMS
# ============================================================================

class MinCostMaxFlow:
    def solve(self, graph: nx.DiGraph) -> Tuple[Dict[str, str], float]:
        """Solve MCMF using NetworkX min_cost_flow"""
        try:
            flow_dict = nx.min_cost_flow(graph, demand='demand', capacity='capacity', weight='weight')
            assignments = {}
            total_cost = 0.0

            for u in flow_dict:
                for v in flow_dict[u]:
                    flow = flow_dict[u][v]
                    if flow > 0:
                        if str(u).startswith('task_') and str(v).startswith('node_'):
                            assignments[u] = v
                            if graph.has_edge(u, v):
                                cost = graph[u][v].get('weight', 0)
                                total_cost += flow * cost

            return assignments, total_cost
        except Exception as e:
            print(f"NetworkX min_cost_flow failed: {e}")
            return self._greedy_fallback(graph)

    def _greedy_fallback(self, graph: nx.DiGraph) -> Tuple[Dict[str, str], float]:
        assignments = {}
        total_cost = 0.0
        tasks = [n for n in graph.nodes() if str(n).startswith('task_')]
        nodes = [n for n in graph.nodes() if str(n).startswith('node_')]

        for task in tasks:
            best_node = None
            best_cost = float('inf')
            for node in nodes:
                if graph.has_edge(task, node):
                    cost = graph[task][node].get('weight', 0)
                    if cost < best_cost:
                        best_cost = cost
                        best_node = node

            if best_node and best_cost != float('inf'):
                assignments[task] = best_node
                total_cost += best_cost

        return assignments, total_cost

class FlowGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.source = "SOURCE"
        self.sink = "SINK"

    def build_basic_flow_graph(self, tasks: List[Task], nodes: List[Node],
                               exec_cost: Dict[str, Dict[str, float]]) -> nx.DiGraph:
        self.graph.clear()
        self.graph.add_node(self.source, demand=-len(tasks))
        self.graph.add_node(self.sink, demand=len(tasks))

        for task in tasks:
            self.graph.add_node(f"task_{task.id}", task=task)

        for node in nodes:
            self.graph.add_node(f"node_{node.id}", node=node)

        for task in tasks:
            self.graph.add_edge(self.source, f"task_{task.id}", capacity=1, weight=0)

        for task in tasks:
            for node in nodes:
                if self._is_feasible(task, node):
                    cost = exec_cost.get(task.id, {}).get(node.id, float('inf'))
                    if cost != float('inf'):
                        self.graph.add_edge(f"task_{task.id}", f"node_{node.id}",
                                          capacity=1, weight=cost)

        for node in nodes:
            max_tasks = min(node.cpu_capacity // 1, node.ram_capacity // 1)
            self.graph.add_edge(f"node_{node.id}", self.sink, capacity=max_tasks, weight=0)

        return self.graph

    def _is_feasible(self, task: Task, node: Node) -> bool:
        return task.cpu <= node.cpu_capacity and task.ram <= node.ram_capacity

class TaskScheduler:
    def schedule_with_dependencies(self, tasks: List[Task], assignments: Dict[str, str],
                                  dependencies: List[Tuple[str, str]],
                                  node_capacity_per_time: Dict[str, Dict[int, int]],
                                  time_slots: List[int]) -> Dict[str, Assignment]:
        dep_graph = {task.id: [] for task in tasks}
        in_degree = {task.id: 0 for task in tasks}

        for before, after in dependencies:
            dep_graph[before].append(after)
            in_degree[after] += 1

        ready_tasks = [task_id for task_id, degree in in_degree.items() if degree == 0]
        scheduled = {}
        task_finish_times = {}
        node_usage = {node_id: {t: 0 for t in time_slots} for node_id in set(assignments.values())}

        while ready_tasks:
            task_id = ready_tasks.pop(0)
            node_id = assignments.get(task_id)
            if not node_id:
                continue

            task = next((t for t in tasks if t.id == task_id), None)
            if not task:
                continue

            earliest_start = 0
            for dep_id in [d for d, a in dependencies if a == task_id]:
                if dep_id in task_finish_times:
                    earliest_start = max(earliest_start, task_finish_times[dep_id])

            start_time = self._find_feasible_start_time(
                task, node_id, earliest_start, node_capacity_per_time, node_usage, time_slots)

            if start_time is not None:
                scheduled[task_id] = Assignment(task_id=task_id, node_id=node_id, start_time=start_time)
                task_finish_times[task_id] = start_time + task.duration

                for t in range(start_time, start_time + task.duration):
                    if t in node_usage[node_id]:
                        node_usage[node_id][t] += task.cpu

                for next_task in dep_graph[task_id]:
                    in_degree[next_task] -= 1
                    if in_degree[next_task] == 0:
                        ready_tasks.append(next_task)

        return scheduled

    def _find_feasible_start_time(self, task: Task, node_id: str, earliest_start: int,
                                  node_capacity_per_time: Dict[str, Dict[int, int]],
                                  node_usage: Dict[str, Dict[int, int]],
                                  time_slots: List[int]) -> Optional[int]:
        for start_time in range(earliest_start, max(time_slots) + 1):
            feasible = True
            for t in range(start_time, start_time + task.duration):
                if t not in time_slots:
                    feasible = False
                    break
                available_cpu = node_capacity_per_time.get(node_id, {}).get(t, 0)
                used_cpu = node_usage.get(node_id, {}).get(t, 0)
                if used_cpu + task.cpu > available_cpu:
                    feasible = False
                    break
                if t >= task.deadline:
                    feasible = False
                    break
            if feasible:
                return start_time
        return None

class DPScheduler:
    def schedule_node_tasks(self, node_id: str, tasks: List[Task],
                           resource_per_time: Dict[int, Dict[str, int]],
                           time_slots: List[int]) -> NodeSchedule:
        if not tasks:
            return NodeSchedule(node_id=node_id, task_schedules={},
                              total_idle_time=len(time_slots), penalty_cost=0)

        sorted_tasks = sorted(tasks, key=lambda t: t.deadline)
        schedule = {}
        used_time_slots = set()
        penalty = 0

        for task in sorted_tasks:
            best_start = None
            for start_time in time_slots:
                if start_time in used_time_slots:
                    continue

                can_schedule = True
                for t in range(start_time, min(start_time + task.duration, max(time_slots) + 1)):
                    if t not in time_slots or t in used_time_slots:
                        can_schedule = False
                        break
                    available = resource_per_time.get(t, {})
                    if available.get('cpu', 0) < task.cpu or available.get('ram', 0) < task.ram:
                        can_schedule = False
                        break

                if can_schedule:
                    best_start = start_time
                    break

            if best_start is not None:
                end_time = best_start + task.duration
                meets_deadline = end_time <= task.deadline
                schedule[task.id] = (best_start, meets_deadline)
                for t in range(best_start, end_time):
                    if t in time_slots:
                        used_time_slots.add(t)
                if not meets_deadline:
                    penalty += (end_time - task.deadline) * 10
            else:
                penalty += 100

        idle_time = len(time_slots) - len(used_time_slots)
        return NodeSchedule(node_id=node_id, task_schedules=schedule,
                          total_idle_time=idle_time, penalty_cost=penalty)

# ============================================================================
# PHASE IMPLEMENTATIONS
# ============================================================================

class Phase1MCMF:
    def __init__(self):
        self.graph_builder = FlowGraphBuilder()
        self.mcmf_solver = MinCostMaxFlow()

    def run(self, tasks: List[Task], nodes: List[Node],
            exec_cost: Dict[str, Dict[str, float]]) -> Schedule:
        graph = self.graph_builder.build_basic_flow_graph(tasks, nodes, exec_cost)
        assignments, total_cost = self.mcmf_solver.solve(graph)

        assignment_objects = {}
        for task_key, node_key in assignments.items():
            task_id = str(task_key).replace('task_', '').split('_t')[0]
            node_id = str(node_key).replace('node_', '').split('_t')[0]
            assignment_objects[task_id] = {'node': node_id, 'start_time': None}

        return Schedule(assignments=assignment_objects, total_cost=total_cost,
                       valid=len(assignment_objects) == len(tasks))

class Phase2Scheduling:
    def __init__(self):
        self.scheduler = TaskScheduler()

    def run(self, tasks: List[Task], nodes: List[Node], exec_cost: Dict[str, Dict[str, float]],
            time_slots: List[int], node_capacity_per_time: Dict[str, Dict[int, int]],
            dependencies: List[Tuple[str, str]], initial_assignments: Optional[Dict[str, str]] = None) -> Schedule:

        if initial_assignments:
            scheduled = self.scheduler.schedule_with_dependencies(
                tasks, initial_assignments, dependencies, node_capacity_per_time, time_slots)

            assignments = {}
            total_cost = 0
            for task_id, assignment in scheduled.items():
                assignments[task_id] = {'node': assignment.node_id, 'start_time': assignment.start_time}
                cost = exec_cost.get(task_id, {}).get(assignment.node_id, 0)
                total_cost += cost

            return Schedule(assignments=assignments, total_cost=total_cost, valid=True)
        else:
            assignments = {}
            total_cost = 0
            for task in tasks:
                best_node = None
                best_cost = float('inf')
                for node in nodes:
                    if task.cpu <= node.cpu_capacity and task.ram <= node.ram_capacity:
                        cost = exec_cost.get(task.id, {}).get(node.id, float('inf'))
                        if cost < best_cost:
                            best_cost = cost
                            best_node = node
                if best_node:
                    assignments[task.id] = {'node': best_node.id, 'start_time': 0}
                    total_cost += best_cost

            return Schedule(assignments=assignments, total_cost=total_cost,
                          valid=len(assignments) == len(tasks))

class Phase3Dynamic:
    def run(self, current_schedule: Schedule, tasks: List[Task], nodes: List[Node],
            exec_cost: Dict[str, Dict[str, float]], events: List[DynamicEvent],
            time_slots: List[int], node_capacity_per_time: Dict[str, Dict[int, int]],
            dependencies: List[Tuple[str, str]]) -> Dict:

        updated_assignments = copy.deepcopy(current_schedule.assignments)
        reassigned_tasks = []
        failed_tasks = []
        change_penalty = 0

        for event in events:
            if event.type == EventType.NODE_FAILURE:
                failed_node_id = event.data['node']
                affected_tasks = [task_id for task_id, assign in updated_assignments.items()
                                 if assign['node'] == failed_node_id]

                for task_id in affected_tasks:
                    task = next((t for t in tasks if t.id == task_id), None)
                    if task:
                        alternative_found = False
                        for node in nodes:
                            if node.id != failed_node_id and task.cpu <= node.cpu_capacity and task.ram <= node.ram_capacity:
                                updated_assignments[task_id] = {'node': node.id, 'start_time': event.time}
                                reassigned_tasks.append(task_id)
                                change_penalty += 1
                                alternative_found = True
                                break
                        if not alternative_found:
                            failed_tasks.append(task_id)
                            if task_id in updated_assignments:
                                del updated_assignments[task_id]

            elif event.type == EventType.NEW_TASK:
                new_task_data = event.data['task']
                new_task = Task(id=new_task_data['id'], cpu=new_task_data['cpu'],
                              ram=new_task_data['ram'], deadline=new_task_data['deadline'],
                              duration=new_task_data.get('duration', 1))
                tasks.append(new_task)

                assignment_found = False
                for node in nodes:
                    if new_task.cpu <= node.cpu_capacity and new_task.ram <= node.ram_capacity:
                        updated_assignments[new_task.id] = {'node': node.id, 'start_time': event.time}
                        reassigned_tasks.append(new_task.id)
                        assignment_found = True
                        break
                if not assignment_found:
                    failed_tasks.append(new_task.id)

        total_cost = sum(exec_cost.get(task_id, {}).get(assignment['node'], 0)
                        for task_id, assignment in updated_assignments.items())

        return {'updated_schedule': updated_assignments, 'reassigned_tasks': reassigned_tasks,
                'failed_tasks': failed_tasks, 'total_cost': total_cost, 'change_penalty': change_penalty}

class Phase4LocalDP:
    def __init__(self):
        self.dp_scheduler = DPScheduler()

    def run(self, node_id: str, assigned_tasks: List[Task],
            resource_per_time: Dict[int, Dict[str, int]], time_slots: List[int]) -> NodeSchedule:
        return self.dp_scheduler.schedule_node_tasks(node_id, assigned_tasks, resource_per_time, time_slots)

# ============================================================================
# MAIN SCHEDULER
# ============================================================================

class TaskAllocationScheduler:
    def __init__(self):
        self.phase1 = Phase1MCMF()
        self.phase2 = Phase2Scheduling()
        self.phase3 = Phase3Dynamic()
        self.phase4 = Phase4LocalDP()

    def load_input(self, filepath: str) -> Dict[str, Any]:
        with open(filepath, 'r') as f:
            return json.load(f)

    def parse_tasks(self, task_data: list) -> list:
        return [Task(id=t['id'], cpu=t['cpu'], ram=t['ram'], deadline=t['deadline'],
                    duration=t.get('duration', 1), dependencies=t.get('dependencies', []))
                for t in task_data]

    def parse_nodes(self, node_data: list) -> list:
        return [Node(id=n['id'], cpu_capacity=n['cpu_capacity'], ram_capacity=n['ram_capacity'])
                for n in node_data]

    def run_phase1(self, input_file: str):
        print("=" * 50)
        print("PHASE 1: Initial Task Allocation using MCMF")
        print("=" * 50)

        data = self.load_input(input_file)
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
        print("\n" + "=" * 50)
        print("PHASE 2: Time-Aware Scheduling")
        print("=" * 50)

        data = self.load_input(input_file)
        tasks = self.parse_tasks(data['tasks'])
        nodes = self.parse_nodes(data['nodes'])
        exec_cost = data['exec_cost']
        time_slots = data.get('time_slots', list(range(10)))

        node_capacity_per_time = data.get('node_capacity_per_time', {})
        if node_capacity_per_time:
            node_capacity_per_time = {node: {int(t): cap for t, cap in times.items()}
                                     for node, times in node_capacity_per_time.items()}

        dependencies = [(d['before'], d['after']) for d in data.get('dependencies', [])]

        initial_assignments = None
        if phase1_result:
            initial_assignments = {task_id: assignment['node']
                                 for task_id, assignment in phase1_result.assignments.items()}

        result = self.phase2.run(tasks, nodes, exec_cost, time_slots,
                                node_capacity_per_time, dependencies, initial_assignments)

        print(f"Scheduled tasks: {len(result.assignments)}")
        print(f"Total cost: {result.total_cost}")
        print(f"Valid schedule: {result.valid}")
        print("\nSchedule:")
        for task_id, assignment in result.assignments.items():
            print(f"  {task_id} -> Node: {assignment['node']}, Start: {assignment.get('start_time', 'N/A')}")

        return result

    def run_phase3(self, input_file: str, current_schedule):
        print("\n" + "=" * 50)
        print("PHASE 3: Dynamic Reallocation")
        print("=" * 50)

        data = self.load_input(input_file)
        tasks = self.parse_tasks(data['tasks'])
        nodes = self.parse_nodes(data['nodes'])
        exec_cost = data['exec_cost']
        time_slots = data.get('time_slots', list(range(10)))

        node_capacity_per_time = data.get('node_capacity_per_time', {})
        if node_capacity_per_time:
            node_capacity_per_time = {node: {int(t): cap for t, cap in times.items()}
                                     for node, times in node_capacity_per_time.items()}

        dependencies = [(d['before'], d['after']) for d in data.get('dependencies', [])]

        events = []
        if 'events' in data:
            for e in data['events']:
                events.append(DynamicEvent(type=EventType(e['type']), time=e.get('time', 0), data=e))

        result = self.phase3.run(current_schedule, tasks, nodes, exec_cost,
                                events, time_slots, node_capacity_per_time, dependencies)

        print(f"Reassigned tasks: {result['reassigned_tasks']}")
        print(f"Failed tasks: {result['failed_tasks']}")
        print(f"Total cost: {result['total_cost']}")
        print(f"Change penalty: {result['change_penalty']}")

        return result

    def run_phase4(self, input_file: str, assignments=None):
        print("\n" + "=" * 50)
        print("PHASE 4: Local DP Scheduling")
        print("=" * 50)

        data = self.load_input(input_file)

        if 'assigned_tasks' in data:
            tasks = self.parse_tasks(data['assigned_tasks'])
        else:
            all_tasks = self.parse_tasks(data.get('tasks', []))
            node_id = data.get('node', 'N1')
            if assignments:
                tasks = [t for t in all_tasks if assignments.get(t.id, {}).get('node') == node_id]
            else:
                tasks = all_tasks[:2] if len(all_tasks) >= 2 else all_tasks

        time_slots = data.get('time_slots', list(range(10)))
        resource_per_time = data.get('resource_per_time', {})

        if resource_per_time:
            if isinstance(list(resource_per_time.keys())[0] if resource_per_time else 0, str):
                resource_per_time = {int(k): v for k, v in resource_per_time.items()}
        else:
            node_id = data.get('node', 'N1')
            nodes = self.parse_nodes(data.get('nodes', []))
            node = next((n for n in nodes if n.id == node_id), None)
            if node:
                resource_per_time = {t: {"cpu": node.cpu_capacity, "ram": node.ram_capacity}
                                   for t in time_slots}
            else:
                resource_per_time = {t: {"cpu": 5, "ram": 6} for t in time_slots}

        node_id = data.get('node', 'N1')
        result = self.phase4.run(node_id, tasks, resource_per_time, time_slots)

        print(f"Node: {node_id}")
        print(f"Tasks to schedule: {[t.id for t in tasks]}")
        print(f"Tasks scheduled: {len(result.task_schedules)}")
        print(f"Total idle time: {result.total_idle_time}")
        print(f"Penalty cost: {result.penalty_cost}")
        print("\nTask Schedule:")
        for task_id, (start_time, meets_deadline) in result.task_schedules.items():
            status = "✓" if meets_deadline else "✗"
            print(f"  {task_id}: Start={start_time}, Meets deadline={status}")

        return result

def create_demo_data():
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
        },
        "time_slots": [0, 1, 2, 3, 4, 5],
        "node_capacity_per_time": {
            "N1": {"0": 5, "1": 5, "2": 5, "3": 5, "4": 5, "5": 5},
            "N2": {"0": 4, "1": 4, "2": 4, "3": 4, "4": 4, "5": 4},
            "N3": {"0": 3, "1": 3, "2": 3, "3": 3, "4": 3, "5": 3}
        },
        "dependencies": [{"before": "T1", "after": "T3"}]
    }

def save_temp_input(data, filename="temp_input.json"):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    return filename

def run_all_phases_demo():
    print("="*60)
    print("COMPLETE PIPELINE DEMONSTRATION")
    print("="*60)

    scheduler = TaskAllocationScheduler()
    demo_data = create_demo_data()
    input_file = save_temp_input(demo_data)

    try:
        # Phase 1
        phase1_result = scheduler.run_phase1(input_file)

        # Phase 2
        phase2_result = scheduler.run_phase2(input_file, phase1_result)

        # Phase 3
        demo_data_phase3 = demo_data.copy()
        demo_data_phase3['events'] = [
            {"type": "node_failure", "node": "N3", "time": 2},
            {"type": "new_task", "time": 1, "task": {
                "id": "T5", "cpu": 2, "ram": 2, "deadline": 6, "duration": 1,
                "exec_cost": {"N1": 3, "N2": 4}
            }}
        ]
        phase3_file = save_temp_input(demo_data_phase3, "phase3_input.json")
        phase3_result = scheduler.run_phase3(phase3_file, phase2_result)

        # Phase 4
        phase4_data = demo_data.copy()
        phase4_data['node'] = 'N1'
        phase4_file = save_temp_input(phase4_data, "phase4_input.json")
        phase4_result = scheduler.run_phase4(phase4_file, phase2_result.assignments)

        print("\n" + "="*60)
        print("PIPELINE COMPLETED SUCCESSFULLY!")
        print("="*60)

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        for file in [input_file, "phase3_input.json", "phase4_input.json"]:
            if os.path.exists(file):
                os.remove(file)

def main():
    parser = argparse.ArgumentParser(description="Run task allocation pipeline")
    parser.add_argument("phase", nargs='?', default='all', choices=['1', '2', '3', '4', 'all'])
    parser.add_argument("--input", type=str, help="Input JSON file")
    parser.add_argument("--demo", action="store_true", help="Run with demo data")

    args = parser.parse_args()

    if args.input and args.phase != 'all':
        scheduler = TaskAllocationScheduler()
        if args.phase == '1':
            scheduler.run_phase1(args.input)
        elif args.phase == '2':
            phase1_result = scheduler.run_phase1(args.input)
            scheduler.run_phase2(args.input, phase1_result)
        elif args.phase == '3':
            phase1_result = scheduler.run_phase1(args.input)
            phase2_result = scheduler.run_phase2(args.input, phase1_result)
            scheduler.run_phase3(args.input, phase2_result)
        elif args.phase == '4':
            scheduler.run_phase4(args.input)
    else:
        run_all_phases_demo()

if __name__ == "__main__":
    main()