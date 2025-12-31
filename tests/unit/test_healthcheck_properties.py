"""Property-based tests for healthcheck script.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the Docker
configuration improvements feature.

**Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
**Validates: Requirements 4.1, 4.3**
"""

import os
import sys
from unittest.mock import MagicMock, patch

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


# Add scripts directory to path for importing healthcheck
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))

from healthcheck import check_telegram, check_telegram_httpx, check_telegram_urllib


# Strategy for generating invalid tokens (non-empty strings that are not valid Telegram tokens)
# Valid Telegram tokens have format: <bot_id>:<alphanumeric_string>
# We generate strings that don't match this pattern
# Note: We exclude null characters (\x00) as they cannot be set as environment variables
invalid_token_strategy = st.one_of(
    # Empty-ish strings
    st.just(""),
    st.text(alphabet=st.characters(whitelist_categories=("L", "N")), min_size=1, max_size=50),
    # Strings without colon
    st.text(alphabet=st.characters(whitelist_categories=("L", "N")), min_size=5, max_size=30),
    # Strings with invalid format (exclude null characters for env var compatibility)
    st.text(
        alphabet=st.characters(blacklist_characters="\x00"),
        min_size=1,
        max_size=100,
    ).filter(lambda x: ":" not in x or x.count(":") > 1),
)


