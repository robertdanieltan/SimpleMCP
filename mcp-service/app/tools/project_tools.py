"""
MCP tools for project management operations.

This module provides FastMCP tools for creating and listing projects.
All tools include proper error handling and validation.
"""

import logging
from typing import Optional, List, Dict, Any
from pydantic import ValidationError
from psycopg2 import DatabaseError

from ..database.operations import get_db_operations
from ..models.schemas import (
    ProjectCreate, ProjectUpdate, Project, ProjectResponse, ProjectListResponse,
    serialize_project_for_db, serialize_project_update_for_db
)

logger = logging.getLogger(__name__)
db_ops = get_db_operations()


def create_project(
    name: str,
    description: Optional[str] = None,
    status: str = "active"
) -> Dict[str, Any]:
    """
    Create a new project.
    
    Args:
        name: Project name (required)
        description: Project description (optional)
        status: Project status (default: "active")
    
    Returns:
        Dict containing success status, message, and project data
    """
    try:
        # Create and validate project model
        project_data = ProjectCreate(
            name=name,
            description=description,
            status=status
        )
        
        # Create project in database
        result = db_ops.create_project(
            name=project_data.name,
            description=project_data.description,
            status=project_data.status
        )
        
        # Convert to Project model for response
        project = Project(**result)
        
        logger.info(f"Successfully created project: {project.name} (ID: {project.id})")
        
        return {
            "success": True,
            "message": f"Project '{project.name}' created successfully",
            "data": project.model_dump(mode='json')
        }
        
    except ValidationError as e:
        logger.error(f"Project validation failed: {e}")
        return {
            "success": False,
            "message": f"Validation error: {str(e)}",
            "error": "VALIDATION_ERROR"
        }
    except DatabaseError as e:
        logger.error(f"Database error creating project: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error creating project: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }


def list_projects(
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    List projects with optional filtering.
    
    Args:
        status: Filter by status (optional)
        limit: Maximum number of results (default: 100)
        offset: Number of results to skip (default: 0)
    
    Returns:
        Dict containing success status, message, and list of projects
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
        
        # Get projects from database
        results = db_ops.list_projects(
            status=status,
            limit=limit,
            offset=offset
        )
        
        # Convert to Project models
        projects = [Project(**result) for result in results]
        
        logger.info(f"Retrieved {len(projects)} projects")
        
        return {
            "success": True,
            "message": f"Retrieved {len(projects)} projects",
            "data": [project.model_dump(mode='json') for project in projects]
        }
        
    except DatabaseError as e:
        logger.error(f"Database error listing projects: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error listing projects: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }


def update_project(
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
    try:
        # Build update data
        update_data = {}
        if name is not None:
            update_data['name'] = name
        if description is not None:
            update_data['description'] = description
        if status is not None:
            update_data['status'] = status
        
        if not update_data:
            return {
                "success": False,
                "message": "No fields provided for update",
                "error": "NO_UPDATE_FIELDS"
            }
        
        # Validate update data
        try:
            project_update = ProjectUpdate(**update_data)
        except ValidationError as e:
            return {
                "success": False,
                "message": f"Validation error: {str(e)}",
                "error": "VALIDATION_ERROR"
            }
        
        # Update project in database
        result = db_ops.update_project(project_id, **update_data)
        
        if not result:
            return {
                "success": False,
                "message": f"Project with ID {project_id} not found",
                "error": "PROJECT_NOT_FOUND"
            }
        
        # Convert to Project model for response
        project = Project(**result)
        
        logger.info(f"Successfully updated project: {project.name} (ID: {project.id})")
        
        return {
            "success": True,
            "message": f"Project '{project.name}' updated successfully",
            "data": project.model_dump(mode='json')
        }
        
    except DatabaseError as e:
        logger.error(f"Database error updating project {project_id}: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error updating project {project_id}: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }


def delete_project(project_id: int) -> Dict[str, Any]:
    """
    Delete a project and all associated tasks.
    
    Args:
        project_id: Project ID to delete (required)
    
    Returns:
        Dict containing success status and message
    """
    try:
        # Get project details before deletion for logging
        project_data = db_ops.get_project(project_id)
        
        if not project_data:
            return {
                "success": False,
                "message": f"Project with ID {project_id} not found",
                "error": "PROJECT_NOT_FOUND"
            }
        
        # Delete project from database (cascades to tasks)
        deleted = db_ops.delete_project(project_id)
        
        if deleted:
            logger.info(f"Successfully deleted project: {project_data['name']} (ID: {project_id})")
            return {
                "success": True,
                "message": f"Project '{project_data['name']}' and all associated tasks deleted successfully"
            }
        else:
            return {
                "success": False,
                "message": f"Failed to delete project with ID {project_id}",
                "error": "DELETE_FAILED"
            }
        
    except DatabaseError as e:
        logger.error(f"Database error deleting project {project_id}: {e}")
        return {
            "success": False,
            "message": f"Database error: {str(e)}",
            "error": "DATABASE_ERROR"
        }
    except Exception as e:
        logger.error(f"Unexpected error deleting project {project_id}: {e}")
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}",
            "error": "INTERNAL_ERROR"
        }