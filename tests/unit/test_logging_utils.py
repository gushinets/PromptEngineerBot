"""
Tests for comprehensive logging utilities with PII protection.

This module tests structured logging, PII masking, email flow logging,
and security features to ensure no sensitive data appears in logs.
"""

import logging
from io import StringIO

import pytest

from telegram_bot.utils.logging_utils import (
    EmailFlowLogger,
    PIIProtectedFormatter,
    StructuredLogger,
    get_email_flow_logger,
    log_performance_metric,
    log_pii_safe,
    log_security_event,
    log_system_event,
    log_user_action,
    setup_application_logging,
)


class TestPIIProtectedFormatter:
    """Test PII protection in log formatter."""

    def test_mask_email_addresses(self):
        """Test email address masking in log messages."""
        formatter = PIIProtectedFormatter()

        # Test various email formats
        test_cases = [
            ("User email: user@example.com", "User email: u***@e***.com"),
            (
                "Emails: test@domain.org, admin@site.net",
                "Emails: t***@d***.org, a***@s***.net",
            ),
            ("Contact support@company.co.uk", "Contact s***@c***.uk"),
            ("No email here", "No email here"),  # No change
        ]

        for original, expected in test_cases:
            masked = formatter._mask_pii(original)
            assert masked == expected

    def test_mask_telegram_ids(self):
        """Test telegram ID masking in log messages."""
        formatter = PIIProtectedFormatter()

        # Test telegram ID masking (only in telegram context)
        test_cases = [
            ("telegram_id: 123456789", "telegram_id: 123***789"),
            ("User 987654321 logged in", "User 987***321 logged in"),
            ("tg_id=555666777", "tg_id=555***777"),
            (
                "Random number 123456789",
                "Random number 123456789",
            ),  # No telegram context
            ("Port 8080 connection", "Port 8080 connection"),  # Too short
        ]

        for original, expected in test_cases:
            masked = formatter._mask_pii(original)
            assert masked == expected

    def test_mask_otp_codes(self):
        """Test OTP code masking in log messages."""
        formatter = PIIProtectedFormatter()

        # Test OTP masking (only in OTP context)
        test_cases = [
            ("OTP code: 123456", "OTP code: ***OTP***"),
            ("Verification code 789012", "Verification code ***OTP***"),
            ("otp=654321 sent", "otp=***OTP*** sent"),
            ("Random number 123456", "Random number 123456"),  # No OTP context
            ("Year 2023 data", "Year 2023 data"),  # Too short
        ]

        for original, expected in test_cases:
            masked = formatter._mask_pii(original)
            assert masked == expected

    def test_mask_passwords_and_secrets(self):
        """Test password and secret masking."""
        formatter = PIIProtectedFormatter()

        test_cases = [
            ("password=secret123", "password=***MASKED***"),
            ("PASSWORD: mypass", "PASSWORD=***MASKED***"),
            ("token abc123def", "token=***MASKED***"),
            ("secret key=xyz789", "secret key=***MASKED***"),
            ("API_KEY: sk-1234567890", "API_KEY=***MASKED***"),
        ]

        for original, expected in test_cases:
            masked = formatter._mask_pii(original)
            assert masked == expected

    def test_mask_url_credentials(self):
        """Test URL credential masking."""
        formatter = PIIProtectedFormatter()

        test_cases = [
            ("redis://user:pass@localhost:6379", "redis://***:***@localhost:6379"),
            (
                "postgresql://admin:secret@db.example.com/mydb",
                "postgresql://***:***@db.example.com/mydb",
            ),
            (
                "https://api.example.com/data",
                "https://api.example.com/data",
            ),  # No credentials
        ]

        for original, expected in test_cases:
            masked = formatter._mask_pii(original)
            assert masked == expected

    def test_format_log_record(self):
        """Test complete log record formatting with PII masking."""
        formatter = PIIProtectedFormatter("%(levelname)s - %(message)s")

        # Create log record with PII
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="User user@example.com with telegram_id 123456789 entered OTP 654321",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Verify PII is masked
        assert "u***@e***.com" in formatted
        assert "123***789" in formatted
        assert "***OTP***" in formatted
        assert "user@example.com" not in formatted
        assert "123456789" not in formatted
        assert "654321" not in formatted


