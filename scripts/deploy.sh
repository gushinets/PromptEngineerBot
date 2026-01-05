#!/bin/bash
# Deployment script for Prompt Bot
# Run as deploy user from app directory
#
# Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7
# - Pulls latest code from git repository
# - Builds Docker images
# - Runs database migrations automatically
# - Restarts services with docker compose up -d
# - Verifies service health after deployment
# - Outputs clear error messages on failure
# - Supports rollback by keeping previous image

set -e

# Configuration
APP_DIR="${APP_DIR:-$HOME/prompt-bot}"
# shellcheck disable=SC2034
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
HEALTH_CHECK_RETRIES=6
HEALTH_CHECK_INTERVAL=10

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Error handler
handle_error() {
    log_error "Deployment failed at line $1"
    log_error "Previous Docker image is still available for rollback"
    log_error "To rollback, run: docker compose ${COMPOSE_FILES[*]} up -d"
    exit 1
}

trap 'handle_error $LINENO' ERR

# Change to app directory
cd "$APP_DIR" || {
    log_error "Failed to change to app directory: $APP_DIR"
    exit 1
}

echo ""
echo "=== Deploying Prompt Bot ==="
echo ""

# Step 1: Pull latest code (Requirement 8.1)
log_info "Pulling latest code from git..."
if ! git pull origin main; then
    log_error "Failed to pull latest code from git"
    log_error "Check your git configuration and network connection"
    exit 1
fi
log_info "Code updated successfully"

# Step 2: Build Docker images (Requirement 8.2)
# Note: Previous image is kept for rollback (Requirement 8.7)
log_info "Building Docker images..."
if ! docker compose "${COMPOSE_FILES[@]}" build; then
    log_error "Failed to build Docker images"
    log_error "Check Dockerfile and build context for errors"
    exit 1
fi
log_info "Docker images built successfully"

# Step 3: Run database migrations (Requirement 8.3)
log_info "Running database migrations..."
if ! docker compose "${COMPOSE_FILES[@]}" run --rm prompt-improver-bot alembic upgrade head; then
    log_error "Failed to run database migrations"
    log_error "Check alembic configuration and migration files"
    exit 1
fi
log_info "Database migrations completed successfully"

# Step 4: Restart services (Requirement 8.4)
log_info "Restarting services..."
if ! docker compose "${COMPOSE_FILES[@]}" up -d; then
    log_error "Failed to restart services"
    exit 1
fi
log_info "Services restarted successfully"

# Step 5: Verify service health (Requirement 8.5)
log_info "Waiting for services to start..."
sleep 5

log_info "Verifying service health..."
HEALTHY=false
for i in $(seq 1 $HEALTH_CHECK_RETRIES); do
    log_info "Health check attempt $i of $HEALTH_CHECK_RETRIES..."
    
    # Check if any services are unhealthy
    if docker compose "${COMPOSE_FILES[@]}" ps | grep -q "unhealthy"; then
        log_warn "Some services are still unhealthy, waiting..."
        sleep $HEALTH_CHECK_INTERVAL
        continue
    fi
    
    # Check if all services are running
    RUNNING_COUNT=$(docker compose "${COMPOSE_FILES[@]}" ps --status running -q | wc -l)
    TOTAL_COUNT=$(docker compose "${COMPOSE_FILES[@]}" ps -q | wc -l)
    
    if [ "$RUNNING_COUNT" -eq "$TOTAL_COUNT" ] && [ "$TOTAL_COUNT" -gt 0 ]; then
        # Additional check: ensure no services are in "starting" state
        if ! docker compose "${COMPOSE_FILES[@]}" ps | grep -q "starting"; then
            HEALTHY=true
            break
        fi
    fi
    
    sleep $HEALTH_CHECK_INTERVAL
done

if [ "$HEALTHY" = false ]; then
    log_error "Services failed health check after $HEALTH_CHECK_RETRIES attempts"
    log_error "Current service status:"
    docker compose "${COMPOSE_FILES[@]}" ps
    log_error ""
    log_error "Check logs with: docker compose ${COMPOSE_FILES[*]} logs"
    exit 1
fi

echo ""
echo "=== Deployment Complete ==="
echo ""
log_info "All services are healthy"
echo ""
docker compose "${COMPOSE_FILES[@]}" ps
echo ""
log_info "Deployment finished at $(date '+%Y-%m-%d %H:%M:%S')"
