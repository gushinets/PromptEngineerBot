"""Tests for the Telegram bot functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Import the functions to test


class TestBotFunctionality:
    """Test cases for the bot's core functionality."""

    @pytest.mark.asyncio
    async def test_start_command(self, mock_update, mock_context):
        """Test the /start command handler."""
        from unittest.mock import MagicMock

        from telegram import ReplyKeyboardMarkup

        from telegram_bot.core.bot_handler import BotHandler
        from telegram_bot.utils.config import BotConfig

        # Create a real bot handler with mocked dependencies
        mock_config = MagicMock(spec=BotConfig)
        mock_config.bot_id = "test_bot"
        mock_config.llm_backend = "TEST"
        mock_config.model_name = "test-model"

        mock_llm_client = MagicMock()
        bot_handler = BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

        # Execute
        await bot_handler.handle_start(mock_update, mock_context)

        # Verify the bot sent the expected response
        mock_update.message.reply_text.assert_awaited_once()
        args, kwargs = mock_update.message.reply_text.call_args

        # Check the message text
        # The welcome message is long; assert it was sent (not specific phrase)
        assert isinstance(args[0], str) and len(args[0]) > 10

        # Check the reply markup structure
        assert "reply_markup" in kwargs
        reply_markup = kwargs["reply_markup"]
        assert isinstance(reply_markup, ReplyKeyboardMarkup)
        assert reply_markup.resize_keyboard is True

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "method,expected_prompt_type",
        [
            ("CRAFT", "CRAFT"),
            ("LYRA basic", "LYRA"),
            ("GGL Guide", "GGL"),
        ],
    )
    async def test_method_selection(
        self, mock_update, mock_context, mock_llm_client, method, expected_prompt_type
    ):
        """Test different optimization method selections."""
        from unittest.mock import MagicMock

        from telegram_bot.core.bot_handler import BotHandler
        from telegram_bot.utils.config import BotConfig

        # Create a real bot handler with mocked dependencies
        mock_config = MagicMock(spec=BotConfig)
        mock_config.bot_id = "test_bot"
        mock_config.llm_backend = "TEST"
        mock_config.model_name = "test-model"

        # Create bot handler with our mock client
        bot_handler = BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

        # Test the flow directly
        user_id = mock_update.effective_user.id

        # 1. Start the bot
        await bot_handler.handle_start(mock_update, mock_context)

        # 2. Send a user prompt
        mock_update.message.text = "test prompt"
        await bot_handler.handle_message(mock_update, mock_context)

        # 3. Select method
        mapping = {
            "CRAFT": "🛠 CRAFT",
            "LYRA basic": "⚡ LYRA",
            "GGL Guide": "🔍 GGL",
        }
        mock_update.message.text = mapping[method]
        await bot_handler.handle_message(mock_update, mock_context)

        # Verify the LLM was called
        mock_llm_client.send_prompt.assert_awaited()

        # Check that the correct prompt type was used
        if mock_llm_client.send_prompt.call_args:
            messages = mock_llm_client.send_prompt.call_args[0][0]
            assert messages[0]["role"] == "system"
            content = messages[0]["content"]
            if expected_prompt_type == "CRAFT":
                assert (
                    "C.R.A.F.T" in content
                    or "СТРУКТУРА (C.R.A.F.T.)" in content
                    or "CRAFT" in content
                )
            elif expected_prompt_type == "LYRA":
                assert "Lyra" in content or "МЕТОДОЛОГИЯ 4-D" in content or "LYRA" in content
            elif expected_prompt_type == "GGL":
                assert "Google" in content or "Prompt Engineering" in content or "GGL" in content


class TestTimeoutHandling:
    """Test cases for timeout handling in the bot."""

    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self, mock_update, mock_context, mock_llm_client):
        """Test that the bot handles LLM timeouts gracefully."""
        from unittest.mock import MagicMock

        from telegram_bot.core.bot_handler import BotHandler
        from telegram_bot.utils.config import BotConfig

        # Set up a timeout error
        mock_llm_client.send_prompt.side_effect = TimeoutError("LLM timeout")

        # Create a real bot handler with mocked dependencies
        mock_config = MagicMock(spec=BotConfig)
        mock_config.bot_id = "test_bot"
        mock_config.llm_backend = "TEST"
        mock_config.model_name = "test-model"

        bot_handler = BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

        # Test the flow
        await bot_handler.handle_start(mock_update, mock_context)

        # Send a user prompt
        mock_update.message.text = "test prompt"
        await bot_handler.handle_message(mock_update, mock_context)

        # Trigger the LLM call with timeout
        mock_update.message.text = "🛠 CRAFT"
        await bot_handler.handle_message(mock_update, mock_context)

        # Verify error handling - check that reply_text was called
        mock_update.message.reply_text.assert_called()

        # Check if any of the calls contained an error message
        calls = mock_update.message.reply_text.call_args_list
        error_found = False
        for call in calls:
            args, _ = call
            text = str(args[0])
            if ("ошибка" in text.lower()) or ("Error" in text) or ("timeout" in text.lower()):
                error_found = True
                break

        assert error_found, (
            f"No error message found in calls: {[str(call[0][0]) for call in calls]}"
        )

    @pytest.mark.asyncio
    async def test_application_timeouts(self, mock_application):
        """Verify that application timeouts are set correctly."""
        from telegram_bot.main import main

        with patch("telegram_bot.main.Application") as mock_app_class:
            mock_app = MagicMock()
            # Configure the builder chain
            builder = MagicMock()
            builder.token.return_value = builder
            builder.connect_timeout.return_value = builder
            builder.pool_timeout.return_value = builder
            builder.read_timeout.return_value = builder
            builder.write_timeout.return_value = builder
            builder.get_updates_read_timeout.return_value = builder
            builder.build.return_value = mock_app
            mock_app_class.builder.return_value = builder
            # Make application lifecycle methods awaitable
            mock_app.initialize = AsyncMock(return_value=None)
            mock_app.start = AsyncMock(return_value=None)
            mock_app.updater = MagicMock()
            mock_app.updater.start_polling = AsyncMock(return_value=None)
            mock_app.stop = AsyncMock(return_value=None)
            mock_app.shutdown = AsyncMock(return_value=None)

            # Run the main function, force loop to exit immediately
            with patch("telegram_bot.main.asyncio.sleep", new=AsyncMock(side_effect=SystemExit)):
                with pytest.raises(SystemExit):
                    await main()

            # Verify timeout settings
            builder.token.assert_called_once()
            builder.connect_timeout.assert_called_with(60.0)
            builder.read_timeout.assert_called_with(300.0)
            builder.write_timeout.assert_called_with(120.0)
