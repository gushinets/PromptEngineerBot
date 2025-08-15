"""
Factory for creating LLM clients based on configuration.
"""

from .config import BotConfig
from .llm_client_base import LLMClientBase
from .openai_client import OpenAIClient
from .openrouter_client import OpenRouterClient


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
            )

        elif config.llm_backend == "OPENROUTER":
            if not config.openrouter_api_key:
                raise ValueError(
                    "OpenRouter API key is required for OpenRouter backend"
                )

            return OpenRouterClient(
                api_key=config.openrouter_api_key,
                model_name=config.model_name,
                timeout=config.openrouter_timeout,
            )

        else:
            raise ValueError(f"Unsupported LLM backend: {config.llm_backend}")
