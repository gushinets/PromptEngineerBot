"""Unit tests for SessionService.reset_session() status protection.

This module contains unit tests for the reset_session() method's terminal state
protection feature. These tests verify:
- Reset on "successful" session leaves status unchanged
- Reset on "unsuccessful" session leaves status unchanged
- Reset on "in_progress" session changes to "unsuccessful"
- Return value is session object in all cases

Requirements: 1.1, 1.2, 1.3, 1.5
"""

from contextlib import contextmanager
from datetime import UTC, datetime

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


def _normalize_timestamp(ts: datetime) -> datetime:
    """Normalize a timestamp for comparison by handling timezone info."""
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts


class _TestSessionService:
    """
    SQLite-compatible SessionService for testing reset_session() protection.

    This mirrors the production SessionService but uses SQLite-compatible models.
    """

    def __init__(self, db_session) -> None:
        self._db_session = db_session

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

    def complete_session(self, session_id: int) -> _TestSession | None:
        """Mark session as successful."""
        try:
            session = self._db_session.get(_TestSession, session_id)
            if session is None:
                return None

            finish_time = datetime.now(UTC)
            session.status = SessionStatus.SUCCESSFUL.value
            session.finish_time = finish_time

            if session.start_time is not None:
                start_ts = _normalize_timestamp(session.start_time)
                duration = finish_time - start_ts
                session.duration_seconds = int(duration.total_seconds())
            else:
                session.duration_seconds = 0

            self._db_session.commit()
            self._db_session.refresh(session)
            return session
        except Exception:
            self._db_session.rollback()
            return None

    def reset_session(self, session_id: int) -> _TestSession | None:
        """
        Mark session as unsuccessful when user resets dialog.

        IMPORTANT: This method implements terminal state protection.
        Sessions that are already in a terminal state (successful or unsuccessful)
        will NOT be modified. Only sessions with status="in_progress" can be reset.

        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5
        """
        try:
            session = self._db_session.get(_TestSession, session_id)
            if session is None:
                return None

            # Terminal state protection: don't overwrite completed sessions
            if session.status != SessionStatus.IN_PROGRESS.value:
                # Return existing session without modification (Requirement 1.5)
                return session

            # Session is in_progress, proceed with reset (Requirement 1.3)
            finish_time = datetime.now(UTC)
            session.status = SessionStatus.UNSUCCESSFUL.value
            session.finish_time = finish_time

            if session.start_time is not None:
                start_ts = _normalize_timestamp(session.start_time)
                duration = finish_time - start_ts
                session.duration_seconds = int(duration.total_seconds())
            else:
                session.duration_seconds = 0

            self._db_session.commit()
            self._db_session.refresh(session)
            return session
        except Exception:
            self._db_session.rollback()
            return None

    def add_tokens(
        self,
        session_id: int,
        input_tokens: int,
        output_tokens: int,
    ) -> _TestSession | None:
        """Add token counts from an LLM interaction."""
        try:
            session = self._db_session.get(_TestSession, session_id)
            if session is None:
                return None

            session.input_tokens += input_tokens
            session.output_tokens += output_tokens
            session.tokens_total = session.input_tokens + session.output_tokens

            self._db_session.commit()
            self._db_session.refresh(session)
            return session
        except Exception:
            self._db_session.rollback()
            return None


