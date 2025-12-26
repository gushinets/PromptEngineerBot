#!/usr/bin/env python3
"""
Standalone test for audit service functionality.
"""

import os
import sys

import pytest


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from telegram_bot.data.database import AuthEvent, get_db_session, init_database
from telegram_bot.utils.audit_service import (
    init_audit_service,
)


def test_audit_service():
    """Test audit service functionality."""
    print("Testing audit service...")

    # Initialize database
    db_manager = init_database("sqlite:///:memory:")
    db_manager.create_tables()
    print("✓ Database initialized")

    # Initialize audit service
    audit_service = init_audit_service()
    print("✓ Audit service initialized")

    # Test logging an event
    telegram_id = 123456789
    email = "test@example.com"

    result = audit_service.log_otp_sent(telegram_id, email)
    print(f"✓ OTP sent event logged: {result}")

    # Verify event was stored
    with get_db_session() as session:
        event = session.query(AuthEvent).filter(AuthEvent.telegram_id == telegram_id).first()

        if event:
            print(f"✓ Event stored: {event.event_type}, success: {event.success}")
        else:
            pytest.fail("Event not found in database")

    # Test different event types
    audit_service.log_otp_verified(telegram_id, email)
    audit_service.log_email_send_success(telegram_id, email)
    audit_service.log_email_send_failure(telegram_id, email, "SMTP timeout")

    # Get user events
    events = audit_service.get_user_events(telegram_id)
    print(f"✓ Retrieved {len(events)} events for user")

    # Test event counts
    counts = audit_service.get_event_counts()
    print(f"✓ Event counts: {counts}")

    # Test purging (should be 0 since events are recent)
    purged = audit_service.purge_old_events(retention_days=90)
    print(f"✓ Purged {purged} old events")

    print("All tests passed!")


if __name__ == "__main__":
    test_audit_service()
