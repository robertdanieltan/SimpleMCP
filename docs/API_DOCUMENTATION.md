# AI Agent Service API Documentation

This document provides comprehensive API documentation for the Multi-LLM AI Agent Service, including provider-aware examples and configuration guidance.

## Overview

The AI Agent Service provides natural language processing capabilities through multiple LLM providers, with automatic provider selection and comprehensive monitoring.

**Base URL:** `http://localhost:8000`

**Supported Providers:**
- Gemini (Google AI)
- OpenAI (GPT models)
- Anthropic (Claude models)
- Ollama (Local LLM)

## Authentication

No authentication required for local development. All endpoints are publicly accessible.

## Core Endpoints

### Health Check

**GET** `/health`

Returns comprehensive health information including current provider status.

**Response Example (Healthy Gemini):**
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
      "supports_functions": true,
      "supported_languages": ["en", "es", "fr", "de", "it", "ja", "ko", "zh"]
    }
  },
  "services": {
    "mcp_service": {
      "available": true,
      "url": "http://mcp-service:8001",
      "response_time_ms": 50,
      "last_check": "2024-01-15T10:29:55Z"
    }
  },
  "performance_metrics": {
    "system_uptime_seconds": 3600,
    "total_requests": 1250,
    "overall_success_rate": 0.98,
    "avg_response_time_ms": 1100,
    "active_providers": 1
  }
}
```

**Response Example (Degraded - Provider Issues):**
```json
{
  "status": "degraded",
  "service": "ai-agent-service",
  "selected_provider": {
    "status": "unhealthy",
    "provider_name": "openai",
    "available": false,
    "initialized": false,
    "error": "Authentication failed: Invalid API key"
  }
}
```

### Agent Status

**GET** `/agent/status`

Returns detailed agent status with current provider information.

**Response Example (OpenAI Provider):**
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
      "supported_languages": ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"],
      "context_window": 4096,
      "supports_images": false,
      "supports_audio": false,
      "cost_per_token": 0.0015,
      "rate_limit_rpm": 3500,
      "rate_limit_tpm": 90000
    },
    "performance": {
      "recent_avg_response_time_ms": 850,
      "success_rate": 0.99,
      "total_requests": 500,
      "last_success": "2024-01-15T10:29:45Z"
    }
  },
  "services": {
    "mcp_service": {
      "available": true,
      "url": "http://mcp-service:8001",
      "response_time_ms": 45,
      "last_check": "2024-01-15T10:29:50Z"
    }
  },
  "capabilities": [
    "natural_language_processing",
    "task_management",
    "intent_analysis",
    "mcp_integration",
    "multi_provider_support"
  ],
  "configuration": {
    "provider_selection": "environment",
    "fallback_enabled": false,
    "session_timeout": 24,
    "max_concurrent_requests": 100
  },
  "performance_metrics": {
    "requests_per_minute": 25,
    "avg_processing_time_ms": 1200,
    "cache_hit_rate": 0.15
  }
}
```

**Response Example (Anthropic Provider):**
```json
{
  "agent_status": "ready",
  "current_provider": {
    "provider_name": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "available": true,
    "initialized": true,
    "health_status": "healthy",
    "capabilities": {
      "max_tokens": 4096,
      "supports_streaming": true,
      "supports_functions": false,
      "supported_languages": ["en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh"],
      "context_window": 200000,
      "supports_images": true,
      "supports_audio": false,
      "cost_per_token": 0.003
    }
  }
}
```

### Process Agent Request

**POST** `/agent/process`

Process natural language requests through the selected LLM provider.

**Request Body:**
```json
{
  "user_input": "Create a task to review the quarterly report",
  "context": {
    "user_id": "user123",
    "session_type": "work",
    "priority": "high"
  }
}
```

