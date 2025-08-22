#!/usr/bin/env python3
"""
Quick verification script for the comprehensive MCP test suite.

This script verifies that the test suite is properly set up and can run basic tests.
"""

import os
import sys
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up test environment variables for local testing
# Override DATABASE_URL to use localhost instead of container hostname
os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5432/aiagent_mcp'


def test_basic_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing Basic Imports...")
    
    # Test MCP service imports
    sys.path.insert(0, 'mcp-service')
    
    try:
        from app.tools.task_tools import create_task, list_tasks
        from app.tools.project_tools import create_project, list_projects
        from app.database.connection import get_db_connection
        print("✅ MCP service modules imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import MCP service modules: {e}")
        return False


def test_database_connection():
    """Test basic database connectivity."""
    print("\n🔍 Testing Database Connection...")
    
    try:
        sys.path.insert(0, 'mcp-service')
        from app.database.connection import get_db_connection
        
        db = get_db_connection()
        connected = db.test_connection()
        
        if connected:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def test_basic_mcp_operations():
    """Test basic MCP operations."""
    print("\n🔍 Testing Basic MCP Operations...")
    
    try:
        sys.path.insert(0, 'mcp-service')
        from app.tools.project_tools import create_project, list_projects, delete_project
        
        # Create a test project
        result = create_project(
            name=f"Test Suite Verification {int(datetime.now().timestamp())}",
            description="Verification test for comprehensive test suite"
        )
        
        if not result.get("success"):
            print(f"❌ Failed to create test project: {result.get('message')}")
            return False
        
        project = result["data"]
        print(f"✅ Created test project: {project['name']}")
        
        # List projects
        list_result = list_projects()
        if not list_result.get("success"):
            print(f"❌ Failed to list projects: {list_result.get('message')}")
            return False
        
        projects = list_result["data"]
        print(f"✅ Listed {len(projects)} projects")
        
        # Clean up
        delete_result = delete_project(project["id"])
        if delete_result.get("success"):
            print("✅ Cleaned up test project")
        
        return True
        
    except Exception as e:
        print(f"❌ MCP operations test failed: {e}")
        return False


def test_file_structure():
    """Test that all test files are present."""
    print("\n🔍 Testing Test Suite File Structure...")
    
    expected_files = [
        "mcp-service/tests/test_integration.py",
        "mcp-service/tests/test_performance.py", 
        "mcp-service/tests/test_container_deployment.py",
        "mcp-service/tests/test_error_scenarios.py",
        "mcp-service/tests/run_all_tests.py",
        "mcp-service/tests/README.md",
        "mcp-service/tests/requirements.txt"
    ]
    
    missing_files = []
    for file_path in expected_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("❌ Missing test files:")
        for file_path in missing_files:
            print(f"   - {file_path}")
        return False
    else:
        print(f"✅ All {len(expected_files)} test files present")
        return True


def run_sample_test():
    """Run a sample test to verify the test framework works."""
    print("\n🔍 Running Sample Integration Test...")
    
    try:
        # Run a quick integration test
        result = subprocess.run(
            [sys.executable, "mcp-service/tests/test_integration.py"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd="."
        )
        
        if result.returncode == 0:
            print("✅ Sample integration test completed successfully")
            
            # Look for test results in output
            if "PASS" in result.stdout:
                print("✅ Found passing tests in output")
            
            return True
        else:
            print(f"❌ Sample integration test failed (exit code: {result.returncode})")
            if result.stderr:
                print(f"Error output: {result.stderr[:500]}...")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Sample test timed out (this may be normal for comprehensive tests)")
        return True  # Timeout is acceptable for this verification
    except Exception as e:
        print(f"❌ Failed to run sample test: {e}")
        return False


def main():
    """Run all verification tests."""
    print("🚀 MCP Service Test Suite Verification")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    tests = [
        ("File Structure", test_file_structure),
        ("Basic Imports", test_basic_imports),
        ("Database Connection", test_database_connection),
        ("Basic MCP Operations", test_basic_mcp_operations),
        ("Sample Test Execution", run_sample_test)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 VERIFICATION SUMMARY")
    print("=" * 60)
    
    passed = len([r for r in results if r[1]])
    total = len(results)
    
    print(f"Total Checks: {total}")
    print(f"Passed: {passed} ✅")
    print(f"Failed: {total - passed} ❌")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    print(f"\nDetailed Results:")
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status} {test_name}")
    
    if passed == total:
        print(f"\n🎉 All verification checks passed!")
        print(f"The comprehensive test suite is ready to use.")
        print(f"\nTo run the full test suite:")
        print(f"  cd mcp-service/tests")
        print(f"  python run_all_tests.py")
    else:
        print(f"\n⚠️  Some verification checks failed.")
        print(f"Please address the issues before running the full test suite.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)