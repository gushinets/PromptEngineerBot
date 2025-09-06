"""
Tests for email service functionality including provider error extraction.
"""

import smtplib
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.config import BotConfig
from src.email_service import EmailDeliveryResult, EmailService


def create_mock_config():
    """Create mock configuration for testing."""
    config = Mock(spec=BotConfig)
    config.smtp_host = "smtp.example.com"
    config.smtp_port = 587
    config.smtp_username = "test@example.com"
    config.smtp_password = "password"
    config.smtp_from_email = "test@example.com"
    config.smtp_from_name = "Test Bot"
    config.smtp_use_tls = True
    config.smtp_use_ssl = False
    config.language = "en"
    return config


def create_email_service():
    """Create email service instance for testing."""
    mock_config = create_mock_config()
    with patch("src.email_service.EmailTemplates"):
        return EmailService(mock_config)


class TestProviderErrorExtraction:
    """Test provider error extraction functionality."""

    def test_extract_provider_error_timeout(self):
        """Test timeout error extraction."""
        email_service = create_email_service()
        error_msg = "Connection timed out after 30 seconds"
        result = email_service._extract_provider_error(error_msg)
        assert result == "smtp_timeout"

    def test_extract_provider_error_connection_refused(self):
        """Test connection refused error extraction."""
        email_service = create_email_service()
        error_msg = "Connection refused by server"
        result = email_service._extract_provider_error(error_msg)
        assert result == "connection_refused"

    def test_extract_provider_error_authentication_failed(self):
        """Test authentication failed error extraction."""
        email_service = create_email_service()
        error_msg = "Authentication failed: Invalid credentials"
        result = email_service._extract_provider_error(error_msg)
        assert result == "authentication_failed"

    def test_extract_provider_error_invalid_recipient(self):
        """Test invalid recipient error extraction."""
        email_service = create_email_service()
        error_msg = "Recipient rejected: user@invalid-domain.com"
        result = email_service._extract_provider_error(error_msg)
        assert result == "invalid_recipient"

    def test_extract_provider_error_quota_exceeded(self):
        """Test quota exceeded error extraction."""
        email_service = create_email_service()
        error_msg = "Quota exceeded: Daily limit reached"
        result = email_service._extract_provider_error(error_msg)
        assert result == "quota_exceeded"

    def test_extract_provider_error_dns_error(self):
        """Test DNS error extraction."""
        email_service = create_email_service()
        error_msg = "DNS lookup failed for hostname smtp.example.com"
        result = email_service._extract_provider_error(error_msg)
        assert result == "dns_error"

    def test_extract_provider_error_ssl_tls_error(self):
        """Test SSL/TLS error extraction."""
        email_service = create_email_service()
        error_msg = "SSL handshake failed"
        result = email_service._extract_provider_error(error_msg)
        assert result == "ssl_tls_error"

    def test_extract_provider_error_network_error(self):
        """Test network error extraction."""
        email_service = create_email_service()
        error_msg = "Network unreachable"
        result = email_service._extract_provider_error(error_msg)
        assert result == "network_error"

    def test_extract_provider_error_server_unavailable(self):
        """Test server unavailable error extraction."""
        email_service = create_email_service()
        error_msg = "Server unavailable, try again later"
        result = email_service._extract_provider_error(error_msg)
        assert result == "server_unavailable"

    def test_extract_provider_error_generic(self):
        """Test generic error extraction for unknown errors."""
        email_service = create_email_service()
        error_msg = "Some unknown SMTP error occurred"
        result = email_service._extract_provider_error(error_msg)
        assert result == "smtp_error"

    def test_extract_provider_error_empty_message(self):
        """Test error extraction with empty message."""
        email_service = create_email_service()
        result = email_service._extract_provider_error("")
        assert result == "unknown_error"

    def test_extract_provider_error_none_message(self):
        """Test error extraction with None message."""
        email_service = create_email_service()
        result = email_service._extract_provider_error(None)
        assert result == "unknown_error"


