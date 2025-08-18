"""Example scenarios for testing the task allocation system"""

import random
from typing import Dict, List, Tuple
import json

def create_simple_scenario() -> Dict:
    """Create a simple scenario with few tasks and nodes"""
    return {
        "name": "Simple Scenario",
        "description": "Basic scenario with 3 tasks and 2 nodes",
        "tasks": [
            {"id": "T1", "cpu": 2, "ram": 4, "deadline": 3, "duration": 1},
            {"id": "T2", "cpu": 1, "ram": 2, "deadline": 4, "duration": 1},
            {"id": "T3", "cpu": 3, "ram": 3, "deadline": 5, "duration": 2}
        ],
        "nodes": [
            {"id": "N1", "cpu_capacity": 5, "ram_capacity": 6},
            {"id": "N2", "cpu_capacity": 4, "ram_capacity": 5}
        ],
        "exec_cost": {
            "T1": {"N1": 4, "N2": 6},
            "T2": {"N1": 3, "N2": 2},
            "T3": {"N1": 5, "N2": 7}
        },
        "time_slots": list(range(6)),
        "node_capacity_per_time": {
            "N1": {str(i): 5 for i in range(6)},
            "N2": {str(i): 4 for i in range(6)}
        },
        "dependencies": []
    }

def create_complex_scenario() -> Dict:
    """Create a complex scenario with dependencies and time constraints"""
    return {
        "name": "Complex Scenario",
        "description": "Scenario with 10 tasks, 4 nodes, and complex dependencies",
        "tasks": [
            {"id": f"T{i}", "cpu": random.randint(1, 3), 
             "ram": random.randint(1, 4), 
             "deadline": random.randint(5, 10),
             "duration": random.randint(1, 3)}
            for i in range(1, 11)
        ],
        "nodes": [
            {"id": f"N{i}", 
             "cpu_capacity": random.randint(4, 8),
             "ram_capacity": random.randint(4, 8)}
            for i in range(1, 5)
        ],
        "exec_cost": {
            f"T{i}": {
                f"N{j}": random.randint(1, 10)
                for j in range(1, 5)
            }
            for i in range(1, 11)
        },
        "time_slots": list(range(12)),
        "node_capacity_per_time": {
            f"N{i}": {str(t): random.randint(3, 6) for t in range(12)}
            for i in range(1, 5)
        },
        "dependencies": [
            ("T1", "T3"), ("T1", "T4"), ("T2", "T5"),
            ("T3", "T6"), ("T4", "T7"), ("T5", "T8"),
            ("T6", "T9"), ("T7", "T9"), ("T8", "T10")
        ]
    }

def create_stress_test_scenario() -> Dict:
    """Create a stress test scenario with many tasks and nodes"""
    n_tasks = 100
    n_nodes = 20
    
    tasks = []
    for i in range(1, n_tasks + 1):
        tasks.append({
            "id": f"T{i}",
            "cpu": random.randint(1, 4),
            "ram": random.randint(1, 6),
            "deadline": random.randint(10, 50),
            "duration": random.randint(1, 5)
        })
    
    nodes = []
    for i in range(1, n_nodes + 1):
        nodes.append({
            "id": f"N{i}",
            "cpu_capacity": random.randint(8, 16),
            "ram_capacity": random.randint(8, 16)
        })
    
    exec_cost = {}
    for task in tasks:
        exec_cost[task["id"]] = {}
        for node in nodes:
            # Some task-node combinations are infeasible
            if random.random() > 0.2:
                exec_cost[task["id"]][node["id"]] = random.randint(1, 20)
            else:
                exec_cost[task["id"]][node["id"]] = 999999
    
    # Create random dependencies (DAG)
    dependencies = []
    for i in range(1, n_tasks):
        if random.random() > 0.7:  # 30% chance of dependency
            j = random.randint(i + 1, min(i + 10, n_tasks))
            dependencies.append((f"T{i}", f"T{j}"))
    
    return {
        "name": "Stress Test Scenario",
        "description": f"Large scenario with {n_tasks} tasks and {n_nodes} nodes",
        "tasks": tasks,
        "nodes": nodes,
        "exec_cost": exec_cost,
        "time_slots": list(range(60)),
        "node_capacity_per_time": {
            node["id"]: {str(t): node["cpu_capacity"] for t in range(60)}
            for node in nodes
        },
        "dependencies": dependencies
    }