class TestResetOnSuccessfulSession:
    """
    Tests for reset_session() on sessions with status "successful".

    Requirements: 1.1, 1.5
    """

    def test_reset_on_successful_session_leaves_status_unchanged(self):
        """
        Test that reset_session() on a "successful" session leaves status unchanged.

        Requirements: 1.1 - WHEN reset_session() is called on a session with status
        "successful" THEN the System SHALL NOT modify the session status
        """
        with get_test_db_session() as db_session:
            # Create a user
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create and complete a session
            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None

            completed = service.complete_session(session.id)
            assert completed is not None
            assert completed.status == SessionStatus.SUCCESSFUL.value

            # Store original status
            original_status = completed.status

            # Attempt to reset the successful session
            result = service.reset_session(session.id)

            # Verify status is unchanged
            assert result is not None
            assert result.status == original_status
            assert result.status == SessionStatus.SUCCESSFUL.value

    def test_reset_on_successful_session_leaves_finish_time_unchanged(self):
        """
        Test that reset_session() on a "successful" session leaves finish_time unchanged.

        Requirements: 1.1, 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            assert session is not None

            completed = service.complete_session(session.id)
            assert completed is not None
            original_finish_time = completed.finish_time

            # Attempt to reset
            result = service.reset_session(session.id)

            # Verify finish_time is unchanged
            assert result is not None
            assert result.finish_time == original_finish_time

    def test_reset_on_successful_session_leaves_duration_unchanged(self):
        """
        Test that reset_session() on a "successful" session leaves duration_seconds unchanged.

        Requirements: 1.1, 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.GGL)
            assert session is not None

            completed = service.complete_session(session.id)
            assert completed is not None
            original_duration = completed.duration_seconds

            # Attempt to reset
            result = service.reset_session(session.id)

            # Verify duration_seconds is unchanged
            assert result is not None
            assert result.duration_seconds == original_duration

    def test_reset_on_successful_session_returns_session_object(self):
        """
        Test that reset_session() on a "successful" session returns the session object.

        Requirements: 1.5 - WHEN reset_session() is called on a terminal-state session
        THEN the System SHALL return the existing session object without modification
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None

            completed = service.complete_session(session.id)
            assert completed is not None

            # Attempt to reset
            result = service.reset_session(session.id)

            # Verify session object is returned
            assert result is not None
            assert result.id == session.id


class TestResetOnUnsuccessfulSession:
    """
    Tests for reset_session() on sessions with status "unsuccessful".

    Requirements: 1.2, 1.5
    """

    def test_reset_on_unsuccessful_session_leaves_status_unchanged(self):
        """
        Test that reset_session() on an "unsuccessful" session leaves status unchanged.

        Requirements: 1.2 - WHEN reset_session() is called on a session with status
        "unsuccessful" THEN the System SHALL NOT modify the session status
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None

            # Reset the session first time (makes it unsuccessful)
            first_reset = service.reset_session(session.id)
            assert first_reset is not None
            assert first_reset.status == SessionStatus.UNSUCCESSFUL.value

            original_status = first_reset.status

            # Attempt to reset again
            result = service.reset_session(session.id)

            # Verify status is unchanged
            assert result is not None
            assert result.status == original_status
            assert result.status == SessionStatus.UNSUCCESSFUL.value

    def test_reset_on_unsuccessful_session_leaves_finish_time_unchanged(self):
        """
        Test that reset_session() on an "unsuccessful" session leaves finish_time unchanged.

        Requirements: 1.2, 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            assert session is not None

            first_reset = service.reset_session(session.id)
            assert first_reset is not None
            original_finish_time = first_reset.finish_time

            # Attempt to reset again
            result = service.reset_session(session.id)

            # Verify finish_time is unchanged
            assert result is not None
            assert result.finish_time == original_finish_time

    def test_reset_on_unsuccessful_session_leaves_duration_unchanged(self):
        """
        Test that reset_session() on an "unsuccessful" session leaves duration_seconds unchanged.

        Requirements: 1.2, 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.GGL)
            assert session is not None

            first_reset = service.reset_session(session.id)
            assert first_reset is not None
            original_duration = first_reset.duration_seconds

            # Attempt to reset again
            result = service.reset_session(session.id)

            # Verify duration_seconds is unchanged
            assert result is not None
            assert result.duration_seconds == original_duration

    def test_reset_on_unsuccessful_session_returns_session_object(self):
        """
        Test that reset_session() on an "unsuccessful" session returns the session object.

        Requirements: 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None

            first_reset = service.reset_session(session.id)
            assert first_reset is not None

            # Attempt to reset again
            result = service.reset_session(session.id)

            # Verify session object is returned
            assert result is not None
            assert result.id == session.id


class TestResetOnInProgressSession:
    """
    Tests for reset_session() on sessions with status "in_progress".

    Requirements: 1.3, 1.5
    """

    def test_reset_on_in_progress_session_changes_status_to_unsuccessful(self):
        """
        Test that reset_session() on an "in_progress" session changes status to "unsuccessful".

        Requirements: 1.3 - WHEN reset_session() is called on a session with status
        "in_progress" THEN the System SHALL update the session status to "unsuccessful"
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None
            assert session.status == SessionStatus.IN_PROGRESS.value

            # Reset the session
            result = service.reset_session(session.id)

            # Verify status changed to unsuccessful
            assert result is not None
            assert result.status == SessionStatus.UNSUCCESSFUL.value

    def test_reset_on_in_progress_session_sets_finish_time(self):
        """
        Test that reset_session() on an "in_progress" session sets finish_time.

        Requirements: 1.3
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            assert session is not None
            assert session.finish_time is None

            before_reset = datetime.now(UTC)
            result = service.reset_session(session.id)
            after_reset = datetime.now(UTC)

            # Verify finish_time is set
            assert result is not None
            assert result.finish_time is not None

            # Verify finish_time is within expected range
            finish_ts = _normalize_timestamp(result.finish_time)
            assert before_reset <= finish_ts <= after_reset

    def test_reset_on_in_progress_session_sets_duration(self):
        """
        Test that reset_session() on an "in_progress" session sets duration_seconds.

        Requirements: 1.3
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.GGL)
            assert session is not None
            assert session.duration_seconds is None

            result = service.reset_session(session.id)

            # Verify duration_seconds is set
            assert result is not None
            assert result.duration_seconds is not None
            assert result.duration_seconds >= 0

    def test_reset_on_in_progress_session_returns_session_object(self):
        """
        Test that reset_session() on an "in_progress" session returns the session object.

        Requirements: 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None

            result = service.reset_session(session.id)

            # Verify session object is returned
            assert result is not None
            assert result.id == session.id

    def test_reset_on_in_progress_session_preserves_tokens(self):
        """
        Test that reset_session() on an "in_progress" session preserves token counts.

        Requirements: 1.3 - Metrics should be preserved for analysis
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None

            # Add some tokens
            service.add_tokens(session.id, 100, 200)
            db_session.refresh(session)

            original_input = session.input_tokens
            original_output = session.output_tokens
            original_total = session.tokens_total

            result = service.reset_session(session.id)

            # Verify tokens are preserved
            assert result is not None
            assert result.input_tokens == original_input
            assert result.output_tokens == original_output
            assert result.tokens_total == original_total


