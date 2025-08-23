# Environment-Based Provider Selection Guide

This guide explains how to configure and use environment-based LLM provider selection in the AI Agent Service.

## Overview

The AI Agent Service supports multiple LLM providers through a unified configuration system. You can select your preferred provider using environment variables, making it easy to switch between providers without code changes.

## Quick Start

### 1. Choose Your Provider

Set the `LLM_PROVIDER` environment variable:

```bash
# For Google Gemini
LLM_PROVIDER=gemini

# For OpenAI GPT models
LLM_PROVIDER=openai

# For Anthropic Claude models
LLM_PROVIDER=anthropic

# For local Ollama models
LLM_PROVIDER=ollama
```

### 2. Configure API Access

Set your API key using the unified variable:

```bash
# Generic API key (works with any provider)
LLM_API_KEY=your_api_key_here

# Optional: Set specific model
LLM_MODEL=gpt-3.5-turbo  # or gemini-pro, claude-3-sonnet-20240229, llama2
```

### 3. Start the Service

```bash
docker-compose up --build
```

## Detailed Configuration

### Unified Configuration (Recommended)

The unified approach uses generic environment variables that work with any provider:

```bash
# .env file
LLM_PROVIDER=openai                    # Provider selection
LLM_API_KEY=sk-your_openai_key_here   # API key
LLM_MODEL=gpt-3.5-turbo               # Model selection
LLM_TEMPERATURE=0.7                   # Response randomness
LLM_MAX_TOKENS=1000                   # Maximum response length
LLM_TIMEOUT=30                        # Request timeout in seconds
```

### Provider-Specific Variables

Some providers support additional configuration options:

```bash
# OpenAI specific
LLM_ORGANIZATION=org-your_org_id      # OpenAI organization
LLM_BASE_URL=https://api.openai.com/v1 # Custom endpoint

# Ollama specific
LLM_BASE_URL=http://localhost:11434   # Ollama server URL
LLM_KEEP_ALIVE=5m                     # Model keep-alive time
LLM_NUM_PREDICT=-1                    # Max tokens to predict

# Anthropic specific (uses standard variables)
# No additional variables needed
```

### Legacy Configuration (Backward Compatibility)

The service still supports provider-specific variables for backward compatibility:

```bash
# Legacy Gemini configuration
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-pro

# Legacy OpenAI configuration
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_ORGANIZATION=your_org_id

# Legacy Anthropic configuration
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Legacy Ollama configuration
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

## Provider Selection Logic

The service uses the following priority order for provider selection:

1. **Explicit Selection:** `LLM_PROVIDER` environment variable
2. **Auto-Detection:** Based on available API keys
3. **Default Fallback:** Gemini (if configured)

### Selection Examples

```bash
# Explicit selection (highest priority)
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_key

# Auto-detection (if LLM_PROVIDER not set)
OPENAI_API_KEY=sk-your_key  # Will auto-select OpenAI

# Mixed configuration (explicit wins)
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-your_key
OPENAI_API_KEY=sk-other_key  # Ignored because LLM_PROVIDER=anthropic
```

## Configuration Validation

### Automatic Validation

The service automatically validates your configuration on startup:

```bash
# Check logs for validation results
docker-compose logs ai-agent | grep -i provider

# Expected success messages:
# INFO: Using unified LLM configuration with provider: openai
# INFO: Provider openai initialized successfully
```

### Manual Validation

Use the validation endpoint to check your configuration:

```bash
# Validate current provider
curl -X POST "http://localhost:8000/provider/validate?provider_name=openai"

# Response for valid configuration:
{
  "provider_name": "openai",
  "is_valid": true,
  "missing_variables": [],
  "invalid_variables": [],
  "warnings": [],
  "suggestions": ["Configuration looks good! Test with a simple request."]
}
```

### Common Validation Issues

```bash
# Missing API key
{
  "is_valid": false,
  "missing_variables": ["LLM_API_KEY or OPENAI_API_KEY"],
  "suggestions": ["Set LLM_API_KEY with your OpenAI API key"]
}

# Wrong API key format
{
  "is_valid": false,
  "invalid_variables": ["API key should start with 'sk-'"],
  "suggestions": ["Verify your API key format"]
}

# Provider mismatch
{
  "is_valid": true,
  "warnings": ["LLM_PROVIDER is set to 'gemini' but validating 'openai'"],
  "suggestions": ["Ensure LLM_PROVIDER matches your intended provider"]
}
```

## Provider-Specific Setup

### Gemini (Google AI)

```bash
# Configuration
LLM_PROVIDER=gemini
LLM_API_KEY=AIzaSyC...your_key_here
LLM_MODEL=gemini-pro  # or gemini-pro-vision

# Get API key from:
# https://makersuite.google.com/app/apikey

# Supported models:
# - gemini-pro: Text generation
# - gemini-pro-vision: Text and image processing
```

**Validation:**
```bash
# API key should start with "AIza"
echo $LLM_API_KEY | grep "^AIza" && echo "Valid format" || echo "Invalid format"

