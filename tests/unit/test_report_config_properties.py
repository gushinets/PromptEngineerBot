"""Property-based tests for ReportConfig configuration parsing.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 1: Configuration Parsing Consistency**
**Validates: Requirements 1.1, 1.2, 1.4**
"""

import os
from unittest.mock import patch

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from telegram_bot.services.report_config import ReportConfig


# Strategy for generating valid time strings in HH:MM format
valid_time_strategy = st.builds(
    lambda h, m: f"{h:02d}:{m:02d}",
    h=st.integers(min_value=0, max_value=23),
    m=st.integers(min_value=0, max_value=59),
)

# Strategy for generating valid user activity days (non-negative integers)
valid_activity_days_strategy = st.integers(min_value=0, max_value=365)

# Strategy for generating simple valid email addresses (faster than st.emails())
# Format: local@domain.tld where local and domain are alphanumeric
simple_email_strategy = st.builds(
    lambda local, domain, tld: f"{local}@{domain}.{tld}",
    local=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=10),
    domain=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=1, max_size=10),
    tld=st.sampled_from(["com", "org", "net", "io", "co"]),
)

# Strategy for generating lists of valid email addresses
valid_email_list_strategy = st.lists(simple_email_strategy, min_size=0, max_size=5)


class TestConfigurationParsingConsistency:
    """
    **Feature: marketing-reports, Property 1: Configuration Parsing Consistency**
    **Validates: Requirements 1.1, 1.2, 1.4**

    Property 1: Configuration Parsing Consistency
    *For any* valid environment configuration with REPORT_GENERATION_TIME,
    REPORT_USER_ACTIVITY_DAYS, and REPORT_RECIPIENT_EMAILS, parsing and then
    serializing the configuration should produce equivalent values.
    """

    @given(
        generation_time=valid_time_strategy,
        user_activity_days=valid_activity_days_strategy,
        recipient_emails=valid_email_list_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_config_parsing_preserves_generation_time(
        self,
        generation_time: str,
        user_activity_days: int,
        recipient_emails: list[str],
    ):
        """
        **Feature: marketing-reports, Property 1: Configuration Parsing Consistency**
        **Validates: Requirements 1.1**

        For any valid REPORT_GENERATION_TIME in HH:MM format, parsing from
        environment should preserve the exact time value.
        """
        # Build the comma-separated email string
        emails_str = ",".join(recipient_emails)

        # Mock environment variables
        env_vars = {
            "REPORT_GENERATION_TIME": generation_time,
            "REPORT_USER_ACTIVITY_DAYS": str(user_activity_days),
            "REPORT_RECIPIENT_EMAILS": emails_str,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ReportConfig.from_env()

            # Property: generation_time should be preserved exactly
            assert config.generation_time == generation_time, (
                f"generation_time should be '{generation_time}', got: '{config.generation_time}'"
            )

    @given(
        generation_time=valid_time_strategy,
        user_activity_days=valid_activity_days_strategy,
        recipient_emails=valid_email_list_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_config_parsing_preserves_user_activity_days(
        self,
        generation_time: str,
        user_activity_days: int,
        recipient_emails: list[str],
    ):
        """
        **Feature: marketing-reports, Property 1: Configuration Parsing Consistency**
        **Validates: Requirements 1.2**

        For any valid REPORT_USER_ACTIVITY_DAYS (non-negative integer), parsing
        from environment should preserve the exact value.
        """
        # Build the comma-separated email string
        emails_str = ",".join(recipient_emails)

        # Mock environment variables
        env_vars = {
            "REPORT_GENERATION_TIME": generation_time,
            "REPORT_USER_ACTIVITY_DAYS": str(user_activity_days),
            "REPORT_RECIPIENT_EMAILS": emails_str,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ReportConfig.from_env()

            # Property: user_activity_days should be preserved exactly
            assert config.user_activity_days == user_activity_days, (
                f"user_activity_days should be {user_activity_days}, "
                f"got: {config.user_activity_days}"
            )

    @given(
        generation_time=valid_time_strategy,
        user_activity_days=valid_activity_days_strategy,
        recipient_emails=valid_email_list_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_config_parsing_preserves_recipient_emails(
        self,
        generation_time: str,
        user_activity_days: int,
        recipient_emails: list[str],
    ):
        """
        **Feature: marketing-reports, Property 1: Configuration Parsing Consistency**
        **Validates: Requirements 1.4**

        For any valid comma-separated list of REPORT_RECIPIENT_EMAILS, parsing
        from environment should preserve all email addresses in order.
        """
        # Build the comma-separated email string
        emails_str = ",".join(recipient_emails)

        # Mock environment variables
        env_vars = {
            "REPORT_GENERATION_TIME": generation_time,
            "REPORT_USER_ACTIVITY_DAYS": str(user_activity_days),
            "REPORT_RECIPIENT_EMAILS": emails_str,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ReportConfig.from_env()

            # Property: recipient_emails should be preserved exactly
            assert config.recipient_emails == recipient_emails, (
                f"recipient_emails should be {recipient_emails}, got: {config.recipient_emails}"
            )

    @given(
        generation_time=valid_time_strategy,
        user_activity_days=valid_activity_days_strategy,
        recipient_emails=valid_email_list_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_config_round_trip_consistency(
        self,
        generation_time: str,
        user_activity_days: int,
        recipient_emails: list[str],
    ):
        """
        **Feature: marketing-reports, Property 1: Configuration Parsing Consistency**
        **Validates: Requirements 1.1, 1.2, 1.4**

        For any valid configuration, parsing from environment and then
        comparing all fields should produce equivalent values to the original
        input - demonstrating full round-trip consistency.
        """
        # Build the comma-separated email string
        emails_str = ",".join(recipient_emails)

        # Mock environment variables
        env_vars = {
            "REPORT_GENERATION_TIME": generation_time,
            "REPORT_USER_ACTIVITY_DAYS": str(user_activity_days),
            "REPORT_RECIPIENT_EMAILS": emails_str,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ReportConfig.from_env()

            # Property: All fields should match the original input
            assert config.generation_time == generation_time
            assert config.user_activity_days == user_activity_days
            assert config.recipient_emails == recipient_emails

    @given(
        recipient_emails=st.lists(
            st.tuples(simple_email_strategy, st.text(alphabet=" \t", max_size=3)),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_config_parsing_strips_whitespace_from_emails(
        self,
        recipient_emails: list[tuple[str, str]],
    ):
        """
        **Feature: marketing-reports, Property 1: Configuration Parsing Consistency**
        **Validates: Requirements 1.4**

        For any email addresses with surrounding whitespace, parsing should
        strip the whitespace and preserve the core email address.
        """
        # Build emails with random whitespace padding
        padded_emails = [f"{ws}{email}{ws}" for email, ws in recipient_emails]
        expected_emails = [email for email, _ in recipient_emails]
        emails_str = ",".join(padded_emails)

        # Mock environment variables
        env_vars = {
            "REPORT_GENERATION_TIME": "01:00",
            "REPORT_USER_ACTIVITY_DAYS": "30",
            "REPORT_RECIPIENT_EMAILS": emails_str,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = ReportConfig.from_env()

            # Property: emails should be stripped of whitespace
            assert config.recipient_emails == expected_emails, (
                f"recipient_emails should be {expected_emails}, got: {config.recipient_emails}"
            )
