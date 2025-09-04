"""
Simple tests for Task 8 implementation without complex fixtures.

This module tests the core functionality of health monitoring, logging utilities,
and graceful degradation without relying on problematic pytest fixtures.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.config import BotConfig
from src.graceful_degradation import (
    DegradationLevel,
    DegradationRule,
    DegradationState,
    GracefulDegradationManager,
    ServiceType,
)
from src.health_checks import (
    HealthCheckResult,
    HealthMonitor,
    HealthStatus,
    ServiceHealth,
)
from src.logging_utils import PIIProtectedFormatter, StructuredLogger, get_logger


def test_health_monitoring_basic():
    """Test basic health monitoring functionality."""
    # Create mock config
    config = MagicMock(spec=BotConfig)

    # Test HealthMonitor creation
    monitor = HealthMonitor(config)
    assert monitor is not None

    # Test service initialization
    assert "database" in monitor._services
    assert "redis" in monitor._services
    assert "smtp" in monitor._services

    # Test health status enum
    assert HealthStatus.HEALTHY.value == "healthy"
    assert HealthStatus.UNHEALTHY.value == "unhealthy"
    assert HealthStatus.UNKNOWN.value == "unknown"

    # Test health check result
    result = HealthCheckResult(
        service="database", status=HealthStatus.HEALTHY, response_time_ms=50
    )
    assert result.service == "database"
    assert result.status == HealthStatus.HEALTHY
    assert result.response_time_ms == 50

    print("✓ Health monitoring basic tests passed")


def test_graceful_degradation_basic():
    """Test basic graceful degradation functionality."""
    # Create mock config
    config = MagicMock(spec=BotConfig)
    config.language = "EN"

    # Test GracefulDegradationManager creation
    manager = GracefulDegradationManager(config)
    assert manager is not None

    # Test service types
    assert ServiceType.DATABASE.value == "database"
    assert ServiceType.REDIS.value == "redis"
    assert ServiceType.SMTP.value == "smtp"

    # Test degradation levels
    assert DegradationLevel.NORMAL.value == "normal"
    assert DegradationLevel.PARTIAL.value == "partial"
    assert DegradationLevel.MINIMAL.value == "minimal"
    assert DegradationLevel.EMERGENCY.value == "emergency"

    # Test degradation level calculation
    level = manager._calculate_degradation_level([])
    assert level == DegradationLevel.NORMAL

    level = manager._calculate_degradation_level([ServiceType.REDIS])
    assert level == DegradationLevel.PARTIAL

    level = manager._calculate_degradation_level([ServiceType.REDIS, ServiceType.SMTP])
    assert level == DegradationLevel.MINIMAL

    level = manager._calculate_degradation_level([ServiceType.DATABASE])
    assert level == DegradationLevel.EMERGENCY

    # Test service availability
    assert manager.is_service_available(ServiceType.REDIS) is True
    assert manager.is_service_available(ServiceType.SMTP) is True
    assert manager.is_service_available(ServiceType.DATABASE) is True

    print("✓ Graceful degradation basic tests passed")


def test_logging_utilities_basic():
    """Test basic logging utilities functionality."""
    # Test PII protected formatter
    formatter = PIIProtectedFormatter()
    assert formatter is not None

    # Test email masking
    masked = formatter._mask_pii("User email: user@example.com")
    assert "u***@e***.com" in masked
    assert "user@example.com" not in masked

    # Test telegram ID masking
    masked = formatter._mask_pii("telegram_id: 123456789")
    assert "123***789" in masked
    assert "123456789" not in masked

    # Test OTP masking
    masked = formatter._mask_pii("OTP code: 123456")
    assert "***OTP***" in masked
    assert "123456" not in masked

    # Test password masking
    masked = formatter._mask_pii("password=secret123")
    assert "password=***MASKED***" in masked
    assert "secret123" not in masked

    # Test structured logger
    logger = get_logger("test")
    assert isinstance(logger, StructuredLogger)

    # Test context formatting
    context_str = logger._format_context(
        email="user@example.com",
        telegram_id=123456789,
        otp="654321",
        password="secret",
        normal_field="value",
    )
    assert "u***@e***.com" in context_str
    assert "123***789" in context_str
    assert "***MASKED***" in context_str
    assert "normal_field=value" in context_str

    print("✓ Logging utilities basic tests passed")


async def test_health_monitoring_async():
    """Test async health monitoring functionality."""
    config = MagicMock(spec=BotConfig)
    monitor = HealthMonitor(config)

    # Test starting and stopping monitoring
    await monitor.start_monitoring(check_interval=1)
    assert monitor._monitoring_running is True
    assert monitor._monitoring_task is not None

    await monitor.stop_monitoring()
    assert monitor._monitoring_running is False
    assert monitor._monitoring_task is None

    print("✓ Health monitoring async tests passed")


async def test_graceful_degradation_async():
    """Test async graceful degradation functionality."""
    config = MagicMock(spec=BotConfig)
    config.language = "EN"
    manager = GracefulDegradationManager(config)

    # Test starting and stopping monitoring
    await manager.start_monitoring(check_interval=1)
    assert manager._monitoring_running is True
    assert manager._monitoring_task is not None

    await manager.stop_monitoring()
    assert manager._monitoring_running is False
    assert manager._monitoring_task is None

    print("✓ Graceful degradation async tests passed")


def test_degradation_rules():
    """Test degradation rules functionality."""
    config = MagicMock(spec=BotConfig)
    config.language = "EN"
    manager = GracefulDegradationManager(config)

    # Test that rules are initialized
    rules = manager._degradation_rules
    assert len(rules) > 0

    # Test that rules exist for all service types
    redis_rules = [r for r in rules if r.service == ServiceType.REDIS]
    smtp_rules = [r for r in rules if r.service == ServiceType.SMTP]
    db_rules = [r for r in rules if r.service == ServiceType.DATABASE]

    assert len(redis_rules) > 0
    assert len(smtp_rules) > 0
    assert len(db_rules) > 0

    # Test specific rules
    assert any(r.fallback_action == "disable_email_auth" for r in redis_rules)
    assert any(r.fallback_action == "email_to_chat_fallback" for r in smtp_rules)
    assert any(r.fallback_action == "disable_user_persistence" for r in db_rules)

    print("✓ Degradation rules tests passed")


def test_user_messages():
    """Test user message generation."""
    config = MagicMock(spec=BotConfig)
    config.language = "EN"
    manager = GracefulDegradationManager(config)

    # Test normal state - no message
    message = manager.get_user_message("EN")
    assert message is None

    # Test Redis degraded state
    manager._current_state = DegradationState(
        level=DegradationLevel.PARTIAL,
        degraded_services=[ServiceType.REDIS],
        active_fallbacks=[],
    )

    message = manager.get_user_message("EN")
    assert message is not None
    assert "temporarily unavailable" in message

    # Test SMTP degraded state
    manager._current_state = DegradationState(
        level=DegradationLevel.PARTIAL,
        degraded_services=[ServiceType.SMTP],
        active_fallbacks=[],
    )

    message = manager.get_user_message("EN")
    assert message is not None
    assert "Email delivery" in message

    # Test Russian messages
    message = manager.get_user_message("RU")
    assert message is not None
    assert "недоступна" in message or "недоступен" in message

    print("✓ User messages tests passed")


def run_all_tests():
    """Run all tests."""
    print("Running Task 8 implementation tests...\n")

    # Run synchronous tests
    test_health_monitoring_basic()
    test_graceful_degradation_basic()
    test_logging_utilities_basic()
    test_degradation_rules()
    test_user_messages()

    # Run asynchronous tests
    asyncio.run(test_health_monitoring_async())
    asyncio.run(test_graceful_degradation_async())

    print("\n🎉 All Task 8 implementation tests passed!")


if __name__ == "__main__":
    run_all_tests()
