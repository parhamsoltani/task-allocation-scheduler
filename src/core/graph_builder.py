import networkx as nx
from typing import List, Dict, Optional, Tuple
from .models import Task, Node

class FlowGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.source = "SOURCE"
        self.sink = "SINK"
        
    def build_basic_flow_graph(self, tasks: List[Task], nodes: List[Node], 
                               exec_cost: Dict[str, Dict[str, float]]) -> nx.DiGraph:
        """Build basic flow graph for Phase 1 MCMF"""
        self.graph.clear()
        
        # Add source and sink
        self.graph.add_node(self.source, demand=-len(tasks))
        self.graph.add_node(self.sink, demand=len(tasks))
        
        # Add task and node vertices
        for task in tasks:
            self.graph.add_node(f"task_{task.id}", task=task)
            
        for node in nodes:
            self.graph.add_node(f"node_{node.id}", node=node)
        
        # Add edges from source to tasks
        for task in tasks:
            self.graph.add_edge(self.source, f"task_{task.id}", 
                               capacity=1, weight=0)
        
        # Add edges from tasks to nodes (if feasible)
        for task in tasks:
            for node in nodes:
                if self._is_feasible(task, node):
                    cost = exec_cost.get(task.id, {}).get(node.id, float('inf'))
                    if cost != float('inf'):
                        self.graph.add_edge(f"task_{task.id}", f"node_{node.id}",
                                          capacity=1, weight=cost)
        
        # Add edges from nodes to sink
        for node in nodes:
            max_tasks = min(node.cpu_capacity // 1, node.ram_capacity // 1)  # Simplified
            self.graph.add_edge(f"node_{node.id}", self.sink,
                               capacity=max_tasks, weight=0)
        
        return self.graph
    
    def build_time_expanded_graph(self, tasks: List[Task], nodes: List[Node],
                                 exec_cost: Dict[str, Dict[str, float]],
                                 time_slots: List[int],
                                 node_capacity_per_time: Dict[str, Dict[int, int]],
                                 dependencies: List[Tuple[str, str]]) -> nx.DiGraph:
        """Build time-expanded flow graph for Phase 2"""
        self.graph.clear()
        
        # Calculate total flow needed
        total_flow = len(tasks)
        
        # Add source and sink
        self.graph.add_node(self.source, demand=-total_flow)
        self.graph.add_node(self.sink, demand=total_flow)
        
        # Add task nodes for each valid time slot
        for task in tasks:
            for t in time_slots:
                if t + task.duration <= task.deadline:
                    node_id = f"task_{task.id}_t{t}"
                    self.graph.add_node(node_id, task=task, time=t)
                    # Edge from source
                    self.graph.add_edge(self.source, node_id, capacity=1, weight=0)
        
        # Add node-time vertices
        for node in nodes:
            for t in time_slots:
                node_time_id = f"node_{node.id}_t{t}"
                capacity = node_capacity_per_time.get(node.id, {}).get(t, 0)
                self.graph.add_node(node_time_id, node=node, time=t, capacity=capacity)
                # Edge to sink
                self.graph.add_edge(node_time_id, self.sink, 
                                   capacity=capacity, weight=0)
        
        # Add task-to-node edges considering time and dependencies
        for task in tasks:
            for node in nodes:
                if self._is_feasible(task, node):
                    cost = exec_cost.get(task.id, {}).get(node.id, float('inf'))
                    if cost != float('inf'):
                        for t in time_slots:
                            if self._check_time_feasibility(task, t, dependencies, time_slots):
                                task_node_id = f"task_{task.id}_t{t}"
                                node_time_id = f"node_{node.id}_t{t}"
                                if task_node_id in self.graph and node_time_id in self.graph:
                                    self.graph.add_edge(task_node_id, node_time_id,
                                                      capacity=1, weight=cost)
        
        return self.graph
    
    def _is_feasible(self, task: Task, node: Node) -> bool:
        """Check if task can be assigned to node based on resources"""
        return task.cpu <= node.cpu_capacity and task.ram <= node.ram_capacity
    
    def _check_time_feasibility(self, task: Task, start_time: int, 
                                dependencies: List[Tuple[str, str]], 
                                time_slots: List[int]) -> bool:
        """Check if task can start at given time considering dependencies"""
        # Check deadline
        if start_time + task.duration > task.deadline:
            return False
        
        # Check if start time is valid
        if start_time not in time_slots:
            return False
        
        # Additional dependency checks would go here
        return True