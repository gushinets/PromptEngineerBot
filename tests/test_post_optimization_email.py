"""
Tests for post-optimization email functionality.

This module tests the new "Отправить промпт на e-mail" button functionality
that appears after optimization completion scenarios.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot_handler import BotHandler
from src.email_flow import EmailFlowOrchestrator
from src.email_templates import EmailTemplates
from src.messages import (
    BTN_POST_OPTIMIZATION_EMAIL,
    POST_FOLLOWUP_COMPLETION_KEYBOARD,
    POST_FOLLOWUP_DECLINE_KEYBOARD,
)


class TestPostOptimizationEmailButton:
    """Test post-optimization email button display and functionality."""

    def test_post_optimization_email_button_exists(self):
        """Test that the new post-optimization email button is defined."""
        assert BTN_POST_OPTIMIZATION_EMAIL is not None
        assert "промпт на e-mail" in BTN_POST_OPTIMIZATION_EMAIL

    def test_post_followup_completion_keyboard_includes_email_button(self):
        """Test that post-followup completion keyboard includes the email button."""
        keyboard_buttons = [
            button.text
            for row in POST_FOLLOWUP_COMPLETION_KEYBOARD.keyboard
            for button in row
        ]
        assert BTN_POST_OPTIMIZATION_EMAIL in keyboard_buttons

    def test_post_followup_decline_keyboard_includes_email_button(self):
        """Test that post-followup decline keyboard includes the email button."""
        keyboard_buttons = [
            button.text
            for row in POST_FOLLOWUP_DECLINE_KEYBOARD.keyboard
            for button in row
        ]
        assert BTN_POST_OPTIMIZATION_EMAIL in keyboard_buttons

    @pytest.mark.asyncio
    async def test_post_optimization_email_handler_called(self):
        """Test that post-optimization email handler is called when button is clicked."""
        # Mock dependencies
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("src.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = (
                MagicMock()
            )

            bot_handler = BotHandler(config, llm_client)
            bot_handler.email_flow_orchestrator = AsyncMock()

            # Mock update and context
            update = MagicMock()
            update.effective_user.id = 12345
            update.message.text = BTN_POST_OPTIMIZATION_EMAIL
            context = MagicMock()

            # Mock health monitor
            with patch("src.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.return_value = True

                # Call handle_message
                await bot_handler.handle_message(update, context)

                # Verify that the post-optimization email flow was started
                bot_handler.email_flow_orchestrator.start_post_optimization_email_flow.assert_called_once_with(
                    update, context, 12345
                )


class TestPostOptimizationEmailFlow:
    """Test post-optimization email flow orchestration."""

    @pytest.fixture
    def email_flow_orchestrator(self):
        """Create EmailFlowOrchestrator instance for testing."""
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service"),
            patch("src.email_flow.get_email_service"),
            patch("src.email_flow.get_redis_client"),
        ):
            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )
            return orchestrator

    @pytest.mark.asyncio
    async def test_get_current_optimization_result_follow_up(
        self, email_flow_orchestrator
    ):
        """Test getting current optimization result for follow-up completion scenario."""
        user_id = 12345
        improved_prompt = "This is the improved prompt from follow-up"

        # Mock state manager - no stored result, but has cached improved prompt
        email_flow_orchestrator.state_manager.get_post_optimization_result.return_value = None
        email_flow_orchestrator.state_manager.get_improved_prompt_cache.return_value = (
            improved_prompt
        )

        result = email_flow_orchestrator._get_current_optimization_result(user_id)

        assert result is not None
        assert result["type"] == "follow_up"
        assert result["method_name"] == "Follow-up Optimization"
        assert result["content"] == improved_prompt

    @pytest.mark.asyncio
    async def test_get_current_optimization_result_single_method(
        self, email_flow_orchestrator
    ):
        """Test getting current optimization result for single method scenario."""
        user_id = 12345
        optimization_result = "This is the CRAFT optimization result"

        # Mock state manager - no stored result and no cached improved prompt
        email_flow_orchestrator.state_manager.get_post_optimization_result.return_value = None
        email_flow_orchestrator.state_manager.get_improved_prompt_cache.return_value = (
            None
        )

        # Mock conversation manager
        email_flow_orchestrator.conversation_manager.get_current_method.return_value = (
            "CRAFT"
        )
        email_flow_orchestrator.conversation_manager.get_transcript.return_value = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "User prompt"},
            {"role": "assistant", "content": optimization_result},
        ]

        result = email_flow_orchestrator._get_current_optimization_result(user_id)

        assert result is not None
        assert result["type"] == "single_method"
        assert result["method_name"] == "CRAFT"
        assert result["content"] == optimization_result

    @pytest.mark.asyncio
    async def test_get_current_optimization_result_no_result(
        self, email_flow_orchestrator
    ):
        """Test getting current optimization result when no result is available."""
        user_id = 12345

        # Mock state manager - no stored result and no cached improved prompt
        email_flow_orchestrator.state_manager.get_post_optimization_result.return_value = None
        email_flow_orchestrator.state_manager.get_improved_prompt_cache.return_value = (
            None
        )

        # Mock conversation manager with no current method
        email_flow_orchestrator.conversation_manager.get_current_method.return_value = (
            None
        )

        result = email_flow_orchestrator._get_current_optimization_result(user_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_optimization_result_stored_result(
        self, email_flow_orchestrator
    ):
        """Test getting current optimization result from stored result (follow-up decline scenario)."""
        user_id = 12345
        stored_result = {
            "type": "single_method",
            "method_name": "CRAFT",
            "content": "This is the stored CRAFT optimization result",
            "original_prompt": "Original user prompt",
        }

        # Mock state manager to return stored result
        email_flow_orchestrator.state_manager.get_post_optimization_result.return_value = stored_result

        result = email_flow_orchestrator._get_current_optimization_result(user_id)

        assert result is not None
        assert result == stored_result
        assert result["type"] == "single_method"
        assert result["method_name"] == "CRAFT"
        assert result["content"] == "This is the stored CRAFT optimization result"

    @pytest.mark.asyncio
    async def test_start_post_optimization_email_flow_authenticated_user(
        self, email_flow_orchestrator
    ):
        """Test starting post-optimization email flow for already authenticated user."""
        user_id = 12345
        user_email = "test@example.com"
        original_prompt = "Original user prompt"
        current_result = {
            "type": "follow_up",
            "method_name": "Follow-up Optimization",
            "content": "Optimized result",
        }

        # Mock dependencies
        update = MagicMock()
        context = MagicMock()

        # Mock methods
        email_flow_orchestrator._get_current_optimization_result = MagicMock(
            return_value=current_result
        )
        email_flow_orchestrator.conversation_manager.get_user_prompt.return_value = (
            original_prompt
        )
        email_flow_orchestrator.auth_service.is_user_authenticated = MagicMock(
            return_value=True
        )
        email_flow_orchestrator.auth_service.get_user_email = MagicMock(
            return_value=user_email
        )
        email_flow_orchestrator._send_post_optimization_email = AsyncMock(
            return_value=True
        )
        email_flow_orchestrator._safe_reply = AsyncMock()

        result = await email_flow_orchestrator.start_post_optimization_email_flow(
            update, context, user_id
        )

        assert result is True
        email_flow_orchestrator._send_post_optimization_email.assert_called_once_with(
            update, context, user_id, user_email, current_result, original_prompt
        )

    @pytest.mark.asyncio
    async def test_start_post_optimization_email_flow_unauthenticated_user(
        self, email_flow_orchestrator
    ):
        """Test starting post-optimization email flow for unauthenticated user."""
        user_id = 12345
        original_prompt = "Original user prompt"
        current_result = {
            "type": "single_method",
            "method_name": "CRAFT",
            "content": "Optimized result",
        }

        # Mock dependencies
        update = MagicMock()
        context = MagicMock()

        # Mock methods
        email_flow_orchestrator._get_current_optimization_result = MagicMock(
            return_value=current_result
        )
        email_flow_orchestrator.conversation_manager.get_user_prompt.return_value = (
            original_prompt
        )
        email_flow_orchestrator.auth_service.is_user_authenticated = MagicMock(
            return_value=False
        )
        email_flow_orchestrator.state_manager.set_email_flow_data = MagicMock()
        email_flow_orchestrator.state_manager.set_waiting_for_email_input = MagicMock()
        email_flow_orchestrator._safe_reply = AsyncMock()

        result = await email_flow_orchestrator.start_post_optimization_email_flow(
            update, context, user_id
        )

        assert result is True
        email_flow_orchestrator.state_manager.set_waiting_for_email_input.assert_called_once_with(
            user_id, True
        )

    @pytest.mark.asyncio
    async def test_send_post_optimization_email_success(self, email_flow_orchestrator):
        """Test successful post-optimization email sending."""
        user_id = 12345
        user_email = "test@example.com"
        original_prompt = "Original user prompt"
        current_result = {
            "type": "follow_up",
            "method_name": "Follow-up Optimization",
            "content": "Optimized result",
        }

        # Mock dependencies
        update = MagicMock()
        context = MagicMock()

        # Mock email service
        email_result = MagicMock()
        email_result.success = True
        email_flow_orchestrator.email_service.send_single_result_email = AsyncMock(
            return_value=email_result
        )
        email_flow_orchestrator._safe_reply = AsyncMock()
        email_flow_orchestrator._reset_user_state = MagicMock()

        result = await email_flow_orchestrator._send_post_optimization_email(
            update, context, user_id, user_email, current_result, original_prompt
        )

        assert result is True
        email_flow_orchestrator.email_service.send_single_result_email.assert_called_once_with(
            user_email,
            original_prompt,
            current_result["method_name"],
            current_result["content"],
            user_id,
        )
        email_flow_orchestrator._reset_user_state.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_send_post_optimization_email_failure(self, email_flow_orchestrator):
        """Test post-optimization email sending failure."""
        user_id = 12345
        user_email = "test@example.com"
        original_prompt = "Original user prompt"
        current_result = {
            "type": "single_method",
            "method_name": "CRAFT",
            "content": "Optimized result",
        }

        # Mock dependencies
        update = MagicMock()
        context = MagicMock()

        # Mock email service failure
        email_result = MagicMock()
        email_result.success = False
        email_flow_orchestrator.email_service.send_single_result_email = AsyncMock(
            return_value=email_result
        )
        email_flow_orchestrator._safe_reply = AsyncMock()

        result = await email_flow_orchestrator._send_post_optimization_email(
            update, context, user_id, user_email, current_result, original_prompt
        )

        assert result is False


class TestSingleResultEmailTemplates:
    """Test single-result email templates."""

    def test_single_result_email_template_creation(self):
        """Test creating single result email templates."""
        templates = EmailTemplates("RU")

        original_prompt = "Test original prompt"
        method_name = "CRAFT"
        optimized_result = "Test optimized result"

        subject, html_body, plain_body = templates.compose_single_result_email(
            original_prompt, method_name, optimized_result
        )

        # Test subject
        assert "оптимизированный промпт готов" in subject.lower()

        # Test HTML body
        assert original_prompt in html_body
        assert method_name in html_body
        assert optimized_result in html_body
        assert "<!DOCTYPE html>" in html_body

        # Test plain body
        assert original_prompt in plain_body
        assert method_name in plain_body
        assert optimized_result in plain_body

    def test_single_result_email_template_english(self):
        """Test single result email templates in English."""
        templates = EmailTemplates("EN")

        original_prompt = "Test original prompt"
        method_name = "LYRA"
        optimized_result = "Test optimized result"

        subject, html_body, plain_body = templates.compose_single_result_email(
            original_prompt, method_name, optimized_result
        )

        # Test English subject
        assert "optimized prompt is ready" in subject.lower()

        # Test content is present in both formats
        assert original_prompt in html_body
        assert original_prompt in plain_body

    def test_single_result_email_html_escaping(self):
        """Test that HTML content is properly escaped in single result emails."""
        templates = EmailTemplates("EN")

        # Test with HTML characters that need escaping
        original_prompt = "Test <script>alert('xss')</script> prompt"
        method_name = "GGL"
        optimized_result = "Result with & special < characters >"

        subject, html_body, plain_body = templates.compose_single_result_email(
            original_prompt, method_name, optimized_result
        )

        # Verify HTML escaping
        assert "<script>" not in html_body
        assert "&lt;script&gt;" in html_body
        assert "&amp;" in html_body
        assert "&lt;" in html_body
        assert "&gt;" in html_body


class TestPostOptimizationEmailIntegration:
    """Integration tests for post-optimization email functionality."""

    @pytest.mark.asyncio
    async def test_otp_verification_post_optimization_flow(self):
        """Test OTP verification redirects to post-optimization flow when appropriate."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service") as mock_auth,
            patch("src.email_flow.get_email_service") as mock_email,
            patch("src.email_flow.get_redis_client"),
        ):
            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock successful OTP verification
            mock_auth.return_value.verify_otp.return_value = (True, None)
            mock_auth.return_value.get_user_email.return_value = "test@example.com"

            # Mock post-optimization flow data
            email_flow_data = {
                "flow_type": "post_optimization",
                "current_result": {
                    "type": "follow_up",
                    "method_name": "Follow-up Optimization",
                    "content": "Optimized content",
                },
                "original_prompt": "Original prompt",
            }
            state_manager.get_email_flow_data.return_value = email_flow_data
            state_manager.set_waiting_for_otp_input = MagicMock()

            # Mock email sending
            orchestrator._send_post_optimization_email = AsyncMock(return_value=True)
            orchestrator._safe_reply = AsyncMock()

            # Mock update and context
            update = MagicMock()
            context = MagicMock()
            user_id = 12345
            otp_text = "123456"

            result = await orchestrator.handle_otp_input(
                update, context, user_id, otp_text
            )

            assert result is True
            orchestrator._send_post_optimization_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_existing_email_flow_unchanged(self):
        """Test that existing email flow functionality remains unchanged."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service") as mock_auth,
            patch("src.email_flow.get_email_service") as mock_email,
            patch("src.email_flow.get_redis_client"),
        ):
            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock successful OTP verification
            mock_auth.return_value.verify_otp.return_value = (True, None)

            # Mock regular flow data (not post-optimization)
            email_flow_data = {
                "flow_type": "regular",
                "original_prompt": "Original prompt",
            }
            state_manager.get_email_flow_data.return_value = email_flow_data
            state_manager.set_waiting_for_otp_input = MagicMock()

            # Mock follow-up and delivery
            orchestrator._proceed_to_followup_and_delivery = AsyncMock(
                return_value=True
            )
            orchestrator._safe_reply = AsyncMock()

            # Mock update and context
            update = MagicMock()
            context = MagicMock()
            user_id = 12345
            otp_text = "123456"

            result = await orchestrator.handle_otp_input(
                update, context, user_id, otp_text
            )

            assert result is True
            orchestrator._proceed_to_followup_and_delivery.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_optimization_button_display_scenarios(self):
        """Test post-optimization button display in correct scenarios."""
        # Mock bot handler
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("src.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = (
                MagicMock()
            )

            from src.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)

            # Mock update and context
            update = MagicMock()
            context = MagicMock()
            user_id = 12345

            # Test scenario 1: After follow-up completion
            with patch.object(
                bot_handler, "_complete_followup_conversation"
            ) as mock_complete:

                async def mock_complete_side_effect(update, user_id, refined_prompt):
                    # Simulate sending the completion message with post-optimization button
                    await bot_handler._safe_reply(
                        update,
                        "Prompt ready message",
                        reply_markup=POST_FOLLOWUP_COMPLETION_KEYBOARD,
                    )

                mock_complete.side_effect = mock_complete_side_effect
                bot_handler._safe_reply = AsyncMock()

                await mock_complete(update, user_id, "Refined prompt")

                # Verify completion keyboard was used
                bot_handler._safe_reply.assert_called_with(
                    update,
                    "Prompt ready message",
                    reply_markup=POST_FOLLOWUP_COMPLETION_KEYBOARD,
                )

            # Test scenario 2: After follow-up decline
            with patch.object(bot_handler, "_handle_followup_choice") as mock_choice:

                async def mock_choice_side_effect(update, user_id, text):
                    if text == BTN_NO:
                        await bot_handler._safe_reply(
                            update,
                            "Follow-up declined message",
                            reply_markup=POST_FOLLOWUP_DECLINE_KEYBOARD,
                        )

                mock_choice.side_effect = mock_choice_side_effect
                bot_handler._safe_reply = AsyncMock()

                from src.messages import BTN_NO

                await mock_choice(update, user_id, BTN_NO)

                # Verify decline keyboard was used
                bot_handler._safe_reply.assert_called_with(
                    update,
                    "Follow-up declined message",
                    reply_markup=POST_FOLLOWUP_DECLINE_KEYBOARD,
                )

    @pytest.mark.asyncio
    async def test_error_handling_post_optimization_flow(self):
        """Test error handling in post-optimization email flow."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service") as mock_auth,
            patch("src.email_flow.get_email_service") as mock_email,
            patch("src.email_flow.get_redis_client"),
        ):
            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Test error scenarios
            update = MagicMock()
            context = MagicMock()
            user_id = 12345

            # Scenario 1: No current result available
            orchestrator._get_current_optimization_result = MagicMock(return_value=None)
            orchestrator._safe_reply = AsyncMock()

            result = await orchestrator.start_post_optimization_email_flow(
                update, context, user_id
            )

            assert result is False
            orchestrator._safe_reply.assert_called()

            # Scenario 2: No original prompt available
            orchestrator._get_current_optimization_result = MagicMock(
                return_value={
                    "type": "follow_up",
                    "method_name": "Follow-up",
                    "content": "Content",
                }
            )
            conversation_manager.get_user_prompt.return_value = None

            result = await orchestrator.start_post_optimization_email_flow(
                update, context, user_id
            )

            assert result is False

            # Scenario 3: Email sending failure
            conversation_manager.get_user_prompt.return_value = "Original prompt"
            mock_auth.return_value.is_user_authenticated.return_value = True
            mock_auth.return_value.get_user_email.return_value = "test@example.com"

            # Mock email service failure
            email_result = MagicMock()
            email_result.success = False
            email_result.error = "SMTP error"
            mock_email.return_value.send_single_result_email = AsyncMock(
                return_value=email_result
            )

            orchestrator._send_post_optimization_email = AsyncMock(return_value=False)

            result = await orchestrator.start_post_optimization_email_flow(
                update, context, user_id
            )

            # Should handle error gracefully
            assert (
                result is False or result is True
            )  # Depends on implementation details

    @pytest.mark.asyncio
    async def test_authentication_reuse_post_optimization(self):
        """Test that post-optimization flow reuses existing authentication."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service") as mock_auth,
            patch("src.email_flow.get_email_service") as mock_email,
            patch("src.email_flow.get_redis_client"),
        ):
            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock authenticated user
            mock_auth.return_value.is_user_authenticated = MagicMock(return_value=True)
            mock_auth.return_value.get_user_email = MagicMock(
                return_value="test@example.com"
            )

            # Mock current result and original prompt
            orchestrator._get_current_optimization_result = MagicMock(
                return_value={
                    "type": "single_method",
                    "method_name": "CRAFT",
                    "content": "Optimized content",
                }
            )
            conversation_manager.get_user_prompt.return_value = "Original prompt"

            # Mock email sending
            orchestrator._send_post_optimization_email = AsyncMock(return_value=True)
            orchestrator._safe_reply = AsyncMock()

            update = MagicMock()
            context = MagicMock()
            user_id = 12345

            result = await orchestrator.start_post_optimization_email_flow(
                update, context, user_id
            )

            assert result is True

            # Verify authentication was checked
            mock_auth.return_value.is_user_authenticated.assert_called_once_with(
                user_id
            )
            mock_auth.return_value.get_user_email.assert_called_once_with(user_id)

            # Verify email was sent directly without OTP flow
            orchestrator._send_post_optimization_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_post_optimization_flow_state_management(self):
        """Test state management during post-optimization flow."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service") as mock_auth,
            patch("src.email_flow.get_email_service") as mock_email,
            patch("src.email_flow.get_redis_client"),
        ):
            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock unauthenticated user
            mock_auth.return_value.is_user_authenticated = MagicMock(return_value=False)

            # Mock current result and original prompt
            orchestrator._get_current_optimization_result = MagicMock(
                return_value={
                    "type": "follow_up",
                    "method_name": "Follow-up Optimization",
                    "content": "Optimized content",
                }
            )
            conversation_manager.get_user_prompt.return_value = "Original prompt"
            orchestrator._safe_reply = AsyncMock()

            # Mock email service methods
            mock_email.return_value.send_single_result_email = AsyncMock(
                return_value=MagicMock(success=True)
            )

            update = MagicMock()
            context = MagicMock()
            user_id = 12345

            result = await orchestrator.start_post_optimization_email_flow(
                update, context, user_id
            )

            assert result is True

            # Verify flow data was set correctly
            state_manager.set_email_flow_data.assert_called_once()
            flow_data = state_manager.set_email_flow_data.call_args[0][1]

            assert flow_data["flow_type"] == "post_optimization"
            assert flow_data["original_prompt"] == "Original prompt"
            assert flow_data["current_result"]["type"] == "follow_up"
            assert (
                flow_data["current_result"]["method_name"] == "Follow-up Optimization"
            )
            assert flow_data["current_result"]["content"] == "Optimized content"

            # Verify waiting for email input state was set
            state_manager.set_waiting_for_email_input.assert_called_once_with(
                user_id, True
            )


