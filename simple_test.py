#!/usr/bin/env python3
"""
Simple Phase 1 test with proper capacity constraints
"""
import sys
import os
import json
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
from itertools import combinations

# Add the src directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'src')
sys.path.insert(0, src_path)

try:
    import networkx as nx
    print("Imports successful!")
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

@dataclass
class Task:
    id: str
    cpu: int
    ram: int
    deadline: int
    duration: int = 1

@dataclass
class Node:
    id: str
    cpu_capacity: int
    ram_capacity: int

def load_from_json(filepath: str) -> Tuple[List[Task], List[Node], Dict]:
    """Load tasks, nodes, and costs from JSON file"""
    print(f"Loading from {filepath}")

    if not os.path.exists(filepath):
        print(f"❌ File {filepath} not found!")
        return None, None, None

    with open(filepath, 'r') as f:
        data = json.load(f)

    print(f"JSON data loaded: {len(data.get('tasks', []))} tasks, {len(data.get('nodes', []))} nodes")

    tasks = []
    for t in data['tasks']:
        tasks.append(Task(
            id=t['id'],
            cpu=t['cpu'],
            ram=t['ram'],
            deadline=t['deadline'],
            duration=t.get('duration', 1)
        ))

    nodes = []
    for n in data['nodes']:
        nodes.append(Node(
            id=n['id'],
            cpu_capacity=n['cpu_capacity'],
            ram_capacity=n['ram_capacity']
        ))

    exec_cost = data['exec_cost']

    return tasks, nodes, exec_cost

def can_tasks_fit_on_node(task_ids: List[str], tasks: List[Task], node: Node) -> bool:
    """Check if a combination of tasks can fit on a node"""
    total_cpu = sum(t.cpu for t in tasks if t.id in task_ids)
    total_ram = sum(t.ram for t in tasks if t.id in task_ids)

    return total_cpu <= node.cpu_capacity and total_ram <= node.ram_capacity

def build_proper_mcmf_graph(tasks: List[Task], nodes: List[Node], exec_cost: Dict) -> nx.DiGraph:
    """Build MCMF graph with proper capacity constraints using configuration nodes"""
    graph = nx.DiGraph()
    source = "SOURCE"
    sink = "SINK"

    # Add source and sink
    graph.add_node(source, demand=-len(tasks))
    graph.add_node(sink, demand=len(tasks))

    # Add task nodes
    for task in tasks:
        task_node = f"task_{task.id}"
        graph.add_node(task_node)
        graph.add_edge(source, task_node, capacity=1, weight=0)

    # For each node, enumerate valid task combinations (configurations)
    for node in nodes:
        valid_configs = []

        # Generate all possible combinations of tasks that fit on this node
        for r in range(len(tasks) + 1):
            for task_combo in combinations([t.id for t in tasks], r):
                if can_tasks_fit_on_node(list(task_combo), tasks, node):
                    valid_configs.append(task_combo)

        print(f"Node {node.id}: {len(valid_configs)} valid configurations")

        # Create a configuration node for each valid combination
        for i, config in enumerate(valid_configs):
            config_node = f"config_{node.id}_{i}"
            graph.add_node(config_node)

            # Edge from config to sink (each config can be used once)
            graph.add_edge(config_node, sink, capacity=1, weight=0)

            # Edges from tasks to config (only if task is in this config)
            for task in tasks:
                if task.id in config:
                    task_node = f"task_{task.id}"
                    cost = exec_cost.get(task.id, {}).get(node.id, 999)
                    if cost < 999:
                        graph.add_edge(task_node, config_node, capacity=1, weight=cost)

    return graph

def solve_mcmf(graph: nx.DiGraph) -> Tuple[Dict, float]:
    """Solve MCMF and extract assignments"""
    try:
        flow_dict = nx.min_cost_flow(graph, demand='demand', capacity='capacity', weight='weight')

        assignments = {}
        total_cost = 0.0

        for u in flow_dict:
            for v in flow_dict[u]:
                flow = flow_dict[u][v]
                if flow > 0 and str(u).startswith('task_') and str(v).startswith('config_'):
                    task_id = str(u).replace('task_', '')
                    # Extract node ID from config name: config_N1_0 -> N1
                    node_id = str(v).split('_')[1]
                    assignments[task_id] = node_id

                    if graph.has_edge(u, v):
                        cost = graph[u][v].get('weight', 0)
                        total_cost += flow * cost

        return assignments, total_cost

    except Exception as e:
        print(f"MCMF failed: {e}")
        return {}, float('inf')

def greedy_assignment(tasks: List[Task], nodes: List[Node], exec_cost: Dict) -> Tuple[Dict, float]:
    """Greedy assignment with proper capacity checking"""
    print("Using greedy assignment...")

    assignments = {}
    total_cost = 0.0
    node_usage = {node.id: {'cpu': 0, 'ram': 0, 'tasks': []} for node in nodes}

    # Sort tasks by minimum cost
    task_costs = []
    for task in tasks:
        min_cost = min(exec_cost.get(task.id, {}).values())
        task_costs.append((task, min_cost))

    task_costs.sort(key=lambda x: x[1])  # Sort by cost

    for task, _ in task_costs:
        best_node = None
        best_cost = float('inf')

        for node in nodes:
            # Check if task fits with current assignments
            current_cpu = node_usage[node.id]['cpu']
            current_ram = node_usage[node.id]['ram']

            if (current_cpu + task.cpu <= node.cpu_capacity and
                current_ram + task.ram <= node.ram_capacity):

                cost = exec_cost.get(task.id, {}).get(node.id, float('inf'))
                if cost < best_cost:
                    best_cost = cost
                    best_node = node

        if best_node:
            assignments[task.id] = best_node.id
            total_cost += best_cost
            node_usage[best_node.id]['cpu'] += task.cpu
            node_usage[best_node.id]['ram'] += task.ram
            node_usage[best_node.id]['tasks'].append(task.id)
        else:
            print(f"Cannot assign task {task.id} - no node has sufficient capacity")

    return assignments, total_cost

