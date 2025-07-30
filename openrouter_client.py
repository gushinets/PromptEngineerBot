import aiohttp
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
            async with session.post(
                self.base_url,
                headers=self.headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logging.error(f"{log_prefix} API request failed: {error_text}")
                    raise Exception(f"API request failed: {error_text}")
                data = await response.json()
                response_text = data['choices'][0]['message']['content']
                logging.info(f"{log_prefix} Received response from model: {response_text}")
                return response_text
