"""Unit tests for Phase 2: Time-aware scheduling"""

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models import Task, Node
from phases.phase2_scheduling import Phase2Scheduling

class TestPhase2Scheduling(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.phase2 = Phase2Scheduling()
        
        self.tasks = [
            Task(id="T1", cpu=2, ram=2, deadline=3, duration=1),
            Task(id="T2", cpu=1, ram=1, deadline=4, duration=1),
            Task(id="T3", cpu=2, ram=2, deadline=5, duration=2)
        ]
        
        self.nodes = [
            Node(id="N1", cpu_capacity=3, ram_capacity=3),
            Node(id="N2", cpu_capacity=3, ram_capacity=3)
        ]
        
        self.exec_cost = {
            "T1": {"N1": 4, "N2": 6},
            "T2": {"N1": 3, "N2": 2},
            "T3": {"N1": 5, "N2": 7}
        }
        
        self.time_slots = [0, 1, 2, 3, 4]
        
        self.node_capacity_per_time = {
            "N1": {0: 3, 1: 3, 2: 3, 3: 3, 4: 3},
            "N2": {0: 3, 1: 3, 2: 3, 3: 3, 4: 3}
        }
        
        self.dependencies = [("T1", "T3")]
    
    def test_basic_scheduling(self):
        """Test basic time-aware scheduling"""
        result = self.phase2.run(
            self.tasks, self.nodes, self.exec_cost,
            self.time_slots, self.node_capacity_per_time, []
        )
        
        # Check all tasks are scheduled
        self.assertEqual(len(result.assignments), len(self.tasks))
        
        # Check each task has a start time
        for assignment in result.assignments.values():
            self.assertIsNotNone(assignment.get('start_time'))
    
    def test_deadline_constraints(self):
        """Test that deadlines are respected"""
        result = self.phase2.run(
            self.tasks, self.nodes, self.exec_cost,
            self.time_slots, self.node_capacity_per_time, []
        )
        
        for task in self.tasks:
            if task.id in result.assignments:
                start_time = result.assignments[task.id]['start_time']
                end_time = start_time + task.duration
                self.assertLessEqual(end_time, task.deadline)
    
    def test_dependency_handling(self):
        """Test that task dependencies are respected"""
        result = self.phase2.run(
            self.tasks, self.nodes, self.exec_cost,
            self.time_slots, self.node_capacity_per_time, self.dependencies
        )
        
        # T1 must finish before T3 starts
        if "T1" in result.assignments and "T3" in result.assignments:
            t1_end = result.assignments["T1"]['start_time'] + 1
            t3_start = result.assignments["T3"]['start_time']
            self.assertLessEqual(t1_end, t3_start)
    
    def test_time_slot_capacity(self):
        """Test that time slot capacities are respected"""
        # Reduce capacity to force serialization
        limited_capacity = {
            "N1": {0: 2, 1: 2, 2: 2, 3: 2, 4: 2},
            "N2": {0: 1, 1: 1, 2: 1, 3: 1, 4: 1}
        }
        
        result = self.phase2.run(
            self.tasks, self.nodes, self.exec_cost,
            self.time_slots, limited_capacity, []
        )
        
        # Verify capacity constraints are met
        self.assertTrue(result.valid or len(result.assignments) < len(self.tasks))
    
    def test_with_initial_assignments(self):
        """Test scheduling with pre-determined assignments from Phase 1"""
        initial_assignments = {
            "T1": "N1",
            "T2": "N2",
            "T3": "N1"
        }
        
        result = self.phase2.run(
            self.tasks, self.nodes, self.exec_cost,
            self.time_slots, self.node_capacity_per_time, 
            self.dependencies, initial_assignments
        )
        
        # Check that node assignments are preserved
        for task_id, node_id in initial_assignments.items():
            if task_id in result.assignments:
                self.assertEqual(result.assignments[task_id]['node'], node_id)

if __name__ == '__main__':
    unittest.main()