"""
Unit tests for user profile utilities.

Tests profile extraction from Telegram effective_user objects, handling of
missing/partial data, and profile comparison functionality.
"""

from unittest.mock import MagicMock

import pytest

from telegram_bot.auth.user_profile_utils import (
    extract_user_profile,
    has_meaningful_profile_changes,
    should_update_user_profile,
)


class TestExtractUserProfile:
    """Test cases for extract_user_profile function."""

    def test_extract_complete_user_profile(self):
        """Test extraction with complete Telegram user data."""
        # Arrange
        effective_user = MagicMock()
        effective_user.first_name = "John"
        effective_user.last_name = "Doe"
        effective_user.is_bot = False
        effective_user.is_premium = True
        effective_user.language_code = "en"

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "John",
            "last_name": "Doe",
            "is_bot": False,
            "is_premium": True,
            "language_code": "en",
        }
        assert result == expected

    def test_extract_minimal_user_profile(self):
        """Test extraction with minimal required data (only first_name)."""
        # Arrange - Create object with only first_name attribute
        effective_user = type("MockUser", (), {})()
        effective_user.first_name = "Jane"
        # Other attributes will be missing

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "Jane",
            "last_name": None,
            "is_bot": False,  # Default value
            "is_premium": None,
            "language_code": None,
        }
        assert result == expected

    def test_extract_bot_user_profile(self):
        """Test extraction with bot user data."""
        # Arrange
        effective_user = MagicMock()
        effective_user.first_name = "TestBot"
        effective_user.last_name = None
        effective_user.is_bot = True
        effective_user.is_premium = None  # Bots typically don't have premium
        effective_user.language_code = None

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "TestBot",
            "last_name": None,
            "is_bot": True,
            "is_premium": None,
            "language_code": None,
        }
        assert result == expected

    def test_extract_premium_user_profile(self):
        """Test extraction with premium user data."""
        # Arrange
        effective_user = MagicMock()
        effective_user.first_name = "Premium"
        effective_user.last_name = "User"
        effective_user.is_bot = False
        effective_user.is_premium = True
        effective_user.language_code = "es"

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "Premium",
            "last_name": "User",
            "is_bot": False,
            "is_premium": True,
            "language_code": "es",
        }
        assert result == expected

    def test_extract_different_languages(self):
        """Test extraction with various language codes."""
        test_cases = [
            ("en", "English"),
            ("es", "Spanish"),
            ("fr", "French"),
            ("de", "German"),
            ("ru", "Russian"),
            ("zh", "Chinese"),
            ("ja", "Japanese"),
        ]

        for lang_code, description in test_cases:
            # Arrange
            effective_user = MagicMock()
            effective_user.first_name = f"User_{description}"
            effective_user.last_name = "Test"
            effective_user.is_bot = False
            effective_user.is_premium = False
            effective_user.language_code = lang_code

            # Act
            result = extract_user_profile(effective_user)

            # Assert
            assert result["language_code"] == lang_code
            assert result["first_name"] == f"User_{description}"

    def test_extract_with_none_effective_user(self):
        """Test extraction when effective_user is None."""
        # Act
        result = extract_user_profile(None)

        # Assert
        expected = {
            "first_name": None,
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }
        assert result == expected

    def test_extract_with_partial_missing_data(self):
        """Test extraction with some fields missing from effective_user."""
        # Arrange - Create object with only some attributes
        effective_user = type("MockUser", (), {})()
        effective_user.first_name = "Partial"
        effective_user.is_bot = False
        # last_name, is_premium, language_code will be missing

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "Partial",
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }
        assert result == expected

    def test_extract_with_none_values(self):
        """Test extraction when effective_user fields are explicitly None."""
        # Arrange
        effective_user = MagicMock()
        effective_user.first_name = "User"
        effective_user.last_name = None
        effective_user.is_bot = False
        effective_user.is_premium = None
        effective_user.language_code = None

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "User",
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }
        assert result == expected

    def test_extract_with_empty_strings(self):
        """Test extraction when effective_user fields are empty strings."""
        # Arrange
        effective_user = MagicMock()
        effective_user.first_name = ""
        effective_user.last_name = ""
        effective_user.is_bot = False
        effective_user.is_premium = None
        effective_user.language_code = ""

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "",
            "last_name": "",
            "is_bot": False,
            "is_premium": None,
            "language_code": "",
        }
        assert result == expected

    def test_extract_with_missing_attributes(self):
        """Test extraction when effective_user object lacks some attributes entirely."""
        # Arrange - Create object without some attributes
        effective_user = type("MockUser", (), {})()
        effective_user.first_name = "Limited"
        effective_user.is_bot = True
        # Missing: last_name, is_premium, language_code

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "Limited",
            "last_name": None,
            "is_bot": True,
            "is_premium": None,
            "language_code": None,
        }
        assert result == expected

    def test_extract_with_exception_handling(self):
        """Test extraction handles exceptions gracefully."""
        # Arrange - Create object that raises exception on attribute access
        effective_user = MagicMock()
        effective_user.first_name = "Test"

        # Make one attribute raise an exception
        type(effective_user).last_name = property(
            lambda self: (_ for _ in ()).throw(Exception("Test error"))
        )

        # Act
        result = extract_user_profile(effective_user)

        # Assert - Should return safe defaults on exception
        expected = {
            "first_name": None,
            "last_name": None,
            "is_bot": False,
            "is_premium": None,
            "language_code": None,
        }
        assert result == expected

    def test_extract_unicode_names(self):
        """Test extraction with Unicode characters in names."""
        # Arrange
        effective_user = MagicMock()
        effective_user.first_name = "José"
        effective_user.last_name = "García"
        effective_user.is_bot = False
        effective_user.is_premium = False
        effective_user.language_code = "es"

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "José",
            "last_name": "García",
            "is_bot": False,
            "is_premium": False,
            "language_code": "es",
        }
        assert result == expected

    def test_extract_long_names(self):
        """Test extraction with very long names."""
        # Arrange
        effective_user = MagicMock()
        effective_user.first_name = "A" * 100  # Very long first name
        effective_user.last_name = "B" * 100  # Very long last name
        effective_user.is_bot = False
        effective_user.is_premium = True
        effective_user.language_code = "en"

        # Act
        result = extract_user_profile(effective_user)

        # Assert
        expected = {
            "first_name": "A" * 100,
            "last_name": "B" * 100,
            "is_bot": False,
            "is_premium": True,
            "language_code": "en",
        }
        assert result == expected


