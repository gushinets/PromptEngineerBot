"""
Integration tests for email flow inline button functionality.

This module tests the inline button implementation for follow-up choice
in the email flow, ensuring the same behavior as the regular flow.

Validates: Requirements 8.1, 8.4, 8.5, 8.7
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import CallbackQuery, InlineKeyboardMarkup, Update, User
from telegram.ext import ContextTypes

from telegram_bot.flows.email_flow import EmailFlowOrchestrator
from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.messages import (
    BTN_NO,
    BTN_YES,
    CALLBACK_FOLLOWUP_NO,
    CALLBACK_FOLLOWUP_YES,
    FOLLOWUP_CHOICE_INLINE_KEYBOARD,
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
    client.send_prompt = AsyncMock(return_value="LLM response with questions")
    client.get_last_usage = MagicMock(
        return_value={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )
    return client


@pytest.fixture
def mock_conversation_manager():
    """Create mock conversation manager."""
    manager = MagicMock()
    manager.start_followup_conversation = MagicMock()
    manager.get_transcript = MagicMock(return_value=[])
    manager.append_message = MagicMock()
    manager.accumulate_token_usage = MagicMock()
    manager.reset_token_totals = MagicMock()
    manager.prompt_loader = MagicMock()
    manager.prompt_loader.followup_prompt = "Follow-up system prompt"
    manager.prompt_loader.craft_prompt = "CRAFT system prompt"
    return manager


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    manager = MagicMock()

    # Create a mock user state
    user_state = MagicMock()
    user_state.waiting_for_followup_choice = True
    manager.get_user_state = MagicMock(return_value=user_state)

    manager.set_in_followup_conversation = MagicMock()
    manager.set_waiting_for_followup_choice = MagicMock()
    manager.get_improved_prompt_cache = MagicMock(return_value="Improved prompt")
    manager.get_email_flow_data = MagicMock(
        return_value={"original_prompt": "Original prompt", "email": "test@example.com"}
    )
    manager.set_improved_prompt_cache = MagicMock()
    return manager


@pytest.fixture
def mock_update_with_callback():
    """Create mock Telegram update with callback query."""
    update = MagicMock(spec=Update)

    # Create callback query
    query = MagicMock(spec=CallbackQuery)
    query.from_user = MagicMock(spec=User)
    query.from_user.id = 12345
    query.data = CALLBACK_FOLLOWUP_YES
    query.answer = AsyncMock()
    query.message = MagicMock()
    query.edit_message_reply_markup = AsyncMock()

    update.callback_query = query
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()

    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.fixture
def email_flow_orchestrator(
    mock_config, mock_llm_client, mock_conversation_manager, mock_state_manager
):
    """Create EmailFlowOrchestrator with mocked dependencies."""
    with (
        patch("telegram_bot.flows.email_flow.get_auth_service") as mock_auth,
        patch("telegram_bot.flows.email_flow.get_email_service") as mock_email,
        patch("telegram_bot.flows.email_flow.get_redis_client") as mock_redis,
    ):
        mock_auth_service = MagicMock()
        mock_auth_service.is_user_authenticated.return_value = False
        mock_auth.return_value = mock_auth_service

        mock_email_service = MagicMock()
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service.send_otp_email = AsyncMock(return_value=mock_email_result)
        mock_email.return_value = mock_email_service

        mock_redis.return_value = MagicMock()

        orchestrator = EmailFlowOrchestrator(
            config=mock_config,
            llm_client=mock_llm_client,
            conversation_manager=mock_conversation_manager,
            state_manager=mock_state_manager,
        )

        yield orchestrator


class TestEmailFlowInlineKeyboardConstants:
    """Test that inline keyboard constants are properly defined."""

    def test_followup_choice_inline_keyboard_is_inline_keyboard_markup(self):
        """Test that FOLLOWUP_CHOICE_INLINE_KEYBOARD is an InlineKeyboardMarkup.

        Validates: Requirements 8.1
        """
        assert isinstance(FOLLOWUP_CHOICE_INLINE_KEYBOARD, InlineKeyboardMarkup)

    def test_followup_choice_inline_keyboard_has_two_buttons(self):
        """Test that FOLLOWUP_CHOICE_INLINE_KEYBOARD has two buttons side by side.

        Validates: Requirements 8.2
        """
        assert len(FOLLOWUP_CHOICE_INLINE_KEYBOARD.inline_keyboard) == 1
        assert len(FOLLOWUP_CHOICE_INLINE_KEYBOARD.inline_keyboard[0]) == 2

    def test_followup_choice_inline_keyboard_callback_data(self):
        """Test that inline buttons have correct callback data.

        Validates: Requirements 8.3
        """
        yes_button = FOLLOWUP_CHOICE_INLINE_KEYBOARD.inline_keyboard[0][0]
        no_button = FOLLOWUP_CHOICE_INLINE_KEYBOARD.inline_keyboard[0][1]

        assert yes_button.callback_data == CALLBACK_FOLLOWUP_YES
        assert no_button.callback_data == CALLBACK_FOLLOWUP_NO


class TestEmailFlowFollowupCallback:
    """Test callback handler for follow-up choice in email flow."""

    @pytest.mark.asyncio
    async def test_handle_followup_callback_yes(
        self, email_flow_orchestrator, mock_update_with_callback, mock_context
    ):
        """Test handling YES callback in email flow.

        Validates: Requirements 8.4, 8.7
        """
        mock_update_with_callback.callback_query.data = CALLBACK_FOLLOWUP_YES

        # Mock the _process_followup_llm_request to avoid full LLM call
        email_flow_orchestrator._process_followup_llm_request = AsyncMock(return_value=True)

        result = await email_flow_orchestrator.handle_followup_callback(
            mock_update_with_callback, mock_context
        )

        # Verify callback was answered
        mock_update_with_callback.callback_query.answer.assert_called_once()

        # Verify buttons were disabled
        mock_update_with_callback.callback_query.edit_message_reply_markup.assert_called_once()

        assert result is True

    @pytest.mark.asyncio
    async def test_handle_followup_callback_no(
        self, email_flow_orchestrator, mock_update_with_callback, mock_context
    ):
        """Test handling NO callback in email flow.

        Validates: Requirements 8.4, 8.7
        """
        mock_update_with_callback.callback_query.data = CALLBACK_FOLLOWUP_NO

        # Mock the _run_optimization_and_email_delivery to avoid full flow
        email_flow_orchestrator._run_optimization_and_email_delivery = AsyncMock(return_value=True)

        result = await email_flow_orchestrator.handle_followup_callback(
            mock_update_with_callback, mock_context
        )

        # Verify callback was answered
        mock_update_with_callback.callback_query.answer.assert_called_once()

        # Verify buttons were disabled
        mock_update_with_callback.callback_query.edit_message_reply_markup.assert_called_once()

        assert result is True

    @pytest.mark.asyncio
    async def test_handle_followup_callback_invalid_state(
        self, email_flow_orchestrator, mock_update_with_callback, mock_context
    ):
        """Test callback is ignored when user is not in follow-up choice state.

        Validates: Requirements 8.4
        """
        # Set user state to not waiting for follow-up choice
        user_state = MagicMock()
        user_state.waiting_for_followup_choice = False
        email_flow_orchestrator.state_manager.get_user_state.return_value = user_state

        result = await email_flow_orchestrator.handle_followup_callback(
            mock_update_with_callback, mock_context
        )

        # Verify callback was answered but no further processing
        mock_update_with_callback.callback_query.answer.assert_called_once()
        mock_update_with_callback.callback_query.edit_message_reply_markup.assert_not_called()

        assert result is False


class TestEmailFlowDisableButtons:
    """Test button disabling functionality in email flow."""

    @pytest.mark.asyncio
    async def test_disable_followup_buttons_yes_selected(
        self, email_flow_orchestrator, mock_update_with_callback
    ):
        """Test that buttons are disabled with YES selected.

        Validates: Requirements 8.5
        """
        query = mock_update_with_callback.callback_query

        await email_flow_orchestrator._disable_followup_buttons(query, selected="yes")

        # Verify edit_message_reply_markup was called
        query.edit_message_reply_markup.assert_called_once()

        # Get the keyboard that was passed
        call_args = query.edit_message_reply_markup.call_args
        keyboard = call_args.kwargs["reply_markup"]

        # Verify it's an InlineKeyboardMarkup
        assert isinstance(keyboard, InlineKeyboardMarkup)

        # Verify YES button has checkmark
        yes_button = keyboard.inline_keyboard[0][0]
        assert "✓" in yes_button.text
        assert BTN_YES in yes_button.text

        # Verify both buttons have "disabled" callback data
        no_button = keyboard.inline_keyboard[0][1]
        assert yes_button.callback_data == "disabled"
        assert no_button.callback_data == "disabled"

    @pytest.mark.asyncio
    async def test_disable_followup_buttons_no_selected(
        self, email_flow_orchestrator, mock_update_with_callback
    ):
        """Test that buttons are disabled with NO selected.

        Validates: Requirements 8.5
        """
        query = mock_update_with_callback.callback_query

        await email_flow_orchestrator._disable_followup_buttons(query, selected="no")

        # Verify edit_message_reply_markup was called
        query.edit_message_reply_markup.assert_called_once()

        # Get the keyboard that was passed
        call_args = query.edit_message_reply_markup.call_args
        keyboard = call_args.kwargs["reply_markup"]

        # Verify NO button has checkmark
        no_button = keyboard.inline_keyboard[0][1]
        assert "✓" in no_button.text
        assert BTN_NO in no_button.text

        # Verify both buttons have "disabled" callback data
        yes_button = keyboard.inline_keyboard[0][0]
        assert yes_button.callback_data == "disabled"
        assert no_button.callback_data == "disabled"


class TestEmailFlowStartFollowupQuestionsInlineKeyboard:
    """Test that _start_followup_questions uses inline keyboard."""

    @pytest.mark.asyncio
    async def test_start_followup_questions_uses_inline_keyboard(
        self, email_flow_orchestrator, mock_context
    ):
        """Test that follow-up offer uses inline keyboard.

        Validates: Requirements 8.1, 8.6, 8.7
        """
        # Create mock update
        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()

        user_id = 12345

        # Mock _get_improved_prompt to return a prompt
        email_flow_orchestrator._get_improved_prompt = AsyncMock(return_value="Improved prompt")

        result = await email_flow_orchestrator._start_followup_questions(
            update, mock_context, user_id
        )

        assert result is True

        # Verify reply_text was called at least twice (processing message with reset keyboard + offer message with inline buttons)
        assert update.message.reply_text.call_count >= 2

        # Check that inline keyboard was used for the offer message
        # and reset keyboard was attached to the processing message
        calls = update.message.reply_text.call_args_list

        inline_keyboard_found = False
        reset_keyboard_found = False

        for call in calls:
            kwargs = call.kwargs if call.kwargs else {}
            if "reply_markup" in kwargs:
                reply_markup = kwargs["reply_markup"]
                if isinstance(reply_markup, InlineKeyboardMarkup):
                    inline_keyboard_found = True
                    # Verify it's the follow-up choice inline keyboard
                    assert len(reply_markup.inline_keyboard) == 1
                    assert len(reply_markup.inline_keyboard[0]) == 2
                elif hasattr(reply_markup, "keyboard"):
                    # Check if it's the reset keyboard (attached to processing message)
                    reset_keyboard_found = True

        assert inline_keyboard_found, "Expected inline keyboard to be sent with follow-up offer"
        assert reset_keyboard_found, "Expected reset keyboard to be attached to processing message"
