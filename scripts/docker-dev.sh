#!/bin/bash
set -e

# Docker development helper script

# Detect docker compose command
if command -v docker-compose &> /dev/null; then
  DC="docker-compose"
elif docker compose version &> /dev/null; then
  DC="docker compose"
else
  echo "Error: Neither 'docker-compose' nor 'docker compose' is available. Please install Docker Compose."
  exit 1
fi

case "$1" in
  start)
    echo "Starting Docker services..."
    cd docker && $DC up -d
    echo "Services started. API: http://localhost:8000, Flower: http://localhost:5555"
    ;;
  
  stop)
    echo "Stopping Docker services..."
    cd docker && $DC down
    ;;
  
  restart)
    echo "Restarting Docker services..."
    cd docker && $DC restart
    ;;
  
  logs)
    cd docker && $DC logs -f ${2:-}
    ;;
  
  build)
    echo "Building Docker images..."
    cd docker && $DC build ${2:-}
    ;;
  
  shell)
    service=${2:-api}
    cd docker && $DC exec $service /bin/bash
    ;;
  
  db-shell)
    cd docker && $DC exec postgres psql -U postgres -d fastapi_k8_proto
    ;;
  
  redis-cli)
    cd docker && $DC exec redis redis-cli
    ;;
  
  test)
    echo "Running tests in Docker..."
    cd docker && $DC run --rm api pytest tests/ -v
    ;;
  
  clean)
    echo "Cleaning up Docker resources..."
    cd docker && $DC down -v
    docker system prune -f
    ;;
  
  *)
    echo "Usage: $0 {start|stop|restart|logs|build|shell|db-shell|redis-cli|test|clean} [service]"
    exit 1
    ;;
esac 