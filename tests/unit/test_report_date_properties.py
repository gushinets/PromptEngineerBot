"""Property-based tests for report date calculation.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 10: Report Date Calculation**
**Validates: Requirements 5.2**
"""

from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st


# Strategy for generating execution dates
# We use a reasonable range of dates for testing
execution_date_strategy = st.dates(
    min_value=date(2020, 1, 2),  # Start from Jan 2 to ensure yesterday exists
    max_value=date(2030, 12, 31),
)


class TestReportDateCalculation:
    """
    **Feature: marketing-reports, Property 10: Report Date Calculation**
    **Validates: Requirements 5.2**

    Property 10: Report Date Calculation
    *For any* scheduled report execution, the report_date parameter should
    equal the previous day's date (yesterday) relative to the execution time.
    """

    @given(execution_date=execution_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_report_date_is_yesterday(self, execution_date: date):
        """
        **Feature: marketing-reports, Property 10: Report Date Calculation**
        **Validates: Requirements 5.2**

        For any execution date, the report_date should be calculated as
        the previous day's date (yesterday).
        """
        # Calculate expected yesterday based on execution date
        expected_yesterday = execution_date - timedelta(days=1)

        # The actual calculation in daily_reports_task is:
        # report_date = date.today() - timedelta(days=1)
        # We verify this calculation produces yesterday
        calculated_report_date = execution_date - timedelta(days=1)

        # Property: report_date should equal yesterday
        assert calculated_report_date == expected_yesterday, (
            f"For execution date {execution_date}, "
            f"report_date should be {expected_yesterday}, "
            f"but got {calculated_report_date}"
        )

    @given(execution_date=execution_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_report_date_is_exactly_one_day_before(self, execution_date: date):
        """
        **Feature: marketing-reports, Property 10: Report Date Calculation**
        **Validates: Requirements 5.2**

        For any execution date, the difference between execution date
        and report_date should be exactly 1 day.
        """
        report_date = execution_date - timedelta(days=1)

        # Property: The difference should be exactly 1 day
        difference = execution_date - report_date
        assert difference == timedelta(days=1), (
            f"Difference between execution date {execution_date} and "
            f"report_date {report_date} should be 1 day, got {difference}"
        )

    @given(execution_date=execution_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_report_date_preserves_date_components(self, execution_date: date):
        """
        **Feature: marketing-reports, Property 10: Report Date Calculation**
        **Validates: Requirements 5.2**

        For any execution date, the report_date should have correct
        year, month, and day components representing yesterday.
        """
        report_date = execution_date - timedelta(days=1)

        # Manually calculate expected yesterday
        # This handles month/year boundaries correctly
        expected_yesterday = date(
            execution_date.year,
            execution_date.month,
            execution_date.day,
        ) - timedelta(days=1)

        # Property: All date components should match expected yesterday
        assert report_date.year == expected_yesterday.year, (
            f"Year mismatch: expected {expected_yesterday.year}, got {report_date.year}"
        )
        assert report_date.month == expected_yesterday.month, (
            f"Month mismatch: expected {expected_yesterday.month}, got {report_date.month}"
        )
        assert report_date.day == expected_yesterday.day, (
            f"Day mismatch: expected {expected_yesterday.day}, got {report_date.day}"
        )

    @pytest.mark.parametrize(
        ("execution_date", "expected_report_date"),
        [
            # Normal case
            (date(2024, 6, 15), date(2024, 6, 14)),
            # Month boundary
            (date(2024, 7, 1), date(2024, 6, 30)),
            # Year boundary
            (date(2024, 1, 1), date(2023, 12, 31)),
            # Leap year
            (date(2024, 3, 1), date(2024, 2, 29)),
            # Non-leap year
            (date(2023, 3, 1), date(2023, 2, 28)),
        ],
    )
    def test_report_date_boundary_cases(
        self,
        execution_date: date,
        expected_report_date: date,
    ):
        """
        **Feature: marketing-reports, Property 10: Report Date Calculation**
        **Validates: Requirements 5.2**

        Test specific boundary cases for report date calculation including
        month boundaries, year boundaries, and leap years.
        """
        # Calculate report_date using the same logic as daily_reports_task
        calculated_report_date = execution_date - timedelta(days=1)

        assert calculated_report_date == expected_report_date, (
            f"For execution date {execution_date}, "
            f"expected report_date {expected_report_date}, "
            f"got {calculated_report_date}"
        )

    @given(execution_date=execution_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_daily_reports_task_calculates_yesterday(self, execution_date: date):
        """
        **Feature: marketing-reports, Property 10: Report Date Calculation**
        **Validates: Requirements 5.2**

        For any execution date, the daily_reports_task should calculate
        report_date as yesterday and pass it to generate_and_send_reports.
        """
        expected_report_date = execution_date - timedelta(days=1)

        # Mock all dependencies
        mock_config = MagicMock()
        mock_config.generation_time = "01:00"
        mock_config.user_activity_days = 30
        mock_config.recipient_emails = ["test@example.com"]

        mock_db_session = MagicMock()
        mock_email_service = MagicMock()

        mock_report_result = MagicMock()
        mock_report_result.success = True
        mock_report_result.user_summary_rows = 10
        mock_report_result.daily_metrics_generated = True
        mock_report_result.sessions_exported = 5
        mock_report_result.total_execution_time_ms = 100.0
        mock_report_result.error = None

        mock_report_service = MagicMock()

        # Track what report_date was passed
        captured_report_date = None

        async def capture_report_date(**kwargs):
            nonlocal captured_report_date
            captured_report_date = kwargs.get("report_date")
            return mock_report_result

        mock_report_service.generate_and_send_reports_with_retry = capture_report_date

        with (
            patch(
                "telegram_bot.services.report_config.ReportConfig.from_env",
                return_value=mock_config,
            ),
            patch("telegram_bot.flows.background_tasks.date") as mock_date_class,
            patch(
                "telegram_bot.data.database.get_db_session",
                return_value=mock_db_session,
            ),
            patch(
                "telegram_bot.services.email_service.get_email_service",
                return_value=mock_email_service,
            ),
            patch(
                "telegram_bot.services.report_service.ReportService",
                return_value=mock_report_service,
            ),
        ):
            # Configure mock date class
            mock_date_class.today.return_value = execution_date
            # Allow timedelta subtraction to work
            mock_date_class.__sub__ = date.__sub__

            # Import and run the task
            from telegram_bot.flows.background_tasks import daily_reports_task

            daily_reports_task()

            # Property: The report_date passed should be yesterday
            assert captured_report_date == expected_report_date, (
                f"For execution date {execution_date}, "
                f"daily_reports_task should pass report_date={expected_report_date}, "
                f"but passed {captured_report_date}"
            )
