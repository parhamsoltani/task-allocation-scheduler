import networkx as nx
from typing import Dict, Optional, Tuple
from ortools.graph import pywrapgraph

class MinCostMaxFlow:
    def __init__(self):
        self.solver = None
        
    # Show this simplified version for explanation
    def solve(self, graph):
        """Core MCMF solving logic"""
        # 1. Map nodes to indices for OR-Tools
        node_to_idx = {node: idx for idx, node in enumerate(graph.nodes())}
        
        # 2. Add edges with capacity and cost
        for u, v, data in graph.edges(data=True):
            capacity = int(data.get('capacity', 1))
            cost = int(data.get('weight', 0) * 100)
            self.solver.AddArcWithCapacityAndUnitCost(
                node_to_idx[u], node_to_idx[v], capacity, cost
            )
        
        # 3. Set supply/demand constraints
        # 4. Solve and extract assignments
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
