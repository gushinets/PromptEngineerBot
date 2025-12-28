"""Property-based tests for ReportService retry behavior.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 11: Retry Behavior**
**Validates: Requirements 6.1, 6.2**
"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from telegram_bot.services.report_config import ReportConfig
from telegram_bot.services.report_models import ReportResult
from telegram_bot.services.report_service import RETRY_DELAYS, ReportService


# Strategy for generating report dates
report_date_strategy = st.dates(
    min_value=date(2020, 1, 1),
    max_value=date(2030, 12, 31),
)

# Strategy for generating error messages
error_message_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P", "S")),
    min_size=1,
    max_size=100,
)


class TestRetryBehavior:
    """
    **Feature: marketing-reports, Property 11: Retry Behavior**
    **Validates: Requirements 6.1, 6.2**

    Property 11: Retry Behavior
    *For any* report generation that fails, the system should retry exactly
    3 times with delays of 1, 5, and 15 minutes before logging failure.
    """

    def test_retry_delays_are_correct(self):
        """
        **Feature: marketing-reports, Property 11: Retry Behavior**
        **Validates: Requirements 6.2**

        Verify that RETRY_DELAYS constant has the correct values:
        1 minute (60s), 5 minutes (300s), 15 minutes (900s).
        """
        assert RETRY_DELAYS == [60, 300, 900], (
            f"RETRY_DELAYS should be [60, 300, 900], got: {RETRY_DELAYS}"
        )

    @pytest.mark.asyncio
    @given(
        report_date=report_date_strategy,
        error_message=error_message_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    async def test_retry_attempts_exactly_three_times_on_failure(
        self,
        report_date: date,
        error_message: str,
    ):
        """
        **Feature: marketing-reports, Property 11: Retry Behavior**
        **Validates: Requirements 6.1**

        For any report generation that consistently fails, the system should
        attempt exactly 3 times before giving up.
        """
        # Create mock dependencies
        mock_db_session = MagicMock()
        mock_email_service = MagicMock()
        mock_config = ReportConfig(
            generation_time="01:00",
            user_activity_days=30,
            recipient_emails=["test@example.com"],
        )

        # Create service
        service = ReportService(
            db_session=mock_db_session,
            email_service=mock_email_service,
            config=mock_config,
        )

        # Track call count
        call_count = 0

        async def mock_generate_and_send(**kwargs):
            nonlocal call_count
            call_count += 1
            return ReportResult(
                success=False,
                user_summary_rows=0,
                daily_metrics_generated=False,
                sessions_exported=0,
                query_timings=[],
                total_query_time_ms=0.0,
                total_execution_time_ms=0.0,
                error=error_message,
            )

        # Patch generate_and_send_reports and asyncio.sleep
        with (
            patch.object(service, "generate_and_send_reports", side_effect=mock_generate_and_send),
            patch("telegram_bot.services.report_service.asyncio.sleep", new_callable=AsyncMock),
        ):
            # Run the retry method
            result = await service.generate_and_send_reports_with_retry(report_date=report_date)

        # Property: Should attempt exactly 3 times
        assert call_count == 3, (
            f"Should attempt exactly 3 times on consistent failure, got: {call_count}"
        )

        # Property: Final result should indicate failure
        assert result.success is False, "Result should indicate failure after all retries"

    @pytest.mark.asyncio
    @given(
        report_date=report_date_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    async def test_retry_uses_correct_delays(
        self,
        report_date: date,
    ):
        """
        **Feature: marketing-reports, Property 11: Retry Behavior**
        **Validates: Requirements 6.2**

        For any report generation that fails, the retry delays should be
        1 minute, 5 minutes, and 15 minutes (60, 300, 900 seconds).
        """
        # Create mock dependencies
        mock_db_session = MagicMock()
        mock_email_service = MagicMock()
        mock_config = ReportConfig(
            generation_time="01:00",
            user_activity_days=30,
            recipient_emails=["test@example.com"],
        )

        # Create service
        service = ReportService(
            db_session=mock_db_session,
            email_service=mock_email_service,
            config=mock_config,
        )

        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        async def mock_generate_and_send(**kwargs):
            return ReportResult(
                success=False,
                user_summary_rows=0,
                daily_metrics_generated=False,
                sessions_exported=0,
                query_timings=[],
                total_query_time_ms=0.0,
                total_execution_time_ms=0.0,
                error="Test failure",
            )

        # Patch generate_and_send_reports and asyncio.sleep
        with (
            patch.object(service, "generate_and_send_reports", side_effect=mock_generate_and_send),
            patch(
                "telegram_bot.services.report_service.asyncio.sleep",
                side_effect=mock_sleep,
            ),
        ):
            # Run the retry method
            await service.generate_and_send_reports_with_retry(report_date=report_date)

        # Property: Should have called sleep with correct delays
        # After 1st failure: wait 60s, after 2nd failure: wait 300s
        # After 3rd failure: no more sleep (exhausted)
        expected_delays = [60, 300]  # Only 2 sleeps for 3 attempts
        assert sleep_calls == expected_delays, (
            f"Sleep delays should be {expected_delays}, got: {sleep_calls}"
        )

    @pytest.mark.asyncio
    @given(
        report_date=report_date_strategy,
        success_on_attempt=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    async def test_retry_stops_on_success(
        self,
        report_date: date,
        success_on_attempt: int,
    ):
        """
        **Feature: marketing-reports, Property 11: Retry Behavior**
        **Validates: Requirements 6.1**

        For any report generation that succeeds on attempt N (1-3),
        the system should stop retrying and return success.
        """
        # Create mock dependencies
        mock_db_session = MagicMock()
        mock_email_service = MagicMock()
        mock_config = ReportConfig(
            generation_time="01:00",
            user_activity_days=30,
            recipient_emails=["test@example.com"],
        )

        # Create service
        service = ReportService(
            db_session=mock_db_session,
            email_service=mock_email_service,
            config=mock_config,
        )

        # Track call count
        call_count = 0

        async def mock_generate_and_send(**kwargs):
            nonlocal call_count
            call_count += 1
            # Succeed on the specified attempt
            if call_count >= success_on_attempt:
                return ReportResult(
                    success=True,
                    user_summary_rows=10,
                    daily_metrics_generated=True,
                    sessions_exported=5,
                    query_timings=[],
                    total_query_time_ms=100.0,
                    total_execution_time_ms=200.0,
                    error=None,
                )
            return ReportResult(
                success=False,
                user_summary_rows=0,
                daily_metrics_generated=False,
                sessions_exported=0,
                query_timings=[],
                total_query_time_ms=0.0,
                total_execution_time_ms=0.0,
                error="Test failure",
            )

        # Patch generate_and_send_reports and asyncio.sleep
        with (
            patch.object(service, "generate_and_send_reports", side_effect=mock_generate_and_send),
            patch("telegram_bot.services.report_service.asyncio.sleep", new_callable=AsyncMock),
        ):
            # Run the retry method
            result = await service.generate_and_send_reports_with_retry(report_date=report_date)

        # Property: Should stop at the successful attempt
        assert call_count == success_on_attempt, (
            f"Should stop at attempt {success_on_attempt}, but made {call_count} attempts"
        )

        # Property: Result should indicate success
        assert result.success is True, "Result should indicate success"

    @pytest.mark.asyncio
    @given(
        report_date=report_date_strategy,
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    async def test_retry_handles_exceptions(
        self,
        report_date: date,
    ):
        """
        **Feature: marketing-reports, Property 11: Retry Behavior**
        **Validates: Requirements 6.1**

        For any report generation that raises an exception, the system
        should catch it and retry up to 3 times.
        """
        # Create mock dependencies
        mock_db_session = MagicMock()
        mock_email_service = MagicMock()
        mock_config = ReportConfig(
            generation_time="01:00",
            user_activity_days=30,
            recipient_emails=["test@example.com"],
        )

        # Create service
        service = ReportService(
            db_session=mock_db_session,
            email_service=mock_email_service,
            config=mock_config,
        )

        # Track call count
        call_count = 0
        error_msg = "Database connection failed"

        async def mock_generate_and_send(**kwargs):
            nonlocal call_count
            call_count += 1
            raise RuntimeError(error_msg)

        # Patch generate_and_send_reports and asyncio.sleep
        with (
            patch.object(service, "generate_and_send_reports", side_effect=mock_generate_and_send),
            patch("telegram_bot.services.report_service.asyncio.sleep", new_callable=AsyncMock),
        ):
            # Run the retry method
            result = await service.generate_and_send_reports_with_retry(report_date=report_date)

        # Property: Should attempt exactly 3 times even with exceptions
        assert call_count == 3, f"Should attempt exactly 3 times on exceptions, got: {call_count}"

        # Property: Final result should indicate failure
        assert result.success is False, "Result should indicate failure after all retries"
        assert result.error is not None, "Error message should be set"
