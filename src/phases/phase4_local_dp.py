from typing import List, Dict
from ..core.models import Task, NodeSchedule
from ..algorithms.dynamic_programming import DPScheduler

class Phase4LocalDP:
    def __init__(self):
        self.dp_scheduler = DPScheduler()
        
    def run(self, node_id: str, assigned_tasks: List[Task],
            resource_per_time: Dict[int, Dict[str, int]],
            time_slots: List[int]) -> NodeSchedule:
        """
        Phase 4: Local task scheduling using DP on individual nodes
        """
        
        # Use DP to find optimal local schedule
        schedule = self.dp_scheduler.schedule_node_tasks(
            node_id, assigned_tasks, resource_per_time, time_slots
        )
        
        return schedule
    
    def run_all_nodes(self, assignments: Dict[str, Dict],
                     tasks: List[Task], nodes: List[Node],
                     resource_per_time: Dict[str, Dict[int, Dict[str, int]]],
                     time_slots: List[int]) -> Dict[str, NodeSchedule]:
        """Run Phase 4 for all nodes"""
        
        # Group tasks by assigned node
        node_tasks = {node.id: [] for node in nodes}
        
        for task in tasks:
            if task.id in assignments:
                node_id = assignments[task.id]['node']
                if node_id in node_tasks:
                    node_tasks[node_id].append(task)
        
        # Schedule each node
        results = {}
        for node_id, tasks_list in node_tasks.items():
            if tasks_list:
                node_resource = resource_per_time.get(node_id, {})
                results[node_id] = self.run(
                    node_id, tasks_list, node_resource, time_slots
                )
        
        return results