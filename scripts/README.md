# Development Scripts

This directory contains development and testing utilities for the AI Agent MCP Service Learning Project.

## Scripts Overview

### 🏥 Health and Status Monitoring

#### `health_check.py`
Comprehensive health check for all services.
```bash
python scripts/health_check.py
```
- Tests AI Agent service endpoints
- Tests MCP service endpoints  
- Tests database connectivity through MCP service
- Returns exit code 0 (success) or 1 (failure)

#### `docker_status.sh`
Quick Docker container status overview.
```bash
./scripts/docker_status.sh
```
- Shows container status and health
- Displays service URLs
- Lists common Docker commands

### 🗄️ Database Testing

#### `test_database.py`
Direct database connectivity and operations testing.
```bash
python scripts/test_database.py
```
- Tests PostgreSQL connection
- Validates database schema
- Tests CRUD operations
- Checks database indexes
- Returns exit code 0 (success) or 1 (failure)

### 🌐 API Testing

#### `api_examples.py`
API endpoint testing with sample requests.
```bash
python scripts/api_examples.py
```
- Tests all AI Agent endpoints
- Tests all MCP service tools
- Provides curl command examples
- Returns exit code 0 (success) or 1 (failure)

### 🧪 Test Suite

#### `run_all_tests.py`
Runs all development utilities in sequence.
```bash
python scripts/run_all_tests.py
```
- Executes health checks
- Runs database tests
- Tests API endpoints
- Provides comprehensive summary
- Returns exit code 0 (success) or 1 (failure)

## Setup

### Install Dependencies
```bash
# Install Python dependencies for scripts
pip install -r scripts/requirements.txt
```

### Environment Variables
Scripts use the same environment variables as the main application:
- `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`
- Or use defaults: localhost:5432, aiagent_mcp, aiagent, secure_password_here

## Usage Examples

### Quick Health Check
```bash
# Check if all services are running
python scripts/health_check.py && echo "All systems go!" || echo "Issues detected"
```

### Development Workflow
```bash
# 1. Start services
docker-compose up -d

# 2. Wait for startup
sleep 10

# 3. Run full test suite
python scripts/run_all_tests.py

# 4. Check status
./scripts/docker_status.sh
```

### Troubleshooting
```bash
# If health checks fail, check Docker status
./scripts/docker_status.sh

# View service logs
docker-compose logs -f

# Test database directly
python scripts/test_database.py

# Test specific API endpoints
python scripts/api_examples.py
```

## Integration with CI/CD

These scripts are designed to be used in automated testing:

```bash
#!/bin/bash
# Example CI script
set -e

# Start services
docker-compose up -d

# Wait for services to be ready
sleep 30

# Run tests
python scripts/run_all_tests.py

# Cleanup
docker-compose down
```

## Script Exit Codes

All scripts follow standard exit code conventions:
- `0`: Success - all tests passed
- `1`: Failure - one or more tests failed

This allows for easy integration with shell scripts and CI/CD pipelines:

```bash
if python scripts/health_check.py; then
    echo "Services are healthy"
else
    echo "Service issues detected"
    exit 1
fi
```

## Customization

### Adding New Tests
To add new test scripts:

1. Create script in `scripts/` directory
2. Make it executable: `chmod +x scripts/your_script.py`
3. Follow the exit code convention (0=success, 1=failure)
4. Add it to `run_all_tests.py` if needed
5. Update this README

### Environment Configuration
Scripts can be configured via environment variables:

```bash
# Custom database connection
export POSTGRES_HOST=custom-host
export POSTGRES_PORT=5433
python scripts/test_database.py

# Custom service URLs
export AI_AGENT_URL=http://localhost:9000
export MCP_SERVICE_URL=http://localhost:9001
python scripts/health_check.py
```

## Troubleshooting Scripts

### Common Issues

#### Import Errors
```bash
# Install missing dependencies
pip install -r scripts/requirements.txt
```

#### Permission Errors
```bash
# Make scripts executable
chmod +x scripts/*.py scripts/*.sh
```

#### Connection Errors
```bash
# Verify services are running
docker-compose ps

# Check service logs
docker-compose logs -f [service-name]
```

For more detailed troubleshooting, see `docs/DEVELOPMENT_GUIDE.md`.