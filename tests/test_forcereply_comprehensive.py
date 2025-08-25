"""Comprehensive tests for ForceReply functionality in follow-up questions feature."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from telegram import ForceReply

from src.bot_handler import BotHandler
from src.config import BotConfig
from src.messages import (
    BTN_NO,
    BTN_YES,
    FOLLOWUP_PROMPT_INPUT_MESSAGE,
    create_prompt_input_reply,
)


class TestForceReplyCreationComprehensive:
    """Comprehensive tests for ForceReply creation with various prompt formats."""

    def test_create_forcereply_minimal_prompt(self):
        """Test ForceReply creation with minimal single-word prompt."""
        prompt = "Hello"
        force_reply = create_prompt_input_reply(prompt)

        assert isinstance(force_reply, ForceReply)
        assert force_reply.input_field_placeholder == prompt
        assert force_reply.selective is False

    def test_create_forcereply_medium_prompt(self):
        """Test ForceReply creation with medium-length prompt."""
        prompt = "Write a detailed story about a brave knight who saves a village from a dragon."
        force_reply = create_prompt_input_reply(prompt)

        assert isinstance(force_reply, ForceReply)
        assert force_reply.input_field_placeholder == prompt
        assert force_reply.selective is False

    def test_create_forcereply_very_long_prompt(self):
        """Test ForceReply creation with very long prompt (stress test)."""
        # Create a 2000+ character prompt
        base_segment = "This is a detailed segment of a very comprehensive prompt that includes many specific instructions and requirements. "
        prompt = base_segment * 20  # ~2000 characters

        force_reply = create_prompt_input_reply(prompt)

        assert isinstance(force_reply, ForceReply)
        assert force_reply.input_field_placeholder == prompt
        assert len(force_reply.input_field_placeholder) > 2000

    def test_create_forcereply_multiline_formatted_prompt(self):
        """Test ForceReply creation with multiline formatted prompt."""
        prompt = """Create a comprehensive business plan that includes:

1. Executive Summary
2. Market Analysis
3. Financial Projections
4. Marketing Strategy