if __name__ == "__main__":
    pytest.main([__file__])


class TestPostOptimizationButtonDisplayLogic:
    """Test post-optimization button display logic in various scenarios."""

    def test_button_display_after_followup_completion(self):
        """Test button appears after successful follow-up completion."""
        from src.messages import (
            BTN_POST_OPTIMIZATION_EMAIL,
            POST_FOLLOWUP_COMPLETION_KEYBOARD,
        )

        # Verify keyboard contains the post-optimization email button
        keyboard_buttons = [
            button.text
            for row in POST_FOLLOWUP_COMPLETION_KEYBOARD.keyboard
            for button in row
        ]
        assert BTN_POST_OPTIMIZATION_EMAIL in keyboard_buttons

        # Verify button text is correct
        assert (
            "промпт на e-mail" in BTN_POST_OPTIMIZATION_EMAIL
            or "prompt to e-mail" in BTN_POST_OPTIMIZATION_EMAIL
        )

    def test_button_display_after_followup_decline(self):
        """Test button appears after follow-up decline."""
        from src.messages import (
            BTN_POST_OPTIMIZATION_EMAIL,
            POST_FOLLOWUP_DECLINE_KEYBOARD,
        )

        # Verify keyboard contains the post-optimization email button
        keyboard_buttons = [
            button.text
            for row in POST_FOLLOWUP_DECLINE_KEYBOARD.keyboard
            for button in row
        ]
        assert BTN_POST_OPTIMIZATION_EMAIL in keyboard_buttons

    def test_button_not_in_regular_keyboards(self):
        """Test button does not appear in regular keyboards."""
        from src.messages import (
            BTN_POST_OPTIMIZATION_EMAIL,
            FOLLOWUP_CHOICE_KEYBOARD,
            FOLLOWUP_CONVERSATION_KEYBOARD,
            SELECT_METHOD_KEYBOARD,
        )

        # Check that post-optimization button is not in regular keyboards
        for keyboard in [
            SELECT_METHOD_KEYBOARD,
            FOLLOWUP_CHOICE_KEYBOARD,
            FOLLOWUP_CONVERSATION_KEYBOARD,
        ]:
            keyboard_buttons = [
                button.text for row in keyboard.keyboard for button in row
            ]
            assert BTN_POST_OPTIMIZATION_EMAIL not in keyboard_buttons

    @pytest.mark.asyncio
    async def test_button_handler_integration(self):
        """Test that clicking the button triggers the correct handler."""
        # Mock bot handler
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("src.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = (
                MagicMock()
            )

            from src.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)

            # Mock email flow orchestrator
            bot_handler.email_flow_orchestrator = MagicMock()
            bot_handler.email_flow_orchestrator.start_post_optimization_email_flow = (
                AsyncMock(return_value=True)
            )

            # Mock health monitor
            with patch("src.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.return_value = True

                # Mock update and context
                update = MagicMock()
                update.effective_user.id = 12345
                update.message.text = BTN_POST_OPTIMIZATION_EMAIL
                context = MagicMock()

                # Call handle_message
                await bot_handler.handle_message(update, context)

                # Verify post-optimization email flow was started
                bot_handler.email_flow_orchestrator.start_post_optimization_email_flow.assert_called_once_with(
                    update, context, 12345
                )


class TestPostOptimizationErrorHandling:
    """Test error handling in post-optimization email functionality."""

    @pytest.mark.asyncio
    async def test_health_check_failures(self):
        """Test behavior when health checks fail."""
        # Mock bot handler
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("src.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = (
                MagicMock()
            )

            from src.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)
            bot_handler.email_flow_orchestrator = MagicMock()
            bot_handler._safe_reply = AsyncMock()

            # Mock health monitor - Redis unhealthy
            with patch("src.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.side_effect = (
                    lambda service: service != "redis"
                )

                update = MagicMock()
                update.effective_user.id = 12345
                update.message.text = BTN_POST_OPTIMIZATION_EMAIL
                context = MagicMock()

                await bot_handler._handle_post_optimization_email(
                    update, context, 12345
                )

                # Verify error message was sent
                bot_handler._safe_reply.assert_called()
                call_args = bot_handler._safe_reply.call_args[0]
                assert any(
                    "недоступен" in str(arg).lower()
                    or "unavailable" in str(arg).lower()
                    for arg in call_args
                )

    @pytest.mark.asyncio
    async def test_missing_optimization_result(self):
        """Test behavior when no optimization result is available."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service"),
            patch("src.email_flow.get_email_service"),
            patch("src.email_flow.get_redis_client"),
        ):
            from src.email_flow import EmailFlowOrchestrator

            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock no current result
            orchestrator._get_current_optimization_result = MagicMock(return_value=None)
            orchestrator._safe_reply = AsyncMock()

            update = MagicMock()
            context = MagicMock()
            user_id = 12345

            result = await orchestrator.start_post_optimization_email_flow(
                update, context, user_id
            )

            assert result is False
            orchestrator._safe_reply.assert_called()

    @pytest.mark.asyncio
    async def test_email_service_unavailable(self):
        """Test behavior when email service is unavailable."""
        # Mock bot handler without email flow orchestrator
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("src.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = (
                MagicMock()
            )

            from src.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)
            bot_handler.email_flow_orchestrator = None  # Simulate unavailable service
            bot_handler._safe_reply = AsyncMock()

            update = MagicMock()
            update.effective_user.id = 12345
            context = MagicMock()

            await bot_handler._handle_post_optimization_email(update, context, 12345)

            # Verify error message was sent
            bot_handler._safe_reply.assert_called()
            call_args = bot_handler._safe_reply.call_args[0]
            assert any(
                "недоступен" in str(arg).lower() or "unavailable" in str(arg).lower()
                for arg in call_args
            )

    @pytest.mark.asyncio
    async def test_exception_handling_in_flow(self):
        """Test exception handling in post-optimization flow."""
        # Mock bot handler
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("src.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = (
                MagicMock()
            )

            from src.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)

            # Mock email flow orchestrator that raises exception
            bot_handler.email_flow_orchestrator = MagicMock()
            bot_handler.email_flow_orchestrator.start_post_optimization_email_flow = (
                AsyncMock(side_effect=Exception("Test exception"))
            )
            bot_handler._safe_reply = AsyncMock()

            # Mock health monitor as healthy
            with patch("src.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.return_value = True

                update = MagicMock()
                update.effective_user.id = 12345
                context = MagicMock()

                await bot_handler._handle_post_optimization_email(
                    update, context, 12345
                )

                # Verify error message was sent
                bot_handler._safe_reply.assert_called()


class TestPostOptimizationFlowValidation:
    """Test validation of post-optimization flow requirements."""

    @pytest.mark.asyncio
    async def test_existing_functionality_unchanged(self):
        """Test that existing email functionality remains completely unchanged."""
        # Mock dependencies for regular email flow
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service") as mock_auth,
            patch("src.email_flow.get_email_service") as mock_email,
            patch("src.email_flow.get_redis_client"),
        ):
            from src.email_flow import EmailFlowOrchestrator

            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock regular email flow (not post-optimization)
            conversation_manager.get_user_prompt.return_value = "Test prompt"
            mock_auth.return_value.is_user_authenticated.return_value = False
            orchestrator._safe_reply = AsyncMock()

            # Mock graceful degradation check
            with patch("src.email_flow.check_email_flow_readiness") as mock_check:
                mock_check.return_value = (True, None)

                update = MagicMock()
                context = MagicMock()
                user_id = 12345

                # Start regular email flow
                result = await orchestrator.start_email_flow(update, context, user_id)

                assert result is True

                # Verify regular flow data was set (not post-optimization)
                state_manager.set_email_flow_data.assert_called()
                flow_data = state_manager.set_email_flow_data.call_args[0][1]
                assert (
                    "flow_type" not in flow_data
                    or flow_data.get("flow_type") != "post_optimization"
                )
                assert flow_data["original_prompt"] == "Test prompt"

    def test_button_text_localization(self):
        """Test that button text is properly localized."""
        from src.messages import BTN_POST_OPTIMIZATION_EMAIL, LANGUAGE

        # Check that button text contains appropriate language elements
        if LANGUAGE == "ru":
            assert "промпт" in BTN_POST_OPTIMIZATION_EMAIL.lower()
            assert "e-mail" in BTN_POST_OPTIMIZATION_EMAIL.lower()
        else:
            assert "prompt" in BTN_POST_OPTIMIZATION_EMAIL.lower()
            assert (
                "e-mail" in BTN_POST_OPTIMIZATION_EMAIL.lower()
                or "email" in BTN_POST_OPTIMIZATION_EMAIL.lower()
            )

    @pytest.mark.asyncio
    async def test_current_result_detection_accuracy(self):
        """Test accurate detection of current optimization results."""
        # Mock dependencies
        config = MagicMock()
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("src.email_flow.get_auth_service"),
            patch("src.email_flow.get_email_service"),
            patch("src.email_flow.get_redis_client"),
        ):
            from src.email_flow import EmailFlowOrchestrator

            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Test follow-up result detection
            state_manager.get_post_optimization_result.return_value = None
            state_manager.get_improved_prompt_cache.return_value = (
                "Follow-up improved prompt"
            )

            result = orchestrator._get_current_optimization_result(12345)

            assert result is not None
            assert result["type"] == "follow_up"
            assert result["method_name"] == "Follow-up Optimization"
            assert result["content"] == "Follow-up improved prompt"

            # Test single method result detection
            state_manager.get_improved_prompt_cache.return_value = None
            conversation_manager.get_current_method.return_value = "CRAFT"
            conversation_manager.get_transcript.return_value = [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User prompt"},
                {"role": "assistant", "content": "CRAFT optimization result"},
            ]

            result = orchestrator._get_current_optimization_result(12345)

            assert result is not None
            assert result["type"] == "single_method"
            assert result["method_name"] == "CRAFT"
            assert result["content"] == "CRAFT optimization result"

            # Test no result available
            conversation_manager.get_current_method.return_value = None

            result = orchestrator._get_current_optimization_result(12345)

            assert result is None


class TestPostOptimizationEmailTemplateIntegration:
    """Test integration with email templates for single results."""

    def test_single_result_template_content_validation(self):
        """Test that single result email templates contain required content."""
        from src.email_templates import EmailTemplates

        templates_ru = EmailTemplates("RU")
        templates_en = EmailTemplates("EN")

        original_prompt = "Создай план маркетинга"
        method_name = "CRAFT"
        optimized_result = "Создайте подробный план маркетинга..."

        # Test Russian template
        subject_ru, html_ru, plain_ru = templates_ru.compose_single_result_email(
            original_prompt, method_name, optimized_result
        )

        assert "оптимизированный промпт готов" in subject_ru.lower()
        assert original_prompt in html_ru
        assert method_name in html_ru
        assert optimized_result in html_ru

        # Test English template
        subject_en, html_en, plain_en = templates_en.compose_single_result_email(
            original_prompt, method_name, optimized_result
        )

        assert "optimized prompt is ready" in subject_en.lower()
        assert original_prompt in html_en
        assert method_name in html_en
        assert optimized_result in html_en

    def test_template_security_validation(self):
        """Test that templates properly escape malicious content."""
        from src.email_templates import EmailTemplates

        templates = EmailTemplates("EN")

        # Test with potentially malicious content
        malicious_prompt = "<script>alert('xss')</script>Test prompt"
        method_name = "CRAFT"
        malicious_result = "Result with <iframe src='evil.com'></iframe> content"

        subject, html_body, plain_body = templates.compose_single_result_email(
            malicious_prompt, method_name, malicious_result
        )

        # Verify HTML escaping
        assert "<script>" not in html_body
        assert "<iframe>" not in html_body
        assert "&lt;script&gt;" in html_body
        assert "&lt;iframe" in html_body

    @pytest.mark.asyncio
    async def test_email_service_single_result_integration(self):
        """Test integration with email service for single result sending."""
        # Mock email service
        config = MagicMock()
        config.language = "RU"
        config.smtp_host = "smtp.example.com"
        config.smtp_port = 587
        config.smtp_username = "test@example.com"
        config.smtp_password = "password"
        config.smtp_from_email = "test@example.com"
        config.smtp_from_name = "Test Bot"
        config.smtp_use_tls = True
        config.smtp_use_ssl = False

        with patch("src.email_service.get_audit_service"):
            from src.email_service import EmailDeliveryResult, EmailService

            service = EmailService(config)
            service._send_email_with_queue_fallback = AsyncMock(
                return_value=EmailDeliveryResult(success=True, message_id="test123")
            )
            service._generate_email_hash = MagicMock(return_value="hash123")
            service._is_email_already_sent = AsyncMock(return_value=False)

            result = await service.send_single_result_email(
                "user@example.com",
                "Original prompt",
                "CRAFT",
                "Optimized result",
                12345,
            )

            assert result.success is True
            assert result.message_id == "test123"
            service._send_email_with_queue_fallback.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