class TestHealthcheckInvalidToken:
    """
    **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
    **Validates: Requirements 4.1, 4.3**

    Property 2: Healthcheck Failure on Invalid/Missing Token
    *For any* invalid or missing Telegram bot token, when the healthcheck script
    is executed, the script SHALL exit with code 1.
    """

    def test_missing_token_returns_false(self):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1, 4.3**

        When TELEGRAM_TOKEN is not set, check_telegram should return False.
        """
        # Ensure TELEGRAM_TOKEN is not set
        with patch.dict(os.environ, {}, clear=True):
            # Remove TELEGRAM_TOKEN if it exists
            os.environ.pop("TELEGRAM_TOKEN", None)
            result = check_telegram()

        assert result is False, "check_telegram should return False when TELEGRAM_TOKEN is missing"

    def test_empty_token_returns_false(self):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1, 4.3**

        When TELEGRAM_TOKEN is empty string, check_telegram should return False.
        """
        with patch.dict(os.environ, {"TELEGRAM_TOKEN": ""}, clear=True):
            result = check_telegram()

        assert result is False, "check_telegram should return False when TELEGRAM_TOKEN is empty"

    @given(invalid_token=invalid_token_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_token_httpx_returns_false(self, invalid_token: str):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1, 4.3**

        For any invalid token string, check_telegram_httpx should return False
        when the Telegram API rejects the token.
        """
        import httpx

        # Mock httpx.get to simulate API rejection for invalid tokens
        mock_response = MagicMock()
        mock_response.status_code = 401  # Unauthorized
        mock_response.json.return_value = {"ok": False, "error_code": 401}

        with patch.object(httpx, "get", return_value=mock_response):
            result = check_telegram_httpx(invalid_token)

        assert result is False, (
            f"check_telegram_httpx should return False for invalid token: {invalid_token!r}"
        )

    @given(invalid_token=invalid_token_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_token_urllib_returns_false(self, invalid_token: str):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1, 4.3**

        For any invalid token string, check_telegram_urllib should return False
        when the Telegram API rejects the token.
        """
        import urllib.request
        from urllib.error import HTTPError

        # Mock urllib to simulate API rejection for invalid tokens
        with patch.object(urllib.request, "urlopen") as mock_urlopen:
            # Simulate 401 Unauthorized response
            mock_urlopen.side_effect = HTTPError(
                url=f"https://api.telegram.org/bot{invalid_token}/getMe",
                code=401,
                msg="Unauthorized",
                hdrs={},
                fp=None,
            )
            result = check_telegram_urllib(invalid_token)

        assert result is False, (
            f"check_telegram_urllib should return False for invalid token: {invalid_token!r}"
        )

    @given(invalid_token=invalid_token_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_invalid_token_check_telegram_returns_false(self, invalid_token: str):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1, 4.3**

        For any invalid token string set in environment, check_telegram should
        return False when the Telegram API rejects the token.
        """
        import httpx

        # Mock httpx.get to simulate API rejection
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"ok": False}

        with (
            patch.dict(os.environ, {"TELEGRAM_TOKEN": invalid_token}),
            patch.object(httpx, "get", return_value=mock_response),
        ):
            result = check_telegram()

        # Empty token should return False immediately without API call
        if not invalid_token:
            assert result is False, "check_telegram should return False for empty token"
        else:
            assert result is False, (
                f"check_telegram should return False for invalid token: {invalid_token!r}"
            )


class TestHealthcheckNetworkErrors:
    """
    **Feature: docker-config-improvements, Property 3: Healthcheck Timeout Handling**
    **Validates: Requirements 4.3**

    Property 3: Healthcheck Timeout Handling
    *For any* network condition where the Telegram API does not respond within
    the timeout period, the healthcheck script SHALL exit with code 1 rather
    than hanging indefinitely.
    """

    @given(token=st.text(min_size=10, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_httpx_timeout_returns_false(self, token: str):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.3**

        For any token, when httpx times out, check_telegram_httpx should return False.
        """
        import httpx

        with patch.object(httpx, "get", side_effect=httpx.TimeoutException("Connection timed out")):
            result = check_telegram_httpx(token)

        assert result is False, "check_telegram_httpx should return False on timeout"

    @given(token=st.text(min_size=10, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_httpx_connection_error_returns_false(self, token: str):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.3**

        For any token, when httpx has connection error, check_telegram_httpx should return False.
        """
        import httpx

        with patch.object(httpx, "get", side_effect=httpx.ConnectError("Connection refused")):
            result = check_telegram_httpx(token)

        assert result is False, "check_telegram_httpx should return False on connection error"

    @given(token=st.text(min_size=10, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_urllib_timeout_returns_false(self, token: str):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.3**

        For any token, when urllib times out, check_telegram_urllib should return False.
        """
        import urllib.request
        from urllib.error import URLError

        with patch.object(urllib.request, "urlopen", side_effect=URLError("Connection timed out")):
            result = check_telegram_urllib(token)

        assert result is False, "check_telegram_urllib should return False on timeout"

    @given(token=st.text(min_size=10, max_size=50))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_urllib_connection_error_returns_false(self, token: str):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.3**

        For any token, when urllib has connection error, check_telegram_urllib should return False.
        """
        import urllib.request
        from urllib.error import URLError

        with patch.object(urllib.request, "urlopen", side_effect=URLError("Connection refused")):
            result = check_telegram_urllib(token)

        assert result is False, "check_telegram_urllib should return False on connection error"


class TestHealthcheckApiResponse:
    """
    Additional tests for API response handling.
    **Validates: Requirements 4.1, 4.2, 4.3**
    """

    def test_httpx_ok_false_returns_false(self):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1**

        When API returns ok=False, check_telegram_httpx should return False.
        """
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": False}

        with patch.object(httpx, "get", return_value=mock_response):
            result = check_telegram_httpx("some_token")

        assert result is False, "check_telegram_httpx should return False when API returns ok=False"

    def test_urllib_ok_false_returns_false(self):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1**

        When API returns ok=False, check_telegram_urllib should return False.
        """
        import json
        import urllib.request

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": False}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch.object(urllib.request, "urlopen", return_value=mock_response):
            result = check_telegram_urllib("some_token")

        assert result is False, (
            "check_telegram_urllib should return False when API returns ok=False"
        )

    def test_httpx_non_200_status_returns_false(self):
        """
        **Feature: docker-config-improvements, Property 2: Healthcheck Failure on Invalid/Missing Token**
        **Validates: Requirements 4.1**

        When API returns non-200 status, check_telegram_httpx should return False.
        """
        import httpx

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"ok": False}

        with patch.object(httpx, "get", return_value=mock_response):
            result = check_telegram_httpx("some_token")

        assert result is False, "check_telegram_httpx should return False on non-200 status"
