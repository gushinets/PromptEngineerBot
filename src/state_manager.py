from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class UserState:
    """
    Represents the state of a user interacting with the Telegram bot.
    Attributes:
        waiting_for_prompt (bool): Whether the bot is waiting for the user to enter a prompt.
        last_interaction (Optional[str]): The last message or action from the user.
        waiting_for_followup_choice (bool): Whether the bot is waiting for user to choose YES/NO for follow-up questions.
        waiting_for_followup_prompt_input (bool): Whether the bot is waiting for user to input the prompt in ForceReply.
        in_followup_conversation (bool): Whether the user is currently in a follow-up question conversation.
        improved_prompt_cache (Optional[str]): Cached improved prompt for follow-up conversation context.
        waiting_for_email_input (bool): Whether the bot is waiting for user to enter email address.
        waiting_for_otp_input (bool): Whether the bot is waiting for user to enter OTP code.
        email_flow_data (Optional[dict]): Data for email authentication flow (email, original_prompt, etc.).
    """

    waiting_for_prompt: bool = (
        True  # Default to True so new users start in prompt input mode
    )
    last_interaction: Optional[str] = None
    waiting_for_followup_choice: bool = False
    waiting_for_followup_prompt_input: bool = False
    in_followup_conversation: bool = False
    improved_prompt_cache: Optional[str] = None
    waiting_for_email_input: bool = False
    waiting_for_otp_input: bool = False
    email_flow_data: Optional[dict] = None


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

    def set_waiting_for_followup_choice(self, user_id: int, waiting: bool):
        """
        Set whether the bot is waiting for user to choose YES/NO for follow-up questions.
        Args:
            user_id (int): The Telegram user ID.
            waiting (bool): Whether waiting for follow-up choice.
        """
        state = self.get_user_state(user_id)
        state.waiting_for_followup_choice = waiting

    def set_waiting_for_followup_prompt_input(self, user_id: int, waiting: bool):
        """
        Set whether the bot is waiting for user to input the prompt in ForceReply.
        Args:
            user_id (int): The Telegram user ID.
            waiting (bool): Whether waiting for follow-up prompt input.
        """
        state = self.get_user_state(user_id)
        state.waiting_for_followup_prompt_input = waiting

    def set_in_followup_conversation(self, user_id: int, active: bool):
        """
        Set whether the user is currently in a follow-up question conversation.
        Args:
            user_id (int): The Telegram user ID.
            active (bool): Whether in follow-up conversation.
        """
        state = self.get_user_state(user_id)
        state.in_followup_conversation = active

    def set_improved_prompt_cache(self, user_id: int, prompt: Optional[str]):
        """
        Cache the improved prompt for follow-up conversation context.
        Args:
            user_id (int): The Telegram user ID.
            prompt (Optional[str]): The improved prompt to cache, or None to clear.
        """
        state = self.get_user_state(user_id)
        state.improved_prompt_cache = prompt

    def get_improved_prompt_cache(self, user_id: int) -> Optional[str]:
        """
        Get the cached improved prompt for follow-up conversation context.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            Optional[str]: The cached improved prompt, or None if not set.
        """
        state = self.get_user_state(user_id)
        return state.improved_prompt_cache

    def set_waiting_for_email_input(self, user_id: int, waiting: bool):
        """
        Set whether the bot is waiting for user to enter email address.
        Args:
            user_id (int): The Telegram user ID.
            waiting (bool): Whether waiting for email input.
        """
        state = self.get_user_state(user_id)
        state.waiting_for_email_input = waiting

    def set_waiting_for_otp_input(self, user_id: int, waiting: bool):
        """
        Set whether the bot is waiting for user to enter OTP code.
        Args:
            user_id (int): The Telegram user ID.
            waiting (bool): Whether waiting for OTP input.
        """
        state = self.get_user_state(user_id)
        state.waiting_for_otp_input = waiting

    def set_email_flow_data(self, user_id: int, data: Optional[dict]):
        """
        Set email flow data for the user.
        Args:
            user_id (int): The Telegram user ID.
            data (Optional[dict]): Email flow data or None to clear.
        """
        state = self.get_user_state(user_id)
        state.email_flow_data = data

    def get_email_flow_data(self, user_id: int) -> Optional[dict]:
        """
        Get email flow data for the user.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            Optional[dict]: Email flow data or None if not set.
        """
        state = self.get_user_state(user_id)
        return state.email_flow_data
