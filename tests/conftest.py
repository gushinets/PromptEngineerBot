"""Pytest configuration and fixtures for the test suite."""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

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
    update.message.reply_text = MagicMock()
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
    with patch('main.Application.builder') as mock_builder:
        mock_app = MagicMock()
        mock_builder.return_value = MagicMock(
            token=MagicMock(return_value=MagicMock()),
            connect_timeout=MagicMock(return_value=MagicMock()),
            pool_timeout=MagicMock(return_value=MagicMock()),
            read_timeout=MagicMock(return_value=MagicMock()),
            write_timeout=MagicMock(return_value=MagicMock()),
            get_updates_read_timeout=MagicMock(return_value=MagicMock()),
            build=MagicMock(return_value=mock_app)
        )
        yield mock_app

@pytest.fixture(autouse=True)
def mock_llm_client():
    """Mock the LLM client to avoid real API calls during testing."""
    with patch('main.llm_client') as mock_client:
        mock_client.send_prompt = MagicMock(return_value="Mocked LLM response")
        yield mock_client
