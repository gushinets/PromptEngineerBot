"""
Integration tests for bot handler health check gating.

This module tests the health check integration in bot handler,
specifically for gating the email flow based on service health.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import ContextTypes

from telegram_bot.core.bot_handler import BotHandler
from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.messages import (
    BTN_EMAIL_DELIVERY,
    BTN_RESET,
    ERROR_REDIS_UNAVAILABLE,
)


@pytest.fixture
def mock_config():
    """Create mock BotConfig for testing."""
    config = MagicMock(spec=BotConfig)
    config.followup_timeout_seconds = 300
    config.language = "en"
    return config


@pytest.fixture
def mock_llm_client():
    """Create mock LLM client."""
    client = MagicMock()
    client.send_prompt = AsyncMock(return_value="LLM response")
    client.get_last_usage = MagicMock(
        return_value={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
    return client


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.text = BTN_EMAIL_DELIVERY
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.fixture
def mock_email_flow_orchestrator():
    """Create mock email flow orchestrator."""
    orchestrator = MagicMock()
    orchestrator.start_email_flow = AsyncMock(return_value=True)
    return orchestrator


@pytest.fixture
def mock_health_monitor():
    """Create mock health monitor."""
    monitor = MagicMock()
    monitor.is_service_healthy = MagicMock()
    return monitor


@pytest.fixture
def bot_handler(mock_config, mock_llm_client, mock_email_flow_orchestrator):
    """Create bot handler with mocked dependencies."""
    with patch("telegram_bot.bot_handler.get_container") as mock_container:
        # Mock container dependencies
        container = MagicMock()
        container.get_state_manager.return_value = MagicMock()
        container.get_prompt_loader.return_value = MagicMock()
        container.get_conversation_manager.return_value = MagicMock()
        mock_container.return_value = container

        # Create bot handler
        handler = BotHandler(mock_config, mock_llm_client)
        handler.email_flow_orchestrator = mock_email_flow_orchestrator

        # Mock conversation manager methods
        handler.conversation_manager.is_waiting_for_method = MagicMock(
            return_value=True
        )
        handler.conversation_manager.get_user_prompt = MagicMock(
            return_value="test prompt"
        )

        return handler


class TestBotHandlerHealthGating:
    """Test health check gating in bot handler."""

    async def test_redis_unhealthy_blocks_email_flow(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test that Redis being unhealthy blocks email flow with proper error message."""
        user_id = 12345

        # Mock Redis as unhealthy
        mock_health_monitor.is_service_healthy.side_effect = (
            lambda service: service != "redis"
        )

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify Redis health was checked
        mock_health_monitor.is_service_healthy.assert_any_call("redis")

        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once()
        call_args = mock_update.message.reply_text.call_args
        assert ERROR_REDIS_UNAVAILABLE in call_args[0][0]

        # Verify reset keyboard was provided
        assert isinstance(call_args[1]["reply_markup"], ReplyKeyboardMarkup)
        assert BTN_RESET in str(call_args[1]["reply_markup"])

        # Verify email flow was not started
        bot_handler.email_flow_orchestrator.start_email_flow.assert_not_called()

    async def test_smtp_unhealthy_allows_email_flow_with_fallback(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test that SMTP being unhealthy allows email flow to proceed with chat fallback."""
        user_id = 12345

        # Mock SMTP as unhealthy, Redis as healthy
        mock_health_monitor.is_service_healthy.side_effect = (
            lambda service: service != "smtp"
        )

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify both Redis and SMTP health were checked
        mock_health_monitor.is_service_healthy.assert_any_call("redis")
        mock_health_monitor.is_service_healthy.assert_any_call("smtp")

        # Verify email flow was started (with fallback handling)
        bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once_with(
            mock_update, mock_context, user_id
        )

        # Verify no error message was sent to user (flow proceeds)
        mock_update.message.reply_text.assert_not_called()

    async def test_all_services_healthy_allows_email_flow(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test that all services being healthy allows email flow to proceed normally."""
        user_id = 12345

        # Mock all services as healthy
        mock_health_monitor.is_service_healthy.return_value = True

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify both Redis and SMTP health were checked
        mock_health_monitor.is_service_healthy.assert_any_call("redis")
        mock_health_monitor.is_service_healthy.assert_any_call("smtp")

        # Verify email flow was started
        bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once_with(
            mock_update, mock_context, user_id
        )

        # Verify no error message was sent to user
        mock_update.message.reply_text.assert_not_called()

    async def test_health_monitor_unavailable_allows_email_flow(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that health monitor being unavailable allows email flow to proceed."""
        user_id = 12345

        # Mock health monitor as unavailable (raises exception)
        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor",
            side_effect=RuntimeError("Health monitor not initialized"),
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify email flow was started despite health monitor unavailability
        bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once_with(
            mock_update, mock_context, user_id
        )

        # Verify no error message was sent to user
        mock_update.message.reply_text.assert_not_called()

    async def test_health_check_exception_allows_email_flow(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test that health check exceptions allow email flow to proceed."""
        user_id = 12345

        # Mock health check to raise exception
        mock_health_monitor.is_service_healthy.side_effect = Exception(
            "Health check failed"
        )

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify email flow was started despite health check exception
        bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once_with(
            mock_update, mock_context, user_id
        )

        # Verify no error message was sent to user
        mock_update.message.reply_text.assert_not_called()

    async def test_no_email_flow_orchestrator_shows_error(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that missing email flow orchestrator shows appropriate error."""
        user_id = 12345

        # Remove email flow orchestrator
        bot_handler.email_flow_orchestrator = None

        await bot_handler._handle_method_selection(
            mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
        )

        # Verify error message was sent
        mock_update.message.reply_text.assert_called_once_with(
            "❌ Сервис email недоступен. Попробуйте позже."
        )


class TestHealthCheckTransitions:
    """Test health check state transitions and user messaging."""

    async def test_redis_healthy_to_unhealthy_transition(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test transition from Redis healthy to unhealthy blocks subsequent requests."""
        user_id = 12345

        # First request: Redis healthy
        mock_health_monitor.is_service_healthy.return_value = True

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify first request succeeded
        bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once()

        # Reset mocks
        bot_handler.email_flow_orchestrator.start_email_flow.reset_mock()
        mock_update.message.reply_text.reset_mock()

        # Second request: Redis unhealthy
        mock_health_monitor.is_service_healthy.side_effect = (
            lambda service: service != "redis"
        )

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify second request was blocked
        bot_handler.email_flow_orchestrator.start_email_flow.assert_not_called()
        mock_update.message.reply_text.assert_called_once()

    async def test_smtp_unhealthy_to_healthy_transition(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test transition from SMTP unhealthy to healthy allows normal flow."""
        user_id = 12345

        # First request: SMTP unhealthy, Redis healthy
        mock_health_monitor.is_service_healthy.side_effect = (
            lambda service: service != "smtp"
        )

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify first request proceeded with fallback
        bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once()

        # Reset mocks
        bot_handler.email_flow_orchestrator.start_email_flow.reset_mock()

        # Second request: All services healthy
        mock_health_monitor.is_service_healthy.return_value = True

        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            await bot_handler._handle_method_selection(
                mock_update, mock_context, user_id, BTN_EMAIL_DELIVERY
            )

        # Verify second request proceeded normally
        bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])



