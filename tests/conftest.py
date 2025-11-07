"""Pytest configuration and fixtures for the test suite."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from dotenv import load_dotenv


# Import test utilities to ensure autouse fixtures are loaded


# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file
load_dotenv()


@pytest.fixture
def mock_update():
    """Create a mock Update object."""
    update = MagicMock()
    update.effective_user.id = 12345
    update.message = MagicMock()
    update.message.text = "test message"
    update.message.reply_text = AsyncMock(return_value=None)
    return update


@pytest.fixture
def mock_context():
    """Create a mock Context object."""
    context = MagicMock()
    context.bot = MagicMock()
    context.args = []
    return context


@pytest.fixture
def mock_application():
    """Create a mock Application object."""
    with patch("telegram_bot.main.Application.builder") as mock_builder:
        mock_app = MagicMock()
        mock_builder.return_value = MagicMock(
            token=MagicMock(return_value=MagicMock()),
            connect_timeout=MagicMock(return_value=MagicMock()),
            pool_timeout=MagicMock(return_value=MagicMock()),
            read_timeout=MagicMock(return_value=MagicMock()),
            write_timeout=MagicMock(return_value=MagicMock()),
            get_updates_read_timeout=MagicMock(return_value=MagicMock()),
            build=MagicMock(return_value=mock_app),
        )
        # Make application lifecycle methods awaitable
        mock_app.initialize = AsyncMock(return_value=None)
        mock_app.start = AsyncMock(return_value=None)
        mock_app.stop = AsyncMock(return_value=None)
        mock_app.shutdown = AsyncMock(return_value=None)
        mock_app.updater = MagicMock()
        mock_app.updater.start_polling = AsyncMock(return_value=None)
        yield mock_app


@pytest.fixture
def mock_llm_client():
    """Mock the LLM client to avoid real API calls during testing."""
    from unittest.mock import AsyncMock, MagicMock

    # Create a mock LLM client
    mock_client = MagicMock()
    mock_client.send_prompt = AsyncMock(return_value="Mocked LLM response")
    mock_client.get_last_usage = MagicMock(
        return_value={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
    )

    return mock_client
