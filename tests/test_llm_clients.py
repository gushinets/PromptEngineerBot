"""Tests for LLM client implementations."""
import asyncio
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from openai.types.chat import ChatCompletion, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice

# Import the clients to test
from openai_client import OpenAIClient
from openrouter_client import OpenRouterClient

class TestOpenAIClient:
    """Test cases for the OpenAI client."""
    
    @pytest.fixture
    def mock_openai_response(self):
        """Create a mock OpenAI response."""
        return {
            "choices": [{
                "message": {
                    "content": "Mocked OpenAI response",
                    "role": "assistant"
                },
                "finish_reason": "stop",
                "index": 0
            }]
        }
    
    @pytest.mark.asyncio
    async def test_send_prompt_success(self, mock_openai_response):
        """Test successful prompt sending to OpenAI."""
        with patch('openai.resources.chat.completions.AsyncCompletions.create') as mock_create:
            # Mock the response
            mock_create.return_value = ChatCompletion(
                id="test-id",
                model="gpt-4",
                choices=[
                    Choice(
                        finish_reason="stop",
                        index=0,
                        message=ChatCompletionMessage(
                            content="Mocked response",
                            role="assistant"
                        )
                    )
                ],
                created=1234567890,
                object="chat.completion"
            )
            
            # Initialize client and send prompt
            client = OpenAIClient(
                api_key="test-key",
                model_name="gpt-4",
                max_retries=5,
                request_timeout=60.0,
                max_wait_time=300.0
            )
            messages = [{"role": "user", "content": "Test prompt"}]
            response = await client.send_prompt(messages)
            
            # Verify the response
            assert response == "Mocked response"
            mock_create.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_send_prompt_timeout(self):
        """Test timeout handling in OpenAI client."""
        with patch('openai.resources.chat.completions.AsyncCompletions.create', 
                 side_effect=asyncio.TimeoutError("API timeout")):
            
            client = OpenAIClient(
                api_key="test-key",
                model_name="gpt-4",
                max_retries=5,
                request_timeout=60.0,
                max_wait_time=300.0
            )
            messages = [{"role": "user", "content": "Test prompt"}]
            
            with pytest.raises(Exception) as exc_info:
                await client.send_prompt(messages)
            
            assert "timeout" in str(exc_info.value).lower()

class TestOpenRouterClient:
    """Test cases for the OpenRouter client."""
    
    @pytest.fixture
    def mock_openrouter_response(self):
        """Create a mock OpenRouter response."""
        return {
            "choices": [{
                "message": {
                    "content": "Mocked OpenRouter response",
                    "role": "assistant"
                }
            }]
        }
    
    @pytest.mark.asyncio
    async def test_send_prompt_success(self, mock_openrouter_response):
        """Test successful prompt sending to OpenRouter."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock the response
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.json = AsyncMock(return_value=mock_openrouter_response)
            mock_post.return_value.__aenter__.return_value = mock_response
            
            # Initialize client and send prompt
            client = OpenRouterClient(api_key="test-key", model_name="openai/gpt-4")
            messages = [{"role": "user", "content": "Test prompt"}]
            response = await client.send_prompt(messages)
            
            # Verify the response
            assert response == "Mocked OpenRouter response"
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_prompt_http_error(self):
        """Test HTTP error handling in OpenRouter client."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # Mock an HTTP error response
            mock_response = MagicMock()
            mock_response.status = 429
            mock_response.text = AsyncMock(return_value="Rate limit exceeded")
            mock_post.return_value.__aenter__.return_value = mock_response
            
            client = OpenRouterClient(api_key="test-key", model_name="openai/gpt-4")
            messages = [{"role": "user", "content": "Test prompt"}]
            
            with pytest.raises(Exception) as exc_info:
                await client.send_prompt(messages)
            
            assert "429" in str(exc_info.value)
            assert "Rate limit" in str(exc_info.value)

class TestLLMClientIntegration:
    """Integration tests for LLM clients with network simulation."""
    
    @pytest.mark.asyncio
    async def test_client_timeout_handling(self, mocker):
        """Test that clients properly handle timeouts."""
        # Skip this test in CI environment as it requires network access
        if os.getenv('CI'):
            pytest.skip("Skipping network test in CI environment")
            
        # Test with both client types
        test_cases = [
            (OpenAIClient, {"api_key": "test-key", "model_name": "gpt-4"}),
            (OpenRouterClient, {"api_key": "test-key", "model_name": "openai/gpt-4"})
        ]
        
        for client_class, client_kwargs in test_cases:
            # Create a mock response that will sleep to simulate timeout
            async def mock_post(*args, **kwargs):
                await asyncio.sleep(2)  # Sleep longer than the timeout
                return MagicMock(status=200, json=AsyncMock(return_value={
                    "choices": [{"message": {"content": "Slow response", "role": "assistant"}}]
                }))
            
            # Patch the client's session to use our mock
            with patch('aiohttp.ClientSession.post', new=AsyncMock(side_effect=mock_post)) as mock_post:
                try:
                    # Configure client with a short timeout
                    client = client_class(**client_kwargs)
                    if hasattr(client, 'api_base'):  # For OpenRouterClient
                        client.api_base = "http://localhost:8080/v1"
                    
                    # Set a short timeout
                    client.timeout = aiohttp.ClientTimeout(total=0.1)
                    
                    # Test that timeout is properly raised
                    with pytest.raises(asyncio.TimeoutError):
                        await client.send_prompt([{"role": "user", "content": "Test timeout"}])
                        
                except Exception as e:
                    if "Timeout" not in str(e):
                        raise  # Re-raise if it's not a timeout error
