"""
Background task scheduler for periodic maintenance operations.

This module provides a background task system for running periodic maintenance
operations like audit event purging, health checks, and metrics cleanup.
"""

import logging
import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

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


# Global background task scheduler instance
background_scheduler: BackgroundTaskScheduler | None = None


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

    logger.info("Background task scheduler initialized with audit purge and session timeout tasks")
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