def validate_solution(assignments: Dict, tasks: List[Task], nodes: List[Node]) -> bool:
    """Validate the solution"""
    if len(assignments) != len(tasks):
        return False

    node_usage = {node.id: {'cpu': 0, 'ram': 0, 'tasks': []} for node in nodes}

    for task in tasks:
        if task.id not in assignments:
            return False

        node_id = assignments[task.id]
        node_usage[node_id]['cpu'] += task.cpu
        node_usage[node_id]['ram'] += task.ram
        node_usage[node_id]['tasks'].append(task.id)

    for node in nodes:
        usage = node_usage[node.id]
        if usage['cpu'] > node.cpu_capacity or usage['ram'] > node.ram_capacity:
            return False

    return True

def test_phase1(input_file: Optional[str] = None):
    """Test Phase 1 functionality"""
    print("PHASE 1 TEST - MCMF Task Allocation")
    print("=" * 50)

    if input_file:
        tasks, nodes, exec_cost = load_from_json(input_file)
        if tasks is None:
            print("Failed to load JSON file")
            return
    else:
        print("Using built-in test data")
        tasks = [
            Task(id="T1", cpu=2, ram=3, deadline=3, duration=1),
            Task(id="T2", cpu=1, ram=2, deadline=4, duration=1),
            Task(id="T3", cpu=2, ram=2, deadline=5, duration=2)
        ]

        nodes = [
            Node(id="N1", cpu_capacity=5, ram_capacity=6),
            Node(id="N2", cpu_capacity=4, ram_capacity=5)
        ]

        exec_cost = {
            "T1": {"N1": 4, "N2": 6},
            "T2": {"N1": 3, "N2": 2},
            "T3": {"N1": 5, "N2": 7}
        }

    print("\nINPUT DATA:")
    print("Tasks:")
    for task in tasks:
        print(f"  {task.id}: CPU={task.cpu}, RAM={task.ram}, Deadline={task.deadline}")

    print("\nNodes:")
    for node in nodes:
        print(f"  {node.id}: CPU={node.cpu_capacity}, RAM={node.ram_capacity}")

    print("\nExecution Costs:")
    for task_id, costs in exec_cost.items():
        for node_id, cost in costs.items():
            print(f"  {task_id} on {node_id}: {cost}")

    # Try MCMF approach
    print(f"\nBUILDING MCMF GRAPH WITH CONFIGURATIONS...")
    try:
        graph = build_proper_mcmf_graph(tasks, nodes, exec_cost)
        print(f"Graph nodes: {len(graph.nodes())}")
        print(f"Graph edges: {len(graph.edges())}")

        print(f"\nSOLVING MCMF...")
        assignments, total_cost = solve_mcmf(graph)

        if not assignments or total_cost == float('inf'):
            print("MCMF failed, trying greedy...")
            assignments, total_cost = greedy_assignment(tasks, nodes, exec_cost)

    except Exception as e:
        print(f"MCMF approach failed: {e}")
        assignments, total_cost = greedy_assignment(tasks, nodes, exec_cost)

    print(f"\nRESULTS:")
    print(f"Assignments: {assignments}")
    print(f"Total cost: {total_cost}")

    # Validation
    print(f"\nVALIDATION:")
    valid = validate_solution(assignments, tasks, nodes)

    if len(assignments) == len(tasks):
        print("All tasks assigned")
    else:
        print(f"❌ Only {len(assignments)}/{len(tasks)} tasks assigned")

    # Show detailed node usage
    node_usage = {node.id: {'cpu': 0, 'ram': 0, 'tasks': []} for node in nodes}
    for task in tasks:
        if task.id in assignments:
            node_id = assignments[task.id]
            node_usage[node_id]['cpu'] += task.cpu
            node_usage[node_id]['ram'] += task.ram
            node_usage[node_id]['tasks'].append(task.id)

    print("\nNode utilization:")
    for node in nodes:
        usage = node_usage[node.id]
        cpu_ok = usage['cpu'] <= node.cpu_capacity
        ram_ok = usage['ram'] <= node.ram_capacity
        status = "True" if (cpu_ok and ram_ok) else "False"
        tasks_str = ', '.join(usage['tasks']) if usage['tasks'] else 'None'
        print(f"  {node.id}: CPU {usage['cpu']}/{node.cpu_capacity}, RAM {usage['ram']}/{node.ram_capacity} {status}")
        print(f"    Tasks: {tasks_str}")

    if valid:
        print("\nSOLUTION IS VALID!")
    else:
        print("\nSOLUTION VIOLATES CONSTRAINTS!")

    return assignments, total_cost

if __name__ == "__main__":
    input_file = sys.argv[1] if len(sys.argv) > 1 else None
    test_phase1(input_file)