"""Tests for the state manager module."""

from telegram_bot.core.state_manager import StateManager, UserState


class TestUserState:
    """Test cases for UserState dataclass."""

    def test_user_state_defaults(self):
        """Test UserState default values."""
        state = UserState()

        assert state.waiting_for_prompt is True  # Updated to match new default
        assert state.last_interaction is None
        assert state.waiting_for_followup_choice is False
        assert state.in_followup_conversation is False
        assert state.improved_prompt_cache is None

    def test_user_state_with_values(self):
        """Test UserState with custom values."""
        state = UserState(
            waiting_for_prompt=True,
            last_interaction="test",
            waiting_for_followup_choice=True,
            in_followup_conversation=True,
            improved_prompt_cache="cached prompt",
        )

        assert state.waiting_for_prompt is True
        assert state.last_interaction == "test"
        assert state.waiting_for_followup_choice is True
        assert state.in_followup_conversation is True
        assert state.improved_prompt_cache == "cached prompt"


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
        assert state.waiting_for_prompt is True  # Updated to match new default
        assert state.last_interaction is None
        assert state.waiting_for_followup_choice is False
        assert state.in_followup_conversation is False
        assert state.improved_prompt_cache is None
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

    def test_set_waiting_for_followup_choice(self):
        """Test setting waiting_for_followup_choice flag."""
        manager = StateManager()
        user_id = 12345

        # Test setting to True
        manager.set_waiting_for_followup_choice(user_id, True)
        state = manager.get_user_state(user_id)
        assert state.waiting_for_followup_choice is True

        # Test setting to False
        manager.set_waiting_for_followup_choice(user_id, False)
        assert state.waiting_for_followup_choice is False

    def test_set_in_followup_conversation(self):
        """Test setting in_followup_conversation flag."""
        manager = StateManager()
        user_id = 12345

        # Test setting to True
        manager.set_in_followup_conversation(user_id, True)
        state = manager.get_user_state(user_id)
        assert state.in_followup_conversation is True

        # Test setting to False
        manager.set_in_followup_conversation(user_id, False)
        assert state.in_followup_conversation is False

    def test_set_improved_prompt_cache(self):
        """Test setting improved_prompt_cache."""
        manager = StateManager()
        user_id = 12345
        test_prompt = "This is a test improved prompt"

        # Test setting a prompt
        manager.set_improved_prompt_cache(user_id, test_prompt)
        state = manager.get_user_state(user_id)
        assert state.improved_prompt_cache == test_prompt

        # Test clearing the cache
        manager.set_improved_prompt_cache(user_id, None)
        assert state.improved_prompt_cache is None

    def test_get_improved_prompt_cache(self):
        """Test getting improved_prompt_cache."""
        manager = StateManager()
        user_id = 12345
        test_prompt = "This is a test improved prompt"

        # Test getting None when not set
        cached_prompt = manager.get_improved_prompt_cache(user_id)
        assert cached_prompt is None

        # Test getting cached prompt after setting
        manager.set_improved_prompt_cache(user_id, test_prompt)
        cached_prompt = manager.get_improved_prompt_cache(user_id)
        assert cached_prompt == test_prompt

        # Test getting None after clearing
        manager.set_improved_prompt_cache(user_id, None)
        cached_prompt = manager.get_improved_prompt_cache(user_id)
        assert cached_prompt is None

    def test_followup_states_independence(self):
        """Test that follow-up states are independent between users."""
        manager = StateManager()
        user1_id = 12345
        user2_id = 67890
        prompt1 = "User 1 improved prompt"
        prompt2 = "User 2 improved prompt"

        # Set different follow-up states for different users
        manager.set_waiting_for_followup_choice(user1_id, True)
        manager.set_in_followup_conversation(user1_id, False)
        manager.set_improved_prompt_cache(user1_id, prompt1)

        manager.set_waiting_for_followup_choice(user2_id, False)
        manager.set_in_followup_conversation(user2_id, True)
        manager.set_improved_prompt_cache(user2_id, prompt2)

        # Verify states are independent
        user1_state = manager.get_user_state(user1_id)
        user2_state = manager.get_user_state(user2_id)

        assert user1_state.waiting_for_followup_choice is True
        assert user1_state.in_followup_conversation is False
        assert user1_state.improved_prompt_cache == prompt1

        assert user2_state.waiting_for_followup_choice is False
        assert user2_state.in_followup_conversation is True
        assert user2_state.improved_prompt_cache == prompt2

    def test_followup_state_transitions(self):
        """Test typical follow-up conversation state transitions."""
        manager = StateManager()
        user_id = 12345
        test_prompt = "Test improved prompt"

        # Initial state
        state = manager.get_user_state(user_id)
        assert state.waiting_for_prompt is True
        assert state.waiting_for_followup_choice is False
        assert state.in_followup_conversation is False
        assert state.improved_prompt_cache is None

        # After receiving improved prompt, cache it and wait for choice
        manager.set_waiting_for_prompt(user_id, False)
        manager.set_improved_prompt_cache(user_id, test_prompt)
        manager.set_waiting_for_followup_choice(user_id, True)

        assert state.waiting_for_prompt is False
        assert state.waiting_for_followup_choice is True
        assert state.in_followup_conversation is False
        assert state.improved_prompt_cache == test_prompt

        # User chooses ДА - start follow-up conversation directly
        manager.set_waiting_for_followup_choice(user_id, False)
        manager.set_in_followup_conversation(user_id, True)

        assert state.waiting_for_prompt is False
        assert state.waiting_for_followup_choice is False
        assert state.in_followup_conversation is True
        assert state.improved_prompt_cache == test_prompt

        # Complete follow-up conversation - reset to prompt input
        manager.set_in_followup_conversation(user_id, False)
        manager.set_waiting_for_prompt(user_id, True)
        manager.set_improved_prompt_cache(user_id, None)

        assert state.waiting_for_prompt is True
        assert state.waiting_for_followup_choice is False
        assert state.in_followup_conversation is False
        assert state.improved_prompt_cache is None
