#!/usr/bin/env python3
"""
Container deployment verification tests for MCP service.

This test suite covers:
- Docker container health and startup verification
- Service availability and endpoint accessibility
- Container resource usage monitoring
- Multi-container orchestration testing
- Environment variable configuration validation
"""

import os
import sys
import json
import time
import docker
import requests
import subprocess
from datetime import datetime
from typing import Dict, Any, List, Optional


class ContainerDeploymentTester:
    """Test suite for container deployment verification."""
    
    def __init__(self):
        self.docker_client = docker.from_env()
        self.test_results = []
        self.base_url = "http://localhost:8001"
        self.postgres_url = "postgresql://postgres:postgres@localhost:5432/aiagent_mcp"
        
        # Expected containers
        self.expected_containers = [
            "postgres",
            "mcp-service", 
            "pgadmin"
        ]
    
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
    
    def test_docker_compose_status(self):
        """Test Docker Compose deployment status."""
        try:
            # Check if docker-compose is available
            result = subprocess.run(
                ["docker-compose", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode != 0:
                self.log_result("Docker Compose Availability", False, {
                    "error": "docker-compose command not available",
                    "stderr": result.stderr
                })
                return False
            
            self.log_result("Docker Compose Availability", True, {
                "version": result.stdout.strip(),
                "info": "Docker Compose is available"
            })
            
            # Check docker-compose.yml exists
            compose_file = "docker-compose.yml"
            if not os.path.exists(compose_file):
                self.log_result("Docker Compose File", False, {
                    "error": f"{compose_file} not found in current directory"
                })
                return False
            
            self.log_result("Docker Compose File", True, {
                "info": f"{compose_file} found"
            })
            
            return True
            
        except subprocess.TimeoutExpired:
            self.log_result("Docker Compose Availability", False, {
                "error": "docker-compose command timed out"
            })
            return False
        except Exception as e:
            self.log_result("Docker Compose Availability", False, {
                "error": str(e)
            })
            return False
    
    def test_container_status(self):
        """Test individual container status and health."""
        try:
            containers = self.docker_client.containers.list(all=True)
            container_info = {}
            
            for container in containers:
                # Check if this is one of our expected containers
                container_name = container.name
                if any(expected in container_name.lower() for expected in self.expected_containers):
                    container_info[container_name] = {
                        "status": container.status,
                        "image": container.image.tags[0] if container.image.tags else "unknown",
                        "ports": container.ports,
                        "created": container.attrs.get("Created", "unknown"),
                        "health": self.get_container_health(container)
                    }
            
            # Check if all expected containers are present and running
            running_containers = [
                name for name, info in container_info.items() 
                if info["status"] == "running"
            ]
            
            expected_running = len(self.expected_containers)
            actual_running = len(running_containers)
            
            success = actual_running >= expected_running
            
            self.log_result("Container Status", success, {
                "expected_containers": expected_running,
                "running_containers": actual_running,
                "container_details": container_info,
                "running_container_names": running_containers
            })
            
            return success, container_info
            
        except Exception as e:
            self.log_result("Container Status", False, {
                "error": str(e)
            })
            return False, {}
    
    def get_container_health(self, container) -> Dict[str, Any]:
        """Get container health information."""
        try:
            # Get container stats
            stats = container.stats(stream=False)
            
            # Calculate CPU and memory usage
            cpu_usage = 0
            memory_usage = 0
            memory_limit = 0
            
            if 'cpu_stats' in stats and 'precpu_stats' in stats:
                cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                           stats['precpu_stats']['cpu_usage']['total_usage']
                system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                              stats['precpu_stats']['system_cpu_usage']
                
                if system_delta > 0:
                    cpu_usage = (cpu_delta / system_delta) * 100
            
            if 'memory_stats' in stats:
                memory_usage = stats['memory_stats'].get('usage', 0)
                memory_limit = stats['memory_stats'].get('limit', 0)
            
            return {
                "cpu_usage_percent": round(cpu_usage, 2),
                "memory_usage_bytes": memory_usage,
                "memory_limit_bytes": memory_limit,
                "memory_usage_mb": round(memory_usage / 1024 / 1024, 2),
                "memory_limit_mb": round(memory_limit / 1024 / 1024, 2),
                "status": container.status
            }
            
        except Exception as e:
            return {"error": str(e), "status": container.status}
    
    def test_service_endpoints(self):
        """Test service endpoint accessibility."""
        endpoints = [
            {
                "name": "MCP Service Health",
                "url": f"{self.base_url}/health",
                "method": "GET",
                "expected_status": 200,
                "timeout": 10
            },
            {
                "name": "MCP Service Info",
                "url": f"{self.base_url}/mcp/info",
                "method": "GET", 
                "expected_status": 200,
                "timeout": 10
            },
            {
                "name": "MCP Tools List",
                "url": f"{self.base_url}/mcp/tools",
                "method": "GET",
                "expected_status": 200,
                "timeout": 10
            }
        ]
        
        all_endpoints_healthy = True
        endpoint_results = {}
        
        for endpoint in endpoints:
            try:
                start_time = time.time()
                
                if endpoint["method"] == "GET":
                    response = requests.get(
                        endpoint["url"], 
                        timeout=endpoint["timeout"]
                    )
                else:
                    response = requests.post(
                        endpoint["url"], 
                        timeout=endpoint["timeout"]
                    )
                
                response_time = time.time() - start_time
                
                success = response.status_code == endpoint["expected_status"]
                if not success:
                    all_endpoints_healthy = False
                
                endpoint_results[endpoint["name"]] = {
                    "success": success,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "response_size": len(response.content),
                    "content_type": response.headers.get("content-type", "unknown")
                }
                
                # Try to parse JSON response
                try:
                    json_data = response.json()
                    endpoint_results[endpoint["name"]]["json_valid"] = True
                    endpoint_results[endpoint["name"]]["response_keys"] = list(json_data.keys())
                except:
                    endpoint_results[endpoint["name"]]["json_valid"] = False
                
            except requests.exceptions.Timeout:
                all_endpoints_healthy = False
                endpoint_results[endpoint["name"]] = {
                    "success": False,
                    "error": "Request timeout",
                    "timeout": endpoint["timeout"]
                }
            except requests.exceptions.ConnectionError:
                all_endpoints_healthy = False
                endpoint_results[endpoint["name"]] = {
                    "success": False,
                    "error": "Connection error - service may not be running"
                }
            except Exception as e:
                all_endpoints_healthy = False
                endpoint_results[endpoint["name"]] = {
                    "success": False,
                    "error": str(e)
                }
        
        self.log_result("Service Endpoints", all_endpoints_healthy, {
            "total_endpoints": len(endpoints),
            "healthy_endpoints": len([r for r in endpoint_results.values() if r.get("success")]),
            "endpoint_details": endpoint_results
        })
        
        return all_endpoints_healthy
    
    def test_database_connectivity(self):
        """Test database connectivity from outside containers."""
        try:
            import psycopg2
            
            # Test direct database connection
            start_time = time.time()
            conn = psycopg2.connect(self.postgres_url)
            connection_time = time.time() - start_time
            
            # Test basic query
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()[0]
            
            # Test our tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_name IN ('projects', 'tasks');
            """)
            tables = [row[0] for row in cursor.fetchall()]
            
            # Test data exists
            cursor.execute("SELECT COUNT(*) FROM projects;")
            project_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM tasks;")
            task_count = cursor.fetchone()[0]
            
            cursor.close()
            conn.close()
            
            expected_tables = {'projects', 'tasks'}
            tables_exist = set(tables) == expected_tables
            
            self.log_result("Database Connectivity", True, {
                "connection_time": connection_time,
                "database_version": db_version,
                "tables_found": tables,
                "tables_exist": tables_exist,
                "project_count": project_count,
                "task_count": task_count,
                "info": f"Connected successfully in {connection_time:.3f}s"
            })
            
            return True
            
        except ImportError:
            self.log_result("Database Connectivity", False, {
                "error": "psycopg2 not available for direct database testing"
            })
            return False
        except Exception as e:
            self.log_result("Database Connectivity", False, {
                "error": str(e)
            })
            return False
    
    def test_environment_configuration(self):
        """Test environment variable configuration."""
        try:
            # Check if .env file exists
            env_file_exists = os.path.exists(".env")
            env_example_exists = os.path.exists(".env.example")
            
            required_env_vars = [
                "POSTGRES_USER",
                "POSTGRES_PASSWORD", 
                "POSTGRES_DB",
                "DATABASE_URL",
                "PGADMIN_DEFAULT_EMAIL",
                "PGADMIN_DEFAULT_PASSWORD"
            ]
            
            missing_vars = []
            present_vars = []
            
            for var in required_env_vars:
                if os.getenv(var):
                    present_vars.append(var)
                else:
                    missing_vars.append(var)
            
            # Test MCP service can access environment
            try:
                response = requests.get(f"{self.base_url}/health", timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    database_connected = health_data.get("database_connected", False)
                else:
                    database_connected = False
            except:
                database_connected = False
            
            success = (
                env_example_exists and 
                len(missing_vars) == 0 and 
                database_connected
            )
            
            self.log_result("Environment Configuration", success, {
                "env_file_exists": env_file_exists,
                "env_example_exists": env_example_exists,
                "required_vars": required_env_vars,
                "present_vars": present_vars,
                "missing_vars": missing_vars,
                "database_connected_via_service": database_connected
            })
            
            return success
            
        except Exception as e:
            self.log_result("Environment Configuration", False, {
                "error": str(e)
            })
            return False
    
    def test_container_logs(self):
        """Test container logs for errors and warnings."""
        try:
            containers = self.docker_client.containers.list()
            log_analysis = {}
            
            for container in containers:
                if any(expected in container.name.lower() for expected in self.expected_containers):
                    try:
                        # Get recent logs
                        logs = container.logs(tail=100, timestamps=True).decode('utf-8')
                        
                        # Analyze logs for errors and warnings
                        log_lines = logs.split('\n')
                        errors = [line for line in log_lines if 'ERROR' in line.upper()]
                        warnings = [line for line in log_lines if 'WARNING' in line.upper()]
                        
                        log_analysis[container.name] = {
                            "total_log_lines": len(log_lines),
                            "error_count": len(errors),
                            "warning_count": len(warnings),
                            "recent_errors": errors[-5:] if errors else [],
                            "recent_warnings": warnings[-5:] if warnings else [],
                            "log_size_bytes": len(logs)
                        }
                        
                    except Exception as e:
                        log_analysis[container.name] = {
                            "error": f"Could not retrieve logs: {str(e)}"
                        }
            
            # Determine if logs look healthy
            total_errors = sum(
                analysis.get("error_count", 0) 
                for analysis in log_analysis.values()
                if isinstance(analysis.get("error_count"), int)
            )
            
            # Allow some errors but not too many
            logs_healthy = total_errors < 10
            
            self.log_result("Container Logs Analysis", logs_healthy, {
                "total_errors_found": total_errors,
                "containers_analyzed": len(log_analysis),
                "log_details": log_analysis
            })
            
            return logs_healthy
            
        except Exception as e:
            self.log_result("Container Logs Analysis", False, {
                "error": str(e)
            })
            return False
    
    def test_resource_usage(self):
        """Test container resource usage."""
        try:
            containers = self.docker_client.containers.list()
            resource_info = {}
            total_memory_mb = 0
            total_cpu_percent = 0
            
            for container in containers:
                if any(expected in container.name.lower() for expected in self.expected_containers):
                    health_info = self.get_container_health(container)
                    resource_info[container.name] = health_info
                    
                    if "memory_usage_mb" in health_info:
                        total_memory_mb += health_info["memory_usage_mb"]
                    if "cpu_usage_percent" in health_info:
                        total_cpu_percent += health_info["cpu_usage_percent"]
            
            # Check if resource usage is reasonable
            memory_reasonable = total_memory_mb < 1000  # Less than 1GB total
            cpu_reasonable = total_cpu_percent < 200    # Less than 200% total CPU
            
            success = memory_reasonable and cpu_reasonable
            
            self.log_result("Resource Usage", success, {
                "total_memory_mb": round(total_memory_mb, 2),
                "total_cpu_percent": round(total_cpu_percent, 2),
                "memory_reasonable": memory_reasonable,
                "cpu_reasonable": cpu_reasonable,
                "container_resources": resource_info
            })
            
            return success
            
        except Exception as e:
            self.log_result("Resource Usage", False, {
                "error": str(e)
            })
            return False
    
    def test_service_integration(self):
        """Test integration between services."""
        try:
            # Test MCP service can create and retrieve data (indicating DB connection works)
            test_data = {
                "name": "Container Test Project",
                "description": "Testing container deployment integration",
                "status": "active"
            }
            
            # Create project via MCP service
            create_response = requests.post(
                f"{self.base_url}/mcp/tools/create_project_tool",
                json=test_data,
                timeout=10
            )
            
            create_success = create_response.status_code == 200
            if create_success:
                create_data = create_response.json()
                create_success = create_data.get("success", False)
            
            # List projects to verify creation
            list_response = requests.post(
                f"{self.base_url}/mcp/tools/list_projects_tool",
                json={},
                timeout=10
            )
            
            list_success = list_response.status_code == 200
            project_found = False
            
            if list_success:
                list_data = list_response.json()
                list_success = list_data.get("success", False)
                
                if list_success and "data" in list_data:
                    projects = list_data["data"]
                    project_found = any(
                        p.get("name") == test_data["name"] 
                        for p in projects
                    )
            
            # Clean up - delete the test project
            if create_success and create_data.get("data", {}).get("id"):
                project_id = create_data["data"]["id"]
                requests.post(
                    f"{self.base_url}/mcp/tools/delete_project_tool",
                    json={"project_id": project_id},
                    timeout=10
                )
            
            integration_success = create_success and list_success and project_found
            
            self.log_result("Service Integration", integration_success, {
                "create_project_success": create_success,
                "list_projects_success": list_success,
                "project_found_in_list": project_found,
                "mcp_to_database_working": integration_success
            })
            
            return integration_success
            
        except Exception as e:
            self.log_result("Service Integration", False, {
                "error": str(e)
            })
            return False
    
    def generate_report(self):
        """Generate deployment verification report."""
        print("\n" + "=" * 60)
        print("📊 CONTAINER DEPLOYMENT TEST REPORT")
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
        
        # Save detailed results
        with open("container_deployment_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100,
                    "timestamp": datetime.now().isoformat()
                },
                "results": self.test_results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: container_deployment_test_results.json")
    
    def run_all_tests(self):
        """Run all container deployment tests."""
        print("🚀 Starting Container Deployment Verification Tests")
        print("=" * 60)
        
        # Test sequence
        tests = [
            ("Docker Compose Status", self.test_docker_compose_status),
            ("Container Status", lambda: self.test_container_status()[0]),
            ("Service Endpoints", self.test_service_endpoints),
            ("Database Connectivity", self.test_database_connectivity),
            ("Environment Configuration", self.test_environment_configuration),
            ("Container Logs", self.test_container_logs),
            ("Resource Usage", self.test_resource_usage),
            ("Service Integration", self.test_service_integration)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                test_func()
            except Exception as e:
                self.log_result(test_name, False, {"error": str(e)})
        
        # Generate final report
        self.generate_report()


if __name__ == "__main__":
    # Install required packages if not available
    try:
        import docker
        import requests
    except ImportError:
        print("Installing required packages...")
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", 
            "docker", "requests", "psutil"
        ])
        import docker
        import requests
    
    tester = ContainerDeploymentTester()
    tester.run_all_tests()