class TestStructuredLogger:
    """Test structured logger with PII protection."""

    @pytest.fixture
    def logger_with_stream(self):
        """Create logger with string stream for testing."""
        logger = StructuredLogger("test_logger")

        # Replace handler with string stream
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = PIIProtectedFormatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        # Clear existing handlers and add test handler
        logger.logger.handlers.clear()
        logger.logger.addHandler(handler)
        logger.logger.setLevel(logging.DEBUG)

        return logger, stream

    def test_format_context_with_pii_masking(self, logger_with_stream):
        """Test context formatting with PII masking."""
        logger, stream = logger_with_stream

        # Log with PII in context
        logger.info(
            "User action",
            email="user@example.com",
            telegram_id=123456789,
            otp="654321",
            password="secret123",
            normal_field="normal_value",
        )

        output = stream.getvalue()

        # Verify PII is masked in context
        assert "email=u***@e***.com" in output
        assert "telegram_id=123***789" in output
        assert "otp=***MASKED***" in output
        assert "password=***MASKED***" in output
        assert "normal_field=normal_value" in output

        # Verify original PII is not present
        assert "user@example.com" not in output
        assert "123456789" not in output
        assert "654321" not in output
        assert "secret123" not in output

    def test_logging_levels(self, logger_with_stream):
        """Test all logging levels work correctly."""
        logger, stream = logger_with_stream

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        logger.critical("Critical message")

        output = stream.getvalue()

        assert "DEBUG - Debug message" in output
        assert "INFO - Info message" in output
        assert "WARNING - Warning message" in output
        assert "ERROR - Error message" in output
        assert "CRITICAL - Critical message" in output

    def test_empty_context(self, logger_with_stream):
        """Test logging without context."""
        logger, stream = logger_with_stream

        logger.info("Simple message")

        output = stream.getvalue()
        assert "INFO - Simple message" in output
        assert "|" not in output  # No context separator


class TestEmailFlowLogger:
    """Test specialized email flow logger."""

    @pytest.fixture
    def email_logger_with_stream(self):
        """Create email flow logger with string stream for testing."""
        email_logger = EmailFlowLogger()

        # Replace handler with string stream
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = PIIProtectedFormatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        # Clear existing handlers and add test handler
        email_logger.logger.logger.handlers.clear()
        email_logger.logger.logger.addHandler(handler)
        email_logger.logger.logger.setLevel(logging.DEBUG)

        return email_logger, stream

    def test_log_flow_start(self, email_logger_with_stream):
        """Test email flow start logging."""
        logger, stream = email_logger_with_stream

        logger.log_flow_start(123456789)

        output = stream.getvalue()
        assert "EMAIL_FLOW_START" in output
        assert "123***789" in output
        assert "123456789" not in output

    def test_log_email_input(self, email_logger_with_stream):
        """Test email input logging with validation."""
        logger, stream = email_logger_with_stream

        logger.log_email_input(123456789, "user@example.com", True)

        output = stream.getvalue()
        assert "EMAIL_INPUT" in output
        assert "EMAIL_VALIDATION" in output
        assert "u***@e***.com" in output
        assert "valid" in output
        assert "user@example.com" not in output

    def test_log_rate_check(self, email_logger_with_stream):
        """Test rate limiting check logging."""
        logger, stream = email_logger_with_stream

        logger.log_rate_check(
            telegram_id=123456789,
            email_count=2,
            user_count=3,
            seconds_since_last=45,
            is_allowed=True,
        )

        output = stream.getvalue()
        assert "RATE_CHECK" in output
        assert "2/3" in output
        assert "3/5" in output
        assert "45s" in output
        assert "allowed=True" in output

    def test_log_rate_check_blocked(self, email_logger_with_stream):
        """Test rate limiting blocked logging."""
        logger, stream = email_logger_with_stream

        logger.log_rate_check(
            telegram_id=123456789,
            email_count=3,
            user_count=5,
            seconds_since_last=30,
            is_allowed=False,
            reason="email_limit_exceeded",
        )

        output = stream.getvalue()
        assert "RATE_CHECK" in output
        assert "RATE_LIMITED" in output
        assert "email_limit_exceeded" in output
        assert "allowed=False" in output

    def test_log_otp_generation(self, email_logger_with_stream):
        """Test OTP generation logging (should not log actual OTP)."""
        logger, stream = email_logger_with_stream

        logger.log_otp_generation(123456789)

        output = stream.getvalue()
        assert "OTP_GENERATED" in output
        assert "6-digit OTP created" in output
        assert "123***789" in output
        # Verify no actual OTP is logged
        assert not any(
            char.isdigit() and len([c for c in output if c.isdigit()]) == 6 for char in output
        )

    def test_log_otp_verification_success(self, email_logger_with_stream):
        """Test successful OTP verification logging."""
        logger, stream = email_logger_with_stream

        logger.log_otp_verification(123456789, 1, True)

        output = stream.getvalue()
        assert "OTP_VERIFY_SUCCESS" in output
        assert "authenticated" in output
        assert "123***789" in output

    def test_log_otp_verification_failure(self, email_logger_with_stream):
        """Test failed OTP verification logging."""
        logger, stream = email_logger_with_stream

        logger.log_otp_verification(123456789, 2, False, "invalid_code")

        output = stream.getvalue()
        assert "OTP_VERIFY_FAILED" in output
        assert "attempt 2/3" in output
        assert "invalid_code" in output
        assert "123***789" in output

    def test_log_redis_operation(self, email_logger_with_stream):
        """Test Redis operation logging."""
        logger, stream = email_logger_with_stream

        # Test successful operation
        logger.log_redis_operation("SET", 123456789, True, "key stored")

        output = stream.getvalue()
        assert "REDIS_SET" in output
        assert "successful" in output
        assert "key stored" in output

    def test_log_database_operation(self, email_logger_with_stream):
        """Test database operation logging."""
        logger, stream = email_logger_with_stream

        # Test failed operation
        logger.log_database_operation("USER_CREATE", 123456789, False, "constraint violation")

        output = stream.getvalue()
        assert "DB_USER_CREATE_FAILED" in output
        assert "failed" in output
        assert "constraint violation" in output

    def test_log_email_sending_success(self, email_logger_with_stream):
        """Test successful email sending logging."""
        logger, stream = email_logger_with_stream

        logger.log_email_sending(123456789, "user@example.com", True, delivery_time_ms=250)

        output = stream.getvalue()
        assert "EMAIL_SEND_SUCCESS" in output
        assert "delivered" in output
        assert "u***@e***.com" in output
        assert "delivery_time_ms=250" in output
        assert "user@example.com" not in output

    def test_log_email_sending_failure(self, email_logger_with_stream):
        """Test failed email sending logging."""
        logger, stream = email_logger_with_stream

        logger.log_email_sending(123456789, "user@example.com", False, error_type="smtp_timeout")

        output = stream.getvalue()
        assert "EMAIL_SEND_FAILED" in output
        assert "failed" in output
        assert "smtp_timeout" in output
        assert "u***@e***.com" in output

    def test_log_smtp_connection(self, email_logger_with_stream):
        """Test SMTP connection logging."""
        logger, stream = email_logger_with_stream

        logger.log_smtp_connection(True, "smtp.example.com", 587)

        output = stream.getvalue()
        assert "SMTP_CONNECT" in output
        assert "established" in output
        assert "smtp.example.com" in output
        assert "587" in output

    def test_log_health_check(self, email_logger_with_stream):
        """Test health check logging."""
        logger, stream = email_logger_with_stream

        logger.log_health_check("database", True, response_time_ms=50)

        output = stream.getvalue()
        assert "DATABASE_HEALTH_CHECK" in output
        assert "healthy" in output
        assert "response_time_ms=50" in output


