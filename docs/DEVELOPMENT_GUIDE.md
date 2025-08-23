# Development Guide

This guide provides essential commands, troubleshooting steps, and development utilities for the AI Agent MCP Service Learning Project.

## Quick Start

### 1. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your API keys and credentials
# Required: GEMINI_API_KEY, database credentials
```

### 2. Start All Services
```bash
# Start all services in background
docker-compose up -d

# Start with logs visible
docker-compose up

# Start specific services
docker-compose up postgres pgadmin
```

### 3. Verify Setup
```bash
# Run health checks
python scripts/health_check.py

# Test database connectivity
python scripts/test_database.py

# Test API endpoints
python scripts/api_examples.py
```

## Docker Commands

### Service Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart specific service
docker-compose restart ai-agent

# Rebuild and start services
docker-compose up --build

# Remove containers and volumes
docker-compose down -v
```

### Monitoring and Logs
```bash
# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f ai-agent
docker-compose logs -f mcp-service
docker-compose logs -f postgres

# Check service status
docker-compose ps

# View resource usage
docker stats
```

### Container Management
```bash
# Execute command in running container
docker-compose exec ai-agent bash
docker-compose exec mcp-service python -c "import sys; print(sys.version)"
docker-compose exec postgres psql -U aiagent -d aiagent_mcp

# View container details
docker-compose exec ai-agent env
docker inspect $(docker-compose ps -q ai-agent)
```

## Service URLs and Ports

| Service | URL | Purpose |
|---------|-----|---------|
| AI Agent | http://localhost:8000 | FastAPI AI agent service |
| MCP Service | http://localhost:8001 | FastMCP service with tools |
| PostgreSQL | localhost:5432 | Database server |
| pgAdmin | http://localhost:8080 | Database administration |

### Health Check Endpoints
```bash
# AI Agent Service
curl http://localhost:8000/health
curl http://localhost:8000/agent/status

# MCP Service  
curl http://localhost:8001/health
```

## Development Utilities

### Health Check Script
```bash
# Run comprehensive health checks
python scripts/health_check.py

# Expected output: All services healthy
# Exit code: 0 (success) or 1 (failure)
```

### Database Test Script
```bash
# Test database connectivity and operations
python scripts/test_database.py

# Tests: connection, schema, CRUD operations, indexes
# Exit code: 0 (success) or 1 (failure)
```

### API Examples Script
```bash
# Test all API endpoints with sample requests
python scripts/api_examples.py

# Includes: health checks, tool calls, agent requests
# Exit code: 0 (success) or 1 (failure)
```

## Troubleshooting

### Common Issues

#### 1. Services Won't Start
**Symptoms:** `docker-compose up` fails or containers exit immediately

**Solutions:**
```bash
# Check for port conflicts
netstat -tulpn | grep -E ':(8000|8001|5432|8080)'

# View detailed error logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose up --build

# Check disk space
df -h
```

#### 2. Database Connection Errors
**Symptoms:** MCP service can't connect to PostgreSQL

**Solutions:**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test direct connection
docker-compose exec postgres psql -U aiagent -d aiagent_mcp -c "SELECT 1;"

# Verify environment variables
docker-compose exec mcp-service env | grep -E '(DATABASE|POSTGRES)'

# Reset database
docker-compose down -v
docker-compose up postgres
```

#### 3. API Endpoints Not Responding
**Symptoms:** HTTP requests timeout or return connection errors

**Solutions:**
```bash
# Check service status
docker-compose ps

# Verify port bindings
docker-compose port ai-agent 8000
docker-compose port mcp-service 8001

# Check service logs
docker-compose logs ai-agent
docker-compose logs mcp-service

# Test from inside container
docker-compose exec ai-agent curl http://localhost:8000/health
```

#### 4. Gemini API Errors
**Symptoms:** AI agent returns API key or quota errors

**Solutions:**
```bash
# Verify API key is set
docker-compose exec ai-agent env | grep GEMINI_API_KEY

# Check .env file
cat .env | grep GEMINI_API_KEY

# Test API key manually
curl -H "Authorization: Bearer YOUR_API_KEY" \
  https://generativelanguage.googleapis.com/v1/models
```

#### 5. pgAdmin Access Issues
**Symptoms:** Can't access pgAdmin web interface

**Solutions:**
```bash
# Check pgAdmin container
docker-compose ps pgadmin

# View pgAdmin logs
docker-compose logs pgadmin

# Verify credentials
docker-compose exec pgadmin env | grep PGADMIN

# Reset pgAdmin
docker-compose restart pgadmin
```

### Performance Issues

#### Slow Database Operations
```bash
# Check database performance
docker-compose exec postgres psql -U aiagent -d aiagent_mcp -c "
  SELECT schemaname, tablename, attname, n_distinct, correlation 
  FROM pg_stats 
  WHERE schemaname = 'public';"

# Analyze query performance
docker-compose exec postgres psql -U aiagent -d aiagent_mcp -c "
  EXPLAIN ANALYZE SELECT * FROM tasks WHERE status = 'pending';"
```

#### High Memory Usage
```bash
# Monitor container resources
docker stats

# Check container limits
docker-compose exec ai-agent cat /sys/fs/cgroup/memory/memory.limit_in_bytes

# Restart services to free memory
docker-compose restart
```

### Development Tips

#### Code Changes
```bash
# For Python code changes, restart the specific service
docker-compose restart ai-agent
docker-compose restart mcp-service

# For dependency changes, rebuild
docker-compose up --build ai-agent
```

#### Database Schema Changes
```bash
# Apply schema changes
docker-compose exec postgres psql -U aiagent -d aiagent_mcp -f /path/to/migration.sql

# Or recreate database
docker-compose down -v
docker-compose up postgres
```

#### Testing New Features
```bash
# Create test environment
cp docker-compose.yml docker-compose.test.yml
# Modify ports and service names in test file
docker-compose -f docker-compose.test.yml up
```

## Environment Variables Reference

### Required Variables (.env)
```env
# Gemini API Configuration
GEMINI_API_KEY=your_gemini_api_key_here

# Database Configuration
POSTGRES_USER=aiagent
POSTGRES_PASSWORD=secure_password_here
POSTGRES_DB=aiagent_mcp
DATABASE_URL=postgresql://aiagent:secure_password_here@postgres:5432/aiagent_mcp

# pgAdmin Configuration
PGADMIN_DEFAULT_EMAIL=admin@example.com
PGADMIN_DEFAULT_PASSWORD=admin_password_here
```

### Optional Variables
```env
# Service Configuration
AI_AGENT_PORT=8000
MCP_SERVICE_PORT=8001
POSTGRES_PORT=5432
PGADMIN_PORT=8080

# Development Settings
DEBUG=true
LOG_LEVEL=INFO
```

## Useful Commands Reference

### Quick Status Check
```bash
# One-liner to check all services
docker-compose ps && python scripts/health_check.py
```

### Complete Reset
```bash
# Nuclear option: reset everything
docker-compose down -v --remove-orphans
docker system prune -f
docker-compose up --build
```

### Backup Database
```bash
# Create database backup
docker-compose exec postgres pg_dump -U aiagent aiagent_mcp > backup.sql

# Restore database backup
docker-compose exec -T postgres psql -U aiagent aiagent_mcp < backup.sql
```

### View All Logs
```bash
# Tail all service logs with timestamps
docker-compose logs -f -t
```

This guide should help you develop, debug, and maintain the AI Agent MCP Service project effectively. For additional help, check the service-specific documentation in each service directory.