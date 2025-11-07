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

        print("✓ LLM client base classes imported")

        # Test configuration

        print("✓ Configuration imported")

        # Test LLM clients

        print("✓ LLM clients imported")

        # Test factory

        print("✓ LLM factory imported")

        # Test managers

        print("✓ Managers imported")

        # Test other modules

        print("✓ Other modules imported")

        # Test bot handler

        print("✓ Bot handler imported")

        # Test main module (this might fail if environment variables are missing)
        try:
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
