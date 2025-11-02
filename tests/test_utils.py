"""
Test utilities for managing dependencies and mocks.
"""

from unittest.mock import MagicMock

import pytest

from telegram_prompt_bot.config.dependencies import reset_container


@pytest.fixture(autouse=True)
def reset_dependency_container():
    """Reset the dependency container before each test to ensure isolation."""
    from telegram_prompt_bot.config.dependencies import get_container, reset_all_globals

    # Reset all global state
    reset_all_globals()

    # Create fresh instances for each test
    container = get_container()
    container.create_fresh_instances()

    yield

    # Reset after test
    reset_all_globals()


def create_mock_config():
    """Create a mock BotConfig for testing."""
    mock_config = MagicMock()
    mock_config.model_name = "test-model"
    mock_config.followup_timeout_seconds = 300
    mock_config.email_enabled = True
    return mock_config


def create_mock_llm_client():
    """Create a mock LLM client for testing."""
    mock_llm_client = MagicMock()
    mock_llm_client.send_prompt = MagicMock()
    mock_llm_client.get_last_usage = MagicMock(
        return_value={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
    return mock_llm_client
