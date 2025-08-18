"""Integration tests for the complete follow-up workflow."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import ReplyKeyboardMarkup

from src.bot_handler import BotHandler
from src.config import BotConfig
from src.messages import (
    BTN_GENERATE_PROMPT,
    BTN_NO,
    BTN_RESET,
    BTN_YES,
    FOLLOWUP_CHOICE_KEYBOARD,
    FOLLOWUP_CONVERSATION_KEYBOARD,
    FOLLOWUP_OFFER_MESSAGE,
    PROMPT_READY_FOLLOW_UP,
    RESET_CONFIRMATION,
)


class TestFollowupIntegration:
    """Integration tests for complete follow-up workflow."""

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

    @pytest.mark.asyncio
    async def test_complete_followup_yes_flow_with_refined_prompt(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete ДА flow from offer to refined prompt delivery."""
        user_id = mock_update.effective_user.id

        # Step 1: Simulate receiving an improved prompt that triggers follow-up offer
        original_prompt = "Original user prompt"
        improved_prompt = "This is an improved prompt"

        # Set up initial state as if user just received improved prompt
        bot_handler.conversation_manager.set_user_prompt(user_id, original_prompt)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        # Step 2: User clicks ДА button
        mock_update.message.text = BTN_YES

        # Mock LLM responses for follow-up conversation
        # Note: We need to reset side_effect for each call since the conversation gets reset
        bot_handler.llm_client.send_prompt.side_effect = None
        llm_responses = [
            "What is the main goal of your prompt?",  # Initial question
            "Can you provide more context about your target audience?",  # Follow-up question
            "<REFINED_PROMPT>Your highly refined and improved prompt based on our conversation</REFINED_PROMPT>",  # Final refined prompt
        ]
        response_iter = iter(llm_responses)
        bot_handler.llm_client.send_prompt.side_effect = lambda *args: next(
            response_iter
        )

        # Step 3: Handle ДА choice
        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Verify state transition to follow-up conversation
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is True

        # Verify initial LLM call was made
        assert bot_handler.llm_client.send_prompt.call_count == 1

        # Verify initial question was sent with correct keyboard
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args_list[-1]
        assert "What is the main goal" in call_args[0][0]
        assert call_args[1]["reply_markup"] == FOLLOWUP_CONVERSATION_KEYBOARD

        # Step 4: User provides answer to first question
        mock_update.message.text = "I want to create marketing copy"
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "I want to create marketing copy"
        )

        # Verify user response was added to conversation
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        assert any(
            msg["content"] == "I want to create marketing copy"
            and msg["role"] == "user"
            for msg in transcript
        )

        # Verify second LLM call was made
        assert bot_handler.llm_client.send_prompt.call_count == 2

        # Step 5: User provides answer to second question
        mock_update.message.text = "Small business owners"
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "Small business owners"
        )

        # Note: After the refined prompt is returned, the conversation gets reset
        # So we don't check the transcript here, but verify the final outcome

        # Verify third LLM call was made and refined prompt was processed
        assert bot_handler.llm_client.send_prompt.call_count == 3

        # Step 6: Verify final state after refined prompt delivery
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify refined prompt and completion message were sent
        reply_calls = mock_update.message.reply_text.call_args_list

        # Find the refined prompt message
        refined_prompt_sent = False
        completion_message_sent = False

        for call in reply_calls:
            message_text = call[0][0]
            if "highly refined and improved prompt" in message_text:
                refined_prompt_sent = True
            if PROMPT_READY_FOLLOW_UP in message_text:
                completion_message_sent = True

        assert refined_prompt_sent, "Refined prompt was not sent to user"
        assert completion_message_sent, "Completion message was not sent to user"

    @pytest.mark.asyncio
    async def test_complete_followup_no_flow_to_reset(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete НЕТ flow from offer to prompt input reset."""
        user_id = mock_update.effective_user.id

        # Step 1: Set up follow-up choice waiting state
        improved_prompt = "This is an improved prompt"
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        # Step 2: User clicks НЕТ button
        mock_update.message.text = BTN_NO
        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_NO)

        # Step 3: Verify RESET_CONFIRMATION message was sent
        mock_update.message.reply_text.assert_called()
        call_args = mock_update.message.reply_text.call_args
        assert RESET_CONFIRMATION in call_args[0][0]

        # Verify empty keyboard was set
        assert isinstance(call_args[1]["reply_markup"], ReplyKeyboardMarkup)
        assert call_args[1]["reply_markup"].keyboard == ((),)

        # Step 4: Verify state was properly reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.waiting_for_prompt is True
        assert user_state.improved_prompt_cache is None
        assert user_state.in_followup_conversation is False

        # Verify conversation was reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []

        # Step 5: Verify user can now input a new prompt
        mock_update.message.text = "New prompt for optimization"
        await bot_handler._handle_prompt_input(
            mock_update, user_id, "New prompt for optimization"
        )

        # Verify new prompt was accepted and method selection was triggered
        assert (
            bot_handler.conversation_manager.get_user_prompt(user_id)
            == "New prompt for optimization"
        )
        assert bot_handler.conversation_manager.is_waiting_for_method(user_id) is True

    @pytest.mark.asyncio
    async def test_generate_button_functionality_during_qa_phase(
        self, bot_handler, mock_update, mock_context
    ):
        """Test generate button functionality during question-answer phase."""
        user_id = mock_update.effective_user.id

        # Step 1: Set up follow-up conversation state
        improved_prompt = "Original improved prompt"
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Mock LLM response with refined prompt
        refined_prompt_response = "<REFINED_PROMPT>Generated refined prompt from button click</REFINED_PROMPT>"
        bot_handler.llm_client.send_prompt.return_value = refined_prompt_response

        # Step 2: User clicks generate button
        mock_update.message.text = BTN_GENERATE_PROMPT
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, BTN_GENERATE_PROMPT
        )

        # Note: After the refined prompt is returned, the conversation gets reset
        # So we don't check the transcript here, but verify the LLM was called

        # Verify LLM was called
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Step 4: Verify refined prompt was delivered and state was reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify refined prompt and completion messages were sent
        reply_calls = mock_update.message.reply_text.call_args_list

        refined_prompt_sent = False
        completion_message_sent = False

        for call in reply_calls:
            message_text = call[0][0]
            if "Generated refined prompt from button click" in message_text:
                refined_prompt_sent = True
            if PROMPT_READY_FOLLOW_UP in message_text:
                completion_message_sent = True

        assert refined_prompt_sent, "Refined prompt was not sent to user"
        assert completion_message_sent, "Completion message was not sent to user"

    @pytest.mark.asyncio
    async def test_conversation_state_management_throughout_flow(
        self, bot_handler, mock_update, mock_context
    ):
        """Test conversation state management throughout entire flow."""
        user_id = mock_update.effective_user.id

        # Step 1: Initial state - waiting for prompt
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Step 2: Simulate improved prompt received, follow-up offer sent
        improved_prompt = "Improved prompt content"
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        # Verify follow-up choice state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is False
        assert user_state.waiting_for_followup_choice is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache == improved_prompt

        # Step 3: User accepts follow-up (ДА)
        mock_update.message.text = BTN_YES
        bot_handler.llm_client.send_prompt.return_value = "What is your goal?"

        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Verify follow-up conversation state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is False
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is True
        assert user_state.improved_prompt_cache == improved_prompt

        # Verify conversation manager state
        assert (
            bot_handler.conversation_manager.is_in_followup_conversation(user_id)
            is True
        )

        # Step 4: User provides answer
        mock_update.message.text = "My goal is to create better content"
        bot_handler.llm_client.send_prompt.return_value = (
            "<REFINED_PROMPT>Final refined prompt</REFINED_PROMPT>"
        )

        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "My goal is to create better content"
        )

        # Step 5: Verify final state after completion
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

        # Verify conversation was reset
        assert (
            bot_handler.conversation_manager.is_in_followup_conversation(user_id)
            is False
        )

    @pytest.mark.asyncio
    async def test_proper_cleanup_and_reset_after_completion(
        self, bot_handler, mock_update, mock_context
    ):
        """Test proper cleanup and reset after follow-up completion."""
        user_id = mock_update.effective_user.id

        # Step 1: Set up follow-up conversation with some history
        improved_prompt = "Original improved prompt"
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Add some conversation history
        bot_handler.conversation_manager.append_message(user_id, "user", "First answer")
        bot_handler.conversation_manager.append_message(
            user_id, "assistant", "Follow-up question"
        )
        bot_handler.conversation_manager.append_message(
            user_id, "user", "Second answer"
        )

        # Add some token usage
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id, {"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80}
        )

        # Step 2: Complete the follow-up conversation
        refined_prompt = "Final refined prompt"
        await bot_handler._complete_followup_conversation(
            mock_update, user_id, refined_prompt
        )

        # Step 3: Verify complete cleanup
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None
        assert user_state.last_interaction is None

        # Verify conversation was completely reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []
        assert (
            bot_handler.conversation_manager.is_in_followup_conversation(user_id)
            is False
        )
        assert bot_handler.conversation_manager.get_user_prompt(user_id) is None
        assert bot_handler.conversation_manager.is_waiting_for_method(user_id) is False

        # Verify token usage was cleared (after logging)
        # Note: Token usage might be cleared after logging, depending on implementation

        # Step 4: Verify user can start fresh workflow
        mock_update.message.text = "Brand new prompt"
        await bot_handler._handle_prompt_input(mock_update, user_id, "Brand new prompt")

        # Verify new prompt workflow starts correctly
        assert (
            bot_handler.conversation_manager.get_user_prompt(user_id)
            == "Brand new prompt"
        )
        assert bot_handler.conversation_manager.is_waiting_for_method(user_id) is True

    @pytest.mark.asyncio
    async def test_integration_with_existing_prompt_optimization_methods(
        self, bot_handler, mock_update, mock_context
    ):
        """Test integration with existing prompt optimization methods."""
        user_id = mock_update.effective_user.id

        # Step 1: Start with regular CRAFT optimization that produces improved prompt
        original_prompt = "Help me write better emails"
        bot_handler.conversation_manager.set_user_prompt(user_id, original_prompt)
        bot_handler.conversation_manager.append_message(
            user_id, "user", original_prompt
        )
        bot_handler.conversation_manager.set_current_method(user_id, "CRAFT")

        # Mock LLM response with improved prompt
        improved_prompt_response = "<IMPROVED_PROMPT>You are an expert email writer. Help me craft professional, engaging emails that achieve specific goals. When I provide an email request, analyze the purpose, audience, and desired outcome, then create a well-structured email with appropriate tone, clear subject line, and compelling content.</IMPROVED_PROMPT>"
        bot_handler.llm_client.send_prompt.return_value = improved_prompt_response

        # Step 2: Process with LLM (this should trigger follow-up offer)
        await bot_handler._process_with_llm(mock_update, user_id, "CRAFT")

        # Step 3: Verify improved prompt was sent and follow-up offer was made
        reply_calls = mock_update.message.reply_text.call_args_list

        # Find improved prompt message
        improved_prompt_sent = False
        followup_offer_sent = False

        for call in reply_calls:
            message_text = call[0][0]
            if "expert email writer" in message_text:
                improved_prompt_sent = True
            if FOLLOWUP_OFFER_MESSAGE in message_text:
                followup_offer_sent = True
                # Verify correct keyboard was used
                assert call[1]["reply_markup"] == FOLLOWUP_CHOICE_KEYBOARD

        assert improved_prompt_sent, "Improved prompt was not sent"
        assert followup_offer_sent, "Follow-up offer was not sent"

        # Step 4: Verify state is correctly set for follow-up choice
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is True
        assert user_state.waiting_for_prompt is False
        assert "expert email writer" in user_state.improved_prompt_cache

        # Step 5: Verify conversation was reset but cache preserved
        assert bot_handler.conversation_manager.get_transcript(user_id) == []
        assert bot_handler.conversation_manager.is_waiting_for_method(user_id) is False

        # Step 6: User accepts follow-up and completes the flow
        mock_update.message.text = BTN_YES
        bot_handler.llm_client.send_prompt.side_effect = [
            "What type of emails do you write most often?",
            "<REFINED_PROMPT>You are an expert email writer specializing in business communications. Help me craft professional, engaging emails that achieve specific goals. When I provide an email request, analyze the purpose, audience, and desired outcome, then create a well-structured email with appropriate tone, clear subject line, and compelling content. Focus on clarity, professionalism, and actionable outcomes.</REFINED_PROMPT>",
        ]

        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Answer the follow-up question
        mock_update.message.text = "Business emails to clients and partners"
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "Business emails to clients and partners"
        )

        # Step 7: Verify final refined prompt incorporates follow-up context
        final_reply_calls = mock_update.message.reply_text.call_args_list

        refined_prompt_sent = False
        for call in final_reply_calls:
            message_text = call[0][0]
            if "specializing in business communications" in message_text:
                refined_prompt_sent = True
                break

        assert refined_prompt_sent, "Refined prompt with follow-up context was not sent"

        # Step 8: Verify system is ready for next optimization
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

    @pytest.mark.asyncio
    async def test_message_routing_during_followup_states(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that handle_message routes correctly during follow-up states."""
        user_id = mock_update.effective_user.id

        # Test 1: Routing during follow-up choice waiting
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        mock_update.message.text = BTN_YES

        with patch.object(bot_handler, "_handle_followup_choice") as mock_handle_choice:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle_choice.assert_called_once_with(mock_update, user_id, BTN_YES)

        # Test 2: Routing during follow-up conversation
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, False)
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)

        mock_update.message.text = "My answer to the question"

        with patch.object(
            bot_handler, "_handle_followup_conversation"
        ) as mock_handle_conv:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle_conv.assert_called_once_with(
                mock_update, user_id, "My answer to the question"
            )

        # Test 3: Reset button works in any state
        mock_update.message.text = BTN_RESET

        with patch.object(bot_handler, "handle_start") as mock_handle_start:
            await bot_handler.handle_message(mock_update, mock_context)
            mock_handle_start.assert_called_once_with(mock_update, mock_context)

    @pytest.mark.asyncio
    async def test_error_recovery_and_fallback_mechanisms(
        self, bot_handler, mock_update, mock_context
    ):
        """Test error recovery and fallback mechanisms during follow-up."""
        user_id = mock_update.effective_user.id

        # Step 1: Set up follow-up conversation
        improved_prompt = "Original improved prompt"
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Step 2: Simulate LLM error
        bot_handler.llm_client.send_prompt.side_effect = Exception("Network timeout")

        mock_update.message.text = "My answer to the question"
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "My answer to the question"
        )

        # Step 3: Verify fallback to cached improved prompt
        reply_calls = mock_update.message.reply_text.call_args_list

        fallback_used = False
        for call in reply_calls:
            message_text = call[0][0]
            if improved_prompt in message_text:
                fallback_used = True
                break

        assert fallback_used, "Fallback to cached improved prompt was not used"

        # Step 4: Verify state was properly reset after error
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

    @pytest.mark.asyncio
    async def test_followup_with_malformed_llm_responses(
        self, bot_handler, mock_update, mock_context
    ):
        """Test handling of malformed LLM responses during follow-up."""
        user_id = mock_update.effective_user.id

        # Step 1: Set up follow-up conversation
        improved_prompt = "Original improved prompt"
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, improved_prompt
        )

        # Step 2: Test malformed refined prompt response
        malformed_response = "<REFINED_PROMPT>Incomplete refined prompt without closing"
        bot_handler.llm_client.send_prompt.return_value = malformed_response

        mock_update.message.text = "My answer"
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "My answer"
        )

        # Step 3: Verify fallback parsing worked
        reply_calls = mock_update.message.reply_text.call_args_list

        refined_prompt_sent = False
        for call in reply_calls:
            message_text = call[0][0]
            if "Incomplete refined prompt without closing" in message_text:
                refined_prompt_sent = True
                break

        assert refined_prompt_sent, "Malformed refined prompt was not parsed and sent"

        # Step 4: Verify completion flow still worked
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.in_followup_conversation is False

    @pytest.mark.asyncio
    async def test_concurrent_user_followup_isolation(
        self, bot_handler, mock_config, mock_llm_client
    ):
        """Test that follow-up conversations for different users are properly isolated."""
        # Create separate update objects for two users
        user1_id = 12345
        user2_id = 67890

        update1 = MagicMock()
        update1.effective_user.id = user1_id
        update1.message = MagicMock()
        update1.message.reply_text = AsyncMock(return_value=None)

        update2 = MagicMock()
        update2.effective_user.id = user2_id
        update2.message = MagicMock()
        update2.message.reply_text = AsyncMock(return_value=None)

        # Step 1: Set up follow-up conversations for both users
        improved_prompt1 = "User 1 improved prompt"
        improved_prompt2 = "User 2 improved prompt"

        bot_handler.state_manager.set_in_followup_conversation(user1_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user1_id, improved_prompt1)
        bot_handler.conversation_manager.start_followup_conversation(
            user1_id, improved_prompt1
        )

        bot_handler.state_manager.set_in_followup_conversation(user2_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user2_id, improved_prompt2)
        bot_handler.conversation_manager.start_followup_conversation(
            user2_id, improved_prompt2
        )

        # Step 2: Both users provide answers simultaneously
        mock_llm_client.send_prompt.side_effect = [
            "<REFINED_PROMPT>User 1 refined prompt</REFINED_PROMPT>",
            "<REFINED_PROMPT>User 2 refined prompt</REFINED_PROMPT>",
        ]

        update1.message.text = "User 1 answer"
        update2.message.text = "User 2 answer"

        await bot_handler._handle_followup_conversation(
            update1, user1_id, "User 1 answer"
        )
        await bot_handler._handle_followup_conversation(
            update2, user2_id, "User 2 answer"
        )

        # Step 3: Verify each user received their own refined prompt
        user1_calls = update1.message.reply_text.call_args_list
        user2_calls = update2.message.reply_text.call_args_list

        user1_got_correct_prompt = False
        user2_got_correct_prompt = False

        for call in user1_calls:
            if "User 1 refined prompt" in call[0][0]:
                user1_got_correct_prompt = True

        for call in user2_calls:
            if "User 2 refined prompt" in call[0][0]:
                user2_got_correct_prompt = True

        assert user1_got_correct_prompt, "User 1 did not receive correct refined prompt"
        assert user2_got_correct_prompt, "User 2 did not receive correct refined prompt"

        # Step 4: Verify both users' states were properly reset
        user1_state = bot_handler.state_manager.get_user_state(user1_id)
        user2_state = bot_handler.state_manager.get_user_state(user2_id)

        assert user1_state.waiting_for_prompt is True
        assert user1_state.in_followup_conversation is False
        assert user1_state.improved_prompt_cache is None

        assert user2_state.waiting_for_prompt is True
        assert user2_state.in_followup_conversation is False
        assert user2_state.improved_prompt_cache is None
