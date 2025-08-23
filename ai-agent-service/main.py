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
from typing import Union, List
from datetime import datetime

from app.agent.core import AIAgent
from app.llm.provider_selector import cleanup_provider_selector
from app.llm.performance_tracker import get_performance_tracker, cleanup_performance_tracker
from app.models.schemas import (
    AgentRequest, AgentResponse, TaskRequest, TaskResponse,
    HealthResponse, AgentStatusResponse, ErrorResponse,
    ProviderHealthMetrics, ServiceHealthStatus, ProviderStatusInfo,
    ProviderSelectionInfo, ProviderConfigurationGuide, ProviderComparisonInfo,
    ConfigurationValidationResult, TroubleshootingInfo
)

# Configure enhanced logging
from app.llm.logging_config import configure_logging, LogLevel, LogFormat

# Configure logging based on environment variables
log_level = LogLevel(os.getenv("LOG_LEVEL", "INFO"))
log_format = LogFormat(os.getenv("LOG_FORMAT", "structured"))
log_file = os.getenv("LOG_FILE")

logging_config = configure_logging(
    log_level=log_level,
    log_format=log_format,
    log_file=log_file
)

logger = logging.getLogger(__name__)

# Global agent instance
agent: AIAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global agent
    
    logger.info("Starting AI Agent Service...")
    
    # Initialize performance tracker
    try:
        performance_tracker = get_performance_tracker()
        logger.info("Performance tracker initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize performance tracker: {e}")
    
    # Initialize AI Agent
    try:
        agent = AIAgent()
        logger.info("AI Agent initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize AI Agent: {e}")
        agent = None
    
    # Verify required environment variables
    mcp_url = os.getenv("MCP_SERVICE_URL")
    llm_provider = os.getenv("LLM_PROVIDER")
    llm_api_key = os.getenv("LLM_API_KEY")
    
    # Check for unified configuration
    if llm_provider and llm_api_key:
        logger.info(f"Using unified LLM configuration with provider: {llm_provider}")
    else:
        # Check for legacy configuration
        legacy_vars = ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
        has_legacy = any(os.getenv(var) for var in legacy_vars)
        
        if has_legacy:
            logger.info("Using legacy LLM configuration")
        else:
            logger.warning("No LLM provider configuration found. Set LLM_PROVIDER and LLM_API_KEY or use legacy variables.")
    
    if not mcp_url:
        logger.warning("MCP_SERVICE_URL not set, using default: http://mcp-service:8001")
    
    yield
    
    logger.info("Shutting down AI Agent Service...")
    
    # Cleanup provider selector and performance tracker
    try:
        await cleanup_provider_selector()
        logger.info("Provider selector cleanup completed")
    except Exception as e:
        logger.error(f"Error during provider cleanup: {e}")
    
    try:
        cleanup_performance_tracker()
        logger.info("Performance tracker cleanup completed")
    except Exception as e:
        logger.error(f"Error during performance tracker cleanup: {e}")


