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

    # Database settings
    database_url: str = "sqlite:///./bot.db"
    database_pool_size: int = 10
    database_max_overflow: int = 20
    database_pool_pre_ping: bool = True

    # Redis settings
    redis_url: str = "redis://localhost:6379"
    redis_max_connections: int = 10

    # SMTP settings
    smtp_host: str = "smtp-pulse.com"
    smtp_port: int = 587  # Default to TLS port
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    smtp_from_email: Optional[str] = None
    smtp_from_name: str = "Prompt Engineering Bot"

    # Email authentication settings
    otp_ttl_seconds: int = 300  # 5 minutes
    otp_max_attempts: int = 3
    email_rate_limit_per_hour: int = 3
    user_rate_limit_per_hour: int = 5
    otp_spacing_seconds: int = 60

    # Audit settings
    audit_retention_days: int = 90
    audit_purge_enabled: bool = True

    # Follow-up conversation settings
    followup_timeout_seconds: int = 300  # 5 minutes

    # Localization settings
    language: str = "EN"  # EN or RU

    # Email feature toggle
    email_enabled: bool = True

    @staticmethod
    def _get_default_smtp_port() -> int:
        """Get default SMTP port based on TLS/SSL settings."""
        smtp_use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in (
            "true",
            "1",
            "yes",
        )
        smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

        if smtp_use_ssl:
            return 465
        elif smtp_use_tls:
            return 587
        else:
            return 25

    @classmethod
    def from_env(cls) -> "BotConfig":
        """Create configuration from environment variables."""
        # Required settings
        telegram_token = os.getenv("TELEGRAM_TOKEN")
        if not telegram_token:
            raise ValueError("TELEGRAM_TOKEN environment variable is required")

        llm_backend = os.getenv("LLM_BACKEND", "OPENROUTER").upper()
        model_name = os.getenv(
            "MODEL_NAME", "openai/gpt-4" if llm_backend == "OPENROUTER" else "gpt-4o"
        )

        # Validate backend-specific API keys
        if llm_backend == "OPENAI" and not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY is required when using OpenAI backend")
        elif llm_backend == "OPENROUTER" and not os.getenv("OPENROUTER_API_KEY"):
            raise ValueError(
                "OPENROUTER_API_KEY is required when using OpenRouter backend"
            )

        return cls(
            telegram_token=telegram_token,
            llm_backend=llm_backend,
            model_name=model_name,
            initial_prompt=os.getenv("INITIAL_PROMPT"),
            bot_id=os.getenv("BOT_ID"),
            # OpenAI settings
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_max_retries=int(os.getenv("OPENAI_MAX_RETRIES", 5)),
            openai_request_timeout=float(os.getenv("OPENAI_REQUEST_TIMEOUT", 60.0)),
            openai_max_wait_time=float(os.getenv("OPENAI_MAX_WAIT_TIME", 300.0)),
            # OpenRouter settings
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            openrouter_timeout=float(os.getenv("OPENROUTER_TIMEOUT", 60.0)),
            # Google Sheets settings
            gsheets_logging_enabled=os.getenv("GSHEETS_LOGGING_ENABLED", "").lower()
            in ("true", "1", "yes"),
            google_service_account_json=os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"),
            google_application_credentials=os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
            gsheets_spreadsheet_id=os.getenv("GSHEETS_SPREADSHEET_ID"),
            gsheets_spreadsheet_name=os.getenv("GSHEETS_SPREADSHEET_NAME"),
            gsheets_worksheet=os.getenv("GSHEETS_WORKSHEET", "Logs"),
            gsheets_batch_size=int(os.getenv("GSHEETS_BATCH_SIZE", 20)),
            gsheets_flush_interval_seconds=float(
                os.getenv("GSHEETS_FLUSH_INTERVAL_SECONDS", 5.0)
            ),
            # Database settings
            database_url=os.getenv("DATABASE_URL", "sqlite:///./bot.db"),
            database_pool_size=int(os.getenv("DATABASE_POOL_SIZE", 10)),
            database_max_overflow=int(os.getenv("DATABASE_MAX_OVERFLOW", 20)),
            database_pool_pre_ping=os.getenv("DATABASE_POOL_PRE_PING", "true").lower()
            in ("true", "1", "yes"),
            # Redis settings
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            redis_max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", 10)),
            # SMTP settings
            smtp_host=os.getenv("SMTP_HOST", "smtp-pulse.com"),
            smtp_port=int(os.getenv("SMTP_PORT", cls._get_default_smtp_port())),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower()
            in ("true", "1", "yes"),
            smtp_use_ssl=os.getenv("SMTP_USE_SSL", "false").lower()
            in ("true", "1", "yes"),
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL"),
            smtp_from_name=os.getenv("SMTP_FROM_NAME", "Prompt Engineering Bot"),
            # Email authentication settings
            otp_ttl_seconds=int(os.getenv("OTP_TTL_SECONDS", 300)),
            otp_max_attempts=int(os.getenv("OTP_MAX_ATTEMPTS", 3)),
            email_rate_limit_per_hour=int(os.getenv("EMAIL_RATE_LIMIT_PER_HOUR", 3)),
            user_rate_limit_per_hour=int(os.getenv("USER_RATE_LIMIT_PER_HOUR", 5)),
            otp_spacing_seconds=int(os.getenv("OTP_SPACING_SECONDS", 60)),
            # Audit settings
            audit_retention_days=int(os.getenv("AUDIT_RETENTION_DAYS", 90)),
            audit_purge_enabled=os.getenv("AUDIT_PURGE_ENABLED", "true").lower()
            in ("true", "1", "yes"),
            # Follow-up conversation settings
            followup_timeout_seconds=int(os.getenv("FOLLOWUP_TIMEOUT_SECONDS", 300)),
            # Localization settings
            language=os.getenv("LANGUAGE", "EN").upper(),
            # Email feature toggle
            email_enabled=os.getenv("EMAIL_ENABLED", "true").lower()
            in ("true", "1", "yes"),
        )

    def validate(self) -> None:
        """Validate configuration settings."""
        if self.llm_backend not in ("OPENAI", "OPENROUTER"):
            raise ValueError(
                f"Invalid LLM_BACKEND: {self.llm_backend}. Must be 'OPENAI' or 'OPENROUTER'"
            )

        if self.gsheets_logging_enabled:
            if not (self.gsheets_spreadsheet_id or self.gsheets_spreadsheet_name):
                raise ValueError(
                    "Google Sheets logging enabled but no spreadsheet ID or name provided"
                )
            if not (
                self.google_service_account_json or self.google_application_credentials
            ):
                raise ValueError(
                    "Google Sheets logging enabled but no credentials provided"
                )

        # Validate SMTP settings
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValueError("Cannot use both TLS and SSL for SMTP. Choose one.")

        # Validate language setting
        if self.language not in ("EN", "RU"):
            raise ValueError(f"Invalid LANGUAGE: {self.language}. Must be 'EN' or 'RU'")

        # Validate rate limiting settings
        if self.email_rate_limit_per_hour <= 0:
            raise ValueError("EMAIL_RATE_LIMIT_PER_HOUR must be positive")

        if self.user_rate_limit_per_hour <= 0:
            raise ValueError("USER_RATE_LIMIT_PER_HOUR must be positive")

        if self.otp_ttl_seconds <= 0:
            raise ValueError("OTP_TTL_SECONDS must be positive")

        if self.otp_max_attempts <= 0:
            raise ValueError("OTP_MAX_ATTEMPTS must be positive")

        if self.otp_spacing_seconds < 0:
            raise ValueError("OTP_SPACING_SECONDS must be non-negative")

        # Validate audit settings
        if self.audit_retention_days <= 0:
            raise ValueError("AUDIT_RETENTION_DAYS must be positive")

        # Validate follow-up settings
        if self.followup_timeout_seconds <= 0:
            raise ValueError("FOLLOWUP_TIMEOUT_SECONDS must be positive")
