"""
Data Models and Schemas for AI Agent Service

This module contains Pydantic models for request/response validation
and data structures used throughout the AI agent service.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, date
from pydantic import BaseModel, Field


class AgentRequest(BaseModel):
    """Request model for agent processing"""
    user_input: str = Field(..., min_length=1, max_length=10000, description="User's natural language input")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context information")
    session_id: Optional[str] = Field(None, max_length=100, description="Optional session identifier")


class AgentResponse(BaseModel):
    """Response model for agent processing"""
    success: bool = Field(..., description="Whether the request was successful")
    user_input: str = Field(..., description="Original user input")
    response: str = Field(..., description="Natural language response")
    intent: Optional[Dict[str, Any]] = Field(None, description="Detected intent information")
    action_result: Optional[Dict[str, Any]] = Field(None, description="Results from executed actions")
    timestamp: str = Field(..., description="Response timestamp")
    error: Optional[str] = Field(None, description="Error message if applicable")


class TaskRequest(BaseModel):
    """Request model for task operations"""
    action: str = Field(..., pattern="^(create|update|delete|list)$", description="Task action (create, update, delete, list)")
    task_data: Optional[Dict[str, Any]] = Field(None, description="Task data for create/update operations")
    task_id: Optional[int] = Field(None, gt=0, description="Task ID for update/delete operations")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filters for list operations")


class TaskResponse(BaseModel):
    """Response model for task operations"""
    success: bool = Field(..., description="Whether the operation was successful")
    message: str = Field(..., description="Human-readable message")
    data: Optional[Any] = Field(None, description="Operation result data")
    error: Optional[str] = Field(None, description="Error message if applicable")


class HealthResponse(BaseModel):
    """Response model for health checks"""
    status: str = Field(..., pattern="^(healthy|degraded|unhealthy)$", description="Service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: Optional[Dict[str, Any]] = Field(None, description="Environment information")
    timestamp: Optional[str] = Field(None, description="Health check timestamp")


class AgentStatusResponse(BaseModel):
    """Response model for agent status"""
    agent_status: str = Field(..., description="Agent status")
    timestamp: str = Field(..., description="Status timestamp")
    services: Dict[str, Any] = Field(..., description="Dependent services status")
    capabilities: List[str] = Field(..., description="Agent capabilities")


class IntentAnalysis(BaseModel):
    """Model for intent analysis results"""
    intent: str = Field(..., description="Detected intent")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    entities: Dict[str, Any] = Field(default_factory=dict, description="Extracted entities")
    action: str = Field(..., description="Recommended action")
    error: Optional[str] = Field(None, description="Error message if analysis failed")


class GeminiResponse(BaseModel):
    """Model for Gemini API responses"""
    success: bool = Field(..., description="Whether the request was successful")
    response: str = Field(..., description="Generated response text")
    source: str = Field(..., description="Response source (gemini, fallback)")
    tokens_used: Optional[int] = Field(None, description="Approximate tokens used")
    error: Optional[str] = Field(None, description="Error message if applicable")


class MCPToolCall(BaseModel):
    """Model for MCP tool calls"""
    tool_name: str = Field(..., description="Name of the MCP tool")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")
    timeout: Optional[int] = Field(30, description="Request timeout in seconds")


class MCPToolResponse(BaseModel):
    """Model for MCP tool responses"""
    success: bool = Field(..., description="Whether the tool call was successful")
    result: Optional[Any] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if applicable")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")


class ErrorResponse(BaseModel):
    """Standard error response model"""
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error code or type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat(), description="Error timestamp")


# Task and Project models (matching MCP service schemas)

class Task(BaseModel):
    """Task model matching MCP service schema"""
    id: Optional[int] = Field(None, description="Task ID")
    project_id: Optional[int] = Field(None, description="Associated project ID")
    title: str = Field(..., description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    status: str = Field("pending", description="Task status")
    priority: str = Field("medium", description="Task priority")
    assigned_to: Optional[str] = Field(None, description="Assigned user")
    due_date: Optional[date] = Field(None, description="Due date")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class Project(BaseModel):
    """Project model matching MCP service schema"""
    id: Optional[int] = Field(None, description="Project ID")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    status: str = Field("active", description="Project status")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")


class CreateTaskRequest(BaseModel):
    """Request model for creating tasks"""
    title: str = Field(..., min_length=1, max_length=255, description="Task title")
    description: Optional[str] = Field(None, max_length=1000, description="Task description")
    project_id: Optional[int] = Field(None, gt=0, description="Associated project ID")
    status: str = Field("pending", pattern="^(pending|in_progress|completed|cancelled)$", description="Task status")
    priority: str = Field("medium", pattern="^(low|medium|high|urgent)$", description="Task priority")
    assigned_to: Optional[str] = Field(None, max_length=100, description="Assigned user")
    due_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$", description="Due date in YYYY-MM-DD format")


class CreateProjectRequest(BaseModel):
    """Request model for creating projects"""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: Optional[str] = Field(None, max_length=1000, description="Project description")
    status: str = Field("active", pattern="^(active|inactive|completed|archived)$", description="Project status")


class UpdateTaskRequest(BaseModel):
    """Request model for updating tasks"""
    task_id: int = Field(..., description="Task ID to update")
    title: Optional[str] = Field(None, description="New task title")
    description: Optional[str] = Field(None, description="New task description")
    project_id: Optional[int] = Field(None, description="New project ID")
    status: Optional[str] = Field(None, description="New task status")
    priority: Optional[str] = Field(None, description="New task priority")
    assigned_to: Optional[str] = Field(None, description="New assigned user")
    due_date: Optional[str] = Field(None, description="New due date in YYYY-MM-DD format")


class ListTasksRequest(BaseModel):
    """Request model for listing tasks"""
    project_id: Optional[int] = Field(None, description="Filter by project ID")
    status: Optional[str] = Field(None, description="Filter by status")
    assigned_to: Optional[str] = Field(None, description="Filter by assignee")
    limit: int = Field(100, description="Maximum number of results")
    offset: int = Field(0, description="Number of results to skip")


class ListProjectsRequest(BaseModel):
    """Request model for listing projects"""
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(100, description="Maximum number of results")
    offset: int = Field(0, description="Number of results to skip")