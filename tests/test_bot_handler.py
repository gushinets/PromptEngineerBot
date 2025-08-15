"""Tests for the bot handler module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import ReplyKeyboardMarkup

from src.bot_handler import BotHandler
from src.config import BotConfig
from src.messages import BTN_CRAFT, BTN_GGL, BTN_LYRA, BTN_RESET


class TestBotHandler:
    """Test cases for BotHandler class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = MagicMock(spec=BotConfig)
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        config.model_name = "test-model"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.send_prompt = AsyncMock(return_value="Mocked LLM response")
        client.get_last_usage = MagicMock(
            return_value={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            }
        )
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
        assert "Ошибка" in args[0]

    @pytest.mark.asyncio
    async def test_process_with_llm_improved_prompt(
        self, bot_handler, mock_update, mock_context
    ):
        """Test LLM processing with improved prompt response."""
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

        # Verify response was sent
        mock_update.message.reply_text.assert_called()

        # Verify conversation was reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []
        assert (
            bot_handler.state_manager.get_user_state(user_id).waiting_for_prompt is True
        )

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
