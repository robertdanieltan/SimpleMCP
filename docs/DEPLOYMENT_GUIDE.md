# AI Agent MCP Service - Complete Deployment Guide

This guide provides step-by-step instructions for deploying the AI Agent MCP Service Learning Project on any computer system.

## 📋 Prerequisites

### System Requirements
- **Operating System**: macOS, Linux, or Windows 10/11
- **RAM**: Minimum 4GB, Recommended 8GB+
- **Storage**: At least 2GB free space
- **Network**: Internet connection for downloading dependencies

### Required Software

#### 1. Docker & Docker Compose
**macOS:**
```bash
# Install Docker Desktop
# Download from: https://docs.docker.com/desktop/mac/install/
# Or using Homebrew:
brew install --cask docker
```

**Linux (Ubuntu/Debian):**
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect
```

**Windows:**
```powershell
# Install Docker Desktop for Windows
# Download from: https://docs.docker.com/desktop/windows/install/
# Requires WSL2 - follow Docker Desktop installation wizard
```

#### 2. Git
**macOS:**
```bash
# Git is usually pre-installed, or install via Homebrew:
brew install git
```

**Linux:**
```bash
sudo apt update
sudo apt install git
```

**Windows:**
```powershell
# Download Git for Windows from: https://git-scm.com/download/win
# Or using Chocolatey:
choco install git
```

#### 3. Python 3.8+ (Optional - for development scripts)
**macOS:**
```bash
brew install python3
```

**Linux:**
```bash
sudo apt update
sudo apt install python3 python3-pip
```

**Windows:**
```powershell
# Download from: https://www.python.org/downloads/
# Or using Chocolatey:
choco install python
```

### API Keys Required

#### Google Gemini API Key (Required)
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the generated API key (starts with `AIzaSy...`)
5. Keep this key secure - you'll need it for configuration

## 🚀 Deployment Steps

### Step 1: Clone the Repository

```bash
# Clone the project
git clone https://github.com/robertdanieltan/SimpleMCP.git
cd SimpleMCP

# Verify you have all files
ls -la
# Should show: README.md, docker-compose.yml, .env.example, etc.
```

### Step 2: Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit the .env file with your configuration
# Use your preferred text editor (nano, vim, code, etc.)
nano .env
```

**Required Configuration in `.env`:**
```env
# REQUIRED: Your Gemini API key
GEMINI_API_KEY=your_actual_gemini_api_key_here

# Database Configuration (change passwords for security)
POSTGRES_PASSWORD=your_secure_database_password
PGADMIN_DEFAULT_PASSWORD=your_admin_interface_password

# Optional: Change default email for pgAdmin
PGADMIN_DEFAULT_EMAIL=your_email@example.com
```

**Security Notes:**
- Replace `your_secure_database_password` with a strong password
- Replace `your_admin_interface_password` with a strong password
- Never commit the `.env` file to version control
- Keep your Gemini API key secure

### Step 3: Verify Docker Installation

```bash
# Check Docker is running
docker --version
docker-compose --version

# Test Docker (should show "Hello from Docker!")
docker run hello-world

# If Docker isn't running, start Docker Desktop or Docker service
```

### Step 4: Deploy the Services

```bash
# Start all services in background
docker-compose up -d

# Monitor startup (optional - press Ctrl+C to exit)
docker-compose logs -f

# Check service status
docker-compose ps
```

**Expected Output:**
```
NAME                COMMAND                  SERVICE             STATUS              PORTS
ai-agent            "uvicorn main:app --…"   ai-agent            running (healthy)   0.0.0.0:8000->8000/tcp
mcp-service         "uvicorn main:app --…"   mcp-service         running (healthy)   0.0.0.0:8001->8001/tcp
pgadmin             "/entrypoint.sh"         pgadmin             running (healthy)   0.0.0.0:8080->80/tcp
postgres            "docker-entrypoint.s…"   postgres            running (healthy)   0.0.0.0:5432->5432/tcp
```

### Step 5: Verify Deployment

#### Quick Health Check
```bash
# Test AI Agent Service
curl http://localhost:8000/health
# Expected: {"status": "healthy", "service": "ai-agent"}

# Test MCP Service
curl http://localhost:8001/health
# Expected: {"status": "healthy", "service": "mcp-service"}
```

#### Web Interface Access
Open your web browser and visit:
- **AI Agent API Documentation**: http://localhost:8000/docs
- **pgAdmin Database Interface**: http://localhost:8080
  - Email: From your `.env` file (`PGADMIN_DEFAULT_EMAIL`)
  - Password: From your `.env` file (`PGADMIN_DEFAULT_PASSWORD`)

#### Comprehensive Testing (if Python is installed)
```bash
# Install Python dependencies for testing
pip install requests psycopg2-binary

# Run comprehensive health checks
python scripts/health_check.py

# Run all development tests
python scripts/run_all_tests.py
```

## 🔧 Configuration Options

### Port Configuration
If you need to change ports (due to conflicts), edit `docker-compose.yml`:

```yaml
services:
  ai-agent:
    ports:
      - "9000:8000"  # Change 8000 to 9000 for external access
  
  mcp-service:
    ports:
      - "9001:8001"  # Change 8001 to 9001 for external access
```

Then update your `.env` file accordingly.

### Database Configuration
For production use, consider:
- Using external PostgreSQL database
- Setting up database backups
- Configuring connection pooling

### Resource Limits
For resource-constrained systems, add to `docker-compose.yml`:

