# LLM Provider Troubleshooting Guide

This guide helps diagnose and resolve common issues with LLM provider configuration and usage.

## Quick Diagnosis

### Check Service Status
```bash
# Overall health
curl http://localhost:8000/health

# Detailed status
curl http://localhost:8000/agent/status

# Service logs
docker-compose logs ai-agent
```

### Configuration Validation
```bash
# Check environment variables
docker-compose exec ai-agent env | grep LLM

# Test basic functionality
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{"user_input": "test"}'
```

## Common Issues and Solutions

### 1. Service Won't Start

#### Symptoms
- Container exits immediately
- "Failed to initialize AI Agent" in logs
- Service unreachable

#### Possible Causes
- Missing environment variables
- Invalid configuration
- Port conflicts
- Docker issues

#### Solutions

**Check Environment Configuration:**
```bash
# Verify .env file exists
ls -la .env

# Check required variables
grep -E "LLM_|GEMINI_|OPENAI_|ANTHROPIC_" .env
```

**Validate Docker Setup:**
```bash
# Rebuild containers
docker-compose down
docker-compose up --build

# Check port conflicts
netstat -tulpn | grep :8000
```

**Fix Common Configuration Issues:**
```bash
# Ensure no trailing spaces in .env
sed -i 's/[[:space:]]*$//' .env

# Check for special characters
cat -A .env | grep LLM
```

### 2. Provider Authentication Failures

#### Symptoms
- "Invalid API key" errors
- "Authentication failed" messages
- 401/403 HTTP errors

#### Diagnosis Steps

**Verify API Key Format:**
```bash
# Check key length and format
echo $LLM_API_KEY | wc -c

# Gemini keys start with "AIza"
# OpenAI keys start with "sk-"
# Anthropic keys start with "sk-ant-"
```

**Test API Key Directly:**
```bash
# Gemini
curl -H "x-goog-api-key: $LLM_API_KEY" \
  "https://generativelanguage.googleapis.com/v1/models"

# OpenAI
curl -H "Authorization: Bearer $LLM_API_KEY" \
  "https://api.openai.com/v1/models"

# Anthropic
curl -H "x-api-key: $LLM_API_KEY" \
  "https://api.anthropic.com/v1/messages" \
  -X POST -d '{"model":"claude-3-sonnet-20240229","max_tokens":1,"messages":[{"role":"user","content":"test"}]}'
```

#### Solutions

**Regenerate API Keys:**
1. Visit provider console
2. Create new API key
3. Update `.env` file
4. Restart service

**Check Account Status:**
- Verify account is active
- Check billing/credits
- Ensure API access is enabled

### 3. Model Not Found Errors

#### Symptoms
- "Model not found" errors
- "Invalid model" messages
- Model-specific failures

#### Solutions

**Verify Model Names:**
```bash
# Check supported models per provider
curl http://localhost:8000/agent/status | jq '.current_provider.capabilities'
```

**Update Model Configuration:**
```bash
# Gemini
LLM_MODEL=gemini-pro  # or gemini-pro-vision

# OpenAI
LLM_MODEL=gpt-3.5-turbo  # or gpt-4, gpt-4-turbo

# Anthropic
LLM_MODEL=claude-3-sonnet-20240229  # or claude-3-opus-20240229

# Ollama - ensure model is pulled
ollama pull llama2
LLM_MODEL=llama2
```

### 4. Ollama Connection Issues

#### Symptoms
- "Connection refused" to localhost:11434
- Ollama provider unavailable
- Timeout errors

#### Diagnosis
```bash
# Check if Ollama is running
ps aux | grep ollama

# Test Ollama API
curl http://localhost:11434/api/tags

# Check available models
ollama list
```

#### Solutions

**Start Ollama Service:**
```bash
# Start Ollama
ollama serve

# Or as background service
nohup ollama serve > ollama.log 2>&1 &
```

**Pull Required Models:**
```bash
# Pull model
ollama pull llama2

# Verify model is available
ollama list
```

**Fix Network Issues:**
```bash
# Check if port is accessible
telnet localhost 11434

# Update base URL if needed
LLM_BASE_URL=http://host.docker.internal:11434  # For Docker
```

### 5. Rate Limiting Issues

#### Symptoms
- "Rate limit exceeded" errors
- 429 HTTP status codes
- Intermittent failures

#### Solutions

**Check Rate Limits:**
- Gemini: 60 requests/minute (free tier)
- OpenAI: Varies by plan
- Anthropic: Varies by plan

**Implement Backoff:**
```bash
# Increase timeout
LLM_TIMEOUT=60

# Reduce concurrent requests
LLM_MAX_RETRIES=3
```

**Upgrade Plan:**
- Consider paid tiers for higher limits
- Monitor usage in provider consoles

### 6. Response Quality Issues

#### Symptoms
- Poor response quality
- Inconsistent behavior
- Unexpected outputs

#### Solutions

**Adjust Parameters:**
```bash
# Lower temperature for more consistent responses
LLM_TEMPERATURE=0.3

# Increase max tokens for longer responses
LLM_MAX_TOKENS=2000

# Try different models
LLM_MODEL=gpt-4  # More capable but slower/expensive
```

**Provider-Specific Tuning:**
```bash
# Gemini safety settings
LLM_SAFETY_SETTINGS=default

# OpenAI organization for better models
LLM_ORGANIZATION=your_org_id

# Anthropic for analysis tasks
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-opus-20240229
```

### 7. Performance Issues

#### Symptoms
- Slow response times
- Timeouts
- High latency

