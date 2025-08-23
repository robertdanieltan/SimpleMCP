# Team Setup Guide - AI Agent MCP Service Project

## 🎯 For New Team Members

Welcome to the AI Agent MCP Service Learning Project! This guide will get you up and running quickly.

### 📋 Prerequisites
- Docker & Docker Compose installed
- Git installed
- Google account (for Gemini API key)

### 🚀 Quick Setup (15 minutes)

#### 1. Clone the Repository
```bash
git clone https://github.com/robertdanieltan/SimpleMCP.git
cd SimpleMCP
```

#### 2. Get Your Gemini API Key
1. Visit: https://makersuite.google.com/app/apikey
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key (starts with `AIzaSy...`)

#### 3. Configure Environment
```bash
# Copy the environment template
cp .env.example .env

# Edit .env file and add your API key
# Replace 'your_gemini_api_key_here' with your actual key
```

**Important**: Never commit your `.env` file! It contains your personal API key.

#### 4. Start the Services
```bash
# Start all services
docker-compose up -d

# Verify everything is working
python scripts/health_check.py
```

#### 5. Access the Services
- **AI Agent API**: http://localhost:8000/docs
- **MCP Service**: http://localhost:8001
- **Database Admin**: http://localhost:8080
  - Email: admin@example.com
  - Password: admin123

### 🧪 Test It Works
```bash
# Try the AI agent
curl -X POST http://localhost:8000/agent/process \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a project called Team Project"}'
```

### 📚 Learning Resources
- **Beginner's Guide**: `MCP_BEGINNER_GUIDE.md`
- **Deployment Guide**: `docs/DEPLOYMENT_GUIDE.md`
- **Development Guide**: `docs/DEVELOPMENT_GUIDE.md`

### 🤝 Team Workflow

#### Daily Development
```bash
# Pull latest changes
git pull origin main

# Start services
docker-compose up -d

# Make your changes...

# Test your changes
python scripts/run_all_tests.py

# Commit and push
git add .
git commit -m "Your descriptive message"
git push origin main
```

#### Working on Features
```bash
# Create a feature branch
git checkout -b feature/your-feature-name

# Make your changes...

# Push your branch
git push origin feature/your-feature-name

# Create a Pull Request on GitHub
```

### 🔧 Common Commands
```bash
# View service logs
docker-compose logs -f [service-name]

# Restart a service
docker-compose restart [service-name]

# Stop all services
docker-compose down

# Clean restart
docker-compose down && docker-compose up -d
```

### 🐛 Troubleshooting
- **Port conflicts**: Change ports in `docker-compose.yml`
- **API key issues**: Verify your key in `.env` file
- **Docker issues**: Restart Docker Desktop
- **Database issues**: Try `docker-compose down -v && docker-compose up -d`

### 📞 Getting Help
- Check the comprehensive guides in `docs/`
- Open an issue on GitHub
- Ask team members in your communication channel

---

**Happy coding! 🚀**