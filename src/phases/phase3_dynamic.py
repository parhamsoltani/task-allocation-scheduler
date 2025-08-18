from typing import List, Dict, Optional
from ..core.models import Task, Node, Schedule, DynamicEvent, EventType
from ..phases.phase1_mcmf import Phase1MCMF
from ..phases.phase2_scheduling import Phase2Scheduling
import copy

class Phase3Dynamic:
    def __init__(self):
        self.phase1 = Phase1MCMF()
        self.phase2 = Phase2Scheduling()
        
    def run(self, current_schedule: Schedule,
            tasks: List[Task], nodes: List[Node],
            exec_cost: Dict[str, Dict[str, float]],
            events: List[DynamicEvent],
            time_slots: List[int],
            node_capacity_per_time: Dict[str, Dict[int, int]],
            dependencies: List[Tuple[str, str]]) -> Dict:
        """
        Phase 3: Dynamic reallocation in response to runtime events
        """
        
        # Copy current state
        active_tasks = copy.deepcopy(tasks)
        active_nodes = copy.deepcopy(nodes)
        updated_assignments = copy.deepcopy(current_schedule.assignments)
        
        reassigned_tasks = []
        failed_tasks = []
        change_penalty = 0
        
        # Process each event
        for event in events:
            if event.type == EventType.NODE_FAILURE:
                # Handle node failure
                failed_node_id = event.data['node']
                current_time = event.data['time']
                
                # Find tasks assigned to failed node
                affected_tasks = [
                    task_id for task_id, assign in updated_assignments.items()
                    if assign['node'] == failed_node_id and 
                    (assign.get('start_time', 0) >= current_time or 
                     assign.get('start_time', 0) + self._get_task_duration(task_id, active_tasks) > current_time)
                ]
                
                # Remove failed node
                active_nodes = [n for n in active_nodes if n.id != failed_node_id]
                
                # Remove node from capacity map
                if failed_node_id in node_capacity_per_time:
                    del node_capacity_per_time[failed_node_id]
                
                # Reassign affected tasks
                for task_id in affected_tasks:
                    task = next((t for t in active_tasks if t.id == task_id), None)
                    if task:
                        # Try to find alternative node
                        new_assignment = self._find_alternative_assignment(
                            task, active_nodes, exec_cost, current_time,
                            node_capacity_per_time, time_slots
                        )
                        
                        if new_assignment:
                            updated_assignments[task_id] = new_assignment
                            reassigned_tasks.append(task_id)
                            change_penalty += 1
                        else:
                            failed_tasks.append(task_id)
                            if task_id in updated_assignments:
                                del updated_assignments[task_id]
                
            elif event.type == EventType.NEW_TASK:
                # Handle new task arrival
                new_task_data = event.data['task']
                new_task = Task(
                    id=new_task_data['id'],
                    cpu=new_task_data['cpu'],
                    ram=new_task_data['ram'],
                    deadline=new_task_data['deadline'],
                    duration=new_task_data.get('duration', 1)
                )
                
                active_tasks.append(new_task)
                
                # Update execution cost matrix
                if 'exec_cost' in new_task_data:
                    for node_id, cost in new_task_data['exec_cost'].items():
                        if new_task.id not in exec_cost:
                            exec_cost[new_task.id] = {}
                        exec_cost[new_task.id][node_id] = cost
                
                # Find assignment for new task
                new_assignment = self._find_alternative_assignment(
                    new_task, active_nodes, exec_cost, event.time,
                    node_capacity_per_time, time_slots
                )
                
                if new_assignment:
                    updated_assignments[new_task.id] = new_assignment
                    reassigned_tasks.append(new_task.id)
                else:
                    failed_tasks.append(new_task.id)
            
            elif event.type == EventType.CAPACITY_CHANGE:
                # Handle capacity changes
                for node_id, time_updates in event.data.items():
                    for time_slot, new_capacity in time_updates.items():
                        if node_id not in node_capacity_per_time:
                            node_capacity_per_time[node_id] = {}
                        node_capacity_per_time[node_id][int(time_slot)] = new_capacity
        
        # Recalculate total cost
        total_cost = 0
        for task_id, assignment in updated_assignments.items():
            cost = exec_cost.get(task_id, {}).get(assignment['node'], 0)
            total_cost += cost
        
        return {
            'updated_schedule': updated_assignments,
            'reassigned_tasks': reassigned_tasks,
            'failed_tasks': failed_tasks,
            'total_cost': total_cost,
            'change_penalty': change_penalty
        }
    
    def _get_task_duration(self, task_id: str, tasks: List[Task]) -> int:
        """Get duration of a task"""
        task = next((t for t in tasks if t.id == task_id), None)
        return task.duration if task else 1
    
    def _find_alternative_assignment(self, task: Task, nodes: List[Node],
                                    exec_cost: Dict[str, Dict[str, float]],
                                    current_time: int,
                                    node_capacity_per_time: Dict[str, Dict[int, int]],
                                    time_slots: List[int]) -> Optional[Dict]:
        """Find alternative assignment for a task"""
        
        best_assignment = None
        best_cost = float('inf')
        
        for node in nodes:
            # Check if node can handle task
            if task.cpu > node.cpu_capacity or task.ram > node.ram_capacity:
                continue
            
            # Find feasible start time
            for start_time in range(current_time, max(time_slots) + 1):
                if start_time + task.duration > task.deadline:
                    break
                
                # Check capacity at all required time slots
                feasible = True
                for t in range(start_time, start_time + task.duration):
                    if t not in time_slots:
                        feasible = False
                        break
                    
                    available = node_capacity_per_time.get(node.id, {}).get(t, 0)
                    if available < task.cpu:
                        feasible = False
                        break
                
                if feasible:
                    cost = exec_cost.get(task.id, {}).get(node.id, float('inf'))
                    if cost < best_cost:
                        best_cost = cost
                        best_assignment = {
                            'node': node.id,
                            'start_time': start_time
                        }
                    break  # Found feasible time for this node
        
        return best_assignment