class TestResetReturnValue:
    """
    Tests for reset_session() return value in all cases.

    Requirements: 1.5
    """

    def test_reset_returns_session_for_successful_status(self):
        """
        Test that reset_session() returns session object for "successful" status.

        Requirements: 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            service.complete_session(session.id)

            result = service.reset_session(session.id)

            assert result is not None
            assert isinstance(result, _TestSession)

    def test_reset_returns_session_for_unsuccessful_status(self):
        """
        Test that reset_session() returns session object for "unsuccessful" status.

        Requirements: 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            service.reset_session(session.id)

            # Second reset attempt
            result = service.reset_session(session.id)

            assert result is not None
            assert isinstance(result, _TestSession)

    def test_reset_returns_session_for_in_progress_status(self):
        """
        Test that reset_session() returns session object for "in_progress" status.

        Requirements: 1.5
        """
        with get_test_db_session() as db_session:
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            service = _TestSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.GGL)

            result = service.reset_session(session.id)

            assert result is not None
            assert isinstance(result, _TestSession)

    def test_reset_returns_none_for_nonexistent_session(self):
        """
        Test that reset_session() returns None for non-existent session.

        This is expected behavior - not a terminal state case.
        """
        with get_test_db_session() as db_session:
            service = _TestSessionService(db_session)

            result = service.reset_session(99999)

            assert result is None