def create_real_world_scenario() -> Dict:
    """Create a scenario mimicking real-world cloud computing workload"""
    
    # Define task types (web server, database, batch processing, ML training)
    task_types = {
        "web": {"cpu": (1, 2), "ram": (2, 4), "duration": (1, 2)},
        "db": {"cpu": (2, 4), "ram": (4, 8), "duration": (2, 4)},
        "batch": {"cpu": (4, 8), "ram": (4, 8), "duration": (5, 10)},
        "ml": {"cpu": (8, 16), "ram": (8, 16), "duration": (10, 20)}
    }
    
    # Define node types (small, medium, large instances)
    node_types = {
        "small": {"cpu": 4, "ram": 8, "cost_factor": 1},
        "medium": {"cpu": 8, "ram": 16, "cost_factor": 1.8},
        "large": {"cpu": 16, "ram": 32, "cost_factor": 3.5}
    }
    
    # Create tasks
    tasks = []
    task_id = 1
    for task_type, props in task_types.items():
        count = {"web": 20, "db": 5, "batch": 10, "ml": 3}[task_type]
        for _ in range(count):
            tasks.append({
                "id": f"T{task_id}_{task_type}",
                "cpu": random.randint(*props["cpu"]),
                "ram": random.randint(*props["ram"]),
                "deadline": random.randint(20, 100),
                "duration": random.randint(*props["duration"]),
                "type": task_type
            })
            task_id += 1
    
    # Create nodes
    nodes = []
    node_id = 1
    for node_type, props in node_types.items():
        count = {"small": 10, "medium": 5, "large": 2}[node_type]
        for _ in range(count):
            nodes.append({
                "id": f"N{node_id}_{node_type}",
                "cpu_capacity": props["cpu"],
                "ram_capacity": props["ram"],
                "type": node_type,
                "cost_factor": props["cost_factor"]
            })
            node_id += 1
    
    # Create execution costs based on node type and task requirements
    exec_cost = {}
    for task in tasks:
        exec_cost[task["id"]] = {}
        for node in nodes:
            base_cost = task["cpu"] + task["ram"]
            node_cost_factor = node["cost_factor"]
            
            # Check if node can handle task
            if task["cpu"] <= node["cpu_capacity"] and task["ram"] <= node["ram_capacity"]:
                # Prefer matching task types to node sizes
                if (task["type"] in ["web", "db"] and node["type"] == "small") or \
                   (task["type"] == "batch" and node["type"] == "medium") or \
                   (task["type"] == "ml" and node["type"] == "large"):
                    cost = base_cost * node_cost_factor * 0.8  # 20% discount for good match
                else:
                    cost = base_cost * node_cost_factor
                exec_cost[task["id"]][node["id"]] = round(cost, 2)
            else:
                exec_cost[task["id"]][node["id"]] = 999999
    
    # Create realistic dependencies
    dependencies = []
    
    # Web tasks depend on DB tasks
    web_tasks = [t["id"] for t in tasks if "web" in t["id"]]
    db_tasks = [t["id"] for t in tasks if "db" in t["id"]]
    for web_task in web_tasks[:10]:
        if db_tasks:
            db_task = random.choice(db_tasks)
            dependencies.append((db_task, web_task))
    
    # Some batch tasks depend on other batch tasks (pipeline)
    batch_tasks = [t["id"] for t in tasks if "batch" in t["id"]]
    for i in range(len(batch_tasks) - 1):
        if random.random() > 0.5:
            dependencies.append((batch_tasks[i], batch_tasks[i + 1]))
    
    # ML tasks might depend on batch preprocessing
    ml_tasks = [t["id"] for t in tasks if "ml" in t["id"]]
    for ml_task in ml_tasks:
        if batch_tasks:
            batch_task = random.choice(batch_tasks)
            dependencies.append((batch_task, ml_task))
    
    # Dynamic events
    events = [
        {
            "type": "node_failure",
            "time": 30,
            "node": random.choice([n["id"] for n in nodes if "small" in n["id"]])
        },
        {
            "type": "new_task",
            "time": 25,
            "task": {
                "id": "T_urgent_web",
                "cpu": 2,
                "ram": 4,
                "deadline": 35,
                "duration": 2,
                "exec_cost": {
                    node["id"]: 5 for node in nodes 
                    if node["cpu_capacity"] >= 2 and node["ram_capacity"] >= 4
                }
            }
        }
    ]
    
    return {
        "name": "Real-World Cloud Scenario",
        "description": "Mimics actual cloud computing workload with different task and node types",
        "tasks": tasks,
        "nodes": nodes,
        "exec_cost": exec_cost,
        "time_slots": list(range(120)),
        "node_capacity_per_time": {
            node["id"]: {str(t): node["cpu_capacity"] for t in range(120)}
            for node in nodes
        },
        "dependencies": dependencies,
        "events": events
    }

