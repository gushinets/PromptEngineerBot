#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.
Run this to check if the refactored imports are working.
"""

import os
import sys

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


def test_imports():
    """Test that all modules can be imported correctly."""
    try:
        print("Testing imports...")

        # Test base classes
        from telegram_bot.services.llm.base import LLMClientBase, TokenUsage

        print("✓ LLM client base classes imported")

        # Test configuration
        from telegram_bot.utils.config import BotConfig

        print("✓ Configuration imported")

        # Test LLM clients
        from telegram_bot.services.llm.openai_client import OpenAIClient
        from telegram_bot.services.llm.openrouter_client import OpenRouterClient

        print("✓ LLM clients imported")

        # Test factory
        from telegram_bot.services.llm.factory import LLMClientFactory

        print("✓ LLM factory imported")

        # Test managers
        from telegram_bot.core.conversation_manager import ConversationManager
        from telegram_bot.core.state_manager import StateManager

        print("✓ Managers imported")

        # Test other modules
        from telegram_bot.services.gsheets_logging import GoogleSheetsHandler
        from telegram_bot.utils.messages import WELCOME_MESSAGE
        from telegram_bot.utils.prompt_loader import PromptLoader

        print("✓ Other modules imported")

        # Test bot handler
        from telegram_bot.core.bot_handler import BotHandler

        print("✓ Bot handler imported")

        # Test main module (this might fail if environment variables are missing)
        try:
            from telegram_bot.main import main

            print("✓ Main module imported")
        except ValueError as e:
            if "environment variable" in str(e).lower():
                print("⚠ Main module import failed due to missing env vars (expected)")
            else:
                raise

        print("\n🎉 All imports successful!")
        return True

    except Exception as e:
        print(f"\n❌ Import failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)
