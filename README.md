
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

## 🤝 Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** following the existing architecture patterns
4. **Add tests** for new functionality
5. **Ensure all tests pass**: `python -m pytest tests/`
6. **Update documentation** as needed
7. **Submit a pull request**

### Development Guidelines:
- Follow the existing modular architecture
- Add comprehensive tests for new features
- Use type hints and proper documentation
- Follow the established error handling patterns
- Update configuration management for new settings

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
