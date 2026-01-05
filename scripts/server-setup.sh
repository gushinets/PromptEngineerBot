#!/bin/bash
# VPS Server Setup Script for Ubuntu 22+
# Run as root or with sudo
#
# Requirements: 5.5, 6.2, 6.3, 6.4, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8
# - Installs Docker and Docker Compose on Ubuntu 22+
# - Creates deploy user with docker group membership
# - Creates required directories (app, backups, logs)
# - Configures UFW firewall to allow SSH only
# - Enables Docker to start on system boot
# - Configures logrotate for bot.log (daily, 14 days, compress, copytruncate)
# - Sets up cron job for daily backups at 2:00 AM
# - Outputs next steps for SSH deploy key setup

set -e

# Configuration
# Use the user who invoked sudo (or current user if not using sudo)
APP_USER="${SUDO_USER:-$(whoami)}"
APP_HOME=$(getent passwd "$APP_USER" | cut -d: -f6)
APP_DIR="$APP_HOME/prompt-bot"
BACKUP_DIR="$APP_HOME/backups"
LOG_DIR="$APP_HOME/prompt-bot/logs"

echo "=== Prompt Bot VPS Setup ==="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: This script must be run as root or with sudo"
    exit 1
fi

# Check Ubuntu version
if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        echo "WARNING: This script is designed for Ubuntu. Detected: $ID"
        echo "Proceeding anyway..."
    fi
    UBUNTU_VERSION="${VERSION_ID%%.*}"
    if [ "$UBUNTU_VERSION" -lt 22 ] 2>/dev/null; then
        echo "WARNING: Ubuntu 22+ recommended. Detected: $VERSION_ID"
    fi
fi

# Update system packages
echo "[1/8] Updating system packages..."
apt-get update && apt-get upgrade -y

# Install Docker (Requirement 7.1)
echo "[2/8] Installing Docker..."
apt-get install -y ca-certificates curl gnupg

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
fi

# Add Docker repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Enable Docker on boot (Requirement 7.5)
echo "[3/8] Enabling Docker on boot..."
systemctl enable docker
systemctl start docker

# Add current user to docker group (Requirement 7.2)
echo "[4/8] Configuring user for Docker access..."
usermod -aG docker "$APP_USER"
echo "Added $APP_USER to docker group"
echo "NOTE: User may need to log out and back in for docker group to take effect"

# Create directories (Requirement 7.3)
echo "[5/8] Creating directories..."
mkdir -p "$APP_DIR" "$BACKUP_DIR" "$LOG_DIR"
chown -R "$APP_USER:$APP_USER" "$APP_DIR" "$BACKUP_DIR"
echo "Created directories:"
echo "  - $APP_DIR"
echo "  - $BACKUP_DIR"
echo "  - $LOG_DIR"

# Configure UFW firewall (Requirement 7.4)
echo "[6/8] Configuring firewall..."
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw --force enable
echo "Firewall configured: SSH allowed, all other incoming blocked"


# Configure logrotate for bot logs (Requirements 6.2, 6.3, 6.4, 6.5)
echo "[7/8] Configuring logrotate..."
cat > /etc/logrotate.d/prompt-bot << EOF
$LOG_DIR/bot.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    copytruncate
    create 644 $APP_USER $APP_USER
}
EOF
echo "Logrotate configured: daily rotation, 14 days retention, compressed"

# Setup backup cron job (Requirement 5.5, 7.7)
echo "[8/8] Setting up backup cron..."
CRON_CMD="0 2 * * * $APP_DIR/scripts/backup-db.sh"
# Remove existing backup-db.sh entry if present, then add new one
(crontab -u "$APP_USER" -l 2>/dev/null | grep -v "backup-db.sh"; echo "$CRON_CMD") | crontab -u "$APP_USER" -
echo "Cron job configured: daily backup at 2:00 AM"

echo ""
echo "=== Setup Complete ==="
echo ""
echo "Next steps for SSH deploy key setup (Requirement 7.8):"
echo ""
echo "1. Generate SSH key for $APP_USER:"
echo "   ssh-keygen -t ed25519 -C '$APP_USER@vps'"
echo ""
echo "2. Add the public key to your GitHub repo as a deploy key:"
echo "   cat $APP_HOME/.ssh/id_ed25519.pub"
echo ""
echo "3. Clone your repository:"
echo "   git clone git@github.com:YOUR_USER/YOUR_REPO.git $APP_DIR"
echo ""
echo "4. Create .env file with your secrets:"
echo "   cp $APP_DIR/.env.example $APP_DIR/.env"
echo "   nano $APP_DIR/.env"
echo ""
echo "5. Copy google_service_key.json to the app directory:"
echo "   cp /path/to/google_service_key.json $APP_DIR/"
echo ""
echo "6. Log out and back in (for docker group), then run the deploy script:"
echo "   $APP_DIR/scripts/deploy.sh"
echo ""
echo "=== Server Information ==="
echo "App user: $APP_USER"
echo "App directory: $APP_DIR"
echo "Backup directory: $BACKUP_DIR"
echo "Log directory: $LOG_DIR"
echo "Backup schedule: Daily at 2:00 AM"
echo "Log rotation: Daily, 14 days retention"
