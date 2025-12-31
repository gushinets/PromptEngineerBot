# Requirements Document

## Introduction

This specification covers improvements to the Docker configuration for the Prompt Engineering Bot. The goal is to enhance security, establish proper dev/prod separation, implement automated backups, improve healthchecks, and create deployment automation for a VPS running Ubuntu 22+.

## Glossary

- **Bot**: The Telegram Prompt Engineering Bot application
- **VPS**: Virtual Private Server running Ubuntu 22+ where production deployment occurs
- **Compose_Base**: The base docker-compose.yml file with shared configuration
- **Compose_Dev**: Development-specific docker-compose.dev.yml overrides
- **Compose_Prod**: Production-specific docker-compose.prod.yml overrides
- **Healthcheck**: Automated verification that the Bot is functioning correctly
- **Deploy_Script**: Shell script that deploys updates to the VPS
- **Setup_Script**: Shell script that performs initial VPS server configuration

## Requirements

### Requirement 1: Remove Secrets from Docker Image

**User Story:** As a developer, I want secrets excluded from the Docker image, so that credentials are not exposed if the image is shared or inspected.

#### Acceptance Criteria

1. WHEN the Dockerfile is built, THE Bot SHALL NOT copy .env files into the image
2. WHEN the Dockerfile is built, THE Bot SHALL NOT copy google_service_key.json into the image
3. WHEN the Bot container runs, THE Compose_Base SHALL mount google_service_key.json as a read-only volume
4. WHEN the Bot container runs, THE Compose_Base SHALL load environment variables via env_file directive only

### Requirement 2: Externalize Database Credentials

**User Story:** As a developer, I want database credentials stored in environment variables, so that passwords are not hardcoded in configuration files.

#### Acceptance Criteria

1. THE Compose_Base SHALL reference POSTGRES_PASSWORD from environment variable substitution
2. THE Compose_Base SHALL reference POSTGRES_USER from environment variable substitution
3. THE Compose_Base SHALL construct DATABASE_URL using environment variable substitution
4. WHEN .env file is missing required database variables, THE Bot SHALL fail to start with a clear error

### Requirement 3: Three-File Compose Structure

**User Story:** As a developer, I want separate compose files for base, dev, and prod configurations, so that environment-specific settings are clearly separated.

#### Acceptance Criteria

1. THE Compose_Base SHALL contain shared service definitions for bot, redis, and postgres
2. THE Compose_Dev SHALL expose Redis port 6379 for local development tools
3. THE Compose_Dev SHALL expose Postgres port 5432 for local development tools
4. THE Compose_Dev SHALL use restart policy "unless-stopped"
5. THE Compose_Prod SHALL NOT expose Redis or Postgres ports externally
6. THE Compose_Prod SHALL use restart policy "always"
7. THE Compose_Prod SHALL configure Docker json-file logging with rotation (10MB max, 3 files)
8. WHEN running in development, THE Bot SHALL be started with "docker compose -f docker-compose.yml -f docker-compose.dev.yml up"
9. WHEN running in production, THE Bot SHALL be started with "docker compose -f docker-compose.yml -f docker-compose.prod.yml up"

### Requirement 4: Telegram API Healthcheck

**User Story:** As an operator, I want the bot container to verify Telegram API connectivity, so that Docker can automatically restart unhealthy containers.

#### Acceptance Criteria

1. THE Bot SHALL include a healthcheck script that calls Telegram getMe API
2. WHEN the Telegram API responds successfully, THE Healthcheck SHALL exit with code 0
3. WHEN the Telegram API fails or times out, THE Healthcheck SHALL exit with code 1
4. THE Dockerfile SHALL configure HEALTHCHECK to run the script every 60 seconds
5. THE Dockerfile SHALL allow 30 seconds start period before first healthcheck
6. THE Dockerfile SHALL retry healthcheck 3 times before marking unhealthy

### Requirement 5: Automated Database Backups

