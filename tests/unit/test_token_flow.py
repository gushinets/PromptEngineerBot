#!/usr/bin/env python3
"""
Test script to verify token flow during follow-up transition.
"""

import os
import sys

sys.path.append("src")

from unittest.mock import MagicMock

from src.bot_handler import BotHandler
from src.config import BotConfig
from src.conversation_manager import ConversationManager


def test_token_flow():
    """Test the token flow during follow-up transition."""

    # Create a mock config
    config = BotConfig("test_token", "TEST", "test-model")
    config.bot_id = "test_bot"

    # Create a mock LLM client
    llm_client = MagicMock()

    # Create bot handler
    bot_handler = BotHandler(config, llm_client)

    user_id = 12345

    # Simulate initial optimization phase
    print("=== Initial Optimization Phase ===")

    # Set up initial conversation
    bot_handler.conversation_manager.set_user_prompt(user_id, "Initial prompt")
    bot_handler.conversation_manager.accumulate_token_usage(
        user_id, {"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150}
    )

    print(
        f"Tokens before logging: {bot_handler.conversation_manager.get_token_totals(user_id)}"
    )

    # Mock the sheets logger
    sheets_calls = []

    def mock_sheets_logger(event, payload):
        sheets_calls.append((event, payload))
        print(f"Logged to sheets: {event} - {payload}")

    bot_handler.log_sheets = mock_sheets_logger

    # Log conversation totals (this should reset tokens)
    bot_handler._log_conversation_totals(user_id, "CRAFT", "Optimized prompt")

    print(
        f"Tokens after logging: {bot_handler.conversation_manager.get_token_totals(user_id)}"
    )

    # Call reset_to_followup_ready (this should preserve tokens)
    bot_handler.conversation_manager.reset_to_followup_ready(user_id)

    print(
        f"Tokens after reset_to_followup_ready: {bot_handler.conversation_manager.get_token_totals(user_id)}"
    )

    print("\n=== Follow-up Phase ===")

    # Cache the optimized prompt (simulating what happens in real flow)
    bot_handler.state_manager.set_improved_prompt_cache(user_id, "Optimized prompt")

    # Simulate follow-up conversation
    bot_handler.conversation_manager.accumulate_token_usage(
        user_id, {"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50}
    )

    print(
        f"Tokens after follow-up accumulation: {bot_handler.conversation_manager.get_token_totals(user_id)}"
    )

    # Log follow-up totals with optimized prompt as UserRequest
    optimized_prompt = bot_handler.state_manager.get_improved_prompt_cache(user_id)
    bot_handler._log_conversation_totals(
        user_id, "FOLLOWUP", "Refined prompt", optimized_prompt
    )

    print(
        f"Tokens after follow-up logging: {bot_handler.conversation_manager.get_token_totals(user_id)}"
    )

    print(f"\nTotal sheets calls: {len(sheets_calls)}")
    for i, (event, payload) in enumerate(sheets_calls):
        print(f"Call {i + 1}: {event}")
        print(f"  Method: {payload['OptimizationModel']}")
        print(f"  Tokens: {payload['total_tokens']}")
        print(f"  UserRequest: {payload['UserRequest'][:50]}...")
        print(f"  Answer: {payload['Answer'][:50]}...")


if __name__ == "__main__":
    test_token_flow()
