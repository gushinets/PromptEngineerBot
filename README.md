
# Telegram Prompt Engineering Bot

A professional Telegram bot that helps users optimize their prompts using different AI-powered methodologies (CRAFT, LYRA, GGL). Built with a clean, modular architecture and comprehensive testing.

## 🚀 Features

- **Multi-Method Prompt Optimization**: CRAFT, LYRA (Basic & Detailed), and GGL methodologies
- **Dual LLM Support**: OpenAI and OpenRouter API integration with factory pattern
- **Conversation Management**: Full conversation context and token usage tracking
- **Google Sheets Integration**: Optional structured logging with batched, non-blocking writes
- **Robust Error Handling**: Comprehensive error handling with automatic fallbacks
- **Production Ready**: Docker support, comprehensive testing, and monitoring
- **Clean Architecture**: Modular design with dependency injection and factory patterns

## 🏗️ Architecture

The bot follows clean architecture principles with clear separation of concerns:

```
src/
├── llm_client_base.py      # Abstract base for LLM clients
├── openai_client.py        # OpenAI API client
├── openrouter_client.py    # OpenRouter API client
├── llm_factory.py          # Factory for creating LLM clients
├── config.py               # Configuration management with validation
├── bot_handler.py          # Core bot logic and conversation handling
├── conversation_manager.py # Conversation state and token tracking
├── state_manager.py        # User state management
├── prompt_loader.py        # Prompt file management
├── messages.py             # Message formatting and parsing
├── gsheets_logging.py      # Google Sheets integration
└── prompts/                # Optimization method prompts
    ├── CRAFT_prompt.txt
    ├── LYRA_prompt.txt
    └── GGL_prompt.txt

tools/
├── diagnose_gsheets.py     # Google Sheets diagnostic tool
├── repair_gsheets.py       # Google Sheets repair tool
└── README.md               # Tools documentation
```

## 📦 Setup

### Local Development

1. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2. **Create a `.env` file with your credentials:**
    ```env
    # Required
    TELEGRAM_TOKEN=your_telegram_token
    LLM_BACKEND=OPENROUTER  # or OPENAI

    # OpenAI Configuration (if using OPENAI backend)
    OPENAI_API_KEY=your_openai_api_key
    OPENAI_MAX_RETRIES=5
    OPENAI_REQUEST_TIMEOUT=60.0
    OPENAI_MAX_WAIT_TIME=300.0

    # OpenRouter Configuration (if using OPENROUTER backend)
    OPENROUTER_API_KEY=your_openrouter_api_key
    OPENROUTER_TIMEOUT=60.0

    # Model Configuration
    MODEL_NAME=openai/gpt-4  # For OpenRouter, or gpt-4o for OpenAI
    INITIAL_PROMPT=your_system_prompt  # Optional
    BOT_ID=your_bot_id  # Optional

    # Google Sheets Logging (Optional)
    GSHEETS_LOGGING_ENABLED=true
    GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
    # OR
    GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
    GSHEETS_SPREADSHEET_ID=your_spreadsheet_id
    # OR
    GSHEETS_SPREADSHEET_NAME=Your Spreadsheet Name
    GSHEETS_WORKSHEET=Logs
    GSHEETS_BATCH_SIZE=20
    GSHEETS_FLUSH_INTERVAL_SECONDS=5.0
    ```

3. **Run the bot:**
    ```bash
    # Using the entry point script (recommended)
    python run_bot.py
    
    # Or using module execution
    python -m src.main
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

### Development with VS Code/Kiro IDE

The project includes VS Code launch configurations for easy debugging:

- **"Run Telegram Bot"**: Uses the entry point script
- **"Run Telegram Bot (Module)"**: Runs as Python module (recommended for debugging)
- **"Run Tests"**: Execute the test suite
- **"Debug Test"**: Debug specific test functions

## 🐳 Docker Deployment

### Docker Build & Run

1. **Build the Docker image:**
    ```bash
    docker build -t prompt-improver-bot .
    ```

2. **Run the container:**
    ```bash
    docker run --env-file .env prompt-improver-bot
    ```

### Docker Compose

1. **Ensure your `.env` file is in the project root**
2. **Start with Docker Compose:**
    ```bash
    docker compose up --build
    ```

## 🧪 Testing

The project includes comprehensive test coverage (84% overall):

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage report
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test categories
python -m pytest tests/test_config.py -v
python -m pytest tests/test_bot_handler.py -v

# Test imports and architecture
python test_imports.py
```

### Test Coverage by Module:
- **BotHandler**: 95% - Core bot logic and conversation flows
- **Config**: 100% - Configuration management and validation
- **ConversationManager**: 100% - State and token tracking
- **StateManager**: 100% - User state management
- **PromptLoader**: 100% - Prompt file management
- **LLMFactory**: 100% - Client creation and backend switching
- **Messages**: 100% - Response parsing and formatting

## 🔧 Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TELEGRAM_TOKEN` | ✅ | - | Your Telegram bot token |
| `LLM_BACKEND` | ✅ | `OPENROUTER` | `OPENAI` or `OPENROUTER` |
| `MODEL_NAME` | ❌ | Backend-specific | Model to use |
| `OPENAI_API_KEY` | ✅* | - | Required if using OpenAI backend |
| `OPENROUTER_API_KEY` | ✅* | - | Required if using OpenRouter backend |
| `GSHEETS_LOGGING_ENABLED` | ❌ | `false` | Enable Google Sheets logging |

