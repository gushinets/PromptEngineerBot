"""
Metrics collection system for monitoring and observability.

This module provides comprehensive metrics collection for OTP operations,
email delivery, and system performance monitoring with latency tracking.
"""

import logging
import time
from collections import defaultdict, deque
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Comprehensive metrics collection system for monitoring and observability."""

    def __init__(self, window_size_minutes: int = 60):
        """
        Initialize metrics collector.

        Args:
            window_size_minutes: Size of the sliding window for rate calculations
        """
        self.window_size = timedelta(minutes=window_size_minutes)
        self._lock = Lock()

        # Counter metrics (cumulative)
        self._counters: Dict[str, int] = defaultdict(int)

        # Time-series metrics (sliding window)
        self._time_series: Dict[str, deque] = defaultdict(lambda: deque())

        # Latency metrics (histogram-like storage)
        self._latencies: Dict[str, List[float]] = defaultdict(list)

        # Success/failure rates
        self._success_rates: Dict[str, Tuple[int, int]] = defaultdict(
            lambda: (0, 0)
        )  # (success, total)

        self.logger = logging.getLogger(f"{__name__}.MetricsCollector")

    def _cleanup_old_entries(self, metric_name: str):
        """Remove entries older than the window size."""
        cutoff_time = datetime.now(timezone.utc) - self.window_size
        time_series = self._time_series[metric_name]

        while time_series and time_series[0][0] < cutoff_time:
            time_series.popleft()

    def increment_counter(self, metric_name: str, value: int = 1):
        """
        Increment a counter metric.

        Args:
            metric_name: Name of the metric
            value: Value to increment by (default: 1)
        """
        with self._lock:
            self._counters[metric_name] += value

            # Also add to time series for rate calculations
            timestamp = datetime.now(timezone.utc)
            self._time_series[metric_name].append((timestamp, value))
            self._cleanup_old_entries(metric_name)

    def record_latency(self, metric_name: str, latency_seconds: float):
        """
        Record a latency measurement.

        Args:
            metric_name: Name of the latency metric
            latency_seconds: Latency in seconds
        """
        with self._lock:
            self._latencies[metric_name].append(latency_seconds)

            # Keep only recent latencies (last 1000 measurements)
            if len(self._latencies[metric_name]) > 1000:
                self._latencies[metric_name] = self._latencies[metric_name][-1000:]

    def record_success_failure(self, metric_name: str, success: bool):
        """
        Record a success or failure for rate calculations.

        Args:
            metric_name: Name of the metric
            success: Whether the operation was successful
        """
        with self._lock:
            current_success, current_total = self._success_rates[metric_name]
            if success:
                self._success_rates[metric_name] = (
                    current_success + 1,
                    current_total + 1,
                )
            else:
                self._success_rates[metric_name] = (current_success, current_total + 1)

    @contextmanager
    def time_operation(self, metric_name: str):
        """
        Context manager to time an operation and record latency.

        Args:
            metric_name: Name of the latency metric

        Usage:
            with metrics.time_operation("smtp_send"):
                send_email()
        """
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            latency = end_time - start_time
            self.record_latency(metric_name, latency)

    def get_counter(self, metric_name: str) -> int:
        """Get current counter value."""
        with self._lock:
            return self._counters[metric_name]

    def get_rate(self, metric_name: str) -> float:
        """
        Get rate per minute for a metric within the sliding window.

        Args:
            metric_name: Name of the metric

        Returns:
            Rate per minute
        """
        with self._lock:
            return self._get_rate_unlocked(metric_name)

    def get_latency_stats(self, metric_name: str) -> Dict[str, float]:
        """
        Get latency statistics for a metric.

        Args:
            metric_name: Name of the latency metric

        Returns:
            Dictionary with min, max, avg, p50, p95, p99 latencies
        """
        with self._lock:
            return self._get_latency_stats_unlocked(metric_name)

    def get_success_rate(self, metric_name: str) -> Dict[str, float]:
        """
        Get success rate for a metric.

        Args:
            metric_name: Name of the metric

        Returns:
            Dictionary with success_count, total_count, success_rate
        """
        with self._lock:
            return self._get_success_rate_unlocked(metric_name)

    def _get_rate_unlocked(self, metric_name: str) -> float:
        """Get rate per minute for a metric (assumes lock is already held)."""
        self._cleanup_old_entries(metric_name)
        time_series = self._time_series[metric_name]

        if not time_series:
            return 0.0

        total_value = sum(value for _, value in time_series)
        window_minutes = self.window_size.total_seconds() / 60

        return total_value / window_minutes if window_minutes > 0 else 0.0

    def _get_latency_stats_unlocked(self, metric_name: str) -> Dict[str, float]:
        """Get latency statistics for a metric (assumes lock is already held)."""
        latencies = self._latencies[metric_name]

        if not latencies:
            return {
                "min": 0.0,
                "max": 0.0,
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
                "count": 0,
            }

        sorted_latencies = sorted(latencies)
        count = len(sorted_latencies)

        return {
            "min": sorted_latencies[0],
            "max": sorted_latencies[-1],
            "avg": sum(sorted_latencies) / count,
            "p50": sorted_latencies[int(count * 0.5)],
            "p95": sorted_latencies[int(count * 0.95)],
            "p99": sorted_latencies[int(count * 0.99)],
            "count": count,
        }

    def _get_success_rate_unlocked(self, metric_name: str) -> Dict[str, float]:
        """Get success rate for a metric (assumes lock is already held)."""
        success_count, total_count = self._success_rates[metric_name]

        success_rate = (success_count / total_count * 100) if total_count > 0 else 0.0

        return {
            "success_count": success_count,
            "total_count": total_count,
            "success_rate": success_rate,
        }

    def get_all_metrics(self) -> Dict[str, any]:
        """
        Get all metrics in a structured format.

        Returns:
            Dictionary containing all metrics
        """
        with self._lock:
            metrics = {
                "counters": dict(self._counters),
                "rates": {},
                "latencies": {},
                "success_rates": {},
            }

            # Calculate rates for all time series metrics
            for metric_name in self._time_series.keys():
                metrics["rates"][metric_name] = self._get_rate_unlocked(metric_name)

            # Get latency stats for all latency metrics
            for metric_name in self._latencies.keys():
                metrics["latencies"][metric_name] = self._get_latency_stats_unlocked(
                    metric_name
                )

            # Get success rates for all success/failure metrics
            for metric_name in self._success_rates.keys():
                metrics["success_rates"][metric_name] = self._get_success_rate_unlocked(
                    metric_name
                )

            return metrics

    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self._counters.clear()
            self._time_series.clear()
            self._latencies.clear()
            self._success_rates.clear()

    # OTP-specific metrics methods
    def record_otp_sent(self):
        """Record an OTP sent event."""
        self.increment_counter("otp_sent")

    def record_otp_verified(self, success: bool):
        """Record an OTP verification attempt."""
        self.increment_counter("otp_verified_attempts")
        if success:
            self.increment_counter("otp_verified_success")
        else:
            self.increment_counter("otp_verified_failed")

        self.record_success_failure("otp_verification", success)

    def record_otp_failed(self, reason: str):
        """Record an OTP failure with reason."""
        self.increment_counter("otp_failed")
        self.increment_counter(f"otp_failed_{reason}")

    def record_otp_expired(self):
        """Record an OTP expiration."""
        self.increment_counter("otp_expired")

    def record_otp_rate_limited(self, reason: str):
        """Record an OTP rate limiting event."""
        self.increment_counter("otp_rate_limited")
        self.increment_counter(f"otp_rate_limited_{reason}")

    # Email-specific metrics methods
    def record_email_sent(self, success: bool, latency_seconds: Optional[float] = None):
        """Record an email sending attempt."""
        self.increment_counter("email_sent_attempts")
        if success:
            self.increment_counter("email_sent_success")
        else:
            self.increment_counter("email_sent_failed")

        self.record_success_failure("email_sending", success)

        if latency_seconds is not None:
            self.record_latency("email_send_latency", latency_seconds)

    def record_email_failure(self, reason: str):
        """Record an email failure with reason."""
        self.increment_counter("email_failed")
        self.increment_counter(f"email_failed_{reason}")

    # LLM-specific metrics methods
    def record_llm_request(
        self, model: str, success: bool, latency_seconds: Optional[float] = None
    ):
        """Record an LLM request."""
        self.increment_counter("llm_requests")
        self.increment_counter(f"llm_requests_{model}")

        if success:
            self.increment_counter("llm_requests_success")
            self.increment_counter(f"llm_requests_success_{model}")
        else:
            self.increment_counter("llm_requests_failed")
            self.increment_counter(f"llm_requests_failed_{model}")

        self.record_success_failure("llm_requests", success)
        self.record_success_failure(f"llm_requests_{model}", success)

        if latency_seconds is not None:
            self.record_latency("llm_latency", latency_seconds)
            self.record_latency(f"llm_latency_{model}", latency_seconds)

    # SMTP-specific metrics methods
    def record_smtp_connection(
        self, success: bool, latency_seconds: Optional[float] = None
    ):
        """Record an SMTP connection attempt."""
        self.increment_counter("smtp_connections")
        if success:
            self.increment_counter("smtp_connections_success")
        else:
            self.increment_counter("smtp_connections_failed")

        self.record_success_failure("smtp_connections", success)

        if latency_seconds is not None:
            self.record_latency("smtp_connection_latency", latency_seconds)

    # Flow-specific metrics methods
    def record_email_flow_started(self):
        """Record an email flow initiation."""
        self.increment_counter("email_flow_started")

    def record_email_flow_completed(self, success: bool):
        """Record an email flow completion."""
        self.increment_counter("email_flow_completed")
        if success:
            self.increment_counter("email_flow_success")
        else:
            self.increment_counter("email_flow_failed")

        self.record_success_failure("email_flow", success)

    def record_email_flow_timeout(self):
        """Record an email flow timeout."""
        self.increment_counter("email_flow_timeout")

    def export_prometheus_format(self) -> str:
        """
        Export metrics in Prometheus format.

        Returns:
            String containing metrics in Prometheus format
        """
        lines = []
        timestamp = int(time.time() * 1000)  # Prometheus expects milliseconds

        # Export counters
        for metric_name, value in self._counters.items():
            lines.append(f"# TYPE {metric_name}_total counter")
            lines.append(f"{metric_name}_total {value} {timestamp}")

        # Export rates
        for metric_name in self._time_series.keys():
            rate = self.get_rate(metric_name)
            lines.append(f"# TYPE {metric_name}_rate gauge")
            lines.append(f"{metric_name}_rate {rate:.2f} {timestamp}")

        # Export latency percentiles
        for metric_name in self._latencies.keys():
            stats = self.get_latency_stats(metric_name)
            for stat_name, value in stats.items():
                if stat_name != "count":
                    lines.append(f"# TYPE {metric_name}_{stat_name} gauge")
                    lines.append(f"{metric_name}_{stat_name} {value:.4f} {timestamp}")

        # Export success rates
        for metric_name in self._success_rates.keys():
            rate_stats = self.get_success_rate(metric_name)
            lines.append(f"# TYPE {metric_name}_success_rate gauge")
            lines.append(
                f"{metric_name}_success_rate {rate_stats['success_rate']:.2f} {timestamp}"
            )

        return "\n".join(lines)

    def log_metrics_summary(self):
        """Log a summary of current metrics."""
        metrics = self.get_all_metrics()

        self.logger.info("=== Metrics Summary ===")

        # Log counters
        if metrics["counters"]:
            self.logger.info("Counters:")
            for name, value in metrics["counters"].items():
                self.logger.info(f"  {name}: {value}")

        # Log rates
        if metrics["rates"]:
            self.logger.info("Rates (per minute):")
            for name, rate in metrics["rates"].items():
                self.logger.info(f"  {name}: {rate:.2f}")

        # Log success rates
        if metrics["success_rates"]:
            self.logger.info("Success Rates:")
            for name, stats in metrics["success_rates"].items():
                self.logger.info(
                    f"  {name}: {stats['success_rate']:.1f}% "
                    f"({stats['success_count']}/{stats['total_count']})"
                )

        # Log latency stats
        if metrics["latencies"]:
            self.logger.info("Latency Stats (seconds):")
            for name, stats in metrics["latencies"].items():
                self.logger.info(
                    f"  {name}: avg={stats['avg']:.3f}s, "
                    f"p50={stats['p50']:.3f}s, p95={stats['p95']:.3f}s, "
                    f"p99={stats['p99']:.3f}s (n={stats['count']})"
                )


# Global metrics collector instance
metrics_collector: Optional[MetricsCollector] = None


def init_metrics_collector(window_size_minutes: int = 60) -> MetricsCollector:
    """
    Initialize global metrics collector.

    Args:
        window_size_minutes: Size of the sliding window for rate calculations

    Returns:
        MetricsCollector instance
    """
    global metrics_collector
    metrics_collector = MetricsCollector(window_size_minutes)
    return metrics_collector


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.

    Returns:
        MetricsCollector instance

    Raises:
        RuntimeError: If metrics collector is not initialized
    """
    if metrics_collector is None:
        raise RuntimeError(
            "Metrics collector not initialized. Call init_metrics_collector() first."
        )
    return metrics_collector


def cleanup_metrics_collector():
    """
    Clean up the global metrics collector instance.

    This should be called when shutting down the application or in tests
    to ensure proper cleanup of resources.
    """
    global metrics_collector
    metrics_collector = None
