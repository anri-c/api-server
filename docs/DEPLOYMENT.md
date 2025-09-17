# Deployment Guide

This guide covers deploying the API server to various environments including local production, Docker, and cloud platforms.

## Prerequisites

- Python 3.13+
- PostgreSQL database
- LINE Developer Account
- Domain name (for production)
- SSL certificate (for production)

## Environment Configuration

### Production Environment Variables

Create a production `.env` file with the following variables:

```bash
# Application
DEBUG=false
LOG_LEVEL=WARNING
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://username:password@host:port/database_name

# LINE OAuth
LINE_CLIENT_ID=your_production_line_client_id
LINE_CLIENT_SECRET=your_production_line_client_secret
LINE_REDIRECT_URI=https://yourdomain.com/auth/line/callback

# JWT Configuration
JWT_SECRET=your_very_secure_jwt_secret_key_here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# Security (optional)
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Local Production Deployment

### 1. Prepare the Environment

```bash
# Clone the repository
git clone <repository-url>
cd api-server

# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync --no-dev

# Create production .env file
cp .env.example .env
# Edit .env with production values
```

### 2. Database Setup

```bash
# Create PostgreSQL database
createdb api_server_prod

# Run migrations
./scripts/db-migrate.sh

# Optional: Seed with initial data
./scripts/db-seed.sh
```

### 3. Run the Application

```bash
# Using uvicorn directly
uv run uvicorn api_server.main:app --host 0.0.0.0 --port 8000

# Or using gunicorn for better production performance
uv run gunicorn api_server.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### 4. Process Management with systemd

Create a systemd service file `/etc/systemd/system/api-server.service`:

```ini
[Unit]
Description=API Server
After=network.target

[Service]
Type=exec
User=api-server
Group=api-server
WorkingDirectory=/opt/api-server
Environment=PATH=/opt/api-server/.venv/bin
ExecStart=/opt/api-server/.venv/bin/uvicorn api_server.main:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable api-server
sudo systemctl start api-server
sudo systemctl status api-server
```

## Docker Deployment

### 1. Create Dockerfile

```dockerfile
FROM python:3.13-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set work directory
WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --no-dev

# Copy application code
COPY src/ ./src/
COPY scripts/ ./scripts/

# Change ownership to app user
RUN chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uv", "run", "uvicorn", "api_server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/api_server
      - DEBUG=false
      - LOG_LEVEL=INFO
    env_file:
      - .env
    depends_on:
      - db
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=api_server
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
    restart: unless-stopped

volumes:
  postgres_data:
```

### 3. Create nginx.conf

```nginx
events {
    worker_connections 1024;
}

http {
    upstream api_server {
        server api:8000;
    }

    server {
        listen 80;
        server_name yourdomain.com www.yourdomain.com;
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name yourdomain.com www.yourdomain.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;

        location / {
            proxy_pass http://api_server;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### 4. Deploy with Docker Compose

```bash
# Build and start services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Run database migrations
docker-compose exec api ./scripts/db-migrate.sh

# Scale the API service
docker-compose up -d --scale api=3
```

## Cloud Deployment

### AWS Deployment with ECS

#### 1. Create ECR Repository

```bash
# Create ECR repository
aws ecr create-repository --repository-name api-server

# Get login token
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push image
docker build -t api-server .
docker tag api-server:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/api-server:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/api-server:latest
```

#### 2. Create ECS Task Definition

```json
{
  "family": "api-server",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "256",
  "memory": "512",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "api-server",
      "image": "<account-id>.dkr.ecr.us-east-1.amazonaws.com/api-server:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "DEBUG",
          "value": "false"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:api-server/database-url"
        },
        {
          "name": "JWT_SECRET",
          "valueFrom": "arn:aws:secretsmanager:us-east-1:<account-id>:secret:api-server/jwt-secret"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/api-server",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run Deployment

#### 1. Prepare for Cloud Run

```bash
# Install Google Cloud SDK
# https://cloud.google.com/sdk/docs/install

# Authenticate
gcloud auth login
gcloud config set project your-project-id

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

#### 2. Create cloudbuild.yaml

```yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/api-server', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/api-server']
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'api-server'
      - '--image'
      - 'gcr.io/$PROJECT_ID/api-server'
      - '--region'
      - 'us-central1'
      - '--platform'
      - 'managed'
      - '--allow-unauthenticated'
```

#### 3. Deploy to Cloud Run

```bash
# Deploy using Cloud Build
gcloud builds submit --config cloudbuild.yaml

# Or deploy directly
gcloud run deploy api-server \
  --image gcr.io/your-project-id/api-server \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars DEBUG=false \
  --set-env-vars LOG_LEVEL=INFO