Please ensure each section is detailed and well-researched."""

        force_reply = create_prompt_input_reply(prompt)

        assert isinstance(force_reply, ForceReply)
        assert force_reply.input_field_placeholder == prompt
        assert "\n" in force_reply.input_field_placeholder

    def test_create_forcereply_special_characters_comprehensive(self):
        """Test ForceReply creation with comprehensive special character set."""
        prompt = "Prompt with \"quotes\", 'apostrophes', symbols: @#$%^&*()+={}[]|\\:\";'<>?,./, unicode: café 🚀 🎯 ✨, and newlines:\nLine 2"

        force_reply = create_prompt_input_reply(prompt)

        assert isinstance(force_reply, ForceReply)
        assert force_reply.input_field_placeholder == prompt
        # Verify all special characters are preserved
        assert '"quotes"' in force_reply.input_field_placeholder
        assert "café 🚀" in force_reply.input_field_placeholder

    def test_create_forcereply_markdown_syntax_preservation(self):
        """Test ForceReply creation preserves markdown syntax without escaping."""
        prompt = "Create content with **bold**, *italic*, `code blocks`, [links](url), and ## headers"

        force_reply = create_prompt_input_reply(prompt)

        assert isinstance(force_reply, ForceReply)
        assert force_reply.input_field_placeholder == prompt
        # Verify markdown is preserved as-is (no escaping for ForceReply)
        assert "**bold**" in force_reply.input_field_placeholder
        assert "*italic*" in force_reply.input_field_placeholder
        assert "`code blocks`" in force_reply.input_field_placeholder

    def test_create_forcereply_edge_cases(self):
        """Test ForceReply creation with edge case inputs."""
        edge_cases = [
            "",  # Empty string
            " ",  # Single space
            "\n",  # Single newline
            "\t",  # Single tab
            "   \n\t   ",  # Mixed whitespace
            "A",  # Single character
            "🚀",  # Single emoji
        ]

        for prompt in edge_cases:
            force_reply = create_prompt_input_reply(prompt)
            assert isinstance(force_reply, ForceReply)
            assert force_reply.input_field_placeholder == prompt
            assert force_reply.selective is False


class TestForceReplyCompleteFlow:
    """Test complete flow from choice to prompt input to conversation start."""

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
        client.send_prompt = AsyncMock(return_value="Follow-up question from LLM")
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
    async def test_complete_flow_yes_choice_to_forcereply(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete flow from YES choice to ForceReply display."""
        user_id = mock_update.effective_user.id
        cached_prompt = "Write a comprehensive guide about machine learning"
        mock_update.message.text = BTN_YES

        # Set up initial state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, cached_prompt)

        # Execute YES choice
        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Verify two messages were sent: instruction and ForceReply with code block
        assert mock_update.message.reply_text.call_count == 2

        # Verify first message is instruction
        first_call = mock_update.message.reply_text.call_args_list[0]
        assert FOLLOWUP_PROMPT_INPUT_MESSAGE in first_call[0][0]

        # Verify second message contains code block with ForceReply
        second_call = mock_update.message.reply_text.call_args_list[1]
        assert f"```\n{cached_prompt}\n```" == second_call[0][0]
        assert "reply_markup" in second_call[1]
        assert isinstance(second_call[1]["reply_markup"], ForceReply)
        assert second_call[1]["reply_markup"].input_field_placeholder == cached_prompt

        # Verify state transition
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.waiting_for_followup_prompt_input is True
        assert user_state.in_followup_conversation is False

    @pytest.mark.asyncio
    async def test_code_block_formatting_in_yes_choice(
        self, bot_handler, mock_update, mock_context
    ):
        """Test that improved prompt is properly wrapped in code blocks for easy copying."""
        user_id = mock_update.effective_user.id
        test_prompts = [
            "Simple prompt",
            "Multi-line\nprompt with\nline breaks",
            "Prompt with special characters: @#$%^&*()",
            "Very long prompt " * 50,  # ~850 characters
        ]

        prompt = "Simple prompt"

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, prompt)
        mock_update.message.text = BTN_YES

        # Execute YES choice
        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Verify code block message is sent correctly with ForceReply
        assert mock_update.message.reply_text.call_count == 2
        code_block_call = mock_update.message.reply_text.call_args_list[1]
        expected_code_block = f"```\n{prompt}\n```"
        assert code_block_call[0][0] == expected_code_block
        # Verify it also has ForceReply markup
        assert "reply_markup" in code_block_call[1]
        assert isinstance(code_block_call[1]["reply_markup"], ForceReply)

    @pytest.mark.asyncio
    async def test_complete_flow_prompt_input_to_conversation(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete flow from prompt input to conversation start."""
        user_id = mock_update.effective_user.id
        original_cached = "Original improved prompt"
        user_modified = "User modified improved prompt with additional details"
        mock_update.message.text = user_modified

        # Set up prompt input waiting state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, original_cached)

        # Execute prompt input
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, user_modified
        )

        # Verify conversation was started with user's modified prompt
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        assert len(transcript) >= 2  # System prompt + user prompt

        # Find user message in transcript
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert len(user_messages) >= 1
        assert user_messages[0]["content"] == user_modified

        # Verify state transition
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_prompt_input is False
        assert user_state.in_followup_conversation is True

        # Verify LLM was called to start asking questions
        bot_handler.llm_client.send_prompt.assert_called_once()

        # Verify response was sent to user
        mock_update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_flow_end_to_end_with_modifications(
        self, bot_handler, mock_update, mock_context
    ):
        """Test complete end-to-end flow with user prompt modifications."""
        user_id = mock_update.effective_user.id
        original_prompt = "Write a story"
        user_modified_prompt = "Write a detailed science fiction story about time travel with complex characters"

        # Step 1: Set up follow-up choice state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, original_prompt)

        # Step 2: User clicks YES
        mock_update.message.text = BTN_YES
        await bot_handler._handle_followup_choice(mock_update, user_id, BTN_YES)

        # Verify two messages were sent: instruction and ForceReply with code block
        assert mock_update.message.reply_text.call_count == 2

        # Verify first message is instruction
        first_call = mock_update.message.reply_text.call_args_list[0]
        assert FOLLOWUP_PROMPT_INPUT_MESSAGE in first_call[0][0]

        # Verify second message contains code block with ForceReply
        second_call = mock_update.message.reply_text.call_args_list[1]
        assert f"```\n{original_prompt}\n```" == second_call[0][0]
        force_reply = second_call[1]["reply_markup"]
        assert isinstance(force_reply, ForceReply)
        assert force_reply.input_field_placeholder == original_prompt

        # Step 3: User modifies and sends prompt
        mock_update.message.text = user_modified_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, user_modified_prompt
        )

        # Verify conversation started with modified prompt
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert user_messages[0]["content"] == user_modified_prompt

        # Verify final state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.in_followup_conversation is True
        assert user_state.waiting_for_followup_prompt_input is False
        assert user_state.waiting_for_followup_choice is False


class TestForceReplyUserModifications:
    """Test user modification scenarios in ForceReply input area."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BotConfig)
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        config.model_name = "test-model"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.send_prompt = AsyncMock(return_value="LLM response")
        return client

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user.id = 12345
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_user_sends_unmodified_prompt(self, bot_handler, mock_update):
        """Test user sends the exact same prompt without modifications."""
        user_id = mock_update.effective_user.id
        original_prompt = "Create a marketing plan for a new product"

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, original_prompt)

        # User sends exact same prompt
        mock_update.message.text = original_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, original_prompt
        )

        # Verify conversation started with original prompt
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert user_messages[0]["content"] == original_prompt

    @pytest.mark.asyncio
    async def test_user_adds_details_to_prompt(self, bot_handler, mock_update):
        """Test user adds additional details to the prompt."""
        user_id = mock_update.effective_user.id
        original_prompt = "Write a story"
        modified_prompt = "Write a story about a detective solving a mysterious case in Victorian London with detailed character development"

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, original_prompt)

        # User sends modified prompt
        mock_update.message.text = modified_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, modified_prompt
        )

        # Verify conversation started with modified prompt
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert user_messages[0]["content"] == modified_prompt
        assert "detective" in user_messages[0]["content"]
        assert "Victorian London" in user_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_user_completely_rewrites_prompt(self, bot_handler, mock_update):
        """Test user completely rewrites the prompt."""
        user_id = mock_update.effective_user.id
        original_prompt = "Write a story about adventure"
        completely_new_prompt = "Create a technical documentation for a REST API with authentication examples"

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, original_prompt)

        # User sends completely different prompt
        mock_update.message.text = completely_new_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, completely_new_prompt
        )

        # Verify conversation started with new prompt
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert user_messages[0]["content"] == completely_new_prompt
        assert "REST API" in user_messages[0]["content"]
        assert "story" not in user_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_user_removes_parts_of_prompt(self, bot_handler, mock_update):
        """Test user removes parts of the original prompt."""
        user_id = mock_update.effective_user.id
        original_prompt = "Write a detailed comprehensive story about adventure with complex characters and multiple plot twists"
        simplified_prompt = "Write a story about adventure"

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, original_prompt)

        # User sends simplified prompt
        mock_update.message.text = simplified_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, simplified_prompt
        )

        # Verify conversation started with simplified prompt
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert user_messages[0]["content"] == simplified_prompt
        assert "complex characters" not in user_messages[0]["content"]
        assert "plot twists" not in user_messages[0]["content"]

    @pytest.mark.asyncio
    async def test_user_adds_formatting_to_prompt(self, bot_handler, mock_update):
        """Test user adds formatting and structure to the prompt."""
        user_id = mock_update.effective_user.id
        original_prompt = "Create a business plan"
        formatted_prompt = """Create a business plan that includes:

1. Executive Summary
2. Market Analysis  
3. Financial Projections
4. Marketing Strategy

Please make it detailed and professional."""

        # Set up state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, original_prompt)

        # User sends formatted prompt
        mock_update.message.text = formatted_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, formatted_prompt
        )

        # Verify conversation started with formatted prompt
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert user_messages[0]["content"] == formatted_prompt
        assert "1. Executive Summary" in user_messages[0]["content"]
        assert "\n" in user_messages[0]["content"]


