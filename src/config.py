"""
Configuration management for the Telegram bot.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class BotConfig:
    """Bot configuration settings."""
    telegram_token: str
    llm_backend: str
    model_name: str
    initial_prompt: Optional[str] = None
    bot_id: Optional[str] = None
    
    # OpenAI settings
    openai_api_key: Optional[str] = None
    openai_max_retries: int = 5
    openai_request_timeout: float = 60.0
    openai_max_wait_time: float = 300.0
    
    # OpenRouter settings
    openrouter_api_key: Optional[str] = None
    openrouter_timeout: float = 60.0
    
    # Google Sheets settings
    gsheets_logging_enabled: bool = False
    google_service_account_json: Optional[str] = None
    google_application_credentials: Optional[str] = None
    gsheets_spreadsheet_id: Optional[str] = None
    gsheets_spreadsheet_name: Optional[str] = None
    gsheets_worksheet: str = "Logs"
    gsheets_batch_size: int = 20
    gsheets_flush_interval_seconds: float = 5.0
    
    @classmethod
    def from_env(cls) -> 'BotConfig':
        """Create configuration from environment variables."""
        # Required settings
        telegram_token = os.getenv('TELEGRAM_TOKEN')
        if not telegram_token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")
        
        llm_backend = os.getenv('LLM_BACKEND', 'OPENROUTER').upper()
        model_name = os.getenv('MODEL_NAME', 'openai/gpt-4' if llm_backend == 'OPENROUTER' else 'gpt-4o')
        
        # Validate backend-specific API keys
        if llm_backend == 'OPENAI' and not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY is required when using OpenAI backend")
        elif llm_backend == 'OPENROUTER' and not os.getenv('OPENROUTER_API_KEY'):
            raise ValueError("OPENROUTER_API_KEY is required when using OpenRouter backend")
        
        return cls(
            telegram_token=telegram_token,
            llm_backend=llm_backend,
            model_name=model_name,
            initial_prompt=os.getenv('INITIAL_PROMPT'),
            bot_id=os.getenv('BOT_ID'),
            
            # OpenAI settings
            openai_api_key=os.getenv('OPENAI_API_KEY'),
            openai_max_retries=int(os.getenv('OPENAI_MAX_RETRIES', 5)),
            openai_request_timeout=float(os.getenv('OPENAI_REQUEST_TIMEOUT', 60.0)),
            openai_max_wait_time=float(os.getenv('OPENAI_MAX_WAIT_TIME', 300.0)),
            
            # OpenRouter settings
            openrouter_api_key=os.getenv('OPENROUTER_API_KEY'),
            openrouter_timeout=float(os.getenv('OPENROUTER_TIMEOUT', 60.0)),
            
            # Google Sheets settings
            gsheets_logging_enabled=os.getenv('GSHEETS_LOGGING_ENABLED', '').lower() in ('true', '1', 'yes'),
            google_service_account_json=os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON'),
            google_application_credentials=os.getenv('GOOGLE_APPLICATION_CREDENTIALS'),
            gsheets_spreadsheet_id=os.getenv('GSHEETS_SPREADSHEET_ID'),
            gsheets_spreadsheet_name=os.getenv('GSHEETS_SPREADSHEET_NAME'),
            gsheets_worksheet=os.getenv('GSHEETS_WORKSHEET', 'Logs'),
            gsheets_batch_size=int(os.getenv('GSHEETS_BATCH_SIZE', 20)),
            gsheets_flush_interval_seconds=float(os.getenv('GSHEETS_FLUSH_INTERVAL_SECONDS', 5.0))
        )
    
    def validate(self) -> None:
        """Validate configuration settings."""
        if self.llm_backend not in ('OPENAI', 'OPENROUTER'):
            raise ValueError(f"Invalid LLM_BACKEND: {self.llm_backend}. Must be 'OPENAI' or 'OPENROUTER'")
        
        if self.gsheets_logging_enabled:
            if not (self.gsheets_spreadsheet_id or self.gsheets_spreadsheet_name):
                raise ValueError("Google Sheets logging enabled but no spreadsheet ID or name provided")
            if not (self.google_service_account_json or self.google_application_credentials):
                raise ValueError("Google Sheets logging enabled but no credentials provided")