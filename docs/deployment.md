# SnackBase Deployment Guide

This guide covers deploying SnackBase in development and production environments.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Database Configuration](#database-configuration)
- [Environment Variables](#environment-variables)
- [Health Checks](#health-checks)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

- **Python**: 3.12 or higher
- **uv**: Package manager ([installation guide](https://github.com/astral-sh/uv))
- **Database**: SQLite (development) or PostgreSQL (production recommended)

### Optional

- **Docker**: For containerized deployment (coming soon)
- **Nginx**: For reverse proxy in production
- **systemd**: For service management on Linux

---

## Development Deployment

### Quick Start

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd SnackBase
   ```

2. **Install dependencies**:

   ```bash
   uv sync
   ```

3. **Create environment file**:

   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start the development server**:

   ```bash
   uv run python -m snackbase serve --reload
   ```

5. **Access the application**:
   - API: http://localhost:8000
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Development Configuration

Create a `.env` file in the project root:

```bash
# Application
SNACKBASE_ENVIRONMENT=development
SNACKBASE_DEBUG=true
SNACKBASE_API_PREFIX=/api/v1

# Server
SNACKBASE_HOST=0.0.0.0
SNACKBASE_PORT=8000

# Database (SQLite for development)
SNACKBASE_DATABASE_URL=sqlite+aiosqlite:///./sb_data/snackbase.db

# Security
SNACKBASE_SECRET_KEY=dev-secret-key-change-in-production

# CORS (allow localhost for development)
SNACKBASE_CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Logging
SNACKBASE_LOG_LEVEL=DEBUG
SNACKBASE_LOG_FORMAT=console
```

### Development Server Options

```bash
# Start with auto-reload (watches for file changes)
uv run python -m snackbase serve --reload

# Custom host and port
uv run python -m snackbase serve --host 127.0.0.1 --port 3000

# Multiple workers (not recommended with --reload)
uv run python -m snackbase serve --workers 4

# Using uvicorn directly
uv run uvicorn snackbase.infrastructure.api.app:app --reload --port 8000
```

### Initialize Database

The database is automatically initialized on first run. To manually initialize:

```bash
uv run python -m snackbase init-db
```

### Development Tools

```bash
# Interactive Python shell with SnackBase context
uv run python -m snackbase shell

# View configuration
uv run python -m snackbase info

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=snackbase

# Code formatting
uv run ruff format .

# Linting
uv run ruff check .

# Type checking
uv run mypy src/
```

---

## Production Deployment

### Deployment Checklist

- [ ] Set strong `SNACKBASE_SECRET_KEY`
- [ ] Use PostgreSQL database
- [ ] Set `SNACKBASE_ENVIRONMENT=production`
- [ ] Set `SNACKBASE_DEBUG=false`
- [ ] Configure proper CORS origins
- [ ] Set up reverse proxy (Nginx)
- [ ] Enable HTTPS/TLS
- [ ] Configure log aggregation
- [ ] Set up monitoring and alerts
- [ ] Configure automated backups
- [ ] Test health check endpoints

### Option 1: Direct Deployment (systemd)

#### 1. Prepare the Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.12
sudo apt install python3.12 python3.12-venv -y

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create application user
sudo useradd -m -s /bin/bash snackbase
```

#### 2. Deploy Application

```bash
# Switch to application user
sudo su - snackbase

# Clone repository
git clone <repository-url> /home/snackbase/app
cd /home/snackbase/app

# Install dependencies
uv sync --frozen

# Create production environment file
nano .env
```

#### 3. Production Environment Configuration

```bash
# Application
SNACKBASE_ENVIRONMENT=production
SNACKBASE_DEBUG=false
SNACKBASE_API_PREFIX=/api/v1

# Server
SNACKBASE_HOST=0.0.0.0
SNACKBASE_PORT=8000

# Database (PostgreSQL)
SNACKBASE_DATABASE_URL=postgresql+asyncpg://snackbase:password@localhost/snackbase_prod

# Security
SNACKBASE_SECRET_KEY=<generate-strong-random-key>
SNACKBASE_ACCESS_TOKEN_EXPIRE_MINUTES=60
SNACKBASE_REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS (restrict to your domains)
SNACKBASE_CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Logging
SNACKBASE_LOG_LEVEL=INFO
SNACKBASE_LOG_FORMAT=json

# Storage
SNACKBASE_STORAGE_PATH=/home/snackbase/app/sb_data/files
```

> **Security Note**: Generate a strong secret key:
>
> ```bash
> python -c "import secrets; print(secrets.token_urlsafe(64))"
> ```

#### 4. Set Up PostgreSQL

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE snackbase_prod;
CREATE USER snackbase WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE snackbase_prod TO snackbase;
\q
EOF
```

#### 5. Create systemd Service

Create `/etc/systemd/system/snackbase.service`:

```ini
[Unit]
Description=SnackBase API Server
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=snackbase
Group=snackbase
WorkingDirectory=/home/snackbase/app
Environment="PATH=/home/snackbase/.local/bin:/usr/local/bin:/usr/bin:/bin"

# Use uv to run the application
ExecStart=/home/snackbase/.local/bin/uv run uvicorn snackbase.infrastructure.api.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers 4 \
    --log-config /home/snackbase/app/logging.json

# Restart policy
Restart=always
RestartSec=10

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/snackbase/app/sb_data

# Resource limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
```

#### 6. Start and Enable Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Start service
sudo systemctl start snackbase

# Enable on boot
sudo systemctl enable snackbase

# Check status
sudo systemctl status snackbase

# View logs
sudo journalctl -u snackbase -f
```

### Option 2: Nginx Reverse Proxy

#### 1. Install Nginx

```bash
sudo apt install nginx -y
```

#### 2. Configure Nginx

Create `/etc/nginx/sites-available/snackbase`:

```nginx
# Upstream to SnackBase
upstream snackbase_backend {
    server 127.0.0.1:8000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name api.yourdomain.com;

    return 301 https://$server_name$request_uri;
}

# HTTPS Server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name api.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security Headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Logging
    access_log /var/log/nginx/snackbase_access.log;
    error_log /var/log/nginx/snackbase_error.log;

    # Client body size (for file uploads)
    client_max_body_size 100M;

    # Proxy to SnackBase
    location / {
        proxy_pass http://snackbase_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket support (for future real-time features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint (bypass auth)
    location /health {
        proxy_pass http://snackbase_backend/health;
        access_log off;
    }
}
```

#### 3. Enable Site and Restart Nginx

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/snackbase /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

#### 4. Set Up SSL with Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### Option 3: Docker Deployment (Coming Soon)

Docker support will be added in a future update. The deployment will include:

- Multi-stage Dockerfile for optimized images
- docker-compose.yml for local development
- Production-ready container configuration
- Health checks and restart policies

---

## Database Configuration

### SQLite (Development Only)

```bash
SNACKBASE_DATABASE_URL=sqlite+aiosqlite:///./sb_data/snackbase.db
```

**Pros**:

- Zero configuration
- Perfect for development
- File-based, easy to backup

**Cons**:

- Not suitable for production
- Limited concurrency
- No network access

### PostgreSQL (Recommended for Production)

```bash
SNACKBASE_DATABASE_URL=postgresql+asyncpg://user:password@host:port/database
```

**Setup**:

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb snackbase_prod

# Create user
sudo -u postgres createuser snackbase -P

# Grant privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE snackbase_prod TO snackbase;"
```

**Connection Pooling**:

SnackBase uses SQLAlchemy's async connection pooling. Configure in `.env`:

```bash
# Pool size (default: 5)
SNACKBASE_DB_POOL_SIZE=10

# Max overflow (default: 10)
SNACKBASE_DB_MAX_OVERFLOW=20

# Pool timeout (default: 30 seconds)
SNACKBASE_DB_POOL_TIMEOUT=30
```

---

## Environment Variables

### Complete Reference

| Variable                                | Default                                      | Description                                   |
| --------------------------------------- | -------------------------------------------- | --------------------------------------------- |
| `SNACKBASE_ENVIRONMENT`                 | `development`                                | Environment: development, staging, production |
| `SNACKBASE_DEBUG`                       | `false`                                      | Enable debug mode                             |
| `SNACKBASE_APP_NAME`                    | `SnackBase`                                  | Application name                              |
| `SNACKBASE_APP_VERSION`                 | `0.1.0`                                      | Application version                           |
| `SNACKBASE_API_PREFIX`                  | `/api/v1`                                    | API route prefix                              |
| `SNACKBASE_HOST`                        | `0.0.0.0`                                    | Server bind address                           |
| `SNACKBASE_PORT`                        | `8000`                                       | Server port                                   |
| `SNACKBASE_DATABASE_URL`                | `sqlite+aiosqlite:///./sb_data/snackbase.db` | Database connection URL                       |
| `SNACKBASE_SECRET_KEY`                  | (auto-generated)                             | JWT signing key                               |
| `SNACKBASE_ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                                         | Access token expiration                       |
| `SNACKBASE_REFRESH_TOKEN_EXPIRE_DAYS`   | `7`                                          | Refresh token expiration                      |
| `SNACKBASE_CORS_ORIGINS`                | `*`                                          | Allowed CORS origins (comma-separated)        |
| `SNACKBASE_CORS_ALLOW_CREDENTIALS`      | `true`                                       | Allow credentials in CORS                     |
| `SNACKBASE_CORS_ALLOW_METHODS`          | `*`                                          | Allowed HTTP methods                          |
| `SNACKBASE_CORS_ALLOW_HEADERS`          | `*`                                          | Allowed headers                               |
| `SNACKBASE_LOG_LEVEL`                   | `INFO`                                       | Logging level: DEBUG, INFO, WARNING, ERROR    |
| `SNACKBASE_LOG_FORMAT`                  | `json`                                       | Log format: json, console                     |
| `SNACKBASE_STORAGE_PATH`                | `./sb_data/files`                            | File storage directory                        |

---

## Health Checks

SnackBase provides three health check endpoints:

### `/health` - Basic Health Check

Returns 200 if the service is running.

```bash
curl http://localhost:8000/health
```

Response:

```json
{
  "status": "healthy",
  "service": "SnackBase",
  "version": "0.1.0"
}
```

### `/ready` - Readiness Check

Returns 200 if the service is ready to accept requests (includes database connectivity).

```bash
curl http://localhost:8000/ready
```

Response:

```json
{
  "status": "ready",
  "service": "SnackBase",
  "version": "0.1.0",
  "database": "connected"
}
```

### `/live` - Liveness Check

Returns 200 if the service is alive (simple ping).

```bash
curl http://localhost:8000/live
```

Response:

```json
{
  "status": "alive",
  "service": "SnackBase",
  "version": "0.1.0"
}
```

### Using Health Checks

**systemd**:

```ini
[Service]
ExecStartPost=/bin/sleep 5
ExecStartPost=/usr/bin/curl -f http://localhost:8000/ready || exit 1
```

**Kubernetes** (future):

```yaml
livenessProbe:
  httpGet:
    path: /live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## Troubleshooting

### Service Won't Start

**Check logs**:

```bash
sudo journalctl -u snackbase -n 50 --no-pager
```

**Common issues**:

- Database connection failure
- Port already in use
- Missing environment variables
- File permission issues

### Database Connection Errors

**PostgreSQL**:

```bash
# Test connection
psql -h localhost -U snackbase -d snackbase_prod

# Check PostgreSQL is running
sudo systemctl status postgresql
```

**SQLite**:

```bash
# Check file permissions
ls -la sb_data/snackbase.db

# Ensure directory exists
mkdir -p sb_data
```

### Permission Denied Errors

```bash
# Fix ownership
sudo chown -R snackbase:snackbase /home/snackbase/app

# Fix permissions
chmod 755 /home/snackbase/app
chmod 644 /home/snackbase/app/.env
```

### High Memory Usage

**Reduce worker count**:

```bash
# In systemd service file
ExecStart=... --workers 2
```

**Configure connection pool**:

```bash
# In .env
SNACKBASE_DB_POOL_SIZE=5
SNACKBASE_DB_MAX_OVERFLOW=10
```

### Slow API Responses

**Check database**:

```bash
# PostgreSQL query performance
sudo -u postgres psql snackbase_prod -c "SELECT * FROM pg_stat_activity;"
```

**Enable query logging**:

```bash
# In .env
SNACKBASE_LOG_LEVEL=DEBUG
```

### CORS Errors

**Update CORS origins**:

```bash
# In .env
SNACKBASE_CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
```

**Check Nginx configuration**:

```bash
# Ensure proxy headers are set
proxy_set_header Host $host;
proxy_set_header X-Forwarded-Proto $scheme;
```

---

## Monitoring and Maintenance

### Log Management

**View logs**:

```bash
# systemd logs
sudo journalctl -u snackbase -f

# Application logs (if file-based)
tail -f /home/snackbase/app/logs/snackbase.log
```

**Log rotation** (if using file-based logging):

Create `/etc/logrotate.d/snackbase`:

```
/home/snackbase/app/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 snackbase snackbase
    sharedscripts
    postrotate
        systemctl reload snackbase > /dev/null 2>&1 || true
    endscript
}
```

### Performance Monitoring

**System resources**:

```bash
# CPU and memory
htop

# Disk usage
df -h

# Database size
du -sh sb_data/
```

**Application metrics** (future):

- Prometheus integration
- Grafana dashboards
- Custom metrics endpoint

### Backup Strategy

**Database backup** (PostgreSQL):

```bash
# Manual backup
pg_dump -U snackbase snackbase_prod > backup_$(date +%Y%m%d_%H%M%S).sql

# Automated backup (cron)
0 2 * * * pg_dump -U snackbase snackbase_prod | gzip > /backups/snackbase_$(date +\%Y\%m\%d).sql.gz
```

**File storage backup**:

```bash
# Backup uploaded files
tar -czf files_backup_$(date +%Y%m%d).tar.gz sb_data/files/
```

> **Note**: Automated backup/restore commands will be added in Phase 5 (F5.10)

---

## Security Best Practices

1. **Use strong secret keys**: Generate with `secrets.token_urlsafe(64)`
2. **Enable HTTPS**: Use Let's Encrypt for free SSL certificates
3. **Restrict CORS**: Only allow trusted domains
4. **Use PostgreSQL**: SQLite is not suitable for production
5. **Regular updates**: Keep dependencies up to date
6. **Monitor logs**: Set up log aggregation and alerts
7. **Firewall**: Only expose necessary ports (80, 443)
8. **Database security**: Use strong passwords, restrict network access
9. **File permissions**: Ensure proper ownership and permissions
10. **Rate limiting**: Add Nginx rate limiting (future enhancement)

---

## Next Steps

After deployment:

1. **Create first account**: Use the `/api/v1/auth/register` endpoint
2. **Test API**: Use Swagger UI at `/docs`
3. **Create collections**: Use the `/api/v1/collections` endpoint
4. **Set up monitoring**: Configure log aggregation and alerts
5. **Configure backups**: Set up automated database backups
6. **Review security**: Follow security best practices checklist

---

## Support

For issues and questions:

- GitHub Issues: [repository-url]/issues
- Documentation: [repository-url]/docs
- Community: [community-link]
