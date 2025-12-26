"""
Integration tests for post-optimization email functionality.

This module tests the complete integration of the new post-optimization email
feature with the existing system, ensuring no regressions and proper functionality.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_bot.utils.messages import (
    BTN_EMAIL_DELIVERY,
    BTN_NO,
    BTN_POST_OPTIMIZATION_EMAIL,
    BTN_RESET,
    BTN_YES,
    POST_FOLLOWUP_COMPLETION_KEYBOARD,
    POST_FOLLOWUP_DECLINE_KEYBOARD,
)


class TestPostOptimizationSystemIntegration:
    """Test complete system integration for post-optimization email functionality."""

    @pytest.mark.asyncio
    async def test_complete_followup_to_email_flow(self):
        """Test complete flow from follow-up completion to email delivery."""
        # Mock bot handler and dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()

        with patch("telegram_bot.core.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = MagicMock()

            from telegram_bot.core.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)

            # Mock email flow orchestrator
            email_flow = MagicMock()
            email_flow.start_post_optimization_email_flow = AsyncMock(return_value=True)
            email_flow.handle_email_input = AsyncMock(return_value=True)
            email_flow.handle_otp_input = AsyncMock(return_value=True)
            bot_handler.email_flow_orchestrator = email_flow

            # Mock health monitor
            with patch("telegram_bot.utils.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.return_value = True

                # Simulate user completing follow-up conversation
                user_id = 12345
                update = MagicMock()
                update.effective_user.id = user_id
                context = MagicMock()

                # Step 1: User completes follow-up (this would show the post-optimization button)
                bot_handler.state_manager.set_improved_prompt_cache(user_id, "Refined prompt")
                bot_handler._safe_reply = AsyncMock()

                # Simulate completion message with keyboard
                await bot_handler._safe_reply(
                    update,
                    "Prompt ready message",
                    reply_markup=POST_FOLLOWUP_COMPLETION_KEYBOARD,
                )

                # Step 2: User clicks post-optimization email button
                update.message.text = BTN_POST_OPTIMIZATION_EMAIL
                await bot_handler.handle_message(update, context)

                # Verify post-optimization flow was started
                email_flow.start_post_optimization_email_flow.assert_called_once_with(
                    update, context, user_id
                )

    @pytest.mark.asyncio
    async def test_complete_decline_to_email_flow(self):
        """Test complete flow from follow-up decline to email delivery."""
        # Mock bot handler and dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()

        with patch("telegram_bot.core.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = MagicMock()

            from telegram_bot.core.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)

            # Mock email flow orchestrator
            email_flow = MagicMock()
            email_flow.start_post_optimization_email_flow = AsyncMock(return_value=True)
            bot_handler.email_flow_orchestrator = email_flow

            # Mock health monitor
            with patch("telegram_bot.utils.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.return_value = True

                user_id = 12345
                update = MagicMock()
                update.effective_user.id = user_id
                context = MagicMock()

                # Step 1: User declines follow-up (this would show the post-optimization button)
                bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
                bot_handler.state_manager.set_improved_prompt_cache(user_id, "Improved prompt")
                bot_handler._safe_reply = AsyncMock()

                # Simulate decline handling
                update.message.text = BTN_NO
                await bot_handler._handle_followup_choice(update, user_id, BTN_NO)

                # Verify decline keyboard was used (would contain post-optimization button)
                bot_handler._safe_reply.assert_called()

                # Step 2: User clicks post-optimization email button
                update.message.text = BTN_POST_OPTIMIZATION_EMAIL
                await bot_handler.handle_message(update, context)

                # Verify post-optimization flow was started
                email_flow.start_post_optimization_email_flow.assert_called_once_with(
                    update, context, user_id
                )

    @pytest.mark.asyncio
    async def test_existing_email_flow_unaffected(self):
        """Test that existing 'Send 3 prompts to email' functionality is completely unaffected."""
        # Mock bot handler and dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()

        with patch("telegram_bot.core.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = MagicMock()

            from telegram_bot.core.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)

            # Mock email flow orchestrator
            email_flow = MagicMock()
            email_flow.start_email_flow = AsyncMock(return_value=True)
            bot_handler.email_flow_orchestrator = email_flow

            # Mock health monitor
            with patch("telegram_bot.utils.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.return_value = True

                user_id = 12345
                update = MagicMock()
                update.effective_user.id = user_id
                context = MagicMock()

                # Set up method selection state
                bot_handler.state_manager.set_waiting_for_prompt(user_id, False)
                bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
                bot_handler.conversation_manager.set_waiting_for_method(user_id, True)

                # User clicks existing email delivery button
                update.message.text = BTN_EMAIL_DELIVERY

                # Mock the method selection handler directly
                await bot_handler._handle_method_selection(
                    update, context, user_id, BTN_EMAIL_DELIVERY
                )

                # Verify existing email flow was started (not post-optimization flow)
                email_flow.start_email_flow.assert_called_once_with(update, context, user_id)

                # Verify post-optimization flow was NOT called
                assert (
                    not hasattr(email_flow, "start_post_optimization_email_flow")
                    or not email_flow.start_post_optimization_email_flow.called
                )

    @pytest.mark.asyncio
    async def test_button_isolation_between_flows(self):
        """Test that post-optimization button only appears in correct scenarios."""
        from telegram_bot.utils.messages import (
            FOLLOWUP_CHOICE_KEYBOARD,
            SELECT_METHOD_KEYBOARD,
        )

        # Verify post-optimization button is NOT in regular keyboards
        regular_keyboards = [SELECT_METHOD_KEYBOARD, FOLLOWUP_CHOICE_KEYBOARD]

        for keyboard in regular_keyboards:
            keyboard_buttons = [button.text for row in keyboard.keyboard for button in row]
            assert BTN_POST_OPTIMIZATION_EMAIL not in keyboard_buttons, (
                f"Post-optimization button found in regular keyboard: {keyboard}"
            )

        # Verify post-optimization button IS in post-scenario keyboards
        post_keyboards = [
            POST_FOLLOWUP_COMPLETION_KEYBOARD,
            POST_FOLLOWUP_DECLINE_KEYBOARD,
        ]

        for keyboard in post_keyboards:
            keyboard_buttons = [button.text for row in keyboard.keyboard for button in row]
            assert BTN_POST_OPTIMIZATION_EMAIL in keyboard_buttons, (
                f"Post-optimization button missing from post-scenario keyboard: {keyboard}"
            )

    @pytest.mark.asyncio
    async def test_state_management_isolation(self):
        """Test that post-optimization flow state is properly isolated."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("telegram_bot.flows.email_flow.get_auth_service") as mock_auth,
            patch("telegram_bot.flows.email_flow.get_email_service") as mock_email,
            patch("telegram_bot.flows.email_flow.get_redis_client"),
        ):
            from telegram_bot.flows.email_flow import EmailFlowOrchestrator

            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock current result and original prompt
            orchestrator._get_current_optimization_result = MagicMock(
                return_value={
                    "type": "follow_up",
                    "method_name": "Follow-up Optimization",
                    "content": "Optimized content",
                }
            )
            conversation_manager.get_user_prompt.return_value = "Original prompt"
            mock_auth.return_value.is_user_authenticated = AsyncMock(return_value=False)
            orchestrator._safe_reply = AsyncMock()

            update = MagicMock()
            context = MagicMock()
            user_id = 12345

            # Start post-optimization flow
            await orchestrator.start_post_optimization_email_flow(update, context, user_id)

            # Verify flow data contains post-optimization markers
            state_manager.set_email_flow_data.assert_called_once()
            flow_data = state_manager.set_email_flow_data.call_args[0][1]

            assert flow_data["flow_type"] == "post_optimization"
            assert "current_result" in flow_data
            assert "result_type" in flow_data
            assert flow_data["result_type"] == "follow_up"

    @pytest.mark.asyncio
    async def test_error_recovery_and_fallback(self):
        """Test error recovery and fallback mechanisms."""
        # Mock bot handler
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("telegram_bot.core.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = MagicMock()

            from telegram_bot.core.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)
            bot_handler._safe_reply = AsyncMock()

            user_id = 12345
            update = MagicMock()
            update.effective_user.id = user_id
            context = MagicMock()

            # Test 1: Email service unavailable
            bot_handler.email_flow_orchestrator = None
            update.message.text = BTN_POST_OPTIMIZATION_EMAIL

            await bot_handler.handle_message(update, context)

            # Verify error message was sent
            bot_handler._safe_reply.assert_called()

            # Test 2: Health check failure
            bot_handler.email_flow_orchestrator = MagicMock()

            with patch("telegram_bot.utils.health_checks.get_health_monitor") as mock_health:
                mock_health.return_value.is_service_healthy.return_value = False

                await bot_handler._handle_post_optimization_email(update, context, user_id)

                # Verify error handling
                bot_handler._safe_reply.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_user_isolation(self):
        """Test that multiple users can use post-optimization flow simultaneously."""
        # Mock dependencies
        config = MagicMock()
        config.language = "RU"
        llm_client = AsyncMock()
        conversation_manager = MagicMock()
        state_manager = MagicMock()

        with (
            patch("telegram_bot.flows.email_flow.get_auth_service") as mock_auth,
            patch("telegram_bot.flows.email_flow.get_email_service") as mock_email,
            patch("telegram_bot.flows.email_flow.get_redis_client"),
        ):
            from telegram_bot.flows.email_flow import EmailFlowOrchestrator

            orchestrator = EmailFlowOrchestrator(
                config, llm_client, conversation_manager, state_manager
            )

            # Mock different results for different users
            def mock_get_result(user_id):
                if user_id == 12345:
                    return {
                        "type": "follow_up",
                        "method_name": "Follow-up Optimization",
                        "content": "User 1 content",
                    }
                if user_id == 67890:
                    return {
                        "type": "single_method",
                        "method_name": "CRAFT",
                        "content": "User 2 content",
                    }
                return None

            orchestrator._get_current_optimization_result = mock_get_result

            def mock_get_prompt(user_id):
                return f"Original prompt for user {user_id}"

            conversation_manager.get_user_prompt = mock_get_prompt
            mock_auth.return_value.is_user_authenticated = AsyncMock(return_value=False)
            orchestrator._safe_reply = AsyncMock()

            # Start flows for both users
            update1 = MagicMock()
            update2 = MagicMock()
            context = MagicMock()

            await orchestrator.start_post_optimization_email_flow(update1, context, 12345)
            await orchestrator.start_post_optimization_email_flow(update2, context, 67890)

            # Verify both flows were started with correct data
            assert state_manager.set_email_flow_data.call_count == 2

            # Check that each user got their own data
            calls = state_manager.set_email_flow_data.call_args_list
            user1_data = calls[0][0][1]
            user2_data = calls[1][0][1]

            assert user1_data["current_result"]["type"] == "follow_up"
            assert user2_data["current_result"]["type"] == "single_method"
            assert user1_data["current_result"]["content"] == "User 1 content"
            assert user2_data["current_result"]["content"] == "User 2 content"


