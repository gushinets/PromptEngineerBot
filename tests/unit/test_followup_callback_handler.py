"""Tests for the follow-up callback handler functionality.

This module tests the handle_followup_callback method in BotHandler
which processes inline button callbacks for follow-up choice (YES/NO).

Requirements: 8.4
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_bot.core.bot_handler import BotHandler
from telegram_bot.utils.messages import (
    CALLBACK_FOLLOWUP_NO,
    CALLBACK_FOLLOWUP_YES,
    FOLLOWUP_DECLINED_MESSAGE,
)
from tests.unit.test_utils import create_mock_config, create_mock_llm_client


class TestFollowupCallbackHandler:
    """Test cases for handle_followup_callback method.

    These tests verify that the callback handler correctly processes
    inline button callbacks for follow-up choice (YES/NO).

    Requirements: 8.4
    """

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = create_mock_llm_client()
        client.send_prompt = AsyncMock(return_value="What is your main goal?")
        client.get_last_usage = MagicMock(
            return_value={"prompt_tokens": 100, "completion_tokens": 50}
        )
        return client

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query for inline button clicks."""
        query = MagicMock()
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.data = CALLBACK_FOLLOWUP_YES
        query.answer = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Create a mock Telegram update with callback query."""
        update = MagicMock()
        update.callback_query = mock_callback_query
        update.effective_user = mock_callback_query.from_user
        # For _safe_reply to work, we need message attribute
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context."""
        return MagicMock()

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        """Create a BotHandler instance with mocked dependencies."""
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    @pytest.mark.asyncio
    async def test_callback_answers_query_immediately(
        self, bot_handler, mock_update_with_callback, mock_context
    ):
        """Test that callback query is answered immediately to remove loading indicator.

        Validates: Requirements 8.4
        """
        user_id = mock_update_with_callback.callback_query.from_user.id

        # Set up state for follow-up choice
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        await bot_handler.handle_followup_callback(mock_update_with_callback, mock_context)

        # Verify callback query was answered
        mock_update_with_callback.callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_callback_yes_processes_followup_yes(
        self, bot_handler, mock_update_with_callback, mock_context
    ):
        """Test that YES callback triggers _process_followup_yes.

        Validates: Requirements 8.4
        """
        user_id = mock_update_with_callback.callback_query.from_user.id
        mock_update_with_callback.callback_query.data = CALLBACK_FOLLOWUP_YES

        # Set up state for follow-up choice
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        with patch.object(bot_handler, "_process_followup_yes") as mock_process_yes:
            mock_process_yes.return_value = None

            await bot_handler.handle_followup_callback(mock_update_with_callback, mock_context)

            mock_process_yes.assert_called_once_with(mock_update_with_callback, user_id)

    @pytest.mark.asyncio
    async def test_callback_no_processes_followup_no(
        self, bot_handler, mock_update_with_callback, mock_context
    ):
        """Test that NO callback triggers _process_followup_no.

        Validates: Requirements 8.4
        """
        user_id = mock_update_with_callback.callback_query.from_user.id
        mock_update_with_callback.callback_query.data = CALLBACK_FOLLOWUP_NO

        # Set up state for follow-up choice
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        with patch.object(bot_handler, "_process_followup_no") as mock_process_no:
            mock_process_no.return_value = None

            await bot_handler.handle_followup_callback(mock_update_with_callback, mock_context)

            mock_process_no.assert_called_once_with(mock_update_with_callback, user_id)

    @pytest.mark.asyncio
    async def test_callback_ignores_invalid_state(
        self, bot_handler, mock_update_with_callback, mock_context
    ):
        """Test that callback is ignored when user is not in follow-up choice state.

        Validates: Requirements 8.4
        """
        user_id = mock_update_with_callback.callback_query.from_user.id
        mock_update_with_callback.callback_query.data = CALLBACK_FOLLOWUP_YES

        # User is NOT in follow-up choice state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, False)

        with patch.object(bot_handler, "_process_followup_yes") as mock_process_yes:
            await bot_handler.handle_followup_callback(mock_update_with_callback, mock_context)

            # Callback should be answered but processing should not happen
            mock_update_with_callback.callback_query.answer.assert_called_once()
            mock_process_yes.assert_not_called()


