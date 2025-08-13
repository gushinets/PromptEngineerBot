import aiohttp
import asyncio
import logging
from typing import List, Dict

from .llm_client_base import LLMClientBase, TokenUsage

class OpenRouterClient(LLMClientBase):
    """
    Client for interacting with the OpenRouter API for chat completions.
    """
    def __init__(self, api_key: str, model_name: str, timeout: float = 60.0):
        """
        Initialize the OpenRouter client.
        Args:
            api_key (str): OpenRouter API key.
            model_name (str): Model name to use (e.g., 'openai/gpt-4').
            timeout (float): Request timeout in seconds.
        """
        super().__init__(api_key, model_name)
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/", # Replace with your actual domain
            "Content-Type": "application/json"
        }

    async def send_prompt(self, messages: List[Dict[str, str]], log_prefix: str = "") -> str:
        """
        Send messages to the OpenRouter chat completion API asynchronously.
        Args:
            messages: List of message dicts with 'role' and 'content' keys
            log_prefix: Optional prefix for logging
        Returns:
            str: The assistant's response from OpenRouter.
        Raises:
            Exception: If the API request fails.
        """
        payload = {
            "model": self.model_name,
            "messages": messages
        }
        self.logger.info(f"{log_prefix} Sending transcript to model: {messages}")

        async with aiohttp.ClientSession() as session:
            async def _do_request():
                # Support both real session.post (async CM) and AsyncMock returning coroutine in tests
                post_result = session.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload
                )
                # If the result is an async context manager, use it; otherwise await it and wrap
                if hasattr(post_result, "__aenter__"):
                    response_cm = post_result
                else:
                    response_obj = await post_result
                    class _ResponseWrapper:
                        def __init__(self, resp):
                            self._resp = resp
                        async def __aenter__(self):
                            return self._resp
                        async def __aexit__(self, exc_type, exc, tb):
                            return False
                    response_cm = _ResponseWrapper(response_obj)

                async with response_cm as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logging.error(f"{log_prefix} API request failed: {error_text}")
                        raise Exception(f"API request failed: {error_text}")
                    data = await response.json()
                    response_text = data['choices'][0]['message']['content']
                    
                    # Log token usage if available
                    if 'usage' in data:
                        usage = data['usage']
                        self.last_usage = TokenUsage(
                            prompt_tokens=usage.get('prompt_tokens', 0),
                            completion_tokens=usage.get('completion_tokens', 0),
                            total_tokens=usage.get('total_tokens', 0)
                        )
                        self.logger.info(
                            f"{log_prefix} Token usage - "
                            f"Prompt: {self.last_usage.prompt_tokens} tokens, "
                            f"Completion: {self.last_usage.completion_tokens} tokens, "
                            f"Total: {self.last_usage.total_tokens} tokens"
                        )
                    
                    self.logger.info(f"{log_prefix} Received response from model: {response_text}")
                    return response_text

            return await asyncio.wait_for(_do_request(), timeout=self.timeout)


