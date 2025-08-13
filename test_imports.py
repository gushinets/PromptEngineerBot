#!/usr/bin/env python3
"""
Test script to verify all imports work correctly.
Run this to check if the refactored imports are working.
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_imports():
    """Test that all modules can be imported correctly."""
    try:
        print("Testing imports...")
        
        # Test base classes
        from src.llm_client_base import LLMClientBase, TokenUsage
        print("✓ LLM client base classes imported")
        
        # Test configuration
        from src.config import BotConfig
        print("✓ Configuration imported")
        
        # Test LLM clients
        from src.openai_client import OpenAIClient
        from src.openrouter_client import OpenRouterClient
        print("✓ LLM clients imported")
        
        # Test factory
        from src.llm_factory import LLMClientFactory
        print("✓ LLM factory imported")
        
        # Test managers
        from src.state_manager import StateManager
        from src.conversation_manager import ConversationManager
        print("✓ Managers imported")
        
        # Test other modules
        from src.messages import WELCOME_MESSAGE
        from src.prompt_loader import PromptLoader
        from src.gsheets_logging import GoogleSheetsHandler
        print("✓ Other modules imported")
        
        # Test bot handler
        from src.bot_handler import BotHandler
        print("✓ Bot handler imported")
        
        # Test main module (this might fail if environment variables are missing)
        try:
            from src.main import main
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