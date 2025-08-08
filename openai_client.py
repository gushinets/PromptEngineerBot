import openai
import logging
import asyncio
from typing import List, Dict
from openai import OpenAI, Timeout
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    RetryCallState
)
from datetime import datetime

class OpenAIClient:
    """
    Client for interacting with the OpenAI API for chat completions.
    """
    def __init__(self, api_key: str, model_name: str, max_retries: int = 5, 
                 request_timeout: float = 60.0, max_wait_time: float = 300.0):
        """
        Initialize the OpenAI client.
        
        Args:
            api_key (str): OpenAI API key.
            model_name (str): Model name to use (e.g., 'gpt-4').
            max_retries (int): Maximum number of retry attempts.
            request_timeout (float): Timeout in seconds for each API request.
            max_wait_time (float): Maximum total time to wait for a response including retries.
        """
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.max_wait_time = max_wait_time
        self.client = OpenAI(api_key=api_key)
        self.start_time = None
        self.last_usage = None  # will hold dict with token usage if available

    def _log_retry(self, retry_state: RetryCallState) -> bool:
        """Log retry attempts and check max wait time."""
        if retry_state.attempt_number > 1:
            wait_time = retry_state.idle_for
            total_time = (datetime.now() - self.start_time).total_seconds()
            
            logging.warning(
                f"Retry attempt {retry_state.attempt_number} after {wait_time:.2f}s. "
                f"Total wait time: {total_time:.2f}s"
            )
            
            if total_time > self.max_wait_time:
                logging.error("Max wait time exceeded, giving up.")
                return False
        return True

    def _should_retry(self, retry_state):
        """Check if we should retry the request."""
        if retry_state.outcome.failed:
            return True  # Always retry on exception
        return self._log_retry(retry_state)

    @retry(
        stop=lambda retry_state: stop_after_attempt(retry_state.args[0].max_retries)(retry_state),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((
            TimeoutError,
            ConnectionError,
            openai.APITimeoutError,
            openai.APIConnectionError
        )),
        before_sleep=lambda retry_state: logging.warning(
            f"Retrying (attempt {retry_state.attempt_number}): {retry_state.outcome.exception()}"
        ) if retry_state.attempt_number > 1 else None,
        retry_error_callback=lambda retry_state: logging.error(
            f"Max retries ({retry_state.attempt_number}) reached. Last error: {retry_state.outcome.exception()}"
        )
    )
    async def _call_openai_api(self, messages: List[Dict[str, str]], log_prefix: str = "[OpenAI]") -> tuple:
        """Make the actual API call with retry logic."""
        response = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                timeout=Timeout(self.request_timeout)  # 60-second timeout
            )
        )
        usage = getattr(response, 'usage', None)
        usage_dict = None
        if usage is not None:
            # Convert pydantic-like object to plain dict safely
            usage_dict = {
                'prompt_tokens': getattr(usage, 'prompt_tokens', None),
                'completion_tokens': getattr(usage, 'completion_tokens', None),
                'total_tokens': getattr(usage, 'total_tokens', None),
            }
        return response.choices[0].message.content, usage_dict

    async def send_prompt(self, messages: List[Dict[str, str]], log_prefix: str = "[OpenAI]") -> str:
        """
        Send a list of messages to the OpenAI chat completion API asynchronously.
        
        Args:
            messages: List of message dicts (role/content) for the conversation.
            log_prefix: Prefix for logging.
            
        Returns:
            The assistant's response from OpenAI.
            
        Raises:
            Exception: If the API request fails after all retry attempts.
        """
        logging.info(f"{log_prefix} Sending transcript to OpenAI: {messages}")
        self.start_time = datetime.now()
        
        try:
            response_text, usage = await self._call_openai_api(messages, log_prefix)
            self.last_usage = usage
            
            # Log token usage if available
            if usage:
                logging.info(
                    f"{log_prefix} Token usage - "
                    f"Prompt: {usage.get('prompt_tokens', 'N/A')} tokens, "
                    f"Completion: {usage.get('completion_tokens', 'N/A')} tokens, "
                    f"Total: {usage.get('total_tokens', 'N/A')} tokens"
                )
            
            logging.info(f"{log_prefix} Received response from OpenAI: {response_text}")
            return response_text
            
        except Exception as e:
            total_time = (datetime.now() - self.start_time).total_seconds()
            logging.error(
                f"{log_prefix} OpenAI API request failed after {total_time:.2f}s: {str(e)}"
            )
            raise
