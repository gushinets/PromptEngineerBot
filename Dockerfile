# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies if needed
RUN apt-get update && apt-get install -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app

# Copy application files (secrets are mounted at runtime, not copied into image)
COPY alembic.ini .
COPY alembic ./alembic
COPY telegram_bot ./telegram_bot
COPY run_bot.py .
COPY scripts/healthcheck.py ./scripts/

# Change ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Healthcheck using Telegram API ping
# Requirements: 4.4, 4.5, 4.6
HEALTHCHECK --interval=60s --timeout=15s --start-period=30s --retries=3 \
    CMD python /app/scripts/healthcheck.py

# Webhook port (uncomment when switching to webhook mode)
# Requirement: 9.1
# EXPOSE 8080

# Run the bot using the new entry point
CMD ["python", "run_bot.py"]
