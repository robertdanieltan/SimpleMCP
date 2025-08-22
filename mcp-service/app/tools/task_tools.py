"""
MCP tools for task management operations.

This module provides FastMCP tools for creating, listing, updating, and deleting tasks.
All tools include proper error handling and validation.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import date
from pydantic import ValidationError
from psycopg2 import DatabaseError

from ..database.operations import get_db_operations
from ..models.schemas import (
    TaskCreate, TaskUpdate, Task, TaskResponse, TaskListResponse,
    serialize_task_for_db, serialize_task_update_for_db
)

logger = logging.getLogger(__name__)
db_ops = get_db_operations()


def create_task(
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
        status: Task status (default: "pending")
        priority: Task priority (default: "medium")
        assigned_to: Assigned user (optional)
        due_date: Due date in YYYY-MM-DD format (optional)
    
    Returns:
        Dict containing success status, message, and task data
    """
    try:
        # Parse due_date if provided
        parsed_due_date = None
        if due_date:
            try:
                parsed_due_date = date.fromisoformat(due_date)
            except ValueError:
                return {
                    "success": False,
                    "message": "Invalid due_date format. Use YYYY-MM-DD",
                    "error": "INVALID_DATE_FORMAT"
                }
        
        # Create and validate task model
        task_data = TaskCreate(
            title=title,
            description=description,
            project_id=project_id,
            status=status,
            priority=priority,
            assigned_to=assigned_to,
            due_date=parsed_due_date
        )
        
        # Create task in database
        result = db_ops.create_task(
            title=task_data.title,
            project_id=task_data.project_id,
            description=task_data.description,
            status=task_data.status,
            priority=task_data.priority,
            assigned_to=task_data.assigned_to,
            due_date=task_data.due_date
        )
        
        # Convert to Task model for response
        task = Task(**result)
        
        logger.info(f"Successfully created task: {task.title} (ID: {task.id})")
        
        return {
            "success": True,
            "message": f"Task '{task.title}' created successfully",
            "data": task.model_dump(mode='json')
        }
        
    except ValidationError as e:
        logger.error(f"Task validation failed: {e}")
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "error": "VALIDATION_ERROR"
        }
    except DatabaseError as e:
        logger.error(f"Database error creating task: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error creating task: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }


def list_tasks(
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
        limit: Maximum number of results (default: 100)
        offset: Number of results to skip (default: 0)
    
    Returns:
        Dict containing success status, message, and list of tasks
    """
    try:
        # Validate limit and offset
        if limit < 1 or limit > 1000:
            return {
                "success": False,
                "message": "Limit must be between 1 and 1000",
                "error": "INVALID_LIMIT"
            }
        
        if offset < 0:
            return {
                "success": False,
                "message": "Offset must be non-negative",
                "error": "INVALID_OFFSET"
            }
        
        # Get tasks from database
        results = db_ops.list_tasks(
            project_id=project_id,
            status=status,
            assigned_to=assigned_to,
            limit=limit,
            offset=offset
        )
        
        # Convert to Task models
        tasks = [Task(**result) for result in results]
        
        logger.info(f"Retrieved {len(tasks)} tasks")
        
        return {
            "success": True,
            "message": f"Retrieved {len(tasks)} tasks",
            "data": [task.model_dump(mode='json') for task in tasks]
        }
        
    except DatabaseError as e:
        logger.error(f"Database error listing tasks: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error listing tasks: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }


def update_task(
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
        due_date: New due date in YYYY-MM-DD format (optional)
    
    Returns:
        Dict containing success status, message, and updated task data
    """
    try:
        # Parse due_date if provided
        parsed_due_date = None
        if due_date is not None:
            if due_date == "":
                parsed_due_date = None  # Clear due date
            else:
                try:
                    parsed_due_date = date.fromisoformat(due_date)
                except ValueError:
                    return {
                        "success": False,
                        "message": "Invalid due_date format. Use YYYY-MM-DD",
                        "error": "INVALID_DATE_FORMAT"
                    }
        
        # Build update data
        update_data = {}
        if title is not None:
            update_data['title'] = title
        if description is not None:
            update_data['description'] = description
        if project_id is not None:
            update_data['project_id'] = project_id
        if status is not None:
            update_data['status'] = status
        if priority is not None:
            update_data['priority'] = priority
        if assigned_to is not None:
            update_data['assigned_to'] = assigned_to
        if due_date is not None:
            update_data['due_date'] = parsed_due_date
        
        if not update_data:
            return {
                "success": False,
                "message": "No fields provided for update",
                "error": "NO_UPDATE_FIELDS"
            }
        
        # Validate update data
        try:
            task_update = TaskUpdate(**update_data)
        except ValidationError as e:
            return {
                "success": False,
                "message": f"Validation error: {str(e)}",
                "error": "VALIDATION_ERROR"
            }
        
        # Update task in database
        result = db_ops.update_task(task_id, **update_data)
        
        if not result:
            return {
                "success": False,
                "message": f"Task with ID {task_id} not found",
                "error": "TASK_NOT_FOUND"
            }
        
        # Convert to Task model for response
        task = Task(**result)
        
        logger.info(f"Successfully updated task: {task.title} (ID: {task.id})")
        
        return {
            "success": True,
            "message": f"Task '{task.title}' updated successfully",
            "data": task.model_dump(mode='json')
        }
        
    except DatabaseError as e:
        logger.error(f"Database error updating task {task_id}: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error updating task {task_id}: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }


def delete_task(task_id: int) -> Dict[str, Any]:
    """
    Delete a task.
    
    Args:
        task_id: Task ID to delete (required)
    
    Returns:
        Dict containing success status and message
    """
    try:
        # Get task details before deletion for logging
        task_data = db_ops.get_task(task_id)
        
        if not task_data:
            return {
                "success": False,
                "message": f"Task with ID {task_id} not found",
                "error": "TASK_NOT_FOUND"
            }
        
        # Delete task from database
        deleted = db_ops.delete_task(task_id)
        
        if deleted:
            logger.info(f"Successfully deleted task: {task_data['title']} (ID: {task_id})")
            return {
                "success": True,
                "message": f"Task '{task_data['title']}' deleted successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete task with ID {task_id}",
                "error": "DELETE_FAILED"
            }
        
    except DatabaseError as e:
        logger.error(f"Database error deleting task {task_id}: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error deleting task {task_id}: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }