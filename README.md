# AI Agent MCP Service Learning Project

A comprehensive learning project focused on **Model Context Protocol (MCP)** service development and AI agent integration. This project demonstrates how to build AI agents that interact with MCP services for task and project management using FastAPI, Docker, and PostgreSQL.

## 🎯 Learning Objectives

- **MCP Development**: Build HTTP-based MCP services using FastAPI/FastMCP
- **AI Agent Integration**: Create agents using Gemini API for natural language processing
- **Containerization**: Learn Docker best practices for AI services
- **Database Integration**: Implement PostgreSQL for data persistence
- **Multi-service Architecture**: Master orchestration patterns with Docker Compose

## 🏗️ Architecture Overview

This project follows a microservices architecture with four containerized services:

```
┌─────────────────┐    HTTP     ┌─────────────────┐
│   AI Agent      │ ──────────► │   MCP Service   │
│   Service       │             │   (FastMCP)     │
│   (FastAPI)     │             │                 │
│   Port: 8000    │             │   Port: 8001    │
└─────────────────┘             └─────────────────┘
         │                               │
         │ Gemini API                    │ SQL
         ▼                               ▼
┌─────────────────┐             ┌─────────────────┐
│   Gemini API    │             │   PostgreSQL    │
│   (External)    │             │   Database      │
└─────────────────┘             │   Port: 5432    │
                                └─────────────────┘
                                         │
                                         │ Admin UI
                                         ▼
                                ┌─────────────────┐
                                │    pgAdmin      │
                                │   Port: 8080    │
                                └─────────────────┘
```

### Service Communication Flow

