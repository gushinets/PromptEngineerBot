"""
Graceful degradation system for service failures.

This module provides fallback behavior when external services (Redis, SMTP, Database)
are unavailable, ensuring the bot continues to function with reduced capabilities
rather than failing completely.
"""

import asyncio
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from telegram_bot.utils.config import BotConfig
from telegram_bot.utils.health_checks import HealthStatus, get_health_monitor
from telegram_bot.utils.logging_utils import get_logger

logger = get_logger(__name__)


class ServiceType(Enum):
    """Types of services that can degrade."""

    DATABASE = "database"
    REDIS = "redis"
    SMTP = "smtp"


class DegradationLevel(Enum):
    """Levels of service degradation."""

    NORMAL = "normal"  # All services healthy
    PARTIAL = "partial"  # Some services degraded
    MINIMAL = "minimal"  # Most services degraded
    EMERGENCY = "emergency"  # Critical services only


@dataclass
class DegradationRule:
    """Rule for handling service degradation."""

    service: ServiceType
    fallback_action: str
    user_message_key: str
    priority: int = 1  # Higher priority rules are applied first


@dataclass
class DegradationState:
    """Current degradation state of the system."""

    level: DegradationLevel
    degraded_services: List[ServiceType]
    active_fallbacks: List[str]
    user_message: Optional[str] = None