```yaml
services:
  ai-agent:
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use
**Error**: `Port 8000 is already allocated`

**Solution**:
```bash
# Find what's using the port
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or change ports in docker-compose.yml
```

#### 2. Docker Not Running
**Error**: `Cannot connect to the Docker daemon`

**Solution**:
```bash
# macOS: Start Docker Desktop application
# Linux: Start Docker service
sudo systemctl start docker

# Windows: Start Docker Desktop application
```

#### 3. Services Won't Start
**Error**: Containers exit immediately

**Solution**:
```bash
# Check logs for specific errors
docker-compose logs

# Common fixes:
# 1. Verify .env file has correct API key
# 2. Check for port conflicts
# 3. Ensure Docker has enough resources
# 4. Try rebuilding containers
docker-compose down
docker-compose up --build
```

#### 4. Database Connection Errors
**Error**: `Connection to database failed`

**Solution**:
```bash
# Wait for database to fully start (can take 30-60 seconds)
docker-compose logs postgres

# Check database is healthy
docker-compose ps postgres

# Reset database if needed
docker-compose down -v
docker-compose up postgres
# Wait for healthy status, then start other services
```

#### 5. Gemini API Errors
**Error**: `Invalid API key` or `Quota exceeded`

**Solution**:
1. Verify API key is correct in `.env`
2. Check API key is activated at [Google AI Studio](https://makersuite.google.com/app/apikey)
3. Verify billing is enabled if required
4. Check API quotas and limits

### Platform-Specific Issues

#### macOS
```bash
# If you get permission errors:
sudo chown -R $(whoami) /usr/local/lib/docker

# If ports are blocked by AirPlay:
# System Preferences > Sharing > AirPlay Receiver > Off
```

#### Linux
```bash
# If Docker commands require sudo:
sudo usermod -aG docker $USER
# Log out and back in

# If firewall blocks ports:
sudo ufw allow 8000
sudo ufw allow 8001
sudo ufw allow 5432
sudo ufw allow 8080
```

#### Windows
```powershell
# If WSL2 integration issues:
# Docker Desktop > Settings > Resources > WSL Integration
# Enable integration with your WSL2 distro

# If antivirus blocks Docker:
# Add Docker installation directory to antivirus exclusions
```

## 🔄 Management Commands

### Daily Operations
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart specific service
docker-compose restart ai-agent

# View logs
docker-compose logs -f [service-name]

# Check status
docker-compose ps
```

### Maintenance
```bash
# Update containers (after code changes)
docker-compose up --build

# Clean up old containers and images
docker system prune -f

# Backup database
docker-compose exec postgres pg_dump -U postgres aiagent_mcp > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres aiagent_mcp < backup.sql
```

### Development
```bash
# Access container shell
docker-compose exec ai-agent bash
docker-compose exec mcp-service bash

# Run tests
python scripts/run_all_tests.py

# Monitor resource usage
docker stats
```

## 🚀 Production Deployment Considerations

### Security
- [ ] Change all default passwords
- [ ] Use environment-specific `.env` files
- [ ] Set up HTTPS/TLS certificates
- [ ] Configure firewall rules
- [ ] Use Docker secrets for sensitive data
- [ ] Regular security updates

### Performance
- [ ] Configure resource limits
- [ ] Set up database connection pooling
- [ ] Enable database query optimization
- [ ] Configure log rotation
- [ ] Monitor resource usage

### Reliability
- [ ] Set up health monitoring
- [ ] Configure automatic restarts
- [ ] Set up database backups
- [ ] Configure log aggregation
- [ ] Set up alerting

### Scaling
- [ ] Use Docker Swarm or Kubernetes
- [ ] Set up load balancing
- [ ] Configure horizontal scaling
- [ ] Use external database service
- [ ] Set up caching layer

## 📚 Next Steps

After successful deployment:

1. **Explore the APIs**:
   - Visit http://localhost:8000/docs for AI Agent API
   - Test endpoints using the interactive documentation

2. **Try the System**:
   ```bash
   # Test AI Agent with natural language
   curl -X POST http://localhost:8000/agent/process \
     -H "Content-Type: application/json" \
     -d '{"message": "Create a project called My First Project"}'
   ```

3. **Learn the Architecture**:
   - Read `MCP_BEGINNER_GUIDE.md` for conceptual understanding
   - Review `docs/DEVELOPMENT_GUIDE.md` for development details

4. **Customize and Extend**:
   - Add new MCP tools in `mcp-service/app/tools/`
   - Modify AI behavior in `ai-agent-service/app/agent/`
   - Extend database schema in `database/init.sql`

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs**: `docker-compose logs [service-name]`
2. **Review troubleshooting**: This guide's troubleshooting section
3. **Run diagnostics**: `python scripts/health_check.py`
4. **Check documentation**: `README.md` and other docs in `docs/`
5. **Verify environment**: Ensure `.env` file is correctly configured

## 📄 Summary

This deployment guide provides everything needed to deploy the AI Agent MCP Service on any system. The deployment includes:

- **AI Agent Service**: Natural language interface using Gemini API
- **MCP Service**: Task and project management tools
- **PostgreSQL Database**: Persistent data storage
- **pgAdmin**: Database administration interface
- **Comprehensive Testing**: Health checks and validation scripts

**Deployment Time**: ~10-15 minutes for first-time setup
**System Requirements**: Docker, 4GB RAM, 2GB storage
**API Key Required**: Google Gemini API key

---

**Happy Deploying! 🎉**

For questions or issues, refer to the troubleshooting section or check the project documentation.