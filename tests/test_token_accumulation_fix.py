"""
Comprehensive test cases for token usage fixes in follow-up questions feature.
Tests cover initial optimization logging, follow-up session tracking, and proper
Google Sheets payload population according to requirements 7.1-7.7.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from telegram import Update

from src.bot_handler import BotHandler
from src.config import BotConfig


class TestTokenUsageFixes:
    """Comprehensive test cases for token usage fixes in follow-up questions feature."""

    @pytest.fixture
    def bot_handler(self):
        """Create a bot handler for testing."""
        config = BotConfig("test_token", "TEST", "test-model")
        config.bot_id = "test_bot"
        llm_client = MagicMock()
        llm_client.send_prompt = AsyncMock(return_value="Mocked response")
        llm_client.get_last_usage = MagicMock(
            return_value={
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            }
        )
        return BotHandler(config, llm_client)

    @pytest.fixture
    def mock_update(self):
        """Create a mock Update object for testing."""
        update = MagicMock()
        update.effective_user.id = 12345
        update.message = MagicMock()
        update.message.text = "test message"
        update.message.reply_text = AsyncMock(return_value=None)
        return update

    def test_token_preservation_during_followup_transition(self, bot_handler):
        """Test that tokens are preserved during follow-up transition and logged correctly."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Simulate initial optimization phase
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        # Verify tokens are accumulated
        tokens_before_logging = bot_handler.conversation_manager.get_token_totals(
            user_id
        )
        assert tokens_before_logging["total_tokens"] == 150

        # Log initial optimization (this should reset tokens)
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Verify tokens are reset after logging
        tokens_after_logging = bot_handler.conversation_manager.get_token_totals(
            user_id
        )
        assert tokens_after_logging["total_tokens"] == 0

        # Call reset_to_followup_ready (should preserve the already-reset tokens)
        bot_handler.conversation_manager.reset_to_followup_ready(user_id)

        # Verify tokens remain reset
        tokens_after_reset = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_after_reset["total_tokens"] == 0

        # Verify initial optimization was logged correctly
        assert len(sheets_calls) == 1
        initial_call = sheets_calls[0]
        assert initial_call[0] == "conversation_totals"
        assert initial_call[1]["OptimizationModel"] == "CRAFT"
        assert initial_call[1]["UserRequest"] == "Initial prompt"
        assert initial_call[1]["Answer"] == "Optimized prompt"
        assert initial_call[1]["total_tokens"] == 150

    def test_followup_token_logging_with_correct_user_request(self, bot_handler):
        """Test that follow-up tokens are logged with optimized prompt as UserRequest."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Set up initial state
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Optimized prompt")

        # Simulate follow-up conversation tokens
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id, {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50}
        )

        # Log follow-up tokens with optimized prompt as UserRequest
        improved_prompt = bot_handler.state_manager.get_improved_prompt_cache(user_id)
        bot_handler._log_conversation_totals(
            user_id, "FOLLOWUP", "Refined prompt", improved_prompt
        )

        # Verify follow-up was logged correctly
        assert len(sheets_calls) == 1
        followup_call = sheets_calls[0]
        assert followup_call[0] == "conversation_totals"
        assert followup_call[1]["OptimizationModel"] == "FOLLOWUP"
        assert (
            followup_call[1]["UserRequest"] == "Optimized prompt"
        )  # Should be optimized, not initial
        assert followup_call[1]["Answer"] == "Refined prompt"
        assert followup_call[1]["total_tokens"] == 50

    def test_complete_token_flow_initial_and_followup(self, bot_handler):
        """Test complete token flow from initial optimization through follow-up."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # === Initial Optimization Phase ===
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        # Log initial optimization
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Reset for follow-up (preserves already-reset tokens)
        bot_handler.conversation_manager.reset_to_followup_ready(user_id)

        # === Follow-up Phase ===
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Optimized prompt")

        # Accumulate follow-up tokens (starting from zero)
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id, {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50}
        )

        # Log follow-up tokens
        improved_prompt = bot_handler.state_manager.get_improved_prompt_cache(user_id)
        bot_handler._log_conversation_totals(
            user_id, "FOLLOWUP", "Refined prompt", improved_prompt
        )

        # === Verify Results ===
        assert len(sheets_calls) == 2

        # Check initial optimization logging
        initial_call = sheets_calls[0]
        assert initial_call[1]["OptimizationModel"] == "CRAFT"
        assert initial_call[1]["UserRequest"] == "Initial prompt"
        assert initial_call[1]["Answer"] == "Optimized prompt"
        assert initial_call[1]["total_tokens"] == 150

        # Check follow-up logging
        followup_call = sheets_calls[1]
        assert followup_call[1]["OptimizationModel"] == "FOLLOWUP"
        assert followup_call[1]["UserRequest"] == "Optimized prompt"
        assert followup_call[1]["Answer"] == "Refined prompt"
        assert followup_call[1]["total_tokens"] == 50

        # Verify tokens are reset after each logging
        final_tokens = bot_handler.conversation_manager.get_token_totals(user_id)
        assert final_tokens["total_tokens"] == 0

    def test_reset_to_followup_ready_preserves_token_state(self, bot_handler):
        """Test that reset_to_followup_ready preserves token totals without resetting them."""
        user_id = 12345

        # Set up some token totals
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        tokens_before = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_before["total_tokens"] == 150

        # Call reset_to_followup_ready
        bot_handler.conversation_manager.reset_to_followup_ready(user_id)

        # Verify tokens are preserved
        tokens_after = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_after["total_tokens"] == 150

        # Verify other state is reset
        assert bot_handler.conversation_manager.get_transcript(user_id) == []
        assert not bot_handler.conversation_manager.is_waiting_for_method(user_id)
        assert bot_handler.conversation_manager.get_current_method(user_id) == "CUSTOM"

    def test_reset_token_totals_separate_method(self, bot_handler):
        """Test that reset_token_totals method works independently."""
        user_id = 12345

        # Set up some token totals
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        tokens_before = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_before["total_tokens"] == 150

        # Call reset_token_totals
        bot_handler.conversation_manager.reset_token_totals(user_id)

        # Verify tokens are reset
        tokens_after = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_after["total_tokens"] == 0

    # ===== COMPREHENSIVE TOKEN USAGE TESTS =====
    # Tests for requirements 7.1-7.7

    def test_initial_optimization_logs_tokens_exactly_once(self, bot_handler):
        """Test that initial optimization logs tokens exactly once (Requirement 7.1, 7.2)."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Simulate initial optimization phase
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial user prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        # Log initial optimization - should happen exactly once
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Verify exactly one logging call
        assert len(sheets_calls) == 1

        # Verify correct payload structure and content
        call_event, call_payload = sheets_calls[0]
        assert call_event == "conversation_totals"
        assert call_payload["OptimizationModel"] == "CRAFT"
        assert call_payload["UserRequest"] == "Initial user prompt"
        assert call_payload["Answer"] == "Optimized prompt"
        assert call_payload["prompt_tokens"] == 100
        assert call_payload["completion_tokens"] == 50
        assert call_payload["total_tokens"] == 150

        # Verify tokens are reset after logging
        tokens_after = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_after["total_tokens"] == 0

        # Additional calls should not log anything (no tokens accumulated)
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Another prompt")
        assert len(sheets_calls) == 1  # Still only one call

    def test_followup_sessions_start_with_zero_token_counters(self, bot_handler):
        """Test that follow-up sessions start with zero token counters (Requirement 7.4, 7.5)."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # === Initial optimization phase ===
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        # Log initial optimization (this resets tokens)
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Verify tokens are reset after initial logging
        tokens_after_initial = bot_handler.conversation_manager.get_token_totals(
            user_id
        )
        assert tokens_after_initial["total_tokens"] == 0

        # === Follow-up phase starts ===
        # reset_to_followup_ready should preserve the already-reset tokens
        bot_handler.conversation_manager.reset_to_followup_ready(user_id)

        # Verify tokens remain at zero (follow-up starts with clean slate)
        tokens_at_followup_start = bot_handler.conversation_manager.get_token_totals(
            user_id
        )
        assert tokens_at_followup_start["prompt_tokens"] == 0
        assert tokens_at_followup_start["completion_tokens"] == 0
        assert tokens_at_followup_start["total_tokens"] == 0

        # Accumulate follow-up tokens (starting from zero)
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id, {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50}
        )

        # Verify only follow-up tokens are accumulated
        followup_tokens = bot_handler.conversation_manager.get_token_totals(user_id)
        assert followup_tokens["prompt_tokens"] == 30
        assert followup_tokens["completion_tokens"] == 20
        assert followup_tokens["total_tokens"] == 50

    def test_followup_completion_logs_only_followup_session_tokens(self, bot_handler):
        """Test that follow-up completion logs only follow-up session tokens (Requirement 7.6, 7.7)."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # === Complete flow simulation ===
        # Initial optimization
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Follow-up setup
        bot_handler.conversation_manager.reset_to_followup_ready(user_id)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Optimized prompt")

        # Follow-up conversation tokens (only these should be logged)
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id, {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50}
        )

        # Log follow-up completion
        improved_prompt = bot_handler.state_manager.get_improved_prompt_cache(user_id)
        bot_handler._log_conversation_totals(
            user_id, "FOLLOWUP", "Refined prompt", improved_prompt
        )

        # Verify two separate logging calls
        assert len(sheets_calls) == 2

        # Verify initial optimization logging
        initial_call = sheets_calls[0]
        assert initial_call[1]["OptimizationModel"] == "CRAFT"
        assert initial_call[1]["UserRequest"] == "Initial prompt"
        assert initial_call[1]["Answer"] == "Optimized prompt"
        assert initial_call[1]["total_tokens"] == 150

        # Verify follow-up logging (only follow-up session tokens)
        followup_call = sheets_calls[1]
        assert followup_call[1]["OptimizationModel"] == "FOLLOWUP"
        assert (
            followup_call[1]["UserRequest"] == "Optimized prompt"
        )  # Optimized prompt as UserRequest
        assert followup_call[1]["Answer"] == "Refined prompt"
        assert followup_call[1]["prompt_tokens"] == 30  # Only follow-up tokens
        assert followup_call[1]["completion_tokens"] == 20  # Only follow-up tokens
        assert followup_call[1]["total_tokens"] == 50  # Only follow-up tokens, not 200

    def test_declining_followup_no_additional_logging(self, bot_handler, mock_update):
        """Test that declining follow-up doesn't cause additional logging (Requirement 7.3)."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # === Initial optimization phase ===
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )

        # Log initial optimization
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Verify initial logging happened
        assert len(sheets_calls) == 1
        assert sheets_calls[0][1]["total_tokens"] == 150

        # === User declines follow-up ===
        # Set up follow-up choice state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        mock_update.effective_user.id = user_id
        mock_update.message.text = "❌НЕТ"  # User declines

        # Handle decline choice (should not cause additional logging)
        # We'll test this by directly calling the state management methods
        # that _handle_followup_choice would call for НЕТ choice
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, False)
        bot_handler.state_manager.set_waiting_for_prompt(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, None)
        bot_handler.conversation_manager.reset(user_id)

        # Verify no additional logging occurred
        assert len(sheets_calls) == 1  # Still only the initial logging

        # Verify user state is reset properly
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert not user_state.waiting_for_followup_choice
        assert not user_state.in_followup_conversation
        assert user_state.waiting_for_prompt

    def test_google_sheets_payload_fields_correctly_populated(self, bot_handler):
        """Test that all Google Sheets payload fields are correctly populated (Requirement 7.1, 7.2, 7.6, 7.7)."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Test initial optimization payload
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 75, "completion_tokens": 25, "total_tokens": 100},
        )

        bot_handler._log_conversation_totals(user_id, "LYRA", "Test optimized prompt")

        # Verify initial optimization payload
        initial_payload = sheets_calls[0][1]
        expected_initial_fields = {
            "BotID": "test_bot",
            "TelegramID": user_id,
            "LLM": "TEST:test-model",
            "OptimizationModel": "LYRA",
            "UserRequest": "Test initial prompt",
            "Answer": "Test optimized prompt",
            "prompt_tokens": 75,
            "completion_tokens": 25,
            "total_tokens": 100,
        }

        for field, expected_value in expected_initial_fields.items():
            assert initial_payload[field] == expected_value, f"Field {field} mismatch"

        # Test follow-up payload
        bot_handler.conversation_manager.reset_to_followup_ready(user_id)
        bot_handler.state_manager.set_improved_prompt_cache(
            user_id, "Test optimized prompt"
        )

        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 40, "completion_tokens": 35, "total_tokens": 75},
        )

        improved_prompt = bot_handler.state_manager.get_improved_prompt_cache(user_id)
        bot_handler._log_conversation_totals(
            user_id, "FOLLOWUP", "Test refined prompt", improved_prompt
        )

        # Verify follow-up payload
        followup_payload = sheets_calls[1][1]
        expected_followup_fields = {
            "BotID": "test_bot",
            "TelegramID": user_id,
            "LLM": "TEST:test-model",
            "OptimizationModel": "FOLLOWUP",
            "UserRequest": "Test optimized prompt",  # Optimized prompt as UserRequest
            "Answer": "Test refined prompt",
            "prompt_tokens": 40,
            "completion_tokens": 35,
            "total_tokens": 75,
        }

        for field, expected_value in expected_followup_fields.items():
            assert followup_payload[field] == expected_value, f"Field {field} mismatch"

    def test_no_logging_with_zero_tokens(self, bot_handler):
        """Test that no logging occurs when token totals are zero."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Try to log with zero tokens
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Some prompt")

        # Verify no logging occurred
        assert len(sheets_calls) == 0

        # Set up zero tokens explicitly
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )

        bot_handler._log_conversation_totals(user_id, "CRAFT", "Some prompt")

        # Verify still no logging occurred
        assert len(sheets_calls) == 0

    def test_token_logging_error_handling(self, bot_handler):
        """Test that token logging errors don't affect normal operation."""
        user_id = 12345

        def failing_sheets_logger(event, payload):
            raise Exception("Simulated logging failure")

        bot_handler.log_sheets = failing_sheets_logger

        # Set up tokens
        bot_handler.conversation_manager.set_user_prompt(user_id, "Test prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 50, "completion_tokens": 25, "total_tokens": 75},
        )

        # This should not raise an exception despite logging failure
        try:
            bot_handler._log_conversation_totals(user_id, "CRAFT", "Test answer")
        except Exception:
            pytest.fail("Token logging error should be handled gracefully")

        # Verify tokens are NOT reset after logging failure (to preserve data)
        tokens_after = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_after["total_tokens"] == 75  # Tokens should be preserved

    def test_multiple_method_names_logged_correctly(self, bot_handler):
        """Test that different optimization methods are logged with correct names."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Test different method names
        methods_to_test = ["CRAFT", "LYRA", "GGL", "FOLLOWUP"]

        for i, method in enumerate(methods_to_test):
            # Reset and set up tokens
            bot_handler.conversation_manager.accumulate_token_usage(
                user_id,
                {
                    "prompt_tokens": 10 + i,
                    "completion_tokens": 5 + i,
                    "total_tokens": 15 + i,
                },
            )

            bot_handler._log_conversation_totals(user_id, method, f"Answer {i}")

        # Verify all methods were logged correctly
        assert len(sheets_calls) == len(methods_to_test)

        for i, method in enumerate(methods_to_test):
            payload = sheets_calls[i][1]
            assert payload["OptimizationModel"] == method
            assert payload["total_tokens"] == 15 + i

    @pytest.mark.asyncio
    async def test_handle_followup_choice_decline_no_logging(
        self, bot_handler, mock_update
    ):
        """Test that _handle_followup_choice with НЕТ doesn't cause additional logging."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Set up initial optimization and logging
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Set up follow-up choice state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Optimized prompt")

        # Verify initial logging happened
        assert len(sheets_calls) == 1

        # Handle НЕТ choice
        mock_update.effective_user.id = user_id
        mock_update.message.text = "❌НЕТ"

        await bot_handler._handle_followup_choice(mock_update, user_id, "❌НЕТ")

        # Verify no additional logging occurred
        assert len(sheets_calls) == 1  # Still only the initial logging

        # Verify state is properly reset
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert not user_state.waiting_for_followup_choice
        assert user_state.waiting_for_prompt
        assert bot_handler.state_manager.get_improved_prompt_cache(user_id) is None

    @pytest.mark.asyncio
    async def test_handle_followup_choice_accept_resets_tokens(
        self, bot_handler, mock_update
    ):
        """Test that _handle_followup_choice with ДА resets token counters for new session."""
        user_id = 12345
        sheets_calls = []

        def mock_sheets_logger(event, payload):
            sheets_calls.append((event, payload))

        bot_handler.log_sheets = mock_sheets_logger

        # Set up initial optimization and logging
        bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
        bot_handler.conversation_manager.accumulate_token_usage(
            user_id,
            {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        )
        bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

        # Set up follow-up choice state
        bot_handler.state_manager.set_waiting_for_followup_choice(user_id, True)
        bot_handler.state_manager.set_improved_prompt_cache(user_id, "Optimized prompt")

        # Verify tokens are reset after initial logging
        tokens_before_followup = bot_handler.conversation_manager.get_token_totals(
            user_id
        )
        assert tokens_before_followup["total_tokens"] == 0

        # Mock the LLM processing to avoid actual LLM calls
        original_process_with_llm = bot_handler._process_with_llm
        bot_handler._process_with_llm = AsyncMock()

        # Handle ДА choice
        mock_update.effective_user.id = user_id
        mock_update.message.text = "✅ДА"

        await bot_handler._handle_followup_choice(mock_update, user_id, "✅ДА")

        # Verify tokens remain at zero (ready for follow-up accumulation)
        tokens_after_accept = bot_handler.conversation_manager.get_token_totals(user_id)
        assert tokens_after_accept["total_tokens"] == 0

        # Verify state is properly set for follow-up conversation
        user_state = bot_handler.state_manager.get_user_state(user_id)
        assert not user_state.waiting_for_followup_choice
        assert user_state.in_followup_conversation

        # Restore original method
        bot_handler._process_with_llm = original_process_with_llm