class TestProcessFollowupYes:
    """Test cases for _process_followup_yes method.

    These tests verify the core logic for accepting follow-up questions.

    Requirements: 8.4
    """

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = create_mock_llm_client()
        client.send_prompt = AsyncMock(return_value="What is your main goal?")
        client.get_last_usage = MagicMock(
            return_value={"prompt_tokens": 100, "completion_tokens": 50}
        )
        return client

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        """Create a BotHandler instance with mocked dependencies."""
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    @pytest.mark.asyncio
    async def test_process_followup_yes_starts_conversation(self, bot_handler, mock_update):
        """Test that _process_followup_yes starts follow-up conversation.

        Validates: Requirements 8.4
        """
        user_id = 12345

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        await bot_handler._process_followup_yes(mock_update, user_id)

        # Verify state transition
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is True

    @pytest.mark.asyncio
    async def test_process_followup_yes_handles_missing_cache(self, bot_handler, mock_update):
        """Test that _process_followup_yes handles missing cached prompt gracefully.

        Validates: Requirements 8.4
        """
        user_id = 12345

        # Set up state WITHOUT cached prompt
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, None)

        await bot_handler._process_followup_yes(mock_update, user_id)

        # Verify fallback behavior - state should be reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True


class TestProcessFollowupNo:
    """Test cases for _process_followup_no method.

    These tests verify the core logic for declining follow-up questions.

    Requirements: 8.4
    """

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = create_mock_llm_client()
        return client

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 12345
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        """Create a BotHandler instance with mocked dependencies."""
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    @pytest.mark.asyncio
    async def test_process_followup_no_resets_state(self, bot_handler, mock_update):
        """Test that _process_followup_no resets state to prompt input.

        Validates: Requirements 8.4
        """
        user_id = 12345

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")
        bot_handler.state_manager.set_cached_method_name(user_id, "CRAFT")

        await bot_handler._process_followup_no(mock_update, user_id)

        # Verify state reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.waiting_for_prompt is True
        assert bot_handler.state_manager.get_improved_prompt_cache(user_id) is None
        assert bot_handler.state_manager.get_cached_method_name(user_id) is None

    @pytest.mark.asyncio
    async def test_process_followup_no_sends_declined_message(self, bot_handler, mock_update):
        """Test that _process_followup_no sends the declined message.

        Validates: Requirements 8.4
        """
        user_id = 12345

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        await bot_handler._process_followup_no(mock_update, user_id)

        # Verify message was sent
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        assert FOLLOWUP_DECLINED_MESSAGE in call_args[0][0]

    @pytest.mark.asyncio
    async def test_process_followup_no_preserves_optimization_result(
        self, bot_handler, mock_update
    ):
        """Test that _process_followup_no preserves optimization result for email.

        Validates: Requirements 8.4
        """
        user_id = 12345
        improved_prompt = "This is the improved prompt"
        method_name = "CRAFT"

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.state_manager.set_cached_method_name(user_id, method_name)
        bot_handler.conversation_manager.set_user_prompt(user_id, "Original prompt")

        await bot_handler._process_followup_no(mock_update, user_id)

        # Verify optimization result was preserved
        result = bot_handler.state_manager.get_post_optimization_result(user_id)
        assert result is not None
        assert result["type"] == "single_method"
        assert result["method_name"] == method_name
        assert result["content"] == improved_prompt


