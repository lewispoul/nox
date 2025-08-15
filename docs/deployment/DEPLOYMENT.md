# Nox Containerized Deployment Guide

This guide covers deploying Nox using Docker containers with monitoring, authentication, and production-ready configurations.

## 📋 Prerequisites

- Docker Engine 20.10+
- Docker Compose V2
- Minimum 4GB RAM, 20GB storage
- PostgreSQL-compatible database (included in compose)
- SSL certificates for production (Let's Encrypt recommended)

## 🚀 Quick Start

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd nox-api-src
cp .env.example .env
```

### 2. Configure Environment Variables

Edit `.env` file with your production values:

```bash
# Database
DATABASE_URL=postgresql://noxuser:secure_password@postgres:5432/noxdb
POSTGRES_PASSWORD=secure_password

# Authentication
JWT_SECRET_KEY=your_super_secure_jwt_secret_here_min_32_chars
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# OAuth2 (optional - for future releases)
OAUTH_GOOGLE_CLIENT_ID=your_google_client_id
OAUTH_GOOGLE_CLIENT_SECRET=your_google_client_secret
OAUTH_GITHUB_CLIENT_ID=your_github_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_github_client_secret

# Application
NOX_API_HOST=0.0.0.0
NOX_API_PORT=8000
NOX_DASHBOARD_HOST=0.0.0.0
NOX_DASHBOARD_PORT=8501
CORS_ORIGINS=http://localhost:8501,https://your-domain.com

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=secure_grafana_password
```

### 3. Initialize Database

```bash
# Start PostgreSQL service first
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
sleep 10

# Initialize database schema
docker-compose exec postgres psql -U noxuser -d noxdb -f /docker-entrypoint-initdb.d/init-db.sql
```

### 4. Deploy All Services

```bash
# Build and start all services
docker-compose up -d

# Check service health
docker-compose ps
```

## 🔧 Service Architecture

### Services Overview

| Service | Port | Purpose | Health Check |
|---------|------|---------|-------------|
| `nox-api` | 8000 | Core API server | `GET /health` |
| `nox-dashboard` | 8501 | Streamlit UI | `GET /_stcore/health` |
| `postgres` | 5432 | Database | `pg_isready` |
| `prometheus` | 9090 | Metrics collection | `GET /-/healthy` |
| `grafana` | 3000 | Monitoring dashboards | `GET /api/health` |

### Network Configuration

- **Internal Network**: `nox-network` (bridge)
- **Service Discovery**: DNS-based service names
- **External Access**: Only API and Dashboard exposed by default

## 🔒 Security Configuration

### Authentication System

- **JWT Tokens**: HS256 algorithm with secure secrets
- **Role-Based Access**: Admin/User roles with granular permissions
- **Password Hashing**: bcrypt with salt rounds
- **Session Management**: Refresh token rotation

### Container Security

```bash
# Non-root users in containers
USER 1001

# Read-only root filesystem where possible
security_opt:
  - no-new-privileges:true

# Resource limits
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

### Network Security

- Internal-only database access
- CORS configuration for web origins
- Health check endpoints protected
- Monitoring access control

## 📊 Monitoring & Observability

### Prometheus Metrics

Access metrics at: `http://localhost:9090`

**Key Metrics:**
- `nox_api_requests_total` - HTTP request counter
- `nox_api_request_duration_seconds` - Request latency
- `nox_api_active_users` - Active user sessions
- `nox_quota_usage_ratio` - User quota utilization

### Grafana Dashboards

Access dashboards at: `http://localhost:3000` (admin/secure_grafana_password)

**Pre-configured Dashboards:**
- Nox API Performance
- User Activity & Quotas
- System Resource Usage
- Error Rates & Alerts

### Alert Rules

**Critical Alerts:**
- API service down (>1 minute)
- High error rate (>5% over 5 minutes)
- Database connection failures
- Storage quota exceeded (>90%)

## 🔄 CI/CD Integration

### GitHub Actions Workflow

The included `.github/workflows/docker-build.yml` provides:

1. **Automated Testing** on PR/push
2. **Multi-platform Builds** (amd64/arm64)
3. **Security Scanning** with Trivy
4. **Container Registry** publishing to GHCR
5. **Staging/Production** deployment hooks

### Manual Build & Push

```bash
# Build images locally
docker build -t nox-api:latest -f Dockerfile.api .
docker build -t nox-dashboard:latest -f Dockerfile.dashboard .

# Tag for registry
docker tag nox-api:latest ghcr.io/your-org/nox-api:v2.4.0
docker tag nox-dashboard:latest ghcr.io/your-org/nox-dashboard:v2.4.0

# Push to registry
docker push ghcr.io/your-org/nox-api:v2.4.0
docker push ghcr.io/your-org/nox-dashboard:v2.4.0
```

## 🐛 Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
docker-compose logs nox-api
docker-compose logs postgres

# Check service health
curl http://localhost:8000/health
```

#### Database Connection Issues

```bash
# Test database connectivity
docker-compose exec nox-api python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://noxuser:password@postgres:5432/noxdb')
    print(await conn.fetchval('SELECT version()'))
    await conn.close()
asyncio.run(test())
"
```

#### High Memory Usage

```bash
# Check container resource usage
docker stats

# Adjust limits in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 1G
```

### Log Analysis

```bash
# Follow API logs
docker-compose logs -f nox-api

# Search for errors
docker-compose logs nox-api | grep ERROR

# Export logs for analysis
docker-compose logs --timestamps > nox-deployment-logs.txt
```

## 🔧 Maintenance

### Database Backup

```bash
# Create backup
docker-compose exec postgres pg_dump -U noxuser noxdb > nox-backup-$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T postgres psql -U noxuser noxdb < nox-backup-20240115.sql
```

### Update Deployment

```bash
# Pull latest images
docker-compose pull

# Recreate containers with new images
docker-compose up -d --force-recreate

# Clean up old images
docker image prune -f
```

### Scaling Services

```bash
# Scale API service
docker-compose up -d --scale nox-api=3

# Use load balancer (nginx/traefik) for multiple API instances
```

## 📈 Performance Tuning

### PostgreSQL Optimization

```sql
-- Add to init-db.sql for production
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
```

### API Performance

```yaml
# In docker-compose.yml
nox-api:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 1G
    replicas: 3
```

## 🛡️ Production Checklist

- [ ] Change all default passwords
- [ ] Configure SSL/TLS certificates
- [ ] Set up log rotation
- [ ] Configure backup strategy
- [ ] Test disaster recovery
- [ ] Set up monitoring alerts
- [ ] Configure firewall rules
- [ ] Review security scan results
- [ ] Test OAuth2 integration (when enabled)
- [ ] Validate quota enforcement
- [ ] Performance load testing

## 🆘 Support

For issues and support:

1. Check service logs: `docker-compose logs <service>`
2. Review Grafana dashboards for metrics
3. Test with health check endpoints
4. Consult troubleshooting section above
5. Check GitHub issues for known problems

---

**Nox Containerized Deployment v2.4+**  
Last updated: January 2024
