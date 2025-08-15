from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserState:
    """
    Represents the state of a user interacting with the Telegram bot.
    Attributes:
        waiting_for_prompt (bool): Whether the bot is waiting for the user to enter a prompt.
        last_interaction (Optional[str]): The last message or action from the user.
    """

    waiting_for_prompt: bool = (
        True  # Default to True so new users start in prompt input mode
    )
    last_interaction: Optional[str] = None


class StateManager:
    """
    Manages the state of all users interacting with the Telegram bot.
    Stores and retrieves per-user state, such as prompt waiting status and last interaction.
    """

    def __init__(self):
        self.states: Dict[int, UserState] = {}

    def get_user_state(self, user_id: int) -> UserState:
        """
        Retrieve the state for a given user, creating it if it doesn't exist.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            UserState: The state object for the user.
        """
        if user_id not in self.states:
            self.states[user_id] = UserState()
        return self.states[user_id]

    def set_waiting_for_prompt(self, user_id: int, waiting: bool):
        """
        Set whether the bot is waiting for a prompt from the user.
        Args:
            user_id (int): The Telegram user ID.
            waiting (bool): Waiting status.
        """
        state = self.get_user_state(user_id)
        state.waiting_for_prompt = waiting

    def set_last_interaction(self, user_id: int, interaction: str):
        """
        Set the last interaction for the user.
        Args:
            user_id (int): The Telegram user ID.
            interaction (str): The last message or action from the user.
        """
        state = self.get_user_state(user_id)
        state.last_interaction = interaction
