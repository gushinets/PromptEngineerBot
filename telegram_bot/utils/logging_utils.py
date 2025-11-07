"""
Comprehensive logging utilities with PII protection.

This module provides structured logging throughout all components with proper
PII masking to ensure no sensitive data (OTPs, credentials, emails, telegram IDs)
appears in logs.
"""

import logging
import re
from functools import wraps

from telegram_bot.data.database import mask_email, mask_telegram_id


class PIIProtectedFormatter(logging.Formatter):
    """
    Custom logging formatter that automatically masks PII in log messages.

    This formatter scans log messages for common PII patterns and masks them
    before outputting to prevent accidental exposure of sensitive data.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Compile regex patterns for PII detection
        self._email_pattern = re.compile(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b", re.UNICODE)
        self._telegram_id_pattern = re.compile(
            r"\b\d{8,12}\b"
        )  # Telegram IDs are typically 8-12 digits
        self._otp_pattern = re.compile(r"\b\d{6}\b")  # 6-digit OTPs
        self._password_pattern = re.compile(
            r"((?:secret\s+key|api_key|password|pwd|pass|secret|token|key))(?:\s*[=:]\s*|\s+)(?!(?:stored|found|missing|error|success|failed|valid|invalid|expired|generated)\b)[^\s]+",
            re.IGNORECASE,
        )
        self._url_credentials_pattern = re.compile(r"://[^:]+:[^@]+@")  # URLs with credentials

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with PII masking."""
        # Format the record normally first
        formatted = super().format(record)

        # Apply PII masking
        formatted = self._mask_pii(formatted)

        return formatted

    def _mask_pii(self, message: str) -> str:
        """
        Mask PII in log message.

        Args:
            message: Original log message

        Returns:
            Log message with PII masked
        """
        if not message:
            return message

        # Mask credentials in URLs first (before email masking)
        message = self._url_credentials_pattern.sub("://***:***@", message)

        # Mask email addresses
        message = self._email_pattern.sub(lambda m: mask_email(m.group(0)), message)

        # Mask telegram IDs (but be careful not to mask other numbers)
        # Only mask if it looks like a telegram ID in context
        if (
            "telegram" in message.lower()
            or "tg_id" in message.lower()
            or "user_id" in message.lower()
            or "user " in message.lower()
        ):
            message = self._telegram_id_pattern.sub(
                lambda m: mask_telegram_id(int(m.group(0))), message
            )

        # Mask 6-digit OTPs (but only if in OTP context)
        if "otp" in message.lower() or "code" in message.lower():
            message = self._otp_pattern.sub("***OTP***", message)

        # Mask passwords and secrets
        message = self._password_pattern.sub(r"\1=***MASKED***", message)

        return message