class TestEmailFailureAuditLogging:
    """Test email failure audit logging with provider error info."""

    @patch("src.email_service.get_audit_service")
    @patch.object(EmailService, "_send_email_with_queue_fallback")
    async def test_otp_email_failure_logs_provider_error(
        self, mock_send, mock_get_audit
    ):
        """Test that OTP email failures log provider error info to audit."""
        # Setup mocks
        mock_audit = Mock()
        mock_get_audit.return_value = mock_audit

        # Mock email sending failure
        mock_send.return_value = EmailDeliveryResult(
            success=False, error="Connection timed out after 30 seconds"
        )

        email_service = create_email_service()

        # Call method
        result = await email_service.send_otp_email(
            "test@example.com", "123456", 123456789
        )

        # Verify audit logging was called with extracted error reason
        mock_audit.log_email_send_failure.assert_called_once_with(
            123456789, "test@example.com", "smtp_timeout"
        )
        assert not result.success

    @patch("src.email_service.get_audit_service")
    @patch.object(EmailService, "_send_email_with_queue_fallback")
    @patch("src.email_service.EmailTemplates")
    async def test_optimization_email_failure_logs_provider_error(
        self, mock_templates_class, mock_send, mock_get_audit
    ):
        """Test that optimization email failures log provider error info to audit."""
        # Setup mocks
        mock_audit = Mock()
        mock_get_audit.return_value = mock_audit

        # Mock email templates
        mock_templates = Mock()
        mock_templates.compose_optimization_email.return_value = (
            "Test Subject",
            "<html>Test HTML</html>",
            "Test Plain Text",
        )
        mock_templates_class.return_value = mock_templates

        # Mock email sending failure
        mock_send.return_value = EmailDeliveryResult(
            success=False, error="Authentication failed: Invalid credentials"
        )

        # Create email service with properly mocked templates
        mock_config = create_mock_config()
        email_service = EmailService(mock_config)
        email_service.templates = mock_templates

        # Call method
        result = await email_service.send_optimized_prompts_email(
            "test@example.com",
            "original prompt",
            "craft result",
            "lyra result",
            "ggl result",
            123456789,
            "improved prompt",
        )

        # Verify audit logging was called with extracted error reason
        mock_audit.log_email_send_failure.assert_called_once_with(
            123456789, "test@example.com", "authentication_failed"
        )
        assert not result.success

    @patch("src.email_service.get_audit_service")
    async def test_unexpected_error_logs_provider_error(self, mock_get_audit):
        """Test that unexpected errors during email sending log provider error info."""
        # Setup mocks
        mock_audit = Mock()
        mock_get_audit.return_value = mock_audit

        email_service = create_email_service()

        # Mock an unexpected exception during email composition
        with patch.object(
            email_service.templates,
            "get_otp_subject",
            side_effect=Exception("DNS lookup failed"),
        ):
            result = await email_service.send_otp_email(
                "test@example.com", "123456", 123456789
            )

        # Verify audit logging was called with extracted error reason
        mock_audit.log_email_send_failure.assert_called_once_with(
            123456789, "test@example.com", "dns_error"
        )
        assert not result.success

    @patch("src.email_service.get_audit_service")
    @patch.object(EmailService, "_send_email_with_queue_fallback")
    async def test_email_success_logs_without_error_reason(
        self, mock_send, mock_get_audit
    ):
        """Test that successful email sending logs success without error reason."""
        # Setup mocks
        mock_audit = Mock()
        mock_get_audit.return_value = mock_audit

        # Mock successful email sending
        mock_send.return_value = EmailDeliveryResult(
            success=True, message_id="test-message-id", delivery_time_ms=500
        )

        email_service = create_email_service()

        # Call method
        result = await email_service.send_otp_email(
            "test@example.com", "123456", 123456789
        )

        # Verify success audit logging was called (no error reason)
        mock_audit.log_email_send_success.assert_called_once_with(
            123456789, "test@example.com"
        )
        mock_audit.log_email_send_failure.assert_not_called()
        assert result.success

    @patch("src.email_service.get_audit_service")
    @patch.object(EmailService, "_send_email_with_queue_fallback")
    async def test_audit_service_failure_does_not_break_email_flow(
        self, mock_send, mock_get_audit
    ):
        """Test that audit service failures don't break the email flow."""
        # Setup mocks
        mock_audit = Mock()
        mock_audit.log_email_send_failure.side_effect = Exception("Audit service error")
        mock_get_audit.return_value = mock_audit

        # Mock email sending failure
        mock_send.return_value = EmailDeliveryResult(
            success=False, error="Connection refused by server"
        )

        email_service = create_email_service()

        # Call method - should not raise exception despite audit failure
        result = await email_service.send_otp_email(
            "test@example.com", "123456", 123456789
        )

        # Verify the email result is still returned correctly
        assert not result.success
        assert "Connection refused by server" in result.error
