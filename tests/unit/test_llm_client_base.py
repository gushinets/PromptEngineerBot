"""Tests for the LLM client base classes."""

from unittest.mock import MagicMock

import pytest

from telegram_bot.services.llm.base import LLMClientBase, TokenUsage


class TestTokenUsage:
    """Test cases for TokenUsage class."""

    def test_token_usage_creation(self):
        """Test creating TokenUsage instance."""
        usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)

        assert usage.prompt_tokens == 10
        assert usage.completion_tokens == 20
        assert usage.total_tokens == 30

    def test_token_usage_defaults(self):
        """Test TokenUsage with default values."""
        usage = TokenUsage()

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0

    def test_token_usage_to_dict(self):
        """Test converting TokenUsage to dictionary."""
        usage = TokenUsage(prompt_tokens=15, completion_tokens=25, total_tokens=40)

        result = usage.to_dict()
        expected = {"prompt_tokens": 15, "completion_tokens": 25, "total_tokens": 40}

        assert result == expected


class TestLLMClientBase:
    """Test cases for LLMClientBase abstract class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that LLMClientBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMClientBase("test_key", "test_model")

    def test_concrete_implementation(self):
        """Test concrete implementation of LLMClientBase."""

        class TestLLMClient(LLMClientBase):
            async def send_prompt(self, messages, log_prefix=""):
                return "test response"

        client = TestLLMClient("test_key", "test_model")

        assert client.api_key == "test_key"
        assert client.model_name == "test_model"
        assert client.last_usage is None
        assert hasattr(client, "logger")

    def test_get_last_usage_none(self):
        """Test get_last_usage when no usage is set."""

        class TestLLMClient(LLMClientBase):
            async def send_prompt(self, messages, log_prefix=""):
                return "test response"

        client = TestLLMClient("test_key", "test_model")

        assert client.get_last_usage() is None

    def test_get_last_usage_with_data(self):
        """Test get_last_usage with TokenUsage data."""

        class TestLLMClient(LLMClientBase):
            async def send_prompt(self, messages, log_prefix=""):
                return "test response"

        client = TestLLMClient("test_key", "test_model")
        client.last_usage = TokenUsage(
            prompt_tokens=10, completion_tokens=20, total_tokens=30
        )

        result = client.get_last_usage()
        expected = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        assert result == expected

    def test_logger_creation(self):
        """Test that logger is created with correct name."""

        class TestLLMClient(LLMClientBase):
            async def send_prompt(self, messages, log_prefix=""):
                return "test response"

        client = TestLLMClient("test_key", "test_model")

        assert client.logger.name == "TestLLMClient"