# Test API access
curl -H "x-goog-api-key: $LLM_API_KEY" \
  "https://generativelanguage.googleapis.com/v1/models"
```

### OpenAI

```bash
# Configuration
LLM_PROVIDER=openai
LLM_API_KEY=sk-...your_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_ORGANIZATION=org-...your_org_id  # Optional

# Get API key from:
# https://platform.openai.com/api-keys

# Popular models:
# - gpt-3.5-turbo: Fast, cost-effective
# - gpt-4: More capable, higher cost
# - gpt-4-turbo: Latest GPT-4 variant
```

**Validation:**
```bash
# API key should start with "sk-"
echo $LLM_API_KEY | grep "^sk-" && echo "Valid format" || echo "Invalid format"

# Test API access
curl -H "Authorization: Bearer $LLM_API_KEY" \
  "https://api.openai.com/v1/models"
```

### Anthropic (Claude)

```bash
# Configuration
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...your_key_here
LLM_MODEL=claude-3-sonnet-20240229

# Get API key from:
# https://console.anthropic.com/

# Available models:
# - claude-3-haiku-20240307: Fast, lightweight
# - claude-3-sonnet-20240229: Balanced performance
# - claude-3-opus-20240229: Most capable
# - claude-3-5-sonnet-20241022: Latest Sonnet
```

**Validation:**
```bash
# API key should start with "sk-ant-"
echo $LLM_API_KEY | grep "^sk-ant-" && echo "Valid format" || echo "Invalid format"

# Test API access (requires a test message)
curl -H "x-api-key: $LLM_API_KEY" \
  -H "Content-Type: application/json" \
  -X POST "https://api.anthropic.com/v1/messages" \
  -d '{"model":"claude-3-sonnet-20240229","max_tokens":1,"messages":[{"role":"user","content":"test"}]}'
```

### Ollama (Local LLM)

```bash
# Configuration
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434  # Default Ollama URL
LLM_MODEL=llama2
LLM_KEEP_ALIVE=5m
LLM_NUM_PREDICT=-1  # No limit

# Install Ollama:
# https://ollama.ai/

# Popular models:
# - llama2: Meta's Llama 2
# - codellama: Code-focused Llama
# - mistral: Mistral 7B
# - neural-chat: Intel's neural chat
```

**Setup:**
```bash
# Install and start Ollama
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve

# Pull a model
ollama pull llama2

# Test Ollama API
curl http://localhost:11434/api/tags

# List available models
ollama list
```

**Docker Configuration:**
```bash
# For Docker containers, use host networking
LLM_BASE_URL=http://host.docker.internal:11434

# Or add Ollama to docker-compose.yml
services:
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
```

## Environment File Examples

### Complete .env Example (OpenAI)

```bash
# =============================================================================
# AI Agent Service Configuration
# =============================================================================

# LLM Provider Configuration
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_openai_api_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
LLM_TIMEOUT=30
LLM_ORGANIZATION=org-your_organization_id

# Database Configuration
POSTGRES_USER=postgres
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=aiagent_mcp
DATABASE_URL=postgresql://postgres:secure_password_here@postgres:5432/aiagent_mcp

# Service Configuration
MCP_SERVICE_URL=http://mcp-service:8001
AI_AGENT_SERVICE_URL=http://ai-agent:8000

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_password_here

# Development Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=true
```

### Multi-Provider .env Example

```bash
# Primary provider
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_openai_key

# Backup providers (for future fallback support)
GEMINI_API_KEY=AIza_your_gemini_key
ANTHROPIC_API_KEY=sk-ant-your_anthropic_key

# Provider-specific settings
LLM_MODEL=gpt-3.5-turbo
LLM_ORGANIZATION=org-your_org_id

# Other configuration...
```

## Switching Providers

### Runtime Provider Switching

To switch providers, update your environment and restart:

```bash
# Stop service
docker-compose down

# Update .env file
sed -i 's/LLM_PROVIDER=gemini/LLM_PROVIDER=openai/' .env
sed -i 's/LLM_API_KEY=AIza.*/LLM_API_KEY=sk-your_openai_key/' .env

# Restart service
docker-compose up --build
```

### Testing Provider Switch

```bash
# Check current provider
curl http://localhost:8000/agent/status | jq '.current_provider.provider_name'

# Test functionality
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Hello, test my new provider configuration"}'

# Verify provider in response
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{"user_input": "test"}' | jq '.provider_info'
```

## Monitoring and Debugging

### Health Monitoring

```bash
# Overall health
curl http://localhost:8000/health | jq '.selected_provider'

# Detailed status
curl http://localhost:8000/agent/status | jq '.current_provider'

# Provider information
curl http://localhost:8000/provider/info
```

### Debug Logging

Enable debug logging for detailed provider information:

```bash
# In .env file
LOG_LEVEL=DEBUG
DEBUG=true

