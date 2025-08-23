# Multi-LLM Configuration Management System

This module provides comprehensive configuration management for multiple Large Language Model (LLM) providers in the AI Agent Service.

## Overview

The configuration management system enables the AI Agent Service to work with multiple LLM providers:
- **Gemini** (Google's Generative AI)
- **OpenAI** (GPT models)
- **Anthropic** (Claude models)
- **Ollama** (Local LLM deployment)

## Key Features

- **Environment-based configuration**: All settings controlled via environment variables
- **Backward compatibility**: Existing Gemini-only setups work unchanged
- **Provider validation**: Automatic validation of API keys and connectivity
- **Flexible configuration**: Per-provider settings for models, temperature, timeouts, etc.
- **Health monitoring**: Built-in health checks and availability monitoring

## Quick Start

### 1. Basic Setup (Gemini only - backward compatible)

```bash
# Minimum configuration for existing setups
GEMINI_API_KEY=your_gemini_api_key_here
```

### 2. Multi-Provider Setup

```bash
# Enable multiple providers
GEMINI_API_KEY=your_gemini_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Enable local Ollama
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Using the Configuration System

```python
from app.config import ConfigManager, ProviderValidator

# Initialize configuration
config_manager = ConfigManager()

# Check available providers
enabled_providers = config_manager.config.get_enabled_providers()
print(f"Available providers: {enabled_providers}")

# Validate provider configuration
validation = config_manager.validate_provider_config('gemini')
if validation['valid']:
    print("Gemini is properly configured")

# Check provider availability
validator = ProviderValidator(config_manager)
results = await validator.validate_all_providers()
```

## Environment Variables

### Provider API Keys

| Variable | Description | Required |
|----------|-------------|----------|
| `GEMINI_API_KEY` | Google Gemini API key | For Gemini |
| `OPENAI_API_KEY` | OpenAI API key (starts with `sk-`) | For OpenAI |
| `ANTHROPIC_API_KEY` | Anthropic API key (starts with `sk-ant-`) | For Anthropic |
| `OLLAMA_ENABLED` | Enable Ollama provider (`true`/`false`) | For Ollama |

### Provider-Specific Settings

#### Gemini
```bash
GEMINI_MODEL=gemini-pro                    # Default: gemini-pro
GEMINI_TEMPERATURE=0.7                     # Default: 0.7
GEMINI_MAX_TOKENS=1000                     # Default: 1000
GEMINI_TIMEOUT=30                          # Default: 30 seconds
```

#### OpenAI
```bash
OPENAI_MODEL=gpt-3.5-turbo                 # Default: gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7                     # Default: 0.7
OPENAI_MAX_TOKENS=1000                     # Default: 1000
OPENAI_TIMEOUT=30                          # Default: 30 seconds
OPENAI_ORGANIZATION=your_org_id            # Optional
```

#### Anthropic
```bash
ANTHROPIC_MODEL=claude-3-sonnet-20240229   # Default: claude-3-sonnet-20240229
ANTHROPIC_TEMPERATURE=0.7                  # Default: 0.7
ANTHROPIC_MAX_TOKENS=1000                  # Default: 1000
ANTHROPIC_TIMEOUT=30                       # Default: 30 seconds
```

#### Ollama
```bash
OLLAMA_BASE_URL=http://localhost:11434     # Default: http://localhost:11434
OLLAMA_MODEL=llama2                        # Default: llama2
OLLAMA_TEMPERATURE=0.7                     # Default: 0.7
OLLAMA_MAX_TOKENS=1000                     # Default: 1000
OLLAMA_TIMEOUT=60                          # Default: 60 seconds
OLLAMA_KEEP_ALIVE=5m                       # Default: 5m
```

### Session Management
```bash
LLM_SESSION_TIMEOUT_HOURS=24               # Default: 24 hours
LLM_MAX_CONCURRENT_SESSIONS=100            # Default: 100 sessions
```

## Configuration Classes

### ConfigManager

Main configuration management class:

```python
config_manager = ConfigManager()

# Get configuration
config = config_manager.config

# Check enabled providers
enabled = config.get_enabled_providers()

# Get provider-specific config
gemini_config = config.get_provider_config('gemini')

# Validate configuration
validation = config_manager.validate_provider_config('openai')

# Get availability summary
summary = config_manager.get_provider_availability_summary()

# Reload configuration
config_manager.reload_config()
```

### ProviderValidator

Provider availability validation:

```python
validator = ProviderValidator(config_manager)

# Validate all providers
results = await validator.validate_all_providers()

# Quick health check
is_healthy = await validator.quick_health_check('gemini')
```

### Configuration Data Classes

#### LLMConfig
```python
@dataclass
class LLMConfig:
    providers: Dict[str, ProviderConfig]
    default_provider: Optional[str]
    session_timeout_hours: int
    max_concurrent_sessions: int
```

#### ProviderConfig
```python
@dataclass
class ProviderConfig:
    name: str
    enabled: bool
    api_key: Optional[str]
    model: Optional[str]
    base_url: Optional[str]
    temperature: float
    max_tokens: int
    timeout: int
    extra_params: Dict[str, Any]
```

## Provider Capabilities

### Gemini
- **Strengths**: Multimodal support, fast responses, good reasoning
- **Best for**: General chat, code analysis, creative tasks
- **API Key format**: Starts with `AI`

### OpenAI
- **Strengths**: Excellent reasoning, function calling, reliable
- **Best for**: Complex analysis, structured output, professional tasks
- **API Key format**: Starts with `sk-`

### Anthropic
- **Strengths**: Safety-focused, long context, helpful responses
- **Best for**: Document analysis, ethical reasoning, research tasks
- **API Key format**: Starts with `sk-ant-`

### Ollama
- **Strengths**: Privacy, offline operation, cost-effective
- **Best for**: Local deployment, sensitive data, development testing
- **Setup**: Requires local Ollama installation

## Testing

### Run Configuration Tests
```bash
# Test with no providers (default state)
python -m ai-agent-service.app.config.test_config

# Test with Gemini only
GEMINI_API_KEY=your_key python -m ai-agent-service.app.config.test_config

# Test with multiple providers
GEMINI_API_KEY=your_key OPENAI_API_KEY=your_key python -m ai-agent-service.app.config.test_config
```

### Run Integration Demo
```bash
python -m ai-agent-service.app.config.integration_example
```

## Migration Guide

### From Gemini-Only Setup

Existing configurations work unchanged:

```bash
# Before (still works)
GEMINI_API_KEY=your_key

# After (same result)
GEMINI_API_KEY=your_key
# System automatically uses Gemini as default provider
```

### Adding Additional Providers

Simply add API keys for desired providers:

```bash
# Existing
GEMINI_API_KEY=your_gemini_key

# Add OpenAI
OPENAI_API_KEY=your_openai_key

# Add Anthropic
ANTHROPIC_API_KEY=your_anthropic_key

# Add Ollama
OLLAMA_ENABLED=true
```

## Error Handling

The configuration system handles various error scenarios:

- **Missing API keys**: Provider disabled, system continues with available providers
- **Invalid API key format**: Clear error messages during validation
- **Network connectivity issues**: Graceful degradation with error reporting
- **Configuration errors**: Detailed error messages and fallback behavior

## Security Considerations

- API keys are never logged or exposed in responses
- Configuration validation masks sensitive information
- Environment variables are the only supported configuration method
- No API keys are stored in code or configuration files

## Future Enhancements

This configuration system is designed to support future features:

- Dynamic provider selection based on request type
- Load balancing across multiple providers
- Cost-aware provider routing
- Provider-specific optimizations
- Advanced session management

## Troubleshooting

### Common Issues

1. **No providers configured**
   - Solution: Set at least one provider's API key

2. **Invalid API key format**
   - Gemini: Should start with `AI`
   - OpenAI: Should start with `sk-`
   - Anthropic: Should start with `sk-ant-`

3. **Ollama connection failed**
   - Ensure Ollama is running: `ollama serve`
   - Check base URL is correct
   - Verify model is available: `ollama list`

4. **Configuration not loading**
   - Check environment variables are set
   - Restart the service after configuration changes
   - Use `config_manager.reload_config()` for runtime updates

### Debug Mode

Enable detailed logging:

```bash
LOG_LEVEL=DEBUG python your_app.py
```

This will show detailed configuration loading and validation information.