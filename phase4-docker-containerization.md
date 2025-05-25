# Phase 4: Docker Containerization

## Overview
This phase containerizes the FastAPI application and Celery workers using Docker, creating a complete local development environment with Docker Compose.

## Prerequisites
- Phases 1-3 completed successfully
- Docker Desktop or Docker Engine installed
- Docker Compose installed
- All tests from previous phases passing

## Step 4.1: Create Dockerfiles

### AI Agent Instructions:
**Task**: Create Docker configurations for the API and worker services.

**Action 1**: Create the Docker directory structure:
```bash
mkdir -p docker
```

**Action 2**: Create `docker/Dockerfile.api` with the following content:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8000"]
```

**Action 3**: Create `docker/Dockerfile.worker` with the following content:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements/prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Run Celery worker
CMD ["celery", "-A", "app.workers.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
```

**Expected outcome**: Two Dockerfiles created for API and worker containers.

## Step 4.2: Create Docker Compose for Local Development

### AI Agent Instructions:
**Task**: Create a Docker Compose configuration for the complete application stack.

**Action**: Create `docker/docker-compose.yml` with the following content:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fastapi_k8_proto
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_SERVER=postgres
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=fastapi_k8_proto
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000"

  worker:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    environment:
      - POSTGRES_SERVER=postgres
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=fastapi_k8_proto
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      replicas: 2

  flower:
    build:
      context: ..
      dockerfile: docker/Dockerfile.worker
    ports:
      - "5555:5555"
    environment:
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      - redis
    command: celery -A app.workers.celery_app flower --port=5555

volumes:
  postgres_data:
```

**Expected outcome**: Docker Compose file created with all services configured.

## Step 4.3: Create Docker Ignore File

### AI Agent Instructions:
**Task**: Create a .dockerignore file to exclude unnecessary files from Docker builds.

**Action**: Create `.dockerignore` in the project root with the following content:
```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/
.venv
pip-log.txt
pip-delete-this-directory.txt
.pytest_cache/
.coverage
htmlcov/
.tox/
.mypy_cache/
.ruff_cache/

# Development
.git/
.gitignore
.env
.env.*
!.env.example
*.log
*.sqlite
*.db
test.db

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml
Dockerfile.*
!docker/Dockerfile.*

# Documentation
*.md
docs/
README.md

# Tests
tests/
pytest.ini
```

**Expected outcome**: .dockerignore file created to optimize Docker builds.

## Step 4.4: Create Environment Example File

### AI Agent Instructions:
**Task**: Create an example environment file for Docker deployment.

**Action**: Create `.env.example` in the project root with the following content:
```
# API Configuration
PROJECT_NAME="FastAPI K8s Worker Prototype"
VERSION="0.1.0"
API_V1_STR="/api/v1"
BACKEND_CORS_ORIGINS=["http://localhost:3000", "http://localhost:8000"]

# Database
POSTGRES_SERVER=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=fastapi_k8_proto

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# Celery
# These will be auto-generated from Redis settings
# CELERY_BROKER_URL=redis://redis:6379/0
# CELERY_RESULT_BACKEND=redis://redis:6379/0
```

**Expected outcome**: Example environment file created for easy setup.

## Step 4.5: Build and Test Docker Images

### AI Agent Instructions:
**Task**: Build Docker images and verify they work correctly.

**Action 1**: Stop any running local services to avoid port conflicts:
```bash
# Stop local services if running
docker stop postgres-dev redis-dev
docker rm postgres-dev redis-dev
```

**Action 2**: Build the Docker images:
```bash
cd docker
docker-compose build
```

**Action 3**: Start all services:
```bash
docker-compose up -d
```

**Action 4**: Check that all containers are running:
```bash
docker-compose ps
```

**Action 5**: View logs to ensure services started correctly:
```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs api
docker-compose logs worker
docker-compose logs postgres
docker-compose logs redis
```

**Expected outcome**: 
- All images built successfully
- All containers running without errors
- Services accessible on configured ports

## Step 4.6: Test Containerized Application

### AI Agent Instructions:
**Task**: Verify the containerized application works correctly.

**Action 1**: Test API health endpoints:
```bash
# Test health endpoint
curl http://localhost:8000/api/v1/health

