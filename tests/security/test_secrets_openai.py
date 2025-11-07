# Test file for GitLeaks secrets detection - OpenAI API keys
# This file intentionally contains sample secrets for validation
# DO NOT USE THESE KEYS IN PRODUCTION

# Sample OpenAI API Key (fake but valid format)
OPENAI_API_KEY = "sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKL"

# Another example
openai_key = "sk-ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrst"


def initialize_openai():
    """Example function with hardcoded API key"""
    api_key = "sk-ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZzz"
    return api_key
