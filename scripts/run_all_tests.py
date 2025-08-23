#!/usr/bin/env python3
"""
Test runner script that executes all development and testing utilities.
Provides a single command to run all tests and checks.
"""

import subprocess
import sys
import os
from typing import List, Tuple


class TestRunner:
    """Runs all development and testing utilities."""
    
    def __init__(self):
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.results = []
    
    def run_script(self, script_name: str, description: str) -> bool:
        """Run a test script and capture results."""
        script_path = os.path.join(self.script_dir, script_name)
        
        print(f"🧪 Running {description}...")
        print("-" * 50)
        
        try:
            # Run the script and capture output
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=False,  # Show output in real-time
                text=True,
                timeout=60  # 60 second timeout
            )
            
            success = result.returncode == 0
            self.results.append((description, success))
            
            if success:
                print(f"✅ {description} completed successfully\n")
            else:
                print(f"❌ {description} failed with exit code {result.returncode}\n")
            
            return success
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {description} timed out after 60 seconds\n")
            self.results.append((description, False))
            return False
        except Exception as e:
            print(f"💥 {description} failed with error: {e}\n")
            self.results.append((description, False))
            return False
    
    def print_summary(self):
        """Print summary of all test results."""
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = 0
        total = len(self.results)
        
        for description, success in self.results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {description}")
            if success:
                passed += 1
        
        print("-" * 60)
        print(f"Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests completed successfully!")
            print("Your development environment is ready to use.")
        else:
            print("⚠️  Some tests failed!")
            print("Check the output above for specific issues.")
            print("Refer to docs/DEVELOPMENT_GUIDE.md for troubleshooting.")
        
        return passed == total
    
    def run_all_tests(self) -> bool:
        """Run all development and testing utilities."""
        print("🚀 AI Agent MCP Service - Development Test Suite")
        print("=" * 60)
        print("This will run all development utilities to verify your setup.\n")
        
        # List of tests to run
        tests = [
            ("health_check.py", "Service Health Checks"),
            ("test_database.py", "Database Connectivity Tests"),
            ("api_examples.py", "API Endpoint Examples")
        ]
        
        # Run each test
        for script, description in tests:
            self.run_script(script, description)
        
        # Print summary
        return self.print_summary()


def main():
    """Main function to run all tests."""
    runner = TestRunner()
    
    try:
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Test suite interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error in test suite: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()