class GracefulDegradationManager:
    """
    Manager for graceful degradation of services.

    This class monitors service health and applies appropriate fallback
    behaviors when services become unavailable, ensuring the bot continues
    to provide value to users even during partial outages.
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self._degradation_rules = self._init_degradation_rules()
        self._current_state = DegradationState(
            level=DegradationLevel.NORMAL, degraded_services=[], active_fallbacks=[]
        )
        self._fallback_handlers: Dict[str, Callable] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_running = False

        # Register default fallback handlers
        self._register_default_handlers()

    def _init_degradation_rules(self) -> List[DegradationRule]:
        """Initialize degradation rules for different service failures."""
        return [
            # Redis degradation rules
            DegradationRule(
                service=ServiceType.REDIS,
                fallback_action="disable_email_auth",
                user_message_key="redis_unavailable",
                priority=3,
            ),
            DegradationRule(
                service=ServiceType.REDIS,
                fallback_action="disable_rate_limiting",
                user_message_key="rate_limiting_disabled",
                priority=2,
            ),
            DegradationRule(
                service=ServiceType.REDIS,
                fallback_action="disable_flow_state",
                user_message_key="flow_state_disabled",
                priority=1,
            ),
            # SMTP degradation rules
            DegradationRule(
                service=ServiceType.SMTP,
                fallback_action="email_to_chat_fallback",
                user_message_key="smtp_unavailable",
                priority=2,
            ),
            DegradationRule(
                service=ServiceType.SMTP,
                fallback_action="queue_emails_for_retry",
                user_message_key="email_queued",
                priority=1,
            ),
            # Database degradation rules
            DegradationRule(
                service=ServiceType.DATABASE,
                fallback_action="disable_user_persistence",
                user_message_key="database_unavailable",
                priority=3,
            ),
            DegradationRule(
                service=ServiceType.DATABASE,
                fallback_action="disable_audit_logging",
                user_message_key="audit_disabled",
                priority=1,
            ),
        ]

    def _register_default_handlers(self):
        """Register default fallback handlers."""
        self._fallback_handlers.update(
            {
                "disable_email_auth": self._handle_disable_email_auth,
                "disable_rate_limiting": self._handle_disable_rate_limiting,
                "disable_flow_state": self._handle_disable_flow_state,
                "email_to_chat_fallback": self._handle_email_to_chat_fallback,
                "queue_emails_for_retry": self._handle_queue_emails_for_retry,
                "disable_user_persistence": self._handle_disable_user_persistence,
                "disable_audit_logging": self._handle_disable_audit_logging,
            }
        )

    def register_fallback_handler(self, action: str, handler: Callable):
        """
        Register a custom fallback handler.

        Args:
            action: Fallback action name
            handler: Callable to handle the fallback
        """
        self._fallback_handlers[action] = handler
        logger.info(f"DEGRADATION_HANDLER_REGISTERED: {action}")

    async def check_and_update_degradation(self) -> DegradationState:
        """
        Check service health and update degradation state.

        Returns:
            Current degradation state
        """
        try:
            health_monitor = get_health_monitor()

            # Get current service health
            service_health = {
                ServiceType.DATABASE: health_monitor.is_service_healthy("database"),
                ServiceType.REDIS: health_monitor.is_service_healthy("redis"),
                ServiceType.SMTP: health_monitor.is_service_healthy("smtp"),
            }

            # Determine degraded services
            degraded_services = [
                service
                for service, is_healthy in service_health.items()
                if not is_healthy
            ]

            # Check if degradation state changed
            if set(degraded_services) != set(self._current_state.degraded_services):
                await self._update_degradation_state(degraded_services)

            return self._current_state

        except Exception as e:
            logger.error(
                f"DEGRADATION_CHECK_ERROR: Failed to check degradation - {str(e)}"
            )
            return self._current_state

    async def _update_degradation_state(self, degraded_services: List[ServiceType]):
        """Update degradation state and apply fallback rules."""
        old_state = self._current_state

        # Determine new degradation level
        new_level = self._calculate_degradation_level(degraded_services)

        # Create new state
        self._current_state = DegradationState(
            level=new_level, degraded_services=degraded_services, active_fallbacks=[]
        )

        # Apply degradation rules
        await self._apply_degradation_rules(degraded_services)

        # Log state change
        if old_state.level != new_level:
            logger.info(
                f"DEGRADATION_LEVEL_CHANGED: {old_state.level.value} -> {new_level.value}",
                degraded_services=[s.value for s in degraded_services],
                active_fallbacks=self._current_state.active_fallbacks,
            )

        # Log service recovery
        recovered_services = set(old_state.degraded_services) - set(degraded_services)
        for service in recovered_services:
            logger.info(f"SERVICE_RECOVERED: {service.value} is now healthy")

        # Log new service failures
        new_failures = set(degraded_services) - set(old_state.degraded_services)
        for service in new_failures:
            logger.warning(f"SERVICE_DEGRADED: {service.value} is now unhealthy")

    def _calculate_degradation_level(
        self, degraded_services: List[ServiceType]
    ) -> DegradationLevel:
        """Calculate overall degradation level based on degraded services."""
        if not degraded_services:
            return DegradationLevel.NORMAL

        # Critical services that cause emergency mode
        critical_services = {ServiceType.DATABASE}

        # Important services that cause minimal mode
        important_services = {ServiceType.REDIS, ServiceType.SMTP}

        degraded_set = set(degraded_services)

        if degraded_set & critical_services:
            return DegradationLevel.EMERGENCY
        elif len(degraded_set & important_services) >= 2:
            return DegradationLevel.MINIMAL
        elif degraded_set & important_services:
            return DegradationLevel.PARTIAL
        else:
            return DegradationLevel.NORMAL

    async def _apply_degradation_rules(self, degraded_services: List[ServiceType]):
        """Apply degradation rules for failed services."""
        applicable_rules = []

        # Find applicable rules
        for service in degraded_services:
            service_rules = [
                rule for rule in self._degradation_rules if rule.service == service
            ]
            applicable_rules.extend(service_rules)

        # Sort by priority (higher first)
        applicable_rules.sort(key=lambda r: r.priority, reverse=True)

        # Apply rules
        for rule in applicable_rules:
            try:
                await self._apply_fallback_rule(rule)
                self._current_state.active_fallbacks.append(rule.fallback_action)
            except Exception as e:
                logger.error(
                    f"FALLBACK_RULE_ERROR: Failed to apply rule {rule.fallback_action} - {str(e)}"
                )

    async def _apply_fallback_rule(self, rule: DegradationRule):
        """Apply a specific fallback rule."""
        handler = self._fallback_handlers.get(rule.fallback_action)
        if not handler:
            logger.warning(
                f"FALLBACK_HANDLER_MISSING: No handler for {rule.fallback_action}"
            )
            return

        logger.info(
            f"APPLYING_FALLBACK: {rule.fallback_action} for {rule.service.value}"
        )

        if asyncio.iscoroutinefunction(handler):
            await handler(rule)
        else:
            handler(rule)

    # Default fallback handlers

    async def _handle_disable_email_auth(self, rule: DegradationRule):
        """Handle disabling email authentication when Redis is unavailable."""
        logger.info(
            "FALLBACK_APPLIED: Email authentication disabled (Redis unavailable)"
        )
        # This would be used by bot handlers to skip email auth flow

    async def _handle_disable_rate_limiting(self, rule: DegradationRule):
        """Handle disabling rate limiting when Redis is unavailable."""
        logger.info("FALLBACK_APPLIED: Rate limiting disabled (Redis unavailable)")
        # This would be used by auth service to skip rate limit checks

    async def _handle_disable_flow_state(self, rule: DegradationRule):
        """Handle disabling flow state management when Redis is unavailable."""
        logger.info(
            "FALLBACK_APPLIED: Flow state management disabled (Redis unavailable)"
        )
        # This would be used by conversation managers to skip state persistence

    async def _handle_email_to_chat_fallback(self, rule: DegradationRule):
        """Handle falling back to chat delivery when SMTP is unavailable."""
        logger.info(
            "FALLBACK_APPLIED: Email delivery will fallback to chat (SMTP unavailable)"
        )
        # This would be used by email service to deliver content via chat instead

    async def _handle_queue_emails_for_retry(self, rule: DegradationRule):
        """Handle queueing emails for retry when SMTP is temporarily unavailable."""
        logger.info(
            "FALLBACK_APPLIED: Emails will be queued for retry (SMTP temporarily unavailable)"
        )
        # This would be used by email service to queue emails for later delivery

    async def _handle_disable_user_persistence(self, rule: DegradationRule):
        """Handle disabling user data persistence when database is unavailable."""
        logger.warning(
            "FALLBACK_APPLIED: User data persistence disabled (Database unavailable)"
        )
        # This would be used by auth service to skip user data storage

    async def _handle_disable_audit_logging(self, rule: DegradationRule):
        """Handle disabling audit logging when database is unavailable."""
        logger.info("FALLBACK_APPLIED: Audit logging disabled (Database unavailable)")
        # This would be used by audit service to skip event logging

    def get_user_message(self, language: str = "EN") -> Optional[str]:
        """
        Get user-friendly message about current service degradation.

        Args:
            language: Language code (EN or RU)

        Returns:
            User message or None if no degradation
        """
        if self._current_state.level == DegradationLevel.NORMAL:
            return None

        # Import here to avoid circular imports
        from .email_templates import _

        if ServiceType.REDIS in self._current_state.degraded_services:
            return _(
                "⚠️ Сервис временно недоступен. Попробуйте позже или используйте обычную оптимизацию промптов.",
                "⚠️ Service temporarily unavailable. Please try again later or use regular prompt optimization.",
                language,
            )

        if ServiceType.SMTP in self._current_state.degraded_services:
            return _(
                "📧 Отправка email временно недоступна. Результаты будут показаны в чате.",
                "📧 Email delivery temporarily unavailable. Results will be shown in chat.",
                language,
            )

        if ServiceType.DATABASE in self._current_state.degraded_services:
            return _(
                "⚠️ Система работает в ограниченном режиме. Некоторые функции могут быть недоступны.",
                "⚠️ System running in limited mode. Some features may be unavailable.",
                language,
            )

        return _(
            "⚠️ Система работает в ограниченном режиме.",
            "⚠️ System running in limited mode.",
            language,
        )

    def is_service_available(self, service: ServiceType) -> bool:
        """
        Check if a specific service is available (not degraded).

        Args:
            service: Service type to check

        Returns:
            True if service is available, False if degraded
        """
        return service not in self._current_state.degraded_services

    def is_email_auth_available(self) -> bool:
        """Check if email authentication is available."""
        return self.is_service_available(ServiceType.REDIS)

    def is_email_delivery_available(self) -> bool:
        """Check if email delivery is available."""
        return self.is_service_available(ServiceType.SMTP)

    def is_user_persistence_available(self) -> bool:
        """Check if user data persistence is available."""
        return self.is_service_available(ServiceType.DATABASE)

    def should_use_chat_fallback(self) -> bool:
        """Check if should fallback to chat delivery instead of email."""
        return not self.is_email_delivery_available()

    def should_skip_rate_limiting(self) -> bool:
        """Check if should skip rate limiting due to Redis unavailability."""
        return not self.is_service_available(ServiceType.REDIS)

    def should_skip_audit_logging(self) -> bool:
        """Check if should skip audit logging due to database unavailability."""
        return not self.is_service_available(ServiceType.DATABASE)

    def get_degradation_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive degradation summary.

        Returns:
            Dictionary with degradation information
        """
        return {
            "level": self._current_state.level.value,
            "degraded_services": [
                s.value for s in self._current_state.degraded_services
            ],
            "active_fallbacks": self._current_state.active_fallbacks,
            "services_available": {
                "email_auth": self.is_email_auth_available(),
                "email_delivery": self.is_email_delivery_available(),
                "user_persistence": self.is_user_persistence_available(),
            },
            "fallback_behaviors": {
                "use_chat_fallback": self.should_use_chat_fallback(),
                "skip_rate_limiting": self.should_skip_rate_limiting(),
                "skip_audit_logging": self.should_skip_audit_logging(),
            },
        }

    async def start_monitoring(self, check_interval: int = 60):
        """
        Start periodic degradation monitoring.

        Args:
            check_interval: Interval between checks in seconds
        """
        if self._monitoring_running:
            logger.warning(
                "DEGRADATION_MONITOR_ALREADY_RUNNING: Monitoring is already running"
            )
            return

        self._monitoring_running = True
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(check_interval)
        )

        logger.info(
            f"DEGRADATION_MONITOR_STARTED: Monitoring started with {check_interval}s interval"
        )

    async def stop_monitoring(self):
        """Stop periodic degradation monitoring."""
        if not self._monitoring_running:
            return

        self._monitoring_running = False

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
            self._monitoring_task = None

        logger.info("DEGRADATION_MONITOR_STOPPED: Monitoring stopped")

    async def _monitoring_loop(self, check_interval: int):
        """Main monitoring loop for degradation checks."""
        logger.info("DEGRADATION_MONITOR_LOOP_START: Starting degradation monitoring")

        while self._monitoring_running:
            try:
                await self.check_and_update_degradation()
                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(
                    f"DEGRADATION_MONITOR_ERROR: Monitoring loop error - {str(e)}"
                )
                await asyncio.sleep(check_interval)

        logger.info("DEGRADATION_MONITOR_LOOP_STOP: Degradation monitoring stopped")


