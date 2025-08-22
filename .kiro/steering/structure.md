# Project Structure

## Repository Organization

This project follows a multi-service architecture with separate containers for different components.

### Root Level Files
- `.env`: Environment configuration (API keys, database credentials)
- `.gitignore`: Python-focused ignore patterns
- `README.md`: Comprehensive project documentation
- `docker-compose.yml`: Multi-service orchestration configuration

### Expected Service Structure
The project is designed to have separate services in their own directories:

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
└── docker-compose.yml      # Service orchestration
```

## Service Communication Pattern
- **AI Agent Service** (8000) ↔ HTTP ↔ **MCP Service** (8001)
- **MCP Service** (8001) ↔ **PostgreSQL** (5432)
- **pgAdmin** (8080) ↔ **PostgreSQL** (5432)

## Database Organization
- **Synchronous operations only**: Use sync database methods
- **Separate scripts**: Database creation and test data insertion
- **PostgreSQL focus**: All persistence through PostgreSQL

## Container Strategy
- **Separate containers**: Each service runs independently
- **Health checks**: All services include health monitoring
- **Auto-restart**: Services restart on failure
- **Environment isolation**: Each service has its own dependencies

## Development Workflow
1. **Database scripts**: Create initialization and test data scripts first
2. **MCP service**: Implement core MCP tools and HTTP endpoints
3. **AI agent service**: Build agent with MCP client integration
4. **Docker orchestration**: Configure multi-service deployment
5. **Testing**: Use virtual environment for Python test scripts

## Naming Conventions
- **Services**: kebab-case directory names (`ai-agent-service`, `mcp-service`)
- **Files**: snake_case for Python files (`main.py`, `test_data.sql`)
- **Containers**: Match service directory names
- **Database**: snake_case tables and columns