
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

    # Optional: Google Sheets logging via gspread
    GSHEETS_LOGGING_ENABLED=true
    # One of the following two auth methods:
    # 1) Raw service account JSON (escape newlines or store as single-line JSON)
    # GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
    # 2) Path to service account file
    # GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json

    # Target sheet (choose one way):
    GSHEETS_SPREADSHEET_ID=your_spreadsheet_id
    # or
    # GSHEETS_SPREADSHEET_NAME=Your Spreadsheet Name
    GSHEETS_WORKSHEET=Logs
    GSHEETS_BATCH_SIZE=20
    GSHEETS_FLUSH_INTERVAL_SECONDS=5.0
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
- Optional Google Sheets logging using a service account with batched, non-blocking writes

## Google Sheets logging notes

- Create a Google Cloud project and a Service Account; enable the Google Sheets API.
- Share the target spreadsheet with the service account email with Editor access.
- Choose either `GOOGLE_SERVICE_ACCOUNT_JSON` or `GOOGLE_APPLICATION_CREDENTIALS`.
- Configure `GSHEETS_SPREADSHEET_ID` (prefer stable ID) or `GSHEETS_SPREADSHEET_NAME`.
- A worksheet named by `GSHEETS_WORKSHEET` is used (created if missing). A header will be added on first creation.
