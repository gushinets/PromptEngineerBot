"""
Prompt loading and management.
"""

import logging
import os
import sys
from typing import Dict


class PromptLoader:
    """Loads and manages system prompts for different optimization methods."""

    def __init__(self, prompts_dir: str = None):
        if prompts_dir is None:
            prompts_dir = os.path.join(os.path.dirname(__file__), "prompts")
        self.prompts_dir = prompts_dir
        self._prompts: Dict[str, str] = {}
        self._load_prompts()

    def _load_prompts(self):
        """Load all prompt files. Fails fast if any prompt cannot be loaded."""
        prompt_files = {
            "craft": "CRAFT_prompt.txt",
            "lyra": "LYRA_prompt.txt",
            "ggl": "GGL_prompt.txt",
            "followup": "Follow_up_questions_prompt.txt",
        }

        logger = logging.getLogger(__name__)
        logger.info(f"Loading prompts from directory: {self.prompts_dir}")

        loaded_prompts = []
        failed_prompts = []

        for key, filename in prompt_files.items():
            filepath = os.path.join(self.prompts_dir, filename)
            try:
                logger.debug(f"Loading prompt file: {filepath}")
                with open(filepath, "r", encoding="utf-8") as f:
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
                failed_prompts.append(f"{key} ({filename}): {str(e)}")
                raise Exception(error_msg) from e
            except Exception as e:
                error_msg = f"Critical error: Unexpected error loading prompt file {filepath}: {e}"
                logger.error(error_msg)
                failed_prompts.append(f"{key} ({filename}): {str(e)}")
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

    def get_prompt(self, method: str) -> str:
        """
        Get a prompt by method name.

        Args:
            method: Method name ('craft', 'lyra', 'ggl', 'followup')

        Returns:
            The prompt text

        Raises:
            KeyError: If method is not found
        """
        if method.lower() not in self._prompts:
            raise KeyError(f"Unknown prompt method: {method}")
        return self._prompts[method.lower()]