class TestForceReplyStateTransitions:
    """Test state transitions through all phases of enhanced follow-up flow."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BotConfig)
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        config.model_name = "test-model"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.send_prompt = AsyncMock(return_value="LLM question")
        return client

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    def test_state_transition_initial_to_choice_waiting(self, bot_handler):
        """Test state transition from initial state to follow-up choice waiting."""
        user_id = 12345
        improved_prompt = "Improved prompt content"

        # Initial state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False

        # Transition to choice waiting
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, improved_prompt)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        # Verify new state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is False
        assert user_state.waiting_for_followup_choice is True
        assert user_state.improved_prompt_cache == improved_prompt

    def test_state_transition_choice_to_prompt_input_waiting(self, bot_handler):
        """Test state transition from choice waiting to prompt input waiting."""
        user_id = 12345

        # Set up choice waiting state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        # Transition to prompt input waiting (YES choice)
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, False)
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)

        # Verify state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_choice is False
        assert user_state.waiting_for_followup_prompt_input is True
        assert user_state.in_followup_conversation is False

    def test_state_transition_prompt_input_to_conversation(self, bot_handler):
        """Test state transition from prompt input waiting to conversation active."""
        user_id = 12345

        # Set up prompt input waiting state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        # Transition to conversation active
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, False)
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)

        # Verify state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_followup_prompt_input is False
        assert user_state.in_followup_conversation is True

    def test_state_transition_conversation_to_completion(self, bot_handler):
        """Test state transition from conversation active to completion."""
        user_id = 12345

        # Set up conversation active state
        bot_handler.state_manager.set_in_followup_conversation(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")

        # Transition to completion (reset state)
        bot_handler.reset_user_state(user_id)

        # Verify final state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.waiting_for_followup_prompt_input is False
        assert user_state.in_followup_conversation is False
        assert user_state.improved_prompt_cache is None

    def test_state_transition_choice_no_to_reset(self, bot_handler):
        """Test state transition from choice waiting to reset (NO choice)."""
        user_id = 12345

        # Set up choice waiting state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Cached prompt")
        bot_handler.state_manager.set_waiting_for_prompt(user_id, False)

        # Transition to reset (NO choice)
        bot_handler.reset_user_state(user_id)

        # Verify reset state
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert user_state.waiting_for_prompt is True
        assert user_state.waiting_for_followup_choice is False
        assert user_state.improved_prompt_cache is None

    def test_state_validation_during_transitions(self, bot_handler):
        """Test state validation during all transitions."""
        user_id = 12345

        # Test each state individually
        states_to_test = [
            ("waiting_for_followup_choice", True),
            ("waiting_for_followup_prompt_input", True),
            ("in_followup_conversation", True),
        ]

        for state_field, value in states_to_test:
            # Reset to clean state
            bot_handler.reset_user_state(user_id)

            # Set specific state
            if state_field == "waiting_for_followup_choice":
                bot_handler.state_manager.set_waiting_for_followup_choice(
                    user_id, value
                )
            elif state_field == "waiting_for_followup_prompt_input":
                bot_handler.state_manager.set_waiting_for_followup_prompt_input(
                    user_id, value
                )
            elif state_field == "in_followup_conversation":
                bot_handler.state_manager.set_in_followup_conversation(user_id, value)

            # Verify only this state is active
            user_state = bot_handler.state_manager.get_user_state(user_id)
            active_states = [
                user_state.waiting_for_followup_choice,
                user_state.waiting_for_followup_prompt_input,
                user_state.in_followup_conversation,
            ]

            # Only one follow-up state should be active at a time
            assert sum(active_states) == 1


class TestForceReplyIntegrationWithExistingFeatures:
    """Test integration with existing follow-up conversation functionality."""

    @pytest.fixture
    def mock_config(self):
        config = MagicMock(spec=BotConfig)
        config.bot_id = "test_bot"
        config.llm_backend = "TEST"
        config.model_name = "test-model"
        return config

    @pytest.fixture
    def mock_llm_client(self):
        client = MagicMock()
        client.send_prompt = AsyncMock()
        return client

    @pytest.fixture
    def bot_handler(self, mock_config, mock_llm_client):
        return BotHandler(mock_config, mock_llm_client, lambda event, payload: None)

    @pytest.fixture
    def mock_update(self):
        update = MagicMock()
        update.effective_user.id = 12345
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        return update

    @pytest.mark.asyncio
    async def test_integration_forcereply_with_conversation_flow(
        self, bot_handler, mock_update
    ):
        """Test ForceReply integration with existing conversation flow."""
        user_id = mock_update.effective_user.id
        user_prompt = "Modified prompt from ForceReply"

        # Mock LLM responses for conversation
        bot_handler.llm_client.send_prompt.side_effect = [
            "What is your target audience?",  # First question
            "What tone should the content have?",  # Second question
            "<REFINED_PROMPT>Final refined prompt</REFINED_PROMPT>",  # Final result
        ]

        # Start from prompt input state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Original prompt")

        # Step 1: Handle prompt input (from ForceReply)
        mock_update.message.text = user_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, user_prompt
        )

        # Verify conversation started
        assert (
            bot_handler.state_manager.get_user_state(user_id).in_followup_conversation
            is True
        )

        # Step 2: User responds to first question
        mock_update.message.text = "Business professionals"
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "Business professionals"
        )

        # Step 3: User responds to second question
        mock_update.message.text = "Professional and informative"
        await bot_handler._handle_followup_conversation(
            mock_update, user_id, "Professional and informative"
        )

        # Verify all LLM calls were made
        assert bot_handler.llm_client.send_prompt.call_count == 3

        # Verify LLM was called to start and continue conversation
        assert bot_handler.llm_client.send_prompt.call_count >= 1

        # Verify response was sent to user
        mock_update.message.reply_text.assert_called()

        # Verify response was sent to user
        mock_update.message.reply_text.assert_called()

    @pytest.mark.asyncio
    async def test_integration_forcereply_with_generate_button(
        self, bot_handler, mock_update
    ):
        """Test ForceReply integration with generate button functionality."""
        user_id = mock_update.effective_user.id
        user_prompt = "User modified prompt"

        # Mock LLM responses
        bot_handler.llm_client.send_prompt.side_effect = [
            "What specific features do you want?",  # Initial question
            "<REFINED_PROMPT>Generated refined prompt</REFINED_PROMPT>",  # Generate response
        ]

        # Start conversation from ForceReply input
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        mock_update.message.text = user_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, user_prompt
        )

        # User clicks generate button instead of answering question
        from src.messages import BTN_GENERATE_PROMPT

        mock_update.message.text = BTN_GENERATE_PROMPT

        with patch.object(bot_handler, "_process_followup_generation") as mock_generate:
            await bot_handler._handle_followup_conversation(
                mock_update, user_id, BTN_GENERATE_PROMPT
            )
            mock_generate.assert_called_once_with(mock_update, user_id)

    @pytest.mark.asyncio
    async def test_integration_forcereply_with_error_handling(
        self, bot_handler, mock_update
    ):
        """Test ForceReply integration with error handling."""
        user_id = mock_update.effective_user.id
        user_prompt = "User prompt that will cause error"

        # Mock LLM to raise error
        bot_handler.llm_client.send_prompt.side_effect = Exception("LLM Error")

        # Start from prompt input state
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(
            user_id, "Original cached prompt"
        )

        # Handle prompt input with error
        mock_update.message.text = user_prompt
        await bot_handler._handle_followup_prompt_input(
            mock_update, user_id, user_prompt
        )

        # Verify error was handled gracefully
        mock_update.message.reply_text.assert_called()

        # Verify state was reset appropriately
        user_state = bot_handler.state_manager.get_user_state(user_id)
        # Should fall back to original cached prompt or reset state
        assert user_state.waiting_for_followup_prompt_input is False

    def test_integration_forcereply_with_state_manager(self, bot_handler):
        """Test ForceReply integration with StateManager functionality."""
        user_id = 12345

        # Test that ForceReply states work with existing state management
        original_state = bot_handler.state_manager.get_user_state(user_id)
        assert original_state.waiting_for_prompt is True

        # Set ForceReply-related states
        bot_handler.state_manager.set_waiting_for_followup_prompt_input(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Test prompt")

        # Verify states are properly managed
        updated_state = bot_handler.state_manager.get_user_state(user_id)
        assert updated_state.waiting_for_followup_prompt_input is True
        assert updated_state.improved_prompt_cache == "Test prompt"

        # Test reset functionality
        bot_handler.reset_user_state(user_id)
        final_state = bot_handler.state_manager.get_user_state(user_id)
        assert final_state.waiting_for_followup_prompt_input is False
        assert final_state.improved_prompt_cache is None

    def test_integration_forcereply_with_conversation_manager(self, bot_handler):
        """Test ForceReply integration with ConversationManager functionality."""
        user_id = 12345
        user_prompt = "User prompt from ForceReply"

        # Verify conversation manager can handle ForceReply prompts
        bot_handler.conversation_manager.start_followup_conversation(
            user_id, user_prompt
        )

        # Check that conversation was initialized properly
        transcript = bot_handler.conversation_manager.get_transcript(user_id)
        assert len(transcript) >= 1

        # Verify user prompt is in conversation
        user_messages = [msg for msg in transcript if msg["role"] == "user"]
        assert len(user_messages) >= 1
        assert user_messages[0]["content"] == user_prompt

        # Verify conversation state
        assert (
            bot_handler.conversation_manager.is_in_followup_conversation(user_id)
            is True
        )
