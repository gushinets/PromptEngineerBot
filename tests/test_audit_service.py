"""
Tests for audit service functionality.

This module tests comprehensive audit event logging, data masking,
PII protection, and audit event management.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from src.audit_service import (
    AuditEventType,
    AuditService,
    get_audit_service,
    init_audit_service,
)
from src.database import AuthEvent, get_db_session, init_database


@pytest.fixture
def audit_service():
    """Create audit service instance for testing."""
    return AuditService()


@pytest.fixture
def test_database():
    """Create test database with in-memory SQLite."""
    db_manager = init_database("sqlite:///:memory:")
    db_manager.create_tables()
    yield db_manager


class TestAuditService:
    """Test audit service functionality."""

    def test_log_event_success(self, audit_service, test_database):
        """Test successful audit event logging."""
        telegram_id = 123456789
        email = "test@example.com"

        result = audit_service.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_SENT,
            success=True,
            email=email,
        )

        assert result is True

        # Verify event was stored in database
        with get_db_session() as session:
            event = (
                session.query(AuthEvent)
                .filter(AuthEvent.telegram_id == telegram_id)
                .first()
            )

            assert event is not None
            assert event.event_type == "OTP_SENT"
            assert event.success is True
            assert event.email == "test@example.com"  # Normalized
            assert event.reason is None

    def test_log_event_with_reason(self, audit_service, test_database):
        """Test audit event logging with failure reason."""
        telegram_id = 123456789
        email = "test@example.com"
        reason = "invalid_code"

        result = audit_service.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_FAILED,
            success=False,
            email=email,
            reason=reason,
        )

        assert result is True

        # Verify event was stored with reason
        with get_db_session() as session:
            event = (
                session.query(AuthEvent)
                .filter(AuthEvent.telegram_id == telegram_id)
                .first()
            )

            assert event is not None
            assert event.event_type == "OTP_FAILED"
            assert event.success is False
            assert event.reason == reason

    def test_log_event_email_normalization(self, audit_service, test_database):
        """Test email normalization in audit events."""
        telegram_id = 123456789
        email = "Test+Tag@Example.Com"

        result = audit_service.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_SENT,
            success=True,
            email=email,
        )

        assert result is True

        # Verify email was normalized
        with get_db_session() as session:
            event = (
                session.query(AuthEvent)
                .filter(AuthEvent.telegram_id == telegram_id)
                .first()
            )

            assert event is not None
            assert event.email == "test@example.com"  # Normalized

    @patch("src.audit_service.get_db_session")
    def test_log_event_database_error(self, mock_session, audit_service):
        """Test audit event logging handles database errors gracefully."""
        mock_session.side_effect = Exception("Database connection failed")

        result = audit_service.log_event(
            telegram_id=123456789,
            event_type=AuditEventType.OTP_SENT,
            success=True,
            email="test@example.com",
        )

        assert result is False

    def test_log_otp_sent(self, audit_service, test_database):
        """Test OTP sent event logging."""
        telegram_id = 123456789
        email = "test@example.com"

        result = audit_service.log_otp_sent(telegram_id, email)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "OTP_SENT"
            assert event.success is True

    def test_log_otp_verified(self, audit_service, test_database):
        """Test OTP verified event logging."""
        telegram_id = 123456789
        email = "test@example.com"

        result = audit_service.log_otp_verified(telegram_id, email)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "OTP_VERIFIED"
            assert event.success is True

    def test_log_otp_failed(self, audit_service, test_database):
        """Test OTP failed event logging."""
        telegram_id = 123456789
        email = "test@example.com"
        reason = "attempt_limit"

        result = audit_service.log_otp_failed(telegram_id, email, reason)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "OTP_FAILED"
            assert event.success is False
            assert event.reason == reason

    def test_log_otp_expired(self, audit_service, test_database):
        """Test OTP expired event logging."""
        telegram_id = 123456789
        email = "test@example.com"

        result = audit_service.log_otp_expired(telegram_id, email)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "OTP_EXPIRED"
            assert event.success is False
            assert event.reason == "expired"

    def test_log_otp_rate_limited(self, audit_service, test_database):
        """Test OTP rate limited event logging."""
        telegram_id = 123456789
        email = "test@example.com"
        reason = "email_limit_exceeded"

        result = audit_service.log_otp_rate_limited(telegram_id, email, reason)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "OTP_RATE_LIMITED"
            assert event.success is False
            assert event.reason == reason

    def test_log_email_send_success(self, audit_service, test_database):
        """Test email send success event logging."""
        telegram_id = 123456789
        email = "test@example.com"

        result = audit_service.log_email_send_success(telegram_id, email)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "EMAIL_SEND_OK"
            assert event.success is True

    def test_log_email_send_failure(self, audit_service, test_database):
        """Test email send failure event logging with provider error info."""
        telegram_id = 123456789
        email = "test@example.com"
        reason = "SMTP connection timeout"

        result = audit_service.log_email_send_failure(telegram_id, email, reason)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "EMAIL_SEND_FAIL"
            assert event.success is False
            assert event.reason == reason

    def test_log_auth_success(self, audit_service, test_database):
        """Test authentication success event logging."""
        telegram_id = 123456789
        email = "test@example.com"

        result = audit_service.log_auth_success(telegram_id, email)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "AUTH_SUCCESS"
            assert event.success is True

    def test_log_auth_failed(self, audit_service, test_database):
        """Test authentication failed event logging."""
        telegram_id = 123456789
        email = "test@example.com"
        reason = "invalid_credentials"

        result = audit_service.log_auth_failed(telegram_id, email, reason)

        assert result is True

        with get_db_session() as session:
            event = session.query(AuthEvent).first()
            assert event.event_type == "AUTH_FAILED"
            assert event.success is False
            assert event.reason == reason

    def test_log_email_flow_events(self, audit_service, test_database):
        """Test email flow event logging."""
        telegram_id = 123456789
        email = "test@example.com"

        # Test flow start
        result1 = audit_service.log_email_flow_start(telegram_id)
        assert result1 is True

        # Test flow complete
        result2 = audit_service.log_email_flow_complete(telegram_id, email)
        assert result2 is True

        # Test flow timeout
        result3 = audit_service.log_email_flow_timeout(telegram_id, email)
        assert result3 is True

        with get_db_session() as session:
            events = session.query(AuthEvent).order_by(AuthEvent.created_at).all()

            assert len(events) == 3
            assert events[0].event_type == "EMAIL_FLOW_START"
            assert events[1].event_type == "EMAIL_FLOW_COMPLETE"
            assert events[2].event_type == "EMAIL_FLOW_TIMEOUT"

    def test_get_user_events(self, audit_service, test_database):
        """Test retrieving user events."""
        telegram_id = 123456789
        email = "test@example.com"

        # Create multiple events
        audit_service.log_otp_sent(telegram_id, email)
        audit_service.log_otp_verified(telegram_id, email)
        audit_service.log_email_send_success(telegram_id, email)

        events = audit_service.get_user_events(telegram_id)

        assert len(events) == 3
        assert all(event.telegram_id == telegram_id for event in events)

        # Test with event type filter
        otp_events = audit_service.get_user_events(
            telegram_id, event_type=AuditEventType.OTP_SENT
        )

        assert len(otp_events) == 1
        assert otp_events[0].event_type == "OTP_SENT"

    def test_get_email_events(self, audit_service, test_database):
        """Test retrieving email events."""
        telegram_id = 123456789
        email = "test@example.com"

        # Create multiple events
        audit_service.log_otp_sent(telegram_id, email)
        audit_service.log_email_send_success(telegram_id, email)

        events = audit_service.get_email_events(email)

        assert len(events) == 2
        assert all(event.email == email for event in events)

    def test_get_email_events_normalization(self, audit_service, test_database):
        """Test email events retrieval with normalization."""
        telegram_id = 123456789
        original_email = "Test+Tag@Example.Com"
        normalized_email = "test@example.com"

        # Create event with original email
        audit_service.log_otp_sent(telegram_id, original_email)

        # Retrieve with normalized email
        events = audit_service.get_email_events(normalized_email)

        assert len(events) == 1
        assert events[0].email == normalized_email

    def test_get_event_counts(self, audit_service, test_database):
        """Test event counts retrieval."""
        telegram_id = 123456789
        email = "test@example.com"

        # Create multiple events
        audit_service.log_otp_sent(telegram_id, email)
        audit_service.log_otp_sent(telegram_id, email)
        audit_service.log_otp_verified(telegram_id, email)
        audit_service.log_email_send_success(telegram_id, email)

        counts = audit_service.get_event_counts()

        assert counts["OTP_SENT"] == 2
        assert counts["OTP_VERIFIED"] == 1
        assert counts["EMAIL_SEND_OK"] == 1

    def test_get_event_counts_date_range(self, audit_service, test_database):
        """Test event counts with date range filtering."""
        telegram_id = 123456789
        email = "test@example.com"

        # Create event
        audit_service.log_otp_sent(telegram_id, email)

        # Test with future date range (should return 0)
        from datetime import timezone

        future_start = datetime.now(timezone.utc) + timedelta(days=1)
        future_end = datetime.now(timezone.utc) + timedelta(days=2)

        counts = audit_service.get_event_counts(future_start, future_end)

        assert len(counts) == 0

    def test_purge_old_events(self, audit_service, test_database):
        """Test purging old audit events."""
        telegram_id = 123456789
        email = "test@example.com"

        # Create old event by manually setting created_at
        with get_db_session() as session:
            old_event = AuthEvent(
                telegram_id=telegram_id,
                email=email,
                event_type="OTP_SENT",
                success=True,
                created_at=datetime.now(timezone.utc) - timedelta(days=100),
            )
            session.add(old_event)
            session.commit()

        # Create recent event
        audit_service.log_otp_verified(telegram_id, email)

        # Purge events older than 90 days
        purged_count = audit_service.purge_old_events(retention_days=90)

        assert purged_count == 1

        # Verify only recent event remains
        with get_db_session() as session:
            remaining_events = session.query(AuthEvent).all()
            assert len(remaining_events) == 1
            assert remaining_events[0].event_type == "OTP_VERIFIED"

    def test_purge_old_events_no_events(self, audit_service, test_database):
        """Test purging when no old events exist."""
        purged_count = audit_service.purge_old_events(retention_days=90)

        assert purged_count == 0

    @patch("src.audit_service.get_db_session")
    def test_purge_old_events_database_error(self, mock_session, audit_service):
        """Test purge old events handles database errors gracefully."""
        mock_session.side_effect = Exception("Database connection failed")

        purged_count = audit_service.purge_old_events(retention_days=90)

        assert purged_count == 0


class TestAuditServiceGlobal:
    """Test global audit service management."""

    def test_init_audit_service(self):
        """Test audit service initialization."""
        service = init_audit_service()

        assert isinstance(service, AuditService)
        assert get_audit_service() is service

    def test_get_audit_service_not_initialized(self):
        """Test getting audit service when not initialized."""
        # Reset global service
        import src.audit_service

        src.audit_service.audit_service = None

        with pytest.raises(RuntimeError, match="Audit service not initialized"):
            get_audit_service()


class TestDataMasking:
    """Test data masking and PII protection."""

    @patch("logging.getLogger")
    def test_data_masking_in_logs(self, mock_get_logger, audit_service, test_database):
        """Test that sensitive data is properly masked in logs."""
        telegram_id = 123456789
        email = "test@example.com"

        # Set up the mock logger
        mock_logger = mock_get_logger.return_value

        # Replace the audit service logger with our mock
        audit_service.logger = mock_logger

        result = audit_service.log_otp_sent(telegram_id, email)

        # Verify the method returned True (success)
        assert result is True

        # Verify logger was called with masked data
        mock_logger.info.assert_called()
        log_message = mock_logger.info.call_args[0][0]

        # Should contain masked telegram ID and email
        assert "123***789" in log_message
        assert "t***@e***.com" in log_message

        # Should not contain original sensitive data
        assert str(telegram_id) not in log_message
        assert email not in log_message

    def test_database_stores_unmasked_data(self, audit_service, test_database):
        """Test that database stores unmasked data for proper functionality."""
        telegram_id = 123456789
        email = "test@example.com"

        audit_service.log_otp_sent(telegram_id, email)

        # Verify database contains unmasked data
        with get_db_session() as session:
            event = session.query(AuthEvent).first()

            assert event.telegram_id == telegram_id
            assert event.email == email  # Normalized but not masked