# Create FastAPI application
app = FastAPI(
    title="AI Agent Service",
    description="""
    Multi-LLM AI Agent Service with comprehensive provider support and MCP communication.
    
    ## Supported Providers
    - **Gemini** (Google AI) - Fast, cost-effective, multilingual
    - **OpenAI** (GPT models) - Advanced reasoning, function calling
    - **Anthropic** (Claude models) - Safety-focused, large context windows
    - **Ollama** (Local LLM) - Privacy-focused, offline capability
    
    ## Configuration
    Set the `LLM_PROVIDER` environment variable to select your provider:
    - `LLM_PROVIDER=gemini` - Use Google Gemini
    - `LLM_PROVIDER=openai` - Use OpenAI GPT models
    - `LLM_PROVIDER=anthropic` - Use Anthropic Claude
    - `LLM_PROVIDER=ollama` - Use local Ollama models
    
    ## Provider Information
    All responses include provider information showing which LLM was used to generate the response.
    
    ## Documentation
    - Configuration guides: `/provider/config/{provider_name}`
    - Provider comparison: `/provider/comparison`
    - Troubleshooting: `/troubleshooting/{category}`
    """,
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "AI Agent Service",
        "url": "https://github.com/your-repo/ai-agent-service",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
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
    """
    Enhanced health check endpoint with comprehensive service validation and provider metrics.
    
    Returns detailed information about the current LLM provider, service dependencies,
    and performance metrics.
    
    ## Example Response (Healthy Gemini Provider)
    ```json
    {
        "status": "healthy",
        "service": "ai-agent-service",
        "version": "1.0.0",
        "timestamp": "2024-01-15T10:30:00Z",
        "environment": {
            "llm_provider": "gemini",
            "llm_configured": true,
            "mcp_service_url": "http://mcp-service:8001",
            "agent_initialized": true
        },
        "selected_provider": {
            "status": "healthy",
            "provider_name": "gemini",
            "model": "gemini-pro",
            "available": true,
            "initialized": true,
            "response_time_ms": 1200,
            "capabilities": {
                "max_tokens": 8192,
                "supports_streaming": false,
                "supports_functions": true
            }
        },
        "services": {
            "mcp_service": {
                "available": true,
                "url": "http://mcp-service:8001",
                "response_time_ms": 50
            }
        },
        "performance_metrics": {
            "total_requests": 1250,
            "overall_success_rate": 0.98,
            "avg_response_time_ms": 1100
        }
    }
    ```
    
    ## Status Values
    - `healthy`: All systems operational
    - `degraded`: Some issues but service functional
    - `unhealthy`: Critical issues, service may not work
    """
    try:
        # Get performance tracker for system metrics
        performance_tracker = get_performance_tracker()
        
        # Check environment variables
        llm_provider = os.getenv("LLM_PROVIDER")
        llm_api_key = os.getenv("LLM_API_KEY")
        mcp_url = os.getenv("MCP_SERVICE_URL", "http://mcp-service:8001")
        
        # Check for any LLM configuration (unified or legacy)
        llm_configured = bool(llm_api_key) or bool(os.getenv("GEMINI_API_KEY")) or bool(os.getenv("OPENAI_API_KEY")) or bool(os.getenv("ANTHROPIC_API_KEY"))
        
        # Initialize variables for provider and service health
        selected_provider = None
        services = {}
        overall_status = "healthy"
        
        # Check agent status if available
        if agent is not None:
            try:
                status = await agent.get_status()
                agent_status = status.get("agent_status", "unknown")
                
                # Get current provider information
                current_provider = status.get("current_provider")
                if current_provider:
                    selected_provider = ProviderHealthMetrics(
                        status="healthy" if current_provider.get("available", False) else "unhealthy",
                        provider_name=current_provider.get("provider_name", "unknown"),
                        model=current_provider.get("model"),
                        available=current_provider.get("available", False),
                        initialized=current_provider.get("initialized", False),
                        capabilities=current_provider.get("capabilities"),
                        response_time_ms=current_provider.get("performance", {}).get("recent_avg_response_time_ms"),
                        last_health_check=current_provider.get("performance", {}).get("last_success")
                    )
                    
                    if not current_provider.get("available", False):
                        overall_status = "degraded"
                
                # Get MCP service status
                mcp_service = status.get("services", {}).get("mcp_service", {})
                services["mcp_service"] = ServiceHealthStatus(
                    available=mcp_service.get("available", False),
                    url=mcp_service.get("url"),
                    response_time_ms=mcp_service.get("response_time_ms"),
                    last_check=mcp_service.get("last_check"),
                    error=mcp_service.get("error")
                )
                
                if not mcp_service.get("available", False):
                    overall_status = "degraded"
                
                # If agent status is not ready, mark as degraded
                if agent_status != "ready":
                    overall_status = "degraded"
                    
            except Exception as e:
                logger.warning(f"Agent status check failed: {e}")
                overall_status = "unhealthy"
                selected_provider = ProviderHealthMetrics(
                    status="unhealthy",
                    provider_name="unknown",
                    available=False,
                    initialized=False,
                    error=f"Agent status check failed: {str(e)}"
                )
        else:
            overall_status = "unhealthy"
            selected_provider = ProviderHealthMetrics(
                status="unhealthy",
                provider_name="none",
                available=False,
                initialized=False,
                error="Agent not initialized"
            )
        
        # Get system performance metrics
        system_perf = performance_tracker.get_system_performance_summary()
        
        return HealthResponse(
            status=overall_status,
            service="ai-agent-service",
            version="1.0.0",
            timestamp=datetime.utcnow().isoformat(),
            environment={
                "llm_provider": llm_provider or "auto-detected",
                "llm_configured": llm_configured,
                "mcp_service_url": mcp_url,
                "agent_initialized": agent is not None
            },
            selected_provider=selected_provider,
            services=services,
            performance_metrics={
                "system_uptime_seconds": system_perf.get("system_uptime_seconds", 0),
                "total_requests": system_perf.get("total_requests", 0),
                "overall_success_rate": system_perf.get("overall_success_rate", 0.0),
                "avg_response_time_ms": system_perf.get("avg_response_time_ms", 0.0),
                "active_providers": system_perf.get("active_providers", 0)
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Health check failed: {str(e)}"
        )


@app.get("/agent/status", response_model=Union[AgentStatusResponse, ErrorResponse])
async def agent_status():
    """
    Get comprehensive agent status with current provider and performance metrics.
    
    Provides detailed information about the currently selected LLM provider,
    its capabilities, performance metrics, and service dependencies.
    
    ## Example Response (OpenAI Provider)
    ```json
    {
        "agent_status": "ready",
        "timestamp": "2024-01-15T10:30:00Z",
        "current_provider": {
            "provider_name": "openai",
            "model": "gpt-3.5-turbo",
            "available": true,
            "initialized": true,
            "health_status": "healthy",
            "capabilities": {
                "max_tokens": 4096,
                "supports_streaming": true,
                "supports_functions": true,
                "supported_languages": ["en", "es", "fr", "de", "it"],
                "context_window": 4096,
                "cost_per_token": 0.0015
            },
            "performance": {
                "recent_avg_response_time_ms": 850,
                "success_rate": 0.99,
                "total_requests": 500
            }
        },
        "services": {
            "mcp_service": {
                "available": true,
                "url": "http://mcp-service:8001",
                "response_time_ms": 45
            }
        },
        "capabilities": [
            "natural_language_processing",
            "task_management",
            "intent_analysis",
            "mcp_integration"
        ],
        "configuration": {
            "provider_selection": "environment",
            "fallback_enabled": false,
            "session_timeout": 24
        }
    }
    ```
    
    ## Provider Status Values
    - `ready`: Provider is operational and ready to handle requests
    - `initializing`: Provider is starting up
    - `error`: Provider has encountered an error
    - `unavailable`: Provider is not accessible
    """
    try:
        if agent is None:
            raise HTTPException(
                status_code=503, 
                detail="Agent service is not initialized. Please check service configuration and restart."
            )
        
        status = await agent.get_status()
        
        # Validate status structure
        if not isinstance(status, dict):
            raise HTTPException(
                status_code=500,
                detail="Agent returned invalid status format"
            )
        
        # Transform current_provider to ProviderStatusInfo if present
        current_provider = None
        if status.get("current_provider"):
            provider_data = status["current_provider"]
            current_provider = ProviderStatusInfo(
                provider_name=provider_data.get("provider_name", "unknown"),
                model=provider_data.get("model", "unknown"),
                available=provider_data.get("available", False),
                initialized=provider_data.get("initialized", False),
                health_status=provider_data.get("health_status", "unknown"),
                capabilities=provider_data.get("capabilities", {}),
                performance=provider_data.get("performance", {})
            )
        
        # Transform services to ServiceHealthStatus objects
        services = {}
        for service_name, service_data in status.get("services", {}).items():
            services[service_name] = ServiceHealthStatus(
                available=service_data.get("available", False),
                url=service_data.get("url"),
                response_time_ms=service_data.get("response_time_ms"),
                last_check=service_data.get("last_check"),
                error=service_data.get("error")
            )
        
        return AgentStatusResponse(
            agent_status=status.get("agent_status", "unknown"),
            timestamp=status.get("timestamp", datetime.utcnow().isoformat()),
            current_provider=current_provider,
            services=services,
            capabilities=status.get("capabilities", []),
            configuration=status.get("configuration"),
            performance_metrics=status.get("performance_metrics")
        )
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
    """
    Process a natural language request through the AI agent with comprehensive validation.
    
    The response includes information about which LLM provider was used to generate the response.
    
    ## Example Request
    ```json
    {
        "user_input": "Create a task to review the quarterly report",
        "context": {
            "user_id": "user123",
            "session_type": "work"
        }
    }
    ```
    
    ## Example Response (Gemini Provider)
    ```json
    {
        "success": true,
        "user_input": "Create a task to review the quarterly report",
        "response": "I've created a task for you to review the quarterly report.",
        "intent": {
            "intent": "create_task",
            "confidence": 0.95,
            "entities": {"task_title": "review the quarterly report"}
        },
        "action_result": {
            "task_id": 123,
            "status": "created"
        },
        "timestamp": "2024-01-15T10:30:00Z",
        "provider_info": {
            "provider_name": "gemini",
            "model": "gemini-pro",
            "tokens_used": 45,
            "response_time_ms": 1200
        }
    }
    ```
    
    ## Example Response (OpenAI Provider)
    ```json
    {
        "success": true,
        "user_input": "Create a task to review the quarterly report",
        "response": "I've successfully created a task for reviewing the quarterly report.",
        "provider_info": {
            "provider_name": "openai",
            "model": "gpt-3.5-turbo",
            "tokens_used": 52,
            "response_time_ms": 800
        }
    }
    ```
    """
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
        
        # Add provider information to response
        if agent and hasattr(agent, 'get_current_provider_info'):
            try:
                provider_info = await agent.get_current_provider_info()
                result['provider_info'] = provider_info
            except Exception as e:
                logger.warning(f"Failed to get provider info: {e}")
        
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
        
        # Add provider information to response
        provider_info = None
        if agent and hasattr(agent, 'get_current_provider_info'):
            try:
                provider_info = await agent.get_current_provider_info()
            except Exception as e:
                logger.warning(f"Failed to get provider info: {e}")
        
        return TaskResponse(
            success=result.get("success", False),
            message=result.get("response", ""),
            data=result.get("action_result", {}).get("data"),
            error=result.get("error"),
            provider_info=provider_info
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task request handling failed: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Task request failed: {str(e)}"
        )


@app.get("/provider/info", response_model=Union[ProviderSelectionInfo, ErrorResponse])
async def get_provider_info():
    """Get comprehensive information about current provider selection and available providers"""
    try:
        if agent is None:
            raise HTTPException(
                status_code=503,
                detail="Agent service is not initialized"
            )
        
        # Get current status
        status = await agent.get_status()
        current_provider_data = status.get("current_provider", {})
        
        # Determine selection method
        llm_provider = os.getenv("LLM_PROVIDER")
        selection_method = "environment" if llm_provider else "default"
        
        # Check configuration source
        has_unified = bool(os.getenv("LLM_API_KEY"))
        has_legacy = any(os.getenv(var) for var in ["GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"])
        
        if has_unified and has_legacy:
            config_source = "mixed"
        elif has_unified:
            config_source = "unified"
        elif has_legacy:
            config_source = "legacy"
        else:
            config_source = "none"
        
        # Get available providers (mock data for now - would be dynamic in real implementation)
        available_providers = []
        provider_capabilities = {}
        
        if current_provider_data.get("provider_name"):
            available_providers.append(current_provider_data["provider_name"])
            provider_capabilities[current_provider_data["provider_name"]] = current_provider_data.get("capabilities", {})
        
        return ProviderSelectionInfo(
            current_provider=current_provider_data.get("provider_name", "unknown"),
            selection_method=selection_method,
            available_providers=available_providers,
            provider_capabilities=provider_capabilities,
            configuration_source=config_source
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get provider info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider info: {str(e)}")


@app.get("/provider/config/{provider_name}", response_model=Union[ProviderConfigurationGuide, ErrorResponse])
async def get_provider_configuration_guide(provider_name: str):
    """Get configuration guide for a specific provider"""
    try:
        provider_guides = {
            "gemini": ProviderConfigurationGuide(
                provider_name="gemini",
                required_variables=["LLM_API_KEY (or GEMINI_API_KEY)"],
                optional_variables=["LLM_MODEL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS", "LLM_TIMEOUT"],
                example_configuration={
                    "LLM_PROVIDER": "gemini",
                    "LLM_API_KEY": "AIzaSyC...your_key_here",
                    "LLM_MODEL": "gemini-pro",
                    "LLM_TEMPERATURE": "0.7"
                },
                setup_instructions=[
                    "Visit https://makersuite.google.com/app/apikey",
                    "Sign in with your Google account",
                    "Create a new API key",
                    "Copy the key to your .env file as LLM_API_KEY",
                    "Set LLM_PROVIDER=gemini",
                    "Restart the service"
                ],
                troubleshooting_tips=[
                    "Ensure API key starts with 'AIza'",
                    "Check that your Google account has API access enabled",
                    "Verify the key hasn't expired",
                    "Try regenerating the key if authentication fails"
                ],
                api_key_source="https://makersuite.google.com/app/apikey",
                supported_models=["gemini-pro", "gemini-pro-vision"]
            ),
            "openai": ProviderConfigurationGuide(
                provider_name="openai",
                required_variables=["LLM_API_KEY (or OPENAI_API_KEY)"],
                optional_variables=["LLM_MODEL", "LLM_ORGANIZATION", "LLM_BASE_URL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS", "LLM_TIMEOUT"],
                example_configuration={
                    "LLM_PROVIDER": "openai",
                    "LLM_API_KEY": "sk-...your_key_here",
                    "LLM_MODEL": "gpt-3.5-turbo",
                    "LLM_ORGANIZATION": "org-...your_org_id"
                },
                setup_instructions=[
                    "Visit https://platform.openai.com/api-keys",
                    "Sign in to your OpenAI account",
                    "Create a new API key",
                    "Copy the key to your .env file as LLM_API_KEY",
                    "Set LLM_PROVIDER=openai",
                    "Optionally set your organization ID",
                    "Restart the service"
                ],
                troubleshooting_tips=[
                    "Ensure API key starts with 'sk-'",
                    "Check your OpenAI account has sufficient credits",
                    "Verify your organization ID is correct",
                    "Check for rate limiting on your account"
                ],
                api_key_source="https://platform.openai.com/api-keys",
                supported_models=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo", "gpt-4o"]
            ),
            "anthropic": ProviderConfigurationGuide(
                provider_name="anthropic",
                required_variables=["LLM_API_KEY (or ANTHROPIC_API_KEY)"],
                optional_variables=["LLM_MODEL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS", "LLM_TIMEOUT"],
                example_configuration={
                    "LLM_PROVIDER": "anthropic",
                    "LLM_API_KEY": "sk-ant-...your_key_here",
                    "LLM_MODEL": "claude-3-sonnet-20240229"
                },
                setup_instructions=[
                    "Visit https://console.anthropic.com/",
                    "Sign in or create an Anthropic account",
                    "Navigate to API Keys section",
                    "Create a new API key",
                    "Copy the key to your .env file as LLM_API_KEY",
                    "Set LLM_PROVIDER=anthropic",
                    "Restart the service"
                ],
                troubleshooting_tips=[
                    "Ensure API key starts with 'sk-ant-'",
                    "Check your Anthropic account has sufficient credits",
                    "Verify the model name is correct and available",
                    "Check for regional availability restrictions"
                ],
                api_key_source="https://console.anthropic.com/",
                supported_models=["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229", "claude-3-5-sonnet-20241022"]
            ),
            "ollama": ProviderConfigurationGuide(
                provider_name="ollama",
                required_variables=["LLM_PROVIDER=ollama"],
                optional_variables=["LLM_BASE_URL", "LLM_MODEL", "LLM_KEEP_ALIVE", "LLM_NUM_PREDICT", "LLM_TEMPERATURE", "LLM_TIMEOUT"],
                example_configuration={
                    "LLM_PROVIDER": "ollama",
                    "LLM_BASE_URL": "http://localhost:11434",
                    "LLM_MODEL": "llama2",
                    "LLM_KEEP_ALIVE": "5m"
                },
                setup_instructions=[
                    "Install Ollama from https://ollama.ai/",
                    "Start Ollama service: ollama serve",
                    "Pull a model: ollama pull llama2",
                    "Set LLM_PROVIDER=ollama in your .env",
                    "Configure the model name",
                    "Restart the service"
                ],
                troubleshooting_tips=[
                    "Ensure Ollama is running: ps aux | grep ollama",
                    "Test Ollama API: curl http://localhost:11434/api/tags",
                    "Check available models: ollama list",
                    "Verify firewall allows port 11434",
                    "For Docker: use host.docker.internal instead of localhost"
                ],
                api_key_source="No API key required (local installation)",
                supported_models=["llama2", "codellama", "mistral", "neural-chat", "starcode"]
            )
        }
        
        if provider_name.lower() not in provider_guides:
            raise HTTPException(
                status_code=404,
                detail=f"Configuration guide not found for provider: {provider_name}. Supported providers: {', '.join(provider_guides.keys())}"
            )
        
        return provider_guides[provider_name.lower()]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get configuration guide: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get configuration guide: {str(e)}")


@app.get("/provider/comparison", response_model=Union[List[ProviderComparisonInfo], ErrorResponse])
async def get_provider_comparison():
    """Get comparison information between different LLM providers"""
    try:
        comparisons = [
            ProviderComparisonInfo(
                provider_name="gemini",
                strengths=[
                    "Fast response times",
                    "Good multilingual support",
                    "Integrated with Google services",
                    "Cost-effective",
                    "Easy to get started"
                ],
                limitations=[
                    "Newer provider with evolving features",
                    "Limited function calling capabilities",
                    "Fewer model options"
                ],
                cost_info="Free tier available with generous limits, pay-per-use pricing",
                performance_notes="Generally fast responses, good for real-time applications",
                recommended_for=[
                    "General conversation",
                    "Multilingual applications",
                    "Quick prototyping",
                    "Educational projects",
                    "Cost-conscious deployments"
                ]
            ),
            ProviderComparisonInfo(
                provider_name="openai",
                strengths=[
                    "Mature ecosystem",
                    "Excellent function calling",
                    "Wide model selection",
                    "Strong reasoning capabilities",
                    "Extensive documentation"
                ],
                limitations=[
                    "Higher costs",
                    "Rate limiting on free tier",
                    "Requires OpenAI account",
                    "Can be slower for simple tasks"
                ],
                cost_info="Pay-per-token pricing, costs vary by model (GPT-4 more expensive than GPT-3.5)",
                performance_notes="GPT-4 slower but more capable, GPT-3.5-turbo faster and cheaper",
                recommended_for=[
                    "Complex reasoning tasks",
                    "Function calling applications",
                    "Production applications",
                    "Advanced AI features",
                    "Code generation"
                ]
            ),
            ProviderComparisonInfo(
                provider_name="anthropic",
                strengths=[
                    "Strong safety features",
                    "Excellent for analysis",
                    "Large context windows",
                    "Constitutional AI approach",
                    "High-quality responses"
                ],
                limitations=[
                    "Higher costs",
                    "Newer API ecosystem",
                    "Limited availability in some regions",
                    "Fewer integrations"
                ],
                cost_info="Pay-per-token pricing, competitive with OpenAI GPT-4",
                performance_notes="Claude-3 Opus most capable but slowest, Haiku fastest but less capable",
                recommended_for=[
                    "Content analysis",
                    "Safety-critical applications",
                    "Long document processing",
                    "Ethical AI applications",
                    "Research and analysis"
                ]
            ),
            ProviderComparisonInfo(
                provider_name="ollama",
                strengths=[
                    "Complete privacy (local)",
                    "No API costs",
                    "Offline capability",
                    "Full control over models",
                    "No rate limits"
                ],
                limitations=[
                    "Requires local resources",
                    "Setup complexity",
                    "Model management overhead",
                    "Performance depends on hardware",
                    "Limited model selection"
                ],
                cost_info="Free (after hardware costs), no ongoing API fees",
                performance_notes="Performance varies greatly with hardware, GPU acceleration recommended",
                recommended_for=[
                    "Privacy-sensitive applications",
                    "Offline environments",
                    "Development and testing",
                    "Cost-conscious deployments",
                    "Learning and experimentation"
                ]
            )
        ]
        
        return comparisons
    except Exception as e:
        logger.error(f"Failed to get provider comparison: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get provider comparison: {str(e)}")


@app.post("/provider/validate", response_model=Union[ConfigurationValidationResult, ErrorResponse])
async def validate_provider_configuration(provider_name: str):
    """Validate configuration for a specific provider"""
    try:
        # Get current environment variables
        llm_provider = os.getenv("LLM_PROVIDER")
        llm_api_key = os.getenv("LLM_API_KEY")
        
        # Provider-specific validation
        missing_vars = []
        invalid_vars = []
        warnings = []
        suggestions = []
        
        if provider_name.lower() == "gemini":
            # Check for API key
            gemini_key = llm_api_key or os.getenv("GEMINI_API_KEY")
            if not gemini_key:
                missing_vars.append("LLM_API_KEY or GEMINI_API_KEY")
            elif not gemini_key.startswith("AIza"):
                invalid_vars.append("API key should start with 'AIza'")
            
            # Check model
            model = os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL", "gemini-pro")
            if model not in ["gemini-pro", "gemini-pro-vision"]:
                warnings.append(f"Model '{model}' may not be supported")
                
        elif provider_name.lower() == "openai":
            # Check for API key
            openai_key = llm_api_key or os.getenv("OPENAI_API_KEY")
            if not openai_key:
                missing_vars.append("LLM_API_KEY or OPENAI_API_KEY")
            elif not openai_key.startswith("sk-"):
                invalid_vars.append("API key should start with 'sk-'")
            
            # Check organization
            org = os.getenv("LLM_ORGANIZATION") or os.getenv("OPENAI_ORGANIZATION")
            if org and not org.startswith("org-"):
                warnings.append("Organization ID should start with 'org-'")
                
        elif provider_name.lower() == "anthropic":
            # Check for API key
            anthropic_key = llm_api_key or os.getenv("ANTHROPIC_API_KEY")
            if not anthropic_key:
                missing_vars.append("LLM_API_KEY or ANTHROPIC_API_KEY")
            elif not anthropic_key.startswith("sk-ant-"):
                invalid_vars.append("API key should start with 'sk-ant-'")
                
        elif provider_name.lower() == "ollama":
            # Check if Ollama is accessible
            base_url = os.getenv("LLM_BASE_URL") or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            # Note: In a real implementation, we would test connectivity here
            suggestions.append(f"Ensure Ollama is running at {base_url}")
            
        else:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")
        
        # General suggestions
        if not missing_vars and not invalid_vars:
            suggestions.append("Configuration looks good! Test with a simple request.")
        
        if llm_provider != provider_name.lower():
            warnings.append(f"LLM_PROVIDER is set to '{llm_provider}' but validating '{provider_name}'")
        
        is_valid = len(missing_vars) == 0 and len(invalid_vars) == 0
        
        return ConfigurationValidationResult(
            provider_name=provider_name.lower(),
            is_valid=is_valid,
            missing_variables=missing_vars,
            invalid_variables=invalid_vars,
            warnings=warnings,
            suggestions=suggestions
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to validate configuration: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to validate configuration: {str(e)}")


@app.get("/troubleshooting/{issue_category}", response_model=Union[TroubleshootingInfo, ErrorResponse])
async def get_troubleshooting_info(issue_category: str):
    """Get troubleshooting information for common issues"""
    try:
        troubleshooting_guides = {
            "authentication": TroubleshootingInfo(
                issue_category="authentication",
                symptoms=[
                    "Invalid API key errors",
                    "Authentication failed messages",
                    "401/403 HTTP errors",
                    "Provider initialization fails"
                ],
                possible_causes=[
                    "Incorrect API key format",
                    "Expired or revoked API key",
                    "Wrong provider selected",
                    "Missing environment variables",
                    "Account billing issues"
                ],
                solutions=[
                    "Verify API key format (Gemini: AIza*, OpenAI: sk-*, Anthropic: sk-ant-*)",
                    "Regenerate API key from provider console",
                    "Check account status and billing",
                    "Ensure LLM_PROVIDER matches your API key",
                    "Restart service after configuration changes"
                ],
                prevention_tips=[
                    "Use secure key storage",
                    "Set up billing alerts",
                    "Regularly rotate API keys",
                    "Monitor key usage"
                ],
                related_documentation=[
                    "/provider/config/{provider_name}",
                    "/provider/validate"
                ]
            ),
            "connectivity": TroubleshootingInfo(
                issue_category="connectivity",
                symptoms=[
                    "Connection timeout errors",
                    "Network unreachable messages",
                    "Provider unavailable status",
                    "Intermittent failures"
                ],
                possible_causes=[
                    "Network connectivity issues",
                    "Firewall blocking requests",
                    "DNS resolution problems",
                    "Provider service outages",
                    "Rate limiting"
                ],
                solutions=[
                    "Check internet connectivity",
                    "Verify firewall settings",
                    "Test DNS resolution",
                    "Check provider status pages",
                    "Implement retry logic",
                    "For Ollama: ensure service is running locally"
                ],
                prevention_tips=[
                    "Monitor network connectivity",
                    "Set up health checks",
                    "Configure appropriate timeouts",
                    "Have backup providers"
                ],
                related_documentation=[
                    "/health",
                    "/agent/status"
                ]
            ),
            "performance": TroubleshootingInfo(
                issue_category="performance",
                symptoms=[
                    "Slow response times",
                    "Request timeouts",
                    "High latency",
                    "Poor response quality"
                ],
                possible_causes=[
                    "Network latency",
                    "Large token requests",
                    "Complex prompts",
                    "Provider overload",
                    "Suboptimal model selection"
                ],
                solutions=[
                    "Reduce max_tokens parameter",
                    "Optimize prompts for clarity",
                    "Use faster models (e.g., GPT-3.5 vs GPT-4)",
                    "Increase timeout values",
                    "Consider regional endpoints"
                ],
                prevention_tips=[
                    "Monitor response times",
                    "Optimize prompt engineering",
                    "Choose appropriate models",
                    "Implement caching where possible"
                ],
                related_documentation=[
                    "/provider/comparison",
                    "/agent/status"
                ]
            ),
            "configuration": TroubleshootingInfo(
                issue_category="configuration",
                symptoms=[
                    "Service won't start",
                    "Environment variables not loaded",
                    "Provider not found errors",
                    "Model not available errors"
                ],
                possible_causes=[
                    "Missing .env file",
                    "Incorrect variable names",
                    "Invalid model names",
                    "Docker configuration issues",
                    "File permission problems"
                ],
                solutions=[
                    "Verify .env file exists and is readable",
                    "Check environment variable names",
                    "Validate model names against supported lists",
                    "Rebuild Docker containers",
                    "Check file permissions"
                ],
                prevention_tips=[
                    "Use configuration templates",
                    "Validate before deployment",
                    "Document configuration changes",
                    "Use version control for configs"
                ],
                related_documentation=[
                    "/provider/config/{provider_name}",
                    "/provider/validate"
                ]
            )
        }
        
        if issue_category.lower() not in troubleshooting_guides:
            raise HTTPException(
                status_code=404,
                detail=f"Troubleshooting guide not found for category: {issue_category}. Available categories: {', '.join(troubleshooting_guides.keys())}"
            )
        
        return troubleshooting_guides[issue_category.lower()]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get troubleshooting info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get troubleshooting info: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint with comprehensive API documentation"""
    return {
        "message": "AI Agent Service",
        "version": "1.0.0",
        "description": "Multi-LLM AI Agent Service with provider selection and comprehensive documentation",
        "endpoints": {
            "core": {
                "health": "/health",
                "agent_status": "/agent/status",
                "agent_process": "/agent/process",
                "agent_task": "/agent/task"
            },
            "provider_management": {
                "provider_info": "/provider/info",
                "provider_config": "/provider/config/{provider_name}",
                "provider_comparison": "/provider/comparison",
                "validate_config": "/provider/validate"
            },
            "troubleshooting": {
                "troubleshooting_guide": "/troubleshooting/{issue_category}",
                "available_categories": ["authentication", "connectivity", "performance", "configuration"]
            },
            "documentation": {
                "api_docs": "/docs",
                "openapi_spec": "/openapi.json"
            }
        },
        "supported_providers": ["gemini", "openai", "anthropic", "ollama"],
        "configuration": {
            "method": "Set LLM_PROVIDER environment variable",
            "examples": {
                "gemini": "LLM_PROVIDER=gemini",
                "openai": "LLM_PROVIDER=openai",
                "anthropic": "LLM_PROVIDER=anthropic",
                "ollama": "LLM_PROVIDER=ollama"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)