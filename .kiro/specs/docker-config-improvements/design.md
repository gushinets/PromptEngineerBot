# Design Document: Docker Configuration Improvements

## Overview

This design describes the improvements to the Docker configuration for the Prompt Engineering Bot. The changes focus on security hardening, environment separation, operational automation, and comprehensive documentation. The target deployment environment is a VPS running Ubuntu 22+ with Docker.

## Architecture

The deployment architecture follows a 3-file Docker Compose pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│                         VPS (Ubuntu 22+)                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Docker Engine                         │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │   │
│  │  │    Bot      │  │   Redis     │  │  Postgres   │     │   │
│  │  │  Container  │  │  Container  │  │  Container  │     │   │
│  │  └──────┬──────┘  └─────────────┘  └──────┬──────┘     │   │
│  │         │                                  │            │   │
│  │         ▼                                  ▼            │   │
│  │  ┌─────────────┐                   ┌─────────────┐     │   │
│  │  │  logs/      │                   │ postgres_   │     │   │
│  │  │  bot.log    │                   │ data volume │     │   │
│  │  └─────────────┘                   └─────────────┘     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐            │
│  │   .env      │  │  backups/   │  │  logrotate  │            │
│  │   (secrets) │  │  (pg_dump)  │  │  (cron)     │            │
│  └─────────────┘  └─────────────┘  └─────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

### Compose File Structure

```
docker-compose.yml        # Base configuration (shared)
docker-compose.dev.yml    # Development overrides (exposed ports)
docker-compose.prod.yml   # Production overrides (security, logging)
```

**Usage:**
- Development: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`
- Production: `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`

## Components and Interfaces

### 1. Dockerfile

The Dockerfile builds the bot application image with security improvements:

```dockerfile
# Use official Python image
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd --create-home --shell /bin/bash app

# Copy application files ONLY (no secrets)
COPY alembic.ini .
COPY alembic ./alembic
COPY telegram_bot ./telegram_bot
COPY run_bot.py .
COPY scripts/healthcheck.py ./scripts/

# Change ownership
RUN chown -R app:app /app

USER app

# Healthcheck using Telegram API ping
HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD python /app/scripts/healthcheck.py

# Webhook port (uncomment when switching to webhook mode)
# EXPOSE 8080

CMD ["python", "run_bot.py"]
```

**Key changes from current:**
- Removed `COPY .env* ./`
- Removed `COPY google_service_key.json* ./`
- Added healthcheck script copy
- Updated HEALTHCHECK to use Telegram API ping

### 2. Base Compose File (docker-compose.yml)

```yaml
services:
  prompt-improver-bot:
    build: .
    container_name: prompt-improver-bot
    env_file:
      - .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./google_service_key.json:/app/google_service_key.json:ro
      - ./logs:/app/logs
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379

  redis:
    image: redis:7-alpine
    container_name: prompt-bot-redis
    volumes:
      - redis_data:/data
    command: >
      redis-server 
      --appendonly yes 
      --requirepass ${REDIS_PASSWORD}
      --maxmemory 256mb 
      --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    container_name: prompt-bot-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  redis_data:
  postgres_data:

networks:
  default:
    name: prompt-bot-network
```

### 3. Development Compose File (docker-compose.dev.yml)

```yaml
services:
  prompt-improver-bot:
    restart: unless-stopped
    environment:
      - LOG_LEVEL=DEBUG

  redis:
    restart: unless-stopped
    ports:
      - "6379:6379"

  postgres:
    restart: unless-stopped
    ports:
      - "5432:5432"
```

### 4. Production Compose File (docker-compose.prod.yml)

```yaml
services:
  prompt-improver-bot:
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    # Webhook port (uncomment when switching to webhook mode)
    # ports:
    #   - "8080:8080"

  redis:
    restart: always
    command: >
      redis-server 
      --appendonly yes 
      --requirepass ${REDIS_PASSWORD}
      --protected-mode yes
      --maxmemory 256mb 
      --maxmemory-policy allkeys-lru
      --rename-command SLAVEOF ""
      --rename-command REPLICAOF ""
      --rename-command CONFIG ""
      --rename-command FLUSHALL ""

  postgres:
    restart: always
