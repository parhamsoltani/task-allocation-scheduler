from typing import List, Dict, Tuple, Optional
from ..core.models import Task, Node, Schedule, Assignment
from ..core.graph_builder import FlowGraphBuilder
from ..algorithms.mcmf import MinCostMaxFlow
from ..algorithms.scheduling import TaskScheduler

class Phase2Scheduling:
    def __init__(self):
        self.graph_builder = FlowGraphBuilder()
        self.mcmf_solver = MinCostMaxFlow()
        self.scheduler = TaskScheduler()
        
    def run(self, tasks: List[Task], nodes: List[Node],
            exec_cost: Dict[str, Dict[str, float]],
            time_slots: List[int],
            node_capacity_per_time: Dict[str, Dict[int, int]],
            dependencies: List[Tuple[str, str]],
            initial_assignments: Optional[Dict[str, str]] = None) -> Schedule:
        """
        Phase 2: Time-aware scheduling with dependencies
        """
        
        if initial_assignments:
            # Use assignments from Phase 1 and schedule them
            scheduled = self.scheduler.schedule_with_dependencies(
                tasks, initial_assignments, dependencies,
                node_capacity_per_time, time_slots
            )
            
            # Convert to output format
            assignments = {}
            total_cost = 0
            
            for task_id, assignment in scheduled.items():
                assignments[task_id] = {
                    'node': assignment.node_id,
                    'start_time': assignment.start_time
                }
                
                # Calculate cost
                task = next(t for t in tasks if t.id == task_id)
                cost = exec_cost.get(task_id, {}).get(assignment.node_id, 0)
                total_cost += cost
            
            return Schedule(
                assignments=assignments,
                total_cost=total_cost,
                valid=self._validate_schedule(assignments, tasks, dependencies)
            )
        else:
            # Build time-expanded graph and solve directly
            graph = self.graph_builder.build_time_expanded_graph(
                tasks, nodes, exec_cost, time_slots,
                node_capacity_per_time, dependencies
            )
            
            # Solve MCMF on time-expanded graph
            assignments, total_cost = self.mcmf_solver.solve(graph)
            
            # Parse time-stamped assignments
            schedule_assignments = {}
            for task_node, node_time in assignments.items():
                if '_t' in task_node:
                    task_id = task_node.split('_t')[0]
                    time_slot = int(task_node.split('_t')[1])
                    node_id = node_time.split('_t')[0]
                    
                    schedule_assignments[task_id] = {
                        'node': node_id,
                        'start_time': time_slot
                    }
            
            return Schedule(
                assignments=schedule_assignments,
                total_cost=total_cost,
                valid=self._validate_schedule(schedule_assignments, tasks, dependencies)
            )
    
    def _validate_schedule(self, assignments: Dict, tasks: List[Task],
                          dependencies: List[Tuple[str, str]]) -> bool:
        """Validate schedule meets all constraints"""
        
        # Check all tasks are scheduled
        if len(assignments) != len(tasks):
            return False
        
        # Check deadlines
        for task in tasks:
            if task.id not in assignments:
                return False
            
            start_time = assignments[task.id].get('start_time', 0)
            if start_time + task.duration > task.deadline:
                return False
        
        # Check dependencies
        for before, after in dependencies:
            if before not in assignments or after not in assignments:
                return False
            
            before_task = next(t for t in tasks if t.id == before)
            before_end = assignments[before]['start_time'] + before_task.duration
            after_start = assignments[after]['start_time']
            
            if before_end > after_start:
                return False
        
        return True