"""
Abstract base class for LLM clients to ensure consistent interface.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

class TokenUsage:
    """Standardized token usage tracking."""

    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


class LLMClientBase(ABC):
    """Abstract base class for all LLM clients."""

    def __init__(self, api_key: str, model_name: str):
        self.api_key = api_key
        self.model_name = model_name
        self.last_usage: TokenUsage | None = None
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    async def send_prompt(self, messages: list[dict[str, str]], log_prefix: str = "") -> str:
        """
        Send messages to the LLM and return the response.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            log_prefix: Optional prefix for logging

        Returns:
            The LLM's response text

        Raises:
            Exception: If the request fails after retries
        """

    @abstractmethod
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        audio_format: Optional[str] = "ogg",
        transcription_model: Optional[str] = None,
        log_prefix: str = "",
    ) -> str:
        """
        Transcribe audio to text using the LLM.

        Args:
            audio_bytes: Raw audio data in bytes
            audio_format: Audio format (default: "ogg")
            transcription_model: Specific model for transcription (optional)
            log_prefix: Optional prefix for logging

        Returns:
            Transcribed text

        Raises:
            TranscriptionNotSupportedError: If model doesn't support transcription
            CountryRegionTerritoryNotSupportedError: If country restrictions apply
            TranscriptionProviderNotSupportedError: If provider not supported
            Exception: For other transcription errors
        """

    def get_last_usage(self) -> dict[str, int] | None:
        """Get the last token usage as a dict for backward compatibility."""
        return self.last_usage.to_dict() if self.last_usage else None
