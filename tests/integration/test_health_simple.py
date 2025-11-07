#!/usr/bin/env python3
"""
Simple test script for health monitoring system.
This script tests the health monitoring functionality independently.
"""

import asyncio
import os
import sys


# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from datetime import UTC

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

    from datetime import datetime

    health = ServiceHealth(
        service="smtp",
        status=HealthStatus.HEALTHY,
        last_check=datetime.now(UTC),
    )

    assert health.service == "smtp"
    assert health.status == HealthStatus.HEALTHY
    assert health.consecutive_failures == 0
    assert health.last_success is None
    assert health.last_failure is None
    assert health.error_message is None
    print("✓ ServiceHealth creation works")


def test_health_monitor():
    """Test HealthMonitor initialization."""
    print("Testing HealthMonitor...")

    monitor = HealthMonitor(check_interval=1, failure_threshold=2, recovery_threshold=1)

    assert monitor.check_interval == 1
    assert monitor.failure_threshold == 2
    assert monitor.recovery_threshold == 1
    assert not monitor._monitoring_active
    assert len(monitor._service_health) == 0
    print("✓ HealthMonitor initialization works")


def test_mask_sensitive_data():
    """Test sensitive data masking."""
    print("Testing sensitive data masking...")

    monitor = HealthMonitor()

    # Test email masking
    masked_email = monitor._mask_sensitive_data("user@example.com")
    assert masked_email == "u***@e***.com"

    # Test telegram ID masking
    masked_tg_id = monitor._mask_sensitive_data("123456789")
    assert masked_tg_id == "123***789"

    # Test non-sensitive data
    normal_data = monitor._mask_sensitive_data("normal_string")
    assert normal_data == "normal_string"

    print("✓ Sensitive data masking works")


def test_service_health_tracking():
    """Test service health tracking."""
    print("Testing service health tracking...")

    monitor = HealthMonitor(failure_threshold=2)

    # Simulate successful check
    results = {"database": HealthCheckResult(service="database", status=HealthStatus.HEALTHY)}

    monitor._update_service_health(results)

    db_health = monitor.get_service_health("database")
    assert db_health is not None
    assert db_health.status == HealthStatus.HEALTHY
    assert db_health.consecutive_failures == 0

    # Simulate failure
    results = {
        "database": HealthCheckResult(
            service="database", status=HealthStatus.UNHEALTHY, error="connection_failed"
        )
    }

    monitor._update_service_health(results)

    db_health = monitor.get_service_health("database")
    assert db_health.status == HealthStatus.DEGRADED  # First failure
    assert db_health.consecutive_failures == 1

    # Second failure should make it unhealthy
    monitor._update_service_health(results)

    db_health = monitor.get_service_health("database")
    assert db_health.status == HealthStatus.UNHEALTHY
    assert db_health.consecutive_failures == 2
    assert db_health.error_message == "connection_failed"

    print("✓ Service health tracking works")


def test_health_summary():
    """Test health summary generation."""
    print("Testing health summary...")

    from datetime import datetime

    monitor = HealthMonitor()

    now = datetime.now(UTC)

    # Add service health data
    monitor._service_health["database"] = ServiceHealth(
        service="database",
        status=HealthStatus.HEALTHY,
        last_check=now,
        last_success=now,
    )
    monitor._service_health["redis"] = ServiceHealth(
        service="redis",
        status=HealthStatus.UNHEALTHY,
        last_check=now,
        consecutive_failures=3,
        last_failure=now,
        error_message="connection_failed",
    )

    summary = monitor.get_health_summary()

    assert summary["overall_status"] == "degraded"  # Not all services healthy
    assert summary["total_services"] == 2
    assert summary["last_check"] is not None

    # Check service details
    assert "database" in summary["services"]
    assert "redis" in summary["services"]

    db_summary = summary["services"]["database"]
    assert db_summary["status"] == "healthy"
    assert db_summary["consecutive_failures"] == 0

    redis_summary = summary["services"]["redis"]
    assert redis_summary["status"] == "unhealthy"
    assert redis_summary["consecutive_failures"] == 3
    assert redis_summary["error"] == "connection_failed"

    print("✓ Health summary generation works")


def test_global_health_monitor():
    """Test global health monitor functions."""
    print("Testing global health monitor...")

    # Initialize
    monitor = init_health_monitor(check_interval=60, failure_threshold=5, recovery_threshold=3)

    assert monitor.check_interval == 60
    assert monitor.failure_threshold == 5
    assert monitor.recovery_threshold == 3

    # Get should return same instance
    retrieved_monitor = get_health_monitor()
    assert retrieved_monitor is monitor

    print("✓ Global health monitor works")


async def test_monitoring_lifecycle():
    """Test monitoring start/stop lifecycle."""
    print("Testing monitoring lifecycle...")

    monitor = HealthMonitor(check_interval=0.1)  # Very short interval for testing

    # Mock the check_all_services method to avoid actual health checks
    original_check = monitor.check_all_services
    monitor.check_all_services = dict

    try:
        # Start monitoring
        await monitor.start_monitoring()
        assert monitor._monitoring_active is True
        assert monitor._monitoring_task is not None

        # Give it a moment to start
        await asyncio.sleep(0.05)

        # Stop monitoring
        await monitor.stop_monitoring()
        assert monitor._monitoring_active is False

        print("✓ Monitoring lifecycle works")
    finally:
        # Restore original method
        monitor.check_all_services = original_check


def main():
    """Run all tests."""
    print("Running health monitoring system tests...\n")

    try:
        # Run synchronous tests
        test_health_check_result()
        test_service_health()
        test_health_monitor()
        test_mask_sensitive_data()
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
