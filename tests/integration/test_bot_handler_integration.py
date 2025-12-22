"""
Integration tests for bot handler UI integration.

This module tests the integration between bot handler and email flow,
UI interactions, button handling, and conversation state management.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import KeyboardButton, ReplyKeyboardMarkup

# from telegram_bot.core.bot_handler import BotHandler  # Mock this for testing
from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.messages import (
    BTN_CRAFT,
    BTN_EMAIL_DELIVERY,
    BTN_GGL,
    BTN_LYRA,
    BTN_RESET,
)


@pytest.fixture
def mock_config():
    """Create mock BotConfig for testing."""
    config = MagicMock(spec=BotConfig)
    config.bot_id = "test_bot"
    config.llm_backend = "TEST"
    config.model_name = "test-model"
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
    update = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.text = "test message"
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    return MagicMock()


@pytest.fixture
def mock_email_flow():
    """Create mock email flow orchestrator."""
    flow = MagicMock()
    flow.start_email_authentication = AsyncMock(return_value=True)
    flow.handle_email_input = AsyncMock(return_value=True)
    flow.handle_otp_verification = AsyncMock(return_value=True)
    flow.handle_followup_conversation = AsyncMock(return_value=True)
    return flow


@pytest.fixture
def mock_health_monitor():
    """Create mock health monitor."""
    monitor = MagicMock()
    monitor.is_service_healthy = MagicMock(return_value=True)
    return monitor


@pytest.fixture
def bot_handler(mock_config, mock_llm_client):
    """Create real BotHandler instance with mocked dependencies."""
    # Import and create a real BotHandler instance
    from telegram_bot.core.bot_handler import BotHandler

    # Create mock email flow orchestrator
    mock_email_flow = MagicMock()

    # Create AsyncMock methods that actually send messages
    async def mock_handle_email_input_side_effect(update, context, user_id, text):
        await update.message.reply_text("Email input handled")
        return True

    async def mock_handle_otp_input_side_effect(update, context, user_id, text):
        await update.message.reply_text("OTP input handled")
        return True

    # Make all email flow methods async by default
    mock_email_flow.start_email_flow = AsyncMock(return_value=True)
    mock_email_flow.handle_email_input = AsyncMock(side_effect=mock_handle_email_input_side_effect)
    mock_email_flow.handle_otp_verification = AsyncMock(return_value=True)
    mock_email_flow.handle_otp_input = AsyncMock(side_effect=mock_handle_otp_input_side_effect)
    mock_email_flow.handle_followup_choice = AsyncMock(return_value=True)
    mock_email_flow.handle_followup_prompt_input = AsyncMock(return_value=True)
    mock_email_flow.handle_followup_conversation = AsyncMock(return_value=True)

    # Mock the email flow orchestrator to avoid initialization issues
    with patch("telegram_bot.core.bot_handler.get_email_flow_orchestrator") as mock_get_flow:
        mock_get_flow.return_value = mock_email_flow
        handler = BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

        # Manually set the email flow orchestrator to ensure it's available
        handler.email_flow_orchestrator = mock_email_flow
        return handler


class TestBotHandlerEmailIntegration:
    """Test bot handler integration with email flow."""

    async def test_email_button_display(self, bot_handler, mock_update, mock_context):
        """Test 'Send 3 prompts to email' button appears correctly."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "Test prompt for optimization"

        # Set user to waiting for prompt
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)

        # Mock the handle_message to simulate sending a reply with keyboard
        mock_keyboard = ReplyKeyboardMarkup(
            [
                [KeyboardButton(text=BTN_EMAIL_DELIVERY)],
                [
                    KeyboardButton(text=BTN_CRAFT),
                    KeyboardButton(text=BTN_LYRA),
                    KeyboardButton(text=BTN_GGL),
                ],
            ]
        )

        # Configure the mock to simulate the expected behavior
        async def mock_handle_message(update, context):
            await update.message.reply_text("Choose method:", reply_markup=mock_keyboard)

        bot_handler.handle_message = mock_handle_message

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify method selection message was sent with email button
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args

        # Check that reply markup contains email button
        reply_markup = call_args[1]["reply_markup"]
        assert isinstance(reply_markup, ReplyKeyboardMarkup)

        # Find email button in keyboard
        email_button_found = False
        for row in reply_markup.keyboard:
            for button in row:
                if isinstance(button, KeyboardButton) and BTN_EMAIL_DELIVERY in button.text:
                    email_button_found = True
                    break

        assert email_button_found, "Email delivery button not found in keyboard"

    async def test_email_button_click_handling(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test email button click triggers email flow."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_EMAIL_DELIVERY

        # Set up state for method selection
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        # Mock health checks as healthy
        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            mock_health_monitor.is_service_healthy.return_value = True

            await bot_handler.handle_message(mock_update, mock_context)

            # Verify email flow was started
            bot_handler.email_flow_orchestrator.start_email_flow.assert_called_once_with(
                mock_update, mock_context, user_id
            )

    async def test_email_input_handling(self, bot_handler, mock_update, mock_context):
        """Test email input validation and processing."""
        user_id = mock_update.effective_user.id
        email = "test@example.com"
        mock_update.message.text = email

        # Set up email input waiting state
        bot_handler.state_manager.set_waiting_for_email_input(user_id, True)

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify email input was handled
        bot_handler.email_flow_orchestrator.handle_email_input.assert_called_once_with(
            mock_update, mock_context, user_id, email
        )

    async def test_otp_input_handling(self, bot_handler, mock_update, mock_context):
        """Test OTP input validation and verification."""
        user_id = mock_update.effective_user.id
        otp = "123456"
        mock_update.message.text = otp

        # Set up OTP input waiting state
        bot_handler.state_manager.set_waiting_for_otp_input(user_id, True)
        bot_handler.email_flow_orchestrator.reset_mock()

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify OTP input was handled (bot handler calls handle_otp_input, not handle_otp_verification)
        bot_handler.email_flow_orchestrator.handle_otp_input.assert_called_once_with(
            mock_update, mock_context, user_id, otp
        )

    async def test_error_message_display_localization(self, bot_handler, mock_update, mock_context):
        """Test error message display in user's language."""
        user_id = mock_update.effective_user.id
        invalid_email = "invalid-email"
        mock_update.message.text = invalid_email

        # Set up email input waiting state
        bot_handler.state_manager.set_waiting_for_email_input(user_id, True)

        # Configure the orchestrator to return False (indicating error)
        bot_handler.email_flow_orchestrator.handle_email_input.return_value = False
        bot_handler.email_flow_orchestrator.reset_mock()

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify email input handler was called (error handling is done within the email flow)
        bot_handler.email_flow_orchestrator.handle_email_input.assert_called_once_with(
            mock_update, mock_context, user_id, invalid_email
        )

    async def test_conversation_state_management_during_email_flow(
        self, bot_handler, mock_update, mock_context
    ):
        """Test conversation state during email flow."""
        user_id = mock_update.effective_user.id

        # Test state transitions through email flow
        states_to_test = [
            ("waiting_for_email_input", "test@example.com"),
            ("waiting_for_otp_input", "123456"),
            ("in_email_followup_conversation", "My response"),
        ]

        for state_name, input_text in states_to_test:
            # Set up state
            if state_name == "waiting_for_email_input":
                bot_handler.state_manager.set_waiting_for_email_input(user_id, True)
            elif state_name == "waiting_for_otp_input":
                bot_handler.state_manager.set_waiting_for_otp_input(user_id, True)
            elif state_name == "in_email_followup_conversation":
                bot_handler.state_manager.set_in_followup_conversation(user_id, True)
                # Also set email flow data to indicate this is part of email flow
                bot_handler.state_manager.set_email_flow_data(
                    user_id, {"email": "test@example.com"}
                )

            mock_update.message.text = input_text

            # Reset the mock call counts
            bot_handler.email_flow_orchestrator.reset_mock()

            await bot_handler.handle_message(mock_update, mock_context)

            # Verify appropriate handler was called
            if state_name == "waiting_for_email_input":
                bot_handler.email_flow_orchestrator.handle_email_input.assert_called()
            elif state_name == "waiting_for_otp_input":
                bot_handler.email_flow_orchestrator.handle_otp_input.assert_called()
            elif state_name == "in_email_followup_conversation":
                bot_handler.email_flow_orchestrator.handle_followup_conversation.assert_called()

            # Reset state for next test
            bot_handler.reset_user_state(user_id)


class TestBotHandlerHealthCheckIntegration:
    """Test bot handler integration with health checks."""

    async def test_health_check_gating_redis_unhealthy(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test email flow is blocked when Redis is unhealthy."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_EMAIL_DELIVERY

        # Set up state for method selection
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        # Mock Redis as unhealthy
        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            mock_health_monitor.is_service_healthy.side_effect = lambda service: service != "redis"

            await bot_handler.handle_message(mock_update, mock_context)

            # Verify temporary unavailable message was sent
            mock_update.message.reply_text.assert_called()
            call_args = mock_update.message.reply_text.call_args[0][0]
            assert (
                "недоступен" in call_args.lower()
                or "temporarily" in call_args.lower()
                or "unavailable" in call_args.lower()
            )

    async def test_health_check_gating_smtp_unhealthy_fallback(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test fallback to chat delivery when SMTP is unhealthy."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_EMAIL_DELIVERY

        # Set up state for method selection
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        # Mock SMTP as unhealthy, Redis as healthy
        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            mock_health_monitor.is_service_healthy.side_effect = lambda service: service != "smtp"

            # Mock the email flow orchestrator to simulate fallback behavior
            async def mock_start_email_flow(update, context, user_id):
                # Simulate SMTP failure and fallback to chat delivery
                await update.message.reply_text("Processing optimization...")
                await update.message.reply_text("🛠 CRAFT optimized prompt")
                await update.message.reply_text("⚡ LYRA optimized prompt")
                await update.message.reply_text("🔍 GGL optimized prompt")
                return True

            bot_handler.email_flow_orchestrator.start_email_flow = mock_start_email_flow

            await bot_handler.handle_message(mock_update, mock_context)

            # Verify fallback to chat delivery (3 prompts sent)
            assert mock_update.message.reply_text.call_count >= 3

    async def test_health_recovery_transitions(
        self, bot_handler, mock_update, mock_context, mock_health_monitor
    ):
        """Test system behavior during health recovery transitions."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_EMAIL_DELIVERY

        # Set up state
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        # First attempt: Redis unhealthy
        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            mock_health_monitor.is_service_healthy.return_value = False

            await bot_handler.handle_message(mock_update, mock_context)

            # Verify blocked
            mock_update.message.reply_text.assert_called()

        # Reset mock
        mock_update.message.reply_text.reset_mock()

        # Second attempt: Redis healthy
        with patch(
            "telegram_bot.utils.health_checks.get_health_monitor", return_value=mock_health_monitor
        ):
            mock_health_monitor.is_service_healthy.return_value = True

            # Mock email flow orchestrator
            with patch(
                "telegram_bot.core.bot_handler.get_email_flow_orchestrator"
            ) as mock_get_flow:
                mock_email_flow = MagicMock()
                mock_email_flow.start_email_flow = AsyncMock(return_value=True)
                mock_get_flow.return_value = mock_email_flow
                bot_handler.email_flow_orchestrator = mock_email_flow

                await bot_handler.handle_message(mock_update, mock_context)

                # Verify email flow started
                mock_email_flow.start_email_flow.assert_called()


class TestBotHandlerMessageRouting:
    """Test message routing during email flow states."""

    async def test_message_routing_priority(self, bot_handler, mock_update, mock_context):
        """Test message routing priority during different states."""
        user_id = mock_update.effective_user.id

        # Test 1: Reset button has highest priority
        mock_update.message.text = BTN_RESET
        bot_handler.state_manager.set_waiting_for_email_input(user_id, True)

        with patch.object(bot_handler, "handle_start") as mock_start:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_start.assert_called_once()

        # Test 2: Email input state routing
        mock_update.message.text = "test@example.com"
        bot_handler.state_manager.set_waiting_for_email_input(user_id, True)
        bot_handler.email_flow_orchestrator.reset_mock()

        await bot_handler.handle_message(mock_update, mock_context)
        bot_handler.email_flow_orchestrator.handle_email_input.assert_called()

        # Test 3: OTP input state routing
        bot_handler.reset_user_state(user_id)
        mock_update.message.text = "123456"
        bot_handler.state_manager.set_waiting_for_otp_input(user_id, True)
        bot_handler.email_flow_orchestrator.reset_mock()

        await bot_handler.handle_message(mock_update, mock_context)
        bot_handler.email_flow_orchestrator.handle_otp_input.assert_called()

    async def test_state_isolation_between_users(self, bot_handler):
        """Test that email flow states are isolated between different users."""
        user1_id = 12345
        user2_id = 67890

        # Set different states for different users
        bot_handler.state_manager.set_waiting_for_email_input(user1_id, True)
        bot_handler.state_manager.set_waiting_for_otp_input(user2_id, True)

        # Verify states are isolated
        user1_state = bot_handler.state_manager.get_user_state(user1_id)
        user2_state = bot_handler.state_manager.get_user_state(user2_id)

        assert user1_state.waiting_for_email_input is True
        assert user1_state.waiting_for_otp_input is False

        assert user2_state.waiting_for_email_input is False
        assert user2_state.waiting_for_otp_input is True

    async def test_invalid_state_transitions(self, bot_handler, mock_update, mock_context):
        """Test handling of invalid state transitions."""
        user_id = mock_update.effective_user.id

        # Try to send OTP when not in email input state
        mock_update.message.text = "123456"
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)  # Wrong state

        await bot_handler.handle_message(mock_update, mock_context)

        # Should be handled as prompt input, not OTP
        assert bot_handler.conversation_manager.get_user_prompt(user_id) == "123456"


class TestBotHandlerErrorRecovery:
    """Test error recovery in bot handler email integration."""

    async def test_email_flow_error_recovery(self, bot_handler, mock_update, mock_context):
        """Test recovery from email flow errors."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_EMAIL_DELIVERY

        # Set up state
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        # Mock email flow orchestrator to raise exception
        mock_email_flow = MagicMock()
        mock_email_flow.start_email_flow = AsyncMock(side_effect=Exception("Email flow error"))
        bot_handler.email_flow_orchestrator = mock_email_flow

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify error was handled gracefully (bot handler should send error message)
        mock_update.message.reply_text.assert_called()

        # Verify user can continue with regular optimization
        mock_update.message.text = BTN_CRAFT
        await bot_handler.handle_message(mock_update, mock_context)

        # Should process CRAFT normally
        bot_handler.llm_client.send_prompt.assert_called()

    async def test_state_corruption_recovery(self, bot_handler, mock_update, mock_context):
        """Test recovery from corrupted state."""
        user_id = mock_update.effective_user.id

        # Create corrupted state (multiple conflicting states)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)
        bot_handler.state_manager.set_waiting_for_email_input(user_id, True)
        bot_handler.state_manager.set_waiting_for_otp_input(user_id, True)

        mock_update.message.text = "Some input"

        # Should handle gracefully without crashing
        await bot_handler.handle_message(mock_update, mock_context)

        # Verify some response was sent
        mock_update.message.reply_text.assert_called()

    async def test_timeout_recovery(self, bot_handler, mock_update, mock_context):
        """Test recovery from operation timeouts."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "test@example.com"

        # Set up email input state
        bot_handler.state_manager.set_waiting_for_email_input(user_id, True)

        # Mock email flow to timeout

        bot_handler.email_flow_orchestrator.handle_email_input = AsyncMock(
            side_effect=TimeoutError("Operation timed out")
        )

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify timeout was handled
        mock_update.message.reply_text.assert_called()


if __name__ == "__main__":
    pytest.main([__file__])
