"""Unit tests for BotHandler._reset_current_session() protection.

This module contains unit tests for the _reset_current_session() method's
terminal state protection feature. These tests verify:
- Test with no session_id in state skips gracefully
- Test with "successful" session skips with log
- Test with "unsuccessful" session skips with log
- Test with "in_progress" session proceeds with reset
- Test database error handling continues gracefully

Requirements: 2.1, 2.2, 2.3, 2.4, 4.1, 4.2
"""

import logging
from unittest.mock import MagicMock

import pytest

from telegram_bot.core.bot_handler import BotHandler
from tests.unit.test_utils import create_mock_config, create_mock_llm_client


class TestResetCurrentSessionNoSessionId:
    """
    Tests for _reset_current_session() when no session_id exists in state.

    Requirements: 2.5
    """

    @pytest.fixture
    def bot_handler(self):
        """Create a BotHandler instance with mocked dependencies."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        llm_client = create_mock_llm_client()
        handler = BotHandler(config, llm_client, lambda event, payload: None)
        return handler

    def test_no_session_id_skips_gracefully(self, bot_handler, caplog):
        """
        Test that _reset_current_session() skips gracefully when no session_id in state.

        Requirements: 2.5 - WHEN no session exists for the user THEN the System
        SHALL skip the reset operation gracefully
        """
        user_id = 12345

        # Ensure no session_id is set
        bot_handler.state_manager.set_current_session_id(user_id, None)

        # Set up a mock session service
        mock_session_service = MagicMock()
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.DEBUG):
            bot_handler._reset_current_session(user_id)

        # Verify get_session was NOT called (no session_id to look up)
        mock_session_service.get_session.assert_not_called()

        # Verify reset_session was NOT called
        mock_session_service.reset_session.assert_not_called()

        # Verify debug log was written
        assert "reason=no_active_session" in caplog.text

    def test_no_session_service_skips_gracefully(self, bot_handler, caplog):
        """
        Test that _reset_current_session() skips gracefully when session_service is None.

        Requirements: 4.1 - Graceful degradation when session tracking unavailable
        """
        user_id = 12345

        # Set session_service to None
        bot_handler.session_service = None

        with caplog.at_level(logging.DEBUG):
            bot_handler._reset_current_session(user_id)

        # Verify debug log was written
        assert "reason=session_service_not_available" in caplog.text


class TestResetCurrentSessionSuccessfulStatus:
    """
    Tests for _reset_current_session() when session has "successful" status.

    Requirements: 2.2, 5.1
    """

    @pytest.fixture
    def bot_handler(self):
        """Create a BotHandler instance with mocked dependencies."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        llm_client = create_mock_llm_client()
        handler = BotHandler(config, llm_client, lambda event, payload: None)
        return handler

    def test_successful_session_skips_with_log(self, bot_handler, caplog):
        """
        Test that _reset_current_session() skips reset for "successful" session with log.

        Requirements: 2.2 - WHEN the session status is "successful" THEN the System
        SHALL skip the reset operation and log an info message
        """
        user_id = 12345
        session_id = 100

        # Set up session_id in state
        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        # Create mock session with "successful" status
        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.status = "successful"

        # Set up mock session service
        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = mock_session
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.INFO):
            bot_handler._reset_current_session(user_id)

        # Verify get_session was called
        mock_session_service.get_session.assert_called_once_with(session_id)

        # Verify reset_session was NOT called
        mock_session_service.reset_session.assert_not_called()

        # Verify info log was written with correct details
        assert "session_reset_skipped" in caplog.text
        assert "status=successful" in caplog.text
        assert "reason=already_terminal_state" in caplog.text

    def test_successful_session_does_not_modify_status(self, bot_handler):
        """
        Test that _reset_current_session() does not modify "successful" session status.

        Requirements: 2.2
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.status = "successful"

        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = mock_session
        bot_handler.session_service = mock_session_service

        bot_handler._reset_current_session(user_id)

        # Verify reset_session was NOT called (status should remain unchanged)
        mock_session_service.reset_session.assert_not_called()


class TestResetCurrentSessionUnsuccessfulStatus:
    """
    Tests for _reset_current_session() when session has "unsuccessful" status.

    Requirements: 2.3, 5.1
    """

    @pytest.fixture
    def bot_handler(self):
        """Create a BotHandler instance with mocked dependencies."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        llm_client = create_mock_llm_client()
        handler = BotHandler(config, llm_client, lambda event, payload: None)
        return handler

    def test_unsuccessful_session_skips_with_log(self, bot_handler, caplog):
        """
        Test that _reset_current_session() skips reset for "unsuccessful" session with log.

        Requirements: 2.3 - WHEN the session status is "unsuccessful" THEN the System
        SHALL skip the reset operation and log an info message
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.status = "unsuccessful"

        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = mock_session
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.INFO):
            bot_handler._reset_current_session(user_id)

        # Verify get_session was called
        mock_session_service.get_session.assert_called_once_with(session_id)

        # Verify reset_session was NOT called
        mock_session_service.reset_session.assert_not_called()

        # Verify info log was written with correct details
        assert "session_reset_skipped" in caplog.text
        assert "status=unsuccessful" in caplog.text
        assert "reason=already_terminal_state" in caplog.text

    def test_unsuccessful_session_does_not_modify_status(self, bot_handler):
        """
        Test that _reset_current_session() does not modify "unsuccessful" session status.

        Requirements: 2.3
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.status = "unsuccessful"

        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = mock_session
        bot_handler.session_service = mock_session_service

        bot_handler._reset_current_session(user_id)

        # Verify reset_session was NOT called
        mock_session_service.reset_session.assert_not_called()


