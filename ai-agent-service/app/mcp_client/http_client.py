"""
MCP HTTP Client for AI Agent Service

This module provides an HTTP client for communicating with the MCP service.
It includes retry logic with exponential backoff and proper error handling.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

logger = logging.getLogger(__name__)


class MCPClientError(Exception):
    """Base exception for MCP client errors"""
    pass


class MCPServiceUnavailableError(MCPClientError):
    """Raised when MCP service is unavailable"""
    pass


class MCPToolError(MCPClientError):
    """Raised when MCP tool execution fails"""
    pass


class MCPHTTPClient:
    """
    HTTP client for communicating with the MCP service.
    
    Provides methods for calling all MCP tools with retry logic,
    exponential backoff, and proper error handling.
    """
    
    def __init__(self, base_url: Optional[str] = None, timeout: int = 30):
        """
        Initialize the MCP HTTP client.
        
        Args:
            base_url: Base URL of the MCP service (defaults to environment variable)
            timeout: Request timeout in seconds (default: 30)
        """
        self.base_url = base_url or os.getenv("MCP_SERVICE_URL", "http://mcp-service:8001")
        self.timeout = timeout
        
        # Configure session with retry strategy
        self.session = requests.Session()
        
        # Retry strategy with exponential backoff
        retry_strategy = Retry(
            total=3,  # Total number of retries
            backoff_factor=1,  # Exponential backoff factor (1, 2, 4 seconds)
            status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry
            allowed_methods=["HEAD", "GET", "POST", "PUT", "DELETE", "OPTIONS", "TRACE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "AI-Agent-Service/1.0.0"
        })
        
        logger.info(f"Initialized MCP HTTP client with base URL: {self.base_url}")
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make an HTTP request to the MCP service with error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            data: Request data (for POST requests)
        
        Returns:
            Dict containing the response data
        
        Raises:
            MCPServiceUnavailableError: When service is unavailable
            MCPToolError: When tool execution fails
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            logger.debug(f"Making {method} request to {url}")
            
            if method.upper() == "GET":
                response = self.session.get(url, timeout=self.timeout)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data, timeout=self.timeout)
            else:
                raise MCPClientError(f"Unsupported HTTP method: {method}")
            
            # Check if request was successful
            response.raise_for_status()
            
            # Parse JSON response
            try:
                result = response.json()
                logger.debug(f"Received response: {result}")
                return result
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON response: {e}")
                raise MCPToolError(f"Invalid JSON response from MCP service: {e}")
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to MCP service: {e}")
            raise MCPServiceUnavailableError(f"Cannot connect to MCP service at {url}: {e}")
        
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error to MCP service: {e}")
            raise MCPServiceUnavailableError(f"Timeout connecting to MCP service at {url}: {e}")
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error from MCP service: {e}")
            if e.response.status_code >= 500:
                raise MCPServiceUnavailableError(f"MCP service error (HTTP {e.response.status_code}): {e}")
            else:
                raise MCPToolError(f"MCP tool error (HTTP {e.response.status_code}): {e}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error to MCP service: {e}")
            raise MCPServiceUnavailableError(f"Request failed to MCP service: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the MCP service.
        
        Returns:
            Dict containing health status
        """
        try:
            return self._make_request("GET", "/health")
        except Exception as e:
            logger.error(f"MCP service health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }
    
    def list_tools(self) -> Dict[str, Any]:
        """
        List all available MCP tools.
        
        Returns:
            Dict containing list of available tools
        """
        return self._make_request("GET", "/mcp/tools")
    
    def get_mcp_info(self) -> Dict[str, Any]:
        """
        Get MCP server information.
        
        Returns:
            Dict containing MCP server info
        """
        return self._make_request("GET", "/mcp/info")
    
    # Task Management Methods
    
    def create_task(
        self,
        title: str,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        status: str = "pending",
        priority: str = "medium",
        assigned_to: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new task via MCP service.
        
        Args:
            title: Task title (required)
            description: Task description (optional)
            project_id: Associated project ID (optional)
            status: Task status (default: "pending")
            priority: Task priority (default: "medium")
            assigned_to: Assigned user (optional)
            due_date: Due date in YYYY-MM-DD format (optional)
        
        Returns:
            Dict containing task creation result
        """
        data = {
            "title": title,
            "description": description,
            "project_id": project_id,
            "status": status,
            "priority": priority,
            "assigned_to": assigned_to,
            "due_date": due_date
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        return self._make_request("POST", "/mcp/tools/create_task_tool", data)
    
    def list_tasks(
        self,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List tasks with optional filtering via MCP service.
        
        Args:
            project_id: Filter by project ID (optional)
            status: Filter by status (optional)
            assigned_to: Filter by assignee (optional)
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)
        
        Returns:
            Dict containing list of tasks
        """
        data = {
            "project_id": project_id,
            "status": status,
            "assigned_to": assigned_to,
            "limit": limit,
            "offset": offset
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        return self._make_request("POST", "/mcp/tools/list_tasks_tool", data)
    
    def update_task(
        self,
        task_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        project_id: Optional[int] = None,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        assigned_to: Optional[str] = None,
        due_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing task via MCP service.
        
        Args:
            task_id: Task ID to update (required)
            title: New task title (optional)
            description: New task description (optional)
            project_id: New project ID (optional)
            status: New task status (optional)
            priority: New task priority (optional)
            assigned_to: New assignee (optional)
            due_date: New due date in YYYY-MM-DD format (optional)
        
        Returns:
            Dict containing task update result
        """
        data = {
            "task_id": task_id,
            "title": title,
            "description": description,
            "project_id": project_id,
            "status": status,
            "priority": priority,
            "assigned_to": assigned_to,
            "due_date": due_date
        }
        
        # Remove None values except task_id
        data = {k: v for k, v in data.items() if v is not None or k == "task_id"}
        
        return self._make_request("POST", "/mcp/tools/update_task_tool", data)
    
    def delete_task(self, task_id: int) -> Dict[str, Any]:
        """
        Delete a task via MCP service.
        
        Args:
            task_id: Task ID to delete (required)
        
        Returns:
            Dict containing task deletion result
        """
        data = {"task_id": task_id}
        return self._make_request("POST", "/mcp/tools/delete_task_tool", data)
    
    # Project Management Methods
    
    def create_project(
        self,
        name: str,
        description: Optional[str] = None,
        status: str = "active"
    ) -> Dict[str, Any]:
        """
        Create a new project via MCP service.
        
        Args:
            name: Project name (required)
            description: Project description (optional)
            status: Project status (default: "active")
        
        Returns:
            Dict containing project creation result
        """
        data = {
            "name": name,
            "description": description,
            "status": status
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        return self._make_request("POST", "/mcp/tools/create_project_tool", data)
    
    def list_projects(
        self,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List projects with optional filtering via MCP service.
        
        Args:
            status: Filter by status (optional)
            limit: Maximum number of results (default: 100)
            offset: Number of results to skip (default: 0)
        
        Returns:
            Dict containing list of projects
        """
        data = {
            "status": status,
            "limit": limit,
            "offset": offset
        }
        
        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}
        
        return self._make_request("POST", "/mcp/tools/list_projects_tool", data)
    
    def update_project(
        self,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update an existing project via MCP service.
        
        Args:
            project_id: Project ID to update (required)
            name: New project name (optional)
            description: New project description (optional)
            status: New project status (optional)
        
        Returns:
            Dict containing project update result
        """
        data = {
            "project_id": project_id,
            "name": name,
            "description": description,
            "status": status
        }
        
        # Remove None values except project_id
        data = {k: v for k, v in data.items() if v is not None or k == "project_id"}
        
        return self._make_request("POST", "/mcp/tools/update_project_tool", data)
    
    def delete_project(self, project_id: int) -> Dict[str, Any]:
        """
        Delete a project and all associated tasks via MCP service.
        
        Args:
            project_id: Project ID to delete (required)
        
        Returns:
            Dict containing project deletion result
        """
        data = {"project_id": project_id}
        return self._make_request("POST", "/mcp/tools/delete_project_tool", data)


# Global client instance
_mcp_client: Optional[MCPHTTPClient] = None


def get_mcp_client() -> MCPHTTPClient:
    """
    Get a singleton instance of the MCP HTTP client.
    
    Returns:
        MCPHTTPClient instance
    """
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPHTTPClient()
    return _mcp_client


def reset_mcp_client():
    """Reset the global MCP client instance (useful for testing)."""
    global _mcp_client
    _mcp_client = None


# Alias for backward compatibility
MCPClient = MCPHTTPClient