# Restart and check logs
docker-compose up --build
docker-compose logs ai-agent | grep -i provider
```

### Common Debug Scenarios

```bash
# Check environment variables
docker-compose exec ai-agent env | grep -E "LLM_|GEMINI_|OPENAI_|ANTHROPIC_"

# Test provider connectivity
docker-compose exec ai-agent curl -s http://localhost:8000/health

# Validate configuration
docker-compose exec ai-agent curl -s -X POST \
  "http://localhost:8000/provider/validate?provider_name=$(echo $LLM_PROVIDER)"
```

## Best Practices

### Configuration Management

1. **Use Unified Variables:**
   ```bash
   # Preferred
   LLM_PROVIDER=openai
   LLM_API_KEY=your_key
   
   # Instead of
   OPENAI_API_KEY=your_key
   ```

2. **Validate Before Deployment:**
   ```bash
   # Test configuration
   docker-compose config
   curl -X POST http://localhost:8000/provider/validate?provider_name=openai
   ```

3. **Monitor Provider Health:**
   ```bash
   # Set up health checks
   curl -f http://localhost:8000/health || echo "Service unhealthy"
   ```

### Security

1. **Protect API Keys:**
   ```bash
   # Never commit .env files
   echo ".env" >> .gitignore
   
   # Use secure permissions
   chmod 600 .env
   ```

2. **Rotate Keys Regularly:**
   ```bash
   # Set reminders to rotate keys
   # Monitor for key exposure
   # Use key management systems in production
   ```

### Performance

1. **Choose Appropriate Models:**
   ```bash
   # For speed: gpt-3.5-turbo, gemini-pro
   # For capability: gpt-4, claude-3-opus
   # For privacy: ollama models
   ```

2. **Monitor Usage:**
   ```bash
   # Check provider dashboards
   # Set up billing alerts
   # Track response times
   ```

## Troubleshooting

### Provider Not Loading

```bash
# Check environment variables
env | grep LLM_PROVIDER

# Verify API key format
echo $LLM_API_KEY | head -c 10

# Check service logs
docker-compose logs ai-agent | grep -i error
```

### Authentication Failures

```bash
# Validate API key
curl -X POST http://localhost:8000/provider/validate?provider_name=$LLM_PROVIDER

# Test direct API access
# (See provider-specific validation commands above)

# Regenerate API key if needed
```

### Performance Issues

```bash
# Check response times
curl -s http://localhost:8000/agent/status | jq '.current_provider.performance'

# Try different model
LLM_MODEL=gpt-3.5-turbo  # Faster than gpt-4

# Adjust parameters
LLM_MAX_TOKENS=500  # Reduce for faster responses
LLM_TIMEOUT=60      # Increase for complex requests
```

## Migration Guide

### From Single Provider to Multi-Provider

1. **Backup Current Configuration:**
   ```bash
   cp .env .env.backup
   ```

2. **Update to Unified Format:**
   ```bash
   # From:
   GEMINI_API_KEY=your_key
   
   # To:
   LLM_PROVIDER=gemini
   LLM_API_KEY=your_key
   ```

3. **Test New Configuration:**
   ```bash
   docker-compose up --build
   curl http://localhost:8000/health
   ```

4. **Verify Functionality:**
   ```bash
   curl -X POST http://localhost:8000/agent/process \
     -H "Content-Type: application/json" \
     -d '{"user_input": "test migration"}'
   ```

### From Legacy to Unified Variables

```bash
# Migration script example
#!/bin/bash

# Read current values
CURRENT_PROVIDER=""
CURRENT_KEY=""

if [ ! -z "$GEMINI_API_KEY" ]; then
    CURRENT_PROVIDER="gemini"
    CURRENT_KEY="$GEMINI_API_KEY"
elif [ ! -z "$OPENAI_API_KEY" ]; then
    CURRENT_PROVIDER="openai"
    CURRENT_KEY="$OPENAI_API_KEY"
elif [ ! -z "$ANTHROPIC_API_KEY" ]; then
    CURRENT_PROVIDER="anthropic"
    CURRENT_KEY="$ANTHROPIC_API_KEY"
fi

# Update .env file
if [ ! -z "$CURRENT_PROVIDER" ]; then
    echo "LLM_PROVIDER=$CURRENT_PROVIDER" >> .env
    echo "LLM_API_KEY=$CURRENT_KEY" >> .env
    echo "Migration complete. Please restart the service."
fi
```

## Support Resources

- **Configuration Help:** `/provider/config/{provider_name}`
- **Validation:** `/provider/validate?provider_name={provider}`
- **Troubleshooting:** `/troubleshooting/{category}`
- **Health Monitoring:** `/health` and `/agent/status`
- **API Documentation:** `/docs`

For provider-specific issues, consult the official documentation:
- Gemini: https://ai.google.dev/docs
- OpenAI: https://platform.openai.com/docs
- Anthropic: https://docs.anthropic.com/
- Ollama: https://ollama.ai/docs