"""Utility functions for the task allocation system"""

import json
import csv
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import networkx as nx
import matplotlib.pyplot as plt
from .models import Task, Node, Schedule, Assignment

def validate_input(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate input data structure and constraints
    Returns (is_valid, list_of_errors)
    """
    errors = []
    
    # Check required fields
    required_fields = ['tasks', 'nodes', 'exec_cost']
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    if errors:
        return False, errors
    
    # Validate tasks
    task_ids = set()
    for task in data['tasks']:
        if 'id' not in task:
            errors.append("Task missing 'id' field")
        elif task['id'] in task_ids:
            errors.append(f"Duplicate task ID: {task['id']}")
        else:
            task_ids.add(task['id'])
        
        for field in ['cpu', 'ram', 'deadline']:
            if field not in task:
                errors.append(f"Task {task.get('id', '?')} missing '{field}' field")
            elif not isinstance(task[field], (int, float)) or task[field] < 0:
                errors.append(f"Task {task.get('id', '?')} has invalid '{field}' value")
    
    # Validate nodes
    node_ids = set()
    for node in data['nodes']:
        if 'id' not in node:
            errors.append("Node missing 'id' field")
        elif node['id'] in node_ids:
            errors.append(f"Duplicate node ID: {node['id']}")
        else:
            node_ids.add(node['id'])
        
        for field in ['cpu_capacity', 'ram_capacity']:
            if field not in node:
                errors.append(f"Node {node.get('id', '?')} missing '{field}' field")
            elif not isinstance(node[field], (int, float)) or node[field] < 0:
                errors.append(f"Node {node.get('id', '?')} has invalid '{field}' value")
    
    # Validate execution costs
    for task_id, costs in data['exec_cost'].items():
        if task_id not in task_ids:
            errors.append(f"Execution cost for unknown task: {task_id}")
        for node_id, cost in costs.items():
            if node_id not in node_ids:
                errors.append(f"Execution cost for unknown node: {node_id}")
            if not isinstance(cost, (int, float)) or cost < 0:
                errors.append(f"Invalid execution cost for {task_id}->{node_id}")
    
    # Validate dependencies if present
    if 'dependencies' in data:
        for dep in data['dependencies']:
            if 'before' not in dep or 'after' not in dep:
                errors.append("Dependency missing 'before' or 'after' field")
            elif dep['before'] not in task_ids:
                errors.append(f"Dependency references unknown task: {dep['before']}")
            elif dep['after'] not in task_ids:
                errors.append(f"Dependency references unknown task: {dep['after']}")
    
    return len(errors) == 0, errors

def calculate_metrics(schedule: Schedule, tasks: List[Task], 
                     nodes: List[Node]) -> Dict[str, Any]:
    """Calculate performance metrics for a schedule"""
    metrics = {
        'total_cost': schedule.total_cost,
        'tasks_scheduled': len(schedule.assignments),
        'tasks_total': len(tasks),
        'completion_rate': len(schedule.assignments) / len(tasks) if tasks else 0,
        'node_utilization': {},
        'makespan': 0,
        'average_task_delay': 0,
        'deadline_violations': 0
    }
    
    # Calculate node utilization
    node_usage = {node.id: {'cpu': 0, 'ram': 0, 'tasks': 0} for node in nodes}
    task_delays = []
    
    for task in tasks:
        if task.id in schedule.assignments:
            assignment = schedule.assignments[task.id]
            node_id = assignment.get('node')
            start_time = assignment.get('start_time', 0)
            
            if node_id in node_usage:
                node_usage[node_id]['cpu'] += task.cpu
                node_usage[node_id]['ram'] += task.ram
                node_usage[node_id]['tasks'] += 1
            
            # Calculate makespan
            end_time = start_time + task.duration
            metrics['makespan'] = max(metrics['makespan'], end_time)
            
            # Check deadline violations
            if end_time > task.deadline:
                metrics['deadline_violations'] += 1
                task_delays.append(end_time - task.deadline)
            else:
                task_delays.append(0)
    
    # Calculate utilization percentages
    for node in nodes:
        if node.id in node_usage:
            usage = node_usage[node.id]
            metrics['node_utilization'][node.id] = {
                'cpu_util': usage['cpu'] / node.cpu_capacity if node.cpu_capacity > 0 else 0,
                'ram_util': usage['ram'] / node.ram_capacity if node.ram_capacity > 0 else 0,
                'task_count': usage['tasks']
            }
    
    # Calculate average delay
    if task_delays:
        metrics['average_task_delay'] = sum(task_delays) / len(task_delays)
    
    return metrics

def export_schedule(schedule: Schedule, filepath: str, format: str = 'json'):
    """Export schedule to file in specified format"""
    if format == 'json':
        with open(filepath, 'w') as f:
            json.dump({
                'assignments': schedule.assignments,
                'total_cost': schedule.total_cost,
                'valid': schedule.valid,
                'timestamp': datetime.now().isoformat()
            }, f, indent=2)
    
    elif format == 'csv':
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Task ID', 'Node ID', 'Start Time', 'Cost'])
            for task_id, assignment in schedule.assignments.items():
                writer.writerow([
                    task_id,
                    assignment.get('node'),
                    assignment.get('start_time', 'N/A'),
                    'N/A'  # Cost per assignment would need to be tracked
                ])
    
    else:
        raise ValueError(f"Unsupported format: {format}")

def import_schedule(filepath: str) -> Schedule:
    """Import schedule from file"""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    return Schedule(
        assignments=data['assignments'],
        total_cost=data['total_cost'],
        valid=data.get('valid', True)
    )

def visualize_schedule(schedule: Schedule, tasks: List[Task], 
                      nodes: List[Node], save_path: Optional[str] = None):
    """Create a Gantt chart visualization of the schedule"""
    import matplotlib.patches as mpatches
    
    fig, ax = plt.subplots(figsize=(12, 6))
    
    # Color map for tasks
    colors = plt.cm.Set3(range(len(tasks)))
    task_colors = {task.id: colors[i] for i, task in enumerate(tasks)}
    
    # Node positions on y-axis
    node_positions = {node.id: i for i, node in enumerate(nodes)}
    
    # Plot tasks
    for task in tasks:
        if task.id in schedule.assignments:
            assignment = schedule.assignments[task.id]
            node_id = assignment.get('node')
            start_time = assignment.get('start_time', 0)
            
            if node_id in node_positions:
                y_pos = node_positions[node_id]
                rect = mpatches.Rectangle(
                    (start_time, y_pos - 0.4),
                    task.duration, 0.8,
                    facecolor=task_colors[task.id],
                    edgecolor='black',
                    linewidth=1
                )
                ax.add_patch(rect)
                
                # Add task label
                ax.text(start_time + task.duration/2, y_pos,
                       task.id, ha='center', va='center',
                       fontsize=8, fontweight='bold')
    
    # Set axis labels and limits
    ax.set_ylim(-0.5, len(nodes) - 0.5)
    ax.set_yticks(range(len(nodes)))
    ax.set_yticklabels([node.id for node in nodes])
    ax.set_xlabel('Time')
    ax.set_ylabel('Nodes')
    ax.set_title('Task Schedule Gantt Chart')
    ax.grid(True, alpha=0.3)
    
    # Add legend
    legend_elements = [mpatches.Patch(facecolor=color, edgecolor='black', label=task_id)
                      for task_id, color in task_colors.items()]
    ax.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.15, 1))
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()

def create_dependency_graph(tasks: List[Task], dependencies: List[Tuple[str, str]],
                           save_path: Optional[str] = None):
    """Visualize task dependencies as a directed graph"""
    G = nx.DiGraph()
    
    # Add nodes
    for task in tasks:
        G.add_node(task.id, cpu=task.cpu, ram=task.ram, deadline=task.deadline)
    
    # Add edges
    for before, after in dependencies:
        G.add_edge(before, after)
    
    # Create layout
    pos = nx.spring_layout(G, k=2, iterations=50)
    
    # Draw graph
    plt.figure(figsize=(10, 8))
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', 
                          node_size=1500, alpha=0.8)
    nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
    nx.draw_networkx_edges(G, pos, edge_color='gray', 
                          arrows=True, arrowsize=20, arrowstyle='->')
    
    # Add node attributes as labels
    node_labels = {}
    for task in tasks:
        node_labels[task.id] = f"CPU:{task.cpu}\nRAM:{task.ram}\nDL:{task.deadline}"
    
    pos_below = {k: (v[0], v[1]-0.1) for k, v in pos.items()}
    nx.draw_networkx_labels(G, pos_below, node_labels, font_size=8)
    
    plt.title("Task Dependency Graph")
    plt.axis('off')
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
    else:
        plt.show()

def calculate_communication_cost(task1: Task, task2: Task, 
                                 node1: str, node2: str,
                                 bandwidth_matrix: Optional[Dict] = None) -> float:
    """Calculate communication cost between two tasks on different nodes"""
    if node1 == node2:
        return 0.0  # No communication cost for same node
    
    # Default communication cost
    base_cost = 1.0
    
    # Use bandwidth matrix if provided
    if bandwidth_matrix and node1 in bandwidth_matrix and node2 in bandwidth_matrix[node1]:
        bandwidth = bandwidth_matrix[node1][node2]
        if bandwidth > 0:
            # Assume some data size based on task RAM requirements
            data_size = (task1.ram + task2.ram) / 2
            base_cost = data_size / bandwidth
    
    return base_cost