class TestResetCurrentSessionInProgressStatus:
    """
    Tests for _reset_current_session() when session has "in_progress" status.

    Requirements: 2.4, 5.2
    """

    @pytest.fixture
    def bot_handler(self):
        """Create a BotHandler instance with mocked dependencies."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        llm_client = create_mock_llm_client()
        handler = BotHandler(config, llm_client, lambda event, payload: None)
        return handler

    def test_in_progress_session_proceeds_with_reset(self, bot_handler, caplog):
        """
        Test that _reset_current_session() proceeds with reset for "in_progress" session.

        Requirements: 2.4 - WHEN the session status is "in_progress" THEN the System
        SHALL proceed with the reset operation
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.status = "in_progress"

        mock_reset_result = MagicMock()
        mock_reset_result.duration_seconds = 120
        mock_reset_result.tokens_total = 500

        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = mock_session
        mock_session_service.reset_session.return_value = mock_reset_result
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.INFO):
            bot_handler._reset_current_session(user_id)

        # Verify get_session was called
        mock_session_service.get_session.assert_called_once_with(session_id)

        # Verify reset_session WAS called
        mock_session_service.reset_session.assert_called_once_with(session_id)

        # Verify info log was written for successful reset
        assert "session_reset |" in caplog.text
        assert "status=unsuccessful" in caplog.text

    def test_in_progress_session_logs_reset_details(self, bot_handler, caplog):
        """
        Test that _reset_current_session() logs reset details for "in_progress" session.

        Requirements: 5.2 - WHEN a session reset proceeds normally THEN the System
        SHALL log the session_id and status change
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.status = "in_progress"

        mock_reset_result = MagicMock()
        mock_reset_result.duration_seconds = 60
        mock_reset_result.tokens_total = 250

        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = mock_session
        mock_session_service.reset_session.return_value = mock_reset_result
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.INFO):
            bot_handler._reset_current_session(user_id)

        # Verify log contains session details
        assert f"session_id={session_id}" in caplog.text
        assert "duration=60s" in caplog.text
        assert "tokens=250" in caplog.text


class TestResetCurrentSessionDatabaseError:
    """
    Tests for _reset_current_session() database error handling.

    Requirements: 4.1, 4.2
    """

    @pytest.fixture
    def bot_handler(self):
        """Create a BotHandler instance with mocked dependencies."""
        config = create_mock_config()
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        llm_client = create_mock_llm_client()
        handler = BotHandler(config, llm_client, lambda event, payload: None)
        return handler

    def test_get_session_error_continues_gracefully(self, bot_handler, caplog):
        """
        Test that _reset_current_session() continues gracefully on get_session error.

        Requirements: 4.1 - WHEN session status check fails due to database error
        THEN the System SHALL log the error and proceed with state reset
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session_service = MagicMock()
        mock_session_service.get_session.side_effect = Exception("Database connection failed")
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.ERROR):
            # Should not raise exception
            bot_handler._reset_current_session(user_id)

        # Verify error was logged
        assert "session_reset_error" in caplog.text
        assert "Database connection failed" in caplog.text

    def test_reset_session_error_continues_gracefully(self, bot_handler, caplog):
        """
        Test that _reset_current_session() continues gracefully on reset_session error.

        Requirements: 4.1
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session = MagicMock()
        mock_session.id = session_id
        mock_session.status = "in_progress"

        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = mock_session
        mock_session_service.reset_session.return_value = None  # Indicates failure
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.WARNING):
            # Should not raise exception
            bot_handler._reset_current_session(user_id)

        # Verify warning was logged
        assert "session_reset_failed" in caplog.text
        assert "continuing_without_reset" in caplog.text

    def test_session_not_found_logs_warning(self, bot_handler, caplog):
        """
        Test that _reset_current_session() logs warning when session not found.

        Requirements: 4.1
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session_service = MagicMock()
        mock_session_service.get_session.return_value = None  # Session not found
        bot_handler.session_service = mock_session_service

        with caplog.at_level(logging.WARNING):
            bot_handler._reset_current_session(user_id)

        # Verify warning was logged
        assert "session_reset_skipped" in caplog.text
        assert "reason=session_not_found" in caplog.text

        # Verify reset_session was NOT called
        mock_session_service.reset_session.assert_not_called()

    def test_no_error_displayed_to_user(self, bot_handler):
        """
        Test that _reset_current_session() does not raise exceptions on errors.

        Requirements: 4.2 - WHEN session status protection is applied THEN the System
        SHALL NOT display any error messages to the user
        """
        user_id = 12345
        session_id = 100

        bot_handler.state_manager.set_current_session_id(user_id, session_id)

        mock_session_service = MagicMock()
        mock_session_service.get_session.side_effect = Exception("Critical database error")
        bot_handler.session_service = mock_session_service

        # Should not raise any exception - graceful degradation
        try:
            bot_handler._reset_current_session(user_id)
        except Exception as e:
            pytest.fail(f"_reset_current_session raised an exception: {e}")