```

### Heroku Deployment

#### 1. Prepare for Heroku

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login to Heroku
heroku login

# Create Heroku app
heroku create your-api-server-app
```

#### 2. Create Procfile

```
web: uv run uvicorn api_server.main:app --host 0.0.0.0 --port $PORT
```

#### 3. Configure Environment Variables

```bash
# Set environment variables
heroku config:set DEBUG=false
heroku config:set LOG_LEVEL=INFO
heroku config:set JWT_SECRET=your_jwt_secret
heroku config:set LINE_CLIENT_ID=your_line_client_id
heroku config:set LINE_CLIENT_SECRET=your_line_client_secret

# Add PostgreSQL addon
heroku addons:create heroku-postgresql:hobby-dev
```

#### 4. Deploy to Heroku

```bash
# Deploy
git push heroku main

# Run database migrations
heroku run ./scripts/db-migrate.sh

# Check logs
heroku logs --tail
```

## Monitoring and Logging

### Application Monitoring

#### 1. Health Checks

The application provides health check endpoints:

```bash
# Basic health check
curl http://localhost:8000/api/health

# Detailed health check (includes database)
curl http://localhost:8000/api/health/detailed
```

#### 2. Logging Configuration

Configure structured logging in production:

```python
# In logging_config.py
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(name)s %(levelname)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}
```

#### 3. Metrics Collection

Add metrics collection with Prometheus:

```python
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    
    REQUEST_COUNT.labels(method=request.method, endpoint=request.url.path).inc()
    REQUEST_DURATION.observe(duration)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### Database Monitoring

#### 1. Connection Pool Monitoring

Monitor database connection pool:

```python
@app.get("/api/health/database")
async def database_health():
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid()
    }
```

#### 2. Query Performance

Log slow queries:

```python
import logging
from sqlalchemy import event
from sqlalchemy.engine import Engine

logging.basicConfig()
logger = logging.getLogger("sqlalchemy.engine")
logger.setLevel(logging.INFO)

@event.listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@event.listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time
    if total > 0.1:  # Log queries taking more than 100ms
        logger.warning(f"Slow query: {total:.2f}s - {statement[:100]}...")
```

## Security Considerations

### 1. Environment Security

- Use environment variables for sensitive configuration
- Never commit secrets to version control
- Use secret management services (AWS Secrets Manager, etc.)
- Rotate secrets regularly

### 2. Network Security

- Use HTTPS in production
- Configure proper CORS settings
- Implement rate limiting
- Use a Web Application Firewall (WAF)

### 3. Database Security

- Use connection pooling
- Enable SSL for database connections
- Implement proper access controls
- Regular security updates

### 4. Application Security

- Validate all input data
- Use parameterized queries
- Implement proper authentication
- Log security events

## Backup and Recovery

### 1. Database Backups

```bash
# Create backup
pg_dump $DATABASE_URL > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
psql $DATABASE_URL < backup_20250916_120000.sql
```

### 2. Automated Backups

Create a backup script:

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/api_server_$DATE.sql"

# Create backup
pg_dump $DATABASE_URL > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Upload to S3 (optional)
aws s3 cp $BACKUP_FILE.gz s3://your-backup-bucket/

# Clean up old backups (keep last 7 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +7 -delete
```

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   ```bash
   # Check database connectivity
   psql $DATABASE_URL -c "SELECT 1;"
   
   # Check connection pool
   curl http://localhost:8000/api/health/database
   ```

2. **Memory Issues**
   ```bash
   # Monitor memory usage
   docker stats
   
   # Check application logs
   docker logs api-server
   ```

3. **Performance Issues**
   ```bash
   # Check response times
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/api/health
   
   # Monitor database queries
   # Enable query logging in PostgreSQL
   ```

### Debugging

Enable debug mode temporarily:

```bash
# Set debug environment variable
export DEBUG=true

# Restart application
systemctl restart api-server

# Check detailed logs
journalctl -u api-server -f
```

## Scaling

### Horizontal Scaling

1. **Load Balancer Configuration**
   - Use nginx or cloud load balancer
   - Configure health checks
   - Implement session affinity if needed

2. **Database Scaling**
   - Use read replicas for read-heavy workloads
   - Implement connection pooling
   - Consider database sharding for large datasets

3. **Caching**
   - Implement Redis for session storage
   - Add application-level caching
   - Use CDN for static assets

### Vertical Scaling

1. **Resource Monitoring**
   - Monitor CPU and memory usage
   - Track database performance
   - Monitor network I/O

2. **Performance Optimization**
   - Optimize database queries
   - Implement async processing
   - Use connection pooling

This deployment guide provides comprehensive instructions for deploying the API server in various environments. Choose the deployment method that best fits your infrastructure and requirements.