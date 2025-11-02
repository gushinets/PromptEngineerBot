#!/usr/bin/env python3
"""
Standalone test for metrics collection system.
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.metrics import (
    MetricsCollector,
    cleanup_metrics_collector,
    init_metrics_collector,
)


def test_metrics_system():
    """Test metrics collection system functionality."""
    print("Testing metrics collection system...")

    # Initialize metrics collector
    metrics = init_metrics_collector(window_size_minutes=1)
    print("✓ Metrics collector initialized")

    # Test counter metrics
    metrics.increment_counter("test_counter", 5)
    assert metrics.get_counter("test_counter") == 5
    print("✓ Counter metrics working")

    # Test latency metrics
    metrics.record_latency("test_latency", 0.1)
    metrics.record_latency("test_latency", 0.2)
    metrics.record_latency("test_latency", 0.3)

    latency_stats = metrics.get_latency_stats("test_latency")
    assert latency_stats["count"] == 3
    assert abs(latency_stats["avg"] - 0.2) < 0.001  # Allow for floating point precision
    print("✓ Latency metrics working")

    # Test success/failure rates
    metrics.record_success_failure("test_operation", True)
    metrics.record_success_failure("test_operation", True)
    metrics.record_success_failure("test_operation", False)

    success_stats = metrics.get_success_rate("test_operation")
    assert abs(success_stats["success_rate"] - 66.67) < 0.1  # 2/3 * 100
    print("✓ Success rate metrics working")

    # Test timing context manager
    with metrics.time_operation("test_timing"):
        time.sleep(0.01)  # 10ms

    timing_stats = metrics.get_latency_stats("test_timing")
    assert timing_stats["count"] == 1
    assert timing_stats["min"] >= 0.01
    print("✓ Timing context manager working")

    # Test OTP-specific metrics
    metrics.record_otp_sent()
    metrics.record_otp_verified(True)
    metrics.record_otp_verified(False)
    metrics.record_otp_failed("invalid_code")
    metrics.record_otp_expired()
    metrics.record_otp_rate_limited("email_limit")

    assert metrics.get_counter("otp_sent") == 1
    assert metrics.get_counter("otp_verified_success") == 1
    assert metrics.get_counter("otp_verified_failed") == 1
    assert metrics.get_counter("otp_failed_invalid_code") == 1
    assert metrics.get_counter("otp_expired") == 1
    assert metrics.get_counter("otp_rate_limited_email_limit") == 1
    print("✓ OTP metrics working")

    # Test email-specific metrics
    metrics.record_email_sent(True, 0.5)
    metrics.record_email_sent(False, 1.0)
    metrics.record_email_failure("smtp_timeout")

    assert metrics.get_counter("email_sent_success") == 1
    assert metrics.get_counter("email_sent_failed") == 1
    assert metrics.get_counter("email_failed_smtp_timeout") == 1

    email_latency = metrics.get_latency_stats("email_send_latency")
    assert email_latency["count"] == 2
    assert abs(email_latency["avg"] - 0.75) < 0.001
    print("✓ Email metrics working")

    # Test LLM-specific metrics
    metrics.record_llm_request("gpt-4", True, 2.5)
    metrics.record_llm_request("claude", False, 1.0)

    assert metrics.get_counter("llm_requests_gpt-4") == 1
    assert metrics.get_counter("llm_requests_claude") == 1
    assert metrics.get_counter("llm_requests_success") == 1
    assert metrics.get_counter("llm_requests_failed") == 1

    llm_latency = metrics.get_latency_stats("llm_latency")
    assert llm_latency["count"] == 2
    print("✓ LLM metrics working")

    # Test SMTP-specific metrics
    metrics.record_smtp_connection(True, 0.1)
    metrics.record_smtp_connection(False, 0.2)

    assert metrics.get_counter("smtp_connections_success") == 1
    assert metrics.get_counter("smtp_connections_failed") == 1

    smtp_success_rate = metrics.get_success_rate("smtp_connections")
    assert abs(smtp_success_rate["success_rate"] - 50.0) < 0.1
    print("✓ SMTP metrics working")

    # Test flow-specific metrics
    metrics.record_email_flow_started()
    metrics.record_email_flow_completed(True)
    metrics.record_email_flow_timeout()

    assert metrics.get_counter("email_flow_started") == 1
    assert metrics.get_counter("email_flow_success") == 1
    assert metrics.get_counter("email_flow_timeout") == 1
    print("✓ Flow metrics working")

    # Test comprehensive metrics export
    all_metrics = metrics.get_all_metrics()
    assert "counters" in all_metrics
    assert "rates" in all_metrics
    assert "latencies" in all_metrics
    assert "success_rates" in all_metrics
    print("✓ Comprehensive metrics export working")

    # Test Prometheus format export
    prometheus_output = metrics.export_prometheus_format()
    assert "# TYPE" in prometheus_output
    assert "_total" in prometheus_output
    assert "_rate" in prometheus_output
    print("✓ Prometheus format export working")

    # Test metrics summary logging
    metrics.log_metrics_summary()
    print("✓ Metrics summary logging working")

    # Test rate calculations
    rate = metrics.get_rate("test_counter")
    assert abs(rate - 5.0) < 0.1  # 5 events in 1 minute window
    print("✓ Rate calculations working")

    # Test metrics reset
    metrics.reset_metrics()
    assert metrics.get_counter("test_counter") == 0
    assert metrics.get_latency_stats("test_latency")["count"] == 0
    print("✓ Metrics reset working")

    print("All metrics tests passed!")

    # Clean up the global metrics collector
    cleanup_metrics_collector()
    print("✓ Metrics collector cleaned up")

    return True


if __name__ == "__main__":
    try:
        success = test_metrics_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        # Clean up even on failure
        cleanup_metrics_collector()
        sys.exit(1)
