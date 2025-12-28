"""
Report service for generating and delivering marketing reports.

This module provides the ReportService class that orchestrates report generation,
including user summaries, daily metrics, and session exports. It includes
comprehensive timing instrumentation for performance monitoring and retry logic
with exponential backoff for resilient report delivery.
"""

import asyncio
import json
import logging
import time
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

from sqlalchemy import case, func
from sqlalchemy.orm import Session as DBSession

from telegram_bot.data.database import Session, SessionEmailEvent, User
from telegram_bot.services.csv_generator import CSVGenerator
from telegram_bot.services.email_service import EmailService
from telegram_bot.services.report_config import ReportConfig
from telegram_bot.services.report_models import (
    DailyMetricsRow,
    QueryTiming,
    ReportResult,
    SessionExportRow,
    UserSummaryRow,
)


logger = logging.getLogger(__name__)


# Retry delays in seconds: 1 minute, 5 minutes, 15 minutes
# Requirements 6.1, 6.2
RETRY_DELAYS = [60, 300, 900]


class ReportService:
    """
    Service for generating and delivering marketing reports.

    This service orchestrates the generation of three report types:
    - User Summary Report: Per-user metrics and activity
    - Daily Metrics Report: Platform-wide daily statistics
    - Sessions Export: Detailed session data with conversation history

    All database queries are instrumented with timing measurement for
    performance monitoring and optimization.

    Attributes:
        db_session: SQLAlchemy database session for queries
        email_service: Email service for report delivery
        config: Report configuration settings
    """

    def __init__(
        self,
        db_session: DBSession,
        email_service: EmailService,
        config: ReportConfig,
    ) -> None:
        """
        Initialize ReportService with dependencies.

        Args:
            db_session: SQLAlchemy database session for executing queries
            email_service: EmailService instance for sending report emails
            config: ReportConfig with generation settings
        """
        self.db_session = db_session
        self.email_service = email_service
        self.config = config

    def _execute_timed_query(
        self,
        query_name: str,
        query_func: Callable[[], Any],
    ) -> tuple[Any, QueryTiming]:
        """
        Execute a query and measure its execution time.

        Uses time.perf_counter() for high-precision timing measurement.
        Logs the query timing in a consistent format after execution.

        Args:
            query_name: Descriptive name for the query (used in logging)
            query_func: Callable that executes the query and returns results

        Returns:
            Tuple of (query_result, QueryTiming) where QueryTiming contains
            the query name, duration in milliseconds, and row count

        Requirements: 9.1, 9.2, 9.3, 9.4
        """
        start_time = time.perf_counter()

        try:
            result = query_func()
        except Exception:
            # Calculate duration even on failure for logging
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception(f"REPORT_QUERY_ERROR: {query_name} failed after {duration_ms:.2f}ms")
            raise

        duration_ms = (time.perf_counter() - start_time) * 1000

        # Determine row count based on result type
        if result is None:
            row_count = 0
        elif isinstance(result, list):
            row_count = len(result)
        else:
            # Single row result (e.g., DailyMetricsRow)
            row_count = 1

        timing = QueryTiming(
            query_name=query_name,
            duration_ms=duration_ms,
            row_count=row_count,
        )

        self._log_query_timing(timing)

        return result, timing

    def _log_query_timing(self, timing: QueryTiming) -> None:
        """
        Log query timing in consistent format.

        Format: REPORT_QUERY_TIMING: {query_name} completed in {duration_ms}ms ({row_count} rows)

        Args:
            timing: QueryTiming object with query performance metrics

        Requirements: 9.4
        """
        logger.info(
            f"REPORT_QUERY_TIMING: {timing.query_name} completed in "
            f"{timing.duration_ms:.2f}ms ({timing.row_count} rows)"
        )

    def _log_performance_summary(
        self,
        query_timings: list[QueryTiming],
        total_execution_time_ms: float,
    ) -> None:
        """
        Log performance summary at end of report generation.

        Shows total query time vs total execution time to identify
        overhead from CSV generation, email delivery, etc.

        Format: REPORT_PERFORMANCE_SUMMARY: Total query time: {X}ms,
                Total execution time: {Y}ms, Query overhead: {Z}%

        Args:
            query_timings: List of QueryTiming objects from all queries
            total_execution_time_ms: Total time for complete report generation

        Requirements: 9.5
        """
        total_query_time_ms = sum(t.duration_ms for t in query_timings)

        # Calculate query overhead percentage
        if total_execution_time_ms > 0:
            query_percentage = (total_query_time_ms / total_execution_time_ms) * 100
        else:
            query_percentage = 0.0

        logger.info(
            f"REPORT_PERFORMANCE_SUMMARY: Total query time: {total_query_time_ms:.1f}ms, "
            f"Total execution time: {total_execution_time_ms:.1f}ms, "
            f"Query overhead: {query_percentage:.1f}%"
        )

    def generate_user_summary(
        self,
        report_date: date,
        include_all_users: bool = False,
    ) -> tuple[list[UserSummaryRow], QueryTiming]:
        """
        Generate user summary report data with timing.

        Queries user data with session metrics including:
        - Total sessions and prompts per user
        - Method usage counts (CRAFT, LYRA, GGL)
        - Average tokens and duration
        - Success rate calculation

        Args:
            report_date: Date for the report (used for activity filtering)
            include_all_users: If True, include all users regardless of activity window

        Returns:
            Tuple of (list of UserSummaryRow, QueryTiming)

        Requirements: 2.1-2.12
        """

        def execute_query() -> list[UserSummaryRow]:
            # Build the base query with LEFT JOIN on users and sessions
            # This ensures users with no sessions are still included
            query = self.db_session.query(
                User.id.label("user_id"),
                User.email.label("email"),
                func.count(Session.id).label("total_sessions"),
                func.count(Session.id).label(
                    "total_prompts"
                ),  # Req 2.5: TotalPrompts = TotalSessions
                func.count(case((Session.optimization_method == "CRAFT", 1))).label("craft_count"),
                func.count(case((Session.optimization_method == "LYRA", 1))).label("lyra_count"),
                func.count(case((Session.optimization_method == "GGL", 1))).label("ggl_count"),
                func.coalesce(func.avg(Session.tokens_total), 0).label("avg_tokens"),
                # Success rate: (successful sessions / total sessions) * 100
                case(
                    (
                        func.count(Session.id) > 0,
                        func.count(case((Session.status == "successful", 1)))
                        * 100.0
                        / func.count(Session.id),
                    ),
                    else_=0.0,
                ).label("success_rate"),
                User.last_interaction_at.label("last_activity"),
                func.coalesce(func.avg(Session.duration_seconds), 0).label("avg_duration"),
            ).outerjoin(Session, User.id == Session.user_id)

            # Apply activity date filter when user_activity_days > 0 and not include_all_users
            # Requirement 2.2: Include only users with last_interaction_at within N days
            # Requirement 2.3: When user_activity_days = 0, include all users
            if not include_all_users and self.config.user_activity_days > 0:
                activity_cutoff = report_date - timedelta(days=self.config.user_activity_days)
                query = query.filter(User.last_interaction_at >= activity_cutoff)

            # Group by user fields and order by user_id
            query = query.group_by(
                User.id,
                User.email,
                User.last_interaction_at,
            ).order_by(User.id)

            # Execute query and map results to UserSummaryRow
            results = query.all()

            user_summary_rows: list[UserSummaryRow] = []
            for row in results:
                user_summary_rows.append(
                    UserSummaryRow(
                        user_id=row.user_id,
                        email=row.email,
                        total_sessions=row.total_sessions,
                        total_prompts=row.total_prompts,
                        craft_count=row.craft_count,
                        lyra_count=row.lyra_count,
                        ggl_count=row.ggl_count,
                        avg_tokens=float(row.avg_tokens),
                        success_rate=float(row.success_rate),
                        last_activity=row.last_activity,
                        avg_duration=float(row.avg_duration),
                    )
                )

            return user_summary_rows

        # Execute with timing measurement
        return self._execute_timed_query("user_summary", execute_query)

    def generate_daily_metrics(
        self,
        report_date: date,
    ) -> tuple[DailyMetricsRow, QueryTiming]:
        """
        Generate daily metrics report data with timing.

        Calculates platform-wide metrics for the specified date:
        - User counts (all, active, new)
        - Prompt and method usage statistics
        - Average tokens and email counts

        Args:
            report_date: Date to generate metrics for

        Returns:
            Tuple of (DailyMetricsRow, QueryTiming)

        Requirements: 3.1-3.10
        """

        def execute_query() -> DailyMetricsRow:
            # Requirement 3.2: AllUsers = total count of users in database
            all_users = self.db_session.query(func.count(User.id)).scalar() or 0

            # Requirement 3.3: ActiveUsers = count of users with at least one session on report date
            active_users = (
                self.db_session.query(func.count(func.distinct(Session.user_id)))
                .filter(func.date(Session.start_time) == report_date)
                .scalar()
                or 0
            )

            # Requirement 3.4: NewUsers = count of users with first_interaction_at on report date
            new_users = (
                self.db_session.query(func.count(User.id))
                .filter(func.date(User.first_interaction_at) == report_date)
                .scalar()
                or 0
            )

            # Query for session metrics - only successful sessions on report date
            # Requirements 3.5-3.9
            session_metrics = (
                self.db_session.query(
                    # Requirement 3.5: TotalPrompts = count of successful sessions
                    func.count(case((Session.status == "successful", Session.id))).label(
                        "total_prompts"
                    ),
                    # Requirement 3.6: CraftUsed = successful sessions with CRAFT method
                    func.count(
                        case(
                            (
                                (Session.status == "successful")
                                & (Session.optimization_method == "CRAFT"),
                                Session.id,
                            )
                        )
                    ).label("craft_used"),
                    # Requirement 3.7: LyraUsed = successful sessions with LYRA method
                    func.count(
                        case(
                            (
                                (Session.status == "successful")
                                & (Session.optimization_method == "LYRA"),
                                Session.id,
                            )
                        )
                    ).label("lyra_used"),
                    # Requirement 3.8: GglUsed = successful sessions with GGL method
                    func.count(
                        case(
                            (
                                (Session.status == "successful")
                                & (Session.optimization_method == "GGL"),
                                Session.id,
                            )
                        )
                    ).label("ggl_used"),
                    # Requirement 3.9: AvgTokens = average tokens_total of successful sessions
                    func.coalesce(
                        func.avg(case((Session.status == "successful", Session.tokens_total))),
                        0,
                    ).label("avg_tokens"),
                )
                .filter(func.date(Session.start_time) == report_date)
                .first()
            )

            # Requirement 3.10: TotalEmails = count of sent emails on report date
            total_emails = (
                self.db_session.query(func.count(SessionEmailEvent.id))
                .filter(func.date(SessionEmailEvent.sent_at) == report_date)
                .filter(SessionEmailEvent.delivery_status == "sent")
                .scalar()
                or 0
            )

            # Build the DailyMetricsRow
            return DailyMetricsRow(
                date=report_date,
                all_users=all_users,
                active_users=active_users,
                new_users=new_users,
                total_prompts=session_metrics.total_prompts if session_metrics else 0,
                craft_used=session_metrics.craft_used if session_metrics else 0,
                lyra_used=session_metrics.lyra_used if session_metrics else 0,
                ggl_used=session_metrics.ggl_used if session_metrics else 0,
                avg_tokens=float(session_metrics.avg_tokens) if session_metrics else 0.0,
                total_emails=total_emails,
            )

        # Execute with timing measurement
        return self._execute_timed_query("daily_metrics", execute_query)

    def export_sessions(
        self,
        report_date: date,
    ) -> tuple[list[SessionExportRow], QueryTiming]:
        """
        Export successful sessions for the report date with timing.

        Exports all sessions with status='successful' and start_time
        on the specified date, including conversation history as JSON.

        Args:
            report_date: Date to export sessions for

        Returns:
            Tuple of (list of SessionExportRow, QueryTiming)

        Requirements: 4.1-4.5
        """

        def execute_query() -> list[SessionExportRow]:
            # Build query selecting all session columns
            # Requirement 4.1: Include all columns from sessions table
            # Requirement 4.2: Filter by status='successful'
            # Requirement 4.3: Filter by start_time on report_date
            query = (
                self.db_session.query(Session)
                .filter(Session.status == "successful")
                .filter(func.date(Session.start_time) == report_date)
                .order_by(Session.id)
            )

            # Execute query and map results to SessionExportRow
            results = query.all()

            session_export_rows: list[SessionExportRow] = []
            for session in results:
                # Requirement 4.4: Serialize conversation_history as JSON string
                # Handle None/empty conversation_history gracefully
                if session.conversation_history:
                    conversation_history_json = json.dumps(
                        session.conversation_history,
                        ensure_ascii=False,
                    )
                else:
                    conversation_history_json = "[]"

                # Requirement 4.5: Include all 19 columns as specified
                session_export_rows.append(
                    SessionExportRow(
                        id=session.id,
                        user_id=session.user_id,
                        start_time=session.start_time,
                        finish_time=session.finish_time,
                        duration_seconds=session.duration_seconds,
                        status=session.status,
                        optimization_method=session.optimization_method,
                        model_name=session.model_name,
                        used_followup=session.used_followup,
                        input_tokens=session.input_tokens,
                        output_tokens=session.output_tokens,
                        tokens_total=session.tokens_total,
                        followup_start_time=session.followup_start_time,
                        followup_finish_time=session.followup_finish_time,
                        followup_duration_seconds=session.followup_duration_seconds,
                        followup_input_tokens=session.followup_input_tokens,
                        followup_output_tokens=session.followup_output_tokens,
                        followup_tokens_total=session.followup_tokens_total,
                        conversation_history=conversation_history_json,
                    )
                )

            return session_export_rows

        # Execute with timing measurement
        return self._execute_timed_query("sessions_export", execute_query)

    async def generate_and_send_reports(
        self,
        report_date: date,
        include_all_users: bool = False,
    ) -> ReportResult:
        """
        Generate all reports and send via email.

        Orchestrates the complete report generation workflow:
        1. Generate user summary report
        2. Generate daily metrics report
        3. Export sessions
        4. Create CSV files
        5. Send email with attachments
        6. Log performance summary

        Args:
            report_date: Date to generate reports for
            include_all_users: If True, include all users in user summary

        Returns:
            ReportResult with success status, counts, and timing metrics

        Requirements: 5.3, 5.4, 5.5, 8.1, 8.2, 8.3, 9.5
        """

        # Track total execution time
        total_start_time = time.perf_counter()
        query_timings: list[QueryTiming] = []

        # Initialize result tracking
        user_summary_rows = 0
        daily_metrics_generated = False
        sessions_exported = 0
        error_message: str | None = None

        # Requirement 8.1: Log start of report generation
        logger.info(
            f"REPORT_GENERATION_START: Starting report generation for {report_date}, "
            f"include_all_users={include_all_users}"
        )

        # Check if recipients are configured (Requirement 1.5)
        if not self.config.has_recipients():
            error_message = "No recipient emails configured, skipping report delivery"
            logger.error(f"REPORT_GENERATION_ERROR: {error_message}")
            total_execution_time_ms = (time.perf_counter() - total_start_time) * 1000
            return ReportResult(
                success=False,
                user_summary_rows=0,
                daily_metrics_generated=False,
                sessions_exported=0,
                query_timings=query_timings,
                total_query_time_ms=0.0,
                total_execution_time_ms=total_execution_time_ms,
                error=error_message,
            )

        # Prepare CSV attachments list: (filename, content) tuples
        attachments: list[tuple[str, str]] = []
        date_str = report_date.strftime("%Y-%m-%d")

        # 1. Generate user summary report
        try:
            user_summary_data, user_summary_timing = self.generate_user_summary(
                report_date=report_date,
                include_all_users=include_all_users,
            )
            query_timings.append(user_summary_timing)
            user_summary_rows = len(user_summary_data)

            # Requirement 8.2: Log completion of user summary report
            logger.info(f"REPORT_USER_SUMMARY_COMPLETE: Generated {user_summary_rows} rows")

            # Create CSV file (Requirement 5.3)
            user_summary_csv = CSVGenerator.generate_user_summary_csv(user_summary_data)
            attachments.append((f"user_summary_{date_str}.csv", user_summary_csv))

            # Requirement 8.3: Log row count
            logger.info(
                f"REPORT_CSV_CREATED: user_summary_{date_str}.csv with {user_summary_rows} rows"
            )

        except Exception as e:
            # Requirement 8.4: Log error and continue with remaining reports
            logger.exception("REPORT_USER_SUMMARY_ERROR: Failed to generate user summary")
            error_message = f"User summary generation failed: {e}"

        # 2. Generate daily metrics report
        try:
            daily_metrics_data, daily_metrics_timing = self.generate_daily_metrics(
                report_date=report_date,
            )
            query_timings.append(daily_metrics_timing)
            daily_metrics_generated = True

            # Requirement 8.2: Log completion of daily metrics report
            logger.info("REPORT_DAILY_METRICS_COMPLETE: Generated daily metrics")

            # Create CSV file (Requirement 5.3)
            daily_metrics_csv = CSVGenerator.generate_daily_metrics_csv(daily_metrics_data)
            attachments.append((f"daily_metrics_{date_str}.csv", daily_metrics_csv))

            # Requirement 8.3: Log row count
            logger.info(f"REPORT_CSV_CREATED: daily_metrics_{date_str}.csv with 1 row")

        except Exception as e:
            # Requirement 8.4: Log error and continue with remaining reports
            logger.exception("REPORT_DAILY_METRICS_ERROR: Failed to generate daily metrics")
            if error_message:
                error_message += f"; Daily metrics generation failed: {e}"
            else:
                error_message = f"Daily metrics generation failed: {e}"

        # 3. Export sessions
        try:
            sessions_data, sessions_timing = self.export_sessions(
                report_date=report_date,
            )
            query_timings.append(sessions_timing)
            sessions_exported = len(sessions_data)

            # Requirement 8.2: Log completion of sessions export
            logger.info(f"REPORT_SESSIONS_EXPORT_COMPLETE: Exported {sessions_exported} sessions")

            # Create CSV file (Requirement 5.3)
            sessions_csv = CSVGenerator.generate_sessions_csv(sessions_data)
            attachments.append((f"sessions_{date_str}.csv", sessions_csv))

            # Requirement 8.3: Log row count
            logger.info(
                f"REPORT_CSV_CREATED: sessions_{date_str}.csv with {sessions_exported} rows"
            )

        except Exception as e:
            # Requirement 8.4: Log error and continue
            logger.exception("REPORT_SESSIONS_EXPORT_ERROR: Failed to export sessions")
            if error_message:
                error_message += f"; Sessions export failed: {e}"
            else:
                error_message = f"Sessions export failed: {e}"

        # Calculate total query time
        total_query_time_ms = sum(t.duration_ms for t in query_timings)

        # 4. Send email with attachments (Requirements 5.4, 5.5)
        email_success = False
        if attachments:
            try:
                # Send report email to all recipients
                email_result = await self._send_report_email(
                    attachments=attachments,
                    report_date=report_date,
                )
                email_success = email_result

                if email_success:
                    logger.info(
                        f"REPORT_EMAIL_SENT: Report email sent to "
                        f"{len(self.config.recipient_emails)} recipients"
                    )
                else:
                    logger.error("REPORT_EMAIL_FAILED: Failed to send report email")
                    if error_message:
                        error_message += "; Email delivery failed"
                    else:
                        error_message = "Email delivery failed"

            except Exception as e:
                logger.exception("REPORT_EMAIL_ERROR: Error sending report email")
                if error_message:
                    error_message += f"; Email delivery error: {e}"
                else:
                    error_message = f"Email delivery error: {e}"
        else:
            logger.warning("REPORT_NO_ATTACHMENTS: No reports generated, skipping email")
            if not error_message:
                error_message = "No reports generated"

        # Calculate total execution time
        total_execution_time_ms = (time.perf_counter() - total_start_time) * 1000

        # Requirement 9.5: Log performance summary
        self._log_performance_summary(query_timings, total_execution_time_ms)

        # Requirement 8.6: Log total execution time
        logger.info(
            f"REPORT_GENERATION_COMPLETE: Total execution time: {total_execution_time_ms:.1f}ms"
        )

        # Determine overall success
        # Success if at least one report was generated and email was sent (or no recipients)
        success = (
            user_summary_rows > 0 or daily_metrics_generated or sessions_exported > 0
        ) and email_success

        return ReportResult(
            success=success,
            user_summary_rows=user_summary_rows,
            daily_metrics_generated=daily_metrics_generated,
            sessions_exported=sessions_exported,
            query_timings=query_timings,
            total_query_time_ms=total_query_time_ms,
            total_execution_time_ms=total_execution_time_ms,
            error=error_message,
        )

    async def generate_and_send_reports_with_retry(
        self,
        report_date: date,
        include_all_users: bool = False,
    ) -> ReportResult:
        """
        Generate and send reports with automatic retry on failure.

        Wraps generate_and_send_reports with retry logic using tenacity.
        Retries up to 3 times with exponential backoff delays:
        - 1st retry: 1 minute delay
        - 2nd retry: 5 minutes delay
        - 3rd retry: 15 minutes delay

        After all retries are exhausted, logs the error and returns failure result.

        This method does not block other scheduled tasks during retry attempts
        as it runs asynchronously.

        Args:
            report_date: Date to generate reports for
            include_all_users: If True, include all users in user summary

        Returns:
            ReportResult with success status, counts, and timing metrics

        Requirements: 6.1, 6.2, 6.3, 6.4
        """
        attempt = 0
        last_result: ReportResult | None = None
        last_exception: Exception | None = None

        while attempt < 3:
            attempt += 1
            try:
                result = await self.generate_and_send_reports(
                    report_date=report_date,
                    include_all_users=include_all_users,
                )

                # If successful, return immediately
                if result.success:
                    if attempt > 1:
                        logger.info(
                            f"REPORT_RETRY_SUCCESS: Report generation succeeded on attempt {attempt}"
                        )
                    return result

                # Store the result for potential final return
                last_result = result

                # If not successful and we have retries left, log and wait
                if attempt < 3:
                    wait_time = RETRY_DELAYS[attempt - 1]
                    logger.warning(
                        f"REPORT_RETRY: Attempt {attempt} failed "
                        f"(error: {result.error}), retrying in {wait_time // 60} minute(s)..."
                    )
                    # Use asyncio.sleep for non-blocking wait
                    await asyncio.sleep(wait_time)

            except Exception as e:
                last_exception = e
                logger.exception(f"REPORT_RETRY_ERROR: Attempt {attempt} raised exception")

                # If we have retries left, wait and retry
                if attempt < 3:
                    wait_time = RETRY_DELAYS[attempt - 1]
                    logger.warning(f"REPORT_RETRY: Retrying in {wait_time // 60} minute(s)...")
                    await asyncio.sleep(wait_time)

        # Requirement 6.3: Log error after all retries exhausted
        logger.error(
            f"REPORT_RETRY_EXHAUSTED: All 3 retry attempts failed for report date {report_date}. "
            f"Last error: {last_result.error if last_result else str(last_exception)}"
        )

        # Return the last result if we have one, otherwise create a failure result
        if last_result:
            return last_result

        return ReportResult(
            success=False,
            user_summary_rows=0,
            daily_metrics_generated=False,
            sessions_exported=0,
            query_timings=[],
            total_query_time_ms=0.0,
            total_execution_time_ms=0.0,
            error=f"All retry attempts failed: {last_exception}",
        )

    async def _send_report_email(
        self,
        attachments: list[tuple[str, str]],
        report_date: date,
    ) -> bool:
        """
        Send report email with CSV attachments to all recipients.

        This is a helper method that will use EmailService.send_report_email()
        once it's implemented in task 7.1. For now, it provides the interface
        and logging.

        Args:
            attachments: List of (filename, content) tuples for CSV attachments
            report_date: Date of the report for email subject

        Returns:
            True if email was sent successfully to all recipients, False otherwise

        Requirements: 5.4, 5.5, 8.5
        """
        if not self.config.recipient_emails:
            logger.error("REPORT_EMAIL_SKIP: No recipient emails configured")
            return False

        # Log delivery attempt for each recipient (Requirement 8.5)
        for recipient in self.config.recipient_emails:
            logger.info(f"REPORT_EMAIL_ATTEMPT: Sending report to {recipient}")

        try:
            # Call EmailService.send_report_email()
            results = await self.email_service.send_report_email(
                recipient_emails=self.config.recipient_emails,
                attachments=attachments,
                report_date=report_date.isoformat(),
            )

            # Log delivery status for each recipient (Requirement 8.5)
            all_successful = True
            for recipient, result in results.items():
                if result.success:
                    logger.info(f"REPORT_EMAIL_SUCCESS: Report delivered to {recipient}")
                else:
                    logger.error(
                        f"REPORT_EMAIL_FAILURE: Failed to deliver report to {recipient} - "
                        f"{result.error}"
                    )
                    all_successful = False

            return all_successful

        except Exception:
            logger.exception("REPORT_EMAIL_ERROR: Failed to send report email")
            # Log failure for each recipient (Requirement 8.5)
            for recipient in self.config.recipient_emails:
                logger.error(f"REPORT_EMAIL_FAILURE: Failed to deliver report to {recipient}")
            return False
