from dataclasses import dataclass


@dataclass
class UserState:
    """
    Represents the state of a user interacting with the Telegram bot.
    Attributes:
        waiting_for_prompt (bool): Whether the bot is waiting for the user to enter a prompt.
        last_interaction (Optional[str]): The last message or action from the user.
        waiting_for_followup_choice (bool): Whether the bot is waiting for user to choose YES/NO for follow-up questions.
        in_followup_conversation (bool): Whether the user is currently in a follow-up question conversation.
        improved_prompt_cache (Optional[str]): Cached improved prompt for follow-up conversation context.
        cached_method_name (Optional[str]): Cached method name for the improved prompt (CRAFT, LYRA, GGL, etc.).
        waiting_for_email_input (bool): Whether the bot is waiting for user to enter email address.
        waiting_for_otp_input (bool): Whether the bot is waiting for user to enter OTP code.
        email_flow_data (Optional[dict]): Data for email authentication flow (email, original_prompt, etc.).
        post_optimization_result (Optional[dict]): Cached optimization result for post-optimization email button.
    """

    waiting_for_prompt: bool = True  # Default to True so new users start in prompt input mode
    last_interaction: str | None = None
    waiting_for_followup_choice: bool = False
    in_followup_conversation: bool = False
    improved_prompt_cache: str | None = None
    cached_method_name: str | None = None
    waiting_for_email_input: bool = False
    waiting_for_otp_input: bool = False
    email_flow_data: dict | None = None
    post_optimization_result: dict | None = None


class StateManager:
    """
    Manages the state of all users interacting with the Telegram bot.
    Stores and retrieves per-user state, such as prompt waiting status and last interaction.
    """

    def __init__(self):
        self.states: dict[int, UserState] = {}

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

    def set_in_followup_conversation(self, user_id: int, active: bool):
        """
        Set whether the user is currently in a follow-up question conversation.
        Args:
            user_id (int): The Telegram user ID.
            active (bool): Whether in follow-up conversation.
        """
        state = self.get_user_state(user_id)
        state.in_followup_conversation = active

    def set_improved_prompt_cache(self, user_id: int, prompt: str | None):
        """
        Cache the improved prompt for follow-up conversation context.
        Args:
            user_id (int): The Telegram user ID.
            prompt (Optional[str]): The improved prompt to cache, or None to clear.
        """
        state = self.get_user_state(user_id)
        state.improved_prompt_cache = prompt

    def get_improved_prompt_cache(self, user_id: int) -> str | None:
        """
        Get the cached improved prompt for follow-up conversation context.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            Optional[str]: The cached improved prompt, or None if not set.
        """
        state = self.get_user_state(user_id)
        return state.improved_prompt_cache

    def set_cached_method_name(self, user_id: int, method_name: str | None):
        """
        Cache the method name for the improved prompt.
        Args:
            user_id (int): The Telegram user ID.
            method_name (Optional[str]): The method name to cache (CRAFT, LYRA, GGL, etc.), or None to clear.
        """
        state = self.get_user_state(user_id)
        state.cached_method_name = method_name

    def get_cached_method_name(self, user_id: int) -> str | None:
        """
        Get the cached method name for the improved prompt.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            Optional[str]: The cached method name, or None if not set.
        """
        state = self.get_user_state(user_id)
        return state.cached_method_name

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

    def set_email_flow_data(self, user_id: int, data: dict | None):
        """
        Set email flow data for the user.
        Args:
            user_id (int): The Telegram user ID.
            data (Optional[dict]): Email flow data or None to clear.
        """
        state = self.get_user_state(user_id)
        state.email_flow_data = data

    def get_email_flow_data(self, user_id: int) -> dict | None:
        """
        Get email flow data for the user.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            Optional[dict]: Email flow data or None if not set.
        """
        state = self.get_user_state(user_id)
        return state.email_flow_data

    def set_post_optimization_result(self, user_id: int, result: dict | None):
        """
        Set post-optimization result for the user.
        Args:
            user_id (int): The Telegram user ID.
            result (Optional[dict]): Post-optimization result data or None to clear.
        """
        state = self.get_user_state(user_id)
        state.post_optimization_result = result

    def get_post_optimization_result(self, user_id: int) -> dict | None:
        """
        Get post-optimization result for the user.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            Optional[dict]: Post-optimization result data or None if not set.
        """
        state = self.get_user_state(user_id)
        return state.post_optimization_result