```

### 5. Healthcheck Script (scripts/healthcheck.py)

```python
#!/usr/bin/env python3
"""
Healthcheck script that verifies Telegram API connectivity.
Used by Docker HEALTHCHECK to determine container health.
Exit code 0 = healthy, 1 = unhealthy.
"""
import os
import sys

try:
    import httpx
except ImportError:
    # httpx should be installed, but fallback to urllib
    import urllib.request
    import json
    
    def check_telegram():
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            return False
        url = f"https://api.telegram.org/bot{token}/getMe"
        try:
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data.get("ok", False)
        except Exception:
            return False
else:
    def check_telegram():
        token = os.environ.get("TELEGRAM_TOKEN")
        if not token:
            return False
        try:
            response = httpx.get(
                f"https://api.telegram.org/bot{token}/getMe",
                timeout=10.0
            )
            return response.status_code == 200 and response.json().get("ok", False)
        except Exception:
            return False

if __name__ == "__main__":
    sys.exit(0 if check_telegram() else 1)
```

### 6. Backup Script (scripts/backup-db.sh)

```bash
#!/bin/bash
# Database backup script with 14-day retention
# Run via cron: 0 2 * * * /home/deploy/prompt-bot/scripts/backup-db.sh

set -e

BACKUP_DIR="/home/deploy/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/botdb_$TIMESTAMP.sql.gz"
LOG_FILE="$BACKUP_DIR/backup.log"
RETENTION_DAYS=14

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting backup..."

# Run pg_dump inside postgres container and compress
if docker exec prompt-bot-postgres pg_dump -U "${POSTGRES_USER:-botuser}" "${POSTGRES_DB:-botdb}" | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"
else
    log "ERROR: Backup failed!"
    exit 1
fi

# Delete old backups
DELETED=$(find "$BACKUP_DIR" -name "botdb_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "Deleted $DELETED old backup(s) (older than $RETENTION_DAYS days)"
fi

log "Backup process completed"
```

### 7. Server Setup Script (scripts/server-setup.sh)

```bash
#!/bin/bash
# VPS Server Setup Script for Ubuntu 22+
# Run as root or with sudo

set -e

APP_USER="deploy"
APP_DIR="/home/$APP_USER/prompt-bot"
BACKUP_DIR="/home/$APP_USER/backups"
LOG_DIR="/home/$APP_USER/prompt-bot/logs"

echo "=== Prompt Bot VPS Setup ==="

# Update system
echo "Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker
echo "Installing Docker..."
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker on boot
systemctl enable docker
systemctl start docker

# Create deploy user
echo "Creating deploy user..."
if ! id "$APP_USER" &>/dev/null; then
    useradd -m -s /bin/bash "$APP_USER"
    usermod -aG docker "$APP_USER"
fi

# Create directories
echo "Creating directories..."
mkdir -p "$APP_DIR" "$BACKUP_DIR" "$LOG_DIR"
chown -R "$APP_USER:$APP_USER" "/home/$APP_USER"

# Configure UFW firewall
echo "Configuring firewall..."
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw --force enable

# Configure logrotate for bot logs
echo "Configuring logrotate..."
cat > /etc/logrotate.d/prompt-bot << 'EOF'
/home/deploy/prompt-bot/logs/bot.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 644 deploy deploy
}
EOF

