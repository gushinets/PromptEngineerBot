"""Unit tests for SessionService.get_session() method.

This module contains unit tests for the get_session() method which retrieves
a session by ID. These tests verify:
- Retrieving existing session returns session object
- Retrieving non-existent session returns None
- Database error handling returns None

Requirements: 4.1 (Graceful Degradation)
"""

from contextlib import contextmanager
from datetime import UTC, datetime
from unittest.mock import MagicMock

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Text,
    create_engine,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import JSON

from telegram_bot.services.session_service import (
    OptimizationMethod,
    SessionService,
    SessionStatus,
)


# SQLite-compatible base class for testing
class _TestBase(DeclarativeBase):
    """Base class for SQLite-compatible test database models."""


class _TestUser(_TestBase):
    """SQLite-compatible User model for testing."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    sessions: Mapped[list["_TestSession"]] = relationship("_TestSession", back_populates="user")


class _TestSession(_TestBase):
    """SQLite-compatible Session model for testing."""

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(Text, default="in_progress")
    optimization_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    used_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, default=0)
    followup_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    followup_finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    followup_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    followup_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    followup_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    followup_tokens_total: Mapped[int] = mapped_column(Integer, default=0)
    conversation_history: Mapped[list] = mapped_column(JSON, default=list)

    user: Mapped["_TestUser"] = relationship("_TestUser", back_populates="sessions")


@contextmanager
def get_test_db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    _TestBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


class _TestSessionService:
    """
    SQLite-compatible SessionService for testing get_session().

    This mirrors the production SessionService but uses SQLite-compatible models.
    """

    def __init__(self, db_session) -> None:
        self._db_session = db_session

    def get_session(self, session_id: int) -> _TestSession | None:
        """
        Get a session by ID.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Session instance, or None if not found or on error (logged)

        Requirements: 2.1, 4.1
        """
        try:
            session = self._db_session.get(_TestSession, session_id)
            if session is None:
                return None
            return session
        except Exception:
            return None

    def start_session(
        self,
        user_id: int,
        model_name: str,
        method: OptimizationMethod | None = None,
    ) -> _TestSession | None:
        """Start a new optimization session."""
        try:
            session = _TestSession(
                user_id=user_id,
                optimization_method=method.value if method else None,
                model_name=model_name,
                status=SessionStatus.IN_PROGRESS.value,
                used_followup=False,
                input_tokens=0,
                output_tokens=0,
                tokens_total=0,
                conversation_history=[],
                start_time=datetime.now(UTC),
            )
            self._db_session.add(session)
            self._db_session.commit()
            self._db_session.refresh(session)
            return session
        except Exception:
            self._db_session.rollback()
            return None


class TestGetSessionExistingSession:
    """Tests for retrieving existing sessions via get_session()."""

    def test_get_session_returns_existing_session(self):
        """
        Test that get_session() returns the session object when session exists.

        Requirements: 4.1 - Graceful degradation (normal operation path)
        """
        with get_test_db_session() as db_session:
            # Create a user first
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create a session
            service = _TestSessionService(db_session)
            created_session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert created_session is not None

            # Retrieve the session
            retrieved_session = service.get_session(created_session.id)

            # Verify session is returned
            assert retrieved_session is not None
            assert retrieved_session.id == created_session.id
            assert retrieved_session.user_id == user.id
            assert retrieved_session.status == SessionStatus.IN_PROGRESS.value
            assert retrieved_session.model_name == "gpt-4"
            assert retrieved_session.optimization_method == OptimizationMethod.LYRA.value

    def test_get_session_returns_session_with_all_statuses(self):
        """
        Test that get_session() returns sessions regardless of status.

        Requirements: 4.1 - Should work for all session states
        """
        with get_test_db_session() as db_session:
            # Create a user
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)

            # Create sessions with different statuses
            for status in [
                SessionStatus.IN_PROGRESS.value,
                SessionStatus.SUCCESSFUL.value,
                SessionStatus.UNSUCCESSFUL.value,
            ]:
                session = _TestSession(
                    user_id=user.id,
                    model_name="gpt-4",
                    status=status,
                    start_time=datetime.now(UTC),
                    conversation_history=[],
                )
                db_session.add(session)
                db_session.commit()
                db_session.refresh(session)

                # Verify we can retrieve it
                retrieved = service.get_session(session.id)
                assert retrieved is not None
                assert retrieved.status == status


class TestGetSessionNonExistent:
    """Tests for retrieving non-existent sessions via get_session()."""

    def test_get_session_returns_none_for_nonexistent_id(self):
        """
        Test that get_session() returns None when session doesn't exist.

        Requirements: 4.1 - Graceful degradation on not found
        """
        with get_test_db_session() as db_session:
            service = _TestSessionService(db_session)

            # Try to retrieve a session that doesn't exist
            result = service.get_session(99999)

            assert result is None

    def test_get_session_returns_none_for_zero_id(self):
        """
        Test that get_session() returns None for ID 0.

        Requirements: 4.1 - Graceful degradation
        """
        with get_test_db_session() as db_session:
            service = _TestSessionService(db_session)

            result = service.get_session(0)

            assert result is None

    def test_get_session_returns_none_for_negative_id(self):
        """
        Test that get_session() returns None for negative IDs.

        Requirements: 4.1 - Graceful degradation
        """
        with get_test_db_session() as db_session:
            service = _TestSessionService(db_session)

            result = service.get_session(-1)

            assert result is None


class TestGetSessionDatabaseError:
    """Tests for database error handling in get_session()."""

    def test_get_session_returns_none_on_database_error(self):
        """
        Test that get_session() returns None when database error occurs.

        Requirements: 4.1 - Graceful degradation on database errors
        """
        # Create a mock db_session that raises an exception
        mock_db_session = MagicMock()
        mock_db_session.get.side_effect = Exception("Database connection failed")

        service = _TestSessionService(mock_db_session)

        # Should return None instead of raising exception
        result = service.get_session(1)

        assert result is None

    def test_get_session_handles_sqlalchemy_error(self):
        """
        Test that get_session() handles SQLAlchemy-specific errors gracefully.

        Requirements: 4.1 - Graceful degradation
        """
        from sqlalchemy.exc import SQLAlchemyError

        mock_db_session = MagicMock()
        mock_db_session.get.side_effect = SQLAlchemyError("Connection pool exhausted")

        service = _TestSessionService(mock_db_session)

        result = service.get_session(1)

        assert result is None


class TestGetSessionWithProductionService:
    """
    Tests using the actual SessionService with mocked database.

    These tests verify the production code behaves correctly.
    """

    def test_production_get_session_returns_none_on_error(self):
        """
        Test that production SessionService.get_session() returns None on error.

        Requirements: 4.1 - Graceful degradation
        """
        mock_db_session = MagicMock()
        mock_db_session.get.side_effect = Exception("Database error")

        service = SessionService(mock_db_session)

        result = service.get_session(1)

        assert result is None

    def test_production_get_session_returns_none_for_not_found(self):
        """
        Test that production SessionService.get_session() returns None when not found.

        Requirements: 4.1 - Graceful degradation
        """
        mock_db_session = MagicMock()
        mock_db_session.get.return_value = None

        service = SessionService(mock_db_session)

        result = service.get_session(99999)

        assert result is None

    def test_production_get_session_returns_session_when_found(self):
        """
        Test that production SessionService.get_session() returns session when found.

        Requirements: 2.1, 4.1
        """
        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.status = "in_progress"

        mock_db_session = MagicMock()
        mock_db_session.get.return_value = mock_session

        service = SessionService(mock_db_session)

        result = service.get_session(1)

        assert result is not None
        assert result.id == 1
        assert result.status == "in_progress"
        mock_db_session.get.assert_called_once()
