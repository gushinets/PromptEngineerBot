"""
Report configuration for marketing reports.

This module provides configuration management for the marketing reports feature,
loading settings from environment variables with sensible defaults.
"""

import logging
import os
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)


@dataclass
class ReportConfig:
    """
    Configuration for marketing report generation.

    Attributes:
        generation_time: Time to generate reports in HH:MM format (default: "01:00")
        user_activity_days: Number of days to filter active users (0 = all users)
        recipient_emails: List of email addresses to receive reports
    """

    generation_time: str = "01:00"
    user_activity_days: int = 30
    recipient_emails: list[str] = field(default_factory=list)

    @classmethod
    def from_env(cls) -> "ReportConfig":
        """
        Load configuration from environment variables.

        Environment Variables:
            REPORT_GENERATION_TIME: Time to generate reports (HH:MM format, default: "01:00")
            REPORT_USER_ACTIVITY_DAYS: Days to filter active users (default: 30, 0 = all)
            REPORT_RECIPIENT_EMAILS: Comma-separated list of recipient emails

        Returns:
            ReportConfig instance with values from environment or defaults
        """
        # Parse generation time with default
        generation_time = os.getenv("REPORT_GENERATION_TIME", "01:00").strip()

        # Validate time format (HH:MM)
        if not cls._is_valid_time_format(generation_time):
            logger.warning(
                f"REPORT_CONFIG: Invalid REPORT_GENERATION_TIME '{generation_time}', "
                "using default '01:00'"
            )
            generation_time = "01:00"

        # Parse user activity days with default
        try:
            user_activity_days = int(os.getenv("REPORT_USER_ACTIVITY_DAYS", "30"))
            if user_activity_days < 0:
                logger.warning(
                    f"REPORT_CONFIG: Negative REPORT_USER_ACTIVITY_DAYS '{user_activity_days}', "
                    "using default 30"
                )
                user_activity_days = 30
        except ValueError:
            logger.warning(
                f"REPORT_CONFIG: Invalid REPORT_USER_ACTIVITY_DAYS "
                f"'{os.getenv('REPORT_USER_ACTIVITY_DAYS')}', using default 30"
            )
            user_activity_days = 30

        # Parse recipient emails (comma-separated)
        recipient_emails_str = os.getenv("REPORT_RECIPIENT_EMAILS", "").strip()
        recipient_emails: list[str] = []

        if recipient_emails_str:
            # Split by comma and strip whitespace from each email
            recipient_emails = [
                email.strip() for email in recipient_emails_str.split(",") if email.strip()
            ]

        # Log warning if no recipients configured (per requirement 1.5)
        if not recipient_emails:
            logger.error(
                "REPORT_CONFIG: REPORT_RECIPIENT_EMAILS is not configured or empty. "
                "Report delivery will be skipped."
            )

        return cls(
            generation_time=generation_time,
            user_activity_days=user_activity_days,
            recipient_emails=recipient_emails,
        )

    @staticmethod
    def _is_valid_time_format(time_str: str) -> bool:
        """
        Validate time string is in HH:MM format.

        Args:
            time_str: Time string to validate

        Returns:
            True if valid HH:MM format, False otherwise
        """
        if not time_str or ":" not in time_str:
            return False

        parts = time_str.split(":")
        if len(parts) != 2:
            return False

        try:
            hour = int(parts[0])
            minute = int(parts[1])
        except ValueError:
            return False
        else:
            return 0 <= hour <= 23 and 0 <= minute <= 59

    def has_recipients(self) -> bool:
        """
        Check if there are any configured recipients.

        Returns:
            True if at least one recipient email is configured
        """
        return len(self.recipient_emails) > 0
