#!/usr/bin/env python3
"""
Simple test script for logging utilities with PII protection.
This script tests the logging functionality independently.
"""

import logging
import os
import sys
from io import StringIO

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.logging_utils import (
    EmailFlowLogger,
    PIIProtectedFormatter,
    StructuredLogger,
    get_email_flow_logger,
    get_logger,
    setup_application_logging,
)


def test_pii_protected_formatter():
    """Test PII-protected formatter."""
    print("Testing PII-protected formatter...")

    formatter = PIIProtectedFormatter()

    # Test email masking
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="User email: user@example.com sent OTP 123456",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    assert "u***@e***.com" in formatted
    assert "user@example.com" not in formatted
    assert "***OTP***" in formatted
    assert "123456" not in formatted

    print("✓ Email and OTP masking works")

    # Test telegram ID masking
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Telegram ID: 123456789 requested access",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    assert "123***789" in formatted
    assert "123456789" not in formatted

    print("✓ Telegram ID masking works")

    # Test password masking
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Config: password=secret123 and token: abc456",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    assert "***MASKED***" in formatted
    assert "secret123" not in formatted
    assert "abc456" not in formatted

    print("✓ Password and token masking works")


def test_structured_logger():
    """Test structured logger."""
    print("Testing structured logger...")

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger = StructuredLogger("test_logger")
    logger.logger.handlers.clear()
    logger.logger.addHandler(handler)
    logger.logger.setLevel(logging.DEBUG)

    # Test context formatting with PII masking
    logger.info(
        "Test message",
        email="user@example.com",
        telegram_id=123456789,
        otp="654321",
        normal_field="value",
    )

    output = log_stream.getvalue()
    assert "Test message" in output
    assert "email=u***@e***.com" in output
    assert "telegram_id=123***789" in output
    assert "otp=***MASKED***" in output
    assert "normal_field=value" in output

    # Ensure original PII is not in output
    assert "user@example.com" not in output
    assert "123456789" not in output
    assert "654321" not in output

    print("✓ Structured logging with PII masking works")


def test_email_flow_logger():
    """Test email flow logger."""
    print("Testing email flow logger...")

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger = EmailFlowLogger()
    logger.logger.logger.handlers.clear()
    logger.logger.logger.addHandler(handler)
    logger.logger.logger.setLevel(logging.DEBUG)

    # Test various email flow logging methods
    logger.log_flow_start(123456789)
    logger.log_email_input(123456789, "user@example.com", True)
    logger.log_otp_generation(123456789)
    logger.log_otp_verification(123456789, 1, True)
    logger.log_email_sending(123456789, "user@example.com", True, delivery_time_ms=250)

    output = log_stream.getvalue()

    # Check that events are logged
    assert "EMAIL_FLOW_START" in output
    assert "EMAIL_INPUT" in output
    assert "EMAIL_VALIDATION" in output
    assert "OTP_GENERATED" in output
    assert "OTP_VERIFY_SUCCESS" in output
    assert "EMAIL_SEND_SUCCESS" in output

    # Check PII masking
    assert "123***789" in output
    assert "u***@e***.com" in output
    assert "123456789" not in output
    assert "user@example.com" not in output

    # Ensure no actual OTP values are logged
    assert "123456" not in output  # No actual OTP should appear

    print("✓ Email flow logging with PII protection works")


def test_rate_limiting_logging():
    """Test rate limiting logging."""
    print("Testing rate limiting logging...")

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger = EmailFlowLogger()
    logger.logger.logger.handlers.clear()
    logger.logger.logger.addHandler(handler)
    logger.logger.logger.setLevel(logging.DEBUG)

    # Test rate limiting logging
    logger.log_rate_check(123456789, 2, 3, 45, False, "email_limit_exceeded")

    output = log_stream.getvalue()

    # Check rate limiting logs
    assert "RATE_CHECK" in output
    assert "RATE_LIMITED" in output
    assert "2/3" in output  # Email count
    assert "3/5" in output  # User count
    assert "45s" in output  # Time since last
    assert "email_limit_exceeded" in output

    # Check PII masking
    assert "123***789" in output
    assert "123456789" not in output

    print("✓ Rate limiting logging works")


def test_health_check_logging():
    """Test health check logging."""
    print("Testing health check logging...")

    # Capture log output
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    logger = EmailFlowLogger()
    logger.logger.logger.handlers.clear()
    logger.logger.logger.addHandler(handler)
    logger.logger.logger.setLevel(logging.DEBUG)

    # Test health check logging
    logger.log_health_check("database", True, 50)
    logger.log_health_check("redis", False, error="connection_failed")

    output = log_stream.getvalue()

    # Check health check logs
    assert "DATABASE_HEALTH_CHECK" in output
    assert "REDIS_HEALTH_CHECK_FAILED" in output
    assert "response_time_ms=50" in output
    assert "error=connection_failed" in output

    print("✓ Health check logging works")


def test_application_logging_setup():
    """Test application logging setup."""
    print("Testing application logging setup...")

    # Test setup
    setup_application_logging("DEBUG")

    # Check that root logger is configured
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    # Check that handlers have PII-protected formatter
    if root_logger.handlers:
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, PIIProtectedFormatter)

    print("✓ Application logging setup works")


def test_global_email_flow_logger():
    """Test global email flow logger."""
    print("Testing global email flow logger...")

    logger1 = get_email_flow_logger()
    logger2 = get_email_flow_logger()

    # Should return same instance
    assert logger1 is logger2
    assert isinstance(logger1, EmailFlowLogger)

    print("✓ Global email flow logger works")


def test_edge_cases():
    """Test edge cases for PII masking."""
    print("Testing edge cases...")

    formatter = PIIProtectedFormatter()

    # Test multiple PII in one message
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="User 123456789 with email user@example.com used OTP 654321 and password secret123",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    # All PII should be masked
    assert "123***789" in formatted
    assert "u***@e***.com" in formatted
    assert "***OTP***" in formatted
    assert "***MASKED***" in formatted

    # Original values should not be present
    assert "123456789" not in formatted
    assert "user@example.com" not in formatted
    assert "654321" not in formatted
    assert "secret123" not in formatted

    print("✓ Edge cases handled correctly")


def test_no_false_positives():
    """Test that normal data is not masked."""
    print("Testing no false positives...")

    formatter = PIIProtectedFormatter()

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg="Processing 123456 records in 789 seconds with status 200",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)

    # Normal numbers should not be masked
    assert "123456 records" in formatted
    assert "789 seconds" in formatted
    assert "status 200" in formatted

    print("✓ No false positives in masking")


def main():
    """Run all tests."""
    print("Running logging utilities tests...\n")

    try:
        test_pii_protected_formatter()
        test_structured_logger()
        test_email_flow_logger()
        test_rate_limiting_logging()
        test_health_check_logging()
        test_application_logging_setup()
        test_global_email_flow_logger()
        test_edge_cases()
        test_no_false_positives()

        print("\n✅ All logging utilities tests passed!")
        return 0

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
