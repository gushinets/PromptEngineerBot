"""
Prompt loading and management.
"""

import logging
import os
import sys


class PromptLoader:
    """Loads and manages system prompts for different optimization methods."""

    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            # Prompts are in telegram_bot/prompts/, not telegram_bot/utils/prompts/
            package_root = os.path.dirname(os.path.dirname(__file__))
            prompts_dir = os.path.join(package_root, "prompts")
        self.prompts_dir = prompts_dir
        self._prompts: dict[str, str] = {}
        self._load_prompts()

    def _load_prompts(self):
        """Load all prompt files. Fails fast if any prompt cannot be loaded."""
        prompt_files = {
            "craft": "CRAFT_prompt.txt",
            "lyra": "LYRA_prompt.txt",
            "ggl": "GGL_prompt.txt",
            "followup": "Follow_up_questions_prompt.txt",
            "craft_email": "CRAFT_email_prompt.txt",
            "lyra_email": "LYRA_email_prompt.txt",
            "ggl_email": "GGL_email_prompt.txt",
        }

        logger = logging.getLogger(__name__)
        logger.info(f"Loading prompts from directory: {self.prompts_dir}")

        loaded_prompts = []
        failed_prompts = []

        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                logger.debug(f"Loading prompt file: {filepath}")
                with open(filepath, encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content:
                        error_msg = f"Prompt file is empty: {filepath}"
                        logger.error(error_msg)
                        failed_prompts.append(f"{key} ({filename}): Empty file")
                        raise ValueError(error_msg)

                    self._prompts[key] = content
                    loaded_prompts.append(key)
                    logger.info(
                        f"Successfully loaded prompt '{key}' from {filename} ({len(content)} characters)"
                    )

            except FileNotFoundError as e:
                error_msg = f"Critical error: Prompt file not found: {filepath}"
                logger.error(error_msg)
                failed_prompts.append(f"{key} ({filename}): File not found")
                raise FileNotFoundError(error_msg) from e
            except ValueError as e:
                # Re-raise ValueError (empty file) as-is for proper test handling
                raise e
            except (PermissionError, OSError) as e:
                error_msg = f"Critical error: Cannot read prompt file {filepath}: {e}"
                logger.error(error_msg)
                failed_prompts.append(f"{key} ({filename}): {e!s}")
                raise Exception(error_msg) from e
            except Exception as e:
                error_msg = f"Critical error: Unexpected error loading prompt file {filepath}: {e}"
                logger.error(error_msg)
                failed_prompts.append(f"{key} ({filename}): {e!s}")
                raise Exception(error_msg) from e

        # Log summary
        if failed_prompts:
            logger.critical(
                f"Failed to load {len(failed_prompts)} prompt(s): {', '.join(failed_prompts)}"
            )
            logger.critical("Application cannot continue without all required prompts")
            sys.exit(1)

        logger.info(
            f"Successfully loaded all {len(loaded_prompts)} required prompts: {', '.join(loaded_prompts)}"
        )

        # Validate that all expected prompts were loaded
        expected_prompts = set(prompt_files.keys())
        loaded_prompt_keys = set(self._prompts.keys())
        if expected_prompts != loaded_prompt_keys:
            missing = expected_prompts - loaded_prompt_keys
            error_msg = f"Critical error: Missing prompts after loading: {missing}"
            logger.critical(error_msg)
            sys.exit(1)

    @property
    def craft_prompt(self) -> str:
        """Get the CRAFT optimization prompt."""
        return self._prompts["craft"]

    @property
    def lyra_prompt(self) -> str:
        """Get the LYRA optimization prompt."""
        return self._prompts["lyra"]

    @property
    def ggl_prompt(self) -> str:
        """Get the GGL optimization prompt."""
        return self._prompts["ggl"]

    @property
    def followup_prompt(self) -> str:
        """Get the follow-up questions prompt."""
        return self._prompts["followup"]

    @property
    def craft_email_prompt(self) -> str:
        """Get the CRAFT email optimization prompt."""
        return self._prompts["craft_email"]

    @property
    def lyra_email_prompt(self) -> str:
        """Get the LYRA email optimization prompt."""
        return self._prompts["lyra_email"]

    @property
    def ggl_email_prompt(self) -> str:
        """Get the GGL email optimization prompt."""
        return self._prompts["ggl_email"]

    def get_prompt(self, method: str) -> str:
        """
        Get a prompt by method name.

        Args:
            method: Method name ('craft', 'lyra', 'ggl', 'followup', 'craft_email', 'lyra_email', 'ggl_email')

        Returns:
            The prompt text

        Raises:
            KeyError: If method is not found
        """
        if method.lower() not in self._prompts:
            raise KeyError(f"Unknown prompt method: {method}")
        return self._prompts[method.lower()]
