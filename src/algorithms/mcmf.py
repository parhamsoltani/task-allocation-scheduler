import networkx as nx
from typing import Dict, Optional, Tuple

class MinCostMaxFlow:
    def __init__(self):
        pass

    def solve(self, graph: nx.DiGraph) -> Tuple[Dict[str, str], float]:
        """Solve MCMF using NetworkX min_cost_flow"""
        try:
            # Use NetworkX's built-in min cost flow
            flow_dict = nx.min_cost_flow(graph, demand='demand', capacity='capacity', weight='weight')

            # Extract assignments and calculate cost
            assignments = {}
            total_cost = 0.0

            for u in flow_dict:
                for v in flow_dict[u]:
                    flow = flow_dict[u][v]
                    if flow > 0:
                        # Check if this is a task->node assignment
                        if str(u).startswith('task_') and str(v).startswith('node_'):
                            assignments[u] = v
                            # Get cost from graph edge
                            if graph.has_edge(u, v):
                                cost = graph[u][v].get('weight', 0)
                                total_cost += flow * cost

            return assignments, total_cost

        except Exception as e:
            print(f"NetworkX min_cost_flow failed: {e}")
            return self._greedy_fallback(graph)

    def _greedy_fallback(self, graph: nx.DiGraph) -> Tuple[Dict[str, str], float]:
        """Simple greedy assignment fallback"""
        assignments = {}
        total_cost = 0.0

        # Get tasks and nodes
        tasks = [n for n in graph.nodes() if str(n).startswith('task_')]
        nodes = [n for n in graph.nodes() if str(n).startswith('node_')]

        # Simple assignment: each task to cheapest available node
        for task in tasks:
            best_node = None
            best_cost = float('inf')

            for node in nodes:
                if graph.has_edge(task, node):
                    cost = graph[task][node].get('weight', 0)
                    if cost < best_cost:
                        best_cost = cost
                        best_node = node

            if best_node and best_cost != float('inf'):
                assignments[task] = best_node
                total_cost += best_cost

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
                if str(u).startswith('task_') and str(v).startswith('node_'):
                    assignments[u] = v

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
