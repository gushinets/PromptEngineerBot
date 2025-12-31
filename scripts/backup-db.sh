#!/bin/bash
# Database backup script with 14-day retention
# Run via cron: 0 2 * * * /home/deploy/prompt-bot/scripts/backup-db.sh
#
# Requirements: 5.1, 5.2, 5.3, 5.4, 5.6
# - Implements pg_dump with gzip compression
# - Stores backups in /home/deploy/backups directory
# - Deletes backups older than 14 days
# - Logs success or failure to backup.log

set -e

# Configuration
BACKUP_DIR="${BACKUP_DIR:-/home/deploy/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/botdb_$TIMESTAMP.sql.gz"
LOG_FILE="$BACKUP_DIR/backup.log"
RETENTION_DAYS=14

# Container and database settings (can be overridden via environment)
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-prompt-bot-postgres}"
DB_USER="${POSTGRES_USER:-botuser}"
DB_NAME="${POSTGRES_DB:-botdb}"

# Ensure backup directory exists
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

log "Starting backup..."

# Run pg_dump inside postgres container and compress with gzip
if docker exec "$POSTGRES_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup completed: $BACKUP_FILE ($BACKUP_SIZE)"
else
    log "ERROR: Backup failed!"
    exit 1
fi

# Delete old backups (older than 14 days)
DELETED=$(find "$BACKUP_DIR" -name "botdb_*.sql.gz" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    log "Deleted $DELETED old backup(s) (older than $RETENTION_DAYS days)"
fi

log "Backup process completed"
