#!/usr/bin/env python3
"""
Entry point for the Telegram bot.
This script ensures proper module imports and runs the bot.
"""
import sys
import os

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now we can import and run the bot
if __name__ == "__main__":
    from src.main import main
    import asyncio
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Bot crashed: {e}")
        sys.exit(1)