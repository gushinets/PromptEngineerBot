"""Tests for the conversation manager module."""
import pytest

from src.conversation_manager import ConversationManager


class TestConversationManager:
    """Test cases for ConversationManager class."""

    def test_init(self):
        """Test ConversationManager initialization."""
        manager = ConversationManager()
        
        assert manager.transcripts == {}
        assert manager.user_prompts == {}
        assert manager.method_selection == {}
        assert manager.current_methods == {}
        assert manager.token_totals == {}

    def test_get_transcript_new_user(self):
        """Test getting transcript for new user."""
        manager = ConversationManager()
        user_id = 12345
        
        transcript = manager.get_transcript(user_id)
        
        assert transcript == []
        assert user_id in manager.transcripts

    def test_get_transcript_existing_user(self):
        """Test getting transcript for existing user."""
        manager = ConversationManager()
        user_id = 12345
        manager.transcripts[user_id] = [{"role": "user", "content": "test"}]
        
        transcript = manager.get_transcript(user_id)
        
        assert transcript == [{"role": "user", "content": "test"}]

    def test_append_message(self):
        """Test appending message to transcript."""
        manager = ConversationManager()
        user_id = 12345
        
        manager.append_message(user_id, "user", "Hello")
        manager.append_message(user_id, "assistant", "Hi there")
        
        transcript = manager.get_transcript(user_id)
        expected = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"}
        ]
        
        assert transcript == expected

    def test_reset(self):
        """Test resetting user conversation state."""
        manager = ConversationManager()
        user_id = 12345
        
        # Set up some state
        manager.append_message(user_id, "user", "test")
        manager.set_user_prompt(user_id, "test prompt")
        manager.set_waiting_for_method(user_id, True)
        manager.set_current_method(user_id, "CRAFT")
        manager.token_totals[user_id] = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        
        # Reset
        manager.reset(user_id)
        
        # Verify reset
        assert manager.transcripts[user_id] == []
        assert manager.user_prompts[user_id] is None
        assert manager.method_selection[user_id] is False
        assert manager.current_methods[user_id] is None
        assert manager.token_totals[user_id] == {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    def test_set_get_user_prompt(self):
        """Test setting and getting user prompt."""
        manager = ConversationManager()
        user_id = 12345
        prompt = "Test prompt"
        
        manager.set_user_prompt(user_id, prompt)
        result = manager.get_user_prompt(user_id)
        
        assert result == prompt

    def test_get_user_prompt_not_set(self):
        """Test getting user prompt when not set."""
        manager = ConversationManager()
        user_id = 12345
        
        result = manager.get_user_prompt(user_id)
        
        assert result is None

    def test_set_waiting_for_method(self):
        """Test setting waiting for method flag."""
        manager = ConversationManager()
        user_id = 12345
        
        manager.set_waiting_for_method(user_id, True)
        assert manager.is_waiting_for_method(user_id) is True
        
        manager.set_waiting_for_method(user_id, False)
        assert manager.is_waiting_for_method(user_id) is False

    def test_is_waiting_for_method_not_set(self):
        """Test is_waiting_for_method when not set."""
        manager = ConversationManager()
        user_id = 12345
        
        result = manager.is_waiting_for_method(user_id)
        
        assert result is False

    def test_set_get_current_method(self):
        """Test setting and getting current method."""
        manager = ConversationManager()
        user_id = 12345
        method = "CRAFT"
        
        manager.set_current_method(user_id, method)
        result = manager.get_current_method(user_id)
        
        assert result == method

    def test_get_current_method_not_set(self):
        """Test getting current method when not set."""
        manager = ConversationManager()
        user_id = 12345
        
        result = manager.get_current_method(user_id)
        
        assert result == 'CUSTOM'

    def test_accumulate_token_usage_new_user(self):
        """Test accumulating token usage for new user."""
        manager = ConversationManager()
        user_id = 12345
        usage = {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        
        manager.accumulate_token_usage(user_id, usage)
        
        result = manager.get_token_totals(user_id)
        assert result == usage

    def test_accumulate_token_usage_existing_user(self):
        """Test accumulating token usage for existing user."""
        manager = ConversationManager()
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
        manager = ConversationManager()
        user_id = 12345
        
        manager.accumulate_token_usage(user_id, None)
        
        result = manager.get_token_totals(user_id)
        expected = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        assert result == expected

    def test_accumulate_token_usage_missing_keys(self):
        """Test accumulating token usage with missing keys."""
        manager = ConversationManager()
        user_id = 12345
        usage = {"prompt_tokens": 10}  # Missing completion_tokens and total_tokens
        
        manager.accumulate_token_usage(user_id, usage)
        
        result = manager.get_token_totals(user_id)
        expected = {"prompt_tokens": 10, "completion_tokens": 0, "total_tokens": 0}
        assert result == expected

    def test_accumulate_token_usage_invalid_values(self):
        """Test accumulating token usage with invalid values."""
        manager = ConversationManager()
        user_id = 12345
        usage = {"prompt_tokens": "invalid", "completion_tokens": None, "total_tokens": 30}
        
        # Should not raise exception, just ignore invalid values
        manager.accumulate_token_usage(user_id, usage)
        
        result = manager.get_token_totals(user_id)
        # The implementation catches all exceptions and ignores malformed usage
        # So all values will be 0 when there are errors
        expected = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        assert result == expected

    def test_get_token_totals_not_set(self):
        """Test getting token totals when not set."""
        manager = ConversationManager()
        user_id = 12345
        
        result = manager.get_token_totals(user_id)
        expected = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        
        assert result == expected