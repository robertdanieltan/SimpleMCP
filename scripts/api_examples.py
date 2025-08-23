#!/usr/bin/env python3
"""
API request examples for testing the AI Agent MCP Service project.
Demonstrates how to interact with both AI Agent and MCP services.
"""

import requests
import json
import time
from typing import Dict, Any, Optional


class APIExamples:
    """Collection of API request examples for testing services."""
    
    def __init__(self):
        self.ai_agent_url = "http://localhost:8000"
        self.mcp_service_url = "http://localhost:8001"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
    
    def print_request(self, method: str, url: str, data: Optional[Dict] = None):
        """Print formatted request details."""
        print(f"📤 {method} {url}")
        if data:
            print(f"   Body: {json.dumps(data, indent=2)}")
    
    def print_response(self, response: requests.Response):
        """Print formatted response details."""
        status_emoji = "✅" if response.status_code < 400 else "❌"
        print(f"📥 {status_emoji} {response.status_code} {response.reason}")
        
        try:
            response_data = response.json()
            print(f"   Response: {json.dumps(response_data, indent=2)}")
        except json.JSONDecodeError:
            print(f"   Response: {response.text[:200]}...")
        print()
    
    def test_ai_agent_health(self):
        """Test AI Agent service health endpoint."""
        print("🤖 Testing AI Agent Service Health")
        print("-" * 40)
        
        url = f"{self.ai_agent_url}/health"
        self.print_request("GET", url)
        
        try:
            response = self.session.get(url, timeout=10)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def test_ai_agent_status(self):
        """Test AI Agent status endpoint."""
        print("🤖 Testing AI Agent Status")
        print("-" * 40)
        
        url = f"{self.ai_agent_url}/agent/status"
        self.print_request("GET", url)
        
        try:
            response = self.session.get(url, timeout=10)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def test_ai_agent_process(self):
        """Test AI Agent process endpoint with sample request."""
        print("🤖 Testing AI Agent Process Request")
        print("-" * 40)
        
        url = f"{self.ai_agent_url}/agent/process"
        data = {
            "user_input": "List all projects in the system",
            "context": {
                "user_id": "test_user",
                "session_id": "test_session"
            }
        }
        
        self.print_request("POST", url, data)
        
        try:
            response = self.session.post(url, json=data, timeout=30)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def test_mcp_service_health(self):
        """Test MCP service health endpoint."""
        print("🔧 Testing MCP Service Health")
        print("-" * 40)
        
        url = f"{self.mcp_service_url}/health"
        self.print_request("GET", url)
        
        try:
            response = self.session.get(url, timeout=10)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def test_mcp_list_projects(self):
        """Test MCP service list projects tool."""
        print("🔧 Testing MCP List Projects Tool")
        print("-" * 40)
        
        url = f"{self.mcp_service_url}/mcp/tools/list_projects"
        data = {}
        
        self.print_request("POST", url, data)
        
        try:
            response = self.session.post(url, json=data, timeout=10)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def test_mcp_create_project(self):
        """Test MCP service create project tool."""
        print("🔧 Testing MCP Create Project Tool")
        print("-" * 40)
        
        url = f"{self.mcp_service_url}/mcp/tools/create_project"
        data = {
            "name": f"API Test Project {int(time.time())}",
            "description": "Project created via API testing script",
            "status": "active"
        }
        
        self.print_request("POST", url, data)
        
        try:
            response = self.session.post(url, json=data, timeout=10)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def test_mcp_list_tasks(self):
        """Test MCP service list tasks tool."""
        print("🔧 Testing MCP List Tasks Tool")
        print("-" * 40)
        
        url = f"{self.mcp_service_url}/mcp/tools/list_tasks"
        data = {
            "limit": 5
        }
        
        self.print_request("POST", url, data)
        
        try:
            response = self.session.post(url, json=data, timeout=10)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def test_mcp_create_task(self):
        """Test MCP service create task tool."""
        print("🔧 Testing MCP Create Task Tool")
        print("-" * 40)
        
        url = f"{self.mcp_service_url}/mcp/tools/create_task"
        data = {
            "title": f"API Test Task {int(time.time())}",
            "description": "Task created via API testing script",
            "status": "pending",
            "priority": "medium"
        }
        
        self.print_request("POST", url, data)
        
        try:
            response = self.session.post(url, json=data, timeout=10)
            self.print_response(response)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Request failed: {e}\n")
            return False
    
    def run_all_examples(self):
        """Run all API examples."""
        print("🧪 Running API Request Examples")
        print("=" * 50)
        print()
        
        results = {}
        
        # AI Agent Service tests
        results['ai_agent_health'] = self.test_ai_agent_health()
        results['ai_agent_status'] = self.test_ai_agent_status()
        results['ai_agent_process'] = self.test_ai_agent_process()
        
        # MCP Service tests
        results['mcp_health'] = self.test_mcp_service_health()
        results['mcp_list_projects'] = self.test_mcp_list_projects()
        results['mcp_create_project'] = self.test_mcp_create_project()
        results['mcp_list_tasks'] = self.test_mcp_list_tasks()
        results['mcp_create_task'] = self.test_mcp_create_task()
        
        # Print summary
        print("=" * 50)
        print("API Examples Summary")
        print("=" * 50)
        
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        for test_name, success in results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} {test_name}")
        
        print(f"\nResults: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All API examples completed successfully!")
        else:
            print("⚠️  Some API examples failed - check service status")
        
        return passed == total


def print_curl_examples():
    """Print curl command examples for manual testing."""
    print("\n📋 Curl Command Examples")
    print("=" * 50)
    
    examples = [
        {
            "description": "AI Agent Health Check",
            "command": "curl -X GET http://localhost:8000/health"
        },
        {
            "description": "AI Agent Status",
            "command": "curl -X GET http://localhost:8000/agent/status"
        },
        {
            "description": "AI Agent Process Request",
            "command": '''curl -X POST http://localhost:8000/agent/process \\
  -H "Content-Type: application/json" \\
  -d '{
    "user_input": "List all projects",
    "context": {"user_id": "test"}
  }' '''
        },
        {
            "description": "MCP Service Health Check",
            "command": "curl -X GET http://localhost:8001/health"
        },
        {
            "description": "MCP List Projects",
            "command": '''curl -X POST http://localhost:8001/mcp/tools/list_projects \\
  -H "Content-Type: application/json" \\
  -d '{}' '''
        },
        {
            "description": "MCP Create Project",
            "command": '''curl -X POST http://localhost:8001/mcp/tools/create_project \\
  -H "Content-Type: application/json" \\
  -d '{
    "name": "Test Project",
    "description": "Created via curl",
    "status": "active"
  }' '''
        },
        {
            "description": "MCP List Tasks",
            "command": '''curl -X POST http://localhost:8001/mcp/tools/list_tasks \\
  -H "Content-Type: application/json" \\
  -d '{"limit": 10}' '''
        }
    ]
    
    for i, example in enumerate(examples, 1):
        print(f"\n{i}. {example['description']}")
        print("-" * len(f"{i}. {example['description']}"))
        print(example['command'])


def main():
    """Main function to run API examples."""
    try:
        examples = APIExamples()
        success = examples.run_all_examples()
        
        # Print curl examples for reference
        print_curl_examples()
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ API examples interrupted by user")
        return 1
    except Exception as e:
        print(f"💥 Unexpected error during API examples: {e}")
        return 1


if __name__ == "__main__":
    exit(main())