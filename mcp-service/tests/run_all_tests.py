#!/usr/bin/env python3
"""
Comprehensive test runner for MCP service test suite.

This script runs all test suites in sequence and generates a consolidated report.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, List


class TestRunner:
    """Orchestrates execution of all MCP service tests."""
    
    def __init__(self):
        self.test_results = {}
        self.start_time = time.time()
        self.test_suites = [
            {
                "name": "Integration Tests",
                "script": "test_integration.py",
                "description": "Complete CRUD operations and database integration",
                "critical": True
            },
            {
                "name": "Performance Tests", 
                "script": "test_performance.py",
                "description": "Performance benchmarks and load testing",
                "critical": False
            },
            {
                "name": "Container Deployment Tests",
                "script": "test_container_deployment.py", 
                "description": "Docker container and service deployment verification",
                "critical": True
            },
            {
                "name": "Error Scenario Tests",
                "script": "test_error_scenarios.py",
                "description": "Error handling and edge case testing",
                "critical": True
            }
        ]
    
    def check_prerequisites(self) -> bool:
        """Check if prerequisites are met for running tests."""
        print("🔍 Checking Prerequisites...")
        print("=" * 50)
        
        prerequisites_met = True
        
        # Check Python packages
        required_packages = [
            "psycopg2", "docker", "requests", "psutil"
        ]
        
        for package in required_packages:
            try:
                __import__(package)
                print(f"✅ {package} - Available")
            except ImportError:
                print(f"❌ {package} - Missing")
                prerequisites_met = False
        
        # Check database connection
        try:
            import psycopg2
            database_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/aiagent_mcp')
            conn = psycopg2.connect(database_url)
            conn.close()
            print("✅ Database Connection - Available")
        except Exception as e:
            print(f"❌ Database Connection - Failed: {str(e)}")
            prerequisites_met = False
        
        # Check MCP service availability
        try:
            import requests
            response = requests.get("http://localhost:8001/health", timeout=5)
            if response.status_code == 200:
                print("✅ MCP Service - Available")
            else:
                print(f"⚠️  MCP Service - Responding but unhealthy (status: {response.status_code})")
        except Exception as e:
            print(f"⚠️  MCP Service - Not available: {str(e)}")
            print("   Note: Container deployment tests will handle this")
        
        # Check Docker availability (for container tests)
        try:
            result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Docker - Available")
            else:
                print("❌ Docker - Not available")
                prerequisites_met = False
        except FileNotFoundError:
            print("❌ Docker - Not installed")
            prerequisites_met = False
        
        print(f"\nPrerequisites Status: {'✅ Ready' if prerequisites_met else '❌ Issues Found'}")
        
        if not prerequisites_met:
            print("\n📋 To install missing packages:")
            print("pip install psycopg2-binary docker requests psutil pytest")
        
        return prerequisites_met
    
    def run_test_suite(self, suite: Dict[str, Any]) -> Dict[str, Any]:
        """Run a single test suite."""
        print(f"\n🚀 Running {suite['name']}")
        print("=" * 60)
        print(f"Description: {suite['description']}")
        print(f"Script: {suite['script']}")
        print(f"Critical: {'Yes' if suite['critical'] else 'No'}")
        print("-" * 60)
        
        start_time = time.time()
        
        try:
            # Run the test script
            result = subprocess.run(
                [sys.executable, suite['script']],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout per test suite
            )
            
            duration = time.time() - start_time
            
            # Parse output for results
            success = result.returncode == 0
            stdout_lines = result.stdout.split('\n') if result.stdout else []
            stderr_lines = result.stderr.split('\n') if result.stderr else []
            
            # Try to find summary information in output
            summary_info = self.extract_summary_from_output(stdout_lines)
            
            test_result = {
                "name": suite['name'],
                "script": suite['script'],
                "success": success,
                "duration": duration,
                "return_code": result.returncode,
                "critical": suite['critical'],
                "summary": summary_info,
                "stdout_lines": len(stdout_lines),
                "stderr_lines": len(stderr_lines),
                "timestamp": datetime.now().isoformat()
            }
            
            # Print real-time output
            if result.stdout:
                print(result.stdout)
            
            if result.stderr and not success:
                print("STDERR:")
                print(result.stderr)
            
            status = "✅ PASSED" if success else "❌ FAILED"
            critical_status = " (CRITICAL)" if suite['critical'] else ""
            print(f"\n{status} {suite['name']}{critical_status} - Duration: {duration:.2f}s")
            
            return test_result
            
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            print(f"⏰ TIMEOUT {suite['name']} - Exceeded 5 minute limit")
            
            return {
                "name": suite['name'],
                "script": suite['script'],
                "success": False,
                "duration": duration,
                "return_code": -1,
                "critical": suite['critical'],
                "error": "Test suite timed out after 5 minutes",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            duration = time.time() - start_time
            print(f"💥 ERROR {suite['name']} - {str(e)}")
            
            return {
                "name": suite['name'],
                "script": suite['script'],
                "success": False,
                "duration": duration,
                "return_code": -1,
                "critical": suite['critical'],
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def extract_summary_from_output(self, output_lines: List[str]) -> Dict[str, Any]:
        """Extract summary information from test output."""
        summary = {}
        
        for line in output_lines:
            line = line.strip()
            
            # Look for common summary patterns
            if "Total Tests:" in line:
                try:
                    summary["total_tests"] = int(line.split(":")[-1].strip())
                except:
                    pass
            
            elif "Passed:" in line and "✅" in line:
                try:
                    summary["passed_tests"] = int(line.split(":")[1].split("✅")[0].strip())
                except:
                    pass
            
            elif "Failed:" in line and "❌" in line:
                try:
                    summary["failed_tests"] = int(line.split(":")[1].split("❌")[0].strip())
                except:
                    pass
            
            elif "Success Rate:" in line:
                try:
                    summary["success_rate"] = float(line.split(":")[-1].replace("%", "").strip())
                except:
                    pass
        
        return summary
    
    def load_detailed_results(self) -> Dict[str, Any]:
        """Load detailed results from individual test result files."""
        result_files = {
            "integration": "mcp_integration_test_results.json",
            "performance": "mcp_performance_test_results.json", 
            "container": "container_deployment_test_results.json",
            "error_scenarios": "error_scenario_test_results.json"
        }
        
        detailed_results = {}
        
        for test_type, filename in result_files.items():
            if os.path.exists(filename):
                try:
                    with open(filename, 'r') as f:
                        detailed_results[test_type] = json.load(f)
                except Exception as e:
                    detailed_results[test_type] = {"error": f"Could not load {filename}: {str(e)}"}
            else:
                detailed_results[test_type] = {"error": f"Result file {filename} not found"}
        
        return detailed_results
    
    def generate_consolidated_report(self):
        """Generate consolidated test report."""
        total_duration = time.time() - self.start_time
        
        print("\n" + "=" * 80)
        print("📊 CONSOLIDATED MCP SERVICE TEST REPORT")
        print("=" * 80)
        
        # Overall summary
        total_suites = len(self.test_results)
        passed_suites = len([r for r in self.test_results.values() if r["success"]])
        failed_suites = total_suites - passed_suites
        critical_failures = len([
            r for r in self.test_results.values() 
            if not r["success"] and r["critical"]
        ])
        
        print(f"Test Execution Summary:")
        print(f"  Total Test Suites: {total_suites}")
        print(f"  Passed: {passed_suites} ✅")
        print(f"  Failed: {failed_suites} ❌")
        print(f"  Critical Failures: {critical_failures} 🚨")
        print(f"  Total Duration: {total_duration:.2f}s")
        print(f"  Success Rate: {(passed_suites/total_suites)*100:.1f}%")
        
        # Individual suite results
        print(f"\nIndividual Test Suite Results:")
        for suite_name, result in self.test_results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            critical = " (CRITICAL)" if result["critical"] else ""
            duration = result["duration"]
            
            print(f"  {status} {suite_name}{critical} - {duration:.2f}s")
            
            # Show summary if available
            if "summary" in result and result["summary"]:
                summary = result["summary"]
                if "total_tests" in summary:
                    total = summary.get("total_tests", 0)
                    passed = summary.get("passed_tests", 0)
                    rate = summary.get("success_rate", 0)
                    print(f"    └─ {passed}/{total} tests passed ({rate:.1f}%)")
        
        # Load detailed results
        detailed_results = self.load_detailed_results()
        
        # Aggregate detailed statistics
        total_individual_tests = 0
        total_passed_individual = 0
        
        for test_type, details in detailed_results.items():
            if "summary" in details:
                summary = details["summary"]
                total_individual_tests += summary.get("total_tests", 0)
                total_passed_individual += summary.get("passed", summary.get("passed_tests", 0))
        
        if total_individual_tests > 0:
            print(f"\nDetailed Test Statistics:")
            print(f"  Total Individual Tests: {total_individual_tests}")
            print(f"  Passed Individual Tests: {total_passed_individual}")
            print(f"  Individual Test Success Rate: {(total_passed_individual/total_individual_tests)*100:.1f}%")
        
        # Recommendations
        print(f"\nRecommendations:")
        if critical_failures > 0:
            print("  🚨 CRITICAL: Address critical test failures before deployment")
            for suite_name, result in self.test_results.items():
                if not result["success"] and result["critical"]:
                    print(f"    - Fix issues in {suite_name}")
        
        if failed_suites > 0 and critical_failures == 0:
            print("  ⚠️  Review non-critical test failures for potential improvements")
        
        if passed_suites == total_suites:
            print("  🎉 All tests passed! System is ready for deployment")
        
        # Performance insights
        performance_details = detailed_results.get("performance", {})
        if "summary" in performance_details:
            perf_summary = performance_details["summary"]
            perf_rate = perf_summary.get("performance_rate", 0)
            print(f"  📈 Performance: {perf_rate:.1f}% of operations within thresholds")
        
        # Save consolidated report
        consolidated_report = {
            "execution_summary": {
                "total_suites": total_suites,
                "passed_suites": passed_suites,
                "failed_suites": failed_suites,
                "critical_failures": critical_failures,
                "total_duration": total_duration,
                "success_rate": (passed_suites/total_suites)*100,
                "timestamp": datetime.now().isoformat()
            },
            "suite_results": self.test_results,
            "detailed_results": detailed_results,
            "individual_test_stats": {
                "total_tests": total_individual_tests,
                "passed_tests": total_passed_individual,
                "success_rate": (total_passed_individual/total_individual_tests)*100 if total_individual_tests > 0 else 0
            }
        }
        
        with open("mcp_consolidated_test_report.json", "w") as f:
            json.dump(consolidated_report, f, indent=2)
        
        print(f"\n📄 Consolidated report saved to: mcp_consolidated_test_report.json")
        
        # Return overall success status
        return critical_failures == 0
    
    def run_all_tests(self) -> bool:
        """Run all test suites and generate consolidated report."""
        print("🚀 Starting MCP Service Comprehensive Test Suite")
        print("=" * 80)
        print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Test Suites: {len(self.test_suites)}")
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n❌ Prerequisites not met. Please install missing dependencies.")
            return False
        
        # Run each test suite
        for suite in self.test_suites:
            result = self.run_test_suite(suite)
            self.test_results[suite['name']] = result
            
            # If critical test fails, consider stopping
            if not result["success"] and result["critical"]:
                print(f"\n🚨 CRITICAL TEST FAILURE: {suite['name']}")
                print("Consider fixing critical issues before continuing...")
                
                # Continue with remaining tests but note the critical failure
        
        # Generate consolidated report
        overall_success = self.generate_consolidated_report()
        
        return overall_success


if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)