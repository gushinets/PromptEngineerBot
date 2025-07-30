import openai
import logging

class OpenAIClient:
    """
    Client for interacting with the OpenAI API for chat completions.
    """
    def __init__(self, api_key: str, model_name: str):
        """
        Initialize the OpenAI client.
        Args:
            api_key (str): OpenAI API key.
            model_name (str): Model name to use (e.g., 'gpt-4o').
        """
        self.api_key = api_key
        self.model_name = model_name
        openai.api_key = api_key

    async def send_prompt(self, messages, log_prefix="[OpenAI]") -> str:
        """
        Send a list of messages to the OpenAI chat completion API asynchronously.
        Args:
            messages (list): List of message dicts (role/content) for the conversation.
            log_prefix (str): Prefix for logging.
        Returns:
            str: The assistant's response from OpenAI.
        Raises:
            Exception: If the API request fails.
        """
        logging.info(f"{log_prefix} Sending transcript to OpenAI: {messages}")
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            # Use the new API for openai>=1.0.0
            response = await loop.run_in_executor(
                None,
                lambda: openai.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
            )
            response_text = response.choices[0].message.content
            logging.info(f"{log_prefix} Received response from OpenAI: {response_text}")
            return response_text
        except Exception as e:
            logging.error(f"{log_prefix} OpenAI API request failed: {e}")
            raise
