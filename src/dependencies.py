"""
Dependency injection container for managing shared instances.

Bridges legacy container calls to the new `promptbot.app.container.AppContainer`.
"""

from typing import Optional

from promptbot.app.container import AppContainer


class DependencyContainer:
    """Adapter delegating to the new AppContainer."""

    def __init__(self):
        self._app_container = AppContainer.from_env()

    # Legacy interface expected by callers
    def get_state_manager(self):
        return self._app_container.get_state_manager()

    def get_prompt_loader(self):
        return self._app_container.get_prompt_loader()

    def get_conversation_manager(self):
        return self._app_container.get_conversation_manager()

    # Test helpers
    def reset(self):
        self._app_container = AppContainer.from_env()

    def create_fresh_instances(self):
        # Rebuild container to clear caches
        self._app_container = AppContainer.from_env()


# Global container instance
_container: Optional[DependencyContainer] = None


def get_container() -> DependencyContainer:
    """Get the global dependency container (adapter)."""
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
        from . import email_flow

        email_flow.email_flow_orchestrator = None
    except ImportError:
        pass