# Global degradation manager instance
degradation_manager: Optional[GracefulDegradationManager] = None


def init_degradation_manager(config: BotConfig) -> GracefulDegradationManager:
    """
    Initialize global degradation manager.

    Args:
        config: BotConfig instance

    Returns:
        GracefulDegradationManager instance
    """
    global degradation_manager
    degradation_manager = GracefulDegradationManager(config)
    return degradation_manager


def get_degradation_manager() -> GracefulDegradationManager:
    """
    Get the global degradation manager instance.

    Returns:
        GracefulDegradationManager instance

    Raises:
        RuntimeError: If degradation manager is not initialized
    """
    if degradation_manager is None:
        raise RuntimeError(
            "Degradation manager not initialized. Call init_degradation_manager() first."
        )
    return degradation_manager


# Convenience functions for common degradation checks


def is_email_auth_available() -> bool:
    """Check if email authentication is available."""
    try:
        return get_degradation_manager().is_email_auth_available()
    except RuntimeError:
        # If degradation manager not initialized, assume services are available
        return True


def is_email_delivery_available() -> bool:
    """Check if email delivery is available."""
    try:
        return get_degradation_manager().is_email_delivery_available()
    except RuntimeError:
        # If degradation manager not initialized, assume services are available
        return True


def should_use_chat_fallback() -> bool:
    """Check if should fallback to chat delivery."""
    try:
        return get_degradation_manager().should_use_chat_fallback()
    except RuntimeError:
        # If degradation manager not initialized, don't use fallback
        return False