# Test readiness
curl http://localhost:8000/api/v1/health/ready

# Test liveness
curl http://localhost:8000/api/v1/health/live
```

**Action 2**: Test job creation and processing:
```bash
# Create a job
curl -X POST http://localhost:8000/api/v1/jobs \
  -H "Content-Type: application/json" \
  -d '{"name": "Docker Test Job", "description": "Testing Docker setup"}'

# Check job status (replace 1 with actual job ID)
curl http://localhost:8000/api/v1/jobs/1/status

# List all jobs
curl http://localhost:8000/api/v1/jobs
```

**Action 3**: Check Flower monitoring:
```bash
# Open Flower in browser
open http://localhost:5555

# Or check via curl
curl http://localhost:5555/api/workers
```

**Action 4**: Verify worker scaling:
```bash
# Check running workers
docker-compose ps | grep worker

# Scale workers up
docker-compose up -d --scale worker=4

# Verify new workers
docker-compose ps | grep worker

# Scale workers down
docker-compose up -d --scale worker=2
```

**Expected outcome**:
- All API endpoints responding correctly
- Jobs being processed by workers
- Flower showing active workers
- Worker scaling functioning properly

## Step 4.7: Create Docker Development Scripts

### AI Agent Instructions:
**Task**: Create helper scripts for Docker development workflow.

**Action 1**: Create `scripts/docker-dev.sh`:
```bash
#!/bin/bash
set -e

# Docker development helper script

case "$1" in
  start)
    echo "Starting Docker services..."
    cd docker && docker-compose up -d
    echo "Services started. API: http://localhost:8000, Flower: http://localhost:5555"
    ;;
  
  stop)
    echo "Stopping Docker services..."
    cd docker && docker-compose down
    ;;
  
  restart)
    echo "Restarting Docker services..."
    cd docker && docker-compose restart
    ;;
  
  logs)
    cd docker && docker-compose logs -f ${2:-}
    ;;
  
  build)
    echo "Building Docker images..."
    cd docker && docker-compose build ${2:-}
    ;;
  
  shell)
    service=${2:-api}
    cd docker && docker-compose exec $service /bin/bash
    ;;
  
  db-shell)
    cd docker && docker-compose exec postgres psql -U postgres -d fastapi_k8_proto
    ;;
  
  redis-cli)
    cd docker && docker-compose exec redis redis-cli
    ;;
  
  test)
    echo "Running tests in Docker..."
    cd docker && docker-compose run --rm api pytest tests/ -v
    ;;
  
  clean)
    echo "Cleaning up Docker resources..."
    cd docker && docker-compose down -v
    docker system prune -f
    ;;
  
  *)
    echo "Usage: $0 {start|stop|restart|logs|build|shell|db-shell|redis-cli|test|clean} [service]"
    exit 1
    ;;
esac
```

**Action 2**: Make the script executable:
```bash
chmod +x scripts/docker-dev.sh
```

**Action 3**: Create `Makefile` in the project root:
```makefile
.PHONY: help docker-start docker-stop docker-logs docker-build docker-test docker-clean

help:
	@echo "Available commands:"
	@echo "  make docker-start    - Start all Docker services"
	@echo "  make docker-stop     - Stop all Docker services"
	@echo "  make docker-logs     - View Docker logs"
	@echo "  make docker-build    - Build Docker images"
	@echo "  make docker-test     - Run tests in Docker"
	@echo "  make docker-clean    - Clean up Docker resources"

docker-start:
	./scripts/docker-dev.sh start

docker-stop:
	./scripts/docker-dev.sh stop

docker-logs:
	./scripts/docker-dev.sh logs

docker-build:
	./scripts/docker-dev.sh build

docker-test:
	./scripts/docker-dev.sh test

