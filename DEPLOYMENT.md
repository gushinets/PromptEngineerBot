# Deployment Guide

This guide covers deploying the Prompt Engineering Bot with email authentication features.

## Prerequisites

- Docker and Docker Compose installed
- Telegram bot token from @BotFather
- SMTP credentials (e.g., SMTP-Pulse account)
- LLM API key (OpenAI or OpenRouter)

## Quick Start

1. **Clone and configure**:
   ```bash
   git clone <repository>
   cd prompt-engineering-bot
   cp .env.example .env
   ```

2. **Edit `.env` file** with your credentials:
   ```bash
   # Required settings
   TELEGRAM_TOKEN=your_telegram_token
   OPENROUTER_API_KEY=your_openrouter_key  # or OPENAI_API_KEY
   SMTP_USERNAME=your_smtp_username
   SMTP_PASSWORD=your_smtp_password
   SMTP_FROM_EMAIL=noreply@yourdomain.com
   ```

3. **Start services**:
   ```bash
   docker compose up -d
   ```

4. **Run database migrations** (choose one):
   - Option A — from host (recommended):
     ```bash
     python -m venv .venv
     .venv/Scripts/pip install -r requirements.txt
     $env:DATABASE_URL = "postgresql://botuser:botpass@localhost:5432/botdb"
     .venv/Scripts/alembic upgrade head
     ```
   - Option B — one-off container with repo bind-mounted (Windows PowerShell):
     ```bash
     docker compose run --rm -v ${PWD}:/app prompt-improver-bot alembic upgrade head
     ```

## Configuration Options

### Email Feature Toggle

To disable email features entirely:
```bash
EMAIL_ENABLED=false
```

### Database Options

**Development (SQLite)**:
```bash
DATABASE_URL=sqlite:///./bot.db
```

**Production (PostgreSQL)**:
```bash
DATABASE_URL=postgresql://botuser:botpass@postgres:5432/botdb
```

### SMTP Configuration

**SMTP-Pulse (recommended)**:
```bash
SMTP_HOST=smtp-pulse.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

**Gmail SMTP**:
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false
```

**Custom SMTP with SSL**:
```bash
SMTP_HOST=your-smtp-server.com
SMTP_PORT=465
SMTP_USE_TLS=false
SMTP_USE_SSL=true
```

### Rate Limiting

Adjust rate limits based on your needs:
```bash
EMAIL_RATE_LIMIT_PER_HOUR=3    # Max OTP emails per email address per hour
USER_RATE_LIMIT_PER_HOUR=5     # Max OTP emails per user per hour
OTP_SPACING_SECONDS=60         # Minimum seconds between OTP sends
```

## Database Migrations

### Initial Setup

After first deployment, run migrations (pick one method):
```bash
# A) Host-based (recommended)
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
$env:DATABASE_URL="postgresql://botuser:botpass@localhost:5432/botdb"
.venv/Scripts/alembic upgrade head

# B) One-off container with repo bind-mounted (Windows PowerShell)
docker compose run --rm -v ${PWD}:/app prompt-improver-bot alembic upgrade head

or
docker-compose exec prompt-improver-bot python -m alembic upgrade head
```

### User Profile Fields Migration

The bot includes enhanced user profiling with Telegram profile data:

**New Profile Fields Added:**
- `first_name`: User's first name from Telegram
- `last_name`: User's last name from Telegram  
- `is_bot`: Boolean indicating bot accounts
- `is_premium`: Telegram Premium subscription status
- `language_code`: User's language preference (ISO 639-1)

**Performance Indexes:**
- `ix_users_language_code`: Language-based user queries
- `ix_users_is_premium`: Premium user filtering
- `ix_users_bot_premium`: Composite index for user analytics

**Migration Safety:**
- All new fields are nullable or have defaults for backward compatibility
- Existing user data is preserved during migration
- Profile data is captured automatically during user interactions

### Creating New Migrations

When modifying database models:
```bash
# Generate migration
docker-compose exec prompt-improver-bot python -m alembic revision --autogenerate -m "Description"

# Apply migration
docker-compose exec prompt-improver-bot python -m alembic upgrade head
```

### Migration Rollback

To rollback to previous version:
```bash
# Rollback one version
docker-compose exec prompt-improver-bot python -m alembic downgrade -1

# Rollback to specific revision
docker-compose exec prompt-improver-bot python -m alembic downgrade <revision_id>
```

## Monitoring and Health Checks

### Health Check Endpoints

The bot includes built-in health monitoring for:
- Database connectivity
- Redis connectivity  
- SMTP server connectivity

### Logs

View bot logs:
```bash
docker compose logs -f prompt-improver-bot
```

View service logs:
```bash
docker compose logs -f redis postgres
```

### Metrics

The bot collects metrics for:
- OTP generation and verification rates
- Email delivery success/failure rates
- LLM and SMTP response times
- Authentication success rates

## Security Considerations

### Environment Variables

Never commit sensitive data to version control:
- Keep `.env` file in `.gitignore`
- Use secrets management in production
- Rotate credentials regularly

### Database Security

- Use strong passwords for PostgreSQL
- Enable SSL/TLS for database connections in production
- Regularly backup database

### SMTP Security