class TestPostOptimizationEmailTemplateValidation:
    """Test email template functionality for post-optimization scenarios."""

    def test_single_result_template_completeness(self):
        """Test that single result templates contain all required elements."""
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates("RU")

        original_prompt = "Создай план маркетинга для стартапа"
        method_name = "CRAFT"
        optimized_result = "Создайте подробный план маркетинга для технологического стартапа..."

        subject, html_body, plain_body = templates.compose_single_result_email(
            original_prompt, method_name, optimized_result
        )

        # Verify subject contains key elements
        assert "оптимизированный промпт готов" in subject.lower()

        # Verify HTML body contains all required elements
        required_elements = [original_prompt, method_name, optimized_result]
        for element in required_elements:
            assert element in html_body, f"Missing element in HTML: {element}"

        # Verify HTML structure
        assert "<!DOCTYPE html>" in html_body
        assert "<html" in html_body
        assert "</html>" in html_body
        assert "<body>" in html_body or '<div class="container">' in html_body

        # Verify plain text body contains all required elements
        for element in required_elements:
            assert element in plain_body, f"Missing element in plain text: {element}"

    def test_template_security_comprehensive(self):
        """Test comprehensive security measures in templates."""
        from telegram_bot.utils.email_templates import EmailTemplates

        templates = EmailTemplates("EN")

        # Test various malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "<iframe src='javascript:alert(1)'></iframe>",
            "<img src='x' onerror='alert(1)'>",
            "javascript:alert('xss')",
            "<object data='evil.swf'></object>",
            "<embed src='evil.swf'>",
            "<link rel='stylesheet' href='evil.css'>",
            "<meta http-equiv='refresh' content='0;url=evil.com'>",
        ]

        for malicious_input in malicious_inputs:
            subject, html_body, plain_body = templates.compose_single_result_email(
                malicious_input, "CRAFT", "Safe result"
            )

            # Verify dangerous elements are escaped or removed (excluding legitimate meta tags)
            dangerous_patterns = [
                "<script",
                "<iframe",
                "<object",
                "<embed",
                "<link rel=",  # Only dangerous link tags
                "javascript:",
                "onerror=",
                "onload=",
            ]

            for pattern in dangerous_patterns:
                assert pattern not in html_body.lower(), (
                    f"Dangerous pattern '{pattern}' found in HTML body with input: {malicious_input}"
                )

            # Verify that malicious input content is properly escaped
            if "<script>" in malicious_input:
                assert "&lt;script&gt;" in html_body, "Script tags should be HTML escaped"
            if "javascript:" in malicious_input:
                assert "javascript:" not in html_body, "JavaScript protocol should be removed"

    @pytest.mark.asyncio
    async def test_email_service_integration_comprehensive(self):
        """Test comprehensive integration with email service."""
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

        with patch("telegram_bot.services.email_service.get_audit_service"):
            from telegram_bot.services.email_service import EmailDeliveryResult, EmailService

            service = EmailService(config)

            # Test successful sending
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

            # Test duplicate prevention
            service._is_email_already_sent = AsyncMock(return_value=True)

            result = await service.send_single_result_email(
                "user@example.com",
                "Original prompt",
                "CRAFT",
                "Optimized result",
                12345,
            )

            assert result.success is True
            assert result.message_id == "duplicate_blocked"

            # Test failure handling
            service._is_email_already_sent = AsyncMock(return_value=False)
            service._send_email_with_queue_fallback = AsyncMock(
                return_value=EmailDeliveryResult(success=False, error="SMTP error")
            )

            result = await service.send_single_result_email(
                "user@example.com",
                "Original prompt",
                "CRAFT",
                "Optimized result",
                12345,
            )

            assert result.success is False
            assert "SMTP error" in result.error


