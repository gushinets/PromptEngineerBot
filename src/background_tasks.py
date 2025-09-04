"""
Background task scheduler for periodic maintenance operations.

This module provides a background task system for running periodic maintenance
operations like audit event purging, health checks, and metrics cleanup.
"""

import asyncio
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, Optional

from src.audit_service import get_audit_service
from src.config import BotConfig

logger = logging.getLogger(__name__)


class BackgroundTaskScheduler:
    """Background task scheduler for periodic maintenance operations."""

    def __init__(self):
        """Initialize background task scheduler."""
        self.logger = logging.getLogger(f"{__name__}.BackgroundTaskScheduler")
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._tasks: Dict[str, Dict] = {}
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
            "last_run": None if run_immediately else datetime.now(timezone.utc),
            "run_immediately": run_immediately,
        }

        self.logger.info(
            f"Added background task '{name}' with {interval_hours}h interval"
        )

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
                current_time = datetime.now(timezone.utc)

                for task_name, task_info in self._tasks.items():
                    try:
                        should_run = False

                        # Check if task should run immediately on first iteration
                        if (
                            task_info["run_immediately"]
                            and task_info["last_run"] is None
                        ):
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
                        self.logger.error(
                            f"Error processing background task '{task_name}': {e}"
                        )

                # Sleep for 1 hour before next check, but wake up if stop is requested
                self._stop_event.wait(timeout=3600)  # 1 hour

            except Exception as e:
                self.logger.error(f"Error in background task scheduler loop: {e}")
                # Sleep briefly before retrying to avoid tight error loops
                self._stop_event.wait(timeout=60)  # 1 minute

        self.logger.info("Background task scheduler loop ended")

    def get_task_status(self) -> Dict[str, Dict]:
        """
        Get status of all scheduled tasks.

        Returns:
            Dictionary with task status information
        """
        status = {}
        current_time = datetime.now(timezone.utc)

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


def audit_purge_task() -> Dict[str, any]:
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


# Global background task scheduler instance
background_scheduler: Optional[BackgroundTaskScheduler] = None


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

    logger.info("Background task scheduler initialized with audit purge task")
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