# Setup backup cron job
echo "Setting up backup cron..."
CRON_CMD="0 2 * * * /home/deploy/prompt-bot/scripts/backup-db.sh"
(crontab -u "$APP_USER" -l 2>/dev/null | grep -v "backup-db.sh"; echo "$CRON_CMD") | crontab -u "$APP_USER" -

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "1. Generate SSH key for deploy user:"
echo "   sudo -u $APP_USER ssh-keygen -t ed25519 -C 'deploy@vps'"
echo ""
echo "2. Add the public key to your GitHub repo as a deploy key:"
echo "   sudo -u $APP_USER cat /home/$APP_USER/.ssh/id_ed25519.pub"
echo ""
echo "3. Clone your repository:"
echo "   sudo -u $APP_USER git clone git@github.com:YOUR_USER/YOUR_REPO.git $APP_DIR"
echo ""
echo "4. Create .env file with your secrets:"
echo "   sudo -u $APP_USER cp $APP_DIR/.env.example $APP_DIR/.env"
echo "   sudo -u $APP_USER nano $APP_DIR/.env"
echo ""
echo "5. Run the deploy script:"
echo "   sudo -u $APP_USER $APP_DIR/scripts/deploy.sh"
```

### 8. Deployment Script (scripts/deploy.sh)

```bash
#!/bin/bash
# Deployment script for Prompt Bot
# Run as deploy user from app directory

set -e

APP_DIR="/home/deploy/prompt-bot"
COMPOSE_FILES="-f docker-compose.yml -f docker-compose.prod.yml"

cd "$APP_DIR"

echo "=== Deploying Prompt Bot ==="

# Pull latest code
echo "Pulling latest code..."
git pull origin main

# Build new image (keeps old image for rollback)
echo "Building Docker image..."
docker compose $COMPOSE_FILES build

# Run database migrations
echo "Running database migrations..."
docker compose $COMPOSE_FILES run --rm prompt-improver-bot alembic upgrade head

# Restart services
echo "Restarting services..."
docker compose $COMPOSE_FILES up -d

# Wait for services to start
echo "Waiting for services to start..."
sleep 10

# Verify health
echo "Verifying service health..."
if docker compose $COMPOSE_FILES ps | grep -q "unhealthy"; then
    echo "ERROR: Some services are unhealthy!"
    docker compose $COMPOSE_FILES ps
    exit 1
fi

echo ""
echo "=== Deployment Complete ==="
docker compose $COMPOSE_FILES ps
```

## Data Models

### Environment Variables (.env)

```bash
# Telegram Bot
TELEGRAM_TOKEN=your_telegram_bot_token

# Database
POSTGRES_DB=botdb
POSTGRES_USER=botuser
POSTGRES_PASSWORD=your_secure_password_here

# Redis
REDIS_PASSWORD=your_redis_password_here

# LLM API (choose one)
OPENROUTER_API_KEY=your_openrouter_key
# OPENAI_API_KEY=your_openai_key

# Email (optional)
EMAIL_ENABLED=true
SMTP_HOST=smtp-pulse.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false
SMTP_USERNAME=your_smtp_username
SMTP_PASSWORD=your_smtp_password
SMTP_FROM_EMAIL=noreply@yourdomain.com

# Rate Limiting
EMAIL_RATE_LIMIT_PER_HOUR=3
USER_RATE_LIMIT_PER_HOUR=5
OTP_SPACING_SECONDS=60

# Logging
LOG_LEVEL=INFO