class TestPostOptimizationRegressionPrevention:
    """Test to prevent regressions in existing functionality."""

    def test_existing_button_definitions_unchanged(self):
        """Test that existing button definitions are not modified."""
        from telegram_bot.utils.messages import (
            BTN_CRAFT,
            BTN_EMAIL_DELIVERY,
            BTN_GGL,
            BTN_LYRA,
        )

        # Verify existing buttons still exist and have expected content
        assert "3 промпта" in BTN_EMAIL_DELIVERY or "3 prompts" in BTN_EMAIL_DELIVERY
        assert "CRAFT" in BTN_CRAFT
        assert "LYRA" in BTN_LYRA
        assert "GGL" in BTN_GGL

    def test_existing_keyboard_layouts_unchanged(self):
        """Test that existing keyboard layouts are not modified."""
        from telegram_bot.utils.messages import (
            FOLLOWUP_CHOICE_KEYBOARD,
            SELECT_METHOD_KEYBOARD,
        )

        # Verify method selection keyboard still contains expected buttons
        method_buttons = [button.text for row in SELECT_METHOD_KEYBOARD.keyboard for button in row]
        assert BTN_EMAIL_DELIVERY in method_buttons

        # Verify follow-up choice keyboard still contains expected buttons
        choice_buttons = [
            button.text for row in FOLLOWUP_CHOICE_KEYBOARD.keyboard for button in row
        ]
        assert BTN_YES in choice_buttons
        assert BTN_NO in choice_buttons

    @pytest.mark.asyncio
    async def test_existing_message_handlers_unchanged(self):
        """Test that existing message handlers still work correctly."""
        # Mock bot handler
        config = MagicMock()
        llm_client = AsyncMock()

        with patch("telegram_bot.core.bot_handler.get_container") as mock_container:
            mock_container.return_value.get_state_manager.return_value = MagicMock()
            mock_container.return_value.get_prompt_loader.return_value = MagicMock()
            mock_container.return_value.get_conversation_manager.return_value = MagicMock()

            from telegram_bot.core.bot_handler import BotHandler

            bot_handler = BotHandler(config, llm_client)

            user_id = 12345
            update = MagicMock()
            update.effective_user.id = user_id
            context = MagicMock()

            # Test reset button still works
            update.message.text = BTN_RESET
            with patch.object(bot_handler, "handle_start") as mock_start:
                await bot_handler.handle_message(update, context)
                mock_start.assert_called_once()

            # Test prompt input still works
            bot_handler.state_manager.set_waiting_for_prompt(user_id, True)
            update.message.text = "Test prompt"

            # Mock the _safe_reply method to avoid async issues
            bot_handler._safe_reply = AsyncMock()

            await bot_handler._handle_prompt_input(update, user_id, "Test prompt")

            # Verify prompt was processed
            assert bot_handler.conversation_manager.set_user_prompt.called
            assert bot_handler.conversation_manager.set_waiting_for_method.called

    def test_message_constants_backward_compatibility(self):
        """Test that message constants maintain backward compatibility."""
        from telegram_bot.utils.messages import (
            EMAIL_INPUT_MESSAGE,
            EMAIL_OPTIMIZATION_SUCCESS,
            ERROR_GENERIC,
            OTP_VERIFICATION_SUCCESS,
            WELCOME_MESSAGE,
            WELCOME_MESSAGE_1,
            WELCOME_MESSAGE_2,
        )

        # Verify key messages still exist and contain expected content
        # WELCOME_MESSAGE is deprecated but kept for backward compatibility
        assert isinstance(WELCOME_MESSAGE, str) and len(WELCOME_MESSAGE) > 0
        # New split welcome messages
        assert isinstance(WELCOME_MESSAGE_1, str) and len(WELCOME_MESSAGE_1) > 0
        assert isinstance(WELCOME_MESSAGE_2, str) and len(WELCOME_MESSAGE_2) > 0
        # Verify identifying emojis are present
        assert "🤖" in WELCOME_MESSAGE_1
        assert "ℹ️" in WELCOME_MESSAGE_2
        assert isinstance(ERROR_GENERIC, str) and len(ERROR_GENERIC) > 0
        assert isinstance(EMAIL_INPUT_MESSAGE, str) and len(EMAIL_INPUT_MESSAGE) > 0
        assert isinstance(OTP_VERIFICATION_SUCCESS, str) and len(OTP_VERIFICATION_SUCCESS) > 0
        assert isinstance(EMAIL_OPTIMIZATION_SUCCESS, str) and len(EMAIL_OPTIMIZATION_SUCCESS) > 0


if __name__ == "__main__":
    pytest.main([__file__])
