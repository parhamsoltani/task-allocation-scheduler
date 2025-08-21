from typing import List, Dict, Tuple
import sys
import os

# Add the src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from core.models import Task, Node, Schedule
from core.graph_builder import FlowGraphBuilder
from algorithms.mcmf import MinCostMaxFlow

class Phase1MCMF:
    def __init__(self):
        self.graph_builder = FlowGraphBuilder()
        self.mcmf_solver = MinCostMaxFlow()
        
    def run(self, tasks: List[Task], nodes: List[Node],
            exec_cost: Dict[str, Dict[str, float]]) -> Schedule:
        """
        Phase 1: Initial task-to-node allocation using MCMF
        """
        
        # Build flow graph
        graph = self.graph_builder.build_basic_flow_graph(tasks, nodes, exec_cost)
        
        # Solve MCMF
        assignments, total_cost = self.mcmf_solver.solve(graph)
        
        # Convert to Assignment objects
        assignment_objects = {}
        for task_key, node_key in assignments.items():
            # Handle both 'task_T1' and 'task_T1_t0' formats
            task_id = str(task_key).replace('task_', '')
            if '_t' in task_id:
                task_id = task_id.split('_t')[0]

            node_id = str(node_key).replace('node_', '')
            if '_t' in node_id:
                node_id = node_id.split('_t')[0]

            assignment_objects[task_id] = {
                'node': node_id,
                'start_time': None
            }

        return Schedule(
            assignments=assignment_objects,
            total_cost=total_cost,
            valid=len(assignment_objects) == len(tasks)
        )
    
    def validate_solution(self, schedule: Schedule, tasks: List[Task], 
                         nodes: List[Node]) -> bool:
        """Validate that the solution respects all constraints"""
        
        # Check all tasks are assigned
        if len(schedule.assignments) != len(tasks):
            return False
        
        # Check node capacities
        node_usage = {node.id: {'cpu': 0, 'ram': 0} for node in nodes}
        
        for task in tasks:
            if task.id not in schedule.assignments:
                return False
            
            node_id = schedule.assignments[task.id]['node']
            if node_id not in node_usage:
                return False
                
            node_usage[node_id]['cpu'] += task.cpu
            node_usage[node_id]['ram'] += task.ram
        
        for node in nodes:
            if node_usage[node.id]['cpu'] > node.cpu_capacity:
                return False
            if node_usage[node.id]['ram'] > node.ram_capacity:
                return False
        
        return True