# Language
LANGUAGE=EN
```

### Logrotate Configuration

```
/home/deploy/prompt-bot/logs/bot.log {
    daily           # Rotate daily
    rotate 14       # Keep 14 days
    compress        # Gzip old logs
    delaycompress   # Compress on next rotation
    missingok       # Don't error if log missing
    notifempty      # Don't rotate empty logs
    copytruncate    # Truncate in place (no restart needed)
    create 644 deploy deploy
}
```

### Cron Configuration

```
# Database backup - daily at 2:00 AM
0 2 * * * /home/deploy/prompt-bot/scripts/backup-db.sh
```



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

Based on the prework analysis, most requirements in this specification are configuration/static checks that are best verified as examples rather than properties. However, the healthcheck script has behavioral properties that can be formally specified:

### Property 1: Healthcheck Success on Valid Token

*For any* valid Telegram bot token, when the healthcheck script is executed with that token in the TELEGRAM_TOKEN environment variable, the script SHALL exit with code 0 if and only if the Telegram API returns a successful response.

**Validates: Requirements 4.1, 4.2**

### Property 2: Healthcheck Failure on Invalid/Missing Token

*For any* invalid or missing Telegram bot token, when the healthcheck script is executed, the script SHALL exit with code 1.

**Validates: Requirements 4.1, 4.3**

### Property 3: Healthcheck Timeout Handling

*For any* network condition where the Telegram API does not respond within the timeout period, the healthcheck script SHALL exit with code 1 rather than hanging indefinitely.

**Validates: Requirements 4.3**

### Non-Property Verifications

The remaining requirements are configuration checks best verified as examples:

- **Dockerfile contents**: Verify absence of secret copies, presence of healthcheck config
- **Compose file structure**: Verify service definitions, environment variable substitution, volume mounts
- **Script contents**: Verify correct commands and configurations in shell scripts
- **Documentation**: Manual review for completeness and accuracy

## Error Handling

### Container Startup Failures

| Error Condition | Handling |
|-----------------|----------|
| Missing .env file | Docker Compose fails with clear "env file not found" error |
| Missing required env vars | Container fails to start; depends_on with healthcheck prevents cascade |
| Database not ready | Bot waits via depends_on condition: service_healthy |
| Redis not ready | Bot waits via depends_on condition: service_healthy |
| Invalid TELEGRAM_TOKEN | Healthcheck fails, container marked unhealthy after retries |

### Backup Script Errors

| Error Condition | Handling |
|-----------------|----------|
| Postgres container not running | pg_dump fails, script logs error and exits with code 1 |
| Disk full | gzip fails, script logs error and exits with code 1 |
| Permission denied | Script logs error and exits with code 1 |

### Deployment Script Errors

| Error Condition | Handling |
|-----------------|----------|
| Git pull fails | Script exits immediately with error (set -e) |
| Build fails | Script exits immediately with error |
| Migration fails | Script exits immediately with error |
| Unhealthy services after deploy | Script reports error and exits with code 1 |

## Testing Strategy

### Dual Testing Approach

This specification primarily involves infrastructure configuration rather than application logic. Testing is divided into:

1. **Static Configuration Tests (Examples)**: Verify file contents match expected patterns
2. **Integration Tests**: Verify containers start and communicate correctly
3. **Property Tests**: Verify healthcheck script behavior

### Unit/Example Tests

Configuration verification tests using shell scripts or Python:

```python
# Example: Verify Dockerfile doesn't copy secrets
def test_dockerfile_no_secrets():
    with open("Dockerfile") as f:
        content = f.read()
    assert "COPY .env" not in content
    assert "COPY google_service_key.json" not in content or "google_service_key.json*" in content

# Example: Verify compose uses env var substitution
def test_compose_uses_env_vars():
    with open("docker-compose.yml") as f:
        content = f.read()
    assert "${POSTGRES_PASSWORD}" in content
    assert "${POSTGRES_USER}" in content
```

### Property-Based Tests

Using pytest with hypothesis for healthcheck script testing:

```python
# Property test for healthcheck behavior
from hypothesis import given, strategies as st

@given(st.text())
def test_healthcheck_invalid_token_fails(invalid_token):
    """For any invalid token string, healthcheck should return exit code 1"""
    # Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token
    # Validates: Requirements 4.1, 4.3
    result = run_healthcheck_with_token(invalid_token)
    assert result.returncode == 1
```

### Integration Tests

Manual or CI-based verification:

1. Build image and verify no secrets inside
2. Start services with dev compose and verify port exposure
3. Start services with prod compose and verify no port exposure
4. Verify healthcheck transitions container to healthy state
5. Run backup script and verify backup file created
6. Run deploy script on test environment

### Test Configuration

- Property tests: Minimum 100 iterations per property
- Integration tests: Run in CI pipeline before merge
- Configuration tests: Run as pre-commit hooks

### Testing Tools

- **pytest**: Python test framework
- **hypothesis**: Property-based testing library
- **shellcheck**: Shell script linting
- **hadolint**: Dockerfile linting
- **docker-compose config**: Validate compose file syntax
