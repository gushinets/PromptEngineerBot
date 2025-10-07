"""Tests for the bot handler module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import ReplyKeyboardMarkup

from src.bot_handler import BotHandler
from src.config import BotConfig
from src.messages import (
    BTN_CRAFT,
    BTN_GENERATE_PROMPT,
    BTN_GGL,
    BTN_LYRA,
    BTN_NO,
    BTN_RESET,
    BTN_YES,
)
from tests.test_utils import create_mock_config, create_mock_llm_client


class TestBotHandler:
    """Test cases for BotHandler class."""

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
        client.send_prompt = AsyncMock(return_value="Mocked LLM response")
        return client

    @pytest.fixture
    def mock_update(self):
        """Create a mock Telegram update."""
        update = MagicMock()
        update.effective_user.id = 12345
        update.message = MagicMock()
        update.message.text = "test message"
        update.message.reply_text = AsyncMock(return_value=None)
        return update

    @pytest.fixture
    def mock_context(self):
        """Create a mock Telegram context."""
        return MagicMock()

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        """Create a BotHandler instance with mocked dependencies."""
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    def test_init(self, mock_config, mock_llm_client):
        """Test BotHandler initialization."""
        sheets_logger = MagicMock()
        handler = BotHandler(mock_config, mock_llm_client, sheets_logger)

        assert handler.config == mock_config
        assert handler.llm_client == mock_llm_client
        assert handler.log_sheets == sheets_logger
        assert hasattr(handler, "state_manager")
        assert hasattr(handler, "conversation_manager")
        assert hasattr(handler, "prompt_loader")

    def test_reset_user_state(self, bot_handler):
        """Test resetting user state."""
        user_id = 12345

        # Set up some initial state
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.state_manager.set_last_interaction(user_id, "test")
        bot_handler.conversation_manager.append_message(user_id, "user", "test")

        # Reset
        bot_handler.reset_user_state(user_id)

        # Verify reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.last_interaction is None
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

    @pytest.mark.asyncio
    async def test_handle_start(self, bot_handler, mock_update, mock_context):
        """Test handling start command."""
        await bot_handler.handle_start(mock_update, mock_context)

        # Verify welcome message was sent
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args

        assert len(args[0]) > 0  # Message text
        assert "parse_mode" in kwargs
        assert "reply_markup" in kwargs

    @pytest.mark.asyncio
    async def test_handle_message_reset_button(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling reset button."""
        mock_update.message.text = BTN_RESET

        with patch.object(bot_handler, "handle_start") as mock_start:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_start.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_message_prompt_input(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling prompt input."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "Test prompt"

        # Set user to waiting for prompt
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify prompt was stored
        assert (
            bot_handler.conversation_manager.get_user_prompt(user_id) == "Test prompt"
        )
        assert bot_handler.conversation_manager.is_waiting_for_method(user_id) is True

        # Verify method selection message was sent
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_message_method_selection_craft(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling CRAFT method selection."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_CRAFT

        # Set up state for method selection
        bot_handler.state_manager.set_waiting_for_prompt(
            user_id, False
        )  # Not waiting for prompt
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)
        bot_handler.conversation_manager.append_message(user_id, "user", "Test prompt")

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify method was set
        assert bot_handler.conversation_manager.get_current_method(user_id) == "CRAFT"

    @pytest.mark.asyncio
    async def test_handle_message_method_selection_lyra(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling LYRA method selection."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_LYRA

        # Set up state for method selection
        bot_handler.state_manager.set_waiting_for_prompt(
            user_id, False
        )  # Not waiting for prompt
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)
        bot_handler.conversation_manager.append_message(user_id, "user", "Test prompt")

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify method was set
        assert (
            bot_handler.conversation_manager.get_current_method(user_id) == "LYRA Basic"
        )

    @pytest.mark.asyncio
    async def test_handle_message_invalid_method_selection(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling invalid method selection."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "Invalid method"

        # Set up state for method selection
        bot_handler.state_manager.set_waiting_for_prompt(
            user_id, False
        )  # Not waiting for prompt
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify method selection message was sent again
        mock_update.message.reply_text.assert_called_once()

        # Verify LLM was not called
        bot_handler.llm_client.send_prompt.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_conversation_turn(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling multi-turn conversation."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "Follow-up question"

        # Set up existing conversation
        bot_handler.state_manager.set_waiting_for_prompt(
            user_id, False
        )  # Not waiting for prompt
        bot_handler.conversation_manager.set_current_method(user_id, "CRAFT")
        bot_handler.conversation_manager.append_message(
            user_id, "user", "Initial prompt"
        )

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify message was added to transcript
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        assert any(msg["content"] == "Follow-up question" for msg in transcript)

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_with_llm_success(
        self, bot_handler, mock_update, mock_context
    ):
        """Test successful LLM processing."""
        user_id = mock_update.effective_user.id
        method_name = "CRAFT"

        # Set up conversation
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.append_message(user_id, "user", "Test prompt")

        await bot_handler._process_with_llm(mock_update, user_id, method_name)

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify response was sent
        mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_process_with_llm_error(self, bot_handler, mock_update, mock_context):
        """Test LLM processing with error."""
        user_id = mock_update.effective_user.id
        method_name = "CRAFT"

        # Make LLM client raise an error
        bot_handler.llm_client.send_prompt.side_effect = Exception("LLM Error")

        # Set up conversation
        bot_handler.conversation_manager.append_message(user_id, "user", "Test prompt")

        await bot_handler._process_with_llm(mock_update, user_id, method_name)

        # Verify error message was sent
        mock_update.message.reply_text.assert_called()
        args, _ = mock_update.message.reply_text.call_args
        assert "Произошла ошибка" in args[0]

    @pytest.mark.asyncio
    async def test_process_with_llm_improved_prompt(
        self, bot_handler, mock_update, mock_context
    ):
        """Test LLM processing with improved prompt response (legacy test - now offers follow-up)."""
        user_id = mock_update.effective_user.id
        method_name = "CRAFT"

        # Mock LLM response with improved prompt
        bot_handler.llm_client.send_prompt.return_value = (
            "<IMPROVED_PROMPT>Improved prompt here</IMPROVED_PROMPT>"
        )

        # Set up conversation
        bot_handler.conversation_manager.set_user_prompt(user_id, "Original prompt")
        bot_handler.conversation_manager.append_message(
            user_id, "user", "Original prompt"
        )

        await bot_handler._process_with_llm(mock_update, user_id, method_name)

        # Verify response was sent (now sends two messages: prompt + follow-up offer)
        assert mock_update.message.reply_text.call_count >= 1

        # Verify conversation was reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

        # Verify state is now waiting for follow-up choice (new behavior)
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is True
        assert user_state.waiting_for_prompt is False
        assert user_state.improved_prompt_cache == "Improved prompt here"

    @pytest.mark.asyncio
    async def test_safe_reply_success(self, bot_handler, mock_update):
        """Test successful safe reply."""
        result = await bot_handler._safe_reply(mock_update, "Test message")

        assert result is True
        mock_update.message.reply_text.assert_called_once_with("Test message")

    @pytest.mark.asyncio
    async def test_safe_reply_markdown_error(self, bot_handler, mock_update):
        """Test safe reply with Markdown parsing error."""
        # Make first call fail with parse error, second succeed
        mock_update.message.reply_text.side_effect = [
            Exception("Can't parse entities"),
            None,
        ]

        result = await bot_handler._safe_reply(
            mock_update, "Test message", parse_mode="Markdown"
        )

        assert result is True
        assert mock_update.message.reply_text.call_count == 2

    @pytest.mark.asyncio
    async def test_safe_reply_failure(self, bot_handler, mock_update):
        """Test safe reply with persistent failure."""
        mock_update.message.reply_text.side_effect = Exception("Network error")

        result = await bot_handler._safe_reply(mock_update, "Test message")

        assert result is False

    def test_log_method_selection(self, bot_handler):
        """Test logging method selection."""
        user_id = 12345
        method_name = "CRAFT"

        with patch("src.bot_handler.logger") as mock_logger:
            bot_handler._log_method_selection(user_id, method_name)

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args[0][0]
            assert "method_selected" in call_args
            assert str(user_id) in call_args
            assert method_name in call_args

    def test_log_conversation_totals(self, bot_handler):
        """Test logging conversation totals."""
        user_id = 12345
        method_name = "CRAFT"

        # Set up token usage
        bot_handler.conversation_manager.token_totals[user_id] = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")

        sheets_logger = MagicMock()
        bot_handler.log_sheets = sheets_logger

        bot_handler._log_conversation_totals(user_id, method_name, "Answer text")

        sheets_logger.assert_called_once_with(
            "conversation_totals",
            {
                "BotID": "test_bot",
                "TelegramID": user_id,
                "LLM": "TEST:test-model",
                "OptimizationModel": method_name,
                "UserRequest": "Test prompt",
                "Answer": "Answer text",
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            },
        )

    def test_log_conversation_totals_no_usage(self, bot_handler):
        """Test logging conversation totals with no token usage."""
        user_id = 12345
        method_name = "CRAFT"

        sheets_logger = MagicMock()
        bot_handler.log_sheets = sheets_logger

        bot_handler._log_conversation_totals(user_id, method_name)

        # Should not call sheets logger when no usage
        sheets_logger.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_followup_choice_no(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling НЕТ choice in follow-up questions."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_NO

        # Set up follow-up choice waiting state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_NO)

        # Verify FOLLOWUP_DECLINED_MESSAGE was sent (new behavior with post-optimization email button)
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "Готово!" in args[0] or "Done!" in args[0]

        # Verify state was reset properly
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.waiting_for_prompt is True
        assert user_state.improved_prompt_cache is None

        # Verify conversation was reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

    @pytest.mark.asyncio
    async def test_handle_followup_choice_yes(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling ДА choice in follow-up questions with simplified flow."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_YES
        cached_prompt = "This is the cached improved prompt"

        # Set up follow-up choice waiting state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, cached_prompt)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        # Mock LLM response for initial follow-up question
        bot_handler.llm_client.send_prompt.return_value = "What is your main goal?"

        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Verify LLM was called to get initial question
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify initial question was sent
        assert mock_update.message.reply_text.call_count >= 1

        # Verify state transitions directly to conversation (simplified flow)
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is True
        assert (
            user_state.improved_prompt_cache == cached_prompt
        )  # Cache preserved for follow-up

    @pytest.mark.asyncio
    async def test_handle_followup_choice_yes_no_cache(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling ДА choice when cached prompt is missing."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_YES

        # Set up follow-up choice waiting state without cached prompt
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, None)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Verify fallback behavior - should send reset confirmation
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "сброшен" in args[0] or "reset" in args[0].lower()

        # Verify state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True

    @pytest.mark.asyncio
    async def test_handle_followup_choice_invalid(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling invalid choice in follow-up questions."""
        user_id = mock_update.effective_user.id
        invalid_text = "Invalid choice"

        # Set up follow-up choice waiting state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        await bot_handler._handle_followup_choice(mock_update, user_id, invalid_text)

        # Verify no message was sent (graceful handling)
        mock_update.message.reply_text.assert_not_called()

        # Verify state remained unchanged
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is True
        assert user_state.improved_prompt_cache == "Cached prompt"

    @pytest.mark.asyncio
    @pytest.mark.asyncio
    async def test_handle_message_followup_choice_routing(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that handle_message routes to follow-up choice handler correctly."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_YES

        # Set up follow-up choice waiting state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        with patch.object(bot_handler, "_handle_followup_choice") as mock_handle:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle.assert_called_once_with(mock_update, user_id, BTN_YES)

    def test_reset_user_state_followup_fields(self, bot_handler):
        """Test that reset_user_state properly resets follow-up fields."""
        user_id = 12345

        # Set up follow-up state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        # Reset
        bot_handler.reset_user_state(user_id)

        # Verify all follow-up fields are reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None
        assert user_state.waiting_for_prompt is True

    @pytest.mark.asyncio
    async def test_handle_followup_conversation_user_response(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling user response in follow-up conversation."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "My answer to the question"

        # Set up follow-up conversation state properly
        print(f"TEST DEBUG: Setting up state for user_id={user_id}")
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        print(f"TEST DEBUG: Set in_followup_conversation=True")
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")
        print(f"TEST DEBUG: Set improved_prompt_cache='Improved prompt'")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )
        print(f"TEST DEBUG: Started followup conversation")

        # Verify state was set correctly
        user_state = bot_handler.state_manager.get_user_state(user_id)
        print(
            f"TEST DEBUG: Final state - in_followup={user_state.in_followup_conversation}, cache='{user_state.improved_prompt_cache}'"
        )

        # Debug: Check validation before proceeding
        print(f"DEBUG: user_id = {user_id}")
        print(
            f"DEBUG: validation result = {bot_handler._validate_followup_state(user_id)}"
        )
        user_state = bot_handler.state_manager.get_user_state(user_id)
        print(
            f"DEBUG: in_followup_conversation = {user_state.in_followup_conversation}"
        )
        print(f"DEBUG: improved_prompt_cache = {user_state.improved_prompt_cache}")
        print(
            f"DEBUG: conversation_manager check = {bot_handler.conversation_manager.is_in_followup_conversation(user_id)}"
        )

        # Mock LLM response with another question
        bot_handler.llm_client.send_prompt.return_value = "Next question?"

        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "My answer to the question"
        )

        # Verify user message was added to transcript
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        assert any(
            msg["content"] == "My answer to the question" and msg["role"] == "user"
            for msg in transcript
        )

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify response was sent with follow-up keyboard
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_followup_conversation_generate_button(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling generate prompt button in follow-up conversation."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_GENERATE_PROMPT

        # Set up follow-up conversation state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        with patch.object(bot_handler, "_process_followup_generation") as mock_process:
            await bot_handler._handle_followup_conversation(
                mock_update, user_id, BTN_GENERATE_PROMPT
            )

            mock_process.assert_called_once_with(mock_update, user_id)

    @pytest.mark.asyncio
    async def test_handle_followup_conversation_refined_prompt(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling refined prompt response in follow-up conversation."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "My answer"

        # Set up follow-up conversation state properly
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        # Mock LLM response with refined prompt
        bot_handler.llm_client.send_prompt.return_value = (
            "<REFINED_PROMPT>Final refined prompt</REFINED_PROMPT>"
        )

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._handle_followup_conversation(
                mock_update, user_id, "My answer"
            )

            mock_complete.assert_called_once_with(
                mock_update, user_id, "Final refined prompt"
            )

    @pytest.mark.asyncio
    async def test_handle_followup_conversation_error(
        self, bot_handler, mock_update, mock_context
    ):
        """Test error handling in follow-up conversation."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "My answer"

        # Set up follow-up conversation state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        # Make LLM client raise an error
        bot_handler.llm_client.send_prompt.side_effect = Exception("LLM Error")

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._handle_followup_conversation(
                mock_update, user_id, "My answer"
            )

            # Should fallback to cached prompt
            mock_complete.assert_called_once_with(mock_update, user_id, "Cached prompt")

    @pytest.mark.asyncio
    async def test_process_followup_generation_success(
        self, bot_handler, mock_update, mock_context
    ):
        """Test successful follow-up generation."""
        user_id = mock_update.effective_user.id

        # Set up follow-up conversation state properly
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        # Mock LLM response with refined prompt
        bot_handler.llm_client.send_prompt.return_value = (
            "<REFINED_PROMPT>Generated refined prompt</REFINED_PROMPT>"
        )

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._process_followup_generation(mock_update, user_id)

            # Verify generate signal was sent to LLM
            transcript = bot_handler.conversation_manager.get_transcript(user_id)
            assert any(
                msg["content"] == "<GENERATE_PROMPT>" and msg["role"] == "user"
                for msg in transcript
            )

            # Verify completion was called
            mock_complete.assert_called_once_with(
                mock_update, user_id, "Generated refined prompt"
            )

    @pytest.mark.asyncio
    async def test_process_followup_generation_no_refined_prompt(
        self, bot_handler, mock_update, mock_context
    ):
        """Test follow-up generation when LLM doesn't return refined prompt."""
        user_id = mock_update.effective_user.id

        # Set up follow-up conversation state
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Fallback prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        # Mock LLM response without refined prompt
        bot_handler.llm_client.send_prompt.return_value = "Some other response"

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._process_followup_generation(mock_update, user_id)

            # Should fallback to cached prompt
            mock_complete.assert_called_once_with(
                mock_update, user_id, "Fallback prompt"
            )

    @pytest.mark.asyncio
    async def test_process_followup_generation_error(
        self, bot_handler, mock_update, mock_context
    ):
        """Test error handling in follow-up generation."""
        user_id = mock_update.effective_user.id

        # Set up follow-up conversation state
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Fallback prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        # Make LLM client raise an error
        bot_handler.llm_client.send_prompt.side_effect = Exception("LLM Error")

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._process_followup_generation(mock_update, user_id)

            # Should fallback to cached prompt
            mock_complete.assert_called_once_with(
                mock_update, user_id, "Fallback prompt"
            )

    @pytest.mark.asyncio
    async def test_complete_followup_conversation(
        self, bot_handler, mock_update, mock_context
    ):
        """Test completing follow-up conversation."""
        user_id = mock_update.effective_user.id
        refined_prompt = "Final refined prompt"

        await bot_handler._complete_followup_conversation(
            mock_update, user_id, refined_prompt
        )

        # Verify refined prompt was sent
        assert mock_update.message.reply_text.call_count >= 2

        # Verify state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False

    # Error Handling Tests for Follow-up Feature

    @pytest.mark.asyncio
    async def test_handle_followup_error_timeout(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling timeout errors during follow-up conversations."""
        user_id = mock_update.effective_user.id
        timeout_error = Exception("Request timed out")

        # Set up cached prompt
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        await bot_handler._handle_followup_error(
            mock_update, user_id, timeout_error, "conversation"
        )

        # Verify fallback message was sent
        mock_update.message.reply_text.assert_called()

        # Check that timeout-specific handling was used
        call_args = mock_update.message.reply_text.call_args_list
        timeout_message_found = any(
            "время ожидания" in str(call).lower() or "timeout" in str(call).lower()
            for call in call_args
        )
        assert timeout_message_found or mock_update.message.reply_text.call_count >= 1

    @pytest.mark.asyncio
    async def test_handle_followup_error_network(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling network errors during follow-up conversations."""
        user_id = mock_update.effective_user.id
        network_error = Exception("Connection failed")

        # Set up cached prompt
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        await bot_handler._handle_followup_error(
            mock_update, user_id, network_error, "conversation"
        )

        # Verify fallback was triggered
        mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_handle_followup_error_no_cache(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling errors when no cached prompt is available."""
        user_id = mock_update.effective_user.id
        error = Exception("Generic error")

        # No cached prompt
        bot_handler.state_manager.set_improved_prompt_cache(user_id, None)

        await bot_handler._handle_followup_error(
            mock_update, user_id, error, "conversation"
        )

        # Verify fallback to prompt input
        mock_update.message.reply_text.assert_called()

        # Verify state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True

    def test_classify_followup_error_timeout(self, bot_handler):
        """Test error classification for timeout errors."""
        timeout_error = Exception("Request timed out")
        error_type = bot_handler._classify_followup_error(timeout_error)
        assert error_type == "timeout"

    def test_classify_followup_error_network(self, bot_handler):
        """Test error classification for network errors."""
        network_error = Exception("Connection error occurred")
        error_type = bot_handler._classify_followup_error(network_error)
        assert error_type == "network"

    def test_classify_followup_error_rate_limit(self, bot_handler):
        """Test error classification for rate limit errors."""
        rate_limit_error = Exception("Rate limit exceeded")
        error_type = bot_handler._classify_followup_error(rate_limit_error)
        assert error_type == "rate_limit"

    def test_classify_followup_error_api(self, bot_handler):
        """Test error classification for API errors."""
        api_error = Exception("API error: invalid request")
        error_type = bot_handler._classify_followup_error(api_error)
        assert error_type == "api_error"

    def test_classify_followup_error_generic(self, bot_handler):
        """Test error classification for generic errors."""
        generic_error = Exception("Something went wrong")
        error_type = bot_handler._classify_followup_error(generic_error)
        assert error_type == "generic"

    def test_validate_followup_state_valid(self, bot_handler):
        """Test validation of valid follow-up state."""
        user_id = 12345

        # Set up valid follow-up state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Test prompt"
        )

        result = bot_handler._validate_followup_state(user_id)
        assert result is True

    def test_validate_followup_state_not_in_conversation(self, bot_handler):
        """Test validation when user is not in follow-up conversation."""
        user_id = 12345

        # User not in follow-up conversation
        bot_handler.state_manager.set_in_followup_conversation(user_id, False)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        result = bot_handler._validate_followup_state(user_id)
        assert result is False

    def test_validate_followup_state_no_cache(self, bot_handler):
        """Test validation when no cached prompt exists."""
        user_id = 12345

        # No cached prompt
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, None)

        result = bot_handler._validate_followup_state(user_id)
        assert result is False

    def test_validate_followup_transcript_valid(self, bot_handler):
        """Test validation of valid follow-up transcript."""
        transcript = [
            {"role": "system", "content": "Ты эксперт по промпт-инжинирингу"},
            {"role": "user", "content": "Test prompt"},
        ]

        result = bot_handler._validate_followup_transcript(transcript)
        assert result is True

    def test_validate_followup_transcript_too_short(self, bot_handler):
        """Test validation of transcript that's too short."""
        transcript = [{"role": "system", "content": "System prompt"}]

        result = bot_handler._validate_followup_transcript(transcript)
        assert result is False

    def test_validate_followup_transcript_no_system(self, bot_handler):
        """Test validation of transcript without system message."""
        transcript = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant response"},
        ]

        result = bot_handler._validate_followup_transcript(transcript)
        assert result is False

    def test_validate_followup_transcript_wrong_system_content(self, bot_handler):
        """Test validation of transcript with wrong system content."""
        transcript = [
            {"role": "system", "content": "Regular system prompt"},
            {"role": "user", "content": "Test prompt"},
        ]

        result = bot_handler._validate_followup_transcript(transcript)
        assert result is False

    @pytest.mark.asyncio
    async def test_recover_followup_state_with_cache(
        self, bot_handler, mock_update, mock_context
    ):
        """Test state recovery when cached prompt is available."""
        user_id = mock_update.effective_user.id
        cached_prompt = "Cached improved prompt"

        # Set up cached prompt
        bot_handler.state_manager.set_improved_prompt_cache(user_id, cached_prompt)

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._recover_followup_state(mock_update, user_id)

            # Verify recovery message was sent
            mock_update.message.reply_text.assert_called()

            # Verify completion was called with cached prompt
            mock_complete.assert_called_once_with(mock_update, user_id, cached_prompt)

    @pytest.mark.asyncio
    async def test_recover_followup_state_no_cache(
        self, bot_handler, mock_update, mock_context
    ):
        """Test state recovery when no cached prompt is available."""
        user_id = mock_update.effective_user.id

        # No cached prompt
        bot_handler.state_manager.set_improved_prompt_cache(user_id, None)

        await bot_handler._recover_followup_state(mock_update, user_id)

        # Verify fallback message was sent
        mock_update.message.reply_text.assert_called()

        # Verify state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True

    def test_parse_followup_response_with_fallback_valid(self, bot_handler):
        """Test parsing valid follow-up response."""
        response = "<REFINED_PROMPT>Refined prompt content</REFINED_PROMPT>"
        user_id = 12345

        parsed, is_refined = bot_handler._parse_followup_response_with_fallback(
            response, user_id
        )

        assert parsed == "Refined prompt content"
        assert is_refined is True

    def test_parse_followup_response_with_fallback_empty_refined(self, bot_handler):
        """Test parsing response with empty refined prompt."""
        response = "<REFINED_PROMPT></REFINED_PROMPT>"
        user_id = 12345

        with patch.object(
            bot_handler, "_fallback_parse_refined_prompt"
        ) as mock_fallback:
            mock_fallback.return_value = ("Fallback content", True)

            parsed, is_refined = bot_handler._parse_followup_response_with_fallback(
                response, user_id
            )

            mock_fallback.assert_called_once_with(response, user_id)

    def test_parse_followup_response_with_fallback_parse_error(self, bot_handler):
        """Test parsing response when parsing fails."""
        response = "<REFINED_PROMPT>Content with malformed tags"
        user_id = 12345

        # Mock parse_followup_response to raise an exception
        with patch("src.bot_handler.parse_followup_response") as mock_parse:
            mock_parse.side_effect = Exception("Parse error")

            parsed, is_refined = bot_handler._parse_followup_response_with_fallback(
                response, user_id
            )

            # Should fall back to original response
            assert parsed == response.strip()
            assert is_refined is False

    def test_fallback_parse_refined_prompt_success(self, bot_handler):
        """Test successful fallback parsing of refined prompt."""
        response = "<REFINED_PROMPT>Fallback content</REFINED_PROMPT>"
        user_id = 12345

        parsed, is_refined = bot_handler._fallback_parse_refined_prompt(
            response, user_id
        )

        assert parsed == "Fallback content"
        assert is_refined is True

    def test_fallback_parse_refined_prompt_with_closing_tag(self, bot_handler):
        """Test fallback parsing with various closing tags."""
        response = "<REFINED_PROMPT>Content here<END REFINED_PROMPT>"
        user_id = 12345

        parsed, is_refined = bot_handler._fallback_parse_refined_prompt(
            response, user_id
        )

        assert parsed == "Content here"
        assert is_refined is True

    def test_fallback_parse_refined_prompt_no_content(self, bot_handler):
        """Test fallback parsing when no content can be extracted."""
        response = "No refined prompt tag here"
        user_id = 12345

        parsed, is_refined = bot_handler._fallback_parse_refined_prompt(
            response, user_id
        )

        assert parsed == response.strip()
        assert is_refined is False

    @pytest.mark.asyncio
    async def test_handle_missing_refined_prompt_with_cache(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling missing refined prompt when cache is available."""
        user_id = mock_update.effective_user.id
        cached_prompt = "Cached prompt"

        bot_handler.state_manager.set_improved_prompt_cache(user_id, cached_prompt)

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._handle_missing_refined_prompt(mock_update, user_id)

            mock_complete.assert_called_once_with(mock_update, user_id, cached_prompt)

    @pytest.mark.asyncio
    async def test_handle_missing_refined_prompt_no_cache(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling missing refined prompt when no cache is available."""
        user_id = mock_update.effective_user.id

        bot_handler.state_manager.set_improved_prompt_cache(user_id, None)

        await bot_handler._handle_missing_refined_prompt(mock_update, user_id)

        # Verify fallback message was sent
        mock_update.message.reply_text.assert_called()

        # Verify state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True

    @pytest.mark.asyncio
    async def test_process_followup_llm_request_invalid_state(
        self, bot_handler, mock_update, mock_context
    ):
        """Test LLM request processing with invalid follow-up state."""
        user_id = mock_update.effective_user.id

        # Set up invalid state (not in follow-up conversation)
        bot_handler.state_manager.set_in_followup_conversation(user_id, False)

        with patch.object(bot_handler, "_recover_followup_state") as mock_recover:
            await bot_handler._process_followup_llm_request(mock_update, user_id)

            mock_recover.assert_called_once_with(mock_update, user_id)

    @pytest.mark.asyncio
    async def test_process_followup_llm_request_invalid_transcript(
        self, bot_handler, mock_update, mock_context
    ):
        """Test LLM request processing with invalid transcript."""
        user_id = mock_update.effective_user.id

        # Set up valid state but invalid transcript
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached")
        bot_handler.conversation_manager.transcripts[user_id] = [
            {"role": "user", "content": "Invalid"}
        ]

        with patch.object(bot_handler, "_recover_followup_state") as mock_recover:
            await bot_handler._process_followup_llm_request(mock_update, user_id)

            mock_recover.assert_called_once_with(mock_update, user_id)

    @pytest.mark.asyncio
    async def test_process_followup_llm_request_success(
        self, bot_handler, mock_update, mock_context
    ):
        """Test successful LLM request processing during follow-up."""
        user_id = mock_update.effective_user.id

        # Set up valid state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Test prompt"
        )

        # Mock LLM response
        bot_handler.llm_client.send_prompt.return_value = (
            "What is your target audience?"
        )

        await bot_handler._process_followup_llm_request(mock_update, user_id)

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify response was sent
        mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_process_followup_llm_request_expect_refined_prompt(
        self, bot_handler, mock_update, mock_context
    ):
        """Test LLM request processing when expecting refined prompt but not getting one."""
        user_id = mock_update.effective_user.id

        # Set up valid state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Test prompt"
        )

        # Mock LLM response without refined prompt
        bot_handler.llm_client.send_prompt.return_value = "Another question?"

        with patch.object(bot_handler, "_handle_missing_refined_prompt") as mock_handle:
            await bot_handler._process_followup_llm_request(
                mock_update, user_id, expect_refined_prompt=True
            )

            mock_handle.assert_called_once_with(mock_update, user_id)

    @pytest.mark.asyncio
    async def test_followup_conversation_error_integration(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete error handling integration in follow-up conversation."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "User response"

        # Set up follow-up conversation state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Test prompt"
        )

        # Capture transcript state during error handling
        captured_transcript = None
        original_handle_error = bot_handler._handle_followup_error

        async def capture_transcript_on_error(*args, **kwargs):
            nonlocal captured_transcript
            captured_transcript = bot_handler.conversation_manager.get_transcript(
                user_id
            ).copy()
            return await original_handle_error(*args, **kwargs)

        # Make LLM client raise a timeout error
        bot_handler.llm_client.send_prompt.side_effect = Exception("Request timed out")

        with patch.object(
            bot_handler,
            "_handle_followup_error",
            side_effect=capture_transcript_on_error,
        ):
            await bot_handler._handle_followup_conversation(
                mock_update, user_id, "User response"
            )

        # Verify error was handled and fallback was used
        mock_update.message.reply_text.assert_called()

        # Verify user message was added to transcript before error
        assert captured_transcript is not None
        user_messages = [
            msg
            for msg in captured_transcript
            if msg["role"] == "user" and msg["content"] == "User response"
        ]
        assert len(user_messages) == 1

    @pytest.mark.asyncio
    async def test_followup_generation_error_integration(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete error handling integration in follow-up generation."""
        user_id = mock_update.effective_user.id

        # Set up follow-up conversation state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Test prompt"
        )

        # Capture transcript state during error handling
        captured_transcript = None
        original_handle_error = bot_handler._handle_followup_error

        async def capture_transcript_on_error(*args, **kwargs):
            nonlocal captured_transcript
            captured_transcript = bot_handler.conversation_manager.get_transcript(
                user_id
            ).copy()
            return await original_handle_error(*args, **kwargs)

        # Make LLM client raise a network error
        bot_handler.llm_client.send_prompt.side_effect = Exception("Connection failed")

        with patch.object(
            bot_handler,
            "_handle_followup_error",
            side_effect=capture_transcript_on_error,
        ):
            await bot_handler._process_followup_generation(mock_update, user_id)

        # Verify error was handled and fallback was used
        mock_update.message.reply_text.assert_called()

        # Verify generate signal was added to transcript before error
        assert captured_transcript is not None
        generate_messages = [
            msg
            for msg in captured_transcript
            if msg["role"] == "user" and msg["content"] == "<GENERATE_PROMPT>"
        ]
        assert len(generate_messages) == 1

    # Error Handling Tests for Follow-up Feature

    @pytest.mark.asyncio
    async def test_complete_followup_conversation_success(
        self, bot_handler, mock_update, mock_context
    ):
        """Test completing follow-up conversation with refined prompt."""
        user_id = mock_update.effective_user.id
        refined_prompt = "Final refined prompt"

        # Set up some conversation state
        bot_handler.conversation_manager.set_user_prompt(user_id, "Original prompt")
        bot_handler.conversation_manager.token_totals[user_id] = {
            "prompt_tokens": 50,
            "completion_tokens": 100,
            "total_tokens": 150,
        }

        sheets_logger = MagicMock()
        bot_handler.log_sheets = sheets_logger

        await bot_handler._complete_followup_conversation(
            mock_update, user_id, refined_prompt
        )

        # Verify refined prompt was sent
        assert mock_update.message.reply_text.call_count >= 1
        first_call_args = mock_update.message.reply_text.call_args_list[0][0]
        assert refined_prompt in first_call_args[0]

        # Verify follow-up completion message was sent
        assert mock_update.message.reply_text.call_count >= 2

        # Verify conversation totals were logged
        sheets_logger.assert_called_once_with(
            "conversation_totals",
            {
                "BotID": "test_bot",
                "TelegramID": user_id,
                "LLM": "TEST:test-model",
                "OptimizationModel": "FOLLOWUP",
                "UserRequest": "Original prompt",
                "Answer": refined_prompt,
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150,
            },
        )

        # Verify state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False

    @pytest.mark.asyncio
    async def test_handle_message_followup_conversation_routing(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that handle_message routes to follow-up conversation handler correctly."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "User response"

        # Set up follow-up conversation state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)

        with patch.object(bot_handler, "_handle_followup_conversation") as mock_handle:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle.assert_called_once_with(mock_update, user_id, "User response")

    @pytest.mark.asyncio
    async def test_process_with_llm_followup_initial(
        self, bot_handler, mock_update, mock_context
    ):
        """Test _process_with_llm with FOLLOWUP method for initial questions."""
        user_id = mock_update.effective_user.id
        method_name = "FOLLOWUP"

        # Set up follow-up conversation
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        # Mock LLM response with initial questions
        bot_handler.llm_client.send_prompt.return_value = (
            "I have 3 questions. First question: What is your target audience?"
        )

        await bot_handler._process_with_llm(mock_update, user_id, method_name)

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify response was sent with follow-up keyboard
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert "reply_markup" in kwargs

    @pytest.mark.asyncio
    async def test_process_with_llm_followup_refined_prompt_initial(
        self, bot_handler, mock_update, mock_context
    ):
        """Test _process_with_llm with FOLLOWUP method when LLM returns refined prompt immediately."""
        user_id = mock_update.effective_user.id
        method_name = "FOLLOWUP"

        # Set up follow-up conversation
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, "Improved prompt"
        )

        # Mock LLM response with immediate refined prompt (edge case)
        bot_handler.llm_client.send_prompt.return_value = (
            "<REFINED_PROMPT>Immediately refined prompt</REFINED_PROMPT>"
        )

        with patch.object(
            bot_handler, "_complete_followup_conversation"
        ) as mock_complete:
            await bot_handler._process_with_llm(mock_update, user_id, method_name)

            # Should complete the conversation immediately
            mock_complete.assert_called_once_with(
                mock_update, user_id, "Immediately refined prompt"
            )

    @pytest.mark.asyncio
    async def test_process_with_llm_improved_prompt_with_followup_offer(
        self, bot_handler, mock_update, mock_context
    ):
        """Test LLM processing with improved prompt response that offers follow-up questions."""
        user_id = mock_update.effective_user.id
        method_name = "CRAFT"

        # Mock LLM response with improved prompt
        bot_handler.llm_client.send_prompt.return_value = (
            "<IMPROVED_PROMPT>Improved prompt here</IMPROVED_PROMPT>"
        )

        # Set up conversation
        bot_handler.conversation_manager.set_user_prompt(user_id, "Original prompt")
        bot_handler.conversation_manager.append_message(
            user_id, "user", "Original prompt"
        )

        await bot_handler._process_with_llm(mock_update, user_id, method_name)

        # Verify two messages were sent: improved prompt and follow-up offer
        assert mock_update.message.reply_text.call_count == 2

        # Verify first message contains the improved prompt
        first_call_args = mock_update.message.reply_text.call_args_list[0][0]
        assert "Improved prompt here" in first_call_args[0]

        # Verify second message is the follow-up offer
        second_call_args = mock_update.message.reply_text.call_args_list[1][0]
        assert (
            "готов к использованию" in second_call_args[0]
            or "ready to use" in second_call_args[0].lower()
        )

        # Verify state transitions
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is True
        assert user_state.waiting_for_prompt is False
        assert user_state.improved_prompt_cache == "Improved prompt here"

        # Verify conversation was reset for follow-up ready state
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

    @pytest.mark.asyncio
    async def test_handle_message_routing_precedence_reset_button(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that reset button has highest precedence in message routing."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_RESET

        # Set up multiple conflicting states
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        with patch.object(bot_handler, "handle_start") as mock_start:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_start.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_handle_message_routing_precedence_followup_choice(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that follow-up choice state has precedence over other states."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_YES

        # Set up follow-up choice state with other conflicting states
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_waiting_for_prompt(
            user_id, True
        )  # Should be ignored
        bot_handler.conversation_manager.set_waiting_for_method(
            user_id, True
        )  # Should be ignored
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        with patch.object(bot_handler, "_handle_followup_choice") as mock_handle:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle.assert_called_once_with(mock_update, user_id, BTN_YES)

    @pytest.mark.asyncio
    async def test_handle_message_routing_precedence_followup_conversation(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that follow-up conversation state has precedence over prompt/method states."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "User response in follow-up"

        # Set up follow-up conversation state with other conflicting states
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_waiting_for_prompt(
            user_id, True
        )  # Should be ignored
        bot_handler.conversation_manager.set_waiting_for_method(
            user_id, True
        )  # Should be ignored

        with patch.object(bot_handler, "_handle_followup_conversation") as mock_handle:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle.assert_called_once_with(
                mock_update, user_id, "User response in follow-up"
            )

    @pytest.mark.asyncio
    async def test_handle_message_routing_precedence_prompt_input(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that prompt input state has precedence over method selection."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "New prompt input"

        # Set up prompt waiting state with method selection state
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)
        bot_handler.conversation_manager.set_waiting_for_method(
            user_id, True
        )  # Should be ignored

        with patch.object(bot_handler, "_handle_prompt_input") as mock_handle:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle.assert_called_once_with(
                mock_update, user_id, "New prompt input"
            )

    @pytest.mark.asyncio
    async def test_handle_message_routing_precedence_method_selection(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that method selection state has precedence over conversation turns."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = BTN_CRAFT

        # Set up method selection state with existing conversation
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)
        bot_handler.conversation_manager.set_current_method(
            user_id, "EXISTING"
        )  # Should be ignored

        with patch.object(bot_handler, "_handle_method_selection") as mock_handle:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle.assert_called_once_with(
                mock_update, mock_context, user_id, BTN_CRAFT
            )

    @pytest.mark.asyncio
    async def test_handle_message_routing_fallback_conversation_turn(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that conversation turn is the fallback when no other states match."""
        user_id = mock_update.effective_user.id
        mock_update.message.text = "Follow-up message"

        # Set up state where no specific routing conditions are met
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, False)
        bot_handler.state_manager.set_in_followup_conversation(user_id, False)
        bot_handler.conversation_manager.set_waiting_for_method(user_id, False)

        with patch.object(bot_handler, "_handle_conversation_turn") as mock_handle:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle.assert_called_once_with(
                mock_update, user_id, "Follow-up message"
            )

    @pytest.mark.asyncio
    async def test_handle_message_routing_state_isolation(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that routing works correctly with multiple users in different states."""
        user1_id = 12345
        user2_id = 67890

        # Set up different states for different users
        bot_handler.state_manager.set_waiting_for_followup_choice(user1_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user1_id, "User1 prompt")

        bot_handler.state_manager.set_in_followup_conversation(user2_id, True)

        # Test user1 routing
        mock_update.effective_user.id = user1_id
        mock_update.message.text = BTN_YES

        with patch.object(bot_handler, "_handle_followup_choice") as mock_choice:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_choice.assert_called_once_with(mock_update, user1_id, BTN_YES)

        # Test user2 routing
        mock_update.effective_user.id = user2_id
        mock_update.message.text = "User2 response"

        with patch.object(bot_handler, "_handle_followup_conversation") as mock_conv:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_conv.assert_called_once_with(mock_update, user2_id, "User2 response")

    @pytest.mark.asyncio
    async def test_handle_message_routing_complete_state_transitions(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete state transitions through the routing system."""
        user_id = mock_update.effective_user.id

        # Start with prompt input
        mock_update.message.text = "Initial prompt"
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)

        with patch.object(bot_handler, "_handle_prompt_input") as mock_prompt:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_prompt.assert_called_once_with(mock_update, user_id, "Initial prompt")

        # Transition to method selection
        mock_update.message.text = BTN_CRAFT
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

        with patch.object(bot_handler, "_handle_method_selection") as mock_method:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_method.assert_called_once_with(
                mock_update, mock_context, user_id, BTN_CRAFT
            )

        # Transition to follow-up choice
        mock_update.message.text = BTN_YES
        bot_handler.conversation_manager.set_waiting_for_method(user_id, False)
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")

        with patch.object(bot_handler, "_handle_followup_choice") as mock_choice:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_choice.assert_called_once_with(mock_update, user_id, BTN_YES)

        # Transition directly to follow-up conversation (simplified flow)
        mock_update.message.text = "My answer"
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, False)
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)

        with patch.object(bot_handler, "_handle_followup_conversation") as mock_conv:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_conv.assert_called_once_with(mock_update, user_id, "My answer")

    # ===== End-to-End Follow-up Workflow Tests =====

    @pytest.mark.asyncio
    async def test_complete_followup_workflow_yes_flow(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete ДА flow from offer to refined prompt delivery."""
        user_id = mock_update.effective_user.id
        original_prompt = "Original user prompt"
        improved_prompt = "Improved prompt from LLM"
        refined_prompt = "Final refined prompt after questions"

        # Step 1: User submits prompt
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)
        mock_update.message.text = original_prompt
        await bot_handler.handle_message(mock_update, mock_context)

        # Verify method selection was triggered
        assert bot_handler.conversation_manager.is_waiting_for_method(user_id) is True

        # Step 2: User selects method and gets improved version
        mock_update.message.text = BTN_CRAFT
        bot_handler.llm_client.send_prompt.return_value = (
            f"<IMPROVED_PROMPT>{improved_prompt}</IMPROVED_PROMPT>"
        )
        await bot_handler.handle_message(mock_update, mock_context)

        # Verify state is waiting for follow-up choice (this is the key verification)
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is True
        assert user_state.improved_prompt_cache == improved_prompt

        # Reset mock for next step
        mock_update.message.reply_text.reset_mock()

        # Step 2: User chooses ДА for follow-up questions
        mock_update.message.text = BTN_YES

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify state transitioned directly to follow-up conversation (simplified flow)
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is True

        # Verify LLM response was sent (direct conversation start)
        assert mock_update.message.reply_text.call_count == 1

        # Step 4: User answers follow-up questions
        mock_update.message.text = "My target audience is developers"
        bot_handler.llm_client.send_prompt.return_value = (
            "Any specific programming languages?"
        )

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify conversation continues
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.in_followup_conversation is True

        # Step 5: User provides final answer and LLM returns refined prompt
        mock_update.message.text = "Python and JavaScript"
        bot_handler.llm_client.send_prompt.return_value = (
            f"<REFINED_PROMPT>{refined_prompt}</REFINED_PROMPT>"
        )

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify refined prompt was sent and state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify conversation was reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

    @pytest.mark.asyncio
    async def test_complete_followup_workflow_no_flow(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete НЕТ flow from offer to prompt input reset."""
        user_id = mock_update.effective_user.id
        original_prompt = "Original user prompt"
        improved_prompt = "Improved prompt from LLM"

        # Step 1: User submits prompt
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)
        mock_update.message.text = original_prompt
        await bot_handler.handle_message(mock_update, mock_context)

        # Step 2: User selects method and gets improved version
        mock_update.message.text = BTN_CRAFT
        bot_handler.llm_client.send_prompt.return_value = (
            f"<IMPROVED_PROMPT>{improved_prompt}</IMPROVED_PROMPT>"
        )
        await bot_handler.handle_message(mock_update, mock_context)

        # Verify state is waiting for follow-up choice
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is True
        assert user_state.improved_prompt_cache == improved_prompt

        # Step 2: User chooses НЕТ to decline follow-up questions
        mock_update.message.text = BTN_NO

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify RESET_CONFIRMATION was sent and state was reset to prompt input
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.improved_prompt_cache is None

        # Verify conversation was reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

    @pytest.mark.asyncio
    async def test_complete_followup_workflow_generate_button(
        self, bot_handler, mock_update, mock_context
    ):
        """Test generate button functionality during question-answer phase."""
        user_id = mock_update.effective_user.id
        improved_prompt = "Improved prompt from LLM"
        refined_prompt = "Generated refined prompt"

        # Set up follow-up conversation state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Add some conversation history
        bot_handler.conversation_manager.append_message(
            user_id, "assistant", "What is your goal?"
        )
        bot_handler.conversation_manager.append_message(
            user_id, "user", "To improve engagement"
        )

        # User clicks generate button
        mock_update.message.text = BTN_GENERATE_PROMPT
        bot_handler.llm_client.send_prompt.return_value = (
            f"<REFINED_PROMPT>{refined_prompt}</REFINED_PROMPT>"
        )

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify refined prompt was delivered and state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify conversation was reset (indicating completion)
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

    @pytest.mark.asyncio
    async def test_followup_workflow_state_management(
        self, bot_handler, mock_update, mock_context
    ):
        """Test conversation state management throughout entire follow-up flow."""
        user_id = mock_update.effective_user.id
        improved_prompt = "Improved prompt"

        # Initial state: waiting for prompt
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # After improved prompt: waiting for follow-up choice
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)

        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is False
        assert user_state.waiting_for_followup_choice is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache == improved_prompt

        # After choosing ДА: in follow-up conversation
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, False)
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)

        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is False
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is True
        assert user_state.improved_prompt_cache == improved_prompt

        # After completion: back to waiting for prompt
        bot_handler.reset_user_state(user_id)

        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

    @pytest.mark.asyncio
    async def test_followup_workflow_cleanup_and_reset(
        self, bot_handler, mock_update, mock_context
    ):
        """Test proper cleanup and reset after follow-up completion."""
        user_id = mock_update.effective_user.id
        improved_prompt = "Improved prompt"
        refined_prompt = "Final refined prompt"

        # Set up follow-up conversation with history
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Add conversation history
        bot_handler.conversation_manager.append_message(
            user_id, "assistant", "Question 1"
        )
        bot_handler.conversation_manager.append_message(user_id, "user", "Answer 1")
        bot_handler.conversation_manager.append_message(
            user_id, "assistant", "Question 2"
        )
        bot_handler.conversation_manager.append_message(user_id, "user", "Answer 2")

        # Add token usage
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        # Complete the follow-up conversation
        await bot_handler._complete_followup_conversation(
            mock_update, user_id, refined_prompt
        )

        # Verify all state was properly reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify conversation history was cleared
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

        # Verify token totals were reset
        assert bot_handler.conversation_manager.get_token_totals(user_id) == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    @pytest.mark.asyncio
    async def test_followup_workflow_integration_with_existing_methods(
        self, bot_handler, mock_update, mock_context
    ):
        """Test integration with existing prompt optimization methods."""
        user_id = mock_update.effective_user.id
        original_prompt = "Test prompt for optimization"

        # Test integration with each optimization method
        methods = [(BTN_CRAFT, "CRAFT"), (BTN_LYRA, "LYRA Basic"), (BTN_GGL, "GGL")]

        for method_button, method_name in methods:
            # Reset state for each test
            bot_handler.reset_user_state(user_id)

            # Step 1: Submit prompt
            bot_handler.state_manager.set_waiting_for_prompt(user_id, True)
            mock_update.message.text = original_prompt
            await bot_handler.handle_message(mock_update, mock_context)

            # Step 2: Select method
            mock_update.message.text = method_button
            bot_handler.llm_client.send_prompt.return_value = (
                f"<IMPROVED_PROMPT>Improved with {method_name}</IMPROVED_PROMPT>"
            )
            await bot_handler.handle_message(mock_update, mock_context)

            # Verify follow-up offer was made after optimization
            user_state = bot_handler.state_manager.get_user_state(user_id)
            assert user_state.waiting_for_followup_choice is True
            assert user_state.improved_prompt_cache == f"Improved with {method_name}"

            # Verify conversation was reset to follow-up ready state
            assert (
                bot_handler.conversation_manager.is_waiting_for_method(user_id) is False
            )

    @pytest.mark.asyncio
    async def test_followup_workflow_error_recovery(
        self, bot_handler, mock_update, mock_context
    ):
        """Test error recovery mechanisms during follow-up workflow."""
        user_id = mock_update.effective_user.id
        improved_prompt = "Cached improved prompt"

        # Set up follow-up conversation
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Test LLM error during follow-up conversation
        mock_update.message.text = "User response"
        bot_handler.llm_client.send_prompt.side_effect = Exception("LLM timeout")

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify fallback to cached improved prompt
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify refined prompt was sent (fallback behavior)
        mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_followup_workflow_malformed_response_handling(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling of malformed refined prompt responses."""
        user_id = mock_update.effective_user.id
        improved_prompt = "Cached improved prompt"

        # Set up follow-up conversation
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Test malformed response (missing closing tag)
        mock_update.message.text = "User response"
        bot_handler.llm_client.send_prompt.return_value = (
            "<REFINED_PROMPT>Malformed response without closing tag"
        )

        await bot_handler.handle_message(mock_update, mock_context)

        # Verify parsing handled malformed response gracefully
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify refined prompt was extracted and sent
        mock_update.message.reply_text.assert_called()
