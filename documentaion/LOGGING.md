# FastAPI K8s Prototype - Unified Logging System

This document describes the unified logging system implemented for the FastAPI K8s prototype application. The system provides consistent logging patterns across all containers with proper sanitization, structured JSON output, and centralized log management.

## System Overview and Architecture

### Core Components

- **Central Configuration**: `app/core/logging_config.py` - Advanced logging configuration with JSON formatting and sanitization
- **Logger Utility**: `app/core/logger.py` - Convenience helper that guarantees proper logging initialization
- **Shared Log Directory**: `logs/` - Docker volume-mounted directory accessible by all services
- **Environment Configuration**: Environment variables in `.env` for flexible configuration

### Services Integration

All containerized services use the unified logging system:
- **API Service** (`api`): FastAPI application logs
- **Worker Service** (`worker`): Celery worker logs  
- **Flower Service** (`flower`): Celery monitoring logs
- **Test Runner** (`test-runner`): Test execution logs

### Log Flow Architecture

```
Application Code → Logger Utility → Logging Config → Handlers → Outputs
     ↓                    ↓               ↓            ↓         ↓
get_logger(__name__) → Sanitization → JSON Format → File + Console
```

## Configuration Options

### Environment Variables

All logging configuration is controlled via environment variables in `.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_DIR` | `./logs` | Directory for log files |
| `LOG_LEVEL` | `INFO` | Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) |
| `LOG_ROTATION_SIZE` | `10485760` | Log file size before rotation (10MB) |
| `LOG_BACKUP_COUNT` | `5` | Number of backup log files to keep |
| `LOG_SERVICE_HOST` | `localhost` | Service host for log correlation |
| `LOG_SERVICE_PORT` | `8765` | Service port for log correlation |
| `LOG_BUFFER_SIZE` | `1000` | Log buffer size for performance |

### Configuration in `app/core/config.py`

```python
class Settings(BaseSettings):
    # Logging Configuration
    LOG_DIR: str = "./logs"
    LOG_LEVEL: str = "INFO"
    LOG_ROTATION_SIZE: int = 10485760  # 10MB
    LOG_BACKUP_COUNT: int = 5
    LOG_SERVICE_HOST: str = "localhost"
    LOG_SERVICE_PORT: int = 8765
    LOG_BUFFER_SIZE: int = 1000
```

## Usage Examples

### Basic Logger Usage

```python
from app.core.logger import get_logger

logger = get_logger(__name__)

# Basic logging
logger.info("User authentication successful")
logger.warning("Rate limit approaching")
logger.error("Database connection failed")
```

### Structured Logging with Context

```python
# Add context information
logger.info("User logged in", extra={
    "user_id": "12345",
    "component": "auth_service",
    "action": "login"
})

# Error logging with exception info
try:
    # some operation
    pass
except Exception as e:
    logger.error("Operation failed", exc_info=True, extra={
        "component": "payment_service",
        "operation": "process_payment"
    })
```

### Service-Specific Logging

```python
# API endpoint logging
logger = get_logger("app.api.endpoints.users")
logger.info("GET /users endpoint called", extra={
    "endpoint": "/users",
    "method": "GET",
    "component": "api"
})

# Worker task logging
logger = get_logger("app.workers.email_tasks")
logger.info("Email task started", extra={
    "task_id": "email_123",
    "component": "worker"
})
```

## Log Levels and When to Use Them

### DEBUG
- **Use for**: Detailed diagnostic information
- **Examples**: Variable values, function entry/exit, detailed flow tracing
- **Note**: Only visible when LOG_LEVEL=DEBUG

```python
logger.debug("Processing user data", extra={"user_count": len(users)})
```

### INFO
- **Use for**: General information about application flow
- **Examples**: Successful operations, key business events, service start/stop

```python
logger.info("User registration completed", extra={"user_id": user.id})
```

### WARNING
- **Use for**: Recoverable errors or concerning situations
- **Examples**: Deprecated API usage, fallback mechanisms triggered, high resource usage

```python
logger.warning("Database connection slow", extra={"response_time": 5.2})
```

### ERROR
- **Use for**: Error conditions that don't stop the application
- **Examples**: Failed external API calls, data validation errors, recoverable exceptions

```python
logger.error("Payment processing failed", extra={"payment_id": payment.id})
```

### CRITICAL
- **Use for**: Serious errors that may cause application failure
- **Examples**: Database unavailable, critical service failures, security breaches

