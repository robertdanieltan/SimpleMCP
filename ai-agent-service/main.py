"""
AI Agent Service - FastAPI Application

This service provides AI agent capabilities with Gemini integration
and communicates with the MCP service for task and project management.
"""

import os
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from typing import Union
from datetime import datetime

from app.agent.core import AIAgent
from app.models.schemas import (
    AgentRequest, AgentResponse, TaskRequest, TaskResponse,
    HealthResponse, AgentStatusResponse, ErrorResponse
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global agent instance
agent: AIAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global agent
    
    logger.info("Starting AI Agent Service...")
    
    # Initialize AI Agent
    try:
        agent = AIAgent()
        logger.info("AI Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI Agent: {e}")
        agent = None
    
    # Verify required environment variables
    required_env_vars = ["GEMINI_API_KEY", "MCP_SERVICE_URL"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.warning(f"Missing environment variables: {missing_vars}")
    else:
        logger.info("All required environment variables are set")
    
    yield
    
    logger.info("Shutting down AI Agent Service...")


# Create FastAPI application
app = FastAPI(
    title="AI Agent Service",
    description="AI Agent service with Gemini integration and MCP communication",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler for structured error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured error responses"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP_ERROR",
            message=exc.detail,
            details={
                "status_code": exc.status_code,
                "path": str(request.url.path),
                "method": request.method
            }
        ).dict()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with structured error responses"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="INTERNAL_SERVER_ERROR",
            message="An internal server error occurred",
            details={
                "path": str(request.url.path),
                "method": request.method,
                "exception_type": type(exc).__name__
            }
        ).dict()
    )


@app.get("/health", response_model=Union[HealthResponse, ErrorResponse])
async def health_check():
    """Health check endpoint with comprehensive service validation"""
    try:
        # Check environment variables
        gemini_key = os.getenv("GEMINI_API_KEY")
        mcp_url = os.getenv("MCP_SERVICE_URL", "http://mcp-service:8001")
        
        # Check agent status if available
        agent_healthy = agent is not None
        agent_status = "unknown"
        
        if agent_healthy:
            try:
                status = agent.get_status()
                agent_status = status.get("agent_status", "unknown")
                agent_healthy = agent_status == "ready"
            except Exception as e:
                logger.warning(f"Agent status check failed: {e}")
                agent_healthy = False
                agent_status = "error"
        
        # Determine overall health status
        overall_status = "healthy" if agent_healthy else "degraded"
        
        return HealthResponse(
            status=overall_status,
            service="ai-agent-service",
            version="1.0.0",
            environment={
                "gemini_configured": bool(gemini_key),
                "mcp_service_url": mcp_url,
                "agent_initialized": agent is not None,
                "agent_status": agent_status
            },
            timestamp=datetime.utcnow().isoformat()
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/agent/status", response_model=Union[AgentStatusResponse, ErrorResponse])
async def agent_status():
    """Get comprehensive agent status and configuration"""
    try:
        if agent is None:
            raise HTTPException(
                status_code=503, 
                detail="Agent service is not initialized. Please check service configuration and restart."
            )
        
        status = agent.get_status()
        
        # Validate status structure
        if not isinstance(status, dict):
            raise HTTPException(
                status_code=500,
                detail="Agent returned invalid status format"
            )
        
        return AgentStatusResponse(**status)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent status check failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Agent status check failed: {str(e)}"
        )


@app.post("/agent/process", response_model=Union[AgentResponse, ErrorResponse])
async def process_agent_request(request: AgentRequest):
    """Process a natural language request through the AI agent with comprehensive validation"""
    try:
        # Validate agent availability
        if agent is None:
            raise HTTPException(
                status_code=503, 
                detail="Agent service is not initialized. Please check service configuration and restart."
            )
        
        # Validate request input
        if not request.user_input or not request.user_input.strip():
            raise HTTPException(
                status_code=400,
                detail="User input cannot be empty. Please provide a valid request."
            )
        
        # Check input length (reasonable limit)
        if len(request.user_input) > 10000:
            raise HTTPException(
                status_code=400,
                detail="User input is too long. Please limit your request to 10,000 characters."
            )
        
        # Process the request
        result = await agent.process_request(
            user_input=request.user_input.strip(),
            context=request.context
        )
        
        # Validate result structure
        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail="Agent returned invalid response format"
            )
        
        return AgentResponse(**result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Agent request processing failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Request processing failed: {str(e)}"
        )


@app.post("/agent/task", response_model=Union[TaskResponse, ErrorResponse])
async def handle_task_request(request: TaskRequest):
    """Handle specific task management requests with comprehensive validation"""
    try:
        # Validate agent availability
        if agent is None:
            raise HTTPException(
                status_code=503, 
                detail="Agent service is not initialized. Please check service configuration and restart."
            )
        
        # Validate action
        valid_actions = ["create", "list", "update", "delete"]
        if request.action not in valid_actions:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid action '{request.action}'. Valid actions are: {', '.join(valid_actions)}"
            )
        
        # Validate action-specific requirements
        if request.action == "create":
            if not request.task_data:
                raise HTTPException(
                    status_code=400,
                    detail="Task data is required for create action"
                )
            if not isinstance(request.task_data, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Task data must be a valid object"
                )
            if not request.task_data.get("title"):
                raise HTTPException(
                    status_code=400,
                    detail="Task title is required in task_data"
                )
        
        elif request.action in ["update", "delete"]:
            if not request.task_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Task ID is required for {request.action} action"
                )
            if not isinstance(request.task_id, int) or request.task_id <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="Task ID must be a positive integer"
                )
        
        elif request.action == "update" and not request.task_data:
            raise HTTPException(
                status_code=400,
                detail="Task data is required for update action"
            )
        
        # Convert task request to natural language for processing
        if request.action == "create" and request.task_data:
            task_title = request.task_data.get("title", "")
            task_desc = request.task_data.get("description", "")
            user_input = f"Create a task titled '{task_title}'"
            if task_desc:
                user_input += f" with description '{task_desc}'"
        elif request.action == "list":
            filters_str = ""
            if request.filters:
                filter_parts = []
                for key, value in request.filters.items():
                    filter_parts.append(f"{key}={value}")
                filters_str = f" with filters: {', '.join(filter_parts)}"
            user_input = f"List tasks{filters_str}"
        elif request.action == "update" and request.task_id and request.task_data:
            updates = []
            for key, value in request.task_data.items():
                updates.append(f"{key} to {value}")
            user_input = f"Update task {request.task_id}: {', '.join(updates)}"
        elif request.action == "delete" and request.task_id:
            user_input = f"Delete task {request.task_id}"
        else:
            raise HTTPException(
                status_code=400, 
                detail="Invalid task request format or missing required parameters"
            )
        
        # Process the request
        result = await agent.process_request(user_input)
        
        # Validate result structure
        if not isinstance(result, dict):
            raise HTTPException(
                status_code=500,
                detail="Agent returned invalid response format"
            )
        
        return TaskResponse(
            success=result.get("success", False),
            message=result.get("response", ""),
            data=result.get("action_result", {}).get("data"),
            error=result.get("error")
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task request handling failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Task request failed: {str(e)}"
        )


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AI Agent Service",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "agent_status": "/agent/status",
            "agent_process": "/agent/process",
            "agent_task": "/agent/task",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)