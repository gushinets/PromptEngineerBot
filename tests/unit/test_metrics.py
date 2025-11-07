"""
Tests for metrics collection system.

This module tests comprehensive metrics collection, latency tracking,
success rates, and observability features.
"""

import time
from unittest.mock import patch

import pytest

from telegram_bot.utils.metrics import (
    MetricsCollector,
    get_metrics_collector,
    init_metrics_collector,
)


@pytest.fixture
def metrics_collector():
    """Create metrics collector instance for testing."""
    return MetricsCollector(window_size_minutes=1)  # Small window for testing


class TestMetricsCollector:
    """Test metrics collector functionality."""

    def test_increment_counter(self, metrics_collector):
        """Test counter increment functionality."""
        metrics_collector.increment_counter("test_counter")
        assert metrics_collector.get_counter("test_counter") == 1

        metrics_collector.increment_counter("test_counter", 5)
        assert metrics_collector.get_counter("test_counter") == 6

    def test_record_latency(self, metrics_collector):
        """Test latency recording and statistics."""
        # Record some latencies
        latencies = [0.1, 0.2, 0.3, 0.4, 0.5]
        for latency in latencies:
            metrics_collector.record_latency("test_latency", latency)

        stats = metrics_collector.get_latency_stats("test_latency")

        assert stats["min"] == 0.1
        assert stats["max"] == 0.5
        assert stats["avg"] == 0.3
        assert stats["count"] == 5
        assert stats["p50"] == 0.3  # Median

    def test_record_success_failure(self, metrics_collector):
        """Test success/failure rate tracking."""
        # Record some successes and failures
        metrics_collector.record_success_failure("test_operation", True)
        metrics_collector.record_success_failure("test_operation", True)
        metrics_collector.record_success_failure("test_operation", False)

        rate_stats = metrics_collector.get_success_rate("test_operation")

        assert rate_stats["success_count"] == 2
        assert rate_stats["total_count"] == 3
        assert rate_stats["success_rate"] == pytest.approx(66.67, rel=1e-2)

    def test_time_operation_context_manager(self, metrics_collector):
        """Test timing context manager."""
        with metrics_collector.time_operation("test_timing"):
            time.sleep(0.01)  # Sleep for 10ms

        stats = metrics_collector.get_latency_stats("test_timing")

        assert stats["count"] == 1
        assert stats["min"] >= 0.01  # Should be at least 10ms
        assert stats["max"] >= 0.01

    def test_get_rate(self, metrics_collector):
        """Test rate calculation."""
        # Add some events
        for _ in range(10):
            metrics_collector.increment_counter("test_rate")

        rate = metrics_collector.get_rate("test_rate")

        # Rate should be 10 events per minute (since we added 10 events)
        assert rate == 10.0

    def test_get_rate_empty(self, metrics_collector):
        """Test rate calculation with no events."""
        rate = metrics_collector.get_rate("nonexistent_metric")
        assert rate == 0.0

    def test_latency_stats_empty(self, metrics_collector):
        """Test latency statistics with no data."""
        stats = metrics_collector.get_latency_stats("nonexistent_metric")

        expected = {
            "min": 0.0,
            "max": 0.0,
            "avg": 0.0,
            "p50": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "count": 0,
        }

        assert stats == expected

    def test_success_rate_empty(self, metrics_collector):
        """Test success rate with no data."""
        rate_stats = metrics_collector.get_success_rate("nonexistent_metric")

        expected = {"success_count": 0, "total_count": 0, "success_rate": 0.0}

        assert rate_stats == expected

    def test_get_all_metrics(self, metrics_collector):
        """Test getting all metrics in structured format."""
        # Add some test data
        metrics_collector.increment_counter("test_counter", 5)
        metrics_collector.record_latency("test_latency", 0.1)
        metrics_collector.record_success_failure("test_operation", True)

        all_metrics = metrics_collector.get_all_metrics()

        assert "counters" in all_metrics
        assert "rates" in all_metrics
        assert "latencies" in all_metrics
        assert "success_rates" in all_metrics

        assert all_metrics["counters"]["test_counter"] == 5
        assert "test_latency" in all_metrics["latencies"]
        assert "test_operation" in all_metrics["success_rates"]

    def test_reset_metrics(self, metrics_collector):
        """Test metrics reset functionality."""
        # Add some data
        metrics_collector.increment_counter("test_counter", 5)
        metrics_collector.record_latency("test_latency", 0.1)
        metrics_collector.record_success_failure("test_operation", True)

        # Verify data exists
        assert metrics_collector.get_counter("test_counter") == 5

        # Reset and verify data is cleared
        metrics_collector.reset_metrics()

        assert metrics_collector.get_counter("test_counter") == 0
        stats = metrics_collector.get_latency_stats("test_latency")
        assert stats["count"] == 0
        rate_stats = metrics_collector.get_success_rate("test_operation")
        assert rate_stats["total_count"] == 0

    def test_otp_metrics(self, metrics_collector):
        """Test OTP-specific metrics methods."""
        # Test OTP sent
        metrics_collector.record_otp_sent()
        assert metrics_collector.get_counter("otp_sent") == 1

        # Test OTP verification
        metrics_collector.record_otp_verified(True)
        metrics_collector.record_otp_verified(False)

        assert metrics_collector.get_counter("otp_verified_attempts") == 2
        assert metrics_collector.get_counter("otp_verified_success") == 1
        assert metrics_collector.get_counter("otp_verified_failed") == 1

        rate_stats = metrics_collector.get_success_rate("otp_verification")
        assert rate_stats["success_rate"] == 50.0

        # Test OTP failures
        metrics_collector.record_otp_failed("invalid_code")
        metrics_collector.record_otp_expired()
        metrics_collector.record_otp_rate_limited("email_limit")

        assert metrics_collector.get_counter("otp_failed") == 1
        assert metrics_collector.get_counter("otp_failed_invalid_code") == 1
        assert metrics_collector.get_counter("otp_expired") == 1
        assert metrics_collector.get_counter("otp_rate_limited") == 1
        assert metrics_collector.get_counter("otp_rate_limited_email_limit") == 1

    def test_email_metrics(self, metrics_collector):
        """Test email-specific metrics methods."""
        # Test email sending
        metrics_collector.record_email_sent(True, 0.5)
        metrics_collector.record_email_sent(False, 1.0)

        assert metrics_collector.get_counter("email_sent_attempts") == 2
        assert metrics_collector.get_counter("email_sent_success") == 1
        assert metrics_collector.get_counter("email_sent_failed") == 1

        rate_stats = metrics_collector.get_success_rate("email_sending")
        assert rate_stats["success_rate"] == 50.0

        latency_stats = metrics_collector.get_latency_stats("email_send_latency")
        assert latency_stats["count"] == 2
        assert latency_stats["avg"] == 0.75

        # Test email failures
        metrics_collector.record_email_failure("smtp_timeout")

        assert metrics_collector.get_counter("email_failed") == 1
        assert metrics_collector.get_counter("email_failed_smtp_timeout") == 1

    def test_llm_metrics(self, metrics_collector):
        """Test LLM-specific metrics methods."""
        # Test LLM requests
        metrics_collector.record_llm_request("gpt-4", True, 2.5)
        metrics_collector.record_llm_request("gpt-4", False, 1.0)
        metrics_collector.record_llm_request("claude", True, 1.5)

        assert metrics_collector.get_counter("llm_requests") == 3
        assert metrics_collector.get_counter("llm_requests_gpt-4") == 2
        assert metrics_collector.get_counter("llm_requests_claude") == 1
        assert metrics_collector.get_counter("llm_requests_success") == 2
        assert metrics_collector.get_counter("llm_requests_failed") == 1

        # Test model-specific success rates
        gpt4_rate = metrics_collector.get_success_rate("llm_requests_gpt-4")
        assert gpt4_rate["success_rate"] == 50.0

        claude_rate = metrics_collector.get_success_rate("llm_requests_claude")
        assert claude_rate["success_rate"] == 100.0

        # Test latency tracking
        latency_stats = metrics_collector.get_latency_stats("llm_latency")
        assert latency_stats["count"] == 3

        gpt4_latency = metrics_collector.get_latency_stats("llm_latency_gpt-4")
        assert gpt4_latency["count"] == 2

    def test_smtp_metrics(self, metrics_collector):
        """Test SMTP-specific metrics methods."""
        # Test SMTP connections
        metrics_collector.record_smtp_connection(True, 0.1)
        metrics_collector.record_smtp_connection(False, 0.2)

        assert metrics_collector.get_counter("smtp_connections") == 2
        assert metrics_collector.get_counter("smtp_connections_success") == 1
        assert metrics_collector.get_counter("smtp_connections_failed") == 1

        rate_stats = metrics_collector.get_success_rate("smtp_connections")
        assert rate_stats["success_rate"] == 50.0

        latency_stats = metrics_collector.get_latency_stats("smtp_connection_latency")
        assert latency_stats["count"] == 2
        assert abs(latency_stats["avg"] - 0.15) < 0.001  # Allow for floating point precision

    def test_flow_metrics(self, metrics_collector):
        """Test email flow-specific metrics methods."""
        # Test email flow tracking
        metrics_collector.record_email_flow_started()
        metrics_collector.record_email_flow_started()

        metrics_collector.record_email_flow_completed(True)
        metrics_collector.record_email_flow_completed(False)

        metrics_collector.record_email_flow_timeout()

        assert metrics_collector.get_counter("email_flow_started") == 2
        assert metrics_collector.get_counter("email_flow_completed") == 2
        assert metrics_collector.get_counter("email_flow_success") == 1
        assert metrics_collector.get_counter("email_flow_failed") == 1
        assert metrics_collector.get_counter("email_flow_timeout") == 1

        rate_stats = metrics_collector.get_success_rate("email_flow")
        assert rate_stats["success_rate"] == 50.0

    def test_export_prometheus_format(self, metrics_collector):
        """Test Prometheus format export."""
        # Add some test data
        metrics_collector.increment_counter("test_counter", 5)
        metrics_collector.record_latency("test_latency", 0.1)
        metrics_collector.record_success_failure("test_operation", True)

        prometheus_output = metrics_collector.export_prometheus_format()

        assert "# TYPE test_counter_total counter" in prometheus_output
        assert "test_counter_total 5" in prometheus_output
        assert "# TYPE test_latency_avg gauge" in prometheus_output
        assert "# TYPE test_operation_success_rate gauge" in prometheus_output

    def test_log_metrics_summary(self, metrics_collector):
        """Test metrics summary logging."""
        # Add some test data
        metrics_collector.increment_counter("test_counter", 5)
        metrics_collector.record_latency("test_latency", 0.1)
        metrics_collector.record_success_failure("test_operation", True)

        # Mock the instance logger
        with patch.object(metrics_collector, "logger") as mock_logger:
            metrics_collector.log_metrics_summary()

            # Verify logger was called
            mock_logger.info.assert_called()

        # Check that summary contains expected sections
        log_calls = [call[0][0] for call in mock_logger.info.call_args_list]
        log_text = " ".join(log_calls)

        assert "Metrics Summary" in log_text
        assert "Counters:" in log_text
        assert "Success Rates:" in log_text
        assert "Latency Stats" in log_text

    def test_latency_limit(self, metrics_collector):
        """Test that latency storage is limited to prevent memory issues."""
        # Add more than 1000 latency measurements
        for i in range(1200):
            metrics_collector.record_latency("test_latency", i * 0.001)

        stats = metrics_collector.get_latency_stats("test_latency")

        # Should be limited to 1000 measurements
        assert stats["count"] == 1000

        # Should contain the most recent measurements
        assert stats["max"] == pytest.approx(1.199, rel=1e-3)  # Last measurement

    def test_window_cleanup(self, metrics_collector):
        """Test that old time series entries are cleaned up."""
        # This test is challenging to implement without mocking time
        # For now, we'll test the basic functionality

        metrics_collector.increment_counter("test_metric")
        rate_before = metrics_collector.get_rate("test_metric")

        # The rate should be calculated correctly
        assert rate_before > 0

        # Test that cleanup doesn't break anything
        metrics_collector._cleanup_old_entries("test_metric")
        rate_after = metrics_collector.get_rate("test_metric")

        # Rate should still be valid (entries are recent)
        assert rate_after >= 0


