"""
Health monitoring system for external dependencies.

This module provides health checks for database, Redis, and SMTP services,
with periodic monitoring, alerting, and status reporting.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, List, Optional

from telegram_bot.data.database import get_db_manager
from telegram_bot.services.redis_client import get_redis_client
from telegram_bot.utils.config import BotConfig

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    service: str
    status: HealthStatus
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None
    details: Optional[Dict] = None

    def __post_init__(self):
        if self.timestamp is None:
            from datetime import timezone

            self.timestamp = datetime.now(timezone.utc)


@dataclass
class ServiceHealth:
    """Health information for a service."""

    service: str
    current_status: HealthStatus
    last_healthy: Optional[datetime] = None
    last_unhealthy: Optional[datetime] = None
    consecutive_failures: int = 0
    total_checks: int = 0
    total_failures: int = 0
    average_response_time_ms: Optional[float] = None


class HealthMonitor:
    """
    Health monitoring system for external dependencies.

    Features:
    - Database, Redis, and SMTP health checks
    - Periodic health monitoring with configurable intervals
    - Health status reporting and logging
    - Failure detection and alerting
    """

    def __init__(self, config: BotConfig):
        self.config = config
        self._services: Dict[str, ServiceHealth] = {}
        self._monitoring_task: Optional[asyncio.Task] = None
        self._monitoring_running = False
        self._check_interval = 30  # seconds
        self._failure_threshold = 3  # consecutive failures before alerting

        # Initialize service health tracking
        self._init_service_health()

    def _init_service_health(self) -> None:
        """Initialize health tracking for all services."""
        services = ["database", "redis", "smtp"]
        for service in services:
            self._services[service] = ServiceHealth(
                service=service, current_status=HealthStatus.UNKNOWN
            )

    async def check_database_health(self) -> HealthCheckResult:
        """
        Check database connectivity and performance.

        Returns:
            HealthCheckResult with database health status
        """
        start_time = time.time()

        try:
            db_manager = get_db_manager()

            # Test basic connectivity
            is_healthy = db_manager.health_check()

            response_time_ms = max(1, int((time.time() - start_time) * 1000))

            if is_healthy:
                logger.debug(
                    f"DB_HEALTH_CHECK: Database healthy, response time {response_time_ms}ms"
                )
                return HealthCheckResult(
                    service="database",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time_ms,
                    details={"connection_pool": "active"},
                )
            else:
                logger.warning("DB_HEALTH_CHECK: Database unhealthy")
                return HealthCheckResult(
                    service="database",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time_ms,
                    error="Database connectivity test failed",
                )

        except Exception as e:
            response_time_ms = max(1, int((time.time() - start_time) * 1000))
            error_msg = str(e)
            logger.error(
                f"DB_HEALTH_CHECK_ERROR: Database health check failed - {error_msg}"
            )

            return HealthCheckResult(
                service="database",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error=error_msg,
            )

    async def check_redis_health(self) -> HealthCheckResult:
        """
        Check Redis connectivity and performance.

        Returns:
            HealthCheckResult with Redis health status
        """
        start_time = time.time()

        try:
            redis_client = get_redis_client()

            # Test basic connectivity
            is_healthy = redis_client.health_check()

            response_time_ms = max(1, int((time.time() - start_time) * 1000))

            if is_healthy:
                logger.debug(
                    f"REDIS_HEALTH_CHECK: Redis healthy, response time {response_time_ms}ms"
                )
                return HealthCheckResult(
                    service="redis",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time_ms,
                    details={"connection_pool": "active"},
                )
            else:
                logger.warning("REDIS_HEALTH_CHECK: Redis unhealthy")
                return HealthCheckResult(
                    service="redis",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time_ms,
                    error="Redis connectivity test failed",
                )

        except Exception as e:
            response_time_ms = max(1, int((time.time() - start_time) * 1000))
            error_msg = str(e)
            logger.error(
                f"REDIS_HEALTH_CHECK_ERROR: Redis health check failed - {error_msg}"
            )

            return HealthCheckResult(
                service="redis",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error=error_msg,
            )

    async def check_smtp_health(self) -> HealthCheckResult:
        """
        Check SMTP server connectivity and authentication.

        Returns:
            HealthCheckResult with SMTP health status
        """
        start_time = time.time()

        try:
            # Import here to avoid circular imports
            from telegram_bot.services.email_service import EmailService

            email_service = EmailService(self.config)

            # Test SMTP connectivity (this will use the existing health check in EmailService)
            is_healthy = await email_service._check_smtp_health()

            response_time_ms = max(1, int((time.time() - start_time) * 1000))

            if is_healthy:
                logger.debug(
                    f"SMTP_HEALTH_CHECK: SMTP healthy, response time {response_time_ms}ms"
                )
                return HealthCheckResult(
                    service="smtp",
                    status=HealthStatus.HEALTHY,
                    response_time_ms=response_time_ms,
                    details={
                        "host": self.config.smtp_host,
                        "port": self.config.smtp_port,
                        "tls": self.config.smtp_use_tls,
                        "ssl": self.config.smtp_use_ssl,
                    },
                )
            else:
                logger.warning("SMTP_HEALTH_CHECK: SMTP unhealthy")
                return HealthCheckResult(
                    service="smtp",
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=response_time_ms,
                    error="SMTP connectivity test failed",
                )

        except Exception as e:
            response_time_ms = max(1, int((time.time() - start_time) * 1000))
            error_msg = str(e)
            logger.error(
                f"SMTP_HEALTH_CHECK_ERROR: SMTP health check failed - {error_msg}"
            )

            return HealthCheckResult(
                service="smtp",
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                error=error_msg,
            )

    async def check_all_services(self) -> Dict[str, HealthCheckResult]:
        """
        Check health of all services.

        Returns:
            Dictionary mapping service names to health check results
        """
        results = {}

        # Run all health checks concurrently
        tasks = [
            ("database", self.check_database_health()),
            ("redis", self.check_redis_health()),
            ("smtp", self.check_smtp_health()),
        ]

        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = result
            except Exception as e:
                logger.error(
                    f"HEALTH_CHECK_ERROR: Failed to check {service_name} health - {str(e)}"
                )
                results[service_name] = HealthCheckResult(
                    service=service_name,
                    status=HealthStatus.UNHEALTHY,
                    error=f"Health check failed: {str(e)}",
                )

        return results

    def _update_service_health(self, result: HealthCheckResult) -> None:
        """Update service health tracking with new result."""
        service = self._services.get(result.service)
        if not service:
            return

        service.total_checks += 1

        # Update status and timestamps
        old_status = service.current_status
        service.current_status = result.status

        if result.status == HealthStatus.HEALTHY:
            service.last_healthy = result.timestamp
            service.consecutive_failures = 0

            # Update average response time
            if result.response_time_ms is not None:
                if service.average_response_time_ms is None:
                    service.average_response_time_ms = float(result.response_time_ms)
                else:
                    # Simple moving average
                    service.average_response_time_ms = (
                        service.average_response_time_ms * 0.8
                        + result.response_time_ms * 0.2
                    )
        else:
            service.last_unhealthy = result.timestamp
            service.consecutive_failures += 1
            service.total_failures += 1

        # Log status changes
        if old_status != result.status:
            if result.status == HealthStatus.HEALTHY:
                logger.info(f"HEALTH_RECOVERED: {result.service} is now healthy")
            else:
                logger.warning(
                    f"HEALTH_DEGRADED: {result.service} is now unhealthy - {result.error}"
                )

        # Alert on consecutive failures
        if service.consecutive_failures >= self._failure_threshold:
            logger.error(
                f"HEALTH_ALERT: {result.service} has failed {service.consecutive_failures} consecutive times"
            )

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        logger.info("HEALTH_MONITOR_START: Health monitoring started")

        while self._monitoring_running:
            try:
                # Check all services
                results = await self.check_all_services()

                # Update service health tracking
                for result in results.values():
                    self._update_service_health(result)

                # Log summary
                healthy_count = sum(
                    1 for r in results.values() if r.status == HealthStatus.HEALTHY
                )
                total_count = len(results)

                if healthy_count == total_count:
                    logger.debug(f"HEALTH_SUMMARY: All {total_count} services healthy")
                else:
                    unhealthy_services = [
                        r.service
                        for r in results.values()
                        if r.status != HealthStatus.HEALTHY
                    ]
                    logger.warning(
                        f"HEALTH_SUMMARY: {healthy_count}/{total_count} services healthy. "
                        f"Unhealthy: {', '.join(unhealthy_services)}"
                    )

                # Wait for next check
                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"HEALTH_MONITOR_ERROR: Monitoring loop error - {str(e)}")
                await asyncio.sleep(self._check_interval)

        logger.info("HEALTH_MONITOR_STOP: Health monitoring stopped")

    async def start_monitoring(self, check_interval: int = 30) -> None:
        """
        Start periodic health monitoring.

        Args:
            check_interval: Interval between health checks in seconds
        """
        if self._monitoring_running:
            logger.warning(
                "HEALTH_MONITOR_ALREADY_RUNNING: Health monitoring is already running"
            )
            return

        self._check_interval = check_interval
        self._monitoring_running = True
        self._monitoring_task = asyncio.create_task(self._monitoring_loop())

        logger.info(
            f"HEALTH_MONITOR_STARTED: Monitoring started with {check_interval}s interval"
        )

    async def stop_monitoring(self) -> None:
        """Stop periodic health monitoring."""
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

        logger.info("HEALTH_MONITOR_STOPPED: Health monitoring stopped")

    def get_service_health(self, service: str) -> Optional[ServiceHealth]:
        """
        Get health information for a specific service.

        Args:
            service: Service name (database, redis, smtp)

        Returns:
            ServiceHealth object or None if service not found
        """
        return self._services.get(service)

    def get_all_service_health(self) -> Dict[str, ServiceHealth]:
        """
        Get health information for all services.

        Returns:
            Dictionary mapping service names to ServiceHealth objects
        """
        return self._services.copy()

    def is_service_healthy(self, service: str) -> bool:
        """
        Check if a specific service is currently healthy.

        Args:
            service: Service name (database, redis, smtp)

        Returns:
            True if service is healthy, False otherwise
        """
        service_health = self._services.get(service)
        return (
            service_health.current_status == HealthStatus.HEALTHY
            if service_health
            else False
        )

    def are_all_services_healthy(self) -> bool:
        """
        Check if all services are currently healthy.

        Returns:
            True if all services are healthy, False otherwise
        """
        return all(
            service.current_status == HealthStatus.HEALTHY
            for service in self._services.values()
        )

    def get_health_summary(self) -> Dict:
        """
        Get comprehensive health summary for all services.

        Returns:
            Dictionary with health summary information
        """
        healthy_services = []
        unhealthy_services = []
        unknown_services = []

        for service in self._services.values():
            if service.current_status == HealthStatus.HEALTHY:
                healthy_services.append(service.service)
            elif service.current_status == HealthStatus.UNHEALTHY:
                unhealthy_services.append(service.service)
            else:
                unknown_services.append(service.service)

        return {
            "overall_healthy": len(unhealthy_services) == 0,
            "healthy_services": healthy_services,
            "unhealthy_services": unhealthy_services,
            "unknown_services": unknown_services,
            "total_services": len(self._services),
            "healthy_count": len(healthy_services),
            "unhealthy_count": len(unhealthy_services),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


# Global health monitor instance
health_monitor: Optional[HealthMonitor] = None


def init_health_monitor(config: BotConfig) -> HealthMonitor:
    """
    Initialize global health monitor.

    Args:
        config: BotConfig instance with health monitoring settings

    Returns:
        HealthMonitor instance
    """
    global health_monitor
    health_monitor = HealthMonitor(config)
    return health_monitor


def get_health_monitor() -> HealthMonitor:
    """
    Get the global health monitor instance.

    Returns:
        HealthMonitor instance

    Raises:
        RuntimeError: If health monitor is not initialized
    """
    if health_monitor is None:
        raise RuntimeError(
            "Health monitor not initialized. Call init_health_monitor() first."
        )
    return health_monitor
