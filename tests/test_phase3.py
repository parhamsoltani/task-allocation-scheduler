"""Unit tests for Phase 3: Dynamic reallocation"""

import unittest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from core.models import Task, Node, Schedule, DynamicEvent, EventType
from phases.phase3_dynamic import Phase3Dynamic

class TestPhase3Dynamic(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.phase3 = Phase3Dynamic()
        
        self.tasks = [
            Task(id="T1", cpu=2, ram=2, deadline=3, duration=1),
            Task(id="T2", cpu=1, ram=1, deadline=4, duration=1),
            Task(id="T3", cpu=2, ram=2, deadline=5, duration=2)
        ]
        
        self.nodes = [
            Node(id="N1", cpu_capacity=3, ram_capacity=3),
            Node(id="N2", cpu_capacity=3, ram_capacity=3),
            Node(id="N3", cpu_capacity=2, ram_capacity=2)
        ]
        
        self.exec_cost = {
            "T1": {"N1": 4, "N2": 6, "N3": 8},
            "T2": {"N1": 3, "N2": 2, "N3": 4},
            "T3": {"N1": 5, "N2": 7, "N3": 9}
        }
        
        self.current_schedule = Schedule(
            assignments={
                "T1": {"node": "N1", "start_time": 0},
                "T2": {"node": "N2", "start_time": 1},
                "T3": {"node": "N1", "start_time": 2}
            },
            total_cost=11,
            valid=True
        )
        
        self.time_slots = [0, 1, 2, 3, 4]
        self.node_capacity_per_time = {
            "N1": {0: 3, 1: 3, 2: 3, 3: 3, 4: 3},
            "N2": {0: 3, 1: 3, 2: 3, 3: 3, 4: 3},
            "N3": {0: 2, 1: 2, 2: 2, 3: 2, 4: 2}
        }
    
    def test_node_failure_handling(self):
        """Test handling of node failure events"""
        events = [
            DynamicEvent(
                type=EventType.NODE_FAILURE,
                time=1,
                data={"node": "N2", "time": 1}
            )
        ]
        
        result = self.phase3.run(
            self.current_schedule, self.tasks, self.nodes,
            self.exec_cost, events, self.time_slots,
            self.node_capacity_per_time, []
        )
        
        # T2 was on N2, should be reassigned
        self.assertIn("T2", result['reassigned_tasks'])
        
        # N2 should not appear in updated schedule
        for assignment in result['updated_schedule'].values():
            self.assertNotEqual(assignment['node'], "N2")
    
    def test_new_task_arrival(self):
        """Test handling of new task arrivals"""
        events = [
            DynamicEvent(
                type=EventType.NEW_TASK,
                time=1,
                data={
                    "task": {
                        "id": "T4",
                        "cpu": 1,
                        "ram": 1,
                        "deadline": 4,
                        "duration": 1,
                        "exec_cost": {"N1": 2, "N2": 3, "N3": 1}
                    }
                }
            )
        ]
        
        result = self.phase3.run(
            self.current_schedule, self.tasks, self.nodes,
            self.exec_cost, events, self.time_slots,
            self.node_capacity_per_time, []
        )
        
        # New task should be in reassigned list
        self.assertIn("T4", result['reassigned_tasks'])
        
        # New task should have an assignment
        self.assertIn("T4", result['updated_schedule'])
    
    def test_capacity_change(self):
        """Test handling of capacity changes"""
        events = [
            DynamicEvent(
                type=EventType.CAPACITY_CHANGE,
                time=2,
                data={
                    "N1": {"2": 1, "3": 1}  # Reduce N1 capacity at time 2 and 3
                }
            )
        ]
        
        result = self.phase3.run(
            self.current_schedule, self.tasks, self.nodes,
            self.exec_cost, events, self.time_slots,
            self.node_capacity_per_time, []
        )
        
        # T3 might need to be reassigned due to reduced capacity
        # Check that the solution is still valid or tasks are marked as failed
        self.assertTrue(
            len(result['updated_schedule']) + len(result['failed_tasks']) == len(self.tasks)
        )
    
    def test_multiple_events(self):
        """Test handling multiple simultaneous events"""
        events = [
            DynamicEvent(
                type=EventType.NODE_FAILURE,
                time=1,
                data={"node": "N2", "time": 1}
            ),
            DynamicEvent(
                type=EventType.NEW_TASK,
                time=1,
                data={
                    "task": {
                        "id": "T4",
                        "cpu": 1,
                        "ram": 1,
                        "deadline": 4,
                        "duration": 1,
                        "exec_cost": {"N1": 2, "N3": 1}
                    }
                }
            )
        ]
        
        result = self.phase3.run(
            self.current_schedule, self.tasks, self.nodes,
            self.exec_cost, events, self.time_slots,
            self.node_capacity_per_time, []
        )
        
        # Both T2 (due to node failure) and T4 (new task) should be handled
        self.assertIn("T2", result['reassigned_tasks'])
        self.assertIn("T4", result['reassigned_tasks'])
        
        # Change penalty should reflect the disruption
        self.assertGreater(result['change_penalty'], 0)
    
    def test_infeasible_reallocation(self):
        """Test handling of scenarios where reallocation is not possible"""
        # Remove all alternative nodes
        events = [
            DynamicEvent(
                type=EventType.NODE_FAILURE,
                time=0,
                data={"node": "N1", "time": 0}
            ),
            DynamicEvent(
                type=EventType.NODE_FAILURE,
                time=0,
                data={"node": "N2", "time": 0}
            ),
            DynamicEvent(
                type=EventType.NODE_FAILURE,
                time=0,
                data={"node": "N3", "time": 0}
            )
        ]
        
        result = self.phase3.run(
            self.current_schedule, self.tasks, self.nodes,
            self.exec_cost, events, self.time_slots,
            self.node_capacity_per_time, []
        )
        
        # All tasks should fail
        self.assertEqual(len(result['failed_tasks']), len(self.tasks))

if __name__ == '__main__':
    unittest.main()