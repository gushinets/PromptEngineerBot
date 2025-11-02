"""
Tests for health monitoring system.

This module tests health checks for database, Redis, and SMTP services,
periodic monitoring, failure detection, and status reporting.
"""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_prompt_bot.config.settings import BotConfig
from telegram_prompt_bot.infrastructure.health_checks import (
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
    ServiceHealth,
    get_health_monitor,
    init_health_monitor,
)


@pytest.fixture
def mock_config():
    """Create mock BotConfig for testing."""
    config = MagicMock(spec=BotConfig)
    config.smtp_host = "smtp.example.com"
    config.smtp_port = 587
    config.smtp_use_tls = True
    config.smtp_use_ssl = False
    return config


@pytest.fixture
def health_monitor(mock_config):
    """Create HealthMonitor instance for testing."""
    return HealthMonitor(mock_config)


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_health_check_result_creation(self):
        """Test HealthCheckResult creation with default timestamp."""
        result = HealthCheckResult(
            service="database", status=HealthStatus.HEALTHY, response_time_ms=50
        )

        assert result.service == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 50
        assert result.error is None
        assert isinstance(result.timestamp, datetime)

    def test_health_check_result_with_error(self):
        """Test HealthCheckResult creation with error."""
        result = HealthCheckResult(
            service="redis", status=HealthStatus.UNHEALTHY, error="Connection refused"
        )

        assert result.service == "redis"
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Connection refused"


class TestServiceHealth:
    """Test ServiceHealth dataclass."""

    def test_service_health_creation(self):
        """Test ServiceHealth creation."""
        service_health = ServiceHealth(
            service="smtp", current_status=HealthStatus.HEALTHY
        )

        assert service_health.service == "smtp"
        assert service_health.current_status == HealthStatus.HEALTHY
        assert service_health.consecutive_failures == 0
        assert service_health.total_checks == 0