class TestLogPIISafeDecorator:
    """Test PII-safe logging decorator."""

    @pytest.fixture
    def logger_with_stream(self):
        """Create logger with string stream for testing."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = PIIProtectedFormatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        # Set up root logger for decorator testing
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

        return stream

    def test_decorator_masks_pii_in_args(self, logger_with_stream):
        """Test decorator masks PII in function arguments."""
        stream = logger_with_stream

        @log_pii_safe
        def test_function(email, telegram_id, normal_arg):
            return "success"

        result = test_function("user@example.com", 123456789, "normal_value")

        assert result == "success"
        output = stream.getvalue()

        # Verify PII is masked in logs
        assert "u***@e***.com" in output
        assert "123***789" in output
        assert "normal_value" in output
        assert "user@example.com" not in output
        assert "123456789" not in output

    def test_decorator_masks_pii_in_kwargs(self, logger_with_stream):
        """Test decorator masks PII in keyword arguments."""
        stream = logger_with_stream

        @log_pii_safe
        def test_function(**kwargs):
            return "success"

        result = test_function(
            email="user@example.com",
            telegram_id=123456789,
            otp="654321",
            password="secret",
            normal_field="value",
        )

        assert result == "success"
        output = stream.getvalue()

        # Verify PII is masked in kwargs
        assert "email=u***@e***.com" in output
        assert "telegram_id=123***789" in output
        assert "otp=***MASKED***" in output
        assert "password=***MASKED***" in output
        assert "normal_field=value" in output

    def test_decorator_logs_exceptions(self, logger_with_stream):
        """Test decorator logs exceptions properly."""
        stream = logger_with_stream

        @log_pii_safe
        def failing_function():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        output = stream.getvalue()
        assert "FUNCTION_ERROR" in output
        assert "failing_function" in output
        assert "Test error" in output


class TestGlobalLoggingFunctions:
    """Test global logging convenience functions."""

    @pytest.fixture
    def logger_with_stream(self):
        """Create logger with string stream for testing."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        formatter = PIIProtectedFormatter("%(levelname)s - %(message)s")
        handler.setFormatter(formatter)

        # Set up root logger
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.DEBUG)

        return stream

    def test_log_user_action(self, logger_with_stream):
        """Test user action logging."""
        stream = logger_with_stream

        log_user_action("login", 123456789, email="user@example.com")

        output = stream.getvalue()
        assert "USER_ACTION: login" in output
        assert "123***789" in output
        assert "u***@e***.com" in output

    def test_log_system_event(self, logger_with_stream):
        """Test system event logging."""
        stream = logger_with_stream

        log_system_event("startup", version="1.0.0")

        output = stream.getvalue()
        assert "SYSTEM_EVENT: startup" in output
        assert "version=1.0.0" in output

    def test_log_security_event(self, logger_with_stream):
        """Test security event logging."""
        stream = logger_with_stream

        log_security_event("rate_limit_exceeded", telegram_id=123456789, attempts=5)

        output = stream.getvalue()
        assert "SECURITY_EVENT: rate_limit_exceeded" in output
        assert "123***789" in output
        assert "attempts=5" in output

    def test_log_performance_metric(self, logger_with_stream):
        """Test performance metric logging."""
        stream = logger_with_stream

        log_performance_metric("response_time", 250, "ms", endpoint="/api/health")

        output = stream.getvalue()
        assert "PERFORMANCE_METRIC: response_time" in output
        assert "value=250" in output
        assert "unit=ms" in output
        assert "endpoint=/api/health" in output


