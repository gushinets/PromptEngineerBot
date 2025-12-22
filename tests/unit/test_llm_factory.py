"""Tests for the LLM client factory."""

from unittest.mock import MagicMock, patch

import pytest

from telegram_bot.services.llm.factory import LLMClientFactory
from telegram_bot.utils.config import BotConfig


class TestLLMClientFactory:
    """Test cases for LLMClientFactory."""

    def test_create_openai_client(self):
        """Test creating OpenAI client."""
        config = BotConfig(
            telegram_token="test_token",
            llm_backend="OPENAI",
            model_name="gpt-4",
            openai_api_key="test_openai_key",
            openai_max_retries=3,
            openai_request_timeout=30.0,
            openai_max_wait_time=120.0,
        )

        with patch("telegram_bot.services.llm.factory.OpenAIClient") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            result = LLMClientFactory.create_client(config)

            mock_openai.assert_called_once_with(
                api_key="test_openai_key",
                model_name="gpt-4",
                max_retries=3,
                request_timeout=30.0,
                max_wait_time=120.0,
            )
            assert result == mock_client

    def test_create_openrouter_client(self):
        """Test creating OpenRouter client."""
        config = BotConfig(
            telegram_token="test_token",
            llm_backend="OPENROUTER",
            model_name="openai/gpt-4",
            openrouter_api_key="test_openrouter_key",
            openrouter_timeout=45.0,
        )

        with patch("telegram_bot.services.llm.factory.OpenRouterClient") as mock_openrouter:
            mock_client = MagicMock()
            mock_openrouter.return_value = mock_client

            result = LLMClientFactory.create_client(config)

            mock_openrouter.assert_called_once_with(
                api_key="test_openrouter_key", model_name="openai/gpt-4", timeout=45.0
            )
            assert result == mock_client

    def test_create_client_missing_openai_key(self):
        """Test creating OpenAI client without API key."""
        config = BotConfig(telegram_token="test_token", llm_backend="OPENAI", model_name="gpt-4")

        with pytest.raises(ValueError, match="OpenAI API key is required for OpenAI backend"):
            LLMClientFactory.create_client(config)

    def test_create_client_missing_openrouter_key(self):
        """Test creating OpenRouter client without API key."""
        config = BotConfig(
            telegram_token="test_token",
            llm_backend="OPENROUTER",
            model_name="openai/gpt-4",
        )

        with pytest.raises(
            ValueError, match="OpenRouter API key is required for OpenRouter backend"
        ):
            LLMClientFactory.create_client(config)

    def test_create_client_unsupported_backend(self):
        """Test creating client with unsupported backend."""
        config = BotConfig(
            telegram_token="test_token",
            llm_backend="UNSUPPORTED",
            model_name="test_model",
        )

        with pytest.raises(ValueError, match="Unsupported LLM backend: UNSUPPORTED"):
            LLMClientFactory.create_client(config)