class TestDisableFollowupButtons:
    """Test cases for _disable_followup_buttons method.

    These tests verify that the button disabling logic correctly edits
    the inline keyboard to show disabled buttons after user selection.

    Requirements: 8.5
    """

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = create_mock_llm_client()
        return client

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query for inline button clicks."""
        query = MagicMock()
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.edit_message_reply_markup = AsyncMock()
        return query

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        """Create a BotHandler instance with mocked dependencies."""
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    @pytest.mark.asyncio
    async def test_disable_buttons_yes_selected(self, bot_handler, mock_callback_query):
        """Test that selecting YES shows checkmark on YES button.

        Validates: Requirements 8.5
        """
        await bot_handler._disable_followup_buttons(mock_callback_query, selected="yes")

        # Verify edit_message_reply_markup was called
        mock_callback_query.edit_message_reply_markup.assert_called_once()

        # Get the keyboard that was passed
        call_args = mock_callback_query.edit_message_reply_markup.call_args
        keyboard = call_args.kwargs["reply_markup"]

        # Verify keyboard structure
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2

        # Verify YES button has checkmark
        yes_button = keyboard.inline_keyboard[0][0]
        no_button = keyboard.inline_keyboard[0][1]

        assert yes_button.text.startswith("✓ ")
        assert not no_button.text.startswith("✓ ")

        # Verify both buttons have "disabled" callback data
        assert yes_button.callback_data == "disabled"
        assert no_button.callback_data == "disabled"

    @pytest.mark.asyncio
    async def test_disable_buttons_no_selected(self, bot_handler, mock_callback_query):
        """Test that selecting NO shows checkmark on NO button.

        Validates: Requirements 8.5
        """
        await bot_handler._disable_followup_buttons(mock_callback_query, selected="no")

        # Verify edit_message_reply_markup was called
        mock_callback_query.edit_message_reply_markup.assert_called_once()

        # Get the keyboard that was passed
        call_args = mock_callback_query.edit_message_reply_markup.call_args
        keyboard = call_args.kwargs["reply_markup"]

        # Verify keyboard structure
        assert len(keyboard.inline_keyboard) == 1
        assert len(keyboard.inline_keyboard[0]) == 2

        # Verify NO button has checkmark
        yes_button = keyboard.inline_keyboard[0][0]
        no_button = keyboard.inline_keyboard[0][1]

        assert not yes_button.text.startswith("✓ ")
        assert no_button.text.startswith("✓ ")

        # Verify both buttons have "disabled" callback data
        assert yes_button.callback_data == "disabled"
        assert no_button.callback_data == "disabled"

    @pytest.mark.asyncio
    async def test_disable_buttons_handles_edit_failure(self, bot_handler, mock_callback_query):
        """Test that button disabling handles edit failures gracefully.

        Validates: Requirements 8.5
        """
        # Make edit_message_reply_markup raise an exception
        mock_callback_query.edit_message_reply_markup = AsyncMock(
            side_effect=Exception("Message too old to edit")
        )

        # Should not raise an exception
        await bot_handler._disable_followup_buttons(mock_callback_query, selected="yes")

        # Verify edit was attempted
        mock_callback_query.edit_message_reply_markup.assert_called_once()


class TestCallbackHandlerWithButtonDisabling:
    """Test cases for handle_followup_callback with button disabling integration.

    These tests verify that the callback handler correctly disables buttons
    before processing the user's choice.

    Requirements: 8.4, 8.5
    """

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = create_mock_llm_client()
        client.send_prompt = AsyncMock(return_value="What is your main goal?")
        client.get_last_usage = MagicMock(
            return_value={"prompt_tokens": 100, "completion_tokens": 50}
        )
        return client

    @pytest.fixture
    def mock_callback_query(self):
        """Create a mock callback query for inline button clicks."""
        query = MagicMock()
        query.from_user = MagicMock()
        query.from_user.id = 12345
        query.data = CALLBACK_FOLLOWUP_YES
        query.answer = AsyncMock()
        query.message = MagicMock()
        query.message.reply_text = AsyncMock()
        query.edit_message_reply_markup = AsyncMock()
        return query

    @pytest.fixture
    def mock_update_with_callback(self, mock_callback_query):
        """Create a mock Telegram update with callback query."""
        update = MagicMock()
        update.callback_query = mock_callback_query
        update.effective_user = mock_callback_query.from_user
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context."""
        return MagicMock()

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        """Create a BotHandler instance with mocked dependencies."""
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    @pytest.mark.asyncio
    async def test_callback_yes_disables_buttons_before_processing(
        self, bot_handler, mock_update_with_callback, mock_context
    ):
        """Test that YES callback disables buttons before processing.

        Validates: Requirements 8.4, 8.5
        """
        user_id = mock_update_with_callback.callback_query.from_user.id
        mock_update_with_callback.callback_query.data = CALLBACK_FOLLOWUP_YES

        # Set up state for follow-up choice
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        with patch.object(bot_handler, "_process_followup_yes") as mock_process_yes:
            mock_process_yes.return_value = None

            await bot_handler.handle_followup_callback(mock_update_with_callback, mock_context)

            # Verify buttons were disabled
            mock_update_with_callback.callback_query.edit_message_reply_markup.assert_called_once()

            # Verify the keyboard shows YES as selected
            call_args = mock_update_with_callback.callback_query.edit_message_reply_markup.call_args
            keyboard = call_args.kwargs["reply_markup"]
            yes_button = keyboard.inline_keyboard[0][0]
            assert yes_button.text.startswith("✓ ")

    @pytest.mark.asyncio
    async def test_callback_no_disables_buttons_before_processing(
        self, bot_handler, mock_update_with_callback, mock_context
    ):
        """Test that NO callback disables buttons before processing.

        Validates: Requirements 8.4, 8.5
        """
        user_id = mock_update_with_callback.callback_query.from_user.id
        mock_update_with_callback.callback_query.data = CALLBACK_FOLLOWUP_NO

        # Set up state for follow-up choice
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        with patch.object(bot_handler, "_process_followup_no") as mock_process_no:
            mock_process_no.return_value = None

            await bot_handler.handle_followup_callback(mock_update_with_callback, mock_context)

            # Verify buttons were disabled
            mock_update_with_callback.callback_query.edit_message_reply_markup.assert_called_once()

            # Verify the keyboard shows NO as selected
            call_args = mock_update_with_callback.callback_query.edit_message_reply_markup.call_args
            keyboard = call_args.kwargs["reply_markup"]
            no_button = keyboard.inline_keyboard[0][1]
            assert no_button.text.startswith("✓ ")
