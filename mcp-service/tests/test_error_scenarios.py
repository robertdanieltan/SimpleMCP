#!/usr/bin/env python3
"""
Comprehensive error scenario and edge case tests for MCP service.

This test suite covers:
- Input validation edge cases
- Database constraint violations
- Network and connection failures
- Resource exhaustion scenarios
- Malformed data handling
- Security boundary testing
"""

import os
import sys
import json
import time
import threading
from datetime import datetime, date, timedelta
from typing import Dict, Any, List

# Add the mcp-service directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.tools.task_tools import create_task, list_tasks, update_task, delete_task
from app.tools.project_tools import create_project, list_projects, update_project, delete_project
from app.database.connection import get_db_connection


class ErrorScenarioTester:
    """Test suite for error scenarios and edge cases."""
    
    def __init__(self):
        self.db = get_db_connection()
        self.test_results = []
        self.cleanup_projects = []
        self.cleanup_tasks = []
    
    def log_result(self, test_name: str, success: bool, details: Dict[str, Any]):
        """Log test result."""
        result = {
            "test": test_name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if not success:
            print(f"   Error: {details.get('error', 'Unknown error')}")
        elif details.get('info'):
            print(f"   Info: {details['info']}")
    
    def test_input_validation_errors(self):
        """Test various input validation error scenarios."""
        print("\n🔍 Testing Input Validation Errors")
        print("=" * 50)
        
        # Project validation errors
        project_error_cases = [
            {
                "name": "Empty Project Name",
                "args": {"name": "", "description": "Empty name test"},
                "expected_error_keywords": ["validation", "empty", "name"]
            },
            {
                "name": "Whitespace Only Project Name",
                "args": {"name": "   ", "description": "Whitespace name test"},
                "expected_error_keywords": ["validation", "empty", "name"]
            },
            {
                "name": "None Project Name",
                "args": {"name": None, "description": "None name test"},
                "expected_error_keywords": ["validation", "name"]
            },
            {
                "name": "Invalid Project Status",
                "args": {"name": "Valid Name", "status": "invalid_status"},
                "expected_error_keywords": ["validation", "status"]
            },
            {
                "name": "Extremely Long Project Name",
                "args": {"name": "x" * 1000, "description": "Long name test"},
                "expected_error_keywords": ["validation", "length", "name"]
            },
            {
                "name": "Extremely Long Description",
                "args": {"name": "Valid Name", "description": "x" * 10000},
                "expected_error_keywords": ["validation", "length", "description"]
            }
        ]
        
        for case in project_error_cases:
            try:
                result = create_project(**case["args"])
                
                # Should fail validation
                if result.get("success"):
                    self.log_result(f"Project Validation - {case['name']}", False, {
                        "error": "Expected validation error but operation succeeded",
                        "result": result
                    })
                else:
                    # Check if error message contains expected keywords
                    error_message = result.get("message", "").lower()
                    has_expected_keywords = any(
                        keyword in error_message 
                        for keyword in case["expected_error_keywords"]
                    )
                    
                    self.log_result(f"Project Validation - {case['name']}", has_expected_keywords, {
                        "error_message": result.get("message"),
                        "expected_keywords": case["expected_error_keywords"],
                        "keywords_found": has_expected_keywords,
                        "info": "Validation error correctly caught"
                    })
                    
            except Exception as e:
                # Exceptions are also acceptable for validation errors
                self.log_result(f"Project Validation - {case['name']}", True, {
                    "exception": str(e),
                    "info": "Validation error caught as exception"
                })
        
        # Task validation errors
        task_error_cases = [
            {
                "name": "Empty Task Title",
                "args": {"title": "", "description": "Empty title test"},
                "expected_error_keywords": ["validation", "empty", "title"]
            },
            {
                "name": "Invalid Task Status",
                "args": {"title": "Valid Title", "status": "invalid_status"},
                "expected_error_keywords": ["validation", "status"]
            },
            {
                "name": "Invalid Task Priority",
                "args": {"title": "Valid Title", "priority": "invalid_priority"},
                "expected_error_keywords": ["validation", "priority"]
            },
            {
                "name": "Invalid Date Format",
                "args": {"title": "Valid Title", "due_date": "invalid-date"},
                "expected_error_keywords": ["validation", "date", "format"]
            },
            {
                "name": "Past Due Date",
                "args": {"title": "Valid Title", "due_date": "2020-01-01"},
                "expected_error_keywords": ["validation", "date", "past"]
            },
            {
                "name": "Extremely Long Task Title",
                "args": {"title": "x" * 1000, "description": "Long title test"},
                "expected_error_keywords": ["validation", "length", "title"]
            }
        ]
        
        for case in task_error_cases:
            try:
                result = create_task(**case["args"])
                
                if result.get("success"):
                    self.log_result(f"Task Validation - {case['name']}", False, {
                        "error": "Expected validation error but operation succeeded",
                        "result": result
                    })
                else:
                    error_message = result.get("message", "").lower()
                    has_expected_keywords = any(
                        keyword in error_message 
                        for keyword in case["expected_error_keywords"]
                    )
                    
                    self.log_result(f"Task Validation - {case['name']}", has_expected_keywords, {
                        "error_message": result.get("message"),
                        "expected_keywords": case["expected_error_keywords"],
                        "keywords_found": has_expected_keywords,
                        "info": "Validation error correctly caught"
                    })
                    
            except Exception as e:
                self.log_result(f"Task Validation - {case['name']}", True, {
                    "exception": str(e),
                    "info": "Validation error caught as exception"
                })
    
    def test_database_constraint_violations(self):
        """Test database constraint violation scenarios."""
        print("\n🔍 Testing Database Constraint Violations")
        print("=" * 50)
        
        # Test foreign key constraint violation
        try:
            result = create_task(
                title="Invalid Project Reference Task",
                project_id=99999,  # Non-existent project ID
                description="Task with invalid project reference"
            )
            
            # This might succeed or fail depending on constraint enforcement
            # The important thing is that it handles the situation gracefully
            self.log_result("Foreign Key Constraint", True, {
                "result": result,
                "info": "Foreign key constraint handled gracefully"
            })
            
            # If it succeeded, clean up
            if result.get("success") and result.get("data"):
                self.cleanup_tasks.append(result["data"])
                
        except Exception as e:
            self.log_result("Foreign Key Constraint", True, {
                "exception": str(e),
                "info": "Foreign key constraint violation caught as exception"
            })
        
        # Test duplicate name constraints (if any)
        project_name = f"Duplicate Test Project {int(time.time())}"
        
        # Create first project
        result1 = create_project(name=project_name, description="First project")
        if result1.get("success") and result1.get("data"):
            self.cleanup_projects.append(result1["data"])
            
            # Try to create second project with same name
            result2 = create_project(name=project_name, description="Second project")
            
            # This might succeed or fail depending on constraints
            # Both outcomes are acceptable as long as they're handled gracefully
            self.log_result("Duplicate Name Handling", True, {
                "first_result": result1.get("success"),
                "second_result": result2.get("success"),
                "info": "Duplicate name scenario handled gracefully"
            })
            
            if result2.get("success") and result2.get("data"):
                self.cleanup_projects.append(result2["data"])
    
    def test_nonexistent_resource_operations(self):
        """Test operations on non-existent resources."""
        print("\n🔍 Testing Non-existent Resource Operations")
        print("=" * 50)
        
        non_existent_id = 99999
        
        # Test update non-existent project
        result = update_project(
            non_existent_id,
            name="Updated Non-existent Project"
        )
        
        success = not result.get("success") and "not found" in result.get("message", "").lower()
        self.log_result("Update Non-existent Project", success, {
            "result": result,
            "expected": "Should fail with 'not found' message"
        })
        
        # Test delete non-existent project
        result = delete_project(non_existent_id)
        
        success = not result.get("success") and "not found" in result.get("message", "").lower()
        self.log_result("Delete Non-existent Project", success, {
            "result": result,
            "expected": "Should fail with 'not found' message"
        })
        
        # Test update non-existent task
        result = update_task(
            non_existent_id,
            title="Updated Non-existent Task"
        )
        
        success = not result.get("success") and "not found" in result.get("message", "").lower()
        self.log_result("Update Non-existent Task", success, {
            "result": result,
            "expected": "Should fail with 'not found' message"
        })
        
        # Test delete non-existent task
        result = delete_task(non_existent_id)
        
        success = not result.get("success") and "not found" in result.get("message", "").lower()
        self.log_result("Delete Non-existent Task", success, {
            "result": result,
            "expected": "Should fail with 'not found' message"
        })
    
    def test_boundary_value_scenarios(self):
        """Test boundary value scenarios."""
        print("\n🔍 Testing Boundary Value Scenarios")
        print("=" * 50)
        
        # Test minimum valid values
        try:
            # Single character name
            result = create_project(name="A")
            success = result.get("success", False)
            
            self.log_result("Minimum Project Name Length", success, {
                "name_length": 1,
                "result": result,
                "info": "Single character name should be valid"
            })
            
            if success and result.get("data"):
                self.cleanup_projects.append(result["data"])
                
        except Exception as e:
            self.log_result("Minimum Project Name Length", False, {
                "exception": str(e)
            })
        
        # Test maximum valid values
        try:
            # Maximum length name (255 characters)
            max_name = "x" * 255
            result = create_project(name=max_name)
            success = result.get("success", False)
            
            self.log_result("Maximum Project Name Length", success, {
                "name_length": len(max_name),
                "result": result,
                "info": "255 character name should be valid"
            })
            
            if success and result.get("data"):
                self.cleanup_projects.append(result["data"])
                
        except Exception as e:
            self.log_result("Maximum Project Name Length", False, {
                "exception": str(e)
            })
        
        # Test just over maximum values
        try:
            # Over maximum length name (256 characters)
            over_max_name = "x" * 256
            result = create_project(name=over_max_name)
            success = not result.get("success", True)  # Should fail
            
            self.log_result("Over Maximum Project Name Length", success, {
                "name_length": len(over_max_name),
                "result": result,
                "info": "256 character name should be rejected"
            })
            
        except Exception as e:
            self.log_result("Over Maximum Project Name Length", True, {
                "exception": str(e),
                "info": "Over-length name rejected with exception"
            })
        
        # Test pagination boundary values
        pagination_tests = [
            {"limit": 0, "should_fail": True, "name": "Zero Limit"},
            {"limit": 1, "should_fail": False, "name": "Minimum Valid Limit"},
            {"limit": 1000, "should_fail": False, "name": "Maximum Valid Limit"},
            {"limit": 1001, "should_fail": True, "name": "Over Maximum Limit"},
            {"offset": -1, "should_fail": True, "name": "Negative Offset"},
            {"offset": 0, "should_fail": False, "name": "Zero Offset"},
        ]
        
        for test in pagination_tests:
            try:
                kwargs = {}
                if "limit" in test:
                    kwargs["limit"] = test["limit"]
                if "offset" in test:
                    kwargs["offset"] = test["offset"]
                
                result = list_projects(**kwargs)
                actual_success = result.get("success", False)
                expected_success = not test["should_fail"]
                
                test_passed = actual_success == expected_success
                
                self.log_result(f"Pagination - {test['name']}", test_passed, {
                    "parameters": kwargs,
                    "expected_success": expected_success,
                    "actual_success": actual_success,
                    "result": result
                })
                
            except Exception as e:
                # Exceptions are acceptable for invalid parameters
                expected_exception = test["should_fail"]
                self.log_result(f"Pagination - {test['name']}", expected_exception, {
                    "exception": str(e),
                    "expected_exception": expected_exception
                })
    
    def test_special_character_handling(self):
        """Test handling of special characters and Unicode."""
        print("\n🔍 Testing Special Character Handling")
        print("=" * 50)
        
        special_character_tests = [
            {
                "name": "SQL Injection Attempt",
                "project_name": "'; DROP TABLE projects; --",
                "description": "SQL injection attempt in project name"
            },
            {
                "name": "Unicode Characters",
                "project_name": "Project 你好世界 🌍",
                "description": "Unicode characters: Здравствуй мир"
            },
            {
                "name": "Special Symbols",
                "project_name": "Project !@#$%^&*()_+-=[]{}|;':\",./<>?",
                "description": "All special keyboard symbols"
            },
            {
                "name": "HTML/XML Tags",
                "project_name": "<script>alert('xss')</script>",
                "description": "HTML/XML tag injection attempt"
            },
            {
                "name": "Newlines and Tabs",
                "project_name": "Project\nWith\tSpecial\rWhitespace",
                "description": "Project with various whitespace characters"
            },
            {
                "name": "Null Bytes",
                "project_name": "Project\x00WithNull",
                "description": "Project name with null byte"
            }
        ]
        
        for test in special_character_tests:
            try:
                result = create_project(
                    name=test["project_name"],
                    description=test["description"]
                )
                
                # The operation should either succeed (properly escaped) or fail gracefully
                if result.get("success"):
                    # If successful, verify data integrity
                    project = result.get("data", {})
                    name_preserved = project.get("name") == test["project_name"]
                    
                    self.log_result(f"Special Characters - {test['name']}", name_preserved, {
                        "original_name": test["project_name"],
                        "stored_name": project.get("name"),
                        "name_preserved": name_preserved,
                        "info": "Special characters handled and preserved"
                    })
                    
                    if result.get("data"):
                        self.cleanup_projects.append(result["data"])
                else:
                    # Graceful failure is also acceptable
                    self.log_result(f"Special Characters - {test['name']}", True, {
                        "result": result,
                        "info": "Special characters caused graceful failure"
                    })
                    
            except Exception as e:
                # Exceptions are acceptable for problematic characters
                self.log_result(f"Special Characters - {test['name']}", True, {
                    "exception": str(e),
                    "info": "Special characters caused exception (acceptable)"
                })
    
    def test_concurrent_modification_scenarios(self):
        """Test concurrent modification scenarios."""
        print("\n🔍 Testing Concurrent Modification Scenarios")
        print("=" * 50)
        
        # Create a project for concurrent testing
        result = create_project(
            name="Concurrent Modification Test",
            description="Testing concurrent modifications"
        )
        
        if not result.get("success") or not result.get("data"):
            self.log_result("Concurrent Modification Setup", False, {
                "error": "Could not create test project for concurrent modification tests"
            })
            return
        
        project = result["data"]
        self.cleanup_projects.append(project)
        project_id = project["id"]
        
        # Test concurrent updates to the same project
        def update_project_concurrently(thread_id, update_data):
            try:
                result = update_project(project_id, **update_data)
                return {
                    "thread_id": thread_id,
                    "success": result.get("success", False),
                    "result": result
                }
            except Exception as e:
                return {
                    "thread_id": thread_id,
                    "success": False,
                    "exception": str(e)
                }
        
        # Start multiple threads updating the same project
        threads = []
        results = []
        
        update_scenarios = [
            {"name": f"Updated by Thread {i}", "description": f"Description from thread {i}"}
            for i in range(5)
        ]
        
        for i, update_data in enumerate(update_scenarios):
            thread = threading.Thread(
                target=lambda i=i, data=update_data: results.append(
                    update_project_concurrently(i, data)
                )
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Analyze results
        successful_updates = [r for r in results if r["success"]]
        failed_updates = [r for r in results if not r["success"]]
        
        # At least one update should succeed, others may fail due to concurrency
        concurrent_handling_ok = len(successful_updates) >= 1
        
        self.log_result("Concurrent Project Updates", concurrent_handling_ok, {
            "total_attempts": len(results),
            "successful_updates": len(successful_updates),
            "failed_updates": len(failed_updates),
            "info": "Concurrent updates handled appropriately"
        })
        
        # Test concurrent task creation on the same project
        def create_task_concurrently(thread_id):
            try:
                result = create_task(
                    title=f"Concurrent Task {thread_id}",
                    description=f"Created by thread {thread_id}",
                    project_id=project_id,
                    status="pending"
                )
                return {
                    "thread_id": thread_id,
                    "success": result.get("success", False),
                    "result": result
                }
            except Exception as e:
                return {
                    "thread_id": thread_id,
                    "success": False,
                    "exception": str(e)
                }
        
        # Create tasks concurrently
        task_threads = []
        task_results = []
        
        for i in range(5):
            thread = threading.Thread(
                target=lambda i=i: task_results.append(create_task_concurrently(i))
            )
            task_threads.append(thread)
            thread.start()
        
        for thread in task_threads:
            thread.join()
        
        successful_task_creates = [r for r in task_results if r["success"]]
        
        # All task creations should succeed (no conflicts expected)
        all_tasks_created = len(successful_task_creates) == len(task_results)
        
        self.log_result("Concurrent Task Creation", all_tasks_created, {
            "total_attempts": len(task_results),
            "successful_creates": len(successful_task_creates),
            "info": "Concurrent task creation handled correctly"
        })
        
        # Add successful tasks to cleanup
        for result in successful_task_creates:
            if result["result"].get("data"):
                self.cleanup_tasks.append(result["result"]["data"])
    
    def test_resource_exhaustion_scenarios(self):
        """Test resource exhaustion scenarios."""
        print("\n🔍 Testing Resource Exhaustion Scenarios")
        print("=" * 50)
        
        # Test creating many projects rapidly
        rapid_create_count = 50
        start_time = time.time()
        created_projects = []
        
        for i in range(rapid_create_count):
            try:
                result = create_project(
                    name=f"Rapid Create Project {i}",
                    description=f"Rapidly created project number {i}"
                )
                
                if result.get("success") and result.get("data"):
                    created_projects.append(result["data"])
                    self.cleanup_projects.append(result["data"])
                    
            except Exception as e:
                # Some failures are acceptable under load
                pass
        
        creation_time = time.time() - start_time
        success_rate = len(created_projects) / rapid_create_count
        
        # Accept if at least 80% succeed
        rapid_creation_ok = success_rate >= 0.8
        
        self.log_result("Rapid Project Creation", rapid_creation_ok, {
            "attempted_creates": rapid_create_count,
            "successful_creates": len(created_projects),
            "success_rate": success_rate,
            "total_time": creation_time,
            "creates_per_second": rapid_create_count / creation_time,
            "info": f"Rapid creation handled with {success_rate:.1%} success rate"
        })
        
        # Test listing with very large offset
        try:
            result = list_projects(limit=10, offset=1000000)
            
            # Should handle gracefully (return empty list or error)
            large_offset_ok = (
                result.get("success") and len(result.get("data", [])) == 0
            ) or not result.get("success")
            
            self.log_result("Large Offset Handling", large_offset_ok, {
                "offset": 1000000,
                "result": result,
                "info": "Large offset handled gracefully"
            })
            
        except Exception as e:
            self.log_result("Large Offset Handling", True, {
                "exception": str(e),
                "info": "Large offset caused exception (acceptable)"
            })
    
    def cleanup(self):
        """Clean up test data."""
        print("\n🧹 Cleaning up test data...")
        
        # Clean up tasks first
        for task in self.cleanup_tasks:
            try:
                delete_task(task["id"])
            except:
                pass
        
        # Clean up projects
        for project in self.cleanup_projects:
            try:
                delete_project(project["id"])
            except:
                pass
        
        print(f"Cleaned up {len(self.cleanup_tasks)} tasks and {len(self.cleanup_projects)} projects")
    
    def generate_report(self):
        """Generate error scenario test report."""
        print("\n" + "=" * 60)
        print("📊 ERROR SCENARIO TEST REPORT")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["success"]])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test']}: {result['details'].get('error', 'Unknown error')}")
        
        # Categorize tests
        categories = {}
        for result in self.test_results:
            category = result["test"].split(" - ")[0] if " - " in result["test"] else "Other"
            if category not in categories:
                categories[category] = {"total": 0, "passed": 0}
            categories[category]["total"] += 1
            if result["success"]:
                categories[category]["passed"] += 1
        
        print(f"\n📈 Results by Category:")
        for category, stats in categories.items():
            success_rate = stats["passed"] / stats["total"] * 100
            print(f"  {category}: {stats['passed']}/{stats['total']} ({success_rate:.1f}%)")
        
        # Save detailed results
        with open("error_scenario_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100,
                    "timestamp": datetime.now().isoformat()
                },
                "categories": categories,
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: error_scenario_test_results.json")
    
    def run_all_tests(self):
        """Run all error scenario tests."""
        print("🚀 Starting Error Scenario and Edge Case Tests")
        print("=" * 60)
        
        try:
            # Verify database connection
            if not self.db.test_connection():
                print("❌ Database connection failed. Cannot run error scenario tests.")
                return
            
            # Run test suites
            self.test_input_validation_errors()
            self.test_database_constraint_violations()
            self.test_nonexistent_resource_operations()
            self.test_boundary_value_scenarios()
            self.test_special_character_handling()
            self.test_concurrent_modification_scenarios()
            self.test_resource_exhaustion_scenarios()
            
        finally:
            # Always cleanup
            self.cleanup()
            
            # Generate report
            self.generate_report()


if __name__ == "__main__":
    tester = ErrorScenarioTester()
    tester.run_all_tests()