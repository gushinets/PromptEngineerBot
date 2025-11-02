from telegram_prompt_bot.core.prompt_loader import PromptLoader
from telegram_prompt_bot.core.state_manager import StateManager


class ConversationManager:
    """
    Handles conversation state for each user, including message transcripts,
    temporary user prompts, and prompt optimization method selection.
    """

    def __init__(
        self, prompt_loader_or_state_manager=None, state_manager: StateManager = None
    ):
        """
        Initialize conversation storage for all users.

        Args:
            prompt_loader_or_state_manager: Either PromptLoader instance or StateManager instance
            state_manager: StateManager instance (if first arg is PromptLoader)
        """
        # Handle flexible constructor arguments
        if isinstance(prompt_loader_or_state_manager, StateManager):
            # Called with ConversationManager(state_manager)
            self.prompt_loader = PromptLoader()
            self.state_manager = prompt_loader_or_state_manager
        elif state_manager is not None:
            # Called with ConversationManager(prompt_loader, state_manager)
            self.prompt_loader = prompt_loader_or_state_manager or PromptLoader()
            self.state_manager = state_manager
        elif prompt_loader_or_state_manager is None:
            # Called with ConversationManager() - need state_manager
            raise ValueError("StateManager is required for ConversationManager")
        else:
            # Called with ConversationManager(prompt_loader) - need state_manager
            raise ValueError("StateManager is required for ConversationManager")
        self.transcripts = {}
        self.user_prompts = {}  # Store user prompt before method selection
        self.method_selection = {}  # Track if waiting for method selection
        self.current_methods = {}  # Track the current optimization method for each user
        # Track per-conversation token usage totals per user
        # Structure: { user_id: { 'prompt_tokens': int, 'completion_tokens': int, 'total_tokens': int } }
        self.token_totals = {}

    def get_transcript(self, user_id):
        """
        Get the message transcript for a user.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            list: List of message dicts for the user.
        """
        if user_id not in self.transcripts:
            self.transcripts[user_id] = []
        return self.transcripts[user_id]

    def append_message(self, user_id, role, content):
        """
        Append a message to the user's transcript.
        Args:
            user_id (int): The Telegram user ID.
            role (str): 'user' or 'assistant' or 'system'.
            content (str): The message content.
        """
        transcript = self.get_transcript(user_id)
        transcript.append({"role": role, "content": content})

    def reset(self, user_id):
        """
        Reset the conversation state for a user.
        Includes cleanup of follow-up conversation state.
        Args:
            user_id (int): The Telegram user ID.
        """
        self.transcripts[user_id] = []
        self.user_prompts[user_id] = None
        self.method_selection[user_id] = False
        self.current_methods[user_id] = None
        self.token_totals[user_id] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }

        # Reset follow-up conversation state
        self.state_manager.set_in_followup_conversation(user_id, False)

    def set_user_prompt(self, user_id, prompt):
        """
        Store the user's prompt before method selection.
        Args:
            user_id (int): The Telegram user ID.
            prompt (str): The user's prompt.
        """
        self.user_prompts[user_id] = prompt

    def get_user_prompt(self, user_id):
        """
        Retrieve the stored user prompt.
        Args:
            user_id (int): The Telegram user ID.
        Returns:
            str or None: The user's prompt if set.
        """
        return self.user_prompts.get(user_id)

    def set_waiting_for_method(self, user_id, waiting):
        """Set whether we're waiting for method selection from the user."""
        self.method_selection[user_id] = waiting

    def is_waiting_for_method(self, user_id):
        """Check if we're waiting for method selection from the user."""
        return self.method_selection.get(user_id, False)

    def set_current_method(self, user_id, method_name):
        """
        Set the current optimization method for a user.

        Args:
            user_id (int): The Telegram user ID
            method_name (str): The name of the optimization method (e.g., 'CRAFT', 'LYRA', 'GGL')
        """
        self.current_methods[user_id] = method_name

    def get_current_method(self, user_id):
        """
        Get the current optimization method for a user.

        Args:
            user_id (int): The Telegram user ID

        Returns:
            str: The name of the current optimization method, or 'CUSTOM' if not set
        """
        value = self.current_methods.get(user_id)
        return value or "CUSTOM"

    def accumulate_token_usage(self, user_id, usage):
        """
        Accumulate token usage for the user's current conversation.
        'usage' is expected to be a dict with keys 'prompt_tokens', 'completion_tokens', 'total_tokens'.
        Missing keys or None values are treated as zero.
        """
        if user_id not in self.token_totals:
            self.token_totals[user_id] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }
        if not usage:
            return
        totals = self.token_totals[user_id]
        try:
            totals["prompt_tokens"] += int(usage.get("prompt_tokens") or 0)
            totals["completion_tokens"] += int(usage.get("completion_tokens") or 0)
            totals["total_tokens"] += int(usage.get("total_tokens") or 0)
        except Exception:
            # Best-effort accounting; ignore malformed usage
            pass

    def get_token_totals(self, user_id):
        """Return the current token totals dict for the user (zeros if none)."""
        return self.token_totals.get(
            user_id, {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        )

    def start_followup_conversation(self, user_id, improved_prompt):
        """
        Initialize follow-up conversation context with system prompt and improved prompt.

        Args:
            user_id (int): The Telegram user ID
            improved_prompt (str): The improved prompt from previous conversation
        """
        # Reset transcript for new follow-up conversation
        self.transcripts[user_id] = []

        # Load follow-up system prompt using PromptLoader
        # No fallback - if prompt loading fails, the app should have already failed at startup
        system_prompt = self.prompt_loader.followup_prompt

        # Add system context
        self.append_message(user_id, "system", system_prompt)

        # Add improved prompt as user message for context
        self.append_message(user_id, "user", improved_prompt)

        # Update state manager
        self.state_manager.set_in_followup_conversation(user_id, True)

    def is_in_followup_conversation(self, user_id):
        """
        Check if user is currently in a follow-up conversation.

        Args:
            user_id (int): The Telegram user ID

        Returns:
            bool: True if in follow-up conversation, False otherwise
        """
        # Use StateManager for reliable state tracking
        user_state = self.state_manager.get_user_state(user_id)
        return user_state.in_followup_conversation

    def reset_to_followup_ready(self, user_id):
        """
        Reset conversation state to be ready for follow-up choice.
        Clears conversation but preserves user state for follow-up flow.
        Token totals are preserved since they should be logged before calling this method.

        Args:
            user_id (int): The Telegram user ID
        """
        # Clear conversation transcript
        self.transcripts[user_id] = []

        # Reset method selection state but preserve follow-up state
        self.method_selection[user_id] = False
        self.current_methods[user_id] = None

        # Reset follow-up conversation state
        self.state_manager.set_in_followup_conversation(user_id, False)

        # Token totals are NOT reset here - they should be reset after logging
        # This preserves the accumulated tokens for the initial optimization session

    def reset_token_totals(self, user_id):
        """
        Reset token totals for a user after they have been logged.
        This should be called after successful token logging.

        Args:
            user_id (int): The Telegram user ID
        """
        self.token_totals[user_id] = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        }
