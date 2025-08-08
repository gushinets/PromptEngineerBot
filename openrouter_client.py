import aiohttp
import asyncio
import logging

class OpenRouterClient:
    """
    Client for interacting with the OpenRouter API for chat completions.
    """
    def __init__(self, api_key: str, model_name: str):
        """
        Initialize the OpenRouter client.
        Args:
            api_key (str): OpenRouter API key.
            model_name (str): Model name to use (e.g., 'openai/gpt-4').
        """
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/", # Replace with your actual domain
            "Content-Type": "application/json"
        }
        self.last_usage = None  # dict with token usage if available

    async def send_prompt(self, prompt: str = None, system_prompt: str = None, log_prefix: str = "", messages=None) -> str:
        """
        Send a prompt or list of messages to the OpenRouter chat completion API asynchronously.
        Args:
            prompt (str, optional): User prompt if not using messages.
            system_prompt (str, optional): System prompt if not using messages.
            log_prefix (str): Prefix for logging.
            messages (list, optional): List of message dicts (role/content) for the conversation.
        Returns:
            str: The assistant's response from OpenRouter.
        Raises:
            Exception: If the API request fails.
        """
        # If messages is provided, use it directly
        if messages is not None:
            payload = {
                "model": self.model_name,
                "messages": messages
            }
            logging.info(f"{log_prefix} Sending transcript to model: {messages}")
        else:
            # Fallback to old behavior
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            if prompt:
                messages.append({"role": "user", "content": prompt})
            payload = {
                "model": self.model_name,
                "messages": messages
            }
            logging.info(f"{log_prefix} Sending prompt to model: {prompt}")

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
                        # Save usage for external logging
                        self.last_usage = {
                            'prompt_tokens': usage.get('prompt_tokens'),
                            'completion_tokens': usage.get('completion_tokens'),
                            'total_tokens': usage.get('total_tokens'),
                        }
                        logging.info(
                            f"{log_prefix} Token usage - "
                            f"Prompt: {usage.get('prompt_tokens', 'N/A')} tokens, "
                            f"Completion: {usage.get('completion_tokens', 'N/A')} tokens, "
                            f"Total: {usage.get('total_tokens', 'N/A')} tokens"
                        )
                    
                    logging.info(f"{log_prefix} Received response from model: {response_text}")
                    return response_text

            # Respect an optional self.timeout (aiohttp.ClientTimeout or seconds) using asyncio.wait_for
            timeout_seconds = None
            if hasattr(self, 'timeout') and self.timeout is not None:
                t = self.timeout
                timeout_seconds = getattr(t, 'total', None) if not isinstance(t, (int, float)) else t
            if timeout_seconds:
                return await asyncio.wait_for(_do_request(), timeout=timeout_seconds)
            return await _do_request()
