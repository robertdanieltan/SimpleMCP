# Design Document

## Overview

The AI Agent MCP Service Learning Project infrastructure follows a microservices architecture with four containerized services orchestrated through Docker Compose. The design emphasizes simplicity, clear separation of concerns, and educational value while providing a robust foundation for AI agent and MCP service development.

## Architecture

### High-Level Architecture

```mermaid
graph TB
    subgraph "Docker Compose Network"
        subgraph "AI Agent Service (Port 8000)"
            A[FastAPI App]
            A1[Agent Logic]
            A2[MCP HTTP Client]
        end
        
        subgraph "MCP Service (Port 8001)"
            M[FastMCP App]
            M1[Tool Implementations]
            M2[Database Operations]
        end
        
        subgraph "Database Layer"
            P[(PostgreSQL:5432)]
            PA[pgAdmin:8080]
        end
    end
    
    A2 -->|HTTP REST| M
    M2 -->|SQL| P
    PA -->|Admin| P
    
    subgraph "External"
        G[Gemini API]
        U[User/Developer]
    end
    
    A1 -->|API Calls| G
    U -->|HTTP| A
    U -->|Web UI| PA
```

### Service Communication Flow

1. **User Request** → AI Agent Service (FastAPI)
2. **AI Agent** → Gemini API for natural language processing
3. **AI Agent** → MCP Service via HTTP REST calls
4. **MCP Service** → PostgreSQL for data operations
5. **Response** flows back through the chain

## Components and Interfaces

### AI Agent Service (Port 8000)

**Technology Stack:**
- FastAPI framework
- Gemini API integration
- HTTP client for MCP communication

**Directory Structure:**
```
ai-agent-service/
├── main.py                 # FastAPI application entry
├── requirements.txt        # Dependencies
├── Dockerfile             # Container config
└── app/
    ├── __init__.py
    ├── agent/
    │   ├── __init__.py
    │   ├── core.py         # Main agent logic
    │   └── gemini_client.py # Gemini API wrapper
    ├── mcp_client/
    │   ├── __init__.py
    │   └── http_client.py  # MCP service HTTP client
    └── models/
        ├── __init__.py
        └── schemas.py      # Pydantic models
```

**Key Endpoints:**
- `GET /health` - Health check
- `GET /agent/status` - Agent status
- `POST /agent/process` - Process user requests
- `POST /agent/task` - Task management operations

### MCP Service (Port 8001)

**Technology Stack:**
- FastMCP framework (built on FastAPI)
- PostgreSQL driver (psycopg2)
- Synchronous database operations

**Directory Structure:**
```
mcp-service/
├── main.py                 # FastMCP application entry
├── requirements.txt        # Dependencies
├── Dockerfile             # Container config
└── app/
    ├── __init__.py
    ├── tools/
    │   ├── __init__.py
    │   ├── task_tools.py   # Task management tools
    │   └── project_tools.py # Project management tools
    ├── database/
    │   ├── __init__.py
    │   ├── connection.py   # Database connection
    │   └── operations.py   # CRUD operations
    └── models/
        ├── __init__.py
        └── schemas.py      # Database models
```

**MCP Tools:**
- `create_task` - Create new tasks
- `list_tasks` - Retrieve tasks with filtering
- `update_task` - Modify existing tasks
- `delete_task` - Remove tasks
- `create_project` - Create new projects
- `list_projects` - Retrieve projects

### Database Service (PostgreSQL)

**Schema Design:**
```sql
-- Projects table
CREATE TABLE projects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tasks table
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'medium',
    assigned_to VARCHAR(100),
    due_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_projects_status ON projects(status);
```

**Directory Structure:**
```
database/
├── init.sql               # Schema creation
├── test_data.sql          # Sample data insertion
└── schema/
    ├── tables.sql         # Table definitions
    └── indexes.sql        # Index definitions
```

### pgAdmin Service (Port 8080)

**Configuration:**
- Pre-configured server connection to PostgreSQL
- Default admin credentials from environment
- Persistent volume for configuration

## Data Models

### Core Entities

**Project Model:**
```python
class Project(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Task Model:**
```python
class Task(BaseModel):
    id: Optional[int] = None
    project_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    status: str = "pending"
    priority: str = "medium"
    assigned_to: Optional[str] = None
    due_date: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

### API Response Models

**Standard Response:**
```python
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None
```

## Error Handling

### Service-Level Error Handling

**AI Agent Service:**
- Gemini API failures → Graceful degradation with error messages
- MCP service unavailable → Retry logic with exponential backoff
- Invalid requests → Structured error responses

**MCP Service:**
- Database connection failures → Connection retry with circuit breaker
- Invalid tool parameters → Validation error responses
- SQL errors → Sanitized error messages

**Database Service:**
- Connection timeouts → Automatic reconnection
- Schema validation → Migration error handling
- Data integrity → Constraint violation messages

### Global Error Response Format

```python
{
    "success": false,
    "message": "Human-readable error description",
    "error": "ERROR_CODE",
    "details": {
        "service": "service-name",
        "timestamp": "2024-01-01T00:00:00Z",
        "request_id": "uuid"
    }
}
```

## Testing Strategy

### Unit Testing

**AI Agent Service:**
- Mock Gemini API responses
- Test MCP client HTTP calls
- Validate request/response models

**MCP Service:**
- Mock database operations
- Test tool implementations
- Validate MCP protocol compliance

### Integration Testing

**Service Communication:**
- End-to-end HTTP request flows
- Database transaction testing
- Error propagation testing

**Docker Environment:**
- Container startup sequences
- Service discovery testing
- Health check validation

### Test Data Strategy

**Database Test Data:**
```sql
-- Sample projects
INSERT INTO projects (name, description, status) VALUES
('Learning Project', 'AI Agent MCP Service tutorial', 'active'),
('Demo Tasks', 'Sample task management', 'active');

-- Sample tasks
INSERT INTO tasks (project_id, title, description, status, priority) VALUES
(1, 'Setup Infrastructure', 'Create Docker containers and database', 'completed', 'high'),
(1, 'Implement AI Agent', 'Build FastAPI agent service', 'in_progress', 'high'),
(2, 'Create Sample Task', 'Demonstrate task creation', 'pending', 'medium');
```

### Environment Configuration

**Docker Compose Configuration:**
```yaml
version: '3.8'
services:
  ai-agent:
    build: ./ai-agent-service
    ports:
      - "8000:8000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - MCP_SERVICE_URL=http://mcp-service:8001
    depends_on:
      - mcp-service
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  mcp-service:
    build: ./mcp-service
    ports:
      - "8001:8001"
    environment:
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - postgres
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:16
    environment:
      - POSTGRES_USER=${POSTGRES_USER}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=${POSTGRES_DB}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./database/test_data.sql:/docker-entrypoint-initdb.d/02-test-data.sql
    restart: unless-stopped

  pgadmin:
    image: dpage/pgadmin4
    environment:
      - PGADMIN_DEFAULT_EMAIL=${PGADMIN_DEFAULT_EMAIL}
      - PGADMIN_DEFAULT_PASSWORD=${PGADMIN_DEFAULT_PASSWORD}
    ports:
      - "8080:80"
    depends_on:
      - postgres
    restart: unless-stopped

volumes:
  postgres_data:
```

**Environment Variables (.env.example):**
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

This design provides a solid foundation for learning AI agent development while maintaining simplicity and clear separation of concerns. Each service has well-defined responsibilities, and the architecture supports both educational exploration and practical development.