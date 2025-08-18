"""Unit tests for Phase 4: Local DP scheduling"""

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models import Task, Node
from phases.phase4_local_dp import Phase4LocalDP

class TestPhase4LocalDP(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.phase4 = Phase4LocalDP()
        
        self.node_id = "N1"
        
        self.tasks = [
            Task(id="T1", cpu=2, ram=2, deadline=2, duration=1),
            Task(id="T2", cpu=1, ram=1, deadline=3, duration=1),
            Task(id="T3", cpu=2, ram=1, deadline=4, duration=2)
        ]
        
        self.resource_per_time = {
            0: {"cpu": 3, "ram": 3},
            1: {"cpu": 3, "ram": 3},
            2: {"cpu": 3, "ram": 3},
            3: {"cpu": 3, "ram": 3}
        }
        
        self.time_slots = [0, 1, 2, 3]
    
    def test_basic_local_scheduling(self):
        """Test basic DP scheduling on a single node"""
        result = self.phase4.run(
            self.node_id, self.tasks, 
            self.resource_per_time, self.time_slots
        )
        
        # Check that result has required fields
        self.assertEqual(result.node_id, self.node_id)
        self.assertIsNotNone(result.task_schedules)
        self.assertIsNotNone(result.total_idle_time)
        self.assertIsNotNone(result.penalty_cost)
    
    def test_deadline_optimization(self):
        """Test that DP optimizes for meeting deadlines"""
        result = self.phase4.run(
            self.node_id, self.tasks,
            self.resource_per_time, self.time_slots
        )
        
        # Count tasks that meet deadlines
        met_deadlines = sum(
            1 for _, (_, meets) in result.task_schedules.items() if meets
        )
        
        # Should try to maximize tasks meeting deadlines
        self.assertGreater(met_deadlines, 0)
    
    def test_resource_constraints(self):
        """Test that resource constraints are respected"""
        # Create tasks that can't run simultaneously
        conflicting_tasks = [
            Task(id="T1", cpu=3, ram=2, deadline=2, duration=1),
            Task(id="T2", cpu=3, ram=2, deadline=2, duration=1)
        ]
        
        result = self.phase4.run(
            self.node_id, conflicting_tasks,
            self.resource_per_time, self.time_slots
        )
        
        # Tasks should be scheduled at different times
        if len(result.task_schedules) == 2:
            times = [schedule[0] for schedule in result.task_schedules.values()]
            self.assertNotEqual(times[0], times[1])
    
    def test_idle_time_calculation(self):
        """Test idle time calculation"""
        # Single short task should have idle time
        single_task = [Task(id="T1", cpu=1, ram=1, deadline=4, duration=1)]
        
        result = self.phase4.run(
            self.node_id, single_task,
            self.resource_per_time, self.time_slots
        )
        
        # Should have 3 idle slots (4 total - 1 used)
        self.assertEqual(result.total_idle_time, 3)
    
    def test_penalty_calculation(self):
        """Test penalty cost calculation for missed deadlines"""
        # Task with impossible deadline
        impossible_task = [
            Task(id="T1", cpu=2, ram=2, deadline=0, duration=2)
        ]
        
        result = self.phase4.run(
            self.node_id, impossible_task,
            self.resource_per_time, self.time_slots
        )
        
        # Should have penalty for missing deadline
        self.assertGreater(result.penalty_cost, 0)
    
    def test_multiple_nodes_scheduling(self):
        """Test scheduling across multiple nodes"""
        nodes = [
            Node(id="N1", cpu_capacity=3, ram_capacity=3),
            Node(id="N2", cpu_capacity=2, ram_capacity=2)
        ]
        
        assignments = {
            "T1": {"node": "N1", "start_time": None},
            "T2": {"node": "N1", "start_time": None},
            "T3": {"node": "N2", "start_time": None}
        }
        
        all_resource_per_time = {
            "N1": self.resource_per_time,
            "N2": {
                0: {"cpu": 2, "ram": 2},
                1: {"cpu": 2, "ram": 2},
                2: {"cpu": 2, "ram": 2},
                3: {"cpu": 2, "ram": 2}
            }
        }
        
        results = self.phase4.run_all_nodes(
            assignments, self.tasks, nodes,
            all_resource_per_time, self.time_slots
        )
        
        # Should have results for both nodes with assigned tasks
        self.assertIn("N1", results)
        self.assertIn("N2", results)
        
        # N1 should have 2 tasks scheduled
        self.assertEqual(len(results["N1"].task_schedules), 2)
        
        # N2 should have 1 task scheduled
        self.assertEqual(len(results["N2"].task_schedules), 1)

if __name__ == '__main__':
    unittest.main()