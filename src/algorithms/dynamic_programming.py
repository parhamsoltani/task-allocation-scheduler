from typing import List, Dict, Tuple, Optional
from ..core.models import Task, NodeSchedule
import numpy as np

class DPScheduler:
    def __init__(self):
        self.memo = {}

    def schedule_node_tasks(self, node_id: str, tasks: List[Task],
                           resource_per_time: Dict[int, Dict[str, int]],
                           time_slots: List[int]) -> NodeSchedule:
        """Use DP to find optimal local schedule for tasks on a node"""

        n_tasks = len(tasks)
        n_slots = len(time_slots)

        # DP table: dp[time][task_mask] = (min_penalty, schedule)
        # task_mask is a bitmask representing which tasks have been scheduled
        dp = {}

        # Initialize
        dp[(0, 0)] = (0, {})

        # Fill DP table
        for t in range(n_slots):
            for mask in range(1 << n_tasks):
                if (t, mask) not in dp:
                    continue

                current_penalty, current_schedule = dp[(t, mask)]

                # Try scheduling each unscheduled task
                for i in range(n_tasks):
                    if mask & (1 << i):  # Task already scheduled
                        continue

                    task = tasks[i]

                    # Check if task can be scheduled at time t
                    if self._can_schedule_task(task, t, resource_per_time, time_slots):
                        new_mask = mask | (1 << i)
                        end_time = t + task.duration

                        # Calculate penalty
                        penalty = 0
                        if end_time > task.deadline:
                            penalty = (end_time - task.deadline) * 10  # Penalty weight

                        new_penalty = current_penalty + penalty

                        # Update schedule
                        new_schedule = current_schedule.copy()
                        new_schedule[task.id] = (t, end_time <= task.deadline)

                        # Update DP table
                        next_time = min(end_time, n_slots)
                        if next_time < n_slots:
                            key = (next_time, new_mask)
                            if key not in dp or dp[key][0] > new_penalty:
                                dp[key] = (new_penalty, new_schedule)

                # Option to not schedule anything at this time
                if t + 1 < n_slots:
                    key = (t + 1, mask)
                    if key not in dp or dp[key][0] > current_penalty + 1:  # +1 for idle penalty
                        dp[key] = (current_penalty + 1, current_schedule)

        # Find best final state
        best_penalty = float('inf')
        best_schedule = {}

        for (t, mask), (penalty, schedule) in dp.items():
            if penalty < best_penalty:
                best_penalty = penalty
                best_schedule = schedule

        # Calculate idle time
        scheduled_slots = set()
        for task_id, (start_time, _) in best_schedule.items():
            task = next(t for t in tasks if t.id == task_id)
            for t in range(start_time, start_time + task.duration):
                scheduled_slots.add(t)

        idle_time = len(time_slots) - len(scheduled_slots)

        return NodeSchedule(
            node_id=node_id,
            task_schedules=best_schedule,
            total_idle_time=idle_time,
            penalty_cost=best_penalty
        )

    def _can_schedule_task(self, task: Task, start_time: int,
                          resource_per_time: Dict[int, Dict[str, int]],
                          time_slots: List[int]) -> bool:
        """Check if task can be scheduled at given start time"""

        for t in range(start_time, start_time + task.duration):
            if t >= len(time_slots):
                return False

            available = resource_per_time.get(t, {})
            if available.get('cpu', 0) < task.cpu:
                return False
            if available.get('ram', 0) < task.ram:
                return False

        return True

class IntervalDP:
    """Alternative DP formulation using interval scheduling"""

    def __init__(self):
        self.tasks = []
        self.intervals = []

    def schedule_intervals(self, tasks: List[Task],
                          max_time: int) -> Tuple[List[Task], float]:
        """Schedule tasks as intervals to maximize value/minimize cost"""

        # Sort tasks by finish time
        sorted_tasks = sorted(tasks, key=lambda t: t.deadline)

        n = len(sorted_tasks)

        # dp[i] = minimum cost to schedule tasks 0..i-1
        dp = [0] * (n + 1)
        parent = [-1] * (n + 1)

        for i in range(1, n + 1):
            task = sorted_tasks[i - 1]

            # Option 1: Don't schedule task i-1
            dp[i] = dp[i - 1] + 100  # Penalty for not scheduling
            parent[i] = i - 1

            # Option 2: Schedule task i-1
            # Find latest task that doesn't conflict
            j = i - 1
            while j > 0:
                prev_task = sorted_tasks[j - 1]
                if prev_task.deadline <= task.deadline - task.duration:
                    break
                j -= 1

            cost = dp[j]  # No additional cost for scheduling
            if cost < dp[i]:
                dp[i] = cost
                parent[i] = j

        # Reconstruct solution
        scheduled = []
        i = n
        while i > 0:
            if parent[i] != i - 1:  # Task was scheduled
                scheduled.append(sorted_tasks[i - 1])
            i = parent[i]

        return scheduled, dp[n]