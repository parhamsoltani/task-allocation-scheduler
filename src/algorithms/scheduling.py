from typing import List, Dict, Tuple, Optional
from ..core.models import Task, Node, Assignment
import heapq

class TaskScheduler:
    def __init__(self):
        self.tasks = []
        self.nodes = []
        self.dependencies = {}
        
    def schedule_with_dependencies(self, tasks: List[Task], 
                                  assignments: Dict[str, str],
                                  dependencies: List[Tuple[str, str]],
                                  node_capacity_per_time: Dict[str, Dict[int, int]],
                                  time_slots: List[int]) -> Dict[str, Assignment]:
        """Schedule tasks considering dependencies and time constraints"""
        
        # Build dependency graph
        dep_graph = {task.id: [] for task in tasks}
        in_degree = {task.id: 0 for task in tasks}
        
        for before, after in dependencies:
            dep_graph[before].append(after)
            in_degree[after] += 1
        
        # Topological sort for scheduling order
        ready_tasks = [task_id for task_id, degree in in_degree.items() if degree == 0]
        scheduled = {}
        task_finish_times = {}
        
        # Track node usage per time slot
        node_usage = {node_id: {t: 0 for t in time_slots} 
                     for node_id in set(assignments.values())}
        
        while ready_tasks:
            task_id = ready_tasks.pop(0)
            node_id = assignments.get(task_id)
            
            if not node_id:
                continue
            
            # Find task object
            task = next((t for t in tasks if t.id == task_id), None)
            if not task:
                continue
            
            # Find earliest available time slot
            earliest_start = 0
            
            # Consider dependencies
            for dep_id in [d for d, a in dependencies if a == task_id]:
                if dep_id in task_finish_times:
                    earliest_start = max(earliest_start, task_finish_times[dep_id])
            
            # Find feasible start time
            start_time = self._find_feasible_start_time(
                task, node_id, earliest_start, 
                node_capacity_per_time, node_usage, time_slots
            )
            
            if start_time is not None:
                scheduled[task_id] = Assignment(
                    task_id=task_id,
                    node_id=node_id,
                    start_time=start_time
                )
                
                # Update finish time
                task_finish_times[task_id] = start_time + task.duration
                
                # Update node usage
                for t in range(start_time, start_time + task.duration):
                    if t in node_usage[node_id]:
                        node_usage[node_id][t] += task.cpu
                
                # Update ready tasks
                for next_task in dep_graph[task_id]:
                    in_degree[next_task] -= 1
                    if in_degree[next_task] == 0:
                        ready_tasks.append(next_task)
        
        return scheduled
    
    def _find_feasible_start_time(self, task: Task, node_id: str,
                                  earliest_start: int,
                                  node_capacity_per_time: Dict[str, Dict[int, int]],
                                  node_usage: Dict[str, Dict[int, int]],
                                  time_slots: List[int]) -> Optional[int]:
        """Find earliest feasible start time for task on node"""
        
        for start_time in range(earliest_start, max(time_slots) + 1):
            # Check if all required time slots are available
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
                
                # Check deadline
                if t >= task.deadline:
                    feasible = False
                    break
            
            if feasible:
                return start_time
        
        return None

class GreedyScheduler:
    """Greedy scheduling algorithm for comparison"""
    
    def schedule(self, tasks: List[Task], nodes: List[Node],
                exec_cost: Dict[str, Dict[str, float]]) -> Dict[str, str]:
        """Simple greedy assignment based on cost"""
        
        assignments = {}
        node_usage = {node.id: {'cpu': 0, 'ram': 0} for node in nodes}
        
        # Sort tasks by deadline (EDF - Earliest Deadline First)
        sorted_tasks = sorted(tasks, key=lambda t: t.deadline)
        
        for task in sorted_tasks:
            best_node = None
            best_cost = float('inf')
            
            for node in nodes:
                # Check capacity
                if (node_usage[node.id]['cpu'] + task.cpu <= node.cpu_capacity and
                    node_usage[node.id]['ram'] + task.ram <= node.ram_capacity):
                    
                    cost = exec_cost.get(task.id, {}).get(node.id, float('inf'))
                    if cost < best_cost:
                        best_cost = cost
                        best_node = node
            
            if best_node:
                assignments[task.id] = best_node.id
                node_usage[best_node.id]['cpu'] += task.cpu
                node_usage[best_node.id]['ram'] += task.ram
        
        return assignments