1. **User Request** → AI Agent Service (FastAPI)
2. **AI Agent** → Gemini API for natural language processing
3. **AI Agent** → MCP Service via HTTP REST calls
4. **MCP Service** → PostgreSQL for data operations
5. **Response** flows back through the chain

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose installed
- Gemini API key (get from [Google AI Studio](https://makersuite.google.com/app/apikey))

### Setup Instructions

1. **Clone and navigate to the project:**
   ```bash
   git clone <repository-url>
   cd ai-agent-mcp-service
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env file with your actual API keys and credentials
   ```

3. **Start all services:**
   ```bash
   docker-compose up -d
   ```

4. **Verify services are running:**
   ```bash
   # Check all containers
   docker-compose ps
   
   # Test service health
   curl http://localhost:8000/health  # AI Agent Service
   curl http://localhost:8001/health  # MCP Service
   ```

5. **Access services:**
   - **AI Agent Service**: http://localhost:8000
   - **MCP Service**: http://localhost:8001
   - **pgAdmin**: http://localhost:8080 (use credentials from .env)

## 📁 Project Structure

```
├── ai-agent-service/          # AI Agent FastAPI service (Port 8000)
│   ├── main.py               # FastAPI application entry point
│   ├── requirements.txt      # Python dependencies
│   ├── Dockerfile           # Container configuration
│   └── app/                 # Application modules
│       ├── agent/           # AI agent logic
│       ├── mcp_client/      # MCP service HTTP client
│       └── models/          # Data models
│
├── mcp-service/              # MCP Service FastAPI service (Port 8001)
│   ├── main.py              # FastAPI/FastMCP application
│   ├── requirements.txt     # Python dependencies  
│   ├── Dockerfile          # Container configuration
│   └── app/                # Application modules
│       ├── tools/          # MCP tool implementations
│       ├── database/       # Database operations
│       └── models/         # Data models
│
├── database/                # Database setup and scripts
│   ├── init.sql            # Database initialization
│   ├── test_data.sql       # Sample data insertion
│   └── schema/             # Database schema definitions
│
├── docker-compose.yml      # Service orchestration
├── .env.example           # Environment configuration template
└── README.md             # This file
```

## 🛠️ Development Commands

### Docker Operations
```bash
# Start all services
docker-compose up -d

# View logs for all services
docker-compose logs -f

# View logs for specific service
docker-compose logs -f ai-agent

# Stop all services
docker-compose down

# Rebuild and restart services
docker-compose up --build

# Remove all containers and volumes
docker-compose down -v
```

### Service Health Checks
```bash
# AI Agent Service
curl http://localhost:8000/health
curl http://localhost:8000/agent/status

# MCP Service
curl http://localhost:8001/health

# Database connection test
docker-compose exec postgres psql -U aiagent -d aiagent_mcp -c "SELECT version();"
```

### Database Management
```bash
# Connect to PostgreSQL directly
docker-compose exec postgres psql -U aiagent -d aiagent_mcp

# View database logs
docker-compose logs postgres

# Backup database
docker-compose exec postgres pg_dump -U aiagent aiagent_mcp > backup.sql

# Restore database
docker-compose exec -T postgres psql -U aiagent -d aiagent_mcp < backup.sql
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | `your_api_key_here` |
| `POSTGRES_USER` | Database username | `aiagent` |
| `POSTGRES_PASSWORD` | Database password | `secure_password` |
| `POSTGRES_DB` | Database name | `aiagent_mcp` |
| `DATABASE_URL` | Full database connection string | `postgresql://user:pass@host:port/db` |
| `PGADMIN_DEFAULT_EMAIL` | pgAdmin login email | `admin@example.com` |
| `PGADMIN_DEFAULT_PASSWORD` | pgAdmin login password | `admin_password` |

### Service Ports

| Service | Port | Description |
|---------|------|-------------|
| AI Agent Service | 8000 | FastAPI web interface and API |
| MCP Service | 8001 | FastMCP tools and endpoints |
| PostgreSQL | 5432 | Database server |
| pgAdmin | 8080 | Database administration web UI |

## 🧪 Testing

### Manual Testing
```bash
# Test AI Agent endpoints
curl -X GET http://localhost:8000/health
curl -X GET http://localhost:8000/agent/status

# Test MCP Service endpoints
curl -X GET http://localhost:8001/health

# Test database connectivity
docker-compose exec postgres psql -U aiagent -d aiagent_mcp -c "\dt"
```

### Sample API Requests
```bash
# Create a new project via MCP service
curl -X POST http://localhost:8001/tools/create_project \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Project", "description": "A test project"}'

# List all projects
curl -X GET http://localhost:8001/tools/list_projects

# Process natural language request via AI Agent
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a new task called Setup Development Environment"}'
```

## 🐛 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check if ports are already in use
lsof -i :8000 -i :8001 -i :5432 -i :8080

# Check Docker logs
docker-compose logs
```

**Database connection errors:**
```bash
# Verify PostgreSQL is running
docker-compose ps postgres

# Check database logs
docker-compose logs postgres

# Test database connection
docker-compose exec postgres psql -U aiagent -d aiagent_mcp -c "SELECT 1;"
```

**Gemini API errors:**
- Verify your API key is correct in `.env`
- Check API quota and billing status
- Ensure API key has proper permissions

**Container build failures:**
```bash
# Clean Docker cache and rebuild
docker system prune -f
docker-compose build --no-cache
```

### Getting Help

1. Check service logs: `docker-compose logs [service-name]`
2. Verify environment configuration in `.env`
3. Ensure all required ports are available
4. Check Docker and Docker Compose versions

## 📚 Learning Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [FastMCP Framework](https://github.com/pydantic/fastmcp)
- [Model Context Protocol Specification](https://modelcontextprotocol.io/)
- [Google Gemini API Documentation](https://ai.google.dev/docs)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## 🎓 Educational Focus

This project emphasizes:
- **KISS Principle**: Simple, understandable implementations
- **Separation of Concerns**: Clear service boundaries
- **Practical Learning**: Real-world patterns and practices
- **Incremental Development**: Build complexity gradually

Perfect for developers learning AI agent development, MCP services, and modern containerized architectures.

## 📄 License

This project is for educational purposes. Feel free to use and modify for learning.