# Nox API v7.0.0 - Production Deployment Guide

This guide provides comprehensive instructions for deploying Nox API v7.0.0 in production environments using Docker containers and orchestration.

## 🚀 Quick Start

### Prerequisites

- **Docker Engine**: 24.0+ 
- **Docker Compose**: 2.20+
- **Git**: For code deployment
- **PostgreSQL**: Compatible with version 15+
- **Redis**: Compatible with version 7+

### Basic Production Deployment

1. **Clone and Configure**
   ```bash
   git clone <repository-url>
   cd nox-api-src
   cp .env.production .env
   # Edit .env with your production values
   ```

2. **Deploy Services**
   ```bash
   ./scripts/deploy.sh --environment production
   ```

3. **Verify Deployment**
   ```bash
   ./scripts/health-check.sh
   ```

## 🏗️ Architecture Overview

### Container Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Nginx/Proxy   │    │   Nox API v7    │    │   PostgreSQL    │
│   (Port 80/443) │────│   (Port 8082)   │────│   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐    ┌─────────────────┐
                       │      Redis      │    │   Monitoring    │
                       │   (Port 6379)   │    │  (Prometheus)   │
                       └─────────────────┘    └─────────────────┘
```

### Service Components

- **nox-api**: Main application container (FastAPI + Python 3.11)
- **postgres**: Database server (PostgreSQL 15)  
- **redis**: Cache and session storage (Redis 7)
- **prometheus**: Metrics collection (optional)
- **grafana**: Monitoring dashboard (optional)
- **nginx**: Reverse proxy and load balancer

## 📋 Environment Configuration

### Required Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://noxapi:secure_password@postgres:5432/noxdb
POSTGRES_USER=noxapi
POSTGRES_PASSWORD=secure_password
POSTGRES_DB=noxdb

# Redis Configuration  
REDIS_URL=redis://redis:6379/0

# OAuth2 Configuration
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
MICROSOFT_CLIENT_ID=your_microsoft_client_id
MICROSOFT_CLIENT_SECRET=your_microsoft_client_secret

# Security Configuration
SECRET_KEY=your_very_secure_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here

# Application Configuration
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
API_V7_URL=https://your-domain.com
FRONTEND_URL=https://your-frontend-domain.com
```

### Optional Configuration

```bash
# SSL/TLS Configuration
SSL_CERT_PATH=/etc/ssl/certs/fullchain.pem
SSL_KEY_PATH=/etc/ssl/private/privkey.pem

# Monitoring Configuration
PROMETHEUS_ENABLED=true
GRAFANA_ENABLED=true
METRICS_ENABLED=true

# Performance Configuration
WORKER_COUNT=4
MAX_CONNECTIONS=100
POOL_SIZE=20
```

## 🛠️ Deployment Scripts

### Primary Scripts

#### `deploy.sh` - Main Deployment Script
```bash
# Production deployment
./scripts/deploy.sh --environment production

# Development deployment  
./scripts/deploy.sh --environment development

# Skip tests and force rebuild
./scripts/deploy.sh --skip-tests --force-rebuild

# Available options:
# -e, --environment    production|development
# --skip-tests        Skip running tests
# --skip-build        Skip building Docker images
# --force-rebuild     Force rebuild of Docker images
```

#### `health-check.sh` - Health Monitoring
```bash
# Full health check
./scripts/health-check.sh

# Skip system resource checks
./scripts/health-check.sh --skip-system

# Custom API URL and timeout
./scripts/health-check.sh --api-url https://api.example.com --timeout 30

# Available options:
# -v, --verbose       Verbose output
# --skip-system      Skip system resource checks  
# --api-url URL      Custom API base URL
# --timeout SECONDS  Request timeout
```

#### `backup.sh` - Backup Management
```bash
# Create manual backup
./scripts/backup.sh --type manual

# Export Docker images with backup
./scripts/backup.sh --export-images

# List existing backups
./scripts/backup.sh --list

# Available options:
# -t, --type TYPE          Backup type (manual/scheduled/pre-deploy)
# --export-images         Export Docker images
# --skip-database         Skip database backup
# --retention-days N      Days to keep backups
```

