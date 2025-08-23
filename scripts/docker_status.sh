#!/bin/bash
# Docker container status monitoring script.
# Shows the health status of all services in the AI Agent MCP infrastructure.

echo "🐳 Docker Container Status"
echo "=========================="

# Check if docker-compose is running
if ! docker-compose ps >/dev/null 2>&1; then
    echo "❌ Docker Compose is not running or not found"
    echo "💡 Try: docker-compose up -d"
    exit 1
fi

# Show container status
echo ""
echo "📊 Container Overview:"
docker-compose ps

echo ""
echo "🏥 Health Check Status:"
echo "----------------------"

# Check each service health
services=("ai-agent" "mcp-service" "postgres" "pgadmin")

for service in "${services[@]}"; do
    health=$(docker-compose ps -q $service | xargs docker inspect --format='{{.State.Health.Status}}' 2>/dev/null)
    
    if [ -z "$health" ]; then
        status=$(docker-compose ps -q $service | xargs docker inspect --format='{{.State.Status}}' 2>/dev/null)
        if [ "$status" = "running" ]; then
            echo "🟡 $service: Running (no health check)"
        else
            echo "❌ $service: $status"
        fi
    else
        case $health in
            "healthy")
                echo "✅ $service: Healthy"
                ;;
            "unhealthy")
                echo "❌ $service: Unhealthy"
                ;;
            "starting")
                echo "🟡 $service: Starting..."
                ;;
            *)
                echo "🔍 $service: $health"
                ;;
        esac
    fi
done

echo ""
echo "🔗 Service URLs:"
echo "  AI Agent:   http://localhost:8000"
echo "  MCP Service: http://localhost:8001"
echo "  pgAdmin:    http://localhost:8080"

echo ""
echo "📋 Quick Commands:"
echo "  View logs:     docker-compose logs -f [service]"
echo "  Restart:       docker-compose restart [service]"
echo "  Stop all:      docker-compose down"
echo "  Rebuild:       docker-compose up --build -d"
echo "  Run tests:     python scripts/run_all_tests.py"
echo "  Health check:  python scripts/health_check.py"