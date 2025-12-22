"""
Tests for graceful degradation system.

This module tests fallback behavior when Redis is unavailable, SMTP fails,
and other service degradation scenarios with user-friendly error messages.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.graceful_degradation import (
    DegradationLevel,
    DegradationRule,
    DegradationState,
    GracefulDegradationManager,
    ServiceType,
    get_degradation_manager,
    get_user_degradation_message,
    init_degradation_manager,
    is_email_auth_available,
    is_email_delivery_available,
    should_skip_rate_limiting,
    should_use_chat_fallback,
)


@pytest.fixture
def mock_config():
    """Create mock BotConfig for testing."""
    config = MagicMock(spec=BotConfig)
    config.language = "EN"
    return config


@pytest.fixture
def mock_health_monitor():
    """Create mock health monitor."""
    monitor = MagicMock()
    monitor.is_service_healthy.return_value = True
    return monitor


class TestServiceType:
    """Test ServiceType enumeration."""

    def test_service_type_values(self):
        """Test service type enumeration values."""
        assert ServiceType.DATABASE.value == "database"
        assert ServiceType.REDIS.value == "redis"
        assert ServiceType.SMTP.value == "smtp"


class TestDegradationLevel:
    """Test DegradationLevel enumeration."""

    def test_degradation_level_values(self):
        """Test degradation level enumeration values."""
        assert DegradationLevel.NORMAL.value == "normal"
        assert DegradationLevel.PARTIAL.value == "partial"
        assert DegradationLevel.MINIMAL.value == "minimal"
        assert DegradationLevel.EMERGENCY.value == "emergency"


class TestDegradationRule:
    """Test DegradationRule dataclass."""

    def test_degradation_rule_creation(self):
        """Test DegradationRule creation."""
        rule = DegradationRule(
            service=ServiceType.REDIS,
            fallback_action="disable_email_auth",
            user_message_key="redis_unavailable",
            priority=3,
        )

        assert rule.service == ServiceType.REDIS
        assert rule.fallback_action == "disable_email_auth"
        assert rule.user_message_key == "redis_unavailable"
        assert rule.priority == 3

    def test_degradation_rule_defaults(self):
        """Test DegradationRule with default values."""
        rule = DegradationRule(
            service=ServiceType.SMTP,
            fallback_action="email_to_chat_fallback",
            user_message_key="smtp_unavailable",
        )

        assert rule.service == ServiceType.SMTP
        assert rule.fallback_action == "email_to_chat_fallback"
        assert rule.user_message_key == "smtp_unavailable"
        assert rule.priority == 1  # Default priority


class TestDegradationState:
    """Test DegradationState dataclass."""

    def test_degradation_state_creation(self):
        """Test DegradationState creation."""
        state = DegradationState(
            level=DegradationLevel.PARTIAL,
            degraded_services=[ServiceType.REDIS],
            active_fallbacks=["disable_email_auth"],
            user_message="Service degraded",
        )

        assert state.level == DegradationLevel.PARTIAL
        assert ServiceType.REDIS in state.degraded_services
        assert "disable_email_auth" in state.active_fallbacks
        assert state.user_message == "Service degraded"


class TestGracefulDegradationManager:
    """Test GracefulDegradationManager class."""

    @pytest.fixture
    def degradation_manager(self, mock_config):
        """Create GracefulDegradationManager instance for testing."""
        return GracefulDegradationManager(mock_config)

    def test_manager_initialization(self, degradation_manager):
        """Test degradation manager initialization."""
        assert degradation_manager.config.language == "EN"
        assert len(degradation_manager._degradation_rules) > 0
        assert len(degradation_manager._fallback_handlers) > 0
        assert degradation_manager._current_state.level == DegradationLevel.NORMAL

    def test_init_degradation_rules(self, degradation_manager):
        """Test degradation rules initialization."""
        rules = degradation_manager._degradation_rules

        # Check that rules exist for all service types
        redis_rules = [r for r in rules if r.service == ServiceType.REDIS]
        smtp_rules = [r for r in rules if r.service == ServiceType.SMTP]
        db_rules = [r for r in rules if r.service == ServiceType.DATABASE]

        assert len(redis_rules) > 0
        assert len(smtp_rules) > 0
        assert len(db_rules) > 0

        # Check specific rules
        assert any(r.fallback_action == "disable_email_auth" for r in redis_rules)
        assert any(r.fallback_action == "email_to_chat_fallback" for r in smtp_rules)
        assert any(r.fallback_action == "disable_user_persistence" for r in db_rules)

    def test_register_fallback_handler(self, degradation_manager):
        """Test registering custom fallback handler."""

        async def custom_handler(rule):
            return "custom result"

        degradation_manager.register_fallback_handler("custom_action", custom_handler)

        assert "custom_action" in degradation_manager._fallback_handlers
        assert degradation_manager._fallback_handlers["custom_action"] == custom_handler

    def test_calculate_degradation_level_normal(self, degradation_manager):
        """Test degradation level calculation for normal state."""
        level = degradation_manager._calculate_degradation_level([])
        assert level == DegradationLevel.NORMAL

    def test_calculate_degradation_level_partial(self, degradation_manager):
        """Test degradation level calculation for partial degradation."""
        level = degradation_manager._calculate_degradation_level([ServiceType.REDIS])
        assert level == DegradationLevel.PARTIAL

    def test_calculate_degradation_level_minimal(self, degradation_manager):
        """Test degradation level calculation for minimal functionality."""
        level = degradation_manager._calculate_degradation_level(
            [ServiceType.REDIS, ServiceType.SMTP]
        )
        assert level == DegradationLevel.MINIMAL

    def test_calculate_degradation_level_emergency(self, degradation_manager):
        """Test degradation level calculation for emergency mode."""
        level = degradation_manager._calculate_degradation_level([ServiceType.DATABASE])
        assert level == DegradationLevel.EMERGENCY

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_check_and_update_degradation_no_change(
        self, mock_get_monitor, degradation_manager
    ):
        """Test degradation check when no services are degraded."""
        mock_monitor = MagicMock()
        mock_monitor.is_service_healthy.return_value = True
        mock_get_monitor.return_value = mock_monitor

        state = await degradation_manager.check_and_update_degradation()

        assert state.level == DegradationLevel.NORMAL
        assert len(state.degraded_services) == 0
        assert len(state.active_fallbacks) == 0

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_check_and_update_degradation_redis_failed(
        self, mock_get_monitor, degradation_manager
    ):
        """Test degradation check when Redis fails."""
        mock_monitor = MagicMock()
        mock_monitor.is_service_healthy.side_effect = lambda service: service != "redis"
        mock_get_monitor.return_value = mock_monitor

        state = await degradation_manager.check_and_update_degradation()

        assert state.level == DegradationLevel.PARTIAL
        assert ServiceType.REDIS in state.degraded_services
        assert len(state.active_fallbacks) > 0

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_check_and_update_degradation_exception(
        self, mock_get_monitor, degradation_manager
    ):
        """Test degradation check when health monitor raises exception."""
        mock_get_monitor.side_effect = Exception("Health monitor error")

        state = await degradation_manager.check_and_update_degradation()

        # Should return current state without changes
        assert state.level == DegradationLevel.NORMAL

    async def test_apply_fallback_rule(self, degradation_manager):
        """Test applying a fallback rule."""
        rule = DegradationRule(
            service=ServiceType.REDIS,
            fallback_action="disable_email_auth",
            user_message_key="redis_unavailable",
        )

        # Mock the handler
        handler_called = False

        async def mock_handler(rule):
            nonlocal handler_called
            handler_called = True

        degradation_manager._fallback_handlers["disable_email_auth"] = mock_handler

        await degradation_manager._apply_fallback_rule(rule)

        assert handler_called

    async def test_apply_fallback_rule_missing_handler(self, degradation_manager):
        """Test applying fallback rule with missing handler."""
        rule = DegradationRule(
            service=ServiceType.REDIS,
            fallback_action="nonexistent_action",
            user_message_key="redis_unavailable",
        )

        # Should not raise exception
        await degradation_manager._apply_fallback_rule(rule)

    def test_get_user_message_normal(self, degradation_manager):
        """Test user message for normal state."""
        message = degradation_manager.get_user_message("EN")
        assert message is None

    def test_get_user_message_redis_degraded(self, degradation_manager):
        """Test user message when Redis is degraded."""
        degradation_manager._current_state = DegradationState(
            level=DegradationLevel.PARTIAL,
            degraded_services=[ServiceType.REDIS],
            active_fallbacks=[],
        )

        message = degradation_manager.get_user_message("EN")
        assert message is not None
        assert "temporarily unavailable" in message

    def test_get_user_message_smtp_degraded(self, degradation_manager):
        """Test user message when SMTP is degraded."""
        degradation_manager._current_state = DegradationState(
            level=DegradationLevel.PARTIAL,
            degraded_services=[ServiceType.SMTP],
            active_fallbacks=[],
        )

        message = degradation_manager.get_user_message("EN")
        assert message is not None
        assert "Email delivery" in message

    def test_get_user_message_database_degraded(self, degradation_manager):
        """Test user message when database is degraded."""
        degradation_manager._current_state = DegradationState(
            level=DegradationLevel.EMERGENCY,
            degraded_services=[ServiceType.DATABASE],
            active_fallbacks=[],
        )

        message = degradation_manager.get_user_message("EN")
        assert message is not None
        assert "limited mode" in message

    def test_get_user_message_russian(self, degradation_manager):
        """Test user message in Russian."""
        degradation_manager._current_state = DegradationState(
            level=DegradationLevel.PARTIAL,
            degraded_services=[ServiceType.REDIS],
            active_fallbacks=[],
        )

        message = degradation_manager.get_user_message("RU")
        assert message is not None
        assert "недоступен" in message

    def test_is_service_available(self, degradation_manager):
        """Test service availability check."""
        # Initially all services should be available
        assert degradation_manager.is_service_available(ServiceType.REDIS) is True
        assert degradation_manager.is_service_available(ServiceType.SMTP) is True
        assert degradation_manager.is_service_available(ServiceType.DATABASE) is True

        # Mark Redis as degraded
        degradation_manager._current_state = DegradationState(
            level=DegradationLevel.PARTIAL,
            degraded_services=[ServiceType.REDIS],
            active_fallbacks=[],
        )

        assert degradation_manager.is_service_available(ServiceType.REDIS) is False
        assert degradation_manager.is_service_available(ServiceType.SMTP) is True

    def test_convenience_methods(self, degradation_manager):
        """Test convenience methods for checking service availability."""
        assert degradation_manager.is_email_auth_available() is True
        assert degradation_manager.is_email_delivery_available() is True
        assert degradation_manager.is_user_persistence_available() is True
        assert degradation_manager.should_use_chat_fallback() is False
        assert degradation_manager.should_skip_rate_limiting() is False
        assert degradation_manager.should_skip_audit_logging() is False

        # Mark services as degraded
        degradation_manager._current_state = DegradationState(
            level=DegradationLevel.MINIMAL,
            degraded_services=[
                ServiceType.REDIS,
                ServiceType.SMTP,
                ServiceType.DATABASE,
            ],
            active_fallbacks=[],
        )

        assert degradation_manager.is_email_auth_available() is False
        assert degradation_manager.is_email_delivery_available() is False
        assert degradation_manager.is_user_persistence_available() is False
        assert degradation_manager.should_use_chat_fallback() is True
        assert degradation_manager.should_skip_rate_limiting() is True
        assert degradation_manager.should_skip_audit_logging() is True

    def test_get_degradation_summary(self, degradation_manager):
        """Test degradation summary generation."""
        degradation_manager._current_state = DegradationState(
            level=DegradationLevel.PARTIAL,
            degraded_services=[ServiceType.REDIS],
            active_fallbacks=["disable_email_auth"],
        )

        summary = degradation_manager.get_degradation_summary()

        assert summary["level"] == "partial"
        assert "redis" in summary["degraded_services"]
        assert "disable_email_auth" in summary["active_fallbacks"]
        assert summary["services_available"]["email_auth"] is False
        assert summary["services_available"]["email_delivery"] is True
        assert summary["fallback_behaviors"]["use_chat_fallback"] is False
        assert summary["fallback_behaviors"]["skip_rate_limiting"] is True

    async def test_start_stop_monitoring(self, degradation_manager):
        """Test starting and stopping degradation monitoring."""
        # Start monitoring
        await degradation_manager.start_monitoring(check_interval=1)

        assert degradation_manager._monitoring_running is True
        assert degradation_manager._monitoring_task is not None

        # Stop monitoring
        await degradation_manager.stop_monitoring()

        assert degradation_manager._monitoring_running is False
        assert degradation_manager._monitoring_task is None

    async def test_start_monitoring_already_running(self, degradation_manager):
        """Test starting monitoring when already running."""
        # Start monitoring
        await degradation_manager.start_monitoring()
        first_task = degradation_manager._monitoring_task

        # Try to start again
        await degradation_manager.start_monitoring()

        # Should still be the same task
        assert degradation_manager._monitoring_task == first_task

        # Clean up
        await degradation_manager.stop_monitoring()

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_monitoring_loop_integration(self, mock_get_monitor, degradation_manager):
        """Test monitoring loop integration."""
        mock_monitor = MagicMock()
        mock_monitor.is_service_healthy.return_value = True
        mock_get_monitor.return_value = mock_monitor

        # Start monitoring with short interval
        await degradation_manager.start_monitoring(check_interval=0.1)

        # Wait for at least one monitoring cycle
        await asyncio.sleep(0.2)

        # Stop monitoring
        await degradation_manager.stop_monitoring()

        # Verify health check was called
        assert mock_monitor.is_service_healthy.called


class TestDefaultFallbackHandlers:
    """Test default fallback handlers."""

    @pytest.fixture
    def degradation_manager(self, mock_config):
        """Create GracefulDegradationManager instance for testing."""
        return GracefulDegradationManager(mock_config)

    async def test_handle_disable_email_auth(self, degradation_manager):
        """Test disable email auth handler."""
        rule = DegradationRule(
            service=ServiceType.REDIS,
            fallback_action="disable_email_auth",
            user_message_key="redis_unavailable",
        )

        # Should not raise exception
        await degradation_manager._handle_disable_email_auth(rule)

    async def test_handle_disable_rate_limiting(self, degradation_manager):
        """Test disable rate limiting handler."""
        rule = DegradationRule(
            service=ServiceType.REDIS,
            fallback_action="disable_rate_limiting",
            user_message_key="redis_unavailable",
        )

        # Should not raise exception
        await degradation_manager._handle_disable_rate_limiting(rule)

    async def test_handle_email_to_chat_fallback(self, degradation_manager):
        """Test email to chat fallback handler."""
        rule = DegradationRule(
            service=ServiceType.SMTP,
            fallback_action="email_to_chat_fallback",
            user_message_key="smtp_unavailable",
        )

        # Should not raise exception
        await degradation_manager._handle_email_to_chat_fallback(rule)

    async def test_handle_disable_user_persistence(self, degradation_manager):
        """Test disable user persistence handler."""
        rule = DegradationRule(
            service=ServiceType.DATABASE,
            fallback_action="disable_user_persistence",
            user_message_key="database_unavailable",
        )

        # Should not raise exception
        await degradation_manager._handle_disable_user_persistence(rule)


class TestGlobalFunctions:
    """Test global functions for graceful degradation."""

    def test_init_and_get_degradation_manager(self, mock_config):
        """Test initializing and getting global degradation manager."""
        # Initialize degradation manager
        manager = init_degradation_manager(mock_config)

        assert manager is not None
        assert isinstance(manager, GracefulDegradationManager)

        # Get the same instance
        same_manager = get_degradation_manager()
        assert same_manager is manager

    def test_get_degradation_manager_not_initialized(self):
        """Test getting degradation manager when not initialized."""
        # Reset global state
        import telegram_bot.utils.graceful_degradation

        telegram_bot.utils.graceful_degradation.degradation_manager = None

        with pytest.raises(RuntimeError, match="Degradation manager not initialized"):
            get_degradation_manager()

    def test_convenience_functions_manager_initialized(self, mock_config):
        """Test convenience functions with initialized manager."""
        manager = init_degradation_manager(mock_config)

        # Test with all services available
        assert is_email_auth_available() is True
        assert is_email_delivery_available() is True
        assert should_use_chat_fallback() is False
        assert should_skip_rate_limiting() is False

        # Mark services as degraded
        manager._current_state = DegradationState(
            level=DegradationLevel.MINIMAL,
            degraded_services=[ServiceType.REDIS, ServiceType.SMTP],
            active_fallbacks=[],
        )

        assert is_email_auth_available() is False
        assert is_email_delivery_available() is False
        assert should_use_chat_fallback() is True
        assert should_skip_rate_limiting() is True

    def test_convenience_functions_manager_not_initialized(self):
        """Test convenience functions without initialized manager."""
        # Reset global state
        import telegram_bot.utils.graceful_degradation

        telegram_bot.utils.graceful_degradation.degradation_manager = None

        # Should return safe defaults
        assert is_email_auth_available() is True
        assert is_email_delivery_available() is True
        assert should_use_chat_fallback() is False
        assert should_skip_rate_limiting() is False

    def test_get_user_degradation_message_manager_initialized(self, mock_config):
        """Test user degradation message with initialized manager."""
        manager = init_degradation_manager(mock_config)

        # Normal state - no message
        message = get_user_degradation_message("EN")
        assert message is None

        # Degraded state - should have message
        manager._current_state = DegradationState(
            level=DegradationLevel.PARTIAL,
            degraded_services=[ServiceType.REDIS],
            active_fallbacks=[],
        )

        message = get_user_degradation_message("EN")
        assert message is not None
        assert "temporarily unavailable" in message

    def test_get_user_degradation_message_manager_not_initialized(self):
        """Test user degradation message without initialized manager."""
        # Reset global state
        import telegram_bot.utils.graceful_degradation

        telegram_bot.utils.graceful_degradation.degradation_manager = None

        message = get_user_degradation_message("EN")
        assert message is None


class TestDegradationScenarios:
    """Test specific degradation scenarios."""

    @pytest.fixture
    def degradation_manager(self, mock_config):
        """Create GracefulDegradationManager instance for testing."""
        return GracefulDegradationManager(mock_config)

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_redis_failure_scenario(self, mock_get_monitor, degradation_manager):
        """Test complete Redis failure scenario."""
        mock_monitor = MagicMock()
        mock_monitor.is_service_healthy.side_effect = lambda service: service != "redis"
        mock_get_monitor.return_value = mock_monitor

        state = await degradation_manager.check_and_update_degradation()

        # Verify Redis-specific degradation
        assert ServiceType.REDIS in state.degraded_services
        assert state.level == DegradationLevel.PARTIAL
        assert len(state.active_fallbacks) > 0

        # Verify convenience methods
        assert not degradation_manager.is_email_auth_available()
        assert degradation_manager.should_skip_rate_limiting()

        # Verify user message
        message = degradation_manager.get_user_message("EN")
        assert message is not None
        assert "temporarily unavailable" in message

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_smtp_failure_scenario(self, mock_get_monitor, degradation_manager):
        """Test complete SMTP failure scenario."""
        mock_monitor = MagicMock()
        mock_monitor.is_service_healthy.side_effect = lambda service: service != "smtp"
        mock_get_monitor.return_value = mock_monitor

        state = await degradation_manager.check_and_update_degradation()

        # Verify SMTP-specific degradation
        assert ServiceType.SMTP in state.degraded_services
        assert state.level == DegradationLevel.PARTIAL

        # Verify convenience methods
        assert not degradation_manager.is_email_delivery_available()
        assert degradation_manager.should_use_chat_fallback()

        # Verify user message
        message = degradation_manager.get_user_message("EN")
        assert message is not None
        assert "Email delivery" in message

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_database_failure_scenario(self, mock_get_monitor, degradation_manager):
        """Test complete database failure scenario."""
        mock_monitor = MagicMock()
        mock_monitor.is_service_healthy.side_effect = lambda service: service != "database"
        mock_get_monitor.return_value = mock_monitor

        state = await degradation_manager.check_and_update_degradation()

        # Verify database-specific degradation
        assert ServiceType.DATABASE in state.degraded_services
        assert state.level == DegradationLevel.EMERGENCY

        # Verify convenience methods
        assert not degradation_manager.is_user_persistence_available()
        assert degradation_manager.should_skip_audit_logging()

        # Verify user message
        message = degradation_manager.get_user_message("EN")
        assert message is not None
        assert "limited mode" in message

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_multiple_service_failure_scenario(self, mock_get_monitor, degradation_manager):
        """Test multiple service failure scenario."""
        mock_monitor = MagicMock()
        mock_monitor.is_service_healthy.side_effect = lambda service: service == "database"
        mock_get_monitor.return_value = mock_monitor

        state = await degradation_manager.check_and_update_degradation()

        # Verify multiple service degradation
        assert ServiceType.REDIS in state.degraded_services
        assert ServiceType.SMTP in state.degraded_services
        assert state.level == DegradationLevel.MINIMAL

        # Verify all fallback behaviors are active
        assert not degradation_manager.is_email_auth_available()
        assert not degradation_manager.is_email_delivery_available()
        assert degradation_manager.should_use_chat_fallback()
        assert degradation_manager.should_skip_rate_limiting()

    @patch("telegram_bot.utils.graceful_degradation.get_health_monitor")
    async def test_service_recovery_scenario(self, mock_get_monitor, degradation_manager):
        """Test service recovery scenario."""
        mock_monitor = MagicMock()

        # First, simulate Redis failure
        mock_monitor.is_service_healthy.side_effect = lambda service: service != "redis"
        mock_get_monitor.return_value = mock_monitor

        state1 = await degradation_manager.check_and_update_degradation()
        assert ServiceType.REDIS in state1.degraded_services

        # Then, simulate Redis recovery - clear side_effect and set return_value
        mock_monitor.is_service_healthy.side_effect = None
        mock_monitor.is_service_healthy.return_value = True

        state2 = await degradation_manager.check_and_update_degradation()
        assert ServiceType.REDIS not in state2.degraded_services
        assert state2.level == DegradationLevel.NORMAL
        assert len(state2.active_fallbacks) == 0