def should_skip_rate_limiting() -> bool:
    """Check if should skip rate limiting."""
    try:
        return get_degradation_manager().should_skip_rate_limiting()
    except RuntimeError:
        # If degradation manager not initialized, don't skip rate limiting
        return False


def get_user_degradation_message(language: str = "EN") -> Optional[str]:
    """Get user message about current degradation."""
    try:
        return get_degradation_manager().get_user_message(language)
    except RuntimeError:
        # If degradation manager not initialized, no message
        return None


def check_email_flow_readiness(language: str = "EN") -> tuple[bool, Optional[str]]:
    """
    Check if email flow is ready to proceed.

    Args:
        language: Language for user messages

    Returns:
        Tuple of (is_ready, user_message)
        - is_ready: True if email flow can proceed
        - user_message: Message to show user if not ready, None if ready
    """
    try:
        manager = get_degradation_manager()

        # Check if Redis is available for email auth
        if not manager.is_email_auth_available():
            message = manager.get_user_message(language)
            return False, message

        # Email flow is ready
        return True, None

    except RuntimeError:
        # If degradation manager not initialized, assume ready
        return True, None


def handle_smtp_fallback(language: str = "EN") -> tuple[bool, Optional[str]]:
    """
    Handle SMTP fallback when email delivery is unavailable.

    Args:
        language: Language for user messages

    Returns:
        Tuple of (should_fallback, user_message)
        - should_fallback: True if should fallback to chat delivery
        - user_message: Message to show user about fallback, None if no fallback needed
    """
    try:
        manager = get_degradation_manager()

        # Check if SMTP is available for email delivery
        if not manager.is_email_delivery_available():
            # Import here to avoid circular imports
            from .email_templates import _

            message = _(
                "📧 Отправка email временно недоступна. Результаты будут показаны в чате.",
                "📧 Email delivery temporarily unavailable. Results will be shown in chat.",
                language,
            )
            return True, message

        # SMTP is available, no fallback needed
        return False, None

    except RuntimeError:
        # If degradation manager not initialized, don't fallback
        return False, None
