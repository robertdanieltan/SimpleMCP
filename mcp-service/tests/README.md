# MCP Service Test Suite

This directory contains a comprehensive test suite for the MCP service, covering integration tests, performance tests, container deployment verification, and error scenario testing.

## Test Suite Overview

### 1. Integration Tests (`test_integration.py`)
- **Purpose**: Test all MCP tools functionality with real database operations
- **Coverage**: 
  - Complete CRUD operations for projects and tasks
  - Data validation and constraint testing
  - Cross-tool integration (projects with tasks)
  - Database transaction integrity
  - Filtering and pagination
  - Concurrent operations
  - Edge cases and boundary conditions

### 2. Performance Tests (`test_performance.py`)
- **Purpose**: Benchmark database operations and test performance under load
- **Coverage**:
  - Single operation performance benchmarks
  - Bulk operations testing
  - Concurrent request handling
  - Memory usage monitoring
  - Database connection performance
  - Response time analysis

### 3. Container Deployment Tests (`test_container_deployment.py`)
- **Purpose**: Verify Docker container deployment and orchestration
- **Coverage**:
  - Docker Compose status verification
  - Container health and resource monitoring
  - Service endpoint accessibility
  - Database connectivity from containers
  - Environment configuration validation
  - Service integration testing

### 4. Error Scenario Tests (`test_error_scenarios.py`)
- **Purpose**: Test error handling and edge cases
- **Coverage**:
  - Input validation errors
  - Database constraint violations
  - Non-existent resource operations
  - Boundary value scenarios
  - Special character handling
  - Concurrent modification scenarios
  - Resource exhaustion testing

## Prerequisites

### Environment Setup
1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **Environment Variables**: Set up required environment variables in `.env`
3. **Python Dependencies**: Install required packages (see requirements below)

### Required Python Packages
```bash
pip install pytest psycopg2-binary docker requests psutil
```

### Docker Requirements (for container tests)
- Docker and Docker Compose installed
- MCP service containers running (`docker-compose up -d`)

## Running Tests

### Individual Test Suites

#### Integration Tests
```bash
# Run with pytest (recommended)
cd mcp-service/tests
python -m pytest test_integration.py -v

# Run directly
python test_integration.py
```

#### Performance Tests
```bash
python test_performance.py
```

#### Container Deployment Tests
```bash
python test_container_deployment.py
```

#### Error Scenario Tests
```bash
python test_error_scenarios.py
```

### All Tests
```bash
# Run all tests with the test runner
python run_all_tests.py

# Or run individual suites sequentially
python test_integration.py
python test_performance.py
python test_container_deployment.py
python test_error_scenarios.py
```

## Test Configuration

### Environment Variables
The tests use the following environment variables:

```bash
# Database connection
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/aiagent_mcp

# For container tests
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=aiagent_mcp

# Service URLs
MCP_SERVICE_URL=http://localhost:8001
```

### Performance Thresholds
Performance tests use the following thresholds (configurable in `test_performance.py`):

- `create_project`: 0.1s
- `create_task`: 0.1s
- `list_projects`: 0.05s
- `list_tasks`: 0.05s
- `update_project`: 0.1s
- `update_task`: 0.1s
- `delete_project`: 0.1s
- `delete_task`: 0.1s

## Test Results

### Output Files
Each test suite generates detailed JSON results:

- `mcp_integration_test_results.json` - Integration test results
- `mcp_performance_test_results.json` - Performance benchmarks
- `container_deployment_test_results.json` - Container deployment status
- `error_scenario_test_results.json` - Error handling test results

### Result Format
```json
{
  "summary": {
    "total_tests": 50,
    "passed": 48,
    "failed": 2,
    "success_rate": 96.0,
    "timestamp": "2024-01-01T12:00:00Z"
  },
  "results": [
    {
      "test": "Test Name",
      "success": true,
      "timestamp": "2024-01-01T12:00:00Z",
      "details": {}
    }
  ]
}
```

## Test Data Management

### Cleanup
All tests include automatic cleanup of test data:
- Test projects and tasks are automatically deleted after tests
- Failed tests may leave some test data (check manually if needed)

### Test Data Isolation
- Tests use unique names with timestamps to avoid conflicts
- Each test suite manages its own test data
- Tests can run concurrently without interference

## Troubleshooting

### Common Issues

#### Database Connection Errors
```bash
# Check database is running
docker-compose ps postgres

# Check connection manually
psql postgresql://postgres:postgres@localhost:5432/aiagent_mcp
```

#### Container Tests Failing
```bash
# Ensure containers are running
docker-compose up -d

# Check container status
docker-compose ps

# Check service health
curl http://localhost:8001/health
```

#### Permission Errors
```bash
# Ensure proper file permissions
chmod +x test_*.py

# Check Docker permissions
docker ps
```

### Debug Mode
Enable debug logging by setting environment variable:
```bash
export LOG_LEVEL=DEBUG
python test_integration.py
```

## Continuous Integration

### GitHub Actions Example
```yaml
name: MCP Service Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: aiagent_mcp
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        pip install -r mcp-service/requirements.txt
        pip install pytest psycopg2-binary
    
    - name: Run tests
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/aiagent_mcp
      run: |
        cd mcp-service/tests
        python run_all_tests.py
```

## Contributing

### Adding New Tests
1. Follow the existing test structure and naming conventions
2. Include proper cleanup in test teardown
3. Add comprehensive error handling
4. Document test purpose and coverage
5. Update this README with new test information

### Test Guidelines
- Use descriptive test names
- Include both positive and negative test cases
- Test edge cases and boundary conditions
- Ensure tests are idempotent and can run multiple times
- Clean up test data properly
- Log meaningful test results and error messages

## Performance Benchmarks

### Expected Performance (on typical development machine)
- Project creation: < 100ms
- Task creation: < 100ms
- List operations: < 50ms
- Update operations: < 100ms
- Delete operations: < 100ms

### Load Testing Results
- Concurrent operations: 10+ simultaneous requests
- Bulk operations: 100+ items in < 5 seconds
- Memory usage: < 100MB increase during testing
- Database connections: Stable under concurrent load

## Security Testing

The error scenario tests include basic security boundary testing:
- SQL injection attempt handling
- XSS prevention in data storage
- Input validation for malicious content
- Resource exhaustion protection

For comprehensive security testing, consider additional tools like:
- OWASP ZAP for web application security
- SQLMap for SQL injection testing
- Custom penetration testing scripts