class TestHealthMonitor:
    """Test HealthMonitor class."""

    def test_init_service_health(self, health_monitor):
        """Test service health initialization."""
        services = health_monitor._services

        assert "database" in services
        assert "redis" in services
        assert "smtp" in services

        for service in services.values():
            assert service.current_status == HealthStatus.UNKNOWN
            assert service.consecutive_failures == 0

    @patch("telegram_prompt_bot.infrastructure.health_checks.get_db_manager")
    async def test_check_database_health_success(
        self, mock_get_db_manager, health_monitor
    ):
        """Test successful database health check."""
        # Mock database manager
        mock_db_manager = MagicMock()
        mock_db_manager.health_check.return_value = True
        mock_get_db_manager.return_value = mock_db_manager

        result = await health_monitor.check_database_health()

        assert result.service == "database"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms is not None
        assert result.response_time_ms > 0
        assert result.error is None
        assert result.details == {"connection_pool": "active"}

    @patch("telegram_prompt_bot.infrastructure.health_checks.get_db_manager")
    async def test_check_database_health_failure(
        self, mock_get_db_manager, health_monitor
    ):
        """Test database health check failure."""
        # Mock database manager failure
        mock_db_manager = MagicMock()
        mock_db_manager.health_check.return_value = False
        mock_get_db_manager.return_value = mock_db_manager

        result = await health_monitor.check_database_health()

        assert result.service == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Database connectivity test failed"

    @patch("telegram_prompt_bot.infrastructure.health_checks.get_db_manager")
    async def test_check_database_health_exception(
        self, mock_get_db_manager, health_monitor
    ):
        """Test database health check with exception."""
        # Mock database manager exception
        mock_get_db_manager.side_effect = Exception("Connection error")

        result = await health_monitor.check_database_health()

        assert result.service == "database"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Connection error" in result.error

    @patch("telegram_prompt_bot.infrastructure.health_checks.get_redis_client")
    async def test_check_redis_health_success(
        self, mock_get_redis_client, health_monitor
    ):
        """Test successful Redis health check."""
        # Mock Redis client
        mock_redis_client = MagicMock()
        mock_redis_client.health_check.return_value = True
        mock_get_redis_client.return_value = mock_redis_client

        result = await health_monitor.check_redis_health()

        assert result.service == "redis"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms is not None
        assert result.response_time_ms > 0
        assert result.error is None
        assert result.details == {"connection_pool": "active"}

    @patch("telegram_prompt_bot.infrastructure.health_checks.get_redis_client")
    async def test_check_redis_health_failure(
        self, mock_get_redis_client, health_monitor
    ):
        """Test Redis health check failure."""
        # Mock Redis client failure
        mock_redis_client = MagicMock()
        mock_redis_client.health_check.return_value = False
        mock_get_redis_client.return_value = mock_redis_client

        result = await health_monitor.check_redis_health()

        assert result.service == "redis"
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "Redis connectivity test failed"

    @patch("telegram_prompt_bot.infrastructure.health_checks.get_redis_client")
    async def test_check_redis_health_exception(
        self, mock_get_redis_client, health_monitor
    ):
        """Test Redis health check with exception."""
        # Mock Redis client exception
        mock_get_redis_client.side_effect = Exception("Redis connection error")

        result = await health_monitor.check_redis_health()

        assert result.service == "redis"
        assert result.status == HealthStatus.UNHEALTHY
        assert "Redis connection error" in result.error

    @patch("telegram_prompt_bot.email.service.EmailService")
    async def test_check_smtp_health_success(
        self, mock_email_service_class, health_monitor
    ):
        """Test successful SMTP health check."""
        # Mock EmailService
        mock_email_service = AsyncMock()
        mock_email_service._check_smtp_health.return_value = True
        mock_email_service_class.return_value = mock_email_service

        result = await health_monitor.check_smtp_health()

        assert result.service == "smtp"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms is not None
        assert result.response_time_ms > 0
        assert result.error is None
        assert "host" in result.details
        assert "port" in result.details

    @patch("telegram_prompt_bot.email.service.EmailService")
    async def test_check_smtp_health_failure(
        self, mock_email_service_class, health_monitor
    ):
        """Test SMTP health check failure."""
        # Mock EmailService failure
        mock_email_service = AsyncMock()
        mock_email_service._check_smtp_health.return_value = False
        mock_email_service_class.return_value = mock_email_service

        result = await health_monitor.check_smtp_health()

        assert result.service == "smtp"
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error == "SMTP connectivity test failed"

    @patch("telegram_prompt_bot.email.service.EmailService")
    async def test_check_smtp_health_exception(
        self, mock_email_service_class, health_monitor
    ):
        """Test SMTP health check with exception."""
        # Mock EmailService exception
        mock_email_service_class.side_effect = Exception("SMTP error")

        result = await health_monitor.check_smtp_health()

        assert result.service == "smtp"
        assert result.status == HealthStatus.UNHEALTHY
        assert "SMTP error" in result.error

    @patch.object(HealthMonitor, "check_database_health")
    @patch.object(HealthMonitor, "check_redis_health")
    @patch.object(HealthMonitor, "check_smtp_health")
    async def test_check_all_services(
        self, mock_smtp, mock_redis, mock_db, health_monitor
    ):
        """Test checking all services concurrently."""
        # Mock all health checks
        mock_db.return_value = HealthCheckResult("database", HealthStatus.HEALTHY)
        mock_redis.return_value = HealthCheckResult("redis", HealthStatus.HEALTHY)
        mock_smtp.return_value = HealthCheckResult(
            "smtp", HealthStatus.UNHEALTHY, error="SMTP down"
        )

        results = await health_monitor.check_all_services()

        assert len(results) == 3
        assert "database" in results
        assert "redis" in results
        assert "smtp" in results

        assert results["database"].status == HealthStatus.HEALTHY
        assert results["redis"].status == HealthStatus.HEALTHY
        assert results["smtp"].status == HealthStatus.UNHEALTHY

    def test_update_service_health_healthy(self, health_monitor):
        """Test updating service health with healthy result."""
        result = HealthCheckResult(
            service="database", status=HealthStatus.HEALTHY, response_time_ms=50
        )

        health_monitor._update_service_health(result)

        service = health_monitor._services["database"]
        assert service.current_status == HealthStatus.HEALTHY
        assert service.consecutive_failures == 0
        assert service.total_checks == 1
        assert service.total_failures == 0
        assert service.last_healthy is not None
        assert service.average_response_time_ms == 50.0

    def test_update_service_health_unhealthy(self, health_monitor):
        """Test updating service health with unhealthy result."""
        result = HealthCheckResult(
            service="redis", status=HealthStatus.UNHEALTHY, error="Connection failed"
        )

        health_monitor._update_service_health(result)

        service = health_monitor._services["redis"]
        assert service.current_status == HealthStatus.UNHEALTHY
        assert service.consecutive_failures == 1
        assert service.total_checks == 1
        assert service.total_failures == 1
        assert service.last_unhealthy is not None

    def test_update_service_health_consecutive_failures(self, health_monitor):
        """Test consecutive failure tracking and alerting."""
        # Set failure threshold to 2 for testing
        health_monitor._failure_threshold = 2

        # First failure
        result1 = HealthCheckResult("smtp", HealthStatus.UNHEALTHY, error="Error 1")
        health_monitor._update_service_health(result1)

        service = health_monitor._services["smtp"]
        assert service.consecutive_failures == 1

        # Second failure (should trigger alert)
        result2 = HealthCheckResult("smtp", HealthStatus.UNHEALTHY, error="Error 2")
        health_monitor._update_service_health(result2)

        assert service.consecutive_failures == 2
        assert service.total_failures == 2

    def test_update_service_health_recovery(self, health_monitor):
        """Test service recovery after failures."""
        # First make service unhealthy
        unhealthy_result = HealthCheckResult(
            "database", HealthStatus.UNHEALTHY, error="Error"
        )
        health_monitor._update_service_health(unhealthy_result)

        service = health_monitor._services["database"]
        assert service.consecutive_failures == 1

        # Then recover
        healthy_result = HealthCheckResult(
            "database", HealthStatus.HEALTHY, response_time_ms=30
        )
        health_monitor._update_service_health(healthy_result)

        assert service.current_status == HealthStatus.HEALTHY
        assert service.consecutive_failures == 0  # Reset on recovery
        assert service.total_failures == 1  # But total failures remain

    def test_update_service_health_average_response_time(self, health_monitor):
        """Test average response time calculation."""
        # First healthy check
        result1 = HealthCheckResult(
            "database", HealthStatus.HEALTHY, response_time_ms=100
        )
        health_monitor._update_service_health(result1)

        service = health_monitor._services["database"]
        assert service.average_response_time_ms == 100.0

        # Second healthy check (should update average)
        result2 = HealthCheckResult(
            "database", HealthStatus.HEALTHY, response_time_ms=50
        )
        health_monitor._update_service_health(result2)

        # Average should be weighted: 100 * 0.8 + 50 * 0.2 = 90
        assert service.average_response_time_ms == 90.0

    async def test_start_stop_monitoring(self, health_monitor):
        """Test starting and stopping health monitoring."""
        # Start monitoring
        await health_monitor.start_monitoring(check_interval=1)

        assert health_monitor._monitoring_running is True
        assert health_monitor._monitoring_task is not None
        assert health_monitor._check_interval == 1

        # Stop monitoring
        await health_monitor.stop_monitoring()

        assert health_monitor._monitoring_running is False
        assert health_monitor._monitoring_task is None

    async def test_start_monitoring_already_running(self, health_monitor):
        """Test starting monitoring when already running."""
        # Start monitoring
        await health_monitor.start_monitoring()
        first_task = health_monitor._monitoring_task

        # Try to start again
        await health_monitor.start_monitoring()

        # Should still be the same task
        assert health_monitor._monitoring_task == first_task

        # Clean up
        await health_monitor.stop_monitoring()

    def test_get_service_health(self, health_monitor):
        """Test getting health information for specific service."""
        # Update service health first
        result = HealthCheckResult("redis", HealthStatus.HEALTHY, response_time_ms=25)
        health_monitor._update_service_health(result)

        service_health = health_monitor.get_service_health("redis")

        assert service_health is not None
        assert service_health.service == "redis"
        assert service_health.current_status == HealthStatus.HEALTHY

        # Test non-existent service
        assert health_monitor.get_service_health("nonexistent") is None

    def test_get_all_service_health(self, health_monitor):
        """Test getting health information for all services."""
        all_health = health_monitor.get_all_service_health()

        assert len(all_health) == 3
        assert "database" in all_health
        assert "redis" in all_health
        assert "smtp" in all_health

        for service_health in all_health.values():
            assert isinstance(service_health, ServiceHealth)

    def test_is_service_healthy(self, health_monitor):
        """Test checking if specific service is healthy."""
        # Initially all services are unknown
        assert health_monitor.is_service_healthy("database") is False

        # Make database healthy
        result = HealthCheckResult("database", HealthStatus.HEALTHY)
        health_monitor._update_service_health(result)

        assert health_monitor.is_service_healthy("database") is True
        assert health_monitor.is_service_healthy("redis") is False  # Still unknown

        # Test non-existent service
        assert health_monitor.is_service_healthy("nonexistent") is False

    def test_are_all_services_healthy(self, health_monitor):
        """Test checking if all services are healthy."""
        # Initially all services are unknown
        assert health_monitor.are_all_services_healthy() is False

        # Make all services healthy
        for service in ["database", "redis", "smtp"]:
            result = HealthCheckResult(service, HealthStatus.HEALTHY)
            health_monitor._update_service_health(result)

        assert health_monitor.are_all_services_healthy() is True

        # Make one service unhealthy
        result = HealthCheckResult("smtp", HealthStatus.UNHEALTHY, error="Error")
        health_monitor._update_service_health(result)

        assert health_monitor.are_all_services_healthy() is False

    def test_get_health_summary(self, health_monitor):
        """Test getting comprehensive health summary."""
        # Make database healthy, redis unhealthy, smtp unknown
        db_result = HealthCheckResult("database", HealthStatus.HEALTHY)
        redis_result = HealthCheckResult("redis", HealthStatus.UNHEALTHY, error="Error")

        health_monitor._update_service_health(db_result)
        health_monitor._update_service_health(redis_result)

        summary = health_monitor.get_health_summary()

        assert summary["overall_healthy"] is False
        assert "database" in summary["healthy_services"]
        assert "redis" in summary["unhealthy_services"]
        assert "smtp" in summary["unknown_services"]
        assert summary["total_services"] == 3
        assert summary["healthy_count"] == 1
        assert summary["unhealthy_count"] == 1
        assert "timestamp" in summary

    def test_get_health_summary_all_healthy(self, health_monitor):
        """Test health summary when all services are healthy."""
        # Make all services healthy
        for service in ["database", "redis", "smtp"]:
            result = HealthCheckResult(service, HealthStatus.HEALTHY)
            health_monitor._update_service_health(result)

        summary = health_monitor.get_health_summary()

        assert summary["overall_healthy"] is True
        assert len(summary["healthy_services"]) == 3
        assert len(summary["unhealthy_services"]) == 0
        assert len(summary["unknown_services"]) == 0
        assert summary["healthy_count"] == 3
        assert summary["unhealthy_count"] == 0