#### `rollback.sh` - Rollback Management  
```bash
# List available backups
./scripts/rollback.sh --list

# Interactive rollback
./scripts/rollback.sh

# Force rollback to specific backup
./scripts/rollback.sh --backup backup_manual_20241201_140000 --force

# Available options:
# -b, --backup NAME       Backup name to restore
# -l, --list             List available backups
# -f, --force            Force rollback without confirmation
```

## 🏭 Production Deployment Strategies

### Blue-Green Deployment

1. **Deploy to Staging (Green)**
   ```bash
   # Deploy to staging environment
   ./scripts/deploy.sh --environment staging
   
   # Verify staging deployment
   ./scripts/health-check.sh --api-url https://staging-api.example.com
   ```

2. **Switch Traffic (Blue → Green)**
   ```bash
   # Update load balancer configuration
   # Switch DNS or proxy configuration
   # Monitor metrics during transition
   ```

3. **Validate and Rollback if Needed**
   ```bash
   # If issues detected, rollback
   ./scripts/rollback.sh --backup backup_pre_deploy_latest --force
   ```

### Rolling Deployment

1. **Scale Down Gradually**
   ```bash
   docker-compose up --scale nox-api=3 -d
   docker-compose up --scale nox-api=2 -d  
   docker-compose up --scale nox-api=1 -d
   ```

2. **Deploy New Version**
   ```bash
   ./scripts/deploy.sh --environment production --skip-tests
   ```

3. **Scale Up Gradually**
   ```bash
   docker-compose up --scale nox-api=2 -d
   docker-compose up --scale nox-api=4 -d
   ```

### Canary Deployment

1. **Deploy Single Instance**
   ```bash
   # Deploy single canary instance
   docker-compose -f docker-compose.canary.yml up -d
   ```

2. **Route 10% Traffic**
   ```bash
   # Configure load balancer for 90/10 split
   # Monitor metrics and error rates
   ```

3. **Gradually Increase Traffic**
   ```bash
   # 50/50 split, then full deployment
   ```

## 📊 Monitoring and Observability

### Health Endpoints

- **`/api/v7/auth/health`** - Basic health status
- **`/api/v7/status`** - Detailed application status  
- **`/api/v7/metrics/prometheus`** - Prometheus metrics

### Key Metrics to Monitor

```
# Application Metrics
nox_api_requests_total
nox_api_request_duration_seconds
nox_api_active_connections
nox_api_oauth_success_total
nox_api_oauth_failures_total

# System Metrics  
container_memory_usage_bytes
container_cpu_usage_percent
container_network_receive_bytes_total
container_network_transmit_bytes_total

# Database Metrics
postgresql_connections_active
postgresql_locks_count
postgresql_query_duration_seconds
```

### Log Aggregation

```bash
# View all service logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f nox-api
docker-compose logs -f postgres
docker-compose logs -f redis

# Export logs for analysis
docker-compose logs --since 24h > nox-api-logs.txt
```

## 🔒 Security Hardening

### Container Security

- **Non-root execution**: All containers run as non-root users
- **Minimal base images**: Alpine Linux for reduced attack surface  
- **Security scanning**: Trivy integration for vulnerability assessment
- **Secrets management**: Environment variables and Docker secrets

### Network Security

```yaml
# Custom network isolation
networks:
  nox-internal:
    driver: bridge
    internal: true
  nox-external: 
    driver: bridge

# Service network assignment
services:
  nox-api:
    networks:
      - nox-internal
      - nox-external
  postgres:
    networks:
      - nox-internal  # Database isolated from external
```

### SSL/TLS Configuration

```bash
# Generate SSL certificates (Let's Encrypt example)
certbot certonly --webroot -w /var/www/html -d api.example.com

# Configure nginx with SSL
server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate /etc/ssl/certs/fullchain.pem;
    ssl_certificate_key /etc/ssl/private/privkey.pem;
    
    location / {
        proxy_pass http://nox-api:8082;
    }
}
```

## 🚨 Troubleshooting

### Common Issues

