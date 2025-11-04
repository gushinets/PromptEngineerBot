"""Tests for the prompt loader module."""

import os
from unittest.mock import mock_open, patch

import pytest

from telegram_bot.utils.prompt_loader import PromptLoader


class TestPromptLoader:
    """Test cases for PromptLoader class."""

    def test_init_default_directory(self):
        """Test PromptLoader initialization with default directory."""
        with patch(
            "telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"
        ) as mock_load:
            loader = PromptLoader()

            expected_dir = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "telegram_bot", "prompts"
            )
            assert loader.prompts_dir == expected_dir
            mock_load.assert_called_once()

    def test_init_custom_directory(self):
        """Test PromptLoader initialization with custom directory."""
        custom_dir = "/custom/prompts"

        with patch(
            "telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"
        ) as mock_load:
            loader = PromptLoader(custom_dir)

            assert loader.prompts_dir == custom_dir
            mock_load.assert_called_once()

    def test_load_prompts_success(self):
        """Test successful loading of all prompt files."""
        mock_files = {
            "CRAFT_prompt.txt": "CRAFT prompt content",
            "LYRA_prompt.txt": "LYRA prompt content",
            "GGL_prompt.txt": "GGL prompt content",
            "Follow_up_questions_prompt.txt": "Follow-up prompt content",
            "CRAFT_email_prompt.txt": "CRAFT email prompt content",
            "LYRA_email_prompt.txt": "LYRA email prompt content",
            "GGL_email_prompt.txt": "GGL email prompt content",
        }

        def mock_open_func(filepath, *args, **kwargs):
            filename = os.path.basename(filepath)
            if filename in mock_files:
                return mock_open(read_data=mock_files[filename])()
            raise FileNotFoundError(f"File not found: {filepath}")

        with patch("builtins.open", side_effect=mock_open_func):
            loader = PromptLoader("/test/prompts")

            assert loader._prompts["craft"] == "CRAFT prompt content"
            assert loader._prompts["lyra"] == "LYRA prompt content"
            assert loader._prompts["ggl"] == "GGL prompt content"
            assert loader._prompts["followup"] == "Follow-up prompt content"
            assert loader._prompts["craft_email"] == "CRAFT email prompt content"
            assert loader._prompts["lyra_email"] == "LYRA email prompt content"
            assert loader._prompts["ggl_email"] == "GGL email prompt content"

    def test_load_prompts_missing_file(self):
        """Test loading prompts when a file is missing."""
        with patch("builtins.open", side_effect=FileNotFoundError("File not found")):
            with pytest.raises(FileNotFoundError, match="Prompt file not found"):
                PromptLoader("/test/prompts")

    def test_load_prompts_read_error(self):
        """Test loading prompts when file read fails."""
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            with pytest.raises(
                Exception, match="Critical error: Cannot read prompt file"
            ):
                PromptLoader("/test/prompts")

    def test_load_prompts_empty_file(self):
        """Test loading prompts when a file is empty."""
        mock_files = {
            "CRAFT_prompt.txt": "",  # Empty file
            "LYRA_prompt.txt": "LYRA prompt content",
            "GGL_prompt.txt": "GGL prompt content",
            "Follow_up_questions_prompt.txt": "Follow-up prompt content",
        }

        def mock_open_func(filepath, *args, **kwargs):
            filename = os.path.basename(filepath)
            if filename in mock_files:
                return mock_open(read_data=mock_files[filename])()
            raise FileNotFoundError(f"File not found: {filepath}")

        with patch("builtins.open", side_effect=mock_open_func):
            with pytest.raises(ValueError, match="Prompt file is empty"):
                PromptLoader("/test/prompts")

    def test_craft_prompt_property(self):
        """Test craft_prompt property."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"craft": "CRAFT content"}

            assert loader.craft_prompt == "CRAFT content"

    def test_lyra_prompt_property(self):
        """Test lyra_prompt property."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"lyra": "LYRA content"}

            assert loader.lyra_prompt == "LYRA content"

    def test_ggl_prompt_property(self):
        """Test ggl_prompt property."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"ggl": "GGL content"}

            assert loader.ggl_prompt == "GGL content"

    def test_followup_prompt_property(self):
        """Test followup_prompt property."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"followup": "Follow-up content"}

            assert loader.followup_prompt == "Follow-up content"

    def test_craft_email_prompt_property(self):
        """Test craft_email_prompt property."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"craft_email": "CRAFT email content"}

            assert loader.craft_email_prompt == "CRAFT email content"

    def test_lyra_email_prompt_property(self):
        """Test lyra_email_prompt property."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"lyra_email": "LYRA email content"}

            assert loader.lyra_email_prompt == "LYRA email content"

    def test_ggl_email_prompt_property(self):
        """Test ggl_email_prompt property."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"ggl_email": "GGL email content"}

            assert loader.ggl_email_prompt == "GGL email content"

    def test_get_prompt_success(self):
        """Test get_prompt method with valid method name."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"craft": "CRAFT content", "lyra": "LYRA content"}

            assert loader.get_prompt("craft") == "CRAFT content"
            assert loader.get_prompt("CRAFT") == "CRAFT content"  # Case insensitive
            assert loader.get_prompt("Lyra") == "LYRA content"

    def test_get_prompt_unknown_method(self):
        """Test get_prompt method with unknown method name."""
        with patch("telegram_bot.utils.prompt_loader.PromptLoader._load_prompts"):
            loader = PromptLoader()
            loader._prompts = {"craft": "CRAFT content"}

            with pytest.raises(KeyError, match="Unknown prompt method: unknown"):
                loader.get_prompt("unknown")

    def test_prompt_content_stripped(self):
        """Test that prompt content is stripped of whitespace."""
        mock_files = {
            "CRAFT_prompt.txt": "  \n  CRAFT prompt content  \n  ",
            "LYRA_prompt.txt": "\t\tLYRA prompt content\t\t",
            "GGL_prompt.txt": "GGL prompt content",
            "Follow_up_questions_prompt.txt": "  Follow-up prompt content  ",
            "CRAFT_email_prompt.txt": "  CRAFT email prompt content  ",
            "LYRA_email_prompt.txt": "\t\tLYRA email prompt content\t\t",
            "GGL_email_prompt.txt": "GGL email prompt content",
        }

        def mock_open_func(filepath, *args, **kwargs):
            filename = os.path.basename(filepath)
            if filename in mock_files:
                return mock_open(read_data=mock_files[filename])()
            raise FileNotFoundError(f"File not found: {filepath}")

        with patch("builtins.open", side_effect=mock_open_func):
            loader = PromptLoader("/test/prompts")

            assert loader._prompts["craft"] == "CRAFT prompt content"
            assert loader._prompts["lyra"] == "LYRA prompt content"
            assert loader._prompts["ggl"] == "GGL prompt content"
            assert loader._prompts["followup"] == "Follow-up prompt content"
            assert loader._prompts["craft_email"] == "CRAFT email prompt content"
            assert loader._prompts["lyra_email"] == "LYRA email prompt content"
            assert loader._prompts["ggl_email"] == "GGL email prompt content"



