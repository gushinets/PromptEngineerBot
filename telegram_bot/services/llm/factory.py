"""
Factory for creating LLM clients based on configuration.
"""

from telegram_bot.services.llm.base import LLMClientBase
from telegram_bot.services.llm.openai_client import OpenAIClient
from telegram_bot.services.llm.openrouter_client import OpenRouterClient
from telegram_bot.utils.config import BotConfig


class LLMClientFactory:
    """Factory for creating LLM clients."""

    @staticmethod
    def create_client(config: BotConfig) -> LLMClientBase:
        """
        Create an LLM client based on the configuration.

        Args:
            config: Bot configuration

        Returns:
            Configured LLM client

        Raises:
            ValueError: If backend is not supported or configuration is invalid
        """
        if config.llm_backend == "OPENAI":
            if not config.openai_api_key:
                raise ValueError("OpenAI API key is required for OpenAI backend")

            return OpenAIClient(
                api_key=config.openai_api_key,
                model_name=config.model_name,
                max_retries=config.openai_max_retries,
                request_timeout=config.openai_request_timeout,
                max_wait_time=config.openai_max_wait_time,
                transcription_api_name=(
                    config.openai_api_key),
                transcription_model_name=(
                    config.openai_model_transcription)
                )

        if config.llm_backend == "OPENROUTER":
            if not config.openrouter_api_key:
                raise ValueError("OpenRouter API key is required for OpenRouter backend")

            return OpenRouterClient(
                api_key=config.openrouter_api_key,
                model_name=config.model_name,
                timeout=config.openrouter_timeout,
                transcription_api_name=(
                    config.openrouter_api_key
                ),
                transcription_model_name=(
                    config.bot_model_for_transcription
                ),
            )

        raise ValueError(f"Unsupported LLM backend: {config.llm_backend}")