- Use app-specific passwords for Gmail
- Enable 2FA on SMTP provider accounts
- Monitor email sending quotas

### Redis Security

- Use Redis AUTH in production
- Configure Redis to bind to localhost only
- Set memory limits to prevent DoS

## Production Deployment

### Docker Compose Production

Create `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  prompt-improver-bot:
    build: .
    restart: always
    env_file:
      - .env.prod
    depends_on:
      - redis
      - postgres
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  redis:
    image: redis:7-alpine
    restart: always
    command: redis-server --requirepass ${REDIS_PASSWORD} --appendonly yes
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15-alpine
    restart: always
    environment:
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
```

### Environment-Specific Configuration

Create separate environment files:
- `.env.dev` - Development settings
- `.env.staging` - Staging environment
- `.env.prod` - Production settings

### SSL/TLS Configuration

For production, configure SSL certificates:
```bash
# Mount SSL certificates
volumes:
  - ./ssl:/app/ssl:ro

# Update environment
SSL_CERT_PATH=/app/ssl/cert.pem
SSL_KEY_PATH=/app/ssl/key.pem
```

## Troubleshooting

### Common Issues

**Database connection failed**:
```bash
# Check PostgreSQL status
docker compose ps postgres
docker compose logs postgres

# Test connection
docker compose exec postgres psql -U botuser -d botdb -c "SELECT 1;"
```

**Redis connection failed**:
```bash
# Check Redis status
docker compose ps redis
docker compose logs redis

# Test connection
docker compose exec redis redis-cli ping
```

**SMTP authentication failed**:
```bash
# Test SMTP connection
docker compose exec prompt-improver-bot python -c "
from src.email_service import EmailService
from src.config import BotConfig
config = BotConfig.from_env()
service = EmailService(config)
print('SMTP test:', service._check_smtp_health())
"
```

**Email delivery failed**:
- Check SMTP credentials and quotas
- Verify sender email domain reputation
- Check spam filters and blacklists

### Performance Issues

**High memory usage**:
- Reduce Redis memory limit
- Adjust database connection pool size
- Monitor background task frequency

**Slow response times**:
- Check LLM API response times
- Monitor database query performance
- Verify network connectivity

### Log Analysis

**Find authentication issues**:
```bash
docker compose logs prompt-improver-bot | grep "OTP_"
```

**Monitor email delivery**:
```bash
docker compose logs prompt-improver-bot | grep "EMAIL_"
```

**Check health status**:
```bash
docker compose logs prompt-improver-bot | grep "HEALTH_"
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
docker compose exec postgres pg_dump -U botuser botdb > backup.sql

# Restore backup
docker compose exec -T postgres psql -U botuser botdb < backup.sql
```

### Redis Backup

```bash
# Redis automatically saves to /data/dump.rdb
# Copy backup file
docker cp prompt-bot-redis:/data/dump.rdb ./redis-backup.rdb
```

### Full System Backup

```bash
# Stop services
docker compose down

# Backup volumes
docker run --rm -v prompt-engineering-bot_postgres_data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz -C /data .
docker run --rm -v prompt-engineering-bot_redis_data:/data -v $(pwd):/backup alpine tar czf /backup/redis-backup.tar.gz -C /data .

# Restart services
docker compose up -d
```

## Run Production-like Locally

Use only the base compose file to mimic production:

1. Ensure `.env` contains required values (`TELEGRAM_TOKEN`, LLM backend/API key, SMTP if `EMAIL_ENABLED=true`).
2. Pre-create the log file on host to avoid directory bind issues:
   ```bash
   # PowerShell
   if (Test-Path .\bot.log) { Remove-Item -Force .\bot.log }
   New-Item -ItemType File .\bot.log | Out-Null
   ```
3. Start infrastructure:
   ```bash
   docker compose -f docker-compose.yml up -d postgres redis
   ```
4. Run migrations (see Quick Start step 4 for options). Host-based example:
   ```bash
   python -m venv .venv
   .venv/Scripts/pip install -r requirements.txt
   $env:DATABASE_URL = "postgresql://botuser:botpass@localhost:5432/botdb"
   .venv/Scripts/alembic upgrade head
   ```
5. Start the app:
   ```bash
   docker compose -f docker-compose.yml up -d prompt-improver-bot
   ```
6. Verify:
   ```bash
   docker compose -f docker-compose.yml ps
   docker compose -f docker-compose.yml logs -f prompt-improver-bot
   ```

### Prod-like Local Troubleshooting

- bot.log mount error (IsADirectoryError): Ensure `./bot.log` exists as a file before `docker compose up`. See step 2.
- Stale image (outdated sources):
  ```bash
  docker compose -f docker-compose.yml up -d --build --force-recreate
  # or, to force a clean rebuild
  docker compose -f docker-compose.yml build --no-cache --pull prompt-improver-bot
  docker compose -f docker-compose.yml up -d --force-recreate prompt-improver-bot
  ```
- Compose warning about `version` key: Safe to ignore on Compose V2, or remove the `version:` line from `docker-compose.yml` to silence the warning.

## Support

For issues and questions:
1. Check logs for error messages
2. Verify configuration settings
3. Test individual components (database, Redis, SMTP)
4. Review security settings and credentials
5. Monitor resource usage and performance metrics