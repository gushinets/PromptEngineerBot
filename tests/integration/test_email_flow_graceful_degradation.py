"""
Integration tests for email flow graceful degradation.

This module tests that the email flow completes successfully even when
session tracking operations fail. This validates Requirements 7.1, 7.2, 7.3, 7.4.

Requirements:
- 7.1: WHEN session tracking fails during email flow THEN the System SHALL log
       the error and continue with the email delivery
- 7.2: WHEN token tracking fails THEN the System SHALL log the error and
       continue with the optimization
- 7.3: WHEN email event logging fails THEN the System SHALL log the error but
       not affect the user's email delivery status
- 7.4: WHEN any session operation fails THEN the System SHALL NOT display error
       messages to the user about session tracking
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_bot.core.conversation_manager import ConversationManager
from telegram_bot.core.state_manager import StateManager
from telegram_bot.flows.email_flow import EmailFlowOrchestrator
from telegram_bot.services.llm.base import LLMClientBase
from telegram_bot.services.session_service import OptimizationMethod
from telegram_bot.utils.config import BotConfig


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
    client = MagicMock(spec=LLMClientBase)
    client.send_prompt = AsyncMock(return_value="Optimized result")
    client.get_last_usage = MagicMock(
        return_value={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )
    return client


@pytest.fixture
def mock_conversation_manager():
    """Create mock conversation manager."""
    manager = MagicMock(spec=ConversationManager)
    manager.get_user_prompt = MagicMock(return_value="Test prompt")
    return manager


@pytest.fixture
def mock_state_manager():
    """Create mock state manager."""
    manager = MagicMock(spec=StateManager)
    manager.get_current_session_id = MagicMock(return_value=100)
    manager.get_email_flow_data = MagicMock(
        return_value={"original_prompt": "Test prompt", "email": "test@example.com"}
    )
    return manager


@pytest.fixture
def mock_update():
    """Create mock Telegram update."""
    update = MagicMock()
    update.message = MagicMock()
    update.message.reply_text = AsyncMock()
    return update


@pytest.fixture
def mock_context():
    """Create mock Telegram context."""
    return MagicMock()


@pytest.fixture
def mock_session_service_failing():
    """Create mock session service that raises exceptions on all operations."""
    service = MagicMock()
    service.set_optimization_method = MagicMock(
        side_effect=Exception("Session service unavailable")
    )
    service.add_tokens = MagicMock(side_effect=Exception("Token tracking failed"))
    service.add_message = MagicMock(side_effect=Exception("Message logging failed"))
    service.log_email_sent = MagicMock(side_effect=Exception("Email event logging failed"))
    service.complete_session = MagicMock(side_effect=Exception("Session completion failed"))
    service.reset_session = MagicMock(side_effect=Exception("Session reset failed"))
    return service


@pytest.fixture
def real_email_flow_orchestrator(
    mock_config, mock_llm_client, mock_conversation_manager, mock_state_manager
):
    """Create real EmailFlowOrchestrator with mocked dependencies."""
    with (
        patch("telegram_bot.flows.email_flow.get_auth_service") as mock_auth,
        patch("telegram_bot.flows.email_flow.get_email_service") as mock_email,
        patch("telegram_bot.flows.email_flow.get_redis_client") as mock_redis,
    ):
        mock_auth.return_value = MagicMock()
        mock_email.return_value = MagicMock()
        mock_redis.return_value = MagicMock()

        orchestrator = EmailFlowOrchestrator(
            config=mock_config,
            llm_client=mock_llm_client,
            conversation_manager=mock_conversation_manager,
            state_manager=mock_state_manager,
        )
        return orchestrator


class TestEmailFlowGracefulDegradation:
    """Integration tests for graceful degradation when session tracking fails."""

    async def test_email_flow_succeeds_when_set_optimization_method_fails(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
        mock_session_service_failing,
    ):
        """
        Test that email flow completes successfully when set_optimization_method fails.

        Verifies: Requirement 7.1 - Session tracking failures are logged but
        do not block email delivery.
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Test prompt for graceful degradation"

        # Mock state manager
        real_email_flow_orchestrator.state_manager.get_current_session_id = MagicMock(
            return_value=session_id
        )
        real_email_flow_orchestrator.state_manager.get_email_flow_data = MagicMock(
            return_value={"original_prompt": original_prompt, "email": "test@example.com"}
        )

        # Mock email service success
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service = MagicMock()
        mock_email_service.send_optimized_prompts_email = AsyncMock(return_value=mock_email_result)
        real_email_flow_orchestrator.email_service = mock_email_service

        # Mock the session service getter to return failing service
        with patch.object(
            real_email_flow_orchestrator,
            "_get_session_service",
            return_value=mock_session_service_failing,
        ):
            # Mock optimization results
            with patch.object(
                real_email_flow_orchestrator,
                "_run_all_optimizations_with_modified_prompts",
                new_callable=AsyncMock,
                return_value={
                    "CRAFT": "CRAFT result",
                    "LYRA": "LYRA result",
                    "GGL": "GGL result",
                },
            ):
                result = (
                    await real_email_flow_orchestrator._run_direct_optimization_and_email_delivery(
                        mock_update, mock_context, user_id, original_prompt
                    )
                )

        # Verify email flow completed successfully despite session tracking failure
        assert result is True

        # Verify email was sent
        mock_email_service.send_optimized_prompts_email.assert_called_once()

        # Verify set_optimization_method was attempted (and failed)
        mock_session_service_failing.set_optimization_method.assert_called_once_with(
            session_id, OptimizationMethod.ALL
        )

    async def test_email_flow_succeeds_when_token_tracking_fails(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
        mock_session_service_failing,
        mock_llm_client,
    ):
        """
        Test that optimization completes when token tracking fails.

        Verifies: Requirement 7.2 - Token tracking failures are logged but
        do not block optimization.
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Test prompt for token tracking failure"

        # Attach mocked llm_client to orchestrator
        real_email_flow_orchestrator.llm_client = mock_llm_client

        # Mock the session service getter to return failing service
        with patch.object(
            real_email_flow_orchestrator,
            "_get_session_service",
            return_value=mock_session_service_failing,
        ):
            # Mock dependencies container
            with patch("telegram_bot.flows.email_flow.get_container") as mock_container:
                mock_prompt_loader = MagicMock()
                mock_prompt_loader.craft_email_prompt = "CRAFT system prompt"
                mock_prompt_loader.lyra_email_prompt = "LYRA system prompt"
                mock_prompt_loader.ggl_email_prompt = "GGL system prompt"
                mock_container.return_value.get_prompt_loader.return_value = mock_prompt_loader

                # Call the method that tracks tokens
                result = (
                    await real_email_flow_orchestrator._run_all_optimizations_with_modified_prompts(
                        original_prompt, user_id, session_id
                    )
                )

        # Verify optimization completed successfully despite token tracking failure
        assert result is not None
        assert "CRAFT" in result
        assert "LYRA" in result
        assert "GGL" in result

        # Verify add_tokens was attempted 3 times (and failed each time)
        assert mock_session_service_failing.add_tokens.call_count == 3

    async def test_email_flow_succeeds_when_message_logging_fails(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
        mock_llm_client,
    ):
        """
        Test that optimization completes when message logging fails.

        Verifies: Requirement 7.2 - Message logging failures are logged but
        do not block optimization.
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Test prompt for message logging failure"

        # Create a session service that fails only on add_message
        mock_session_service = MagicMock()
        mock_session_service.add_tokens = MagicMock(return_value=MagicMock())  # Success
        mock_session_service.add_message = MagicMock(
            side_effect=Exception("Message logging failed")
        )

        # Attach mocked llm_client to orchestrator
        real_email_flow_orchestrator.llm_client = mock_llm_client

        # Mock the session service getter
        with patch.object(
            real_email_flow_orchestrator,
            "_get_session_service",
            return_value=mock_session_service,
        ):
            # Mock dependencies container
            with patch("telegram_bot.flows.email_flow.get_container") as mock_container:
                mock_prompt_loader = MagicMock()
                mock_prompt_loader.craft_email_prompt = "CRAFT system prompt"
                mock_prompt_loader.lyra_email_prompt = "LYRA system prompt"
                mock_prompt_loader.ggl_email_prompt = "GGL system prompt"
                mock_container.return_value.get_prompt_loader.return_value = mock_prompt_loader

                # Call the method that logs messages
                result = (
                    await real_email_flow_orchestrator._run_all_optimizations_with_modified_prompts(
                        original_prompt, user_id, session_id
                    )
                )

        # Verify optimization completed successfully despite message logging failure
        assert result is not None
        assert "CRAFT" in result
        assert "LYRA" in result
        assert "GGL" in result

        # Verify add_tokens was called 3 times (succeeded)
        assert mock_session_service.add_tokens.call_count == 3

        # Verify add_message was attempted 3 times (and failed each time)
        assert mock_session_service.add_message.call_count == 3

    async def test_email_flow_succeeds_when_email_event_logging_fails(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
        mock_session_service_failing,
    ):
        """
        Test that email delivery status is not affected when email event logging fails.

        Verifies: Requirement 7.3 - Email event logging failures are logged but
        do not affect the user's email delivery status.
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Test prompt for email event logging failure"

        # Mock state manager
        real_email_flow_orchestrator.state_manager.get_current_session_id = MagicMock(
            return_value=session_id
        )
        real_email_flow_orchestrator.state_manager.get_email_flow_data = MagicMock(
            return_value={"original_prompt": original_prompt, "email": "test@example.com"}
        )

        # Mock email service success
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service = MagicMock()
        mock_email_service.send_optimized_prompts_email = AsyncMock(return_value=mock_email_result)
        real_email_flow_orchestrator.email_service = mock_email_service

        # Mock the session service getter to return failing service
        with patch.object(
            real_email_flow_orchestrator,
            "_get_session_service",
            return_value=mock_session_service_failing,
        ):
            # Mock optimization results
            with patch.object(
                real_email_flow_orchestrator,
                "_run_all_optimizations_with_modified_prompts",
                new_callable=AsyncMock,
                return_value={
                    "CRAFT": "CRAFT result",
                    "LYRA": "LYRA result",
                    "GGL": "GGL result",
                },
            ):
                result = (
                    await real_email_flow_orchestrator._run_direct_optimization_and_email_delivery(
                        mock_update, mock_context, user_id, original_prompt
                    )
                )

        # Verify email flow completed successfully despite email event logging failure
        assert result is True

        # Verify email was sent
        mock_email_service.send_optimized_prompts_email.assert_called_once()

        # Verify log_email_sent was attempted (and failed)
        mock_session_service_failing.log_email_sent.assert_called_once()

    async def test_email_flow_succeeds_when_complete_session_fails(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
    ):
        """
        Test that email delivery succeeds when session completion fails.

        Verifies: Requirement 7.1 - Session tracking failures are logged but
        do not block email delivery.
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Test prompt for session completion failure"

        # Create a session service that fails only on complete_session
        mock_session_service = MagicMock()
        mock_session_service.set_optimization_method = MagicMock(return_value=MagicMock())
        mock_session_service.log_email_sent = MagicMock(return_value=MagicMock())  # Success
        mock_session_service.complete_session = MagicMock(
            side_effect=Exception("Session completion failed")
        )

        # Mock state manager
        real_email_flow_orchestrator.state_manager.get_current_session_id = MagicMock(
            return_value=session_id
        )
        real_email_flow_orchestrator.state_manager.get_email_flow_data = MagicMock(
            return_value={"original_prompt": original_prompt, "email": "test@example.com"}
        )

        # Mock email service success
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service = MagicMock()
        mock_email_service.send_optimized_prompts_email = AsyncMock(return_value=mock_email_result)
        real_email_flow_orchestrator.email_service = mock_email_service

        # Mock the session service getter
        with patch.object(
            real_email_flow_orchestrator,
            "_get_session_service",
            return_value=mock_session_service,
        ):
            # Mock optimization results
            with patch.object(
                real_email_flow_orchestrator,
                "_run_all_optimizations_with_modified_prompts",
                new_callable=AsyncMock,
                return_value={
                    "CRAFT": "CRAFT result",
                    "LYRA": "LYRA result",
                    "GGL": "GGL result",
                },
            ):
                result = (
                    await real_email_flow_orchestrator._run_direct_optimization_and_email_delivery(
                        mock_update, mock_context, user_id, original_prompt
                    )
                )

        # Verify email flow completed successfully despite session completion failure
        assert result is True

        # Verify log_email_sent was called (succeeded)
        mock_session_service.log_email_sent.assert_called_once()

        # Verify complete_session was attempted (and failed)
        mock_session_service.complete_session.assert_called_once_with(session_id)

    async def test_no_session_tracking_error_messages_shown_to_user(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
        mock_session_service_failing,
    ):
        """
        Test that no session tracking error messages are shown to the user.

        Verifies: Requirement 7.4 - Session operation failures SHALL NOT display
        error messages to the user about session tracking.
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Test prompt for no error messages"

        # Mock state manager
        real_email_flow_orchestrator.state_manager.get_current_session_id = MagicMock(
            return_value=session_id
        )
        real_email_flow_orchestrator.state_manager.get_email_flow_data = MagicMock(
            return_value={"original_prompt": original_prompt, "email": "test@example.com"}
        )

        # Mock email service success
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service = MagicMock()
        mock_email_service.send_optimized_prompts_email = AsyncMock(return_value=mock_email_result)
        real_email_flow_orchestrator.email_service = mock_email_service

        # Mock the session service getter to return failing service
        with patch.object(
            real_email_flow_orchestrator,
            "_get_session_service",
            return_value=mock_session_service_failing,
        ):
            # Mock optimization results
            with patch.object(
                real_email_flow_orchestrator,
                "_run_all_optimizations_with_modified_prompts",
                new_callable=AsyncMock,
                return_value={
                    "CRAFT": "CRAFT result",
                    "LYRA": "LYRA result",
                    "GGL": "GGL result",
                },
            ):
                await real_email_flow_orchestrator._run_direct_optimization_and_email_delivery(
                    mock_update, mock_context, user_id, original_prompt
                )

        # Verify no error messages about session tracking were sent to user
        # Check all reply_text calls
        for call in mock_update.message.reply_text.call_args_list:
            message = call[0][0] if call[0] else call.kwargs.get("text", "")
            # Verify no session-related error messages
            assert "session" not in message.lower()
            assert "tracking" not in message.lower()
            assert "token" not in message.lower() or (
                "token" in message.lower() and "error" not in message.lower()
            )

    async def test_email_flow_succeeds_when_session_service_unavailable(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
    ):
        """
        Test that email flow completes when session service is completely unavailable.

        Verifies: Requirement 7.1 - Email flow continues when session service
        is not initialized.
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Test prompt for unavailable session service"

        # Mock state manager
        real_email_flow_orchestrator.state_manager.get_current_session_id = MagicMock(
            return_value=session_id
        )
        real_email_flow_orchestrator.state_manager.get_email_flow_data = MagicMock(
            return_value={"original_prompt": original_prompt, "email": "test@example.com"}
        )

        # Mock email service success
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service = MagicMock()
        mock_email_service.send_optimized_prompts_email = AsyncMock(return_value=mock_email_result)
        real_email_flow_orchestrator.email_service = mock_email_service

        # Mock the session service getter to return None (service unavailable)
        with patch.object(real_email_flow_orchestrator, "_get_session_service", return_value=None):
            # Mock optimization results
            with patch.object(
                real_email_flow_orchestrator,
                "_run_all_optimizations_with_modified_prompts",
                new_callable=AsyncMock,
                return_value={
                    "CRAFT": "CRAFT result",
                    "LYRA": "LYRA result",
                    "GGL": "GGL result",
                },
            ):
                result = (
                    await real_email_flow_orchestrator._run_direct_optimization_and_email_delivery(
                        mock_update, mock_context, user_id, original_prompt
                    )
                )

        # Verify email flow completed successfully despite session service being unavailable
        assert result is True

        # Verify email was sent
        mock_email_service.send_optimized_prompts_email.assert_called_once()

    async def test_email_flow_succeeds_when_no_session_id(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
    ):
        """
        Test that email flow completes when no session ID is available.

        Verifies: Requirement 7.1 - Email flow continues when session ID
        is not available.
        """
        user_id = 12345
        original_prompt = "Test prompt for no session ID"

        # Mock state manager to return None for session_id
        real_email_flow_orchestrator.state_manager.get_current_session_id = MagicMock(
            return_value=None
        )
        real_email_flow_orchestrator.state_manager.get_email_flow_data = MagicMock(
            return_value={"original_prompt": original_prompt, "email": "test@example.com"}
        )

        # Mock email service success
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service = MagicMock()
        mock_email_service.send_optimized_prompts_email = AsyncMock(return_value=mock_email_result)
        real_email_flow_orchestrator.email_service = mock_email_service

        # Mock session service (should not be called when session_id is None)
        mock_session_service = MagicMock()

        with patch.object(
            real_email_flow_orchestrator, "_get_session_service", return_value=mock_session_service
        ):
            # Mock optimization results
            with patch.object(
                real_email_flow_orchestrator,
                "_run_all_optimizations_with_modified_prompts",
                new_callable=AsyncMock,
                return_value={
                    "CRAFT": "CRAFT result",
                    "LYRA": "LYRA result",
                    "GGL": "GGL result",
                },
            ):
                result = (
                    await real_email_flow_orchestrator._run_direct_optimization_and_email_delivery(
                        mock_update, mock_context, user_id, original_prompt
                    )
                )

        # Verify email flow completed successfully
        assert result is True

        # Verify email was sent
        mock_email_service.send_optimized_prompts_email.assert_called_once()

        # Verify session service methods were NOT called (no session_id)
        mock_session_service.set_optimization_method.assert_not_called()
        mock_session_service.complete_session.assert_not_called()
        mock_session_service.log_email_sent.assert_not_called()

    async def test_all_session_operations_fail_but_email_succeeds(
        self,
        real_email_flow_orchestrator,
        mock_update,
        mock_context,
        mock_session_service_failing,
        mock_llm_client,
    ):
        """
        Comprehensive test: all session operations fail but email delivery succeeds.

        This is a comprehensive integration test that verifies graceful degradation
        when ALL session tracking operations fail simultaneously.

        Note: Due to the implementation structure, when add_tokens fails, add_message
        is not called (they're in the same try/except block). Similarly, when
        log_email_sent fails, complete_session is not called. This is expected
        behavior - the entire session tracking block fails gracefully together.

        Verifies: Requirements 7.1, 7.2, 7.3, 7.4
        """
        user_id = 12345
        session_id = 100
        original_prompt = "Comprehensive graceful degradation test"
        user_email = "test@example.com"

        # Mock state manager
        real_email_flow_orchestrator.state_manager.get_current_session_id = MagicMock(
            return_value=session_id
        )
        real_email_flow_orchestrator.state_manager.get_email_flow_data = MagicMock(
            return_value={"original_prompt": original_prompt, "email": user_email}
        )

        # Attach mocked llm_client to orchestrator
        real_email_flow_orchestrator.llm_client = mock_llm_client

        # Mock email service success
        mock_email_result = MagicMock()
        mock_email_result.success = True
        mock_email_service = MagicMock()
        mock_email_service.send_optimized_prompts_email = AsyncMock(return_value=mock_email_result)
        real_email_flow_orchestrator.email_service = mock_email_service

        # Mock the session service getter to return failing service
        with patch.object(
            real_email_flow_orchestrator,
            "_get_session_service",
            return_value=mock_session_service_failing,
        ):
            # Mock dependencies container
            with patch("telegram_bot.flows.email_flow.get_container") as mock_container:
                mock_prompt_loader = MagicMock()
                mock_prompt_loader.craft_email_prompt = "CRAFT system prompt"
                mock_prompt_loader.lyra_email_prompt = "LYRA system prompt"
                mock_prompt_loader.ggl_email_prompt = "GGL system prompt"
                mock_container.return_value.get_prompt_loader.return_value = mock_prompt_loader

                result = (
                    await real_email_flow_orchestrator._run_direct_optimization_and_email_delivery(
                        mock_update, mock_context, user_id, original_prompt
                    )
                )

        # Verify email flow completed successfully despite ALL session tracking failures
        assert result is True

        # Verify email was sent
        mock_email_service.send_optimized_prompts_email.assert_called_once()

        # Verify set_optimization_method was attempted (and failed)
        mock_session_service_failing.set_optimization_method.assert_called_once()

        # Verify add_tokens was attempted 3 times (and failed each time)
        # Note: add_message is in the same try/except as add_tokens, so when
        # add_tokens fails, add_message is not called. This is expected behavior.
        assert mock_session_service_failing.add_tokens.call_count == 3

        # Verify log_email_sent was attempted (and failed)
        # Note: complete_session is in the same try/except as log_email_sent, so when
        # log_email_sent fails, complete_session is not called. This is expected behavior.
        mock_session_service_failing.log_email_sent.assert_called_once()

        # Verify no session tracking error messages were shown to user
        for call in mock_update.message.reply_text.call_args_list:
            message = call[0][0] if call[0] else call.kwargs.get("text", "")
            assert "session" not in message.lower()
            assert "tracking" not in message.lower()


if __name__ == "__main__":
    pytest.main([__file__])
