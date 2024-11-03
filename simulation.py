from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import random
from typing import List, Dict, Optional
import matplotlib.pyplot as plt

class TaskStatus(Enum):
    IN_PROGRESS = "in_progress"
    READY_TO_DEPLOY = "ready_to_deploy"
    DEPLOYED = "deployed"
    FAILED = "failed"

@dataclass
class Task:
    id: int
    created_date: datetime
    complexity: int
    status: TaskStatus
    deploy_date: Optional[datetime] = None
    recovery_hours: float = 0
    dependencies: List[str] = None

SIMULATION_DEFAULTS = {
    # Team Parameters
    'team_size': 5,
    'avg_hourly_rate': 75,  # USD per hour
    
    # Task Generation
    'new_tasks_per_day': 3,
    'task_complexity_range': (1, 5),  # Story points
    
    # Business Parameters
    'hourly_revenue': 1000,  # USD per hour of normal operation
    'hourly_downtime_cost': 2000,  # USD per hour of system issues
    
    # Risk Parameters
    'base_deploy_failure_rate': 0.05,  # 5% chance of issues
    'weekend_recovery_multiplier': 3.0,  # Recovery takes 3x longer on weekends
    
    # Time Parameters
    'normal_recovery_hours': 2,
    'context_switch_cost_hours': 1,
    
    # Dependency Parameters
    'dependency_probability': 0.3,  # 30% chance a task needs another team
    'other_teams': [
        {
            'name': 'Backend Team',
            'task_completion_rate': 0.2,
            'allows_friday_deploys': False
        },
        {
            'name': 'Security Team',
            'task_completion_rate': 0.1,
            'allows_friday_deploys': False
        }
    ]
}

class DeploymentSimulation:
    def __init__(self, allow_friday_deploys: bool, params: dict = None, failure_cost_multiplier: float = 1.0):
        self.params = params or SIMULATION_DEFAULTS.copy()
        self.failure_cost_multiplier = failure_cost_multiplier
        self.allow_friday_deploys = allow_friday_deploys
        self.current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        self.tasks: List[Task] = []
        self.task_counter = 0
        self.total_cost = 0
        self.daily_costs = []
        self.metrics = {
            'failed_deploys': 0,
            'successful_deploys': 0,
            'delayed_tasks': 0,
            'total_recovery_hours': 0
        }
    
    def generate_daily_tasks(self):
        for _ in range(self.params['new_tasks_per_day']):
            self.task_counter += 1
            complexity = random.randint(
                self.params['task_complexity_range'][0],
                self.params['task_complexity_range'][1]
            )
            
            # Generate dependencies
            dependencies = []
            if random.random() < self.params['dependency_probability']:
                team = random.choice(self.params['other_teams'])
                dependencies.append(team['name'])
            
            task = Task(
                id=self.task_counter,
                created_date=self.current_date,
                complexity=complexity,
                status=TaskStatus.IN_PROGRESS,
                dependencies=dependencies
            )
            self.tasks.append(task)
    
    def should_deploy_today(self) -> bool:
        if self.current_date.weekday() == 4:  # Friday
            return self.allow_friday_deploys
        return True
    
    def calculate_deploy_risk(self) -> float:
        """Calculate probability of deployment failure"""
        return self.params['base_deploy_failure_rate']
    
    def calculate_recovery_time(self) -> float:
        """Calculate hours needed to recover from a failed deployment"""
        base_time = self.params['normal_recovery_hours']
        if self.current_date.weekday() in [4, 5, 6]:  # Fri, Sat, Sun
            return base_time * self.params['weekend_recovery_multiplier']
        return base_time
    
    def attempt_deployments(self):
        daily_cost = 0
        
        if not self.should_deploy_today():
            return daily_cost
        
        ready_tasks = [t for t in self.tasks if t.status == TaskStatus.READY_TO_DEPLOY]
        
        for task in ready_tasks:
            failure_chance = self.calculate_deploy_risk()
            
            if random.random() < failure_chance:
                task.status = TaskStatus.FAILED
                task.recovery_hours = self.calculate_recovery_time()
                self.metrics['failed_deploys'] += 1
                
                # Calculate failure costs with multiplier
                recovery_cost = (
                    task.recovery_hours * 
                    self.params['team_size'] * 
                    self.params['avg_hourly_rate'] *
                    self.failure_cost_multiplier
                )
                downtime_cost = (
                    task.recovery_hours * 
                    self.params['hourly_downtime_cost'] *
                    self.failure_cost_multiplier
                )
                daily_cost += recovery_cost + downtime_cost
                self.total_cost += recovery_cost + downtime_cost
                self.metrics['total_recovery_hours'] += task.recovery_hours
            else:
                task.status = TaskStatus.DEPLOYED
                task.deploy_date = self.current_date
                self.metrics['successful_deploys'] += 1
        
        return daily_cost
    
    def progress_tasks(self):
        for task in self.tasks:
            if task.status == TaskStatus.IN_PROGRESS:
                # Check dependencies
                if task.dependencies:
                    for dep in task.dependencies:
                        team = next(t for t in self.params['other_teams'] if t['name'] == dep)
                        if random.random() < team['task_completion_rate']:
                            task.dependencies.remove(dep)
                
                # Only progress if no dependencies remain
                if not task.dependencies and random.random() < 0.3:
                    task.status = TaskStatus.READY_TO_DEPLOY
    
    def calculate_daily_delay_cost(self):
        daily_cost = 0
        ready_tasks = [t for t in self.tasks if t.status == TaskStatus.READY_TO_DEPLOY]
        if ready_tasks and not self.should_deploy_today():
            delay_cost = (
                len(ready_tasks) * 
                self.params['hourly_revenue'] * 
                24  # Full day delay
            )
            daily_cost += delay_cost
            self.total_cost += delay_cost
            self.metrics['delayed_tasks'] += len(ready_tasks)
        return daily_cost
    
    def simulate_day(self):
        self.generate_daily_tasks()
        self.progress_tasks()
        deploy_cost = self.attempt_deployments()
        delay_cost = self.calculate_daily_delay_cost()
        self.daily_costs.append(deploy_cost + delay_cost)
        self.current_date += timedelta(days=1)
    
    def run_simulation(self, days: int) -> Dict:
        for _ in range(days):
            self.simulate_day()
        
        return {
            'total_cost': self.total_cost,
            'daily_costs': self.daily_costs,
            'metrics': self.metrics,
            'allow_friday_deploys': self.allow_friday_deploys
        }

