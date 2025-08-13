"""Tests for the state manager module."""
import pytest

from src.state_manager import StateManager, UserState


class TestUserState:
    """Test cases for UserState dataclass."""

    def test_user_state_defaults(self):
        """Test UserState default values."""
        state = UserState()
        
        assert state.waiting_for_prompt is False
        assert state.last_interaction is None

    def test_user_state_with_values(self):
        """Test UserState with custom values."""
        state = UserState(waiting_for_prompt=True, last_interaction="test")
        
        assert state.waiting_for_prompt is True
        assert state.last_interaction == "test"


class TestStateManager:
    """Test cases for StateManager class."""

    def test_init(self):
        """Test StateManager initialization."""
        manager = StateManager()
        
        assert manager.states == {}

    def test_get_user_state_new_user(self):
        """Test getting state for new user."""
        manager = StateManager()
        user_id = 12345
        
        state = manager.get_user_state(user_id)
        
        assert isinstance(state, UserState)
        assert state.waiting_for_prompt is False
        assert state.last_interaction is None
        assert user_id in manager.states

    def test_get_user_state_existing_user(self):
        """Test getting state for existing user."""
        manager = StateManager()
        user_id = 12345
        
        # Create initial state
        initial_state = manager.get_user_state(user_id)
        initial_state.waiting_for_prompt = True
        initial_state.last_interaction = "test"
        
        # Get state again
        state = manager.get_user_state(user_id)
        
        assert state is initial_state
        assert state.waiting_for_prompt is True
        assert state.last_interaction == "test"

    def test_set_waiting_for_prompt(self):
        """Test setting waiting_for_prompt flag."""
        manager = StateManager()
        user_id = 12345
        
        manager.set_waiting_for_prompt(user_id, True)
        state = manager.get_user_state(user_id)
        assert state.waiting_for_prompt is True
        
        manager.set_waiting_for_prompt(user_id, False)
        assert state.waiting_for_prompt is False

    def test_set_last_interaction(self):
        """Test setting last_interaction."""
        manager = StateManager()
        user_id = 12345
        interaction = "user sent message"
        
        manager.set_last_interaction(user_id, interaction)
        state = manager.get_user_state(user_id)
        
        assert state.last_interaction == interaction

    def test_multiple_users(self):
        """Test managing state for multiple users."""
        manager = StateManager()
        user1_id = 12345
        user2_id = 67890
        
        # Set different states for different users
        manager.set_waiting_for_prompt(user1_id, True)
        manager.set_last_interaction(user1_id, "user1 interaction")
        
        manager.set_waiting_for_prompt(user2_id, False)
        manager.set_last_interaction(user2_id, "user2 interaction")
        
        # Verify states are independent
        user1_state = manager.get_user_state(user1_id)
        user2_state = manager.get_user_state(user2_id)
        
        assert user1_state.waiting_for_prompt is True
        assert user1_state.last_interaction == "user1 interaction"
        
        assert user2_state.waiting_for_prompt is False
        assert user2_state.last_interaction == "user2 interaction"
        
        assert user1_state is not user2_state