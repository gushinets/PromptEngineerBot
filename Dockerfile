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

# Copy application files
COPY .env* ./
COPY google_service_key.json* ./
COPY src ./src
COPY run_bot.py .

# Change ownership to app user
RUN chown -R app:app /app

# Switch to non-root user
USER app

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import os; exit(0 if os.getenv('TELEGRAM_TOKEN') else 1)"

# Expose port (if needed, e.g. for webhook)
# EXPOSE 8080

# Run the bot using the new entry point
CMD ["python", "run_bot.py"]