**User Story:** As an operator, I want automated daily database backups with retention policy, so that data can be recovered if needed.

#### Acceptance Criteria

1. THE Setup_Script SHALL create a backup script that runs pg_dump on the postgres container
2. THE Backup_Script SHALL compress backups using gzip
3. THE Backup_Script SHALL store backups in /home/deploy/backups directory
4. THE Backup_Script SHALL delete backups older than 14 days
5. THE Setup_Script SHALL configure cron to run backups daily at 2:00 AM
6. WHEN backup completes, THE Backup_Script SHALL log success or failure

### Requirement 6: Log File Persistence and Rotation

**User Story:** As an operator, I want bot logs persisted and rotated automatically, so that logs are available for debugging without filling disk space.

#### Acceptance Criteria

1. THE Compose_Base SHALL mount a logs volume for bot.log persistence
2. THE Setup_Script SHALL configure logrotate for bot.log with daily rotation
3. THE Logrotate_Config SHALL retain 14 days of logs
4. THE Logrotate_Config SHALL compress rotated logs
5. THE Logrotate_Config SHALL use copytruncate to avoid requiring bot restart

### Requirement 7: VPS Server Setup Script

**User Story:** As an operator, I want a setup script for fresh VPS installation, so that server configuration is automated and repeatable.

#### Acceptance Criteria

1. THE Setup_Script SHALL install Docker and Docker Compose on Ubuntu 22+
2. THE Setup_Script SHALL create a deploy user with appropriate permissions
3. THE Setup_Script SHALL create required directories (app, backups, logs)
4. THE Setup_Script SHALL configure UFW firewall to allow SSH and block unnecessary ports
5. THE Setup_Script SHALL enable Docker to start on system boot
6. THE Setup_Script SHALL configure logrotate for bot logs
7. THE Setup_Script SHALL set up cron job for database backups
8. THE Setup_Script SHALL provide instructions for SSH deploy key setup

### Requirement 8: Deployment Script

**User Story:** As an operator, I want a deployment script that updates the bot, so that deployments are consistent and automated.

#### Acceptance Criteria

1. THE Deploy_Script SHALL pull latest code from git repository
2. THE Deploy_Script SHALL build Docker images
3. THE Deploy_Script SHALL run database migrations automatically
4. THE Deploy_Script SHALL restart services with zero-downtime approach where possible
5. THE Deploy_Script SHALL verify service health after deployment
6. WHEN deployment fails, THE Deploy_Script SHALL output clear error messages
7. THE Deploy_Script SHALL support rollback by keeping previous image

### Requirement 9: Webhook-Ready Configuration

**User Story:** As a developer, I want webhook configuration prepared but commented out, so that switching from polling to webhook mode is straightforward.

#### Acceptance Criteria

1. THE Dockerfile SHALL include commented EXPOSE directive for webhook port 8080
2. THE Compose_Prod SHALL include commented port mapping for webhook
3. THE Documentation SHALL explain steps to enable webhook mode

### Requirement 10: External Monitoring Documentation

**User Story:** As an operator, I want documentation for external monitoring setup, so that I'm alerted when the entire server is down.

#### Acceptance Criteria

1. THE Documentation SHALL explain the limitation of internal-only healthchecks
2. THE Documentation SHALL provide setup instructions for UptimeRobot or similar service
3. THE Documentation SHALL recommend monitoring the VPS IP address

### Requirement 11: Updated Deployment Documentation

**User Story:** As a developer, I want comprehensive deployment documentation, so that the deployment process is clear and follows the new configuration model.

#### Acceptance Criteria

1. THE Documentation SHALL describe the 3-file compose structure
2. THE Documentation SHALL provide complete .env variable reference
3. THE Documentation SHALL include step-by-step VPS setup instructions
4. THE Documentation SHALL include deployment workflow instructions
5. THE Documentation SHALL include backup and restore procedures
6. THE Documentation SHALL include troubleshooting guide
7. THE Documentation SHALL replace the existing DEPLOYMENT.md completely