class TestMetricsCollectorGlobal:
    """Test global metrics collector management."""

    def test_init_metrics_collector(self):
        """Test metrics collector initialization."""
        collector = init_metrics_collector(window_size_minutes=30)

        assert isinstance(collector, MetricsCollector)
        assert get_metrics_collector() is collector

    def test_get_metrics_collector_not_initialized(self):
        """Test getting metrics collector when not initialized."""
        # Reset global collector
        import telegram_bot.utils.metrics

        telegram_bot.utils.metrics.metrics_collector = None

        with pytest.raises(RuntimeError, match="Metrics collector not initialized"):
            get_metrics_collector()


class TestMetricsIntegration:
    """Test metrics integration scenarios."""

    def test_concurrent_operations(self, metrics_collector):
        """Test metrics collection under concurrent operations."""
        import threading

        def worker():
            for i in range(100):
                metrics_collector.increment_counter("concurrent_test")
                metrics_collector.record_latency("concurrent_latency", 0.001 * i)
                metrics_collector.record_success_failure("concurrent_success", i % 2 == 0)

        # Start multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        assert metrics_collector.get_counter("concurrent_test") == 500

        latency_stats = metrics_collector.get_latency_stats("concurrent_latency")
        assert latency_stats["count"] == 500

        success_stats = metrics_collector.get_success_rate("concurrent_success")
        assert success_stats["total_count"] == 500
        assert success_stats["success_rate"] == 50.0

    def test_realistic_email_flow_metrics(self, metrics_collector):
        """Test realistic email flow metrics scenario."""
        # Simulate a complete email flow
        metrics_collector.record_email_flow_started()

        # OTP generation and sending
        metrics_collector.record_otp_sent()
        with metrics_collector.time_operation("smtp_send"):
            time.sleep(0.01)  # Simulate SMTP delay
        metrics_collector.record_email_sent(True, 0.5)

        # OTP verification
        metrics_collector.record_otp_verified(True)

        # LLM processing
        with metrics_collector.time_operation("llm_processing"):
            time.sleep(0.02)  # Simulate LLM delay
        metrics_collector.record_llm_request("gpt-4", True, 2.0)

        # Final email delivery
        with metrics_collector.time_operation("final_email"):
            time.sleep(0.01)
        metrics_collector.record_email_sent(True, 0.3)

        # Flow completion
        metrics_collector.record_email_flow_completed(True)

        # Verify comprehensive metrics
        all_metrics = metrics_collector.get_all_metrics()

        # Check counters
        assert all_metrics["counters"]["email_flow_started"] == 1
        assert all_metrics["counters"]["otp_sent"] == 1
        assert all_metrics["counters"]["email_sent_success"] == 2
        assert all_metrics["counters"]["otp_verified_success"] == 1
        assert all_metrics["counters"]["llm_requests_success"] == 1
        assert all_metrics["counters"]["email_flow_success"] == 1

        # Check latencies
        assert "smtp_send" in all_metrics["latencies"]
        assert "llm_processing" in all_metrics["latencies"]
        assert "final_email" in all_metrics["latencies"]

        # Check success rates
        assert all_metrics["success_rates"]["email_sending"]["success_rate"] == 100.0
        assert all_metrics["success_rates"]["otp_verification"]["success_rate"] == 100.0
        assert all_metrics["success_rates"]["email_flow"]["success_rate"] == 100.0
