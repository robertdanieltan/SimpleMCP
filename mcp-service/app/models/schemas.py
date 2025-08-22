"""
Data models and schemas for the MCP service.

This module contains Pydantic models for Project and Task entities,
API response models, and validation logic for database operations.
"""

from datetime import datetime, date
from typing import Optional, Any, List
from pydantic import BaseModel, Field, validator


class ProjectBase(BaseModel):
    """Base Project model with common fields."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    status: str = Field(default="active", description="Project status")

    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['active', 'inactive', 'completed', 'archived']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Project name cannot be empty')
        return v.strip()


class ProjectCreate(ProjectBase):
    """Model for creating a new project."""
    pass


class ProjectUpdate(BaseModel):
    """Model for updating an existing project."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['active', 'inactive', 'completed', 'archived']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Project name cannot be empty')
        return v.strip() if v else v


class Project(ProjectBase):
    """Complete Project model with database fields."""
    id: int = Field(..., description="Project ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class TaskBase(BaseModel):
    """Base Task model with common fields."""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    status: str = Field(default="pending", description="Task status")
    priority: str = Field(default="medium", description="Task priority")
    assigned_to: Optional[str] = Field(None, max_length=100, description="Assigned user")
    due_date: Optional[date] = Field(None, description="Due date")
    project_id: Optional[int] = Field(None, description="Associated project ID")

    @validator('status')
    def validate_status(cls, v):
        allowed_statuses = ['pending', 'in_progress', 'completed', 'cancelled', 'blocked']
        if v not in allowed_statuses:
            raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        allowed_priorities = ['low', 'medium', 'high', 'urgent']
        if v not in allowed_priorities:
            raise ValueError(f'Priority must be one of: {", ".join(allowed_priorities)}')
        return v

    @validator('title')
    def validate_title(cls, v):
        if not v or not v.strip():
            raise ValueError('Task title cannot be empty')
        return v.strip()

    @validator('due_date')
    def validate_due_date(cls, v):
        if v is not None and v < date.today():
            raise ValueError('Due date cannot be in the past')
        return v


class TaskCreate(TaskBase):
    """Model for creating a new task."""
    pass


class TaskUpdate(BaseModel):
    """Model for updating an existing task."""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = Field(None, max_length=100)
    due_date: Optional[date] = None
    project_id: Optional[int] = None

    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            allowed_statuses = ['pending', 'in_progress', 'completed', 'cancelled', 'blocked']
            if v not in allowed_statuses:
                raise ValueError(f'Status must be one of: {", ".join(allowed_statuses)}')
        return v

    @validator('priority')
    def validate_priority(cls, v):
        if v is not None:
            allowed_priorities = ['low', 'medium', 'high', 'urgent']
            if v not in allowed_priorities:
                raise ValueError(f'Priority must be one of: {", ".join(allowed_priorities)}')
        return v

    @validator('title')
    def validate_title(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Task title cannot be empty')
        return v.strip() if v else v

    @validator('due_date')
    def validate_due_date(cls, v):
        if v is not None and v < date.today():
            raise ValueError('Due date cannot be in the past')
        return v


class Task(TaskBase):
    """Complete Task model with database fields."""
    id: int = Field(..., description="Task ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


# API Response Models

class APIResponse(BaseModel):
    """Standard API response wrapper."""
    success: bool = Field(..., description="Operation success status")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error code if applicable")


class ProjectResponse(APIResponse):
    """API response for single project operations."""
    data: Optional[Project] = None


class ProjectListResponse(APIResponse):
    """API response for project list operations."""
    data: Optional[List[Project]] = None


class TaskResponse(APIResponse):
    """API response for single task operations."""
    data: Optional[Task] = None


class TaskListResponse(APIResponse):
    """API response for task list operations."""
    data: Optional[List[Task]] = None


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service health status")
    timestamp: datetime = Field(..., description="Health check timestamp")
    database_connected: bool = Field(..., description="Database connection status")


# Database serialization helpers

def serialize_project_for_db(project: ProjectCreate) -> dict:
    """Serialize Project model for database insertion."""
    return {
        'name': project.name,
        'description': project.description,
        'status': project.status
    }


def serialize_project_update_for_db(project: ProjectUpdate) -> dict:
    """Serialize ProjectUpdate model for database update."""
    data = {}
    if project.name is not None:
        data['name'] = project.name
    if project.description is not None:
        data['description'] = project.description
    if project.status is not None:
        data['status'] = project.status
    
    if data:
        data['updated_at'] = datetime.now()
    
    return data


def serialize_task_for_db(task: TaskCreate) -> dict:
    """Serialize Task model for database insertion."""
    return {
        'title': task.title,
        'description': task.description,
        'status': task.status,
        'priority': task.priority,
        'assigned_to': task.assigned_to,
        'due_date': task.due_date,
        'project_id': task.project_id
    }


def serialize_task_update_for_db(task: TaskUpdate) -> dict:
    """Serialize TaskUpdate model for database update."""
    data = {}
    if task.title is not None:
        data['title'] = task.title
    if task.description is not None:
        data['description'] = task.description
    if task.status is not None:
        data['status'] = task.status
    if task.priority is not None:
        data['priority'] = task.priority
    if task.assigned_to is not None:
        data['assigned_to'] = task.assigned_to
    if task.due_date is not None:
        data['due_date'] = task.due_date
    if task.project_id is not None:
        data['project_id'] = task.project_id
    
    if data:
        data['updated_at'] = datetime.now()
    
    return data