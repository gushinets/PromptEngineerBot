# Deployment Guide

This guide covers deploying the Prompt Engineering Bot to a VPS running Ubuntu 22+. It documents the 3-file Docker Compose structure, environment configuration, automated backups, and operational procedures.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Docker Compose Structure](#docker-compose-structure)
- [Environment Variables Reference](#environment-variables-reference)
- [VPS Setup Instructions](#vps-setup-instructions)
- [Deployment Workflow](#deployment-workflow)
- [Backup and Restore](#backup-and-restore)
- [Healthchecks and Monitoring](#healthchecks-and-monitoring)
- [Webhook Mode](#webhook-mode)
- [Troubleshooting](#troubleshooting)

---

## Architecture Overview

The deployment uses a 3-file Docker Compose pattern for clear separation between base configuration, development overrides, and production hardening:

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

---

## Docker Compose Structure

The configuration is split into three files:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base configuration with shared service definitions |
| `docker-compose.dev.yml` | Development overrides (exposed ports, debug logging) |
| `docker-compose.prod.yml` | Production hardening (restart policies, log rotation, security) |

### Usage Commands

**Development** (exposes Redis 6379 and Postgres 5432 for local tools):
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

**Production** (no exposed ports, restart always, log rotation):
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Base Configuration (docker-compose.yml)

The base file defines:
- Bot service with environment variable substitution for `DATABASE_URL` and `REDIS_URL`
- Redis with password authentication and memory limits
- PostgreSQL with healthcheck
- Volume mounts for `google_service_key.json` (read-only) and `logs/`
- Service dependencies with `condition: service_healthy`

### Development Overrides (docker-compose.dev.yml)

- `restart: unless-stopped` for all services
- Exposed ports: Redis 6379, Postgres 5432
- `LOG_LEVEL=DEBUG` environment variable

### Production Overrides (docker-compose.prod.yml)

- `restart: always` for all services
- JSON file logging with rotation (10MB max, 3 files)
- Hardened Redis with dangerous commands renamed/disabled
- Commented webhook port mapping (8080)

---

## Environment Variables Reference

Create a `.env` file from the example:
```bash
cp .env.example .env
```

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_TOKEN` | Bot token from @BotFather | `123456:ABC-DEF...` |
| `POSTGRES_DB` | PostgreSQL database name | `botdb` |
| `POSTGRES_USER` | PostgreSQL username | `botuser` |
| `POSTGRES_PASSWORD` | PostgreSQL password | `your_secure_password` |
| `REDIS_PASSWORD` | Redis authentication password | `your_redis_password` |

### LLM Backend (choose one)

| Variable | Description |
|----------|-------------|
| `LLM_BACKEND` | Backend type: `OPENAI` or `OPENROUTER` |
| `OPENAI_API_KEY` | OpenAI API key (if using OPENAI) |
| `OPENROUTER_API_KEY` | OpenRouter API key (if using OPENROUTER) |
| `MODEL_NAME` | Model to use (e.g., `openai/gpt-4`, `gpt-4o`) |

### Email Configuration (optional)

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_ENABLED` | Enable email authentication | `true` |
| `SMTP_HOST` | SMTP server hostname | `smtp-pulse.com` |
| `SMTP_PORT` | SMTP server port | `587` |
| `SMTP_USERNAME` | SMTP authentication username | - |
| `SMTP_PASSWORD` | SMTP authentication password | - |
| `SMTP_USE_TLS` | Use TLS encryption | `true` |
| `SMTP_USE_SSL` | Use SSL encryption | `false` |
| `SMTP_FROM_EMAIL` | Sender email address | - |

### Rate Limiting

| Variable | Description | Default |
|----------|-------------|---------|
| `EMAIL_RATE_LIMIT_PER_HOUR` | Max OTP emails per email/hour | `3` |
| `USER_RATE_LIMIT_PER_HOUR` | Max OTP emails per user/hour | `5` |
| `OTP_SPACING_SECONDS` | Minimum seconds between OTPs | `60` |

### Logging

| Variable | Description | Default |
|----------|-------------|---------|
| `LOG_LEVEL` | Log level (DEBUG, INFO, WARNING, ERROR) | `INFO` |

### Google Sheets Logging (optional)

| Variable | Description |
|----------|-------------|
| `GSHEETS_LOGGING_ENABLED` | Enable Google Sheets logging |
| `GSHEETS_SPREADSHEET_ID` | Spreadsheet ID |
| `GSHEETS_WORKSHEET` | Worksheet name |

---

## VPS Setup Instructions

### Prerequisites

- Fresh Ubuntu 22.04+ VPS
- Root or sudo access
- SSH access configured

### Automated Setup

The `scripts/server-setup.sh` script automates the entire VPS configuration:

```bash
# On your VPS as root
curl -O https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/scripts/server-setup.sh
chmod +x server-setup.sh
./server-setup.sh
```

The script performs:
1. System package updates
2. Docker and Docker Compose installation
3. Creates `deploy` user with docker group membership
4. Creates directories: `/home/deploy/prompt-bot`, `/home/deploy/backups`, `/home/deploy/prompt-bot/logs`
5. Configures UFW firewall (SSH only)
6. Enables Docker on boot
7. Configures logrotate for bot.log (daily, 14 days retention, compressed)
8. Sets up cron job for daily database backups at 2:00 AM

### Manual Setup Steps

If you prefer manual setup:

**1. Install Docker:**
```bash
apt-get update && apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
```

**2. Create deploy user:**
```bash
useradd -m -s /bin/bash deploy
usermod -aG docker deploy
```

**3. Create directories:**
```bash
mkdir -p /home/deploy/prompt-bot /home/deploy/backups /home/deploy/prompt-bot/logs
chown -R deploy:deploy /home/deploy
```

**4. Configure firewall:**
```bash
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw --force enable
```

### Post-Setup: Deploy Key Configuration

After running the setup script:

**1. Generate SSH key for deploy user:**
```bash
sudo -u deploy ssh-keygen -t ed25519 -C 'deploy@vps'
```

**2. Add public key to GitHub as deploy key:**
```bash
sudo -u deploy cat /home/deploy/.ssh/id_ed25519.pub
```
Copy the output and add it to your GitHub repository: Settings → Deploy keys → Add deploy key

**3. Clone repository:**
```bash
sudo -u deploy git clone git@github.com:YOUR_USER/YOUR_REPO.git /home/deploy/prompt-bot
```

**4. Create .env file:**
```bash
sudo -u deploy cp /home/deploy/prompt-bot/.env.example /home/deploy/prompt-bot/.env
sudo -u deploy nano /home/deploy/prompt-bot/.env
```

**5. Copy Google service key (if using Google Sheets logging):**
```bash
sudo -u deploy cp /path/to/google_service_key.json /home/deploy/prompt-bot/
```

---

## Deployment Workflow

### Initial Deployment

```bash
# As deploy user
cd /home/deploy/prompt-bot
./scripts/deploy.sh
```

### What the Deploy Script Does

The `scripts/deploy.sh` script performs:
1. Pulls latest code from git (`git pull origin main`)
2. Builds Docker images (keeps previous image for rollback)
3. Runs database migrations (`alembic upgrade head`)
4. Restarts services (`docker compose up -d`)
5. Verifies service health (retries up to 6 times)
6. Reports success or failure with clear error messages

### Manual Deployment Steps

If you need to deploy manually:

```bash
cd /home/deploy/prompt-bot

# Pull latest code
git pull origin main

# Build images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Run migrations
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm prompt-improver-bot alembic upgrade head

# Restart services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify health
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

### Rollback

If deployment fails, the previous Docker image is preserved:

```bash
# Rollback to previous image
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Or rollback database migration
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm prompt-improver-bot alembic downgrade -1
```

---

## Backup and Restore

### Automated Backups

The server setup configures daily automated backups:
- **Schedule:** Daily at 2:00 AM (cron)
- **Location:** `/home/deploy/backups/`
- **Format:** `botdb_YYYYMMDD_HHMMSS.sql.gz`
- **Retention:** 14 days (older backups auto-deleted)
- **Log:** `/home/deploy/backups/backup.log`

### Manual Backup

```bash
# Run backup script manually
/home/deploy/prompt-bot/scripts/backup-db.sh

# Or direct pg_dump
docker exec prompt-bot-postgres pg_dump -U botuser botdb | gzip > backup_$(date +%Y%m%d).sql.gz
```

### Restore from Backup

```bash
# Stop the bot (keep database running)
docker compose -f docker-compose.yml -f docker-compose.prod.yml stop prompt-improver-bot

# Restore database
gunzip -c /home/deploy/backups/botdb_YYYYMMDD_HHMMSS.sql.gz | docker exec -i prompt-bot-postgres psql -U botuser botdb

# Restart bot
docker compose -f docker-compose.yml -f docker-compose.prod.yml start prompt-improver-bot
```

### Redis Backup

Redis data is persisted via AOF (append-only file):
```bash
# Copy Redis data
docker cp prompt-bot-redis:/data/appendonly.aof ./redis-backup.aof
```

---

## Healthchecks and Monitoring

### Internal Healthcheck

The bot container includes a healthcheck that verifies Telegram API connectivity:

| Setting | Value |
|---------|-------|
| Interval | 60 seconds |
| Timeout | 15 seconds |
| Start period | 30 seconds |
| Retries | 3 |

The healthcheck script (`scripts/healthcheck.py`) calls the Telegram `getMe` API endpoint. If the API responds successfully, the container is marked healthy.

**Check container health status:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps
```

**View healthcheck logs:**
```bash
docker inspect prompt-improver-bot --format='{{json .State.Health}}' | jq
```

### Internal Healthcheck Limitations

The Docker healthcheck only monitors the container from inside the Docker host. It cannot detect:
- VPS network outages
- Docker daemon failures
- Complete server crashes
- Firewall blocking outbound traffic

**If the entire server goes down, the internal healthcheck cannot alert you.**

### External Monitoring with UptimeRobot

For comprehensive monitoring, set up external monitoring using UptimeRobot (free tier available):

**1. Create UptimeRobot account:**
- Go to [https://uptimerobot.com](https://uptimerobot.com)
- Sign up for a free account

**2. Add a new monitor:**
- Click "Add New Monitor"
- Monitor Type: **Ping** (or HTTP if you enable webhook mode)
- Friendly Name: `Prompt Bot VPS`
- IP or Host: Your VPS IP address
- Monitoring Interval: 5 minutes

**3. Configure alerts:**
- Add your email for notifications
- Optionally add Telegram notifications via UptimeRobot's Telegram integration

**4. For HTTP monitoring (webhook mode only):**
- Monitor Type: **HTTP(s)**
- URL: `http://YOUR_VPS_IP:8080/health` (requires webhook mode enabled)
- Monitoring Interval: 5 minutes

**Recommended monitoring strategy:**
- Use Ping monitor for basic server availability
- Use HTTP monitor if webhook mode is enabled
- Set up multiple alert contacts (email + Telegram)

---

## Webhook Mode

The bot runs in polling mode by default. To switch to webhook mode for better performance:

### Step 1: Uncomment Dockerfile EXPOSE

In `Dockerfile`, uncomment the EXPOSE directive:
```dockerfile
# Change this:
# EXPOSE 8080

# To this:
EXPOSE 8080
```

### Step 2: Uncomment Port Mapping

In `docker-compose.prod.yml`, uncomment the ports section:
```yaml
services:
  prompt-improver-bot:
    # Change this:
    # ports:
    #   - "8080:8080"
    
    # To this:
    ports:
      - "8080:8080"
```

### Step 3: Configure Reverse Proxy

Set up nginx or Caddy as a reverse proxy with SSL:

**Nginx example:**
```nginx
server {
    listen 443 ssl;
    server_name bot.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/bot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Step 4: Update Firewall

```bash
# Allow HTTPS traffic
ufw allow 443/tcp
```

### Step 5: Set Webhook URL

Configure your bot to use webhook mode by setting the webhook URL with Telegram:
```bash
curl "https://api.telegram.org/bot${TELEGRAM_TOKEN}/setWebhook?url=https://bot.yourdomain.com/webhook"
```

### Step 6: Rebuild and Deploy

```bash
./scripts/deploy.sh
```

---

## Troubleshooting

### Container Won't Start

**Check logs:**
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs prompt-improver-bot
```

**Common causes:**
- Missing `.env` file or required variables
- Invalid `TELEGRAM_TOKEN`
- Database not ready (check `depends_on` health conditions)

### Database Connection Failed

```bash
# Check PostgreSQL status
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps postgres
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs postgres

# Test connection
docker exec -it prompt-bot-postgres psql -U botuser -d botdb -c "SELECT 1;"
```

### Redis Connection Failed

```bash
# Check Redis status
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps redis
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs redis

# Test connection
docker exec -it prompt-bot-redis redis-cli -a "${REDIS_PASSWORD}" ping
```

### Healthcheck Failing

```bash
# Check healthcheck status
docker inspect prompt-improver-bot --format='{{json .State.Health}}'

# Run healthcheck manually
docker exec prompt-improver-bot python /app/scripts/healthcheck.py
echo $?  # 0 = healthy, 1 = unhealthy

# Common causes:
# - Invalid TELEGRAM_TOKEN
# - Network connectivity issues
# - Telegram API rate limiting
```

### Migration Failed

```bash
# Check migration status
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm prompt-improver-bot alembic current

# View migration history
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm prompt-improver-bot alembic history

# Rollback one migration
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm prompt-improver-bot alembic downgrade -1
```

### Backup Failed

```bash
# Check backup log
cat /home/deploy/backups/backup.log

# Common causes:
# - PostgreSQL container not running
# - Disk full
# - Permission issues

# Test backup manually
/home/deploy/prompt-bot/scripts/backup-db.sh
```

### High Memory Usage

```bash
# Check container resource usage
docker stats

# Redis memory is limited to 256MB by default
# Adjust in docker-compose.yml if needed:
# --maxmemory 512mb
```

### Logs Filling Disk

Production compose configures log rotation:
- Max size: 10MB per file
- Max files: 3

Bot logs are rotated by logrotate:
- Daily rotation
- 14 days retention
- Compressed

**Manual log cleanup:**
```bash
# Truncate bot log
truncate -s 0 /home/deploy/prompt-bot/logs/bot.log

# Clean Docker logs
docker system prune --volumes
```

### Service Status Commands

```bash
# View all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# View logs (follow mode)
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f

# View specific service logs
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f prompt-improver-bot

# Restart specific service
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart prompt-improver-bot

# Stop all services
docker compose -f docker-compose.yml -f docker-compose.prod.yml down

# Stop and remove volumes (WARNING: deletes data)
docker compose -f docker-compose.yml -f docker-compose.prod.yml down -v
```

---

## Security Considerations

### Secrets Management

- Never commit `.env` or `google_service_key.json` to version control
- Both files are in `.gitignore`
- Use strong, unique passwords for PostgreSQL and Redis
- Rotate credentials periodically

### Network Security

- UFW firewall allows only SSH by default
- Redis and PostgreSQL ports are not exposed in production
- Use SSH keys instead of passwords for server access

### Redis Hardening (Production)

The production compose file disables dangerous Redis commands:
- `SLAVEOF`, `REPLICAOF` - Prevents replication attacks
- `CONFIG` - Prevents runtime configuration changes
- `FLUSHALL` - Prevents data deletion

### Database Security

- PostgreSQL uses password authentication
- Connection is internal to Docker network only
- Regular backups with 14-day retention

---

## Quick Reference

### Common Commands

| Action | Command |
|--------|---------|
| Start (dev) | `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` |
| Start (prod) | `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d` |
| Stop | `docker compose -f docker-compose.yml -f docker-compose.prod.yml down` |
| Logs | `docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f` |
| Deploy | `./scripts/deploy.sh` |
| Backup | `./scripts/backup-db.sh` |
| Health | `docker compose -f docker-compose.yml -f docker-compose.prod.yml ps` |

### File Locations (Production)

| Item | Path |
|------|------|
| Application | `/home/deploy/prompt-bot/` |
| Environment | `/home/deploy/prompt-bot/.env` |
| Logs | `/home/deploy/prompt-bot/logs/bot.log` |
| Backups | `/home/deploy/backups/` |
| Backup log | `/home/deploy/backups/backup.log` |
