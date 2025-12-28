"""
Background task scheduler for periodic maintenance operations.

This module provides a background task system for running periodic maintenance
operations like audit event purging, health checks, metrics cleanup, and
daily marketing report generation.
"""

import asyncio
import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta

from telegram_bot.utils.audit_service import get_audit_service
from telegram_bot.utils.config import BotConfig


logger = logging.getLogger(__name__)


# Session timeout task interval in hours (1 hour)
SESSION_TIMEOUT_CHECK_INTERVAL_HOURS = 1


class BackgroundTaskScheduler:
    """Background task scheduler for periodic maintenance operations."""

    def __init__(self):
        """Initialize background task scheduler."""
        self.logger = logging.getLogger(f"{__name__}.BackgroundTaskScheduler")
        self._running = False
        self._thread: threading.Thread | None = None
        self._tasks: dict[str, dict] = {}
        self._stop_event = threading.Event()

    def add_task(
        self,
        name: str,
        func: Callable,
        interval_hours: int = 24,
        run_immediately: bool = False,
    ):
        """
        Add a periodic task to the scheduler.

        Args:
            name: Unique name for the task
            func: Function to execute
            interval_hours: Interval between executions in hours
            run_immediately: Whether to run the task immediately on start
        """
        self._tasks[name] = {
            "func": func,
            "interval": timedelta(hours=interval_hours),
            "last_run": None if run_immediately else datetime.now(UTC),
            "run_immediately": run_immediately,
        }

        self.logger.info(f"Added background task '{name}' with {interval_hours}h interval")

    def start(self):
        """Start the background task scheduler."""
        if self._running:
            self.logger.warning("Background task scheduler is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self._thread.start()

        self.logger.info("Background task scheduler started")

    def stop(self):
        """Stop the background task scheduler."""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

        self.logger.info("Background task scheduler stopped")

    def _run_scheduler(self):
        """Main scheduler loop."""
        self.logger.info("Background task scheduler loop started")

        while self._running and not self._stop_event.is_set():
            try:
                current_time = datetime.now(UTC)

                for task_name, task_info in self._tasks.items():
                    try:
                        should_run = False

                        # Check if task should run immediately on first iteration
                        if task_info["run_immediately"] and task_info["last_run"] is None:
                            should_run = True
                            task_info["run_immediately"] = False

                        # Check if enough time has passed since last run
                        elif task_info["last_run"] is not None:
                            time_since_last = current_time - task_info["last_run"]
                            if time_since_last >= task_info["interval"]:
                                should_run = True

                        if should_run:
                            self.logger.info(f"Running background task: {task_name}")
                            start_time = time.time()

                            try:
                                # Execute the task
                                result = task_info["func"]()
                                execution_time = time.time() - start_time

                                self.logger.info(
                                    f"Background task '{task_name}' completed successfully "
                                    f"in {execution_time:.2f}s"
                                )

                                # Log task-specific results if available
                                if isinstance(result, dict) and "message" in result:
                                    self.logger.info(
                                        f"Task '{task_name}' result: {result['message']}"
                                    )

                            except Exception as e:
                                execution_time = time.time() - start_time
                                self.logger.error(
                                    f"Background task '{task_name}' failed after "
                                    f"{execution_time:.2f}s: {e}"
                                )

                            # Update last run time regardless of success/failure
                            task_info["last_run"] = current_time

                    except Exception as e:
                        self.logger.error(f"Error processing background task '{task_name}': {e}")

                # Sleep for 1 hour before next check, but wake up if stop is requested
                self._stop_event.wait(timeout=3600)  # 1 hour

            except Exception as e:
                self.logger.error(f"Error in background task scheduler loop: {e}")
                # Sleep briefly before retrying to avoid tight error loops
                self._stop_event.wait(timeout=60)  # 1 minute

        self.logger.info("Background task scheduler loop ended")

    def get_task_status(self) -> dict[str, dict]:
        """
        Get status of all scheduled tasks.

        Returns:
            Dictionary with task status information
        """
        status = {}
        current_time = datetime.now(UTC)

        for task_name, task_info in self._tasks.items():
            last_run = task_info["last_run"]
            next_run = None

            if last_run:
                next_run = last_run + task_info["interval"]

            status[task_name] = {
                "interval_hours": task_info["interval"].total_seconds() / 3600,
                "last_run": last_run.isoformat() if last_run else None,
                "next_run": next_run.isoformat() if next_run else "immediate",
                "overdue": (next_run < current_time if next_run else False),
            }

        return status


def audit_purge_task() -> dict[str, any]:
    """
    Background task for purging old audit events.

    Returns:
        Dictionary with task execution results
    """
    try:
        config = BotConfig.from_env()
        retention_days = getattr(config, "audit_retention_days", 90)

        audit_service = get_audit_service()
        purged_count = audit_service.purge_old_events(retention_days=retention_days)

        return {
            "success": True,
            "message": f"Purged {purged_count} audit events older than {retention_days} days",
            "purged_count": purged_count,
            "retention_days": retention_days,
        }

    except Exception as e:
        logger.error(f"Audit purge task failed: {e}")
        return {
            "success": False,
            "message": f"Audit purge task failed: {e}",
            "purged_count": 0,
        }


def session_timeout_task() -> dict[str, any]:
    """
    Background task for timing out stale sessions.

    Periodically checks for sessions that have been inactive for longer than
    the configured timeout period and marks them as unsuccessful.

    Returns:
        Dictionary with task execution results including:
        - success: Whether the task completed without errors
        - message: Human-readable result description
        - timed_out_count: Number of sessions that were timed out
        - timeout_seconds: The configured timeout threshold

    Note:
        This task follows graceful degradation principles. If the session
        service is not available or encounters errors, the task logs the
        failure and returns a failure result without affecting other
        background tasks or the main bot functionality.
    """
    try:
        config = BotConfig.from_env()
        timeout_seconds = config.session_timeout_seconds

        # Get session service from dependency container
        from telegram_bot.dependencies import get_container

        container = get_container()
        session_service = container.get_session_service()

        # Call timeout_stale_sessions with configured timeout
        timed_out_count = session_service.timeout_stale_sessions(timeout_seconds)

        return {
            "success": True,
            "message": f"Timed out {timed_out_count} stale sessions "
            f"(threshold: {timeout_seconds}s / {timeout_seconds // 3600}h)",
            "timed_out_count": timed_out_count,
            "timeout_seconds": timeout_seconds,
        }

    except Exception as e:
        logger.error(f"Session timeout task failed: {e}")
        return {
            "success": False,
            "message": f"Session timeout task failed: {e}",
            "timed_out_count": 0,
        }


def daily_reports_task() -> dict[str, any]:
    """
    Background task for generating and sending daily marketing reports.

    Generates three CSV reports (user summary, daily metrics, sessions export)
    for the previous day and sends them via email to configured recipients.

    Returns:
        Dictionary with task execution results including:
        - success: Whether the task completed without errors
        - message: Human-readable result description
        - report_date: The date for which reports were generated
        - user_summary_rows: Number of rows in user summary report
        - daily_metrics_generated: Whether daily metrics were generated
        - sessions_exported: Number of sessions exported
        - total_execution_time_ms: Total execution time in milliseconds

    Note:
        This task follows graceful degradation principles. If report generation
        or email delivery fails, the task logs the failure and returns a failure
        result without affecting other background tasks.

    Requirements: 5.1, 5.2
    """
    try:
        # Load ReportConfig from environment
        from telegram_bot.services.report_config import ReportConfig

        config = ReportConfig.from_env()

        # Calculate report_date as yesterday (Requirement 5.2)
        report_date = date.today() - timedelta(days=1)

        logger.info(f"DAILY_REPORTS_TASK_START: Starting daily reports task for {report_date}")

        # Get database session
        from telegram_bot.data.database import get_db_session

        db_session = get_db_session()

        # Get email service
        from telegram_bot.services.email_service import get_email_service

        email_service = get_email_service()

        # Initialize ReportService with dependencies
        from telegram_bot.services.report_service import ReportService

        report_service = ReportService(
            db_session=db_session,
            email_service=email_service,
            config=config,
        )

        # Call generate_and_send_reports() using asyncio.run() since this is a sync task
        # The BackgroundTaskScheduler runs tasks synchronously in a thread
        result = asyncio.run(
            report_service.generate_and_send_reports_with_retry(
                report_date=report_date,
                include_all_users=False,
            )
        )

        if result.success:
            logger.info(f"DAILY_REPORTS_TASK_SUCCESS: Reports generated and sent for {report_date}")
            return {
                "success": True,
                "message": f"Daily reports generated and sent for {report_date}. "
                f"User summary: {result.user_summary_rows} rows, "
                f"Sessions exported: {result.sessions_exported}",
                "report_date": report_date.isoformat(),
                "user_summary_rows": result.user_summary_rows,
                "daily_metrics_generated": result.daily_metrics_generated,
                "sessions_exported": result.sessions_exported,
                "total_execution_time_ms": result.total_execution_time_ms,
            }
        logger.error(
            f"DAILY_REPORTS_TASK_FAILED: Report generation failed for {report_date}: {result.error}"
        )
        return {
            "success": False,
            "message": f"Daily reports task failed for {report_date}: {result.error}",
            "report_date": report_date.isoformat(),
            "user_summary_rows": result.user_summary_rows,
            "daily_metrics_generated": result.daily_metrics_generated,
            "sessions_exported": result.sessions_exported,
            "total_execution_time_ms": result.total_execution_time_ms,
            "error": result.error,
        }

    except Exception as e:
        logger.error(f"DAILY_REPORTS_TASK_ERROR: Daily reports task failed: {e}")
        return {
            "success": False,
            "message": f"Daily reports task failed: {e}",
            "report_date": None,
            "user_summary_rows": 0,
            "daily_metrics_generated": False,
            "sessions_exported": 0,
        }


# Global background task scheduler instance
background_scheduler: BackgroundTaskScheduler | None = None


def _parse_generation_time_hour(generation_time: str) -> int:
    """
    Parse the hour from a generation time string in HH:MM format.

    Args:
        generation_time: Time string in HH:MM format (e.g., "01:00", "14:30")

    Returns:
        Hour as integer (0-23), defaults to 1 if parsing fails
    """
    try:
        if ":" in generation_time:
            hour_str = generation_time.split(":")[0]
            hour = int(hour_str)
            if 0 <= hour <= 23:
                return hour
    except (ValueError, IndexError):
        pass

    logger.warning(
        f"BACKGROUND_TASKS: Failed to parse hour from '{generation_time}', using default hour 1"
    )
    return 1


def init_background_tasks() -> BackgroundTaskScheduler:
    """
    Initialize and configure background task scheduler.

    Returns:
        BackgroundTaskScheduler instance
    """
    global background_scheduler
    background_scheduler = BackgroundTaskScheduler()

    # Add audit purge task (runs daily)
    background_scheduler.add_task(
        name="audit_purge",
        func=audit_purge_task,
        interval_hours=24,
        run_immediately=False,  # Don't run immediately on startup
    )

    # Add session timeout task (runs hourly)
    # This task checks for stale sessions and marks them as unsuccessful
    # The timeout threshold is configured via SESSION_TIMEOUT_SECONDS env var
    background_scheduler.add_task(
        name="session_timeout",
        func=session_timeout_task,
        interval_hours=SESSION_TIMEOUT_CHECK_INTERVAL_HOURS,
        run_immediately=False,  # Don't run immediately on startup
    )

    # Add daily reports task (runs daily at configured time)
    # Parse REPORT_GENERATION_TIME to get the hour for logging purposes
    # The task runs on a 24-hour interval; actual execution time depends on when
    # the scheduler starts, but the task generates reports for the previous day
    # regardless of when it runs (Requirement 5.1, 5.2)
    from telegram_bot.services.report_config import ReportConfig

    report_config = ReportConfig.from_env()
    generation_hour = _parse_generation_time_hour(report_config.generation_time)

    background_scheduler.add_task(
        name="daily_reports",
        func=daily_reports_task,
        interval_hours=24,
        run_immediately=False,  # Don't run immediately on startup
    )

    logger.info(
        f"Background task scheduler initialized with audit purge, session timeout, "
        f"and daily reports tasks (reports configured for {report_config.generation_time} / "
        f"hour {generation_hour})"
    )
    return background_scheduler


def get_background_scheduler() -> BackgroundTaskScheduler:
    """
    Get the global background task scheduler instance.

    Returns:
        BackgroundTaskScheduler instance

    Raises:
        RuntimeError: If scheduler is not initialized
    """
    if background_scheduler is None:
        raise RuntimeError(
            "Background task scheduler not initialized. Call init_background_tasks() first."
        )
    return background_scheduler


def start_background_tasks():
    """Start the background task scheduler."""
    scheduler = get_background_scheduler()
    scheduler.start()


def stop_background_tasks():
    """Stop the background task scheduler."""
    if background_scheduler:
        background_scheduler.stop()
