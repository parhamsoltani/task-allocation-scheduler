import networkx as nx
from typing import Dict, Optional, Tuple
from ortools.graph import pywrapgraph

class MinCostMaxFlow:
    def __init__(self):
        self.solver = None
        
    def solve(self, graph: nx.DiGraph) -> Tuple[Dict[str, str], float]:
        """Solve MCMF using OR-Tools"""
        # Create solver
        self.solver = pywrapgraph.SimpleMinCostFlow()
        
        # Map nodes to indices
        node_to_idx = {node: idx for idx, node in enumerate(graph.nodes())}
        idx_to_node = {idx: node for node, idx in node_to_idx.items()}
        
        # Add edges to solver
        for u, v, data in graph.edges(data=True):
            self.solver.AddArcWithCapacityAndUnitCost(
                node_to_idx[u],
                node_to_idx[v],
                data.get('capacity', 1),
                int(data.get('weight', 0) * 100)  # Scale for integer costs
            )
        
        # Set supplies (negative demand = supply)
        for node, data in graph.nodes(data=True):
            if 'demand' in data:
                self.solver.SetNodeSupply(node_to_idx[node], -data['demand'])
        
        # Solve
        status = self.solver.Solve()
        
        if status != self.solver.OPTIMAL:
            return {}, float('inf')
        
        # Extract solution
        assignments = {}
        total_cost = 0
        
        for arc in range(self.solver.NumArcs()):
            if self.solver.Flow(arc) > 0:
                tail = idx_to_node[self.solver.Tail(arc)]
                head = idx_to_node[self.solver.Head(arc)]
                
                # Check if this is a task-to-node assignment
                if tail.startswith('task_') and head.startswith('node_'):
                    task_id = tail.replace('task_', '').split('_t')[0]
                    node_id = head.replace('node_', '').split('_t')[0]
                    assignments[task_id] = node_id
                    total_cost += self.solver.UnitCost(arc) * self.solver.Flow(arc) / 100
        
        return assignments, total_cost

class SuccessiveShortestPath:
    """Alternative MCMF implementation using successive shortest path"""
    
    def __init__(self):
        self.graph = None
        self.flow = {}
        
    def solve(self, graph: nx.DiGraph) -> Tuple[Dict[str, str], float]:
        """Solve using successive shortest path algorithm"""
        self.graph = graph.copy()
        self.flow = {(u, v): 0 for u, v in self.graph.edges()}
        
        # Find source and sink
        source = None
        sink = None
        for node, data in self.graph.nodes(data=True):
            if 'demand' in data:
                if data['demand'] < 0:
                    source = node
                elif data['demand'] > 0:
                    sink = node
        
        if not source or not sink:
            return {}, float('inf')
        
        total_cost = 0
        assignments = {}
        
        # Build residual graph
        residual = self._build_residual_graph()
        
        while True:
            # Find shortest path in residual graph
            try:
                path = nx.shortest_path(residual, source, sink, weight='weight')
            except nx.NetworkXNoPath:
                break
            
            # Find minimum capacity along path
            min_cap = float('inf')
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                if residual.has_edge(u, v):
                    min_cap = min(min_cap, residual[u][v]['capacity'])
            
            if min_cap == float('inf') or min_cap <= 0:
                break
            
            # Update flow along path
            for i in range(len(path) - 1):
                u, v = path[i], path[i + 1]
                
                # Update flow
                if (u, v) in self.flow:
                    self.flow[(u, v)] += min_cap
                    total_cost += min_cap * self.graph[u][v]['weight']
                else:
                    self.flow[(v, u)] -= min_cap
                    total_cost -= min_cap * self.graph[v][u]['weight']
                
                # Extract assignments
                if u.startswith('task_') and v.startswith('node_'):
                    task_id = u.replace('task_', '')
                    node_id = v.replace('node_', '')
                    assignments[task_id] = node_id
            
            # Update residual graph
            residual = self._build_residual_graph()
        
        return assignments, total_cost
    
    def _build_residual_graph(self) -> nx.DiGraph:
        """Build residual graph based on current flow"""
        residual = nx.DiGraph()
        
        for (u, v), flow_value in self.flow.items():
            if self.graph.has_edge(u, v):
                capacity = self.graph[u][v]['capacity']
                weight = self.graph[u][v]['weight']
                
                # Forward edge
                if flow_value < capacity:
                    residual.add_edge(u, v, capacity=capacity-flow_value, weight=weight)
                
                # Backward edge
                if flow_value > 0:
                    residual.add_edge(v, u, capacity=flow_value, weight=-weight)
        
        # Add edges with no flow
        for u, v, data in self.graph.edges(data=True):
            if (u, v) not in self.flow:
                residual.add_edge(u, v, capacity=data['capacity'], weight=data['weight'])
        
        return residual