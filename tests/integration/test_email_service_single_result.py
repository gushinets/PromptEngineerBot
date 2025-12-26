"""
Tests for email service single result functionality.

This module tests the new send_single_result_email method in EmailService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from telegram_bot.services.email_service import EmailDeliveryResult, EmailService
from telegram_bot.utils.email_templates import EmailTemplates


class TestEmailServiceSingleResult:
    """Test EmailService single result email functionality."""

    @pytest.fixture
    def email_service(self):
        """Create EmailService instance for testing."""
        config = MagicMock()
        config.language = "RU"
        config.smtp_host = "smtp.example.com"
        config.smtp_port = 587
        config.smtp_username = "test@example.com"
        config.smtp_password = "password"
        config.smtp_from_email = "test@example.com"
        config.smtp_from_name = "Test Bot"
        config.smtp_use_tls = True
        config.smtp_use_ssl = False

        with patch("telegram_bot.services.email_service.get_audit_service"):
            service = EmailService(config)
            return service

    @pytest.mark.asyncio
    async def test_send_single_result_email_success(self, email_service):
        """Test successful single result email sending."""
        to_email = "user@example.com"
        original_prompt = "Test original prompt"
        method_name = "CRAFT"
        optimized_result = "Test optimized result"
        telegram_id = 12345

        # Mock email sending
        mock_result = EmailDeliveryResult(success=True, message_id="test123")
        email_service._send_email_with_queue_fallback = AsyncMock(return_value=mock_result)
        email_service._generate_email_hash = MagicMock(return_value="hash123")
        email_service._is_email_already_sent = AsyncMock(return_value=False)

        result = await email_service.send_single_result_email(
            to_email, original_prompt, method_name, optimized_result, telegram_id
        )

        assert result.success is True
        assert result.message_id == "test123"
        email_service._send_email_with_queue_fallback.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_single_result_email_duplicate_blocked(self, email_service):
        """Test that duplicate single result emails are blocked."""
        to_email = "user@example.com"
        original_prompt = "Test original prompt"
        method_name = "LYRA"
        optimized_result = "Test optimized result"
        telegram_id = 12345

        # Mock duplicate detection
        email_service._generate_email_hash = MagicMock(return_value="hash123")
        email_service._is_email_already_sent = AsyncMock(return_value=True)

        result = await email_service.send_single_result_email(
            to_email, original_prompt, method_name, optimized_result, telegram_id
        )

        assert result.success is True
        assert result.message_id == "duplicate_blocked"

    @pytest.mark.asyncio
    async def test_send_single_result_email_failure(self, email_service):
        """Test single result email sending failure."""
        to_email = "user@example.com"
        original_prompt = "Test original prompt"
        method_name = "GGL"
        optimized_result = "Test optimized result"
        telegram_id = 12345

        # Mock email sending failure
        mock_result = EmailDeliveryResult(success=False, error="SMTP error")
        email_service._send_email_with_queue_fallback = AsyncMock(return_value=mock_result)
        email_service._generate_email_hash = MagicMock(return_value="hash123")
        email_service._is_email_already_sent = AsyncMock(return_value=False)

        result = await email_service.send_single_result_email(
            to_email, original_prompt, method_name, optimized_result, telegram_id
        )

        assert result.success is False
        assert "SMTP error" in result.error

    @pytest.mark.asyncio
    async def test_send_single_result_email_without_telegram_id(self, email_service):
        """Test single result email sending without telegram_id (no audit logging)."""
        to_email = "user@example.com"
        original_prompt = "Test original prompt"
        method_name = "CRAFT"
        optimized_result = "Test optimized result"

        # Mock email sending
        mock_result = EmailDeliveryResult(success=True, message_id="test123")
        email_service._send_email_with_queue_fallback = AsyncMock(return_value=mock_result)
        email_service._generate_email_hash = MagicMock(return_value="hash123")
        email_service._is_email_already_sent = AsyncMock(return_value=False)

        result = await email_service.send_single_result_email(
            to_email, original_prompt, method_name, optimized_result
        )

        assert result.success is True
        assert result.message_id == "test123"

    def test_single_result_email_content_generation(self, email_service):
        """Test that single result email content is generated correctly."""
        templates = EmailTemplates("RU")

        original_prompt = "Создай план маркетинга"
        method_name = "CRAFT"
        optimized_result = "Создайте подробный план маркетинга для стартапа..."

        subject, html_body, plain_body = templates.compose_single_result_email(
            original_prompt, method_name, optimized_result
        )

        # Verify subject
        assert "оптимизированный промпт готов" in subject.lower()

        # Verify content is present
        assert original_prompt in html_body
        # Method name is mapped to user-friendly display name (CRAFT -> 🛠 По шагам)
        assert "🛠 По шагам" in html_body
        assert optimized_result in html_body

        assert original_prompt in plain_body
        # Method name is mapped to user-friendly display name (CRAFT -> 🛠 По шагам)
        assert "🛠 По шагам" in plain_body
        assert optimized_result in plain_body

        # Verify HTML structure
        assert "<!DOCTYPE html>" in html_body
        assert "<html" in html_body
        assert "</html>" in html_body

    def test_single_result_email_hash_generation(self, email_service):
        """Test that email hash is generated correctly for single result emails."""
        to_email = "user@example.com"
        subject = "Test Subject"
        content_preview = "SINGLE_RESULT:CRAFT:Test prompt:Test result"

        hash1 = email_service._generate_email_hash(to_email, subject, content_preview)
        hash2 = email_service._generate_email_hash(to_email, subject, content_preview)

        # Same inputs should generate same hash
        assert hash1 == hash2

        # Different inputs should generate different hash
        different_content = "SINGLE_RESULT:LYRA:Different prompt:Different result"
        hash3 = email_service._generate_email_hash(to_email, subject, different_content)
        assert hash1 != hash3


if __name__ == "__main__":
    pytest.main([__file__])