class StructuredLogger:
    """
    Structured logger with PII protection and consistent formatting.

    This class provides a consistent interface for logging throughout the application
    with automatic PII masking and structured data support.
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._setup_formatter()

    def _setup_formatter(self):
        """Set up PII-protected formatter if not already configured."""
        # Don't add handlers here - rely on root logger configuration
        # This prevents duplicate handlers when setup_application_logging is used

    def _format_context(self, **context) -> str:
        """Format context data for logging."""
        if not context:
            return ""

        formatted_items = []
        for key, value in context.items():
            # Apply PII masking to context values
            if key.lower() in ["email", "email_address", "to_email", "from_email"]:
                value = mask_email(str(value)) if value else value
            elif key.lower() in ["telegram_id", "tg_id", "user_id"]:
                value = mask_telegram_id(int(value)) if value else value
            elif key.lower() in ["otp", "code", "password", "secret", "token"]:
                value = "***MASKED***"

            formatted_items.append(f"{key}={value}")

        return " | " + " | ".join(formatted_items)

    def debug(self, message: str, **context):
        """Log debug message with context."""
        context_str = self._format_context(**context)
        self.logger.debug(f"{message}{context_str}")

    def info(self, message: str, **context):
        """Log info message with context."""
        context_str = self._format_context(**context)
        self.logger.info(f"{message}{context_str}")

    def warning(self, message: str, **context):
        """Log warning message with context."""
        context_str = self._format_context(**context)
        self.logger.warning(f"{message}{context_str}")

    def error(self, message: str, **context):
        """Log error message with context."""
        context_str = self._format_context(**context)
        self.logger.error(f"{message}{context_str}")

    def critical(self, message: str, **context):
        """Log critical message with context."""
        context_str = self._format_context(**context)
        self.logger.critical(f"{message}{context_str}")


def get_logger(name: str) -> StructuredLogger:
    """
    Get a structured logger instance with PII protection.

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLogger instance
    """
    return StructuredLogger(name)


def log_pii_safe(func):
    """
    Decorator to ensure function arguments are PII-safe in logs.

    This decorator can be applied to functions that might log their arguments
    to ensure any PII is properly masked.
    """

    @wraps(func)
    def wrapper(*args, **kwargs):
        # Get logger for the function's module
        # Use standard logging for better test compatibility
        logger = logging.getLogger(func.__module__)

        # Log function entry (with PII masking)
        safe_args = []
        for i, arg in enumerate(args):
            if isinstance(arg, str) and "@" in arg:
                safe_args.append(mask_email(arg))
            elif isinstance(arg, int) and len(str(arg)) >= 8:
                safe_args.append(mask_telegram_id(arg))
            else:
                safe_args.append(str(arg)[:50])  # Truncate long args

        safe_kwargs = {}
        for key, value in kwargs.items():
            if key.lower() in ["email", "email_address", "to_email"]:
                safe_kwargs[key] = mask_email(str(value)) if value else value
            elif key.lower() in ["telegram_id", "tg_id", "user_id"]:
                safe_kwargs[key] = mask_telegram_id(int(value)) if value else value
            elif key.lower() in ["otp", "password", "secret", "token"]:
                safe_kwargs[key] = "***MASKED***"
            else:
                safe_kwargs[key] = str(value)[:50] if value else value

        # Format kwargs for logging
        kwargs_str = " | ".join([f"{k}={v}" for k, v in safe_kwargs.items()])
        args_str = ", ".join([str(arg) for arg in safe_args[:3]])

        logger.debug(f"FUNCTION_CALL: {func.__name__} | args=[{args_str}] | {kwargs_str}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"FUNCTION_SUCCESS: {func.__name__}")
            return result
        except Exception as e:
            logger.error(f"FUNCTION_ERROR: {func.__name__} | error={e!s}")
            raise

    return wrapper


class EmailFlowLogger:
    """
    Specialized logger for email authentication flow with comprehensive event tracking.

    This logger provides specific methods for logging email flow events with
    proper PII masking and consistent formatting.
    """

    def __init__(self):
        self.logger = get_logger("email_flow")

    def log_flow_start(self, telegram_id: int):
        """Log email flow initiation."""
        self.logger.info("EMAIL_FLOW_START: User initiated email delivery", telegram_id=telegram_id)

    def log_email_input(self, telegram_id: int, email: str, is_valid: bool):
        """Log email input and validation."""
        self.logger.info("EMAIL_INPUT: User provided email", telegram_id=telegram_id, email=email)
        self.logger.info(
            f"EMAIL_VALIDATION: Email format {'valid' if is_valid else 'invalid'}",
            telegram_id=telegram_id,
        )

    def log_rate_check(
        self,
        telegram_id: int,
        email_count: int,
        user_count: int,
        seconds_since_last: int,
        is_allowed: bool,
        reason: str | None = None,
    ):
        """Log rate limiting check."""
        self.logger.info(
            "RATE_CHECK: Rate limit status",
            telegram_id=telegram_id,
            email_count=f"{email_count}/3",
            user_count=f"{user_count}/5",
            last_send=f"{seconds_since_last}s",
            allowed=is_allowed,
        )

        if not is_allowed and reason:
            self.logger.warning(
                "RATE_LIMITED: User blocked", telegram_id=telegram_id, reason=reason
            )

    def log_otp_generation(self, telegram_id: int):
        """Log OTP generation (never log the actual OTP)."""
        self.logger.info("OTP_GENERATED: 6-digit OTP created", telegram_id=telegram_id)

    def log_otp_sent(self, telegram_id: int, email: str):
        """Log OTP email sent."""
        self.logger.info("OTP_SENT: Email sent", telegram_id=telegram_id, email=email)

    def log_otp_verification(
        self,
        telegram_id: int,
        attempt: int,
        success: bool,
        reason: str | None = None,
    ):
        """Log OTP verification attempt."""
        if success:
            self.logger.info("OTP_VERIFY_SUCCESS: User authenticated", telegram_id=telegram_id)
        else:
            self.logger.warning(
                f"OTP_VERIFY_FAILED: Failed attempt {attempt}/3",
                telegram_id=telegram_id,
                reason=reason or "invalid_code",
            )

    def log_otp_expired(self, telegram_id: int):
        """Log OTP expiration."""
        self.logger.warning("OTP_EXPIRED: Expired OTP", telegram_id=telegram_id)

    def log_redis_operation(
        self,
        operation: str,
        telegram_id: int,
        success: bool,
        details: str | None = None,
    ):
        """Log Redis operations."""
        if success:
            self.logger.debug(
                f"REDIS_{operation.upper()}: Operation successful",
                telegram_id=telegram_id,
                details=details,
            )
        else:
            self.logger.error(
                f"REDIS_{operation.upper()}_FAILED: Operation failed",
                telegram_id=telegram_id,
                details=details,
            )

    def log_database_operation(
        self,
        operation: str,
        telegram_id: int,
        success: bool,
        details: str | None = None,
    ):
        """Log database operations."""
        if success:
            self.logger.info(
                f"DB_{operation.upper()}: Operation successful",
                telegram_id=telegram_id,
                details=details,
            )
        else:
            self.logger.error(
                f"DB_{operation.upper()}_FAILED: Operation failed",
                telegram_id=telegram_id,
                details=details,
            )

    def log_email_sending(
        self,
        telegram_id: int,
        email: str,
        success: bool,
        error_type: str | None = None,
        delivery_time_ms: int | None = None,
    ):
        """Log email sending attempts."""
        if success:
            self.logger.info(
                "EMAIL_SEND_SUCCESS: Email delivered",
                telegram_id=telegram_id,
                email=email,
                delivery_time_ms=delivery_time_ms,
            )
        else:
            self.logger.error(
                "EMAIL_SEND_FAILED: Email delivery failed",
                telegram_id=telegram_id,
                email=email,
                error_type=error_type or "unknown",
            )

    def log_smtp_connection(self, success: bool, host: str, port: int, error: str | None = None):
        """Log SMTP connection attempts."""
        if success:
            self.logger.debug("SMTP_CONNECT: Connection established", host=host, port=port)
        else:
            self.logger.error(
                "SMTP_CONNECT_FAILED: Connection failed",
                host=host,
                port=port,
                error=error,
            )

    def log_followup_flow(self, telegram_id: int, stage: str, success: bool = True):
        """Log follow-up questions flow."""
        if success:
            self.logger.info(f"FOLLOWUP_{stage.upper()}: Stage completed", telegram_id=telegram_id)
        else:
            self.logger.warning(
                f"FOLLOWUP_{stage.upper()}_FAILED: Stage failed",
                telegram_id=telegram_id,
            )

    def log_optimization_flow(self, telegram_id: int, stage: str, method: str | None = None):
        """Log optimization flow."""
        if method:
            self.logger.info(
                f"OPTIMIZATION_{stage.upper()}: {method} method",
                telegram_id=telegram_id,
            )
        else:
            self.logger.info(f"OPTIMIZATION_{stage.upper()}: All methods", telegram_id=telegram_id)

    def log_health_check(
        self,
        service: str,
        healthy: bool,
        response_time_ms: int | None = None,
        error: str | None = None,
    ):
        """Log health check results."""
        if healthy:
            self.logger.debug(
                f"{service.upper()}_HEALTH_CHECK: Service healthy",
                response_time_ms=response_time_ms,
            )
        else:
            self.logger.warning(
                f"{service.upper()}_HEALTH_CHECK_FAILED: Service unhealthy", error=error
            )

    def log_error_scenario(
        self,
        scenario: str,
        telegram_id: int | None = None,
        error: str | None = None,
        **context,
    ):
        """Log error scenarios."""
        self.logger.error(
            f"ERROR_{scenario.upper()}: Error occurred",
            telegram_id=telegram_id,
            error=error,
            **context,
        )


def setup_application_logging(log_level: str = "INFO", log_format: str | None = None):
    """
    Set up application-wide logging with PII protection.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Custom log format string (optional)
    """
    # Set root logger level
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler with PII protection
    console_handler = logging.StreamHandler()

    if log_format:
        formatter = PIIProtectedFormatter(log_format)
    else:
        formatter = PIIProtectedFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific logger levels for noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)

    # Create application loggers
    app_logger = get_logger("application")
    app_logger.info(
        "APPLICATION_LOGGING_INITIALIZED: PII-protected logging enabled",
        log_level=log_level,
    )


# Global email flow logger instance
email_flow_logger = EmailFlowLogger()


def get_email_flow_logger() -> EmailFlowLogger:
    """Get the global email flow logger instance."""
    return email_flow_logger


# Convenience functions for common logging patterns
def log_user_action(action: str, telegram_id: int, **context):
    """Log user action with PII protection."""
    logger = get_logger("user_actions")
    logger.info(f"USER_ACTION: {action}", telegram_id=telegram_id, **context)


def log_system_event(event: str, **context):
    """Log system event."""
    logger = get_logger("system")
    logger.info(f"SYSTEM_EVENT: {event}", **context)


def log_security_event(event: str, telegram_id: int | None = None, **context):
    """Log security-related event."""
    logger = get_logger("security")
    logger.warning(f"SECURITY_EVENT: {event}", telegram_id=telegram_id, **context)


def log_performance_metric(metric: str, value: int | float, unit: str = "", **context):
    """Log performance metric."""
    logger = get_logger("performance")
    logger.info(f"PERFORMANCE_METRIC: {metric}", value=value, unit=unit, **context)
