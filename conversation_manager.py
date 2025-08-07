class ConversationManager:
    """
    Handles conversation state for each user, including message transcripts,
    temporary user prompts, and prompt optimization method selection.
    """

    def __init__(self):
        """
        Initialize conversation storage for all users.
        """
        self.transcripts = {}
        self.user_prompts = {}  # Store user prompt before method selection
        self.method_selection = {}  # Track if waiting for method selection
        self.current_methods = {}  # Track the current optimization method for each user

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
        Args:
            user_id (int): The Telegram user ID.
        """
        self.transcripts[user_id] = []
        self.user_prompts[user_id] = None
        self.method_selection[user_id] = False
        self.current_methods[user_id] = None

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
        return self.current_methods.get(user_id, 'CUSTOM')
