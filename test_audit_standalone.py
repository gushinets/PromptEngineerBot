#!/usr/bin/env python3
"""
Standalone test for audit service functionality.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.audit_service import AuditEventType, AuditService, init_audit_service
from src.database import AuthEvent, get_db_session, init_database


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
        event = (
            session.query(AuthEvent)
            .filter(AuthEvent.telegram_id == telegram_id)
            .first()
        )

        if event:
            print(f"✓ Event stored: {event.event_type}, success: {event.success}")
        else:
            print("✗ Event not found in database")
            return False

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
    return True


if __name__ == "__main__":
    try:
        success = test_audit_service()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