#### Diagnosis
```bash
# Check response times in status
curl http://localhost:8000/agent/status | jq '.current_provider.performance'

# Monitor logs for timing
docker-compose logs ai-agent | grep "response_time"
```

#### Solutions

**Optimize Configuration:**
```bash
# Reduce max tokens
LLM_MAX_TOKENS=500

# Increase timeout
LLM_TIMEOUT=60

# Use faster models
LLM_MODEL=gpt-3.5-turbo  # Instead of gpt-4
LLM_MODEL=claude-3-haiku-20240307  # Instead of opus
```

**Network Optimization:**
```bash
# Use regional endpoints if available
LLM_BASE_URL=https://api.openai.com/v1  # Ensure correct endpoint

# Check DNS resolution
nslookup api.openai.com
```

### 8. Docker and Container Issues

#### Symptoms
- Container won't start
- Environment variables not loaded
- Network connectivity issues

#### Solutions

**Fix Environment Loading:**
```bash
# Ensure .env is in correct location
ls -la .env

# Check Docker Compose version
docker-compose --version

# Rebuild with no cache
docker-compose build --no-cache
```

**Network Issues:**
```bash
# Check Docker networks
docker network ls

# Inspect network configuration
docker network inspect ai-agent-mcp-service_default

# Test inter-container connectivity
docker-compose exec ai-agent ping mcp-service
```

**Volume and Permission Issues:**
```bash
# Check file permissions
ls -la .env

# Fix permissions if needed
chmod 644 .env

# Check Docker daemon
sudo systemctl status docker
```

## Advanced Troubleshooting

### Debug Mode

Enable comprehensive logging:

```bash
# In .env file
LOG_LEVEL=DEBUG
DEBUG=true
LOG_FORMAT=detailed

# Restart service
docker-compose up --build
```

### Provider-Specific Debug

**Gemini Debug:**
```bash
# Enable Gemini debug logging
GEMINI_DEBUG=true

# Check safety settings
GEMINI_SAFETY_SETTINGS=debug
```

**OpenAI Debug:**
```bash
# Enable OpenAI debug
OPENAI_DEBUG=true

# Check organization
echo $LLM_ORGANIZATION
```

**Anthropic Debug:**
```bash
# Enable Anthropic debug
ANTHROPIC_DEBUG=true

# Check message format
ANTHROPIC_MESSAGE_FORMAT=debug
```

### Health Check Analysis

Interpret health check responses:

```bash
# Get detailed health info
curl -s http://localhost:8000/health | jq '.'

# Check specific provider status
curl -s http://localhost:8000/agent/status | jq '.current_provider'

# Monitor performance metrics
curl -s http://localhost:8000/health | jq '.performance_metrics'
```

### Log Analysis

Analyze service logs:

```bash
# Filter for errors
docker-compose logs ai-agent | grep ERROR

# Check initialization
docker-compose logs ai-agent | grep "initialized"

# Monitor requests
docker-compose logs ai-agent | grep "process_request"

# Check provider selection
docker-compose logs ai-agent | grep "provider"
```

## Prevention Tips

### Configuration Best Practices

1. **Use Configuration Templates:**
   ```bash
   cp .env.example .env
   # Edit with your values
   ```

2. **Validate Before Deployment:**
   ```bash
   # Test configuration
   docker-compose config
   
   # Dry run
   docker-compose up --dry-run
   ```

3. **Monitor Regularly:**
   ```bash
   # Set up health monitoring
   curl -f http://localhost:8000/health || echo "Service down"
   ```

### Security Best Practices

1. **Secure API Keys:**
   ```bash
   # Never commit .env
   echo ".env" >> .gitignore
   
   # Use strong permissions
   chmod 600 .env
   ```

2. **Rotate Keys Regularly:**
   - Set calendar reminders
   - Use key management systems
   - Monitor for key exposure

3. **Monitor Usage:**
   - Check provider dashboards
   - Set up billing alerts
   - Track unusual patterns

### Maintenance Schedule

**Weekly:**
- Check service health
- Review error logs
- Monitor API usage

**Monthly:**
- Update dependencies
- Review configuration
- Test backup providers

**Quarterly:**
- Rotate API keys
- Review provider costs
- Update documentation

## Getting Help

### Self-Service Resources

1. **Service Endpoints:**
   - Health: `http://localhost:8000/health`
   - Status: `http://localhost:8000/agent/status`
   - Docs: `http://localhost:8000/docs`

2. **Log Files:**
   ```bash
   docker-compose logs ai-agent > debug.log
   ```

3. **Configuration Dump:**
   ```bash
   docker-compose exec ai-agent env | grep -E "LLM_|GEMINI_|OPENAI_|ANTHROPIC_" > config.txt
   ```

### Provider Support

- **Gemini:** https://ai.google.dev/docs
- **OpenAI:** https://platform.openai.com/docs
- **Anthropic:** https://docs.anthropic.com/
- **Ollama:** https://ollama.ai/docs

### Community Resources

- GitHub Issues
- Stack Overflow
- Provider community forums
- Docker community

## Escalation Checklist

Before seeking help, gather:

1. **Service Information:**
   - Version numbers
   - Configuration (sanitized)
   - Error messages
   - Log excerpts

2. **Environment Details:**
   - Operating system
   - Docker version
   - Network configuration
   - Hardware specs (for Ollama)

3. **Reproduction Steps:**
   - Minimal test case
   - Expected vs actual behavior
   - Frequency of issue
   - Recent changes

4. **Troubleshooting Attempted:**
   - Steps already tried
   - Results of each attempt
   - Current workarounds
   - Impact assessment