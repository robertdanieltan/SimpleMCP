# Docker Orchestration and Health Monitoring

This document explains the Docker orchestration setup and health monitoring configuration for the AI Agent MCP Service infrastructure.

## Architecture Overview

The system consists of four containerized services orchestrated with Docker Compose:

```
┌─────────────────┐    ┌─────────────────┐
│   AI Agent      │    │   MCP Service   │
│   (Port 8000)   │◄──►│   (Port 8001)   │
└─────────────────┘    └─────────────────┘
         │                       │
         │              ┌─────────────────┐
         │              │   PostgreSQL    │
         │              │   (Port 5432)   │
         │              └─────────────────┘
         │                       ▲
         │              ┌─────────────────┐
         └─────────────►│    pgAdmin      │
                        │   (Port 8080)   │
                        └─────────────────┘
```

## Service Dependencies

Services start in the following order based on health checks:

1. **PostgreSQL** - Database service (no dependencies)
2. **MCP Service** - Waits for PostgreSQL to be healthy
3. **AI Agent Service** - Waits for MCP Service to be healthy
4. **pgAdmin** - Waits for PostgreSQL to be healthy

## Health Check Configuration

### AI Agent Service
- **Endpoint**: `http://localhost:8000/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 40 seconds

### MCP Service
- **Endpoint**: `http://localhost:8001/health`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 40 seconds

### PostgreSQL
- **Command**: `pg_isready -U postgres -d aiagent_mcp`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 5
- **Start Period**: 30 seconds

### pgAdmin
- **Endpoint**: `http://localhost/misc/ping`
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 60 seconds

## Volume Persistence

### PostgreSQL Data
- **Volume**: `postgres_data`
- **Mount**: `/var/lib/postgresql/data`
- **Purpose**: Persistent database storage

### pgAdmin Configuration
- **Volume**: `pgadmin_data`
- **Mount**: `/var/lib/pgadmin`
- **Purpose**: Persistent pgAdmin settings and connections

### Database Initialization
- **Mount**: `./database/init.sql` → `/docker-entrypoint-initdb.d/01-init.sql`
- **Mount**: `./database/test_data.sql` → `/docker-entrypoint-initdb.d/02-test-data.sql`
- **Purpose**: Automatic database schema and test data setup

### pgAdmin Pre-configuration
- **Mount**: `./database/pgadmin_servers.json` → `/pgadmin4/servers.json`
- **Purpose**: Pre-configured database connection

## Restart Policies

All services use `restart: unless-stopped` policy:
- Services automatically restart on failure
- Services don't restart if manually stopped
- Services restart when Docker daemon starts

## Network Configuration

- **Network**: `aiagent-network` (bridge driver)
- **Purpose**: Isolated network for service communication
- **DNS**: Services can communicate using service names

## Monitoring and Debugging

### Health Check Scripts

#### Python Health Checker
```bash
python scripts/health_check.py
```
Checks HTTP endpoints of all services.

#### Docker Status Monitor
```bash
./scripts/docker_status.sh
```
Shows container status and health information.

### Common Commands

#### Start Services
```bash
docker-compose up -d
```

#### View Service Status
```bash
docker-compose ps
```

#### Check Service Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ai-agent
docker-compose logs -f mcp-service
docker-compose logs -f postgres
docker-compose logs -f pgadmin
```

#### Restart Services
```bash
# All services
docker-compose restart

# Specific service
docker-compose restart ai-agent
```

#### Stop Services
```bash
docker-compose down
```

#### Rebuild and Start
```bash
docker-compose up --build -d
```

### Development Override

The `docker-compose.override.yml` file provides development-specific configurations:
- Debug logging enabled
- PostgreSQL query logging
- Enhanced pgAdmin logging
- Optional source code mounting

## Troubleshooting

### Service Won't Start
1. Check dependencies are healthy: `docker-compose ps`
2. View service logs: `docker-compose logs [service]`
3. Verify environment variables in `.env`

### Health Check Failures
1. Check if service is responding: `curl http://localhost:[port]/health`
2. Verify network connectivity between containers
3. Check service startup time (may need longer start_period)

### Database Connection Issues
1. Verify PostgreSQL is healthy: `docker-compose ps postgres`
2. Check database logs: `docker-compose logs postgres`
3. Test connection: `docker-compose exec postgres psql -U postgres -d aiagent_mcp`

### pgAdmin Access Issues
1. Verify pgAdmin is healthy: `docker-compose ps pgadmin`
2. Check pgAdmin logs: `docker-compose logs pgadmin`
3. Access web interface: http://localhost:8080
4. Default credentials from `.env` file

## Security Considerations

- All services run in isolated Docker network
- Database credentials managed through environment variables
- pgAdmin configured for development use (not production-ready)
- Health check endpoints don't expose sensitive information

## Performance Tuning

### Health Check Intervals
- Adjust `interval` for more/less frequent checks
- Increase `timeout` for slower responses
- Modify `retries` based on reliability needs

### Resource Limits
Add resource limits to docker-compose.yml if needed:
```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

### Database Performance
- PostgreSQL configured with query logging for development
- Consider connection pooling for production use
- Monitor database performance through pgAdmin