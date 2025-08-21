#!/usr/bin/env python3
import sys
import os
import json

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Direct imports
from core.models import Task, Node, Schedule
from core.graph_builder import FlowGraphBuilder
from algorithms.mcmf import MinCostMaxFlow

def test_phase1():
    """Test Phase 1 functionality"""

    # Create test data
    tasks = [
        Task(id="T1", cpu=2, ram=4, deadline=3, duration=1),
        Task(id="T2", cpu=1, ram=2, deadline=4, duration=1),
        Task(id="T3", cpu=3, ram=3, deadline=5, duration=2)
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

    print("PHASE 1 TEST")
    print("=" * 40)
    print(f"Tasks: {[t.id for t in tasks]}")
    print(f"Nodes: {[n.id for n in nodes]}")
    print(f"Execution costs: {exec_cost}")

    # Build graph
    graph_builder = FlowGraphBuilder()
    graph = graph_builder.build_basic_flow_graph(tasks, nodes, exec_cost)

    print(f"\nGraph nodes: {len(graph.nodes())}")
    print(f"Graph edges: {len(graph.edges())}")

    # Solve MCMF
    mcmf_solver = MinCostMaxFlow()
    assignments, total_cost = mcmf_solver.solve(graph)

    print(f"\nRaw assignments: {assignments}")
    print(f"Total cost: {total_cost}")

    # Convert to final format
    final_assignments = {}
    for task_key, node_key in assignments.items():
        task_id = str(task_key).replace('task_', '')
        node_id = str(node_key).replace('node_', '')
        final_assignments[task_id] = {'node': node_id, 'start_time': None}

    print(f"Final assignments: {final_assignments}")

    return final_assignments, total_cost

if __name__ == "__main__":
    test_phase1()