```python
logger.critical("Database connection lost", extra={"service": "api"})
```

## Sensitive Data Handling

### Automatic Sanitization

The logging system automatically redacts sensitive information using the `SanitizingFilter`:

**Sensitive Patterns Detected:**
- Email addresses: `user@example.com` → `[REDACTED_EMAIL]`
- Passwords: `password=secret123` → `password=[REDACTED_PASSWORD]`
- API keys: `api_key=abc123` → `api_key=[REDACTED_API_KEY]`
- Tokens: `token=xyz789` → `token=[REDACTED_TOKEN]`
- Credit card numbers: `4111111111111111` → `[REDACTED_CC]`
- Phone numbers: `+1-555-123-4567` → `[REDACTED_PHONE]`

### Best Practices for Sensitive Data

```python
# BAD: Direct logging of user data
logger.info(f"User details: {user_dict}")

# GOOD: Log non-sensitive identifiers only
logger.info("User updated", extra={"user_id": user.id, "action": "profile_update"})

# GOOD: Trust the sanitization filter for complex objects
logger.info("Processing request", extra={"request_data": request_dict})  # Auto-sanitized
```

### Manual Data Sanitization

For extra security, manually sanitize before logging:

```python
def safe_log_user(user_data):
    safe_data = {
        "user_id": user_data.get("id"),
        "username": user_data.get("username"),
        "created_at": user_data.get("created_at")
        # Exclude email, password, etc.
    }
    logger.info("User processed", extra=safe_data)
```

## Log Output Format

### JSON Structure

All logs are output as structured JSON with consistent fields:

```json
{
  "timestamp": "2025-01-20T10:30:45.123456Z",
  "level": "INFO",
  "name": "app.api.endpoints.users",
  "message": "User registration completed",
  "source": "app.api.endpoints.users",
  "component": "api",
  "user_id": "12345",
  "service_host": "localhost",
  "service_port": 8765
}
```

### Mandatory Fields

| Field | Description | Example |
|-------|-------------|---------|
| `timestamp` | ISO-8601 UTC timestamp | `2025-01-20T10:30:45.123456Z` |
| `level` | Log level | `INFO`, `ERROR`, `DEBUG` |
| `name` | Logger name | `app.api.endpoints.users` |
| `message` | Human-readable message | `User registration completed` |
| `source` | Source identifier | Same as `name` unless overridden |

### Optional Fields

| Field | Description | Example |
|-------|-------------|---------|
| `component` | Service/subsystem identifier | `api`, `worker`, `auth_service` |
| `service_host` | Service host | `localhost`, `api-service` |
| `service_port` | Service port | `8000`, `5555` |
| Any extra data | Custom context fields | `user_id`, `endpoint`, `task_id` |

## Viewing and Monitoring Logs

### Local Development

**View live logs from all services:**
```bash
docker-compose -f docker/docker-compose.yml logs -f
```

**View specific service logs:**
```bash
docker-compose -f docker/docker-compose.yml logs -f api
docker-compose -f docker/docker-compose.yml logs -f worker
```

**Monitor the unified log file:**
```bash
tail -f logs/combined.log | jq .
```

### Log File Locations

- **Unified log file**: `logs/combined.log`
- **Rotated files**: `logs/combined.log.1`, `logs/combined.log.2`, etc.
- **Service-specific filtering**: Use `jq` to filter by component

```bash
# Filter API logs only
tail -f logs/combined.log | jq 'select(.component == "api")'

# Filter by log level
tail -f logs/combined.log | jq 'select(.level == "ERROR")'

# Filter by time range and service
tail -f logs/combined.log | jq 'select(.timestamp > "2025-01-20T10:00:00" and .component == "worker")'
```

## Troubleshooting Guide

### Common Issues

#### 1. No Log Files Created
**Symptoms**: `logs/combined.log` doesn't exist after starting services

**Solutions**:
- Check Docker volume mounting: `docker-compose -f docker/docker-compose.yml config`
- Verify logs directory exists: `ls -la logs/`
- Check container permissions: `docker exec <container> ls -la /app/logs/`

#### 2. Logs Not Appearing in File
**Symptoms**: Console logs work but file logs missing

**Solutions**:
- Check LOG_DIR environment variable
- Verify write permissions in logs directory
- Check log level configuration (file might have different level)

