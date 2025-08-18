"""Unit tests for Phase 1: MCMF allocation"""

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models import Task, Node
from phases.phase1_mcmf import Phase1MCMF

class TestPhase1MCMF(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.phase1 = Phase1MCMF()
        
        # Create test tasks
        self.tasks = [
            Task(id="T1", cpu=2, ram=4, deadline=3, duration=1),
            Task(id="T2", cpu=1, ram=2, deadline=4, duration=1),
            Task(id="T3", cpu=3, ram=3, deadline=5, duration=2)
        ]
        
        # Create test nodes
        self.nodes = [
            Node(id="N1", cpu_capacity=5, ram_capacity=6),
            Node(id="N2", cpu_capacity=4, ram_capacity=5)
        ]
        
        # Create execution cost matrix
        self.exec_cost = {
            "T1": {"N1": 4, "N2": 6},
            "T2": {"N1": 3, "N2": 2},
            "T3": {"N1": 5, "N2": 7}
        }
    
    def test_basic_allocation(self):
        """Test basic task allocation"""
        result = self.phase1.run(self.tasks, self.nodes, self.exec_cost)
        
        # Check that all tasks are assigned
        self.assertEqual(len(result.assignments), len(self.tasks))
        
        # Check that the solution is valid
        self.assertTrue(result.valid)
        
        # Check that total cost is reasonable
        self.assertGreater(result.total_cost, 0)
        self.assertLess(result.total_cost, 100)
    
    def test_capacity_constraints(self):
        """Test that capacity constraints are respected"""
        result = self.phase1.run(self.tasks, self.nodes, self.exec_cost)
        
        # Validate the solution
        is_valid = self.phase1.validate_solution(result, self.tasks, self.nodes)
        self.assertTrue(is_valid)
    
    def test_infeasible_allocation(self):
        """Test handling of infeasible allocation scenarios"""
        # Create tasks that exceed total capacity
        large_tasks = [
            Task(id="T1", cpu=10, ram=10, deadline=3, duration=1),
            Task(id="T2", cpu=10, ram=10, deadline=4, duration=1)
        ]
        
        result = self.phase1.run(large_tasks, self.nodes, self.exec_cost)
        
        # Should not be able to assign all tasks
        self.assertLess(len(result.assignments), len(large_tasks))
    
    def test_single_node(self):
        """Test allocation with single node"""
        single_node = [Node(id="N1", cpu_capacity=10, ram_capacity=10)]
        
        result = self.phase1.run(self.tasks, single_node, self.exec_cost)
        
        # All tasks should be assigned to the single node if feasible
        for assignment in result.assignments.values():
            self.assertEqual(assignment['node'], "N1")
    
    def test_cost_optimization(self):
        """Test that the algorithm optimizes for minimum cost"""
        # Create scenario where cost optimization matters
        cost_matrix = {
            "T1": {"N1": 10, "N2": 1},  # T1 cheaper on N2
            "T2": {"N1": 1, "N2": 10},  # T2 cheaper on N1
            "T3": {"N1": 5, "N2": 5}    # T3 same cost
        }
        
        result = self.phase1.run(self.tasks, self.nodes, cost_matrix)
        
        # Check assignments follow cost optimization
        if "T1" in result.assignments:
            self.assertEqual(result.assignments["T1"]['node'], "N2")
        if "T2" in result.assignments:
            self.assertEqual(result.assignments["T2"]['node'], "N1")

if __name__ == '__main__':
    unittest.main()