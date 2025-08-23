# LLM Configuration Migration Guide

## Overview

The AI Agent MCP Service now supports a **unified LLM configuration approach** that simplifies provider management and makes it easier to switch between different LLM providers.

## New Unified Configuration (Recommended)

### Benefits
- ✅ **Simplicity**: One set of environment variables regardless of provider
- ✅ **Flexibility**: Easy to switch providers by changing just `LLM_PROVIDER`
- ✅ **Scalability**: Adding new providers doesn't require new environment variables
- ✅ **Consistency**: Same variable names across all providers

### Configuration Variables

```bash
# Primary provider selection
LLM_PROVIDER=gemini  # Options: gemini, openai, anthropic, ollama

# Generic configuration (applies to selected provider)
LLM_API_KEY=your_api_key_here
LLM_MODEL=gemini-pro
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
LLM_TIMEOUT=30

# Optional provider-specific settings
LLM_BASE_URL=          # For OpenAI custom endpoints, Ollama
LLM_ORGANIZATION=      # For OpenAI organization
LLM_SAFETY_SETTINGS=   # For Gemini safety settings
LLM_KEEP_ALIVE=        # For Ollama keep-alive
LLM_MAX_RETRIES=       # For retry configuration
```

## Migration Examples

### From Gemini Legacy to Unified

**Before (Legacy):**
```bash
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-pro
GEMINI_TEMPERATURE=0.8
GEMINI_MAX_TOKENS=2000
GEMINI_TIMEOUT=30
```

**After (Unified):**
```bash
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_key
LLM_MODEL=gemini-pro
LLM_TEMPERATURE=0.8
LLM_MAX_TOKENS=2000
LLM_TIMEOUT=30
```

### From OpenAI Legacy to Unified

**Before (Legacy):**
```bash
OPENAI_API_KEY=sk-your_openai_key
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.5
OPENAI_ORGANIZATION=org-123
```

**After (Unified):**
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_openai_key
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.5
LLM_ORGANIZATION=org-123
```

### Switching Between Providers

With unified configuration, switching providers is as simple as:

```bash
# Switch from Gemini to OpenAI
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_openai_key
LLM_MODEL=gpt-3.5-turbo

# Switch from OpenAI to Anthropic
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-your_anthropic_key
LLM_MODEL=claude-3-sonnet-20240229

# Switch to local Ollama
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama2
```

## Provider-Specific Configuration

### Gemini
```bash
LLM_PROVIDER=gemini
LLM_API_KEY=your_gemini_key
LLM_MODEL=gemini-pro                    # or gemini-pro-vision
LLM_SAFETY_SETTINGS=default             # optional
```

### OpenAI
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-your_openai_key
LLM_MODEL=gpt-3.5-turbo                 # or gpt-4, gpt-4-turbo
LLM_ORGANIZATION=org-your_org_id        # optional
LLM_BASE_URL=https://api.openai.com/v1  # optional custom endpoint
```

### Anthropic
```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-your_anthropic_key
LLM_MODEL=claude-3-sonnet-20240229      # or claude-3-opus-20240229
```

### Ollama (Local)
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama2                        # or codellama, mistral
LLM_TIMEOUT=60                          # longer timeout for local models
LLM_KEEP_ALIVE=5m                       # optional
```

## Backward Compatibility

The system maintains **full backward compatibility** with legacy configurations:

- ✅ Existing legacy configurations continue to work
- ✅ No breaking changes to existing deployments
- ✅ Unified configuration takes precedence when both are present
- ✅ Clear migration path with recommendations

## Migration Steps

1. **Identify Current Configuration**
   ```bash
   # Check which legacy variables you're using
   env | grep -E "(GEMINI|OPENAI|ANTHROPIC|OLLAMA)_"
   ```

2. **Set Unified Variables**
   ```bash
   # Set the new unified variables
   export LLM_PROVIDER=your_provider
   export LLM_API_KEY=your_api_key
   export LLM_MODEL=your_model
   # ... other settings
   ```

3. **Test Configuration**
   ```bash
   # Restart your services and verify they work
   docker-compose restart ai-agent
   ```

4. **Remove Legacy Variables** (Optional)
   ```bash
   # Once confirmed working, remove legacy variables
   unset GEMINI_API_KEY GEMINI_MODEL
   # ... other legacy variables
   ```

## Configuration Validation

The system provides configuration validation and recommendations:

```python
from app.config.manager import ConfigManager

config_manager = ConfigManager()

# Get configuration summary
summary = config_manager.get_provider_availability_summary()
print(f"Configuration approach: {summary['configuration_approach']}")

# Get migration recommendations
recommendations = config_manager.get_configuration_recommendations()
for suggestion in recommendations['suggestions']:
    print(f"Recommendation: {suggestion}")
```

## Troubleshooting

### Common Issues

1. **Provider Not Found**
   ```
   Error: Unsupported LLM_PROVIDER: xyz
   ```
   **Solution**: Use one of the supported providers: `gemini`, `openai`, `anthropic`, `ollama`

2. **API Key Missing**
   ```
   Error: LLM_API_KEY required for gemini but not provided
   ```
   **Solution**: Set the `LLM_API_KEY` environment variable

3. **Both Configurations Present**
   ```
   Warning: Both unified and legacy configurations detected
   ```
   **Solution**: Remove legacy variables or keep both (unified takes precedence)

### Validation Commands

```bash
# Check current configuration
curl http://localhost:8000/agent/config

# Check provider health
curl http://localhost:8000/agent/health

# Get configuration recommendations
curl http://localhost:8000/agent/config/recommendations
```

## Best Practices

1. **Use Unified Configuration** for new deployments
2. **Migrate Gradually** from legacy to unified
3. **Test Thoroughly** after migration
4. **Remove Legacy Variables** once migration is complete
5. **Use Environment Files** (`.env`) for local development
6. **Use Secrets Management** for production deployments

## Support

If you encounter issues during migration:

1. Check the application logs for detailed error messages
2. Verify your API keys are valid and have proper permissions
3. Test with a simple configuration first
4. Use the configuration validation endpoints
5. Refer to the provider-specific documentation for API requirements