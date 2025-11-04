"""Tests for the configuration management module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from telegram_bot.utils.config import BotConfig


class TestBotConfig:
    """Test cases for BotConfig class."""

    def test_from_env_minimal_config(self):
        """Test creating config with minimal required environment variables."""
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "LLM_BACKEND": "OPENAI",
                "OPENAI_API_KEY": "test_openai_key",
            },
            clear=True,
        ):
            config = BotConfig.from_env()

            assert config.telegram_token == "test_token"
            assert config.llm_backend == "OPENAI"
            assert config.openai_api_key == "test_openai_key"
            assert config.model_name == "gpt-4o"  # default for OpenAI

    def test_from_env_openrouter_config(self):
        """Test creating config for OpenRouter backend."""
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_TOKEN": "test_token",
                "LLM_BACKEND": "OPENROUTER",
                "OPENROUTER_API_KEY": "test_openrouter_key",
                "MODEL_NAME": "openai/gpt-4",
            },
            clear=True,
        ):
            config = BotConfig.from_env()

            assert config.telegram_token == "test_token"
            assert config.llm_backend == "OPENROUTER"
            assert config.openrouter_api_key == "test_openrouter_key"
            assert config.model_name == "openai/gpt-4"

    def test_from_env_full_config(self):
        """Test creating config with all environment variables."""
        env_vars = {
            "TELEGRAM_TOKEN": "test_token",
            "LLM_BACKEND": "OPENAI",
            "MODEL_NAME": "gpt-4",
            "INITIAL_PROMPT": "test_prompt",
            "BOT_ID": "test_bot",
            "OPENAI_API_KEY": "test_openai_key",
            "OPENAI_MAX_RETRIES": "3",
            "OPENAI_REQUEST_TIMEOUT": "30.0",
            "OPENAI_MAX_WAIT_TIME": "120.0",
            "OPENROUTER_API_KEY": "test_openrouter_key",
            "OPENROUTER_TIMEOUT": "45.0",
            "GSHEETS_LOGGING_ENABLED": "true",
            "GOOGLE_SERVICE_ACCOUNT_JSON": '{"test": "json"}',
            "GSHEETS_SPREADSHEET_ID": "test_sheet_id",
            "GSHEETS_WORKSHEET": "TestLogs",
            "GSHEETS_BATCH_SIZE": "10",
            "GSHEETS_FLUSH_INTERVAL_SECONDS": "2.0",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            config = BotConfig.from_env()

            assert config.telegram_token == "test_token"
            assert config.llm_backend == "OPENAI"
            assert config.model_name == "gpt-4"
            assert config.initial_prompt == "test_prompt"
            assert config.bot_id == "test_bot"
            assert config.openai_max_retries == 3
            assert config.openai_request_timeout == 30.0
            assert config.openai_max_wait_time == 120.0
            assert config.openrouter_timeout == 45.0
            assert config.gsheets_logging_enabled is True
            assert config.gsheets_batch_size == 10
            assert config.gsheets_flush_interval_seconds == 2.0

    def test_from_env_missing_telegram_token(self):
        """Test that missing TELEGRAM_TOKEN raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(
                ValueError, match="TELEGRAM_TOKEN environment variable is required"
            ):
                BotConfig.from_env()

    def test_from_env_missing_openai_key(self):
        """Test that missing OpenAI key raises ValueError when using OpenAI backend."""
        with patch.dict(
            os.environ,
            {"TELEGRAM_TOKEN": "test_token", "LLM_BACKEND": "OPENAI"},
            clear=True,
        ):
            with pytest.raises(
                ValueError, match="OPENAI_API_KEY is required when using OpenAI backend"
            ):
                BotConfig.from_env()

    def test_from_env_missing_openrouter_key(self):
        """Test that missing OpenRouter key raises ValueError when using OpenRouter backend."""
        with patch.dict(
            os.environ,
            {"TELEGRAM_TOKEN": "test_token", "LLM_BACKEND": "OPENROUTER"},
            clear=True,
        ):
            with pytest.raises(
                ValueError,
                match="OPENROUTER_API_KEY is required when using OpenRouter backend",
            ):
                BotConfig.from_env()

    def test_validate_invalid_backend(self):
        """Test validation with invalid LLM backend."""
        config = BotConfig(
            telegram_token="test_token", llm_backend="INVALID", model_name="test_model"
        )

        with pytest.raises(ValueError, match="Invalid LLM_BACKEND: INVALID"):
            config.validate()

    def test_validate_gsheets_missing_spreadsheet(self):
        """Test validation with Google Sheets enabled but no spreadsheet info."""
        config = BotConfig(
            telegram_token="test_token",
            llm_backend="OPENAI",
            model_name="test_model",
            gsheets_logging_enabled=True,
        )

        with pytest.raises(
            ValueError,
            match="Google Sheets logging enabled but no spreadsheet ID or name provided",
        ):
            config.validate()

    def test_validate_gsheets_missing_credentials(self):
        """Test validation with Google Sheets enabled but no credentials."""
        config = BotConfig(
            telegram_token="test_token",
            llm_backend="OPENAI",
            model_name="test_model",
            gsheets_logging_enabled=True,
            gsheets_spreadsheet_id="test_id",
        )

        with pytest.raises(
            ValueError,
            match="Google Sheets logging enabled but no credentials provided",
        ):
            config.validate()

    def test_validate_success(self):
        """Test successful validation."""
        config = BotConfig(
            telegram_token="test_token", llm_backend="OPENAI", model_name="test_model"
        )

        # Should not raise any exception
        config.validate()

    def test_gsheets_boolean_parsing(self):
        """Test that Google Sheets boolean is parsed correctly."""
        test_cases = [
            ("true", True),
            ("1", True),
            ("yes", True),
            ("false", False),
            ("0", False),
            ("no", False),
            ("", False),
        ]

        for env_value, expected in test_cases:
            with patch.dict(
                os.environ,
                {
                    "TELEGRAM_TOKEN": "test_token",
                    "LLM_BACKEND": "OPENAI",
                    "OPENAI_API_KEY": "test_key",
                    "GSHEETS_LOGGING_ENABLED": env_value,
                },
                clear=True,
            ):
                config = BotConfig.from_env()
                assert config.gsheets_logging_enabled == expected



