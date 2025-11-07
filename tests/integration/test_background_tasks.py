"""
Tests for background task scheduler and audit event purging.
"""

from datetime import timedelta
from unittest.mock import MagicMock, patch

import pytest

from telegram_bot.flows.background_tasks import (
    BackgroundTaskScheduler,
    audit_purge_task,
    get_background_scheduler,
    init_background_tasks,
)


@pytest.fixture
def scheduler():
    """Create background task scheduler instance for testing."""
    return BackgroundTaskScheduler()


class TestBackgroundTaskScheduler:
    """Test background task scheduler functionality."""

    def test_add_task(self, scheduler):
        """Test adding tasks to scheduler."""
        mock_func = MagicMock()

        scheduler.add_task(
            name="test_task",
            func=mock_func,
            interval_hours=24,
            run_immediately=False,
        )

        assert "test_task" in scheduler._tasks
        task_info = scheduler._tasks["test_task"]
        assert task_info["func"] == mock_func
        assert task_info["interval"] == timedelta(hours=24)
        assert task_info["run_immediately"] is False

    def test_get_task_status(self, scheduler):
        """Test getting task status information."""
        mock_func = MagicMock()
        scheduler.add_task("test_task", mock_func, interval_hours=12)

        status = scheduler.get_task_status()

        assert "test_task" in status
        task_status = status["test_task"]
        assert task_status["interval_hours"] == 12
        assert "last_run" in task_status
        assert "next_run" in task_status
        assert "overdue" in task_status


class TestAuditPurgeTask:
    """Test audit purge task functionality."""

    @patch("telegram_bot.background_tasks.get_audit_service")
    @patch("telegram_bot.background_tasks.BotConfig.from_env")
    def test_audit_purge_task_success(self, mock_from_env, mock_get_audit_service):
        """Test successful audit purge task execution."""
        # Mock config
        mock_config = MagicMock()
        mock_config.audit_retention_days = 90
        mock_from_env.return_value = mock_config

        # Mock audit service
        mock_audit_service = MagicMock()
        mock_audit_service.purge_old_events.return_value = 42
        mock_get_audit_service.return_value = mock_audit_service

        result = audit_purge_task()

        assert result["success"] is True
        assert result["purged_count"] == 42
        assert result["retention_days"] == 90
        assert "Purged 42 audit events" in result["message"]

        mock_audit_service.purge_old_events.assert_called_once_with(retention_days=90)


class TestBackgroundTasksGlobal:
    """Test global background task management."""

    def test_init_background_tasks(self):
        """Test background task initialization."""
        scheduler = init_background_tasks()

        assert isinstance(scheduler, BackgroundTaskScheduler)
        assert get_background_scheduler() is scheduler

        # Verify audit purge task was added
        assert "audit_purge" in scheduler._tasks
        task_info = scheduler._tasks["audit_purge"]
        assert task_info["interval"] == timedelta(hours=24)
        assert task_info["run_immediately"] is False