#### Container Won't Start
```bash
# Check container logs
docker-compose logs nox-api

# Check container status
docker-compose ps

# Restart specific service
docker-compose restart nox-api
```

#### Database Connection Failed
```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready -U noxapi

# Test database connection
docker-compose exec nox-api python3 -c "
import asyncpg
import asyncio
async def test(): 
    conn = await asyncpg.connect('postgresql://noxapi:password@postgres:5432/noxdb')
    await conn.close()
asyncio.run(test())
"
```

#### OAuth2 Authentication Issues
```bash
# Verify OAuth2 configuration
docker-compose exec nox-api env | grep -E "(GOOGLE|GITHUB|MICROSOFT)"

# Test OAuth2 endpoints
curl -I http://localhost:8082/api/v7/auth/google/login
curl -I http://localhost:8082/api/v7/auth/github/login  
curl -I http://localhost:8082/api/v7/auth/microsoft/login
```

#### Memory/Performance Issues
```bash
# Check resource usage
docker stats

# Check system resources
./scripts/health-check.sh --verbose

# Scale services if needed
docker-compose up --scale nox-api=4 -d
```

### Log Analysis

```bash
# Search for errors
docker-compose logs | grep -i error

# Filter by time range  
docker-compose logs --since 2024-12-01T10:00:00

# Export structured logs
docker-compose logs --json > nox-logs.json
```

## 🔄 Maintenance and Updates

### Regular Maintenance Tasks

1. **Backup Creation** (Daily)
   ```bash
   # Automated via cron
   0 2 * * * /path/to/nox-api-src/scripts/backup.sh --type scheduled --quiet
   ```

2. **Health Monitoring** (Every 5 minutes)
   ```bash
   # Automated health checks
   */5 * * * * /path/to/nox-api-src/scripts/health-check.sh --skip-system --quiet
   ```

3. **Log Rotation** (Weekly)
   ```bash  
   # Rotate Docker logs
   docker-compose down
   docker system prune -f
   docker-compose up -d
   ```

4. **Security Updates** (Monthly)
   ```bash
   # Update base images
   docker-compose pull
   docker-compose up -d
   
   # Rebuild with latest updates
   ./scripts/deploy.sh --force-rebuild
   ```

### Version Updates

```bash
# 1. Create backup before update
./scripts/backup.sh --type pre-deploy

# 2. Pull new code
git fetch && git checkout v7.1.0  

# 3. Review changes
git diff v7.0.0..v7.1.0

# 4. Deploy new version
./scripts/deploy.sh --environment production

# 5. Verify deployment
./scripts/health-check.sh

# 6. Rollback if issues
./scripts/rollback.sh --list  # if needed
```

## 📞 Support and Resources

### Documentation Links
- **API Documentation**: `/docs` endpoint when running
- **OpenAPI Schema**: `/openapi.json` endpoint  
- **Health Status**: `/api/v7/auth/health` endpoint

### Useful Commands Reference

```bash
# Service management
docker-compose up -d                    # Start all services
docker-compose down                     # Stop all services  
docker-compose restart nox-api          # Restart API service
docker-compose ps                       # View service status

# Maintenance  
./scripts/backup.sh --list             # List backups
./scripts/health-check.sh              # Health check
./scripts/deploy.sh --help             # Deployment options

# Monitoring
docker stats                           # Resource usage
docker-compose logs -f --tail=100      # Follow recent logs
curl http://localhost:8082/api/v7/status # API status
```

### Emergency Procedures

1. **Service Down - Quick Recovery**
   ```bash
   docker-compose restart nox-api
   ./scripts/health-check.sh
   ```

2. **Data Corruption - Database Recovery**  
   ```bash
   ./scripts/rollback.sh --list
   ./scripts/rollback.sh --backup backup_scheduled_latest
   ```

3. **Complete System Failure - Full Restore**
   ```bash
   ./scripts/rollback.sh --backup backup_manual_latest --force
   ./scripts/health-check.sh --verbose
   ```

---

*This deployment guide covers Nox API v7.0.0 production deployment. For development setup, see the development documentation.*
