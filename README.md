
# Telegram Bot with OpenRouter & OpenAI Integration

A Telegram bot that processes user prompts through OpenRouter or OpenAI API, with full conversation context.

## Setup


### Local Setup

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2. Create a `.env` file with your credentials:
    ```
    TELEGRAM_TOKEN=your_telegram_token
    OPENROUTER_API_KEY=your_openrouter_api_key
    OPENAI_API_KEY=your_openai_api_key
    MODEL_NAME=your_preferred_model
    INITIAL_PROMPT=your_system_prompt
    LLM_BACKEND=OPENROUTER  # or OPENAI
    ```

3. Run the bot:
    ```bash
    python main.py
    ```

### Docker Deployment

1. Build the Docker image:
    ```bash
    docker build -t prompt-improver-bot .
    ```

2. Run the container (using your .env file):
    ```bash
    docker run --env-file .env prompt-improver-bot
    ```

### Docker Compose Deployment

1. Make sure your `.env` file is present in the project root.
2. Start the bot with Docker Compose:
    ```bash
    docker compose up --build
    ```

## Features

- Processes user prompts through OpenRouter or OpenAI API
- Maintains full conversation transcript for context
- Simple in-memory state management
- Easily switch backend via `.env` (OpenRouter or OpenAI)
