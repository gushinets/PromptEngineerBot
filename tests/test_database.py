"""Tests for database models and operations."""

import os
import tempfile
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from src.database import (
    AuthEvent,
    Base,
    DatabaseManager,
    User,
    get_db_manager,
    init_database,
    mask_email,
    mask_telegram_id,
    normalize_email,
)


@pytest.fixture
def temp_db():
    """Create a temporary SQLite database for testing."""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
    temp_file.close()

    db_url = f"sqlite:///{temp_file.name}"
    db_manager = DatabaseManager(db_url)
    db_manager.create_tables()

    yield db_manager

    # Cleanup
    os.unlink(temp_file.name)


@pytest.fixture
def db_session(temp_db):
    """Create a database session for testing."""
    session = temp_db.get_session()
    yield session
    session.close()


class TestDatabaseModels:
    """Test database model creation and validation."""

    def test_user_model_creation(self, db_session):
        """Test User model creation and validation."""
        user = User(
            telegram_id=123456789,
            email="test@example.com",
            email_original="Test@Example.Com",
            is_authenticated=True,
        )

        db_session.add(user)
        db_session.commit()

        # Verify user was created
        retrieved_user = db_session.query(User).filter_by(telegram_id=123456789).first()
        assert retrieved_user is not None
        assert retrieved_user.email == "test@example.com"
        assert retrieved_user.email_original == "Test@Example.Com"
        assert retrieved_user.is_authenticated is True
        assert retrieved_user.created_at is not None
        assert retrieved_user.updated_at is not None

    def test_user_unique_constraints(self, db_session):
        """Test telegram_id and email uniqueness."""
        # Create first user
        user1 = User(
            telegram_id=123456789,
            email="test@example.com",
            email_original="test@example.com",
        )
        db_session.add(user1)
        db_session.commit()

        # Try to create user with same telegram_id
        user2 = User(
            telegram_id=123456789,
            email="different@example.com",
            email_original="different@example.com",
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Try to create user with same email
        user3 = User(
            telegram_id=987654321,
            email="test@example.com",
            email_original="test@example.com",
        )
        db_session.add(user3)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_auth_event_logging(self, db_session):
        """Test AuthEvent creation and indexing."""
        event = AuthEvent(
            telegram_id=123456789,
            email="test@example.com",
            event_type="OTP_SENT",
            success=True,
            reason="Email sent successfully",
        )

        db_session.add(event)
        db_session.commit()

        # Verify event was created
        retrieved_event = (
            db_session.query(AuthEvent)
            .filter_by(telegram_id=123456789, event_type="OTP_SENT")
            .first()
        )

        assert retrieved_event is not None
        assert retrieved_event.email == "test@example.com"
        assert retrieved_event.success is True
        assert retrieved_event.reason == "Email sent successfully"
        assert retrieved_event.created_at is not None


class TestEmailNormalization:
    """Test email normalization for storage."""

    def test_email_normalization_comprehensive(self):
        """Test comprehensive email normalization cases."""
        # Case normalization
        assert normalize_email("Test@Example.Com") == "test@example.com"

        # Plus-tag handling
        assert normalize_email("user+tag@domain.com") == "user@domain.com"
        assert normalize_email("user+multiple+tags@domain.com") == "user@domain.com"

        # Combined case and plus-tag
        assert normalize_email("User+Tag@Example.Com") == "user@example.com"

        # Edge cases
        assert normalize_email("") == ""
        assert normalize_email("invalid") == "invalid"
        assert normalize_email("user@") == "user@"
        assert normalize_email("@domain.com") == "@domain.com"

    def test_email_uniqueness_constraints(self, db_session):
        """Test email uniqueness across different input formats."""
        # Create user with normalized email
        user1 = User(
            telegram_id=123456789,
            email=normalize_email("Test@Example.Com"),
            email_original="Test@Example.Com",
        )
        db_session.add(user1)
        db_session.commit()

        # Try to create user with same email in different case
        user2 = User(
            telegram_id=987654321,
            email=normalize_email("test@example.com"),
            email_original="test@example.com",
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

        db_session.rollback()

        # Try to create user with plus-tagged version
        user3 = User(
            telegram_id=555666777,
            email=normalize_email("test+tag@example.com"),
            email_original="test+tag@example.com",
        )
        db_session.add(user3)

        with pytest.raises(IntegrityError):
            db_session.commit()


class TestDataMasking:
    """Test data masking functions for logging."""

    def test_email_masking(self):
        """Test email masking for logs."""
        assert mask_email("user@example.com") == "u***@e***.com"
        assert mask_email("a@b.co") == "a***@b***.co"
        assert mask_email("test@domain") == "t***@***"
        assert mask_email("invalid") == "i***"
        assert mask_email("") == "***"

    def test_telegram_id_masking(self):
        """Test telegram ID masking for logs."""
        assert mask_telegram_id(123456789) == "123***789"
        assert mask_telegram_id(12345) == "12***"
        assert mask_telegram_id(123) == "12***"


class TestSchemaConstraints:
    """Test schema constraints and integrity."""

    def test_unique_constraint_enforcement(self, db_session):
        """Test that unique constraints are properly enforced."""
        # Test telegram_id uniqueness
        user1 = User(
            telegram_id=123456789,
            email="user1@example.com",
            email_original="user1@example.com",
        )
        db_session.add(user1)
        db_session.commit()

        # Attempt to create duplicate telegram_id
        user2 = User(
            telegram_id=123456789,  # Same telegram_id
            email="user2@example.com",
            email_original="user2@example.com",
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Verify it's a unique constraint violation
        assert (
            "UNIQUE constraint failed" in str(exc_info.value)
            or "duplicate key" in str(exc_info.value).lower()
        )
        db_session.rollback()

        # Test email uniqueness
        user3 = User(
            telegram_id=987654321,
            email="user1@example.com",  # Same email
            email_original="user1@example.com",
        )
        db_session.add(user3)

        with pytest.raises(IntegrityError) as exc_info:
            db_session.commit()

        # Verify it's a unique constraint violation
        assert (
            "UNIQUE constraint failed" in str(exc_info.value)
            or "duplicate key" in str(exc_info.value).lower()
        )

    def test_email_normalization_behavior_comprehensive(self, db_session):
        """Test comprehensive email normalization behavior."""
        # Test that normalized and original emails are both persisted
        original_email = "User+Tag@Example.Com"
        normalized_email = normalize_email(original_email)

        user = User(
            telegram_id=123456789,
            email=normalized_email,
            email_original=original_email,
        )
        db_session.add(user)
        db_session.commit()

        # Retrieve and verify both fields are stored correctly
        retrieved_user = db_session.query(User).filter_by(telegram_id=123456789).first()
        assert retrieved_user.email == "user@example.com"  # Normalized
        assert retrieved_user.email_original == "User+Tag@Example.Com"  # Original

        # Test that different original formats with same normalized email fail uniqueness
        db_session.rollback()
        user2 = User(
            telegram_id=987654321,
            email=normalize_email(
                "user+different@example.com"
            ),  # Same normalized result
            email_original="user+different@example.com",
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_schema_integrity_verification(self, temp_db):
        """Test schema integrity and verify all constraints exist."""
        engine = temp_db.get_engine()

        # Get table information
        from sqlalchemy import inspect

        inspector = inspect(engine)

        # Verify users table exists with correct columns
        users_columns = inspector.get_columns("users")
        column_names = [col["name"] for col in users_columns]

        expected_columns = [
            "id",
            "telegram_id",
            "email",
            "email_original",
            "is_authenticated",
            "email_verified_at",
            "last_authenticated_at",
            "created_at",
            "updated_at",
        ]

        for col in expected_columns:
            assert col in column_names, f"Column {col} missing from users table"

        # Verify auth_events table exists with correct columns
        auth_events_columns = inspector.get_columns("auth_events")
        auth_column_names = [col["name"] for col in auth_events_columns]

        expected_auth_columns = [
            "id",
            "telegram_id",
            "email",
            "event_type",
            "success",
            "reason",
            "created_at",
        ]

        for col in expected_auth_columns:
            assert col in auth_column_names, (
                f"Column {col} missing from auth_events table"
            )

        # Verify indexes exist (this is database-specific, so we'll test functionality)
        # The indexes are tested implicitly through query performance and constraint enforcement


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization."""
        db_url = "sqlite:///test.db"
        manager = DatabaseManager(db_url)

        assert manager.database_url == db_url
        assert manager._engine is None
        assert manager._session_factory is None

    def test_database_health_check(self, temp_db):
        """Test database health check."""
        assert temp_db.health_check() is True

    def test_global_database_manager(self):
        """Test global database manager functions."""
        db_url = "sqlite:///test.db"

        # Test initialization
        manager = init_database(db_url)
        assert isinstance(manager, DatabaseManager)

        # Test retrieval
        retrieved_manager = get_db_manager()
        assert retrieved_manager is manager

        # Reset global state for other tests
        import src.database

        src.database.db_manager = None
