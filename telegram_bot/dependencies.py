"""
Dependency injection container for managing shared instances.
"""

from typing import Optional

from telegram_bot.core.conversation_manager import ConversationManager
from telegram_bot.core.state_manager import StateManager
from telegram_bot.services.llm.base import LLMClientBase
from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.prompt_loader import PromptLoader


class DependencyContainer:
    """Container for managing shared instances across the application."""

    def __init__(self):
        self._state_manager: Optional[StateManager] = None
        self._prompt_loader: Optional[PromptLoader] = None
        self._conversation_manager: Optional[ConversationManager] = None

    def get_state_manager(self) -> StateManager:
        """Get or create StateManager instance."""
        if self._state_manager is None:
            self._state_manager = StateManager()
        return self._state_manager

    def get_prompt_loader(self) -> PromptLoader:
        """Get or create PromptLoader instance."""
        if self._prompt_loader is None:
            self._prompt_loader = PromptLoader()
        return self._prompt_loader

    def get_conversation_manager(self) -> ConversationManager:
        """Get or create ConversationManager instance."""
        if self._conversation_manager is None:
            self._conversation_manager = ConversationManager(
                self.get_prompt_loader(), self.get_state_manager()
            )
        return self._conversation_manager

    def reset(self):
        """Reset all instances (useful for testing)."""
        self._state_manager = None
        self._prompt_loader = None
        self._conversation_manager = None

    def create_fresh_instances(self):
        """Create fresh instances, replacing any existing ones."""
        self._state_manager = StateManager()
        self._prompt_loader = PromptLoader()
        self._conversation_manager = ConversationManager(
            self._prompt_loader, self._state_manager
        )


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container."""
    global _container
    if _container is None:
        _container = DependencyContainer()
    return _container


def reset_container():
    """Reset the global container (useful for testing)."""
    global _container
    _container = None


def create_fresh_container():
    """Create a fresh container with new instances."""
    global _container
    _container = DependencyContainer()
    _container.create_fresh_instances()
    return _container


def reset_all_globals():
    """Reset all global state for testing."""
    reset_container()

    # Reset email flow orchestrator
    try:
        from telegram_bot.flows import email_flow

        email_flow.email_flow_orchestrator = None
    except ImportError:
        pass
