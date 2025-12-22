#!/usr/bin/env python3
"""
Simple test script for health monitoring system.
This script tests the health monitoring functionality independently.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock


# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


from telegram_bot.utils.health_checks import (
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
    ServiceHealth,
    get_health_monitor,
    init_health_monitor,
)


def test_health_check_result():
    """Test HealthCheckResult creation."""
    print("Testing HealthCheckResult...")

    result = HealthCheckResult(service="database", status=HealthStatus.HEALTHY, response_time_ms=50)

    assert result.service == "database"
    assert result.status == HealthStatus.HEALTHY
    assert result.response_time_ms == 50
    assert result.error is None
    assert result.details is None
    print("✓ HealthCheckResult creation works")


def test_service_health():
    """Test ServiceHealth creation."""
    print("Testing ServiceHealth...")

    health = ServiceHealth(
        service="smtp",
        current_status=HealthStatus.HEALTHY,
    )

    assert health.service == "smtp"
    assert health.current_status == HealthStatus.HEALTHY
    assert health.consecutive_failures == 0
    assert health.last_healthy is None
    assert health.last_unhealthy is None
    print("✓ ServiceHealth creation works")


def test_health_monitor():
    """Test HealthMonitor initialization."""
    print("Testing HealthMonitor...")

    mock_config = MagicMock()
    mock_config.language = "en"

    monitor = HealthMonitor(config=mock_config)

    assert monitor.config == mock_config
    assert not monitor._monitoring_running
    assert len(monitor._services) == 3  # database, redis, smtp
    print("✓ HealthMonitor initialization works")


def test_service_health_tracking():
    """Test service health tracking."""
    print("Testing service health tracking...")

    mock_config = MagicMock()
    monitor = HealthMonitor(config=mock_config)

    # Simulate successful check
    result = HealthCheckResult(service="database", status=HealthStatus.HEALTHY)
    monitor._update_service_health(result)

    db_health = monitor.get_service_health("database")
    assert db_health is not None
    assert db_health.current_status == HealthStatus.HEALTHY
    assert db_health.consecutive_failures == 0

    # Simulate failure
    result = HealthCheckResult(
        service="database", status=HealthStatus.UNHEALTHY, error="connection_failed"
    )
    monitor._update_service_health(result)

    db_health = monitor.get_service_health("database")
    assert db_health.current_status == HealthStatus.UNHEALTHY
    assert db_health.consecutive_failures == 1

    print("✓ Service health tracking works")


def test_health_summary():
    """Test health summary generation."""
    print("Testing health summary...")

    mock_config = MagicMock()
    monitor = HealthMonitor(config=mock_config)

    # Update service health
    result_healthy = HealthCheckResult(service="database", status=HealthStatus.HEALTHY)
    result_unhealthy = HealthCheckResult(
        service="redis", status=HealthStatus.UNHEALTHY, error="connection_failed"
    )

    monitor._update_service_health(result_healthy)
    monitor._update_service_health(result_unhealthy)

    summary = monitor.get_health_summary()

    assert "overall_healthy" in summary or "overall_status" in summary
    assert "database" in str(summary)
    assert "redis" in str(summary)

    print("✓ Health summary generation works")


def test_global_health_monitor():
    """Test global health monitor functions."""
    print("Testing global health monitor...")

    mock_config = MagicMock()

    # Initialize
    monitor = init_health_monitor(config=mock_config)

    assert monitor.config == mock_config

    # Get should return same instance
    retrieved_monitor = get_health_monitor()
    assert retrieved_monitor is monitor

    print("✓ Global health monitor works")


async def test_monitoring_lifecycle():
    """Test monitoring start/stop lifecycle."""
    print("Testing monitoring lifecycle...")

    mock_config = MagicMock()
    monitor = HealthMonitor(config=mock_config)

    # Mock the check_all_services method to avoid actual health checks
    async def mock_check_all_services():
        return {
            "database": HealthCheckResult(service="database", status=HealthStatus.HEALTHY),
            "redis": HealthCheckResult(service="redis", status=HealthStatus.HEALTHY),
            "smtp": HealthCheckResult(service="smtp", status=HealthStatus.HEALTHY),
        }

    monitor.check_all_services = mock_check_all_services

    try:
        # Start monitoring with short interval
        await monitor.start_monitoring(check_interval=1)
        assert monitor._monitoring_running is True
        assert monitor._monitoring_task is not None

        # Give it a moment to start
        await asyncio.sleep(0.05)

        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor._monitoring_running is False

        print("✓ Monitoring lifecycle works")
    except Exception:
        # Stop monitoring if started
        if monitor._monitoring_running:
            await monitor.stop_monitoring()
        raise


def main():
    """Run all tests."""
    print("Running health monitoring system tests...\n")

    try:
        # Run synchronous tests
        test_health_check_result()
        test_service_health()
        test_health_monitor()
        test_service_health_tracking()
        test_health_summary()
        test_global_health_monitor()

        # Run async tests
        asyncio.run(test_monitoring_lifecycle())

        print("\n✅ All health monitoring tests passed!")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
