# Implementation Plan: Docker Configuration Improvements

## Overview

This plan implements security improvements, environment separation, operational automation, and documentation updates for the Docker configuration. Tasks are ordered to build incrementally, with each step validating before proceeding.

## Tasks

- [x] 1. Update Dockerfile to remove secrets and add healthcheck
  - [x] 1.1 Remove COPY .env* and COPY google_service_key.json* lines from Dockerfile
    - Remove lines that copy secrets into the image
    - Keep only application code copies
    - _Requirements: 1.1, 1.2_
  - [x] 1.2 Create healthcheck script at scripts/healthcheck.py
    - Implement Telegram API ping using httpx with urllib fallback
    - Exit 0 on success, 1 on failure
    - Handle timeout gracefully
    - _Requirements: 4.1, 4.2, 4.3_
  - [x] 1.3 Add COPY for healthcheck script and update HEALTHCHECK directive in Dockerfile
    - Copy scripts/healthcheck.py to /app/scripts/
    - Configure HEALTHCHECK with 60s interval, 30s start-period, 3 retries
    - Add commented EXPOSE 8080 for webhook readiness
    - _Requirements: 4.4, 4.5, 4.6, 9.1_
  - [x] 1.4 Write property tests for healthcheck script

    - **Property 2: Healthcheck Failure on Invalid/Missing Token**
    - **Validates: Requirements 4.1, 4.3**

- [x] 2. Restructure Docker Compose files to 3-file pattern
  - [x] 2.1 Update docker-compose.yml as base configuration
    - Remove hardcoded passwords, use ${POSTGRES_PASSWORD}, ${POSTGRES_USER}, ${POSTGRES_DB}
    - Add depends_on with condition: service_healthy for bot
    - Add logs volume mount for bot.log persistence
    - Remove port exposures (move to dev file)
    - _Requirements: 1.3, 1.4, 2.1, 2.2, 2.3, 3.1, 6.1_
  - [x] 2.2 Rename docker-compose.override.yml to docker-compose.dev.yml
    - Configure restart: unless-stopped for all services
    - Add port exposures: Redis 6379, Postgres 5432
    - Add LOG_LEVEL=DEBUG environment variable
    - _Requirements: 3.2, 3.3, 3.4_
  - [x] 2.3 Create docker-compose.prod.yml for production settings
    - Configure restart: always for all services
    - Add json-file logging driver with max-size: 10m, max-file: 3
    - Add hardened Redis command with renamed dangerous commands
    - Add commented webhook port mapping
    - _Requirements: 3.5, 3.6, 3.7, 9.2_

- [x] 3. Checkpoint - Verify Docker configuration
  - Build image and verify no secrets inside
  - Test dev compose starts with exposed ports
  - Test prod compose starts without exposed ports
  - Verify healthcheck transitions to healthy
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Create operational scripts
  - [x] 4.1 Create backup script at scripts/backup-db.sh
    - Implement pg_dump with gzip compression
    - Configure 14-day retention with find -mtime +14 -delete
    - Add logging to backup.log
    - Make script executable
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_
  - [x] 4.2 Create server setup script at scripts/server-setup.sh
    - Install Docker and Docker Compose on Ubuntu 22+
    - Create deploy user with docker group membership
    - Create directories: app, backups, logs
    - Configure UFW firewall (allow SSH only)
    - Enable Docker on boot
    - Configure logrotate for bot.log (daily, 14 days, compress, copytruncate)
    - Set up cron job for daily backups at 2:00 AM
    - Output next steps for SSH deploy key setup
    - _Requirements: 5.5, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_
  - [x] 4.3 Create deployment script at scripts/deploy.sh
    - Pull latest code from git
    - Build Docker images
    - Run alembic migrations
    - Restart services with docker compose up -d
    - Verify service health after deployment
    - Exit with error on any failure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [x] 5. Update environment configuration
  - [x] 5.1 Update .env.example with all required variables
    - Add POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
    - Add REDIS_PASSWORD
    - Add LOG_LEVEL
    - Document all variables with comments
    - _Requirements: 2.1, 2.2, 2.4_
  - [x] 5.2 Update .gitignore to ensure secrets are not committed
    - Verify .env is ignored
    - Verify google_service_key.json is ignored
    - Add backups/ directory to ignore
    - _Requirements: 1.1, 1.2_

- [x] 6. Checkpoint - Verify scripts work correctly
  - Test backup script creates compressed backup file
  - Verify setup script syntax with shellcheck
  - Verify deploy script syntax with shellcheck
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Rewrite deployment documentation
  - [x] 7.1 Create new DEPLOYMENT.md with complete rewrite
    - Document 3-file compose structure and usage
    - Provide complete .env variable reference
    - Include step-by-step VPS setup instructions
    - Include deployment workflow instructions
    - Document backup and restore procedures
    - Include troubleshooting guide
    - Explain internal vs external healthcheck limitations
    - Provide UptimeRobot setup instructions for external monitoring
    - Document steps to enable webhook mode
    - _Requirements: 9.3, 10.1, 10.2, 10.3, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7_

- [x] 8. Final checkpoint - Complete verification
  - Review all files for consistency
  - Verify documentation matches implementation
  - Test full deployment workflow locally
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate healthcheck correctness
- Shell scripts should be tested with shellcheck before deployment
