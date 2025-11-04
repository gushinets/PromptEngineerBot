"""
Audit service for comprehensive event logging and audit trail management.

This module provides audit logging functionality for all authentication and email events,
ensuring proper data masking and PII protection while maintaining comprehensive audit trails.
"""

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional

from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError

from telegram_bot.data.database import (
    AuthEvent,
    get_db_session,
    mask_email,
    mask_telegram_id,
)

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Enumeration of audit event types for consistent logging."""

    # OTP Events
    OTP_SENT = "OTP_SENT"
    OTP_VERIFIED = "OTP_VERIFIED"
    OTP_FAILED = "OTP_FAILED"
    OTP_EXPIRED = "OTP_EXPIRED"
    OTP_RATE_LIMITED = "OTP_RATE_LIMITED"

    # Email Events
    EMAIL_SEND_OK = "EMAIL_SEND_OK"
    EMAIL_SEND_FAIL = "EMAIL_SEND_FAIL"

    # Authentication Events
    AUTH_SUCCESS = "AUTH_SUCCESS"
    AUTH_FAILED = "AUTH_FAILED"

    # Flow Events
    EMAIL_FLOW_START = "EMAIL_FLOW_START"
    EMAIL_FLOW_COMPLETE = "EMAIL_FLOW_COMPLETE"
    EMAIL_FLOW_TIMEOUT = "EMAIL_FLOW_TIMEOUT"


class AuditService:
    """Service for logging audit events with proper data masking and PII protection."""

    def __init__(self):
        """Initialize audit service."""
        self.logger = logging.getLogger(f"{__name__}.AuditService")

    def log_event(
        self,
        telegram_id: int,
        event_type: AuditEventType,
        success: bool,
        email: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Log an audit event to the database with proper data masking.

        Args:
            telegram_id: User's telegram ID
            event_type: Type of event being logged
            success: Whether the event was successful
            email: User's email (will be masked in logs)
            reason: Optional reason for failure or additional context

        Returns:
            bool: True if event was logged successfully, False otherwise
        """
        try:
            # Normalize email for storage (but don't mask for database)
            normalized_email = None
            if email:
                from telegram_bot.data.database import normalize_email

                normalized_email = normalize_email(email)

            # Create audit event
            with get_db_session() as session:
                audit_event = AuthEvent(
                    telegram_id=telegram_id,
                    email=normalized_email,
                    event_type=event_type.value,
                    success=success,
                    reason=reason,
                    created_at=datetime.now(timezone.utc),
                )

                session.add(audit_event)
                session.commit()

                # Log to application logs with masked data
                masked_tg_id = mask_telegram_id(telegram_id)
                masked_email = mask_email(email) if email else None

                log_message = f"AUDIT_EVENT: {event_type.value} for user {masked_tg_id}"
                if masked_email:
                    log_message += f" email {masked_email}"
                log_message += f" success={success}"
                if reason:
                    log_message += f" reason='{reason}'"

                if success:
                    self.logger.info(log_message)
                else:
                    self.logger.warning(log_message)

                return True

        except SQLAlchemyError as e:
            self.logger.error(
                f"Failed to log audit event {event_type.value} for user "
                f"{mask_telegram_id(telegram_id)}: {e}"
            )
            return False
        except Exception as e:
            self.logger.error(
                f"Unexpected error logging audit event {event_type.value} for user "
                f"{mask_telegram_id(telegram_id)}: {e}"
            )
            return False

    def log_otp_sent(self, telegram_id: int, email: str) -> bool:
        """Log OTP sent event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_SENT,
            success=True,
            email=email,
        )

    def log_otp_verified(self, telegram_id: int, email: str) -> bool:
        """Log successful OTP verification event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_VERIFIED,
            success=True,
            email=email,
        )

    def log_otp_failed(
        self, telegram_id: int, email: str, reason: str = "invalid_code"
    ) -> bool:
        """Log failed OTP verification event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_FAILED,
            success=False,
            email=email,
            reason=reason,
        )

    def log_otp_expired(self, telegram_id: int, email: str) -> bool:
        """Log expired OTP event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_EXPIRED,
            success=False,
            email=email,
            reason="expired",
        )

    def log_otp_rate_limited(self, telegram_id: int, email: str, reason: str) -> bool:
        """Log OTP rate limiting event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.OTP_RATE_LIMITED,
            success=False,
            email=email,
            reason=reason,
        )

    def log_email_send_success(self, telegram_id: int, email: str) -> bool:
        """Log successful email delivery event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.EMAIL_SEND_OK,
            success=True,
            email=email,
        )

    def log_email_send_failure(self, telegram_id: int, email: str, reason: str) -> bool:
        """Log failed email delivery event with provider error info."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.EMAIL_SEND_FAIL,
            success=False,
            email=email,
            reason=reason,
        )

    def log_auth_success(self, telegram_id: int, email: str) -> bool:
        """Log successful authentication event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.AUTH_SUCCESS,
            success=True,
            email=email,
        )

    def log_auth_failed(self, telegram_id: int, email: str, reason: str) -> bool:
        """Log failed authentication event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.AUTH_FAILED,
            success=False,
            email=email,
            reason=reason,
        )

    def log_email_flow_start(self, telegram_id: int) -> bool:
        """Log email flow initiation event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.EMAIL_FLOW_START,
            success=True,
        )

    def log_email_flow_complete(self, telegram_id: int, email: str) -> bool:
        """Log email flow completion event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.EMAIL_FLOW_COMPLETE,
            success=True,
            email=email,
        )

    def log_email_flow_timeout(self, telegram_id: int, email: str) -> bool:
        """Log email flow timeout event."""
        return self.log_event(
            telegram_id=telegram_id,
            event_type=AuditEventType.EMAIL_FLOW_TIMEOUT,
            success=False,
            email=email,
            reason="timeout",
        )

    def get_user_events(
        self,
        telegram_id: int,
        limit: int = 100,
        event_type: Optional[AuditEventType] = None,
    ) -> list[AuthEvent]:
        """
        Get audit events for a specific user.

        Args:
            telegram_id: User's telegram ID
            limit: Maximum number of events to return
            event_type: Optional filter by event type

        Returns:
            List of AuthEvent objects
        """
        try:
            with get_db_session() as session:
                query = session.query(AuthEvent).filter(
                    AuthEvent.telegram_id == telegram_id
                )

                if event_type:
                    query = query.filter(AuthEvent.event_type == event_type.value)

                events = query.order_by(AuthEvent.created_at.desc()).limit(limit).all()

                return events

        except SQLAlchemyError as e:
            self.logger.error(
                f"Failed to get user events for {mask_telegram_id(telegram_id)}: {e}"
            )
            return []

    def get_email_events(
        self, email: str, limit: int = 100, event_type: Optional[AuditEventType] = None
    ) -> list[AuthEvent]:
        """
        Get audit events for a specific email.

        Args:
            email: Email address (will be normalized)
            limit: Maximum number of events to return
            event_type: Optional filter by event type

        Returns:
            List of AuthEvent objects
        """
        try:
            from telegram_bot.data.database import normalize_email

            normalized_email = normalize_email(email)

            with get_db_session() as session:
                query = session.query(AuthEvent).filter(
                    AuthEvent.email == normalized_email
                )

                if event_type:
                    query = query.filter(AuthEvent.event_type == event_type.value)

                events = query.order_by(AuthEvent.created_at.desc()).limit(limit).all()

                return events

        except SQLAlchemyError as e:
            self.logger.error(
                f"Failed to get email events for {mask_email(email)}: {e}"
            )
            return []

    def get_event_counts(
        self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
    ) -> dict[str, int]:
        """
        Get event counts by type for a date range.

        Args:
            start_date: Start date for filtering (default: 24 hours ago)
            end_date: End date for filtering (default: now)

        Returns:
            Dictionary with event type counts
        """
        try:
            if start_date is None:
                start_date = datetime.now(timezone.utc) - timedelta(days=1)
            if end_date is None:
                end_date = datetime.now(timezone.utc)

            with get_db_session() as session:
                results = (
                    session.query(
                        AuthEvent.event_type, func.count(AuthEvent.id).label("count")
                    )
                    .filter(
                        and_(
                            AuthEvent.created_at >= start_date,
                            AuthEvent.created_at <= end_date,
                        )
                    )
                    .group_by(AuthEvent.event_type)
                    .all()
                )

                return {result.event_type: result.count for result in results}

        except SQLAlchemyError as e:
            self.logger.error(f"Failed to get event counts: {e}")
            return {}

    def purge_old_events(self, retention_days: int = 90) -> int:
        """
        Purge audit events older than retention period.

        Args:
            retention_days: Number of days to retain events

        Returns:
            Number of events purged
        """
        try:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)

            with get_db_session() as session:
                # Count events to be purged
                count_query = session.query(func.count(AuthEvent.id)).filter(
                    AuthEvent.created_at < cutoff_date
                )
                events_to_purge = count_query.scalar()

                if events_to_purge == 0:
                    self.logger.info("No audit events to purge")
                    return 0

                # Delete old events
                deleted_count = (
                    session.query(AuthEvent)
                    .filter(AuthEvent.created_at < cutoff_date)
                    .delete()
                )

                session.commit()

                self.logger.info(
                    f"Purged {deleted_count} audit events older than {retention_days} days"
                )

                return deleted_count

        except (SQLAlchemyError, Exception) as e:
            self.logger.error(f"Failed to purge old audit events: {e}")
            return 0


# Global audit service instance
audit_service: Optional[AuditService] = None


def init_audit_service() -> AuditService:
    """
    Initialize global audit service.

    Returns:
        AuditService instance
    """
    global audit_service
    audit_service = AuditService()
    return audit_service


def get_audit_service() -> AuditService:
    """
    Get the global audit service instance.

    Returns:
        AuditService instance

    Raises:
        RuntimeError: If audit service is not initialized
    """
    if audit_service is None:
        raise RuntimeError(
            "Audit service not initialized. Call init_audit_service() first."
        )
    return audit_service