**Response Example (Gemini Provider):**
```json
{
  "success": true,
  "user_input": "Create a task to review the quarterly report",
  "response": "I've created a task for you to review the quarterly report. The task has been assigned ID 123 and is set to high priority as requested.",
  "intent": {
    "intent": "create_task",
    "confidence": 0.95,
    "entities": {
      "task_title": "review the quarterly report",
      "priority": "high",
      "task_type": "review"
    },
    "action": "create_task"
  },
  "action_result": {
    "success": true,
    "data": {
      "task_id": 123,
      "title": "Review the quarterly report",
      "status": "pending",
      "priority": "high",
      "created_at": "2024-01-15T10:30:00Z"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "provider_info": {
    "provider_name": "gemini",
    "model": "gemini-pro",
    "tokens_used": 45,
    "response_time_ms": 1200,
    "source": "gemini"
  }
}
```

**Response Example (OpenAI Provider with Function Calling):**
```json
{
  "success": true,
  "user_input": "Create a task to review the quarterly report",
  "response": "I've successfully created a task for reviewing the quarterly report using the task management system.",
  "intent": {
    "intent": "create_task",
    "confidence": 0.98,
    "entities": {
      "task_title": "review the quarterly report",
      "task_category": "business_review"
    },
    "action": "mcp_tool_call"
  },
  "action_result": {
    "success": true,
    "tool_used": "create_task",
    "data": {
      "task_id": 124,
      "title": "Review the quarterly report",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00Z"
    }
  },
  "timestamp": "2024-01-15T10:30:00Z",
  "provider_info": {
    "provider_name": "openai",
    "model": "gpt-3.5-turbo",
    "tokens_used": 52,
    "response_time_ms": 800,
    "source": "openai",
    "function_calls": 1
  }
}
```

**Response Example (Ollama Provider):**
```json
{
  "success": true,
  "user_input": "Create a task to review the quarterly report",
  "response": "I'll help you create a task for reviewing the quarterly report.",
  "provider_info": {
    "provider_name": "ollama",
    "model": "llama2",
    "tokens_used": 38,
    "response_time_ms": 2500,
    "source": "ollama",
    "local_processing": true
  }
}
```

