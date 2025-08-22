"""
MCP Service Main Application

FastMCP-based service for task and project management tools.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from fastmcp import FastMCP
from fastapi import FastAPI

# Import tool functions
from app.tools.task_tools import create_task, list_tasks, update_task, delete_task
from app.tools.project_tools import create_project, list_projects, update_project, delete_project
from app.database.connection import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize FastMCP application
mcp_app = FastMCP("Task Management MCP Service")

# Create FastAPI app for HTTP endpoints
app = FastAPI(title="MCP Task Management Service", version="1.0.0")

# Health check endpoint
@app.get("/health")
def health() -> Dict[str, Any]:
    """
    Health check endpoint for the MCP service.
    
    Returns:
        Dict containing service health status and database connectivity
    """
    try:
        # Test database connection
        db = get_db_connection()
        database_connected = db.test_connection()
        
        return {
            "status": "healthy" if database_connected else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database_connected": database_connected,
            "service": "MCP Task Management Service",
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "database_connected": False,
            "service": "MCP Task Management Service",
            "version": "1.0.0",
            "error": str(e)
        }

# Task Management Tools
@mcp_app.tool()
def create_task_tool(
    title: str,
    description: Optional[str] = None,
    project_id: Optional[int] = None,
    status: str = "pending",
    priority: str = "medium",
    assigned_to: Optional[str] = None,
    due_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new task.
    
    Args:
        title: Task title (required)
        description: Task description (optional)
        project_id: Associated project ID (optional)
        status: Task status - pending, in_progress, completed, cancelled, blocked (default: pending)
        priority: Task priority - low, medium, high, urgent (default: medium)
        assigned_to: Assigned user (optional)
        due_date: Due date in YYYY-MM-DD format (optional)
    
    Returns:
        Dict containing success status, message, and task data
    """
    return create_task(title, description, project_id, status, priority, assigned_to, due_date)

@mcp_app.tool()
def list_tasks_tool(
    project_id: Optional[int] = None,
    status: Optional[str] = None,
    assigned_to: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List tasks with optional filtering.
    
    Args:
        project_id: Filter by project ID (optional)
        status: Filter by status (optional)
        assigned_to: Filter by assignee (optional)
        limit: Maximum number of results (default: 100, max: 1000)
        offset: Number of results to skip (default: 0)
    
    Returns:
        Dict containing success status, message, and list of tasks
    """
    return list_tasks(project_id, status, assigned_to, limit, offset)

@mcp_app.tool()
def update_task_tool(
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
    Update an existing task.
    
    Args:
        task_id: Task ID to update (required)
        title: New task title (optional)
        description: New task description (optional)
        project_id: New project ID (optional)
        status: New task status (optional)
        priority: New task priority (optional)
        assigned_to: New assignee (optional)
        due_date: New due date in YYYY-MM-DD format, empty string to clear (optional)
    
    Returns:
        Dict containing success status, message, and updated task data
    """
    return update_task(task_id, title, description, project_id, status, priority, assigned_to, due_date)

@mcp_app.tool()
def delete_task_tool(task_id: int) -> Dict[str, Any]:
    """
    Delete a task.
    
    Args:
        task_id: Task ID to delete (required)
    
    Returns:
        Dict containing success status and message
    """
    return delete_task(task_id)

# Project Management Tools
@mcp_app.tool()
def create_project_tool(
    name: str,
    description: Optional[str] = None,
    status: str = "active"
) -> Dict[str, Any]:
    """
    Create a new project.
    
    Args:
        name: Project name (required)
        description: Project description (optional)
        status: Project status - active, inactive, completed, archived (default: active)
    
    Returns:
        Dict containing success status, message, and project data
    """
    return create_project(name, description, status)

@mcp_app.tool()
def list_projects_tool(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List projects with optional filtering.
    
    Args:
        status: Filter by status (optional)
        limit: Maximum number of results (default: 100, max: 1000)
        offset: Number of results to skip (default: 0)
    
    Returns:
        Dict containing success status, message, and list of projects
    """
    return list_projects(status, limit, offset)

@mcp_app.tool()
def update_project_tool(
    project_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing project.
    
    Args:
        project_id: Project ID to update (required)
        name: New project name (optional)
        description: New project description (optional)
        status: New project status (optional)
    
    Returns:
        Dict containing success status, message, and updated project data
    """
    return update_project(project_id, name, description, status)

@mcp_app.tool()
def delete_project_tool(project_id: int) -> Dict[str, Any]:
    """
    Delete a project and all associated tasks.
    
    Args:
        project_id: Project ID to delete (required)
    
    Returns:
        Dict containing success status and message
    """
    return delete_project(project_id)

# Add MCP-specific HTTP endpoints for tool discovery and execution
@app.get("/mcp/tools")
async def list_mcp_tools():
    """List all available MCP tools."""
    try:
        tools = await mcp_app.list_tools()
        return {
            "success": True,
            "message": "Tools retrieved successfully",
            "data": {
                "tools": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in tools
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {e}")
        return {
            "success": False,
            "message": "Failed to retrieve tools",
            "error": str(e)
        }

@app.post("/mcp/tools/{tool_name}")
async def call_mcp_tool(tool_name: str, arguments: dict = None):
    """Call an MCP tool by name with arguments."""
    try:
        if arguments is None:
            arguments = {}
        
        result = await mcp_app.call_tool(tool_name, arguments)
        
        # Extract text content from MCP result and parse as JSON
        content = ""
        if result:
            for item in result:
                if hasattr(item, 'text'):
                    content += item.text
                else:
                    content += str(item)
        
        # Try to parse the content as JSON to return structured data
        try:
            import json
            parsed_content = json.loads(content)
            return {
                "success": True,
                "message": f"Tool {tool_name} executed successfully",
                "data": parsed_content
            }
        except json.JSONDecodeError:
            # If not JSON, return as string
            return {
                "success": True,
                "message": f"Tool {tool_name} executed successfully",
                "data": content
            }
    except Exception as e:
        logger.error(f"Failed to call tool {tool_name}: {e}")
        return {
            "success": False,
            "message": f"Failed to execute tool {tool_name}",
            "error": str(e)
        }

@app.get("/mcp/info")
async def mcp_info():
    """Get MCP server information."""
    try:
        tools = await mcp_app.list_tools()
        return {
            "success": True,
            "message": "MCP server information retrieved",
            "data": {
                "name": mcp_app.name,
                "tool_count": len(tools),
                "tools": [tool.name for tool in tools]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get MCP info: {e}")
        return {
            "success": False,
            "message": "Failed to retrieve MCP information",
            "error": str(e)
        }

# Application entry point
if __name__ == "__main__":
    import uvicorn
    logger.info("Starting MCP Task Management Service on port 8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)