class TestHealthMonitorGlobalFunctions:
    """Test global health monitor functions."""

    def test_init_and_get_health_monitor(self, mock_config):
        """Test initializing and getting global health monitor."""
        # Initialize health monitor
        monitor = init_health_monitor(mock_config)

        assert monitor is not None
        assert isinstance(monitor, HealthMonitor)

        # Get the same instance
        same_monitor = get_health_monitor()
        assert same_monitor is monitor

    def test_get_health_monitor_not_initialized(self):
        """Test getting health monitor when not initialized."""
        # Reset global state
        import telegram_prompt_bot.health_checks

        telegram_prompt_bot.infrastructure.health_checks.health_monitor = None

        with pytest.raises(RuntimeError, match="Health monitor not initialized"):
            get_health_monitor()


class TestHealthMonitorIntegration:
    """Integration tests for health monitoring."""

    @patch.object(HealthMonitor, "check_all_services")
    async def test_monitoring_loop_integration(self, mock_check_all, health_monitor):
        """Test monitoring loop integration with service updates."""
        # Mock health check results
        mock_results = {
            "database": HealthCheckResult(
                "database", HealthStatus.HEALTHY, response_time_ms=50
            ),
            "redis": HealthCheckResult(
                "redis", HealthStatus.UNHEALTHY, error="Connection failed"
            ),
            "smtp": HealthCheckResult(
                "smtp", HealthStatus.HEALTHY, response_time_ms=100
            ),
        }
        mock_check_all.return_value = mock_results

        # Start monitoring with short interval
        await health_monitor.start_monitoring(check_interval=0.1)

        # Wait for at least one monitoring cycle
        await asyncio.sleep(0.2)

        # Stop monitoring
        await health_monitor.stop_monitoring()

        # Verify services were updated
        assert health_monitor.is_service_healthy("database") is True
        assert health_monitor.is_service_healthy("redis") is False
        assert health_monitor.is_service_healthy("smtp") is True

        # Verify check was called
        assert mock_check_all.called

    @patch.object(HealthMonitor, "check_all_services")
    async def test_monitoring_loop_exception_handling(
        self, mock_check_all, health_monitor
    ):
        """Test monitoring loop handles exceptions gracefully."""
        # Mock exception on first call, then success
        mock_check_all.side_effect = [
            Exception("Monitoring error"),
            {
                "database": HealthCheckResult("database", HealthStatus.HEALTHY),
                "redis": HealthCheckResult("redis", HealthStatus.HEALTHY),
                "smtp": HealthCheckResult("smtp", HealthStatus.HEALTHY),
            },
        ]

        # Start monitoring with short interval
        await health_monitor.start_monitoring(check_interval=0.1)

        # Wait for monitoring cycles
        await asyncio.sleep(0.3)

        # Stop monitoring
        await health_monitor.stop_monitoring()

        # Verify monitoring continued after exception
        assert mock_check_all.call_count >= 2