def compare_deployment_strategies(days: int = 90, scenarios: List[float] = [1.0, 10.0]):
    plt.figure(figsize=(15, 10))
    
    for idx, failure_multiplier in enumerate(scenarios):
        # Run simulations for this scenario
        friday_sim = DeploymentSimulation(
            allow_friday_deploys=True, 
            failure_cost_multiplier=failure_multiplier
        )
        no_friday_sim = DeploymentSimulation(
            allow_friday_deploys=False,
            failure_cost_multiplier=failure_multiplier
        )
        
        friday_results = friday_sim.run_simulation(days)
        no_friday_results = no_friday_sim.run_simulation(days)
        
        # Print results for this scenario
        print(f"\n=== Scenario {idx + 1}: Failure Cost Multiplier {failure_multiplier}x ===")
        print("\nFriday Deployments Allowed:")
        print(f"Total Cost: ${friday_results['total_cost']:,.2f}")
        print(f"Failed Deploys: {friday_results['metrics']['failed_deploys']}")
        print(f"Successful Deploys: {friday_results['metrics']['successful_deploys']}")
        print(f"Delayed Tasks: {friday_results['metrics']['delayed_tasks']}")
        print(f"Total Recovery Hours: {friday_results['metrics']['total_recovery_hours']:.1f}")
        
        print("\nNo Friday Deployments:")
        print(f"Total Cost: ${no_friday_results['total_cost']:,.2f}")
        print(f"Failed Deploys: {no_friday_results['metrics']['failed_deploys']}")
        print(f"Successful Deploys: {no_friday_results['metrics']['successful_deploys']}")
        print(f"Delayed Tasks: {no_friday_results['metrics']['delayed_tasks']}")
        print(f"Total Recovery Hours: {no_friday_results['metrics']['total_recovery_hours']:.1f}")
        
        # Create subplot for this scenario
        plt.subplot(2, 1, idx + 1)
        
        # Calculate cumulative costs
        friday_cumulative = [sum(friday_results['daily_costs'][:i+1]) for i in range(len(friday_results['daily_costs']))]
        no_friday_cumulative = [sum(no_friday_results['daily_costs'][:i+1]) for i in range(len(no_friday_results['daily_costs']))]
        
        # Plot cumulative costs over time
        plt.plot(range(days), friday_cumulative, label='Friday Deploys', color='blue')
        plt.plot(range(days), no_friday_cumulative, label='No Friday Deploys', color='red')
        
        plt.title(f'Cumulative Costs Over Time (Failure Cost {failure_multiplier}x)')
        plt.xlabel('Days')
        plt.ylabel('Cumulative Cost ($)')
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.legend()
        
        # Format y-axis labels as currency
        plt.gca().yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'${x:,.0f}'))
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    # Set random seed for reproducibility
    random.seed(42)
    
    # Run simulation for 90 days with two scenarios
    compare_deployment_strategies(90, [1.0, 1000.0])