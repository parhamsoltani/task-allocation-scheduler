from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from enum import Enum

class EventType(Enum):
    NODE_FAILURE = "node_failure"
    NEW_TASK = "new_task"
    CAPACITY_CHANGE = "capacity_change"

@dataclass
class Task:
    id: str
    cpu: int
    ram: int
    deadline: int
    duration: int = 1
    dependencies: List[str] = field(default_factory=list)
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Task):
            return self.id == other.id
        return False

@dataclass
class Node:
    id: str
    cpu_capacity: int
    ram_capacity: int
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, Node):
            return self.id == other.id
        return False

@dataclass
class Assignment:
    task_id: str
    node_id: str
    start_time: Optional[int] = None
    
@dataclass
class Schedule:
    assignments: Dict[str, Assignment]
    total_cost: float
    valid: bool = True
    
@dataclass
class DynamicEvent:
    type: EventType
    time: int
    data: Dict

@dataclass
class NodeSchedule:
    node_id: str
    task_schedules: Dict[str, Tuple[int, bool]]  # task_id -> (start_time, meets_deadline)
    total_idle_time: int
    penalty_cost: float