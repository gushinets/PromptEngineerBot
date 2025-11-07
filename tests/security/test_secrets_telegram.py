# Test file for GitLeaks secrets detection - Telegram tokens
# This file intentionally contains sample secrets for validation
# DO NOT USE THESE TOKENS IN PRODUCTION

# Sample Telegram Bot Token (fake but valid format)
TELEGRAM_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz1234567890"

# Another format
bot_token = "987654321:ZYXwvuTSRqponMLKjihGFEdcba0987654321"


def get_telegram_config():
    """Example function with hardcoded token"""
    return {
        "token": "555555555:AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRr",
        "webhook_url": "https://example.com/webhook",
    }
