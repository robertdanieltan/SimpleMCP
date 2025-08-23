# LLM Provider Configuration Guide

This guide provides comprehensive instructions for configuring and using multiple LLM providers with the AI Agent Service.

## Overview

The AI Agent Service supports multiple Large Language Model (LLM) providers:
- **Gemini** (Google AI)
- **OpenAI** (GPT models)
- **Anthropic** (Claude models)
- **Ollama** (Local LLM deployment)

## Configuration Methods

### Unified Configuration (Recommended)

The unified approach uses generic environment variables that work with any provider:

```bash
# Primary provider selection
LLM_PROVIDER=gemini  # Options: gemini, openai, anthropic, ollama

# Generic configuration
LLM_API_KEY=your_api_key_here
LLM_MODEL=gemini-pro
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=1000
LLM_TIMEOUT=30
```

### Legacy Configuration (Backward Compatibility)

Provider-specific variables are still supported:

```bash
# Gemini
GEMINI_API_KEY=your_gemini_key
GEMINI_MODEL=gemini-pro

# OpenAI
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-3.5-turbo

# Anthropic
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Ollama
OLLAMA_ENABLED=true
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

## Provider-Specific Setup

### Gemini (Google AI)

**API Key Source:** https://makersuite.google.com/app/apikey

**Required Variables:**
- `LLM_API_KEY` (or `GEMINI_API_KEY`)

**Optional Variables:**
- `LLM_MODEL` (default: `gemini-pro`)
- `LLM_TEMPERATURE` (default: `0.7`)
- `LLM_MAX_TOKENS` (default: `1000`)
- `LLM_TIMEOUT` (default: `30`)

**Supported Models:**
- `gemini-pro` - Text generation
- `gemini-pro-vision` - Text and image processing

**Example Configuration:**
```bash
LLM_PROVIDER=gemini
LLM_API_KEY=AIzaSyC...your_key_here
LLM_MODEL=gemini-pro
LLM_TEMPERATURE=0.7
```

**Setup Instructions:**
1. Visit https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file
5. Set `LLM_PROVIDER=gemini`
6. Restart the service

### OpenAI

**API Key Source:** https://platform.openai.com/api-keys

**Required Variables:**
- `LLM_API_KEY` (or `OPENAI_API_KEY`)

**Optional Variables:**
- `LLM_MODEL` (default: `gpt-3.5-turbo`)
- `LLM_ORGANIZATION` - Your OpenAI organization ID
- `LLM_BASE_URL` - Custom API endpoint
- `LLM_TEMPERATURE` (default: `0.7`)
- `LLM_MAX_TOKENS` (default: `1000`)
- `LLM_TIMEOUT` (default: `30`)

**Supported Models:**
- `gpt-3.5-turbo` - Fast, cost-effective
- `gpt-4` - More capable, higher cost
- `gpt-4-turbo` - Latest GPT-4 variant
- `gpt-4o` - Optimized GPT-4

**Example Configuration:**
```bash
LLM_PROVIDER=openai
LLM_API_KEY=sk-...your_key_here
LLM_MODEL=gpt-3.5-turbo
LLM_ORGANIZATION=org-...your_org_id
```

**Setup Instructions:**
1. Visit https://platform.openai.com/api-keys
2. Sign in to your OpenAI account
3. Create a new API key
4. Copy the key to your `.env` file
5. Set `LLM_PROVIDER=openai`
6. Optionally set your organization ID
7. Restart the service

### Anthropic (Claude)

**API Key Source:** https://console.anthropic.com/

**Required Variables:**
- `LLM_API_KEY` (or `ANTHROPIC_API_KEY`)

**Optional Variables:**
- `LLM_MODEL` (default: `claude-3-sonnet-20240229`)
- `LLM_TEMPERATURE` (default: `0.7`)
- `LLM_MAX_TOKENS` (default: `1000`)
- `LLM_TIMEOUT` (default: `30`)

**Supported Models:**
- `claude-3-haiku-20240307` - Fast, lightweight
- `claude-3-sonnet-20240229` - Balanced performance
- `claude-3-opus-20240229` - Most capable
- `claude-3-5-sonnet-20241022` - Latest Sonnet

**Example Configuration:**
```bash
LLM_PROVIDER=anthropic
LLM_API_KEY=sk-ant-...your_key_here
LLM_MODEL=claude-3-sonnet-20240229
```

**Setup Instructions:**
1. Visit https://console.anthropic.com/
2. Sign in or create an Anthropic account
3. Navigate to API Keys section
4. Create a new API key
5. Copy the key to your `.env` file
6. Set `LLM_PROVIDER=anthropic`
7. Restart the service

### Ollama (Local LLM)

**Installation:** https://ollama.ai/

**Required Variables:**
- `LLM_PROVIDER=ollama`

**Optional Variables:**
- `LLM_BASE_URL` (default: `http://localhost:11434`)
- `LLM_MODEL` (default: `llama2`)
- `LLM_KEEP_ALIVE` (default: `5m`)
- `LLM_NUM_PREDICT` (default: `-1` for no limit)
- `LLM_TEMPERATURE` (default: `0.7`)
- `LLM_TIMEOUT` (default: `60`)

