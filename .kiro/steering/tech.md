# Technology Stack

## Core Technologies

### Backend Framework
- **FastAPI**: Primary web framework for both AI agent service and MCP service
- **FastMCP**: Framework for MCP service implementation
- **Python 3.11**: Programming language

### AI & ML
- **Gemini API**: Natural language processing and AI agent capabilities
- **CrewAI**: Framework for advanced multi-agent coordination (future enhancement)

### Database
- **PostgreSQL 16**: Primary database for data persistence
- **pgAdmin**: Database administration interface
- **Synchronous database operations**: Use sync methods only

### Containerization
- **Docker**: Container platform
- **Docker Compose**: Multi-service orchestration

## Architecture Ports
- **AI Agent Service**: Port 8000
- **MCP Service**: Port 8001  
- **PostgreSQL**: Port 5432
- **pgAdmin**: Port 8080

## Environment Configuration
Required environment variables in `.env`:
- `GEMINI_API_KEY`: API key for Gemini integration
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database credentials
- `PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`: pgAdmin access
- `DATABASE_URL`: PostgreSQL connection string

## Common Commands

### Development Setup
```bash
# Create virtual environment (if needed for testing)
python -m venv venv
source venv/bin/activate  # On macOS/Linux

# Environment setup
cp .env.example .env  # Configure with actual API keys
```

### Docker Operations
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild containers
docker-compose up --build
```

### Service Health Checks
```bash
# AI Agent Service
curl http://localhost:8000/health
curl http://localhost:8000/agent/status

# MCP Service
curl http://localhost:8001/health
```

## Development Principles
- **KISS Principle**: Keep implementations simple for learning purposes
- **Separate Containers**: AI agent and MCP service run in separate FastAPI containers
- **HTTP Communication**: Services communicate via HTTP REST APIs
- **Synchronous Operations**: Use sync database methods only