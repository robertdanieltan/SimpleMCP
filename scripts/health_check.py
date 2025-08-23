#!/usr/bin/env python3
"""
Health check script for all services in the AI Agent MCP Service project.
Tests connectivity and basic functionality of all services.
"""

import requests
import time
import sys
import json
from typing import Dict, Any, Optional


class HealthChecker:
    """Health checker for all project services."""
    
    def __init__(self):
        self.services = {
            'ai-agent': 'http://localhost:8000',
            'mcp-service': 'http://localhost:8001'
        }
        self.pgadmin_url = 'http://localhost:8080'
        self.results = {}
    
    def check_service_health(self, service_name: str, base_url: str) -> Dict[str, Any]:
        """Check health of a specific service."""
        result = {
            'service': service_name,
            'url': base_url,
            'status': 'unknown',
            'response_time': None,
            'details': {}
        }
        
        try:
            start_time = time.time()
            
            # Try health endpoint first
            health_url = f"{base_url}/health"
            response = requests.get(health_url, timeout=10)
            
            end_time = time.time()
            result['response_time'] = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                result['status'] = 'healthy'
                try:
                    result['details'] = response.json()
                except json.JSONDecodeError:
                    result['details'] = {'response': response.text[:200]}
            else:
                result['status'] = 'unhealthy'
                result['details'] = {
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
                
        except requests.exceptions.ConnectionError:
            result['status'] = 'unreachable'
            result['details'] = {'error': 'Connection refused - service may not be running'}
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['details'] = {'error': 'Request timed out after 10 seconds'}
        except Exception as e:
            result['status'] = 'error'
            result['details'] = {'error': str(e)}
        
        return result
    
    def check_pgadmin_health(self) -> Dict[str, Any]:
        """Check pgAdmin web interface availability."""
        result = {
            'service': 'pgadmin',
            'url': self.pgadmin_url,
            'status': 'unknown',
            'response_time': None,
            'details': {}
        }
        
        try:
            start_time = time.time()
            
            # pgAdmin doesn't have /health, so check root page
            response = requests.get(self.pgadmin_url, timeout=10)
            
            end_time = time.time()
            result['response_time'] = round((end_time - start_time) * 1000, 2)
            
            if response.status_code == 200:
                result['status'] = 'healthy'
                result['details'] = {'message': 'pgAdmin web interface accessible'}
            else:
                result['status'] = 'unhealthy'
                result['details'] = {
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
                
        except requests.exceptions.ConnectionError:
            result['status'] = 'unreachable'
            result['details'] = {'error': 'Connection refused - pgAdmin may not be running'}
        except requests.exceptions.Timeout:
            result['status'] = 'timeout'
            result['details'] = {'error': 'Request timed out after 10 seconds'}
        except Exception as e:
            result['status'] = 'error'
            result['details'] = {'error': str(e)}
        
        return result
    
    def check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity through MCP service."""
        result = {
            'service': 'database',
            'status': 'unknown',
            'details': {}
        }
        
        try:
            # Try to list projects through MCP service to test database
            mcp_url = self.services['mcp-service']
            response = requests.post(
                f"{mcp_url}/mcp/tools/list_projects",
                json={},
                timeout=10
            )
            
            if response.status_code == 200:
                result['status'] = 'healthy'
                result['details'] = {'message': 'Database accessible through MCP service'}
            else:
                result['status'] = 'unhealthy'
                result['details'] = {
                    'status_code': response.status_code,
                    'response': response.text[:200]
                }
                
        except Exception as e:
            result['status'] = 'error'
            result['details'] = {'error': str(e)}
        
        return result
    
    def run_all_checks(self) -> Dict[str, Any]:
        """Run health checks for all services."""
        print("🔍 Running health checks for all services...\n")
        
        # Check each service
        for service_name, base_url in self.services.items():
            print(f"Checking {service_name}...")
            result = self.check_service_health(service_name, base_url)
            self.results[service_name] = result
            
            status_emoji = {
                'healthy': '✅',
                'unhealthy': '❌',
                'unreachable': '🔌',
                'timeout': '⏰',
                'error': '💥',
                'unknown': '❓'
            }.get(result['status'], '❓')
            
            print(f"  {status_emoji} {service_name}: {result['status']}")
            if result['response_time']:
                print(f"     Response time: {result['response_time']}ms")
            if result['details']:
                if 'error' in result['details']:
                    print(f"     Error: {result['details']['error']}")
            print()
        
        # Check pgAdmin separately
        print("Checking pgadmin...")
        pgadmin_result = self.check_pgadmin_health()
        self.results['pgadmin'] = pgadmin_result
        
        status_emoji = {
            'healthy': '✅',
            'unhealthy': '❌',
            'unreachable': '🔌',
            'timeout': '⏰',
            'error': '💥',
            'unknown': '❓'
        }.get(pgadmin_result['status'], '❓')
        
        print(f"  {status_emoji} pgadmin: {pgadmin_result['status']}")
        if pgadmin_result['response_time']:
            print(f"     Response time: {pgadmin_result['response_time']}ms")
        if pgadmin_result['details']:
            if 'error' in pgadmin_result['details']:
                print(f"     Error: {pgadmin_result['details']['error']}")
            elif 'message' in pgadmin_result['details']:
                print(f"     {pgadmin_result['details']['message']}")
        print()
        
        # Check database connectivity
        print("Checking database connectivity...")
        db_result = self.check_database_connectivity()
        self.results['database'] = db_result
        
        status_emoji = {
            'healthy': '✅',
            'unhealthy': '❌',
            'error': '💥',
            'unknown': '❓'
        }.get(db_result['status'], '❓')
        
        print(f"  {status_emoji} database: {db_result['status']}")
        if db_result['details']:
            if 'error' in db_result['details']:
                print(f"     Error: {db_result['details']['error']}")
            elif 'message' in db_result['details']:
                print(f"     {db_result['details']['message']}")
        print()
        
        return self.results
    
    def print_summary(self):
        """Print summary of health check results."""
        healthy_count = sum(1 for result in self.results.values() if result['status'] == 'healthy')
        total_count = len(self.results)
        
        print("=" * 50)
        print(f"Health Check Summary: {healthy_count}/{total_count} services healthy")
        print("=" * 50)
        
        if healthy_count == total_count:
            print("🎉 All services are running and healthy!")
            return True
        else:
            print("⚠️  Some services need attention:")
            for service, result in self.results.items():
                if result['status'] != 'healthy':
                    print(f"   - {service}: {result['status']}")
            return False


def main():
    """Main function to run health checks."""
    checker = HealthChecker()
    
    try:
        results = checker.run_all_checks()
        all_healthy = checker.print_summary()
        
        # Exit with appropriate code
        sys.exit(0 if all_healthy else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Health check interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"💥 Unexpected error during health check: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()