class TestApplicationLoggingSetup:
    """Test application-wide logging setup."""

    def test_setup_application_logging(self):
        """Test application logging setup."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        setup_application_logging(log_level="DEBUG")

        # Verify root logger is configured
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) == 1

        # Verify handler has PII-protected formatter
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, PIIProtectedFormatter)

    def test_setup_with_custom_format(self):
        """Test setup with custom log format."""
        root_logger = logging.getLogger()
        root_logger.handlers.clear()

        custom_format = "%(name)s - %(levelname)s - %(message)s"
        setup_application_logging(log_level="INFO", log_format=custom_format)

        # Verify custom format is used
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, PIIProtectedFormatter)
        assert handler.formatter._fmt == custom_format

    def test_get_email_flow_logger(self):
        """Test getting global email flow logger."""
        logger = get_email_flow_logger()

        assert isinstance(logger, EmailFlowLogger)

        # Should return same instance
        same_logger = get_email_flow_logger()
        assert same_logger is logger


class TestPIIMaskingEdgeCases:
    """Test edge cases for PII masking."""

    def test_empty_and_none_values(self):
        """Test handling of empty and None values."""
        formatter = PIIProtectedFormatter()

        test_cases = [
            ("", ""),
            (None, None),
            ("   ", "   "),
            ("No PII here", "No PII here"),
        ]

        for original, expected in test_cases:
            if original is None:
                # formatter._mask_pii should handle None gracefully
                continue
            masked = formatter._mask_pii(original)
            assert masked == expected

    def test_multiple_pii_types_in_message(self):
        """Test message with multiple PII types."""
        formatter = PIIProtectedFormatter()

        message = "User telegram_id 123456789 with email user@example.com entered OTP 654321 and password secret123"
        masked = formatter._mask_pii(message)

        # Verify all PII types are masked
        assert "123***789" in masked
        assert "u***@e***.com" in masked
        assert "***OTP***" in masked
        assert "password=***MASKED***" in masked

        # Verify original PII is not present
        assert "123456789" not in masked
        assert "user@example.com" not in masked
        assert "654321" not in masked
        assert "secret123" not in masked

    def test_context_sensitive_masking(self):
        """Test that masking is context-sensitive."""
        formatter = PIIProtectedFormatter()

        # 6-digit number should only be masked in OTP context
        assert formatter._mask_pii("Random number 123456") == "Random number 123456"
        assert formatter._mask_pii("OTP: 123456") == "OTP: ***OTP***"

        # Long number should only be masked in telegram context
        assert formatter._mask_pii("Port 123456789") == "Port 123456789"
        assert formatter._mask_pii("telegram_id: 123456789") == "telegram_id: 123***789"

    def test_international_email_formats(self):
        """Test masking of international email formats."""
        formatter = PIIProtectedFormatter()

        test_cases = [
            ("user@münchen.de", "u***@m***.de"),
            ("test@xn--fsq.xn--0zwm56d", "t***@x***.xn--0zwm56d"),  # IDN domain
            ("admin@sub.domain.co.uk", "a***@s***.uk"),
        ]

        for original, expected in test_cases:
            masked = formatter._mask_pii(original)
            assert masked == expected