#### 3. Sensitive Data Not Redacted
**Symptoms**: Passwords or emails appearing in logs

**Solutions**:
- Verify SanitizingFilter is properly configured
- Check custom patterns in `logging_config.py`
- Test sanitization with known patterns

#### 4. Performance Issues
**Symptoms**: High log volume causing slowdowns

**Solutions**:
- Increase LOG_BUFFER_SIZE
- Reduce LOG_LEVEL (e.g., WARNING instead of INFO)
- Increase LOG_ROTATION_SIZE
- Monitor disk space usage

#### 5. Docker Volume Issues
**Symptoms**: Logs not persisting between container restarts

**Solutions**:
```bash
# Check volume mounting
docker-compose -f docker/docker-compose.yml config

# Recreate volumes if needed
docker-compose -f docker/docker-compose.yml down -v
docker-compose -f docker/docker-compose.yml up
```

### Debugging Steps

1. **Check Configuration**:
   ```python
   from app.core.config import get_settings
   settings = get_settings()
   print(f"LOG_DIR: {settings.LOG_DIR}")
   print(f"LOG_LEVEL: {settings.LOG_LEVEL}")
   ```

2. **Test Logger Directly**:
   ```python
   from app.core.logger import get_logger
   logger = get_logger("test")
   logger.info("Test message", extra={"test": True})
   ```

3. **Verify File Creation**:
   ```bash
   ls -la logs/
   cat logs/combined.log | tail -5
   ```

## Performance Considerations

### Log Volume Management

- **Buffer Size**: Configured via `LOG_BUFFER_SIZE` (default 1000)
- **Rotation**: Files rotate at `LOG_ROTATION_SIZE` (default 10MB)
- **Retention**: Keep `LOG_BACKUP_COUNT` files (default 5)

### Performance Best Practices

1. **Use Appropriate Log Levels**:
   - Production: INFO or higher
   - Development: DEBUG for troubleshooting only
   - Staging: INFO with selective DEBUG

2. **Efficient Extra Data**:
   ```python
   # GOOD: Simple values
   logger.info("Operation completed", extra={"duration": 0.5, "count": 100})
   
   # AVOID: Large objects
   logger.info("Large object", extra={"huge_dict": massive_data_structure})
   ```

3. **Lazy Evaluation**:
   ```python
   # GOOD: Only format if level is enabled
   if logger.isEnabledFor(logging.DEBUG):
       logger.debug("Complex data: %s", expensive_operation())
   
   # BETTER: Use lazy formatting
   logger.debug("Complex data: %s", lambda: expensive_operation())
   ```

### Monitoring Performance Impact

- Monitor disk I/O during high log volume
- Use log sampling for very high-volume scenarios
- Consider async logging for performance-critical paths

## Integration with External Systems

### Log Aggregation

The unified JSON format makes integration with log aggregation systems straightforward:

**ELK Stack**:
```yaml
# Filebeat configuration
filebeat.inputs:
- type: log
  paths:
    - "/app/logs/combined.log"
  json.keys_under_root: true
```

**Grafana Loki**:
```yaml
# Promtail configuration  
clients:
  - url: http://loki:3100/loki/api/v1/push
static_configs:
  - targets:
      - localhost
    labels:
      job: fastapi-k8-proto
      __path__: /app/logs/combined.log
```

### Kubernetes Integration

For Kubernetes deployment, use log forwarding:

```yaml
# Fluent-bit sidecar
- name: fluent-bit
  image: fluent/fluent-bit:latest
  volumeMounts:
  - name: logs-volume
    mountPath: /app/logs
```

## Security Considerations

1. **Log File Permissions**: Ensure log files are readable only by authorized users
2. **Sensitive Data**: Trust the sanitization but verify with testing
3. **Log Retention**: Implement log retention policies for compliance
4. **Access Control**: Restrict access to log aggregation systems

## Maintenance and Operations

### Regular Tasks

1. **Monitor disk usage**: `df -h logs/`
2. **Check log rotation**: `ls -la logs/combined.log*`
3. **Verify sanitization**: Regular audit of log content
4. **Performance monitoring**: Watch for log-related performance impact

### Backup and Archival

- Consider archiving rotated log files to long-term storage
- Implement retention policies based on compliance requirements
- Monitor backup systems for log data integrity

This unified logging system provides comprehensive observability while maintaining security and performance across the entire FastAPI K8s prototype application stack. 