docker-clean:
	./scripts/docker-dev.sh clean
```

**Expected outcome**: Helper scripts created for easier Docker management.

## Step 4.8: Create Docker-based Testing

### AI Agent Instructions:
**Task**: Set up testing within Docker containers.

**Action 1**: Create `docker/docker-compose.test.yml`:
```yaml
version: '3.8'

services:
  test-db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: test
      POSTGRES_PASSWORD: test
      POSTGRES_DB: test_db
    
  test-redis:
    image: redis:7-alpine

  test-runner:
    build:
      context: ..
      dockerfile: docker/Dockerfile.api
    environment:
      - POSTGRES_SERVER=test-db
      - POSTGRES_USER=test
      - POSTGRES_PASSWORD=test
      - POSTGRES_DB=test_db
      - REDIS_HOST=test-redis
      - REDIS_PORT=6379
      - TESTING=true
    depends_on:
      - test-db
      - test-redis
    command: >
      sh -c "alembic upgrade head &&
             pytest tests/ -v --cov=app --cov-report=html"
    volumes:
      - ../tests:/app/tests
      - ../htmlcov:/app/htmlcov
```

**Action 2**: Create test script `scripts/test-docker.sh`:
```bash
#!/bin/bash
set -e

echo "Running tests in Docker..."

# Run tests
docker-compose -f docker/docker-compose.test.yml up --build --abort-on-container-exit

# Copy coverage report
echo "Test coverage report available in htmlcov/index.html"

# Cleanup
docker-compose -f docker/docker-compose.test.yml down -v
```

**Action 3**: Make the test script executable:
```bash
chmod +x scripts/test-docker.sh
```

**Expected outcome**: Docker-based testing environment configured.

## Phase 4 Completion Checklist

- [ ] Dockerfiles created for API and worker
- [ ] Docker Compose configuration complete
- [ ] .dockerignore file created
- [ ] Environment example file created
- [ ] All Docker images built successfully
- [ ] All services running in containers
- [ ] API endpoints accessible
- [ ] Jobs processing correctly
- [ ] Worker scaling verified
- [ ] Helper scripts created and working
- [ ] Docker-based testing configured

## Troubleshooting

### Common Issues:

1. **Port already in use**:
   ```bash
   # Find process using port
   lsof -i :8000  # or :5432, :6379, :5555
   
   # Stop conflicting service or change port in docker-compose.yml
   ```

2. **Database connection errors**:
   - Check service names match in environment variables
   - Ensure health checks pass before dependent services start
   - Verify network connectivity between containers

3. **Build failures**:
   - Check Docker daemon is running
   - Ensure sufficient disk space
   - Verify all source files are present

4. **Permission errors**:
   - Ensure user ID 1000 exists in container
   - Check file permissions in mounted volumes
   - Run with appropriate user permissions

## Docker Commands Reference

```bash
# View running containers
docker-compose ps

# View container logs
docker-compose logs -f [service_name]

# Execute command in container
docker-compose exec [service_name] [command]

# Rebuild specific service
docker-compose build [service_name]

# Remove all containers and volumes
docker-compose down -v

# View resource usage
docker stats

# Inspect container
docker inspect [container_id]

# View network
docker network ls
docker network inspect docker_default
```

## Performance Optimization

1. **Multi-stage builds** (optional enhancement):
   ```dockerfile
   # Build stage
   FROM python:3.11-slim as builder
   # ... build dependencies ...
   
   # Runtime stage
   FROM python:3.11-slim
   # ... copy only necessary files ...
   ```

2. **Layer caching**:
   - Copy requirements first, then code
   - Use .dockerignore effectively
   - Minimize layer changes

3. **Resource limits** (add to docker-compose.yml):
   ```yaml
   services:
     api:
       deploy:
         resources:
           limits:
             cpus: '1.0'
             memory: 512M
   ```

## Next Steps
Once Phase 4 is complete and all services are running successfully in Docker, proceed to Phase 5 for Kubernetes deployment. 