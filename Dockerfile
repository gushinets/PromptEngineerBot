# Use official Python image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy requirements and source code
COPY requirements.txt .
COPY .env .
COPY main.py .
COPY openai_client.py .
COPY openrouter_client.py .
COPY state_manager.py .
COPY conversation_manager.py .
COPY prompts ./prompts

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port (if needed, e.g. for webhook)
# EXPOSE 8080

# Run the bot
CMD ["python", "main.py"]