**Popular Models:**
- `llama2` - Meta's Llama 2
- `codellama` - Code-focused Llama
- `mistral` - Mistral 7B
- `neural-chat` - Intel's neural chat
- `starcode` - Code generation

**Example Configuration:**
```bash
LLM_PROVIDER=ollama
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=llama2
LLM_KEEP_ALIVE=5m
```

**Setup Instructions:**
1. Install Ollama from https://ollama.ai/
2. Start Ollama service: `ollama serve`
3. Pull a model: `ollama pull llama2`
4. Set `LLM_PROVIDER=ollama` in your `.env`
5. Configure the model name
6. Restart the service

## Provider Comparison

### Gemini
**Strengths:**
- Fast response times
- Good multilingual support
- Integrated with Google services
- Cost-effective

**Best For:**
- General conversation
- Multilingual applications
- Quick prototyping
- Educational projects

**Limitations:**
- Newer provider with evolving features
- Limited function calling capabilities

### OpenAI
**Strengths:**
- Mature ecosystem
- Excellent function calling
- Wide model selection
- Strong reasoning capabilities

**Best For:**
- Complex reasoning tasks
- Function calling applications
- Production applications
- Advanced AI features

**Limitations:**
- Higher costs
- Rate limiting on free tier
- Requires OpenAI account

### Anthropic
**Strengths:**
- Strong safety features
- Excellent for analysis
- Large context windows
- Constitutional AI approach

**Best For:**
- Content analysis
- Safety-critical applications
- Long document processing
- Ethical AI applications

**Limitations:**
- Higher costs
- Newer API ecosystem
- Limited availability in some regions

### Ollama
**Strengths:**
- Complete privacy (local)
- No API costs
- Offline capability
- Full control over models

**Best For:**
- Privacy-sensitive applications
- Offline environments
- Development/testing
- Cost-conscious deployments

**Limitations:**
- Requires local resources
- Setup complexity
- Model management overhead
- Performance depends on hardware

## Configuration Validation

The service automatically validates your configuration on startup. Check the logs for:

```
INFO: Using unified LLM configuration with provider: gemini
INFO: Provider gemini initialized successfully
```

Or for issues:
```
WARNING: No LLM provider configuration found
ERROR: Failed to initialize provider: Invalid API key
```

## Environment Variables Reference

### Core Configuration
| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `LLM_PROVIDER` | Provider selection | `gemini` | No |
| `LLM_API_KEY` | Generic API key | - | Yes* |
| `LLM_MODEL` | Model name | Provider default | No |
| `LLM_TEMPERATURE` | Response randomness | `0.7` | No |
| `LLM_MAX_TOKENS` | Max response tokens | `1000` | No |
| `LLM_TIMEOUT` | Request timeout (seconds) | `30` | No |

