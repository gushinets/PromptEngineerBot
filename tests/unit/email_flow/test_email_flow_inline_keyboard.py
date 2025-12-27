"""
Unit tests for email flow inline keyboard functionality.

This module tests that the OTP sent message includes the data agreement
inline keyboard with the correct URL.

Validates: Requirements 2.1, 2.4
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import InlineKeyboardMarkup

from telegram_bot.utils.messages import (
    DATA_AGREEMENT_KEYBOARD,
    DATA_AGREEMENT_URL,
)


class TestEmailFlowInlineKeyboard:
    """Test cases for email flow inline keyboard functionality."""

    def test_data_agreement_keyboard_is_inline_keyboard_markup(self):
        """Test that DATA_AGREEMENT_KEYBOARD is an InlineKeyboardMarkup.

        Validates: Requirements 2.1
        """
        assert isinstance(DATA_AGREEMENT_KEYBOARD, InlineKeyboardMarkup)

    def test_data_agreement_keyboard_has_one_row(self):
        """Test that DATA_AGREEMENT_KEYBOARD has exactly one row.

        Validates: Requirements 2.1
        """
        assert len(DATA_AGREEMENT_KEYBOARD.inline_keyboard) == 1

    def test_data_agreement_keyboard_has_one_button(self):
        """Test that DATA_AGREEMENT_KEYBOARD has exactly one button.

        Validates: Requirements 2.1
        """
        assert len(DATA_AGREEMENT_KEYBOARD.inline_keyboard[0]) == 1

    def test_data_agreement_keyboard_button_has_correct_url(self):
        """Test that the agreement button has the correct URL.

        Validates: Requirements 2.4
        """
        button = DATA_AGREEMENT_KEYBOARD.inline_keyboard[0][0]
        assert button.url == DATA_AGREEMENT_URL
        assert button.url == "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"

    def test_data_agreement_url_constant(self):
        """Test that DATA_AGREEMENT_URL is the expected value.

        Validates: Requirements 2.4
        """
        assert DATA_AGREEMENT_URL == "https://disk.yandex.ru/i/zGiuY7mtIfOA-Q"


class TestEmailFlowHandleEmailInputInlineKeyboard:
    """Test cases for handle_email_input inline keyboard integration."""

    @pytest.fixture
    def mock_email_flow_orchestrator(self):
        """Create a mock EmailFlowOrchestrator with necessary dependencies."""
        from telegram_bot.utils.config import BotConfig

        # Create mock dependencies
        mock_config = MagicMock(spec=BotConfig)
        mock_config.followup_timeout_seconds = 300

        mock_llm_client = MagicMock()
        mock_conversation_manager = MagicMock()
        mock_state_manager = MagicMock()
        mock_state_manager.get_email_flow_data.return_value = {"original_prompt": "test prompt"}

        # Create orchestrator with mocked dependencies
        with (
            patch("telegram_bot.flows.email_flow.get_auth_service") as mock_auth,
            patch("telegram_bot.flows.email_flow.get_email_service") as mock_email,
            patch("telegram_bot.flows.email_flow.get_redis_client") as mock_redis,
        ):
            mock_auth_service = MagicMock()
            mock_auth_service.validate_email_format.return_value = True
            mock_auth_service.send_otp.return_value = (True, "otp_sent", "123456")
            mock_auth.return_value = mock_auth_service

            mock_email_service = MagicMock()
            mock_email_result = MagicMock()
            mock_email_result.success = True
            mock_email_service.send_otp_email = AsyncMock(return_value=mock_email_result)
            mock_email.return_value = mock_email_service

            mock_redis.return_value = MagicMock()

            from telegram_bot.flows.email_flow import EmailFlowOrchestrator

            orchestrator = EmailFlowOrchestrator(
                config=mock_config,
                llm_client=mock_llm_client,
                conversation_manager=mock_conversation_manager,
                state_manager=mock_state_manager,
            )

            yield orchestrator

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram Update object."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.message = MagicMock()
        update.message.reply_text = AsyncMock(return_value=None)
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram Context object."""
        return MagicMock()

    @pytest.mark.asyncio
    async def test_handle_email_input_sends_inline_keyboard(
        self, mock_email_flow_orchestrator, mock_update, mock_context
    ):
        """Test that handle_email_input sends the inline keyboard with OTP message.

        Validates: Requirements 2.1
        """
        user_id = 12345
        email = "test@example.com"

        result = await mock_email_flow_orchestrator.handle_email_input(
            mock_update, mock_context, user_id, email
        )

        assert result is True

        # Verify reply_text was called with inline keyboard
        calls = mock_update.message.reply_text.call_args_list

        # Find the call that includes the inline keyboard
        keyboard_call_found = False
        for call in calls:
            kwargs = call.kwargs if call.kwargs else {}
            if "reply_markup" in kwargs:
                reply_markup = kwargs["reply_markup"]
                if isinstance(reply_markup, InlineKeyboardMarkup):
                    keyboard_call_found = True
                    break

        assert keyboard_call_found, "Expected inline keyboard to be sent with OTP message"

    @pytest.mark.asyncio
    async def test_handle_email_input_inline_keyboard_has_correct_url(
        self, mock_email_flow_orchestrator, mock_update, mock_context
    ):
        """Test that the inline keyboard sent has the correct agreement URL.

        Validates: Requirements 2.4
        """
        user_id = 12345
        email = "test@example.com"

        result = await mock_email_flow_orchestrator.handle_email_input(
            mock_update, mock_context, user_id, email
        )

        assert result is True

        # Verify the inline keyboard has the correct URL
        calls = mock_update.message.reply_text.call_args_list

        correct_url_found = False
        for call in calls:
            kwargs = call.kwargs if call.kwargs else {}
            if "reply_markup" in kwargs:
                reply_markup = kwargs["reply_markup"]
                if isinstance(reply_markup, InlineKeyboardMarkup):
                    # Check the button URL
                    if reply_markup.inline_keyboard:
                        button = reply_markup.inline_keyboard[0][0]
                        if button.url == DATA_AGREEMENT_URL:
                            correct_url_found = True
                            break

        assert correct_url_found, f"Expected inline keyboard button URL to be {DATA_AGREEMENT_URL}"
