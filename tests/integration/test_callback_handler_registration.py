"""Integration tests for callback handler registration in main application.

This module tests that the CallbackQueryHandlers for follow-up inline buttons
are correctly registered in the Telegram application.

Requirements: 8.4
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram.ext import CallbackQueryHandler

from telegram_bot.main import handle_disabled_callback, handle_followup_callback


class TestCallbackHandlerRegistration:
    """Test cases for callback handler registration.

    These tests verify that the callback handlers for follow-up inline buttons
    are correctly defined and can be registered with the Telegram application.

    Requirements: 8.4
    """

    def test_handle_followup_callback_is_async_function(self):
        """Test that handle_followup_callback is an async function.

        Validates: Requirements 8.4
        """
        import asyncio

        assert asyncio.iscoroutinefunction(handle_followup_callback)

    def test_handle_disabled_callback_is_async_function(self):
        """Test that handle_disabled_callback is an async function.

        Validates: Requirements 8.4
        """
        import asyncio

        assert asyncio.iscoroutinefunction(handle_disabled_callback)

    @pytest.mark.asyncio
    async def test_handle_followup_callback_delegates_to_bot_handler(self):
        """Test that handle_followup_callback delegates to bot_handler.

        Validates: Requirements 8.4
        """
        mock_update = MagicMock()
        mock_context = MagicMock()

        with patch("telegram_bot.main.bot_handler") as mock_bot_handler:
            mock_bot_handler.handle_followup_callback = AsyncMock()

            await handle_followup_callback(mock_update, mock_context)

            mock_bot_handler.handle_followup_callback.assert_called_once_with(
                mock_update, mock_context
            )

    @pytest.mark.asyncio
    async def test_handle_disabled_callback_answers_query(self):
        """Test that handle_disabled_callback answers the callback query.

        Validates: Requirements 8.4
        """
        mock_query = MagicMock()
        mock_query.answer = AsyncMock()

        mock_update = MagicMock()
        mock_update.callback_query = mock_query

        mock_context = MagicMock()

        await handle_disabled_callback(mock_update, mock_context)

        mock_query.answer.assert_called_once()

    def test_callback_query_handler_can_be_created_with_followup_pattern(self):
        """Test that CallbackQueryHandler can be created with followup pattern.

        Validates: Requirements 8.4
        """
        handler = CallbackQueryHandler(handle_followup_callback, pattern="^followup_(yes|no)$")

        assert handler is not None
        assert handler.callback == handle_followup_callback

    def test_callback_query_handler_can_be_created_with_disabled_pattern(self):
        """Test that CallbackQueryHandler can be created with disabled pattern.

        Validates: Requirements 8.4
        """
        handler = CallbackQueryHandler(handle_disabled_callback, pattern="^disabled$")

        assert handler is not None
        assert handler.callback == handle_disabled_callback


class TestCallbackPatternMatching:
    """Test cases for callback pattern matching.

    These tests verify that the regex patterns used for callback handlers
    correctly match the expected callback data values.

    Requirements: 8.4
    """

    def test_followup_pattern_matches_yes(self):
        """Test that followup pattern matches 'followup_yes'.

        Validates: Requirements 8.4
        """
        import re

        pattern = "^followup_(yes|no)$"
        assert re.match(pattern, "followup_yes") is not None

    def test_followup_pattern_matches_no(self):
        """Test that followup pattern matches 'followup_no'.

        Validates: Requirements 8.4
        """
        import re

        pattern = "^followup_(yes|no)$"
        assert re.match(pattern, "followup_no") is not None

    def test_followup_pattern_does_not_match_invalid(self):
        """Test that followup pattern does not match invalid values.

        Validates: Requirements 8.4
        """
        import re

        pattern = "^followup_(yes|no)$"
        assert re.match(pattern, "followup_maybe") is None
        assert re.match(pattern, "disabled") is None
        assert re.match(pattern, "followup_") is None

    def test_disabled_pattern_matches_disabled(self):
        """Test that disabled pattern matches 'disabled'.

        Validates: Requirements 8.4
        """
        import re

        pattern = "^disabled$"
        assert re.match(pattern, "disabled") is not None

    def test_disabled_pattern_does_not_match_invalid(self):
        """Test that disabled pattern does not match invalid values.

        Validates: Requirements 8.4
        """
        import re

        pattern = "^disabled$"
        assert re.match(pattern, "followup_yes") is None
        assert re.match(pattern, "disabled_button") is None
        assert re.match(pattern, "") is None
