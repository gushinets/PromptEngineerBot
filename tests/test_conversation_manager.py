"""Tests for the conversation manager module."""

import pytest

from src.conversation_manager import ConversationManager
from src.state_manager import StateManager


class TestConversationManager:
    """Test cases for ConversationManager class."""

    def _create_manager(self):
        """Helper method to create ConversationManager with required dependencies."""
        return ConversationManager(state_manager=StateManager())

    def test_init(self):
        """Test ConversationManager initialization."""
        manager = self._create_manager()

        assert manager.transcripts == {}
        assert manager.user_prompts == {}
        assert manager.method_selection == {}
        assert manager.current_methods == {}
        assert manager.token_totals == {}

    def test_get_transcript_new_user(self):
        """Test getting transcript for new user."""
        manager = self._create_manager()
        user_id = 12345

        transcript = manager.get_transcript(user_id)

        assert transcript == []
        assert user_id in manager.transcripts

    def test_get_transcript_existing_user(self):
        """Test getting transcript for existing user."""
        manager = self._create_manager()
        user_id = 12345
        manager.transcripts[user_id] = [{"role": "user", "content": "test"}]

        transcript = manager.get_transcript(user_id)

        assert transcript == [{"role": "user", "content": "test"}]

    def test_append_message(self):
        """Test appending message to transcript."""
        manager = self._create_manager()
        user_id = 12345

        manager.append_message(user_id, "user", "Hello")
        manager.append_message(user_id, "assistant", "Hi there")

        transcript = manager.get_transcript(user_id)
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        assert transcript == expected

    def test_reset(self):
        """Test resetting user conversation state."""
        manager = self._create_manager()
        user_id = 12345

        # Set up some state
        manager.append_message(user_id, "user", "test")
        manager.set_user_prompt(user_id, "test prompt")
        manager.set_waiting_for_method(user_id, True)
        manager.set_current_method(user_id, "CRAFT")
        manager.token_totals[user_id] = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

        # Reset
        manager.reset(user_id)

        # Verify reset
        assert manager.transcripts[user_id] == []
        assert manager.user_prompts[user_id] is None
        assert manager.method_selection[user_id] is False
        assert manager.current_methods[user_id] is None
        assert manager.token_totals[user_id] == {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

    def test_set_get_user_prompt(self):
        """Test setting and getting user prompt."""
        manager = self._create_manager()
        user_id = 12345
        prompt = "Test prompt"

        manager.set_user_prompt(user_id, prompt)
        result = manager.get_user_prompt(user_id)

        assert result == prompt

    def test_get_user_prompt_not_set(self):
        """Test getting user prompt when not set."""
        manager = self._create_manager()
        user_id = 12345

        result = manager.get_user_prompt(user_id)

        assert result is None

    def test_set_waiting_for_method(self):
        """Test setting waiting for method flag."""
        manager = self._create_manager()
        user_id = 12345

        manager.set_waiting_for_method(user_id, True)
        assert manager.is_waiting_for_method(user_id) is True

        manager.set_waiting_for_method(user_id, False)
        assert manager.is_waiting_for_method(user_id) is False

    def test_is_waiting_for_method_not_set(self):
        """Test is_waiting_for_method when not set."""
        manager = self._create_manager()
        user_id = 12345

        result = manager.is_waiting_for_method(user_id)

        assert result is False

    def test_set_get_current_method(self):
        """Test setting and getting current method."""
        manager = self._create_manager()
        user_id = 12345
        method = "CRAFT"

        manager.set_current_method(user_id, method)
        result = manager.get_current_method(user_id)

        assert result == method

    def test_get_current_method_not_set(self):
        """Test getting current method when not set."""
        manager = self._create_manager()
        user_id = 12345

        result = manager.get_current_method(user_id)

        assert result == "CUSTOM"

    def test_accumulate_token_usage_new_user(self):
        """Test accumulating token usage for new user."""
        manager = self._create_manager()
        user_id = 12345
        usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}

        manager.accumulate_token_usage(user_id, usage)

        result = manager.get_token_totals(user_id)
        assert result == usage

    def test_accumulate_token_usage_existing_user(self):
        """Test accumulating token usage for existing user."""
        manager = self._create_manager()
        user_id = 12345

        # First usage
        usage1 = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        manager.accumulate_token_usage(user_id, usage1)

        # Second usage
        usage2 = {"prompt_tokens": 5, "completion_tokens": 15, "total_tokens": 20}
        manager.accumulate_token_usage(user_id, usage2)

        result = manager.get_token_totals(user_id)
        expected = {"prompt_tokens": 15, "completion_tokens": 35, "total_tokens": 50}
        assert result == expected

    def test_accumulate_token_usage_none(self):
        """Test accumulating token usage with None."""
        manager = self._create_manager()
        user_id = 12345

        manager.accumulate_token_usage(user_id, None)

        result = manager.get_token_totals(user_id)
        expected = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        assert result == expected

    def test_accumulate_token_usage_missing_keys(self):
        """Test accumulating token usage with missing keys."""
        manager = self._create_manager()
        user_id = 12345
        usage = {"prompt_tokens": 10}  # Missing completion_tokens and total_tokens

        manager.accumulate_token_usage(user_id, usage)

        result = manager.get_token_totals(user_id)
        expected = {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 0}
        assert result == expected

    def test_accumulate_token_usage_invalid_values(self):
        """Test accumulating token usage with invalid values."""
        manager = self._create_manager()
        user_id = 12345
        usage = {
            "prompt_tokens": "invalid",
            "completion_tokens": None,
            "total_tokens": 30,
        }

        # Should not raise exception, just ignore invalid values
        manager.accumulate_token_usage(user_id, usage)

        result = manager.get_token_totals(user_id)
        # The implementation catches all exceptions and ignores malformed usage
        # So all values will be 0 when there are errors
        expected = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        assert result == expected

    def test_get_token_totals_not_set(self):
        """Test getting token totals when not set."""
        manager = self._create_manager()
        user_id = 12345

        result = manager.get_token_totals(user_id)
        expected = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

        assert result == expected

    def test_start_followup_conversation(self):
        """Test starting follow-up conversation with system prompt and improved prompt."""
        manager = self._create_manager()
        user_id = 12345
        improved_prompt = "Test improved prompt"

        # Set up some existing conversation state
        manager.append_message(user_id, "user", "old message")

        # Start follow-up conversation
        manager.start_followup_conversation(user_id, improved_prompt)

        # Verify transcript was reset and new messages added
        transcript = manager.get_transcript(user_id)
        assert len(transcript) == 2

        # Check system message
        assert transcript[0]["role"] == "system"
        assert "промпт-инжинирингу" in transcript[0]["content"]

        # Check improved prompt was added as user message
        assert transcript[1]["role"] == "user"
        assert transcript[1]["content"] == improved_prompt

    def test_start_followup_conversation_file_not_found(self):
        """Test that ConversationManager fails when PromptLoader cannot load required files."""
        from unittest.mock import patch

        import pytest

        user_id = 12345
        improved_prompt = "Test improved prompt"

        # Mock PromptLoader to raise FileNotFoundError during initialization
        with patch("src.conversation_manager.PromptLoader") as mock_prompt_loader_class:
            mock_prompt_loader_class.side_effect = FileNotFoundError(
                "Prompt file not found"
            )

            # ConversationManager should fail to initialize when PromptLoader fails
            with pytest.raises(FileNotFoundError, match="Prompt file not found"):
                self._create_manager()

    def test_init_requires_state_manager(self):
        """Test that ConversationManager requires StateManager."""
        with pytest.raises(ValueError, match="StateManager is required"):
            ConversationManager()

    def test_is_in_followup_conversation_true(self):
        """Test is_in_followup_conversation returns True when in follow-up."""
        manager = self._create_manager()
        user_id = 12345

        # Start follow-up conversation
        manager.start_followup_conversation(user_id, "test prompt")

        # Should return True
        assert manager.is_in_followup_conversation(user_id) is True

    def test_is_in_followup_conversation_false_empty_transcript(self):
        """Test is_in_followup_conversation returns False for empty transcript."""
        manager = self._create_manager()
        user_id = 12345

        # Should return False for empty transcript
        assert manager.is_in_followup_conversation(user_id) is False

    def test_is_in_followup_conversation_false_regular_conversation(self):
        """Test is_in_followup_conversation returns False for regular conversation."""
        manager = self._create_manager()
        user_id = 12345

        # Add regular conversation messages
        manager.append_message(user_id, "system", "Regular system prompt")
        manager.append_message(user_id, "user", "Regular user message")

        # Should return False
        assert manager.is_in_followup_conversation(user_id) is False

    def test_is_in_followup_conversation_false_no_system_message(self):
        """Test is_in_followup_conversation returns False when no system message."""
        manager = self._create_manager()
        user_id = 12345

        # Add user message without system message
        manager.append_message(user_id, "user", "User message")

        # Should return False
        assert manager.is_in_followup_conversation(user_id) is False

    def test_reset_to_followup_ready(self):
        """Test resetting to follow-up ready state."""
        manager = self._create_manager()
        user_id = 12345

        # Set up some conversation state
        manager.append_message(user_id, "user", "test message")
        manager.set_waiting_for_method(user_id, True)
        manager.set_current_method(user_id, "CRAFT")
        manager.token_totals[user_id] = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }

        # Reset to follow-up ready
        manager.reset_to_followup_ready(user_id)

        # Verify conversation was cleared
        assert manager.get_transcript(user_id) == []

        # Verify method selection state was reset
        assert manager.is_waiting_for_method(user_id) is False
        assert manager.get_current_method(user_id) == "CUSTOM"

        # Verify token totals were preserved (not reset)
        expected_tokens = {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        }
        assert manager.get_token_totals(user_id) == expected_tokens

    def test_reset_token_totals(self):
        """Test resetting token totals after logging."""
        manager = self._create_manager()
        user_id = 12345

        # Set up some token totals
        manager.token_totals[user_id] = {
            "prompt_tokens": 100,
            "completion_tokens": 50,
            "total_tokens": 150,
        }

        # Reset token totals
        manager.reset_token_totals(user_id)

        # Verify token totals were reset to zero
        expected_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        assert manager.get_token_totals(user_id) == expected_tokens

    def test_reset_to_followup_ready_new_user(self):
        """Test resetting to follow-up ready state for new user."""
        manager = self._create_manager()
        user_id = 12345

        # Reset for new user (should not raise errors)
        manager.reset_to_followup_ready(user_id)

        # Verify clean state
        assert manager.get_transcript(user_id) == []
        assert manager.is_waiting_for_method(user_id) is False
        assert manager.get_current_method(user_id) == "CUSTOM"
        expected_tokens = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
        assert manager.get_token_totals(user_id) == expected_tokens

    def test_is_in_followup_conversation_with_state_manager(self):
        """Test is_in_followup_conversation with StateManager integration."""
        from src.state_manager import StateManager

        state_manager = StateManager()
        manager = ConversationManager(state_manager=state_manager)
        user_id = 12345

        # Initially should not be in follow-up conversation
        assert not manager.is_in_followup_conversation(user_id)

        # Start follow-up conversation
        manager.start_followup_conversation(user_id, "Test improved prompt")

        # Should now be in follow-up conversation (via StateManager)
        assert manager.is_in_followup_conversation(user_id)

        # Reset should clear the follow-up state
        manager.reset(user_id)
        assert not manager.is_in_followup_conversation(user_id)

    def test_followup_conversation_integration(self):
        """Test complete follow-up conversation flow integration."""
        manager = self._create_manager()
        user_id = 12345
        improved_prompt = "Improved test prompt"

        # Start follow-up conversation
        manager.start_followup_conversation(user_id, improved_prompt)

        # Verify we're in follow-up conversation
        assert manager.is_in_followup_conversation(user_id) is True

        # Add some follow-up conversation messages
        manager.append_message(user_id, "assistant", "What is your target audience?")
        manager.append_message(user_id, "user", "Software developers")

        # Verify messages were added
        transcript = manager.get_transcript(user_id)
        assert len(transcript) == 4  # system + improved_prompt + question + answer

        # Reset to follow-up ready
        manager.reset_to_followup_ready(user_id)

        # Verify conversation was cleared but we're no longer in follow-up
        assert manager.get_transcript(user_id) == []
        assert manager.is_in_followup_conversation(user_id) is False