class TestHasMeaningfulProfileChanges:
    """Test cases for has_meaningful_profile_changes function."""

    def test_no_changes(self):
        """Test when profiles are identical."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }
        new = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is False

    def test_first_name_change(self):
        """Test when first_name changes."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }
        new = {
            "first_name": "Jane",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is True

    def test_last_name_change(self):
        """Test when last_name changes."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }
        new = {
            "first_name": "John",
            "last_name": "Smith",
            "is_premium": True,
            "language_code": "en",
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is True

    def test_premium_status_change(self):
        """Test when premium status changes."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": False,
            "language_code": "en",
        }
        new = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is True

    def test_language_code_change(self):
        """Test when language_code changes."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }
        new = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "es",
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is True

    def test_multiple_changes(self):
        """Test when multiple fields change."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": False,
            "language_code": "en",
        }
        new = {
            "first_name": "Jane",
            "last_name": "Smith",
            "is_premium": True,
            "language_code": "es",
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is True

    def test_none_to_value_change(self):
        """Test when field changes from None to a value."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": None,
            "is_premium": None,
            "language_code": None,
        }
        new = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is True

    def test_value_to_none_change(self):
        """Test when field changes from value to None."""
        # Arrange
        current = {
            "first_name": "John",
            "last_name": "Doe",
            "is_premium": True,
            "language_code": "en",
        }
        new = {
            "first_name": "John",
            "last_name": None,
            "is_premium": None,
            "language_code": None,
        }

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert
        assert result is True

    def test_exception_handling(self):
        """Test exception handling returns True (safe default)."""
        # Arrange - Invalid profile data that might cause exceptions
        current = None  # This will cause an exception
        new = {"first_name": "John"}

        # Act
        result = has_meaningful_profile_changes(current, new)

        # Assert - Should return True on exception (safe default)
        assert result is True


class TestShouldUpdateUserProfile:
    """Test cases for should_update_user_profile function."""

    def test_should_update_with_changes(self):
        """Test when user profile should be updated due to changes."""
        # Arrange
        mock_user = MagicMock()
        mock_user.telegram_id = 12345
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        mock_user.is_bot = False
        mock_user.is_premium = False
        mock_user.language_code = "en"

        effective_user = MagicMock()
        effective_user.first_name = "Jane"  # Changed
        effective_user.last_name = "Doe"
        effective_user.is_bot = False
        effective_user.is_premium = False
        effective_user.language_code = "en"

        # Act
        result = should_update_user_profile(mock_user, effective_user)

        # Assert
        assert result is True

    def test_should_not_update_without_changes(self):
        """Test when user profile should not be updated (no changes)."""
        # Arrange
        mock_user = MagicMock()
        mock_user.telegram_id = 12345
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        mock_user.is_bot = False
        mock_user.is_premium = False
        mock_user.language_code = "en"

        effective_user = MagicMock()
        effective_user.first_name = "John"
        effective_user.last_name = "Doe"
        effective_user.is_bot = False
        effective_user.is_premium = False
        effective_user.language_code = "en"

        # Act
        result = should_update_user_profile(mock_user, effective_user)

        # Assert
        assert result is False

    def test_should_update_with_none_effective_user(self):
        """Test when effective_user is None."""
        # Arrange
        mock_user = MagicMock()
        mock_user.telegram_id = 12345
        mock_user.first_name = "John"
        mock_user.last_name = "Doe"
        mock_user.is_bot = False
        mock_user.is_premium = False
        mock_user.language_code = "en"

        # Act
        result = should_update_user_profile(mock_user, None)

        # Assert
        # Should return True because extracted profile will be all None/defaults
        # which differs from current user data
        assert result is True

    def test_should_update_exception_handling(self):
        """Test exception handling returns True (safe default)."""
        # Arrange
        mock_user = MagicMock()
        mock_user.telegram_id = 12345
        # Make user attributes raise exceptions
        type(mock_user).first_name = property(
            lambda self: (_ for _ in ()).throw(Exception("Test error"))
        )

        effective_user = MagicMock()
        effective_user.first_name = "John"

        # Act
        result = should_update_user_profile(mock_user, effective_user)

        # Assert - Should return True on exception (safe default)
        assert result is True



