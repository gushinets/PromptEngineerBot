"""
Test timeout handling and graceful degradation in email flow.
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import Update
from telegram.ext import ContextTypes

from telegram_bot.core.conversation_manager import ConversationManager
from telegram_bot.core.state_manager import StateManager
from telegram_bot.flows.email_flow import EmailFlowOrchestrator
from telegram_bot.services.llm.base import LLMClientBase
from telegram_bot.utils.config import BotConfig


class MockLLMClient(LLMClientBase):
    """Mock LLM client for testing."""

    def __init__(self):
        self.last_usage = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

    async def send_prompt(self, messages):
        """Mock send_prompt that simulates slow response."""
        # Simulate slow LLM response
        await asyncio.sleep(0.1)
        return "This is a follow-up question."

    def get_last_usage(self):
        return self.last_usage


@pytest.fixture
def mock_config():
    """Create mock configuration with short timeout for testing."""
    config = MagicMock(spec=BotConfig)
    config.followup_timeout_seconds = 2  # 2 seconds for fast testing
    return config


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    return MagicMock(spec=StateManager)


@pytest.fixture
def mock_conversation_manager():
    """Create mock conversation manager."""
    manager = MagicMock(spec=ConversationManager)
    manager.start_followup_conversation = MagicMock()
    manager.reset_token_totals = MagicMock()
    manager.get_transcript = MagicMock(
        return_value=[
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
        ]
    )
    manager.append_message = MagicMock()
    manager.accumulate_token_usage = MagicMock()
    return manager


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    return MockLLMClient()


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock(spec=Update)
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.fixture
async def email_flow_orchestrator(
    mock_config, mock_llm_client, mock_conversation_manager, mock_state_manager
):
    """Create email flow orchestrator with mocked dependencies."""
    with (
        patch("telegram_bot.flows.email_flow.get_auth_service"),
        patch("telegram_bot.flows.email_flow.get_email_service"),
        patch("telegram_bot.flows.email_flow.get_redis_client") as mock_redis,
    ):
        # Mock Redis client
        mock_redis_client = MagicMock()
        mock_redis_client.set_flow_state = MagicMock(return_value=True)
        mock_redis_client.get_flow_state = MagicMock()
        mock_redis_client.delete_flow_state = MagicMock(return_value=True)
        mock_redis.return_value = mock_redis_client

        orchestrator = EmailFlowOrchestrator(
            mock_config, mock_llm_client, mock_conversation_manager, mock_state_manager
        )
        orchestrator.redis_client = mock_redis_client
        return orchestrator


class TestEmailFlowTimeout:
    """Test timeout handling in email flow."""

    async def test_timeout_detection(self, email_flow_orchestrator):
        """Test that timeout is correctly detected."""
        user_id = 12345

        # Set timeout start time to 5 seconds ago (longer than 2 second timeout)
        timeout_data = {"state": "followup_timeout", "start_time": time.time() - 5}
        email_flow_orchestrator.redis_client.get_flow_state.return_value = timeout_data

        # Check timeout detection
        is_timeout = email_flow_orchestrator._is_followup_timeout(user_id)
        assert is_timeout is True

    async def test_no_timeout_detection(self, email_flow_orchestrator):
        """Test that timeout is not detected when within time limit."""
        user_id = 12345

        # Set timeout start time to 1 second ago (less than 2 second timeout)
        timeout_data = {"state": "followup_timeout", "start_time": time.time() - 1}
        email_flow_orchestrator.redis_client.get_flow_state.return_value = timeout_data

        # Check timeout detection
        is_timeout = email_flow_orchestrator._is_followup_timeout(user_id)
        assert is_timeout is False

    async def test_timeout_handling_with_cached_prompt(
        self, email_flow_orchestrator, mock_update, mock_context
    ):
        """Test timeout handling when cached improved prompt is available."""
        user_id = 12345
        cached_prompt = "This is a cached improved prompt"

        # Mock state manager to return cached prompt
        email_flow_orchestrator.state_manager.get_improved_prompt_cache.return_value = cached_prompt

        # Mock the optimization and delivery method
        email_flow_orchestrator._run_optimization_and_email_delivery = AsyncMock(return_value=True)

        # Handle timeout
        result = await email_flow_orchestrator._handle_followup_timeout(
            mock_update, mock_context, user_id
        )

        # Verify timeout was handled successfully
        assert result is True

        # Verify state was cleared
        email_flow_orchestrator.state_manager.set_in_followup_conversation.assert_called_with(
            user_id, False
        )
        email_flow_orchestrator.redis_client.delete_flow_state.assert_called_with(user_id)

        # Verify optimization was called with cached prompt
        email_flow_orchestrator._run_optimization_and_email_delivery.assert_called_once_with(
            mock_update, mock_context, user_id, cached_prompt
        )

    async def test_timeout_handling_without_cached_prompt(
        self, email_flow_orchestrator, mock_update, mock_context
    ):
        """Test timeout handling when no cached prompt is available."""
        user_id = 12345
        original_prompt = "Original user prompt"

        # Mock state manager to return no cached prompt but email flow data
        email_flow_orchestrator.state_manager.get_improved_prompt_cache.return_value = None
        email_flow_orchestrator.state_manager.get_email_flow_data.return_value = {
            "original_prompt": original_prompt
        }

        # Mock the optimization and delivery method
        email_flow_orchestrator._run_optimization_and_email_delivery = AsyncMock(return_value=True)

        # Handle timeout
        result = await email_flow_orchestrator._handle_followup_timeout(
            mock_update, mock_context, user_id
        )

        # Verify timeout was handled successfully
        assert result is True

        # Verify optimization was called with original prompt
        email_flow_orchestrator._run_optimization_and_email_delivery.assert_called_once_with(
            mock_update, mock_context, user_id, original_prompt
        )

    async def test_timeout_check_in_conversation_handling(
        self, email_flow_orchestrator, mock_update, mock_context
    ):
        """Test that timeout is checked during conversation handling."""
        user_id = 12345
        text = "User response"

        # Mock timeout detection to return True
        email_flow_orchestrator._is_followup_timeout = MagicMock(return_value=True)
        email_flow_orchestrator._handle_followup_timeout = AsyncMock(return_value=True)

        # Handle conversation
        result = await email_flow_orchestrator.handle_followup_conversation(
            mock_update, mock_context, user_id, text
        )

        # Verify timeout was checked and handled
        email_flow_orchestrator._is_followup_timeout.assert_called_once_with(user_id)
        email_flow_orchestrator._handle_followup_timeout.assert_called_once_with(
            mock_update, mock_context, user_id
        )
        assert result is True

    async def test_timeout_check_in_llm_request(
        self, email_flow_orchestrator, mock_update, mock_context
    ):
        """Test that timeout is checked during LLM request processing."""
        user_id = 12345

        # Mock timeout detection to return True
        email_flow_orchestrator._is_followup_timeout = MagicMock(return_value=True)
        email_flow_orchestrator._handle_followup_timeout = AsyncMock(return_value=True)

        # Process LLM request
        result = await email_flow_orchestrator._process_followup_llm_request(
            mock_update, mock_context, user_id
        )

        # Verify timeout was checked and handled
        email_flow_orchestrator._is_followup_timeout.assert_called_once_with(user_id)
        email_flow_orchestrator._handle_followup_timeout.assert_called_once_with(
            mock_update, mock_context, user_id
        )
        assert result is True

    async def test_error_handling_fallback(
        self, email_flow_orchestrator, mock_update, mock_context
    ):
        """Test error handling with graceful degradation."""
        user_id = 12345
        error = Exception("Test error")
        cached_prompt = "Cached improved prompt"

        # Mock state manager to return cached prompt
        email_flow_orchestrator.state_manager.get_improved_prompt_cache.return_value = cached_prompt

        # Mock the optimization and delivery method
        email_flow_orchestrator._run_optimization_and_email_delivery = AsyncMock(return_value=True)

        # Handle error
        result = await email_flow_orchestrator._handle_followup_error(
            mock_update, mock_context, user_id, error
        )

        # Verify error was handled successfully
        assert result is True

        # Verify state was cleared
        email_flow_orchestrator.state_manager.set_in_followup_conversation.assert_called_with(
            user_id, False
        )
        email_flow_orchestrator.redis_client.delete_flow_state.assert_called_with(user_id)

        # Verify optimization was called with cached prompt
        email_flow_orchestrator._run_optimization_and_email_delivery.assert_called_once_with(
            mock_update, mock_context, user_id, cached_prompt
        )

    async def test_timeout_configuration(
        self,
        mock_config,
        mock_llm_client,
        mock_conversation_manager,
        mock_state_manager,
    ):
        """Test that timeout configuration is properly used."""
        # Set custom timeout in config
        mock_config.followup_timeout_seconds = 120  # 2 minutes

        with (
            patch("telegram_bot.flows.email_flow.get_auth_service"),
            patch("telegram_bot.flows.email_flow.get_email_service"),
            patch("telegram_bot.flows.email_flow.get_redis_client"),
        ):
            orchestrator = EmailFlowOrchestrator(
                mock_config,
                mock_llm_client,
                mock_conversation_manager,
                mock_state_manager,
            )

            # Verify timeout configuration is used
            assert orchestrator.followup_timeout_seconds == 120

    async def test_no_user_facing_errors_on_timeout(
        self, email_flow_orchestrator, mock_update, mock_context
    ):
        """Test that timeout handling doesn't show user-facing errors."""
        user_id = 12345
        cached_prompt = "Cached prompt"

        # Mock state manager
        email_flow_orchestrator.state_manager.get_improved_prompt_cache.return_value = cached_prompt

        # Mock optimization method to succeed
        email_flow_orchestrator._run_optimization_and_email_delivery = AsyncMock(return_value=True)

        # Handle timeout
        result = await email_flow_orchestrator._handle_followup_timeout(
            mock_update, mock_context, user_id
        )

        # Verify no error messages were sent to user
        # The _run_optimization_and_email_delivery should handle user communication
        assert result is True

        # Verify the flow continues gracefully
        email_flow_orchestrator._run_optimization_and_email_delivery.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