### Provider-Specific
| Variable | Provider | Description | Default |
|----------|----------|-------------|---------|
| `LLM_BASE_URL` | OpenAI/Ollama | Custom API endpoint | Provider default |
| `LLM_ORGANIZATION` | OpenAI | Organization ID | - |
| `LLM_KEEP_ALIVE` | Ollama | Model keep-alive time | `5m` |
| `LLM_NUM_PREDICT` | Ollama | Max tokens to predict | `-1` |

*Required unless using legacy provider-specific variables

## Migration Guide

### From Legacy to Unified Configuration

1. **Identify Current Provider:**
   ```bash
   # If you have:
   GEMINI_API_KEY=your_key
   
   # Change to:
   LLM_PROVIDER=gemini
   LLM_API_KEY=your_key
   ```

2. **Update Model Configuration:**
   ```bash
   # From:
   GEMINI_MODEL=gemini-pro
   
   # To:
   LLM_MODEL=gemini-pro
   ```

3. **Consolidate Parameters:**
   ```bash
   # From:
   GEMINI_TEMPERATURE=0.7
   GEMINI_MAX_TOKENS=1000
   
   # To:
   LLM_TEMPERATURE=0.7
   LLM_MAX_TOKENS=1000
   ```

4. **Test Configuration:**
   ```bash
   docker-compose up --build
   curl http://localhost:8000/health
   ```

## Troubleshooting

### Common Issues

#### 1. "No LLM provider configuration found"
**Symptoms:**
- Service starts but shows warnings
- Health check shows no provider

**Solutions:**
- Set `LLM_PROVIDER` environment variable
- Ensure `LLM_API_KEY` is set
- Check `.env` file is loaded correctly

#### 2. "Invalid API key"
**Symptoms:**
- Provider initialization fails
- Authentication errors in logs

**Solutions:**
- Verify API key is correct
- Check key hasn't expired
- Ensure no extra spaces in key
- Regenerate key if necessary

#### 3. "Provider unavailable"
**Symptoms:**
- Health check shows provider as unhealthy
- Requests fail with provider errors

**Solutions:**
- Check internet connectivity
- Verify API endpoint is accessible
- Check for rate limiting
- Validate model name is supported

#### 4. "Ollama connection failed"
**Symptoms:**
- Cannot connect to local Ollama
- Timeout errors

**Solutions:**
- Ensure Ollama is running: `ollama serve`
- Check Ollama is accessible: `curl http://localhost:11434/api/tags`
- Verify model is pulled: `ollama list`
- Check firewall settings

#### 5. "Model not found"
**Symptoms:**
- Provider connects but model errors
- Invalid model name errors

**Solutions:**
- Check supported models for your provider
- Verify model name spelling
- For Ollama: `ollama pull model_name`
- Use default model if unsure

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
LOG_LEVEL=DEBUG
DEBUG=true
```

### Health Check Endpoints

Monitor provider status:

```bash
# Overall health
curl http://localhost:8000/health

# Detailed agent status
curl http://localhost:8000/agent/status
```

### Configuration Testing

Test your configuration:

```bash
# Test basic functionality
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{"user_input": "Hello, test my configuration"}'
```

## Best Practices

1. **Use Unified Configuration:** Prefer the new `LLM_PROVIDER` approach
2. **Secure API Keys:** Never commit keys to version control
3. **Monitor Usage:** Track API usage and costs
4. **Test Thoroughly:** Validate configuration after changes
5. **Have Fallbacks:** Consider multiple providers for reliability
6. **Update Regularly:** Keep models and configurations current
7. **Monitor Performance:** Track response times and success rates

## Support

For additional help:
- Check service logs: `docker-compose logs ai-agent`
- Review health endpoints: `/health` and `/agent/status`
- Consult provider documentation
- Check GitHub issues for known problems