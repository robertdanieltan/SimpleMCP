#!/usr/bin/env python3
"""
Test script for MCP HTTP Client

This script tests the MCP HTTP client functionality by making calls
to the MCP service and verifying responses.
"""

import sys
import os
import logging
from typing import Dict, Any

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from mcp_client.http_client import MCPHTTPClient, MCPServiceUnavailableError, MCPToolError

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def test_mcp_client():
    """Test the MCP HTTP client functionality."""
    
    # Initialize client with localhost URL for testing
    client = MCPHTTPClient(base_url="http://localhost:8001")
    
    print("=" * 60)
    print("Testing MCP HTTP Client")
    print("=" * 60)
    
    # Test 1: Health Check
    print("\n1. Testing health check...")
    try:
        health = client.health_check()
        print(f"✓ Health check result: {health}")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False
    
    # Test 2: List Tools
    print("\n2. Testing tool listing...")
    try:
        tools = client.list_tools()
        print(f"✓ Available tools: {tools}")
    except Exception as e:
        print(f"✗ Tool listing failed: {e}")
        return False
    
    # Test 3: MCP Info
    print("\n3. Testing MCP info...")
    try:
        info = client.get_mcp_info()
        print(f"✓ MCP info: {info}")
    except Exception as e:
        print(f"✗ MCP info failed: {e}")
        return False
    
    # Test 4: Create Project
    print("\n4. Testing project creation...")
    try:
        project_result = client.create_project(
            name="Test Project via HTTP Client",
            description="Testing HTTP client functionality",
            status="active"
        )
        print(f"✓ Project creation result: {project_result}")
        
        if project_result.get("success") and project_result.get("data"):
            project_id = project_result["data"]["data"]["id"]
            print(f"✓ Created project with ID: {project_id}")
        else:
            print("✗ Project creation did not return expected data")
            return False
    except Exception as e:
        print(f"✗ Project creation failed: {e}")
        return False
    
    # Test 5: List Projects
    print("\n5. Testing project listing...")
    try:
        projects = client.list_projects()
        print(f"✓ Projects list: {projects}")
    except Exception as e:
        print(f"✗ Project listing failed: {e}")
        return False
    
    # Test 6: Create Task
    print("\n6. Testing task creation...")
    try:
        task_result = client.create_task(
            title="Test Task via HTTP Client",
            description="Testing HTTP client task creation",
            project_id=project_id,
            status="pending",
            priority="medium"
        )
        print(f"✓ Task creation result: {task_result}")
        
        if task_result.get("success") and task_result.get("data"):
            task_id = task_result["data"]["data"]["id"]
            print(f"✓ Created task with ID: {task_id}")
        else:
            print("✗ Task creation did not return expected data")
            return False
    except Exception as e:
        print(f"✗ Task creation failed: {e}")
        return False
    
    # Test 7: List Tasks
    print("\n7. Testing task listing...")
    try:
        tasks = client.list_tasks(project_id=project_id)
        print(f"✓ Tasks list: {tasks}")
    except Exception as e:
        print(f"✗ Task listing failed: {e}")
        return False
    
    # Test 8: Update Task
    print("\n8. Testing task update...")
    try:
        update_result = client.update_task(
            task_id=task_id,
            status="in_progress",
            priority="high"
        )
        print(f"✓ Task update result: {update_result}")
    except Exception as e:
        print(f"✗ Task update failed: {e}")
        return False
    
    # Test 9: Update Project
    print("\n9. Testing project update...")
    try:
        project_update_result = client.update_project(
            project_id=project_id,
            description="Updated description via HTTP client"
        )
        print(f"✓ Project update result: {project_update_result}")
    except Exception as e:
        print(f"✗ Project update failed: {e}")
        return False
    
    # Test 10: Error Handling (try to get non-existent task)
    print("\n10. Testing error handling...")
    try:
        error_result = client.update_task(task_id=99999, title="Non-existent task")
        print(f"✓ Error handling result: {error_result}")
    except Exception as e:
        print(f"✓ Expected error caught: {e}")
    
    print("\n" + "=" * 60)
    print("All tests completed successfully!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_mcp_client()
    sys.exit(0 if success else 1)