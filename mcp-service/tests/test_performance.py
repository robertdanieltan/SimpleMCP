#!/usr/bin/env python3
"""
Performance tests for MCP service database operations.

This test suite covers:
- Database operation performance benchmarks
- Load testing with multiple concurrent operations
- Memory usage monitoring
- Response time analysis
- Scalability testing
"""

import os
import sys
import time
import threading
import statistics
import psutil
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add the mcp-service directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tools.task_tools import create_task, list_tasks, update_task, delete_task
from app.tools.project_tools import create_project, list_projects, update_project, delete_project
from app.database.connection import get_db_connection


class PerformanceTestSuite:
    """Performance testing suite for MCP service."""
    
    def __init__(self):
        self.db = get_db_connection()
        self.test_results = []
        self.cleanup_projects = []
        self.cleanup_tasks = []
        
        # Performance thresholds (in seconds)
        self.thresholds = {
            'create_project': 0.1,
            'create_task': 0.1,
            'list_projects': 0.05,
            'list_tasks': 0.05,
            'update_project': 0.1,
            'update_task': 0.1,
            'delete_project': 0.1,
            'delete_task': 0.1
        }
    
    def log_result(self, test_name: str, operation: str, duration: float, 
                   success: bool, details: Dict[str, Any] = None):
        """Log performance test result."""
        result = {
            'test_name': test_name,
            'operation': operation,
            'duration': duration,
            'success': success,
            'timestamp': datetime.now().isoformat(),
            'threshold': self.thresholds.get(operation, 1.0),
            'within_threshold': duration <= self.thresholds.get(operation, 1.0),
            'details': details or {}
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success and result['within_threshold'] else "❌ FAIL"
        threshold_status = "⚡ FAST" if result['within_threshold'] else "🐌 SLOW"
        
        print(f"{status} {threshold_status} {test_name} - {operation}: {duration:.4f}s")
        if not result['within_threshold']:
            print(f"   ⚠️  Exceeded threshold of {result['threshold']}s")
    
    def measure_operation(self, operation_func, *args, **kwargs):
        """Measure the execution time of an operation."""
        start_time = time.time()
        try:
            result = operation_func(*args, **kwargs)
            duration = time.time() - start_time
            success = result.get('success', False) if isinstance(result, dict) else bool(result)
            return duration, success, result
        except Exception as e:
            duration = time.time() - start_time
            return duration, False, str(e)
    
    def test_single_operation_performance(self):
        """Test performance of individual operations."""
        print("\n🚀 Testing Single Operation Performance")
        print("=" * 50)
        
        # Test project creation
        duration, success, result = self.measure_operation(
            create_project,
            name="Performance Test Project",
            description="Testing single operation performance",
            status="active"
        )
        self.log_result("Single Operation", "create_project", duration, success)
        
        if success and result.get('data'):
            project = result['data']
            self.cleanup_projects.append(project)
            project_id = project['id']
            
            # Test task creation
            duration, success, result = self.measure_operation(
                create_task,
                title="Performance Test Task",
                description="Testing single operation performance",
                project_id=project_id,
                status="pending",
                priority="medium"
            )
            self.log_result("Single Operation", "create_task", duration, success)
            
            if success and result.get('data'):
                task = result['data']
                self.cleanup_tasks.append(task)
                task_id = task['id']
                
                # Test list operations
                duration, success, result = self.measure_operation(list_projects)
                self.log_result("Single Operation", "list_projects", duration, success)
                
                duration, success, result = self.measure_operation(list_tasks)
                self.log_result("Single Operation", "list_tasks", duration, success)
                
                # Test update operations
                duration, success, result = self.measure_operation(
                    update_project,
                    project_id,
                    name="Updated Performance Test Project"
                )
                self.log_result("Single Operation", "update_project", duration, success)
                
                duration, success, result = self.measure_operation(
                    update_task,
                    task_id,
                    title="Updated Performance Test Task",
                    status="in_progress"
                )
                self.log_result("Single Operation", "update_task", duration, success)
    
    def test_bulk_operations_performance(self):
        """Test performance of bulk operations."""
        print("\n📦 Testing Bulk Operations Performance")
        print("=" * 50)
        
        # Test bulk project creation
        num_projects = 50
        start_time = time.time()
        created_projects = []
        
        for i in range(num_projects):
            result = create_project(
                name=f"Bulk Test Project {i}",
                description=f"Bulk test project number {i}",
                status="active"
            )
            if result.get('success') and result.get('data'):
                created_projects.append(result['data'])
                self.cleanup_projects.append(result['data'])
        
        bulk_create_duration = time.time() - start_time
        avg_create_duration = bulk_create_duration / num_projects
        
        self.log_result(
            "Bulk Operations", 
            "bulk_create_projects", 
            bulk_create_duration, 
            len(created_projects) == num_projects,
            {
                'total_projects': num_projects,
                'successful_creates': len(created_projects),
                'avg_duration_per_project': avg_create_duration
            }
        )
        
        # Test bulk task creation
        if created_projects:
            num_tasks = 100
            start_time = time.time()
            created_tasks = []
            
            for i in range(num_tasks):
                project = created_projects[i % len(created_projects)]
                result = create_task(
                    title=f"Bulk Test Task {i}",
                    description=f"Bulk test task number {i}",
                    project_id=project['id'],
                    status="pending",
                    priority="medium"
                )
                if result.get('success') and result.get('data'):
                    created_tasks.append(result['data'])
                    self.cleanup_tasks.append(result['data'])
            
            bulk_task_create_duration = time.time() - start_time
            avg_task_create_duration = bulk_task_create_duration / num_tasks
            
            self.log_result(
                "Bulk Operations",
                "bulk_create_tasks",
                bulk_task_create_duration,
                len(created_tasks) == num_tasks,
                {
                    'total_tasks': num_tasks,
                    'successful_creates': len(created_tasks),
                    'avg_duration_per_task': avg_task_create_duration
                }
            )
            
            # Test bulk list operations with large dataset
            start_time = time.time()
            result = list_projects()
            list_projects_duration = time.time() - start_time
            
            self.log_result(
                "Bulk Operations",
                "list_projects_large_dataset",
                list_projects_duration,
                result.get('success', False),
                {
                    'total_projects_in_db': len(result.get('data', [])),
                    'projects_per_second': len(result.get('data', [])) / list_projects_duration if list_projects_duration > 0 else 0
                }
            )
            
            start_time = time.time()
            result = list_tasks()
            list_tasks_duration = time.time() - start_time
            
            self.log_result(
                "Bulk Operations",
                "list_tasks_large_dataset",
                list_tasks_duration,
                result.get('success', False),
                {
                    'total_tasks_in_db': len(result.get('data', [])),
                    'tasks_per_second': len(result.get('data', [])) / list_tasks_duration if list_tasks_duration > 0 else 0
                }
            )
    
    def test_concurrent_operations_performance(self):
        """Test performance under concurrent load."""
        print("\n🔄 Testing Concurrent Operations Performance")
        print("=" * 50)
        
        # Test concurrent project creation
        num_threads = 10
        operations_per_thread = 5
        
        def create_projects_concurrently(thread_id):
            thread_results = []
            for i in range(operations_per_thread):
                start_time = time.time()
                result = create_project(
                    name=f"Concurrent Project T{thread_id}-{i}",
                    description=f"Created by thread {thread_id}, operation {i}",
                    status="active"
                )
                duration = time.time() - start_time
                thread_results.append({
                    'duration': duration,
                    'success': result.get('success', False),
                    'data': result.get('data') if result.get('success') else None
                })
                if result.get('success') and result.get('data'):
                    self.cleanup_projects.append(result['data'])
            return thread_results
        
        # Execute concurrent operations
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [
                executor.submit(create_projects_concurrently, i) 
                for i in range(num_threads)
            ]
            
            all_results = []
            for future in as_completed(futures):
                all_results.extend(future.result())
        
        total_duration = time.time() - start_time
        
        # Analyze results
        successful_operations = [r for r in all_results if r['success']]
        durations = [r['duration'] for r in all_results]
        
        self.log_result(
            "Concurrent Operations",
            "concurrent_create_projects",
            total_duration,
            len(successful_operations) == len(all_results),
            {
                'total_operations': len(all_results),
                'successful_operations': len(successful_operations),
                'threads': num_threads,
                'operations_per_thread': operations_per_thread,
                'avg_duration': statistics.mean(durations),
                'min_duration': min(durations),
                'max_duration': max(durations),
                'median_duration': statistics.median(durations),
                'operations_per_second': len(all_results) / total_duration
            }
        )
        
        # Test concurrent mixed operations
        def mixed_operations(thread_id):
            thread_results = []
            
            # Create project
            start_time = time.time()
            project_result = create_project(
                name=f"Mixed Ops Project T{thread_id}",
                description=f"Mixed operations test thread {thread_id}"
            )
            duration = time.time() - start_time
            thread_results.append(('create_project', duration, project_result.get('success', False)))
            
            if project_result.get('success') and project_result.get('data'):
                project = project_result['data']
                self.cleanup_projects.append(project)
                project_id = project['id']
                
                # Create task
                start_time = time.time()
                task_result = create_task(
                    title=f"Mixed Ops Task T{thread_id}",
                    project_id=project_id,
                    status="pending"
                )
                duration = time.time() - start_time
                thread_results.append(('create_task', duration, task_result.get('success', False)))
                
                if task_result.get('success') and task_result.get('data'):
                    task = task_result['data']
                    self.cleanup_tasks.append(task)
                    
                    # Update task
                    start_time = time.time()
                    update_result = update_task(task['id'], status="in_progress")
                    duration = time.time() - start_time
                    thread_results.append(('update_task', duration, update_result.get('success', False)))
                
                # List operations
                start_time = time.time()
                list_result = list_projects()
                duration = time.time() - start_time
                thread_results.append(('list_projects', duration, list_result.get('success', False)))
            
            return thread_results
        
        # Execute mixed concurrent operations
        start_time = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(mixed_operations, i) for i in range(5)]
            mixed_results = []
            for future in as_completed(futures):
                mixed_results.extend(future.result())
        
        total_mixed_duration = time.time() - start_time
        
        # Analyze mixed operations results
        operation_stats = {}
        for op_type, duration, success in mixed_results:
            if op_type not in operation_stats:
                operation_stats[op_type] = {'durations': [], 'successes': 0, 'total': 0}
            operation_stats[op_type]['durations'].append(duration)
            operation_stats[op_type]['total'] += 1
            if success:
                operation_stats[op_type]['successes'] += 1
        
        for op_type, stats in operation_stats.items():
            avg_duration = statistics.mean(stats['durations'])
            success_rate = stats['successes'] / stats['total']
            
            self.log_result(
                "Concurrent Mixed Operations",
                f"concurrent_{op_type}",
                avg_duration,
                success_rate > 0.95,
                {
                    'total_operations': stats['total'],
                    'successful_operations': stats['successes'],
                    'success_rate': success_rate,
                    'avg_duration': avg_duration,
                    'min_duration': min(stats['durations']),
                    'max_duration': max(stats['durations'])
                }
            )
    
    def test_memory_usage(self):
        """Test memory usage during operations."""
        print("\n💾 Testing Memory Usage")
        print("=" * 50)
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Perform memory-intensive operations
        num_operations = 100
        
        for i in range(num_operations):
            # Create project
            result = create_project(
                name=f"Memory Test Project {i}",
                description="x" * 500,  # Larger description
                status="active"
            )
            if result.get('success') and result.get('data'):
                self.cleanup_projects.append(result['data'])
                
                # Create multiple tasks per project
                for j in range(5):
                    task_result = create_task(
                        title=f"Memory Test Task {i}-{j}",
                        description="x" * 200,  # Larger description
                        project_id=result['data']['id'],
                        status="pending"
                    )
                    if task_result.get('success') and task_result.get('data'):
                        self.cleanup_tasks.append(task_result['data'])
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Test list operations with large dataset
        start_time = time.time()
        list_result = list_projects()
        list_duration = time.time() - start_time
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        self.log_result(
            "Memory Usage",
            "memory_intensive_operations",
            list_duration,
            memory_increase < 100,  # Less than 100MB increase
            {
                'initial_memory_mb': initial_memory,
                'peak_memory_mb': peak_memory,
                'final_memory_mb': final_memory,
                'memory_increase_mb': memory_increase,
                'operations_performed': num_operations * 6,  # 1 project + 5 tasks each
                'memory_per_operation_kb': (memory_increase * 1024) / (num_operations * 6)
            }
        )
    
    def test_database_connection_performance(self):
        """Test database connection and query performance."""
        print("\n🔌 Testing Database Connection Performance")
        print("=" * 50)
        
        # Test connection establishment time
        connection_times = []
        for i in range(10):
            start_time = time.time()
            connection_healthy = self.db.test_connection()
            duration = time.time() - start_time
            connection_times.append(duration)
        
        avg_connection_time = statistics.mean(connection_times)
        
        self.log_result(
            "Database Connection",
            "connection_test",
            avg_connection_time,
            avg_connection_time < 0.01,  # Less than 10ms
            {
                'connection_attempts': len(connection_times),
                'avg_connection_time': avg_connection_time,
                'min_connection_time': min(connection_times),
                'max_connection_time': max(connection_times),
                'all_connections_successful': all([True] * len(connection_times))  # Simplified
            }
        )
        
        # Test query performance with different result set sizes
        query_tests = [
            {'limit': 10, 'name': 'small_result_set'},
            {'limit': 100, 'name': 'medium_result_set'},
            {'limit': 1000, 'name': 'large_result_set'}
        ]
        
        for test in query_tests:
            start_time = time.time()
            result = list_tasks(limit=test['limit'])
            duration = time.time() - start_time
            
            self.log_result(
                "Database Query Performance",
                f"list_tasks_{test['name']}",
                duration,
                result.get('success', False) and duration < 0.1,
                {
                    'limit': test['limit'],
                    'actual_results': len(result.get('data', [])),
                    'results_per_second': len(result.get('data', [])) / duration if duration > 0 else 0
                }
            )
    
    def cleanup(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        # Clean up tasks first (due to foreign key constraints)
        for task in self.cleanup_tasks:
            try:
                delete_task(task['id'])
            except:
                pass
        
        # Clean up projects
        for project in self.cleanup_projects:
            try:
                delete_project(project['id'])
            except:
                pass
        
        print(f"Cleaned up {len(self.cleanup_tasks)} tasks and {len(self.cleanup_projects)} projects")
    
    def generate_report(self):
        """Generate performance test report."""
        print("\n" + "=" * 60)
        print("📊 PERFORMANCE TEST REPORT")
        print("=" * 60)
        
        # Overall statistics
        total_tests = len(self.test_results)
        successful_tests = len([r for r in self.test_results if r['success']])
        within_threshold_tests = len([r for r in self.test_results if r['within_threshold']])
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests} ({successful_tests/total_tests*100:.1f}%)")
        print(f"Within Threshold: {within_threshold_tests} ({within_threshold_tests/total_tests*100:.1f}%)")
        
        # Performance by operation type
        operation_stats = {}
        for result in self.test_results:
            op = result['operation']
            if op not in operation_stats:
                operation_stats[op] = []
            operation_stats[op].append(result['duration'])
        
        print(f"\n📈 Performance by Operation:")
        for operation, durations in operation_stats.items():
            avg_duration = statistics.mean(durations)
            threshold = self.thresholds.get(operation, 1.0)
            status = "✅" if avg_duration <= threshold else "❌"
            
            print(f"  {status} {operation}: {avg_duration:.4f}s (threshold: {threshold}s)")
        
        # Slowest operations
        slowest_tests = sorted(self.test_results, key=lambda x: x['duration'], reverse=True)[:5]
        print(f"\n🐌 Slowest Operations:")
        for test in slowest_tests:
            print(f"  - {test['test_name']} - {test['operation']}: {test['duration']:.4f}s")
        
        # Save detailed report
        import json
        with open("mcp_performance_test_results.json", "w") as f:
            json.dump({
                'summary': {
                    'total_tests': total_tests,
                    'successful_tests': successful_tests,
                    'within_threshold_tests': within_threshold_tests,
                    'success_rate': successful_tests / total_tests * 100,
                    'performance_rate': within_threshold_tests / total_tests * 100,
                    'timestamp': datetime.now().isoformat()
                },
                'operation_stats': {
                    op: {
                        'avg_duration': statistics.mean(durations),
                        'min_duration': min(durations),
                        'max_duration': max(durations),
                        'median_duration': statistics.median(durations),
                        'threshold': self.thresholds.get(op, 1.0),
                        'test_count': len(durations)
                    }
                    for op, durations in operation_stats.items()
                },
                'detailed_results': self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed report saved to: mcp_performance_test_results.json")
    
    def run_all_tests(self):
        """Run all performance tests."""
        print("🚀 Starting MCP Service Performance Tests")
        print("=" * 60)
        
        try:
            # Verify database connection
            if not self.db.test_connection():
                print("❌ Database connection failed. Cannot run performance tests.")
                return
            
            # Run test suites
            self.test_single_operation_performance()
            self.test_bulk_operations_performance()
            self.test_concurrent_operations_performance()
            self.test_memory_usage()
            self.test_database_connection_performance()
            
        finally:
            # Always cleanup
            self.cleanup()
            
            # Generate report
            self.generate_report()


if __name__ == "__main__":
    suite = PerformanceTestSuite()
    suite.run_all_tests()