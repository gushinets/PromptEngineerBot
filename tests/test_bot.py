"""Tests for the Telegram bot functionality."""
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import the functions to test
from main import start, handle_message, safe_reply

class TestBotFunctionality:
    """Test cases for the bot's core functionality."""

    @pytest.mark.asyncio
    async def test_start_command(self, mock_update, mock_context):
        """Test the /start command handler."""
        # Setup
        from telegram import ReplyKeyboardMarkup
        
        # Execute
        await start(mock_update, mock_context)
        
        # Verify the bot sent the expected response
        mock_update.message.reply_text.assert_called_once()
        args, kwargs = mock_update.message.reply_text.call_args
        
        # Check the message text
        assert "Введите промпт" in args[0]
        
        # Check the reply markup structure
        assert 'reply_markup' in kwargs
        reply_markup = kwargs['reply_markup']
        assert isinstance(reply_markup, ReplyKeyboardMarkup)
        assert reply_markup.resize_keyboard is True
        assert len(reply_markup.keyboard) == 1  # One row
        assert len(reply_markup.keyboard[0]) == 0  # Empty row (no buttons)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,expected_prompt_type", [
        ("CRAFT", "craft_prompt"),
        ("LYRA basic", "lyra_prompt"),
        ("GGL Guide", "ggl_prompt"),
    ])
    async def test_method_selection(self, mock_update, mock_context, mock_llm_client, method, expected_prompt_type):
        """Test different optimization method selections."""
        # First, set up the test with a user prompt
        mock_update.message.text = "test prompt"
        await handle_message(mock_update, mock_context)
        
        # Then test method selection
        mock_update.message.text = method
        await handle_message(mock_update, mock_context)
        
        # Verify the LLM was called with the correct prompt type
        mock_llm_client.send_prompt.assert_called_once()
        messages = mock_llm_client.send_prompt.call_args[0][0]
        assert messages[0]["role"] == "system"
        assert expected_prompt_type in messages[0]["content"]

    @pytest.mark.asyncio
    async def test_safe_reply_success(self, mock_update):
        """Test successful message sending with safe_reply."""
        # Setup
        test_message = "Test message"
        
        # Create an AsyncMock for reply_text
        mock_update.message.reply_text = AsyncMock(return_value=None)
        
        # Execute
        result = await safe_reply(mock_update, test_message)
        
        # Verify
        assert result is True
        mock_update.message.reply_text.assert_awaited_once()
        args, kwargs = mock_update.message.reply_text.call_args
        assert args[0] == test_message

    @pytest.mark.asyncio
    async def test_safe_reply_retry(self, mock_update):
        """Test safe_reply with retry on failure."""
        # Make the first call fail, then succeed
        mock_update.message.reply_text.side_effect = [
            Exception("Network error"),
            "Message sent"
        ]
        
        with patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await safe_reply(mock_update, "Test retry")
            
            # Should have retried once
            assert mock_update.message.reply_text.call_count == 2
            assert mock_sleep.called
            assert result is True

class TestTimeoutHandling:
    """Test cases for timeout handling in the bot."""
    
    @pytest.mark.asyncio
    async def test_llm_timeout_handling(self, mock_update, mock_context, mock_llm_client):
        """Test that the bot handles LLM timeouts gracefully."""
        # Set up a timeout error
        mock_llm_client.send_prompt.side_effect = asyncio.TimeoutError("LLM timeout")
        
        # First set a user prompt
        mock_update.message.text = "test prompt"
        await handle_message(mock_update, mock_context)
        
        # Then trigger the LLM call
        mock_update.message.text = "CRAFT"
        await handle_message(mock_update, mock_context)
        
        # Verify error handling
        mock_update.message.reply_text.assert_called()
        args, _ = mock_update.message.reply_text.call_args
        assert "Ошибка" in args[0] or "Error" in args[0]

    @pytest.mark.asyncio
    async def test_application_timeouts(self, mock_application):
        """Verify that application timeouts are set correctly."""
        from main import main
        
        with patch('main.Application') as mock_app_class:
            mock_app = MagicMock()
            mock_app_class.builder.return_value = mock_app
            
            # Run the main function
            with pytest.raises(SystemExit):
                await main()
            
            # Verify timeout settings
            mock_app.token.assert_called_once()
            mock_app.connect_timeout.assert_called_with(60.0)
            mock_app.read_timeout.assert_called_with(300.0)
            mock_app.write_timeout.assert_called_with(120.0)