**Error Response Example:**
```json
{
  "success": false,
  "error": "PROVIDER_ERROR: Rate limit exceeded",
  "message": "The OpenAI provider has exceeded its rate limit. Please try again in a few minutes.",
  "details": {
    "provider": "openai",
    "error_code": "rate_limit_exceeded",
    "retry_after": 60
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Task Management

**POST** `/agent/task`

Handle specific task management operations.

**Request Body (Create Task):**
```json
{
  "action": "create",
  "task_data": {
    "title": "Review quarterly report",
    "description": "Analyze Q4 financial performance",
    "priority": "high",
    "due_date": "2024-01-30"
  }
}
```

**Response Example:**
```json
{
  "success": true,
  "message": "Task created successfully",
  "data": {
    "task_id": 125,
    "title": "Review quarterly report",
    "status": "pending",
    "priority": "high",
    "created_at": "2024-01-15T10:30:00Z"
  },
  "provider_info": {
    "provider_name": "anthropic",
    "model": "claude-3-sonnet-20240229",
    "tokens_used": 35,
    "response_time_ms": 950
  }
}
```

## Provider Management Endpoints

### Provider Information

**GET** `/provider/info`

Get comprehensive information about current provider selection.

**Response Example:**
```json
{
  "current_provider": "openai",
  "selection_method": "environment",
  "available_providers": ["openai"],
  "provider_capabilities": {
    "openai": {
      "max_tokens": 4096,
      "supports_streaming": true,
      "supports_functions": true,
      "supported_languages": ["en", "es", "fr", "de", "it"],
      "context_window": 4096,
      "supports_images": false,
      "supports_audio": false,
      "cost_per_token": 0.0015
    }
  },
  "configuration_source": "unified"
}
```

### Provider Configuration Guide

**GET** `/provider/config/{provider_name}`

Get detailed configuration guide for a specific provider.

**Example:** `GET /provider/config/gemini`

**Response:**
```json
{
  "provider_name": "gemini",
  "required_variables": ["LLM_API_KEY (or GEMINI_API_KEY)"],
  "optional_variables": ["LLM_MODEL", "LLM_TEMPERATURE", "LLM_MAX_TOKENS", "LLM_TIMEOUT"],
  "example_configuration": {
    "LLM_PROVIDER": "gemini",
    "LLM_API_KEY": "AIzaSyC...your_key_here",
    "LLM_MODEL": "gemini-pro",
    "LLM_TEMPERATURE": "0.7"
  },
  "setup_instructions": [
    "Visit https://makersuite.google.com/app/apikey",
    "Sign in with your Google account",
    "Create a new API key",
    "Copy the key to your .env file as LLM_API_KEY",
    "Set LLM_PROVIDER=gemini",
    "Restart the service"
  ],
  "troubleshooting_tips": [
    "Ensure API key starts with 'AIza'",
    "Check that your Google account has API access enabled",
    "Verify the key hasn't expired",
    "Try regenerating the key if authentication fails"
  ],
  "api_key_source": "https://makersuite.google.com/app/apikey",
  "supported_models": ["gemini-pro", "gemini-pro-vision"]
}
```

### Provider Comparison

**GET** `/provider/comparison`

Get comparison information between different providers.

**Response:**
```json
[
  {
    "provider_name": "gemini",
    "strengths": [
      "Fast response times",
      "Good multilingual support",
      "Cost-effective",
      "Easy to get started"
    ],
    "limitations": [
      "Newer provider with evolving features",
      "Limited function calling capabilities"
    ],
    "cost_info": "Free tier available with generous limits, pay-per-use pricing",
    "performance_notes": "Generally fast responses, good for real-time applications",
    "recommended_for": [
      "General conversation",
      "Multilingual applications",
      "Quick prototyping",
      "Educational projects"
    ]
  },
  {
    "provider_name": "openai",
    "strengths": [
      "Mature ecosystem",
      "Excellent function calling",
      "Wide model selection",
      "Strong reasoning capabilities"
    ],
    "limitations": [
      "Higher costs",
      "Rate limiting on free tier",
      "Requires OpenAI account"
    ],
    "cost_info": "Pay-per-token pricing, costs vary by model",
    "recommended_for": [
      "Complex reasoning tasks",
      "Function calling applications",
      "Production applications",
      "Advanced AI features"
    ]
  }
]
```

### Configuration Validation

**POST** `/provider/validate?provider_name=openai`

Validate configuration for a specific provider.

**Response:**
```json
{
  "provider_name": "openai",
  "is_valid": true,
  "missing_variables": [],
  "invalid_variables": [],
  "warnings": [],
  "suggestions": [
    "Configuration looks good! Test with a simple request."
  ]
}
```

**Response (Invalid Configuration):**
```json
{
  "provider_name": "openai",
  "is_valid": false,
  "missing_variables": ["LLM_API_KEY or OPENAI_API_KEY"],
  "invalid_variables": [],
  "warnings": [
    "LLM_PROVIDER is set to 'gemini' but validating 'openai'"
  ],
  "suggestions": [
    "Set LLM_API_KEY with your OpenAI API key",
    "Ensure LLM_PROVIDER matches the provider you want to use"
  ]
}
```

## Troubleshooting Endpoints

### Troubleshooting Guide

**GET** `/troubleshooting/{issue_category}`

Get troubleshooting information for common issues.

**Available Categories:**
- `authentication`
- `connectivity`
- `performance`
- `configuration`

**Example:** `GET /troubleshooting/authentication`

**Response:**
```json
{
  "issue_category": "authentication",
  "symptoms": [
    "Invalid API key errors",
    "Authentication failed messages",
    "401/403 HTTP errors",
    "Provider initialization fails"
  ],
  "possible_causes": [
    "Incorrect API key format",
    "Expired or revoked API key",
    "Wrong provider selected",
    "Missing environment variables"
  ],
  "solutions": [
    "Verify API key format (Gemini: AIza*, OpenAI: sk-*, Anthropic: sk-ant-*)",
    "Regenerate API key from provider console",
    "Check account status and billing",
    "Ensure LLM_PROVIDER matches your API key"
  ],
  "prevention_tips": [
    "Use secure key storage",
    "Set up billing alerts",
    "Regularly rotate API keys",
    "Monitor key usage"
  ],
  "related_documentation": [
    "/provider/config/{provider_name}",
    "/provider/validate"
  ]
}
```

## Error Handling

All endpoints return structured error responses:

```json
{
  "success": false,
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "details": {
    "additional": "context",
    "status_code": 400,
    "path": "/agent/process"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Common Error Codes:**
- `PROVIDER_ERROR` - LLM provider issues
- `VALIDATION_ERROR` - Request validation failed
- `CONFIGURATION_ERROR` - Service configuration issues
- `NETWORK_ERROR` - Connectivity problems
- `RATE_LIMIT_ERROR` - Rate limiting exceeded
- `AUTHENTICATION_ERROR` - API key or auth issues

## Provider-Specific Behavior

### Response Time Expectations

| Provider | Typical Response Time | Notes |
|----------|----------------------|-------|
| Gemini | 800-1500ms | Fast, consistent |
| OpenAI | 600-1200ms | Varies by model |
| Anthropic | 1000-2000ms | Slower but thorough |
| Ollama | 2000-5000ms | Depends on hardware |

### Token Usage

All responses include token usage information in `provider_info`:

```json
{
  "provider_info": {
    "tokens_used": 45,
    "estimated_cost": 0.000068,
    "input_tokens": 20,
    "output_tokens": 25
  }
}
```

### Model-Specific Features

**Function Calling Support:**
- OpenAI: Full support
- Gemini: Limited support
- Anthropic: No native support
- Ollama: Model-dependent

**Image Processing:**
- Gemini: gemini-pro-vision model
- OpenAI: GPT-4 Vision models
- Anthropic: Claude-3 models
- Ollama: LLaVA models

## Rate Limiting

Rate limits vary by provider and plan:

**Free Tiers:**
- Gemini: 60 requests/minute
- OpenAI: 3 requests/minute (free trial)
- Anthropic: 5 requests/minute (free trial)
- Ollama: No limits (local)

**Paid Tiers:**
- Check provider documentation for current limits
- Monitor usage through provider dashboards
- Implement exponential backoff for rate limit errors

## Best Practices

### Request Optimization

1. **Use appropriate models:**
   - Simple tasks: GPT-3.5-turbo, Gemini-pro
   - Complex reasoning: GPT-4, Claude-3-opus
   - Local/private: Ollama models

2. **Optimize token usage:**
   - Keep prompts concise
   - Use appropriate max_tokens
   - Consider context window limits

3. **Handle errors gracefully:**
   - Implement retry logic
   - Check provider status
   - Have fallback responses

### Configuration Management

1. **Use unified configuration:**
   ```bash
   LLM_PROVIDER=openai
   LLM_API_KEY=your_key
   LLM_MODEL=gpt-3.5-turbo
   ```

2. **Validate configuration:**
   ```bash
   curl -X POST http://localhost:8000/provider/validate?provider_name=openai
   ```

3. **Monitor health:**
   ```bash
   curl http://localhost:8000/health
   ```

### Security

1. **Protect API keys:**
   - Never commit to version control
   - Use environment variables
   - Rotate keys regularly

2. **Monitor usage:**
   - Set up billing alerts
   - Track unusual patterns
   - Review logs regularly

## Support and Resources

- **Health Check:** `/health`
- **Status Monitoring:** `/agent/status`
- **Configuration Help:** `/provider/config/{provider}`
- **Troubleshooting:** `/troubleshooting/{category}`
- **API Documentation:** `/docs`

For additional support, check the provider-specific documentation and troubleshooting guides.