def save_scenario(scenario: Dict, filename: str):
    """Save scenario to JSON file"""
    with open(filename, 'w') as f:
        json.dump(scenario, f, indent=2)

def load_scenario(filename: str) -> Dict:
    """Load scenario from JSON file"""
    with open(filename, 'r') as f:
        return json.load(f)

def generate_random_scenario(n_tasks: int = 20, n_nodes: int = 5,
                           dependency_prob: float = 0.2) -> Dict:
    """Generate a random scenario with specified parameters"""
    
    tasks = []
    for i in range(1, n_tasks + 1):
        tasks.append({
            "id": f"T{i}",
            "cpu": random.randint(1, 4),
            "ram": random.randint(1, 6),
            "deadline": random.randint(5, 30),
            "duration": random.randint(1, 5)
        })
    
    nodes = []
    for i in range(1, n_nodes + 1):
        nodes.append({
            "id": f"N{i}",
            "cpu_capacity": random.randint(4, 12),
            "ram_capacity": random.randint(6, 16)
        })
    
    exec_cost = {}
    for task in tasks:
        exec_cost[task["id"]] = {}
        for node in nodes:
            if task["cpu"] <= node["cpu_capacity"] and task["ram"] <= node["ram_capacity"]:
                exec_cost[task["id"]][node["id"]] = random.randint(1, 15)
            else:
                exec_cost[task["id"]][node["id"]] = 999999
    
    dependencies = []
    for i in range(1, n_tasks):
        if random.random() < dependency_prob:
            j = random.randint(i + 1, n_tasks)
            dependencies.append((f"T{i}", f"T{j}"))
    
    max_deadline = max(task["deadline"] for task in tasks)
    time_slots = list(range(max_deadline + 10))
    
    return {
        "name": f"Random Scenario ({n_tasks} tasks, {n_nodes} nodes)",
        "description": f"Randomly generated scenario with {len(dependencies)} dependencies",
        "tasks": tasks,
        "nodes": nodes,
        "exec_cost": exec_cost,
        "time_slots": time_slots,
        "node_capacity_per_time": {
            node["id"]: {str(t): node["cpu_capacity"] for t in time_slots}
            for node in nodes
        },
        "dependencies": dependencies
    }

if __name__ == "__main__":
    # Generate and save example scenarios
    scenarios = {
        "simple": create_simple_scenario(),
        "complex": create_complex_scenario(),
        "stress": create_stress_test_scenario(),
        "realworld": create_real_world_scenario()
    }
    
    for name, scenario in scenarios.items():
        filename = f"scenario_{name}.json"
        save_scenario(scenario, filename)
        print(f"Saved {scenario['name']} to {filename}")
        print(f"  - Tasks: {len(scenario['tasks'])}")
        print(f"  - Nodes: {len(scenario['nodes'])}")
        print(f"  - Dependencies: {len(scenario.get('dependencies', []))}")
        print()