*Required based on selected backend

### Google Sheets Integration

To enable Google Sheets logging:

1. **Create a Google Cloud project and Service Account**
2. **Enable the Google Sheets API**
3. **Share your spreadsheet with the service account email (Editor access)**
4. **Configure credentials** using either:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: Raw JSON credentials
   - `GOOGLE_APPLICATION_CREDENTIALS`: Path to credentials file
5. **Set spreadsheet target** using either:
   - `GSHEETS_SPREADSHEET_ID`: Spreadsheet ID (recommended)
   - `GSHEETS_SPREADSHEET_NAME`: Spreadsheet name

## 🔍 Troubleshooting

### Google Sheets Issues

#### Empty Cells in Google Sheets
If you see empty cells at the beginning of your Google Sheets rows:

1. **Diagnose the issue:**
   ```bash
   python tools/diagnose_gsheets.py
   ```

2. **Common causes:**
   - Extra empty columns in your Google Sheet
   - Header mismatch between sheet and expected fields
   - Custom `GSHEETS_FIELDS` configuration

3. **Quick fix:**
   ```bash
   python tools/repair_gsheets.py
   ```

4. **Manual fix:**
   - Open your Google Sheet
   - Ensure the first row headers exactly match: `DateTime, BotID, TelegramID, LLM, OptimizationModel, UserRequest, Answer, prompt_tokens, completion_tokens, total_tokens`
   - Delete any extra empty columns at the beginning

#### Header Validation
The bot now automatically validates Google Sheets headers and logs warnings if mismatches are detected. Check your logs for detailed mismatch information.

### API Issues

#### OpenAI Region Restrictions
If you see "Country, region, or territory not supported" errors:
- Switch to OpenRouter: Set `LLM_BACKEND=OPENROUTER`
- Or use a VPN/proxy if appropriate for your use case

#### Rate Limiting
- The bot includes automatic retry logic with exponential backoff
- For high-volume usage, consider upgrading your API plan

### General Debugging

#### Enable Debug Logging
Add to your `.env`:
```env
LOG_LEVEL=DEBUG
```

#### Check Bot Logs
When running in Docker/Compose, logs are written to stdout/stderr by default:
```bash
docker compose logs -f prompt-improver-bot
```

If you explicitly enable file logging, set environment variables and ensure write permissions:
```env
LOG_TO_FILE=true
LOG_FILE_PATH=/app/bot.log
```
And then you can tail the file in the container:
```bash
docker exec -it prompt-improver-bot sh -lc 'tail -f /app/bot.log'
```

## 🏛️ Architecture Details

### Design Patterns Used:
- **Factory Pattern**: `LLMClientFactory` for creating LLM clients
- **Strategy Pattern**: Different prompt optimization methods
- **Dependency Injection**: Clean separation of concerns
- **Abstract Base Classes**: Consistent LLM client interface

### Key Components:
- **BotHandler**: Orchestrates conversation flow and user interactions
- **ConversationManager**: Manages conversation state and token tracking
- **StateManager**: Handles user state (waiting for prompt, method selection)
- **PromptLoader**: Loads and manages optimization method prompts
- **LLMClientBase**: Abstract interface for all LLM clients

### Database Schema:

#### User Model
The `User` model stores authentication data and Telegram profile information:

**Authentication Fields:**
- `telegram_id`: Unique Telegram user identifier
- `email`: User's verified email address
- `is_authenticated`: Email verification status
- `email_verified_at`: Timestamp of email verification
- `last_authenticated_at`: Last successful authentication

**Profile Fields (Auto-captured from Telegram):**
- `first_name`: User's first name from Telegram profile
- `last_name`: User's last name from Telegram profile
- `is_bot`: Boolean indicating if user is a bot account
- `is_premium`: Telegram Premium subscription status
- `language_code`: User's language preference (ISO 639-1 code)

**Profile Update Strategy:**
- **New users**: All available profile data captured during first interaction
- **Existing users**: Selective updates only when meaningful changes detected (name changes, premium status changes)
- **Performance optimization**: Profile updates only occur when necessary to minimize database writes
- **Error handling**: Graceful handling of missing or null Telegram profile data

**Database Indexes:**
- Language-based queries: `ix_users_language_code`
- Premium user filtering: `ix_users_is_premium`  
- User type analytics: `ix_users_bot_premium` (composite)

For detailed information about the user profile system, see [User Profile System Documentation](docs/USER_PROFILE_SYSTEM.md).

### Error Handling:
- **Automatic fallbacks** for Markdown parsing errors
- **Retry logic** with exponential backoff for API calls
- **Graceful degradation** when external services fail
- **Comprehensive logging** for debugging and monitoring

## 🚀 Deployment

### Production Considerations:
- Use environment variables for all configuration
- Enable Google Sheets logging for monitoring
- Set appropriate timeout values for your use case
- Monitor token usage and costs
- Use Docker for consistent deployments

### Scaling:
- The bot uses in-memory state management (suitable for single-instance deployment)
- For multi-instance deployment, consider adding Redis for shared state
- Google Sheets logging is batched and non-blocking for performance

### Development Guidelines:
- Follow the existing modular architecture
- Add comprehensive tests for new features
- Use type hints and proper documentation
- Follow the established error handling patterns
- Update configuration management for new settings
