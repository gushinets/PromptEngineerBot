"""Property-based tests for session tracking feature.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document.

Note: SQLite (used for testing) does not preserve timezone information in datetime
columns. PostgreSQL (used in production) does preserve timezone info. These tests
verify the property holds when timezone info is properly set, acknowledging that
SQLite may strip timezone info during storage/retrieval.

Note: SQLite does not support JSONB type. For testing, we create a test-specific
database schema that uses JSON instead of JSONB for the conversation_history field.
"""

from contextlib import contextmanager
from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st
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


# SQLite-compatible base class for testing (prefixed with _ to avoid pytest collection)
class _SQLiteBase(DeclarativeBase):
    """Base class for SQLite-compatible test database models."""


class _SQLiteUser(_SQLiteBase):
    """SQLite-compatible User model for testing."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    # Relationship to sessions
    sessions: Mapped[list["_SQLiteSession"]] = relationship("_SQLiteSession", back_populates="user")


class _SQLiteSession(_SQLiteBase):
    """
    SQLite-compatible Session model for testing.

    Uses JSON instead of JSONB for conversation_history to work with SQLite.
    """

    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Timing fields
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)

    # Status field
    status: Mapped[str] = mapped_column(Text, default="in_progress")

    # Optimization method and model
    optimization_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    used_followup: Mapped[bool] = mapped_column(Boolean, default=False)

    # Token metrics (cumulative)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    tokens_total: Mapped[int] = mapped_column(Integer, default=0)

    # Conversation history as JSON (SQLite compatible)
    conversation_history: Mapped[list] = mapped_column(JSON, default=list)

    # Relationships
    user: Mapped["_SQLiteUser"] = relationship("_SQLiteUser", back_populates="sessions")
    email_events: Mapped[list["_SQLiteSessionEmailEvent"]] = relationship(
        "_SQLiteSessionEmailEvent", back_populates="session", cascade="all, delete-orphan"
    )


class _SQLiteSessionEmailEvent(_SQLiteBase):
    """
    SQLite-compatible SessionEmailEvent model for testing.

    Records each email sent containing an optimized prompt, linked to the
    session that generated it.
    """

    __tablename__ = "session_email_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)

    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    recipient_email: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_status: Mapped[str] = mapped_column(Text, nullable=False)

    # Relationship
    session: Mapped["_SQLiteSession"] = relationship(
        "_SQLiteSession", back_populates="email_events"
    )


class _SQLiteSessionService:
    """
    SQLite-compatible SessionService for testing.

    This mirrors the production SessionService but uses SQLite-compatible models.
    """

    def __init__(self, db_session) -> None:
        self._db_session = db_session

    def start_session(
        self,
        user_id: int,
        model_name: str,
        method: OptimizationMethod | None = None,
    ) -> _SQLiteSession | None:
        """Start a new optimization session with correct defaults."""
        try:
            session = _SQLiteSession(
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

    def complete_session(self, session_id: int) -> _SQLiteSession | None:
        """
        Mark session as successful when improved prompt is delivered.

        Sets status to SUCCESSFUL, finish_time to current UTC timestamp,
        and calculates duration_seconds.
        """
        try:
            session = self._db_session.get(_SQLiteSession, session_id)
            if session is None:
                return None

            finish_time = datetime.now(UTC)
            session.status = SessionStatus.SUCCESSFUL.value
            session.finish_time = finish_time

            # Calculate duration in seconds
            if session.start_time is not None:
                # Normalize start_time for calculation (SQLite may strip timezone)
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

    def reset_session(self, session_id: int) -> _SQLiteSession | None:
        """
        Mark session as unsuccessful when user resets dialog.

        Sets status to UNSUCCESSFUL, finish_time to current UTC timestamp.
        Preserves all collected metrics (tokens, method, conversation) for analysis.
        """
        try:
            session = self._db_session.get(_SQLiteSession, session_id)
            if session is None:
                return None

            finish_time = datetime.now(UTC)
            session.status = SessionStatus.UNSUCCESSFUL.value
            session.finish_time = finish_time

            # Calculate duration in seconds
            if session.start_time is not None:
                start_ts = _normalize_timestamp(session.start_time)
                duration = finish_time - start_ts
                session.duration_seconds = int(duration.total_seconds())
            else:
                session.duration_seconds = 0

            # Note: All metrics (input_tokens, output_tokens, tokens_total,
            # optimization_method, used_followup, conversation_history) are
            # preserved - we only update status, finish_time, and duration_seconds

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
    ) -> _SQLiteSession | None:
        """
        Add token counts from an LLM interaction.

        Accumulates to existing counts, recalculates total.
        """
        try:
            session = self._db_session.get(_SQLiteSession, session_id)
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

    def set_followup_used(self, session_id: int) -> _SQLiteSession | None:
        """Mark that FOLLOWUP optimization was used in this session."""
        try:
            session = self._db_session.get(_SQLiteSession, session_id)
            if session is None:
                return None

            session.used_followup = True

            self._db_session.commit()
            self._db_session.refresh(session)
            return session
        except Exception:
            self._db_session.rollback()
            return None

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        method: str | None = None,
    ) -> _SQLiteSession | None:
        """
        Add a message to the session's conversation history (JSON).

        Appends a message object with role, content, and ISO8601 timestamp
        to the session's conversation_history JSON field.

        Args:
            session_id: ID of the session to add message to
            role: Message role - "user" or "assistant"
            content: Message content text
            method: Optional optimization method that produced this response
                    (LYRA, CRAFT, GGL). Used for email flow attribution.

        Returns:
            Updated Session instance, or None on error
        """
        try:
            session = self._db_session.get(_SQLiteSession, session_id)
            if session is None:
                return None

            # Create message object with ISO8601 timestamp
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.now(UTC).isoformat(),
            }

            # Add method attribution if provided (for email flow)
            if method:
                message["method"] = method

            # Append to conversation history
            # Need to create a new list to trigger SQLAlchemy change detection for JSON
            current_history = session.conversation_history or []
            session.conversation_history = [*current_history, message]

            self._db_session.commit()
            self._db_session.refresh(session)
            return session
        except Exception:
            self._db_session.rollback()
            return None

    def log_email_sent(
        self,
        session_id: int,
        recipient_email: str,
        delivery_status: str,
    ) -> _SQLiteSessionEmailEvent | None:
        """
        Log an email delivery event for the session.

        Creates a SessionEmailEvent record linked to the session to track
        email deliveries of optimized prompts.
        """
        try:
            # Verify the session exists
            session = self._db_session.get(_SQLiteSession, session_id)
            if session is None:
                return None

            # Create the email event record
            email_event = _SQLiteSessionEmailEvent(
                session_id=session_id,
                recipient_email=recipient_email,
                delivery_status=delivery_status,
            )
            self._db_session.add(email_event)
            self._db_session.commit()
            self._db_session.refresh(email_event)

            return email_event
        except Exception:
            self._db_session.rollback()
            return None

    def get_user_current_session(self, user_id: int) -> _SQLiteSession | None:
        """
        Get the current in-progress session for a user, if any.

        Queries for a session with the given user_id and status="in_progress".
        There should be at most one active session per user at any time.
        """
        try:
            session = (
                self._db_session.query(_SQLiteSession)
                .filter(
                    _SQLiteSession.user_id == user_id,
                    _SQLiteSession.status == SessionStatus.IN_PROGRESS.value,
                )
                .first()
            )
            return session
        except Exception:
            return None

    def timeout_stale_sessions(self, timeout_seconds: int) -> int:
        """
        Mark all sessions inactive for longer than timeout as unsuccessful.

        Queries for sessions with status="in_progress" and start_time older
        than the configured timeout, then marks each as "unsuccessful" with
        finish_time set to the current timestamp.

        Args:
            timeout_seconds: Inactivity threshold in seconds

        Returns:
            Number of sessions successfully timed out
        """
        from datetime import timedelta

        timed_out_count = 0

        try:
            # Calculate the cutoff time
            cutoff_time = datetime.now(UTC).replace(microsecond=0) - timedelta(
                seconds=timeout_seconds
            )

            # Query all stale sessions
            stale_sessions = (
                self._db_session.query(_SQLiteSession)
                .filter(
                    _SQLiteSession.status == SessionStatus.IN_PROGRESS.value,
                    _SQLiteSession.start_time < cutoff_time,
                )
                .all()
            )

            if not stale_sessions:
                return 0

            # Process each session individually to continue on failures
            for session in stale_sessions:
                try:
                    finish_time = datetime.now(UTC)
                    session.status = SessionStatus.UNSUCCESSFUL.value
                    session.finish_time = finish_time

                    # Calculate duration in seconds
                    if session.start_time is not None:
                        start_ts = _normalize_timestamp(session.start_time)
                        duration = finish_time - start_ts
                        session.duration_seconds = int(duration.total_seconds())
                    else:
                        session.duration_seconds = 0

                    self._db_session.commit()
                    timed_out_count += 1
                except Exception:
                    self._db_session.rollback()

            return timed_out_count

        except Exception:
            return timed_out_count


@contextmanager
def get_test_db_session():
    """Create an in-memory SQLite database session for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    _SQLiteBase.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


def _normalize_timestamp(ts: datetime) -> datetime:
    """
    Normalize a timestamp for comparison by handling timezone info.

    SQLite doesn't preserve timezone info, so we need to handle timestamps
    consistently. This helper ensures consistent comparison.
    """
    if ts is None:
        return None
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts


# Strategy for generating valid optimization methods
optimization_method_strategy = st.sampled_from(list(OptimizationMethod))

# Strategy for generating valid model names
model_name_strategy = st.sampled_from(
    [
        "openai/gpt-4",
        "openai/gpt-4o",
        "openai/gpt-3.5-turbo",
        "gpt-4",
        "gpt-4o",
        "claude-3-opus",
    ]
)


class TestStartSessionDefaults:
    """
    **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
    **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

    Property 1: New sessions initialize with correct defaults
    *For any* new session created via `start_session()`, the session SHALL have:
    - status="in_progress"
    - used_followup=False
    - input_tokens=0
    - output_tokens=0
    - tokens_total=0
    - start_time set to a timezone-aware UTC timestamp
    - conversation_history=[]
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_new_session_has_correct_status(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
        **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

        For any new session created via start_session(), the status should be
        "in_progress" as per Requirement 1.4.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)

            # Property assertions
            assert session is not None, "Session should be created successfully"

            # Property 1: status should be "in_progress" (Requirement 1.4)
            assert session.status == SessionStatus.IN_PROGRESS.value, (
                f"New session status should be 'in_progress', got: {session.status}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_new_session_has_followup_false(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
        **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

        For any new session created via start_session(), used_followup should be
        False as per Requirement 6.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)

            # Property assertions
            assert session is not None, "Session should be created successfully"

            # Property 1: used_followup should be False (Requirement 6.3)
            assert session.used_followup is False, (
                f"New session used_followup should be False, got: {session.used_followup}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_new_session_has_zero_tokens(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
        **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

        For any new session created via start_session(), all token counts should
        be initialized to zero as per Requirement 5.1.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)

            # Property assertions
            assert session is not None, "Session should be created successfully"

            # Property 1: token counts should be zero (Requirement 5.1)
            assert session.input_tokens == 0, (
                f"New session input_tokens should be 0, got: {session.input_tokens}"
            )
            assert session.output_tokens == 0, (
                f"New session output_tokens should be 0, got: {session.output_tokens}"
            )
            assert session.tokens_total == 0, (
                f"New session tokens_total should be 0, got: {session.tokens_total}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_new_session_has_start_time_set(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
        **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

        For any new session created via start_session(), start_time should be
        set to the current UTC timestamp as per Requirement 1.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            before_creation = datetime.now(UTC)
            session = service.start_session(user.id, model_name, method)
            after_creation = datetime.now(UTC)

            # Property assertions
            assert session is not None, "Session should be created successfully"

            # Property 1: start_time should be set (Requirement 1.3)
            assert session.start_time is not None, "start_time must be set"

            # Normalize timestamp for comparison (SQLite may strip timezone)
            start_ts = _normalize_timestamp(session.start_time)

            # Property: start_time should be within the test window
            assert before_creation <= start_ts <= after_creation, (
                f"start_time ({start_ts}) should be between {before_creation} and {after_creation}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_new_session_has_empty_conversation_history(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
        **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

        For any new session created via start_session(), conversation_history
        should be an empty list.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)

            # Property assertions
            assert session is not None, "Session should be created successfully"

            # Property 1: conversation_history should be empty list
            assert session.conversation_history == [], (
                f"New session conversation_history should be [], "
                f"got: {session.conversation_history}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_new_session_stores_method_and_model(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
        **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

        For any new session created via start_session(), the optimization_method
        and model_name should be stored correctly.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)

            # Property assertions
            assert session is not None, "Session should be created successfully"

            # Property: optimization_method should match input
            assert session.optimization_method == method.value, (
                f"optimization_method should be {method.value}, got: {session.optimization_method}"
            )

            # Property: model_name should match input
            assert session.model_name == model_name, (
                f"model_name should be {model_name}, got: {session.model_name}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_new_session_links_to_user(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 1: New sessions initialize with correct defaults**
        **Validates: Requirements 1.3, 1.4, 5.1, 6.3**

        For any new session created via start_session(), the user_id should
        correctly reference the user as per Requirement 1.2.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)

            # Property assertions
            assert session is not None, "Session should be created successfully"

            # Property: user_id should reference the correct user
            assert session.user_id == user.id, (
                f"session.user_id should be {user.id}, got: {session.user_id}"
            )


class TestCompleteSessionSetsFinishTimeAndDuration:
    """
    **Feature: session-tracking, Property 4: Successful completion sets finish time and duration**
    **Validates: Requirements 2.1, 2.2, 2.3**

    Property 4: Successful completion sets finish time and duration
    *For any* session marked successful via `complete_session()`:
    - The `finish_time` SHALL be set to a timestamp >= `start_time`
    - The `duration_seconds` SHALL equal `(finish_time - start_time).total_seconds()`
    - The `status` SHALL be "successful"
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_complete_session_sets_status_to_successful(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 4: Successful completion sets finish time and duration**
        **Validates: Requirements 2.1, 2.2, 2.3**

        For any session completed via complete_session(), the status should be
        "successful" as per Requirement 2.1.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Complete the session
            completed_session = service.complete_session(session.id)

            # Property assertions
            assert completed_session is not None, "Session should be completed successfully"
            assert completed_session.status == SessionStatus.SUCCESSFUL.value, (
                f"Completed session status should be 'successful', got: {completed_session.status}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_complete_session_sets_finish_time(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 4: Successful completion sets finish time and duration**
        **Validates: Requirements 2.1, 2.2, 2.3**

        For any session completed via complete_session(), the finish_time should be
        set to the current UTC timestamp as per Requirement 2.2.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Complete the session
            before_completion = datetime.now(UTC)
            completed_session = service.complete_session(session.id)
            after_completion = datetime.now(UTC)

            # Property assertions
            assert completed_session is not None, "Session should be completed successfully"
            assert completed_session.finish_time is not None, "finish_time must be set"

            # Normalize timestamp for comparison (SQLite may strip timezone)
            finish_ts = _normalize_timestamp(completed_session.finish_time)

            # Property: finish_time should be within the test window
            assert before_completion <= finish_ts <= after_completion, (
                f"finish_time ({finish_ts}) should be between "
                f"{before_completion} and {after_completion}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_complete_session_finish_time_after_start_time(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 4: Successful completion sets finish time and duration**
        **Validates: Requirements 2.1, 2.2, 2.3**

        For any session completed via complete_session(), the finish_time should be
        >= start_time.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Complete the session
            completed_session = service.complete_session(session.id)

            # Property assertions
            assert completed_session is not None, "Session should be completed successfully"

            # Normalize timestamps for comparison (SQLite may strip timezone)
            start_ts = _normalize_timestamp(completed_session.start_time)
            finish_ts = _normalize_timestamp(completed_session.finish_time)

            # Property: finish_time >= start_time
            assert finish_ts >= start_ts, (
                f"finish_time ({finish_ts}) should be >= start_time ({start_ts})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_complete_session_calculates_duration(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 4: Successful completion sets finish time and duration**
        **Validates: Requirements 2.1, 2.2, 2.3**

        For any session completed via complete_session(), the duration_seconds should
        equal (finish_time - start_time).total_seconds() as per Requirement 2.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Complete the session
            completed_session = service.complete_session(session.id)

            # Property assertions
            assert completed_session is not None, "Session should be completed successfully"
            assert completed_session.duration_seconds is not None, "duration_seconds must be set"

            # Normalize timestamps for calculation (SQLite may strip timezone)
            start_ts = _normalize_timestamp(completed_session.start_time)
            finish_ts = _normalize_timestamp(completed_session.finish_time)

            # Calculate expected duration
            expected_duration = int((finish_ts - start_ts).total_seconds())

            # Property: duration_seconds should equal (finish_time - start_time).total_seconds()
            assert completed_session.duration_seconds == expected_duration, (
                f"duration_seconds ({completed_session.duration_seconds}) should equal "
                f"expected duration ({expected_duration})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_complete_session_duration_is_non_negative(
        self, telegram_id: int, method: OptimizationMethod, model_name: str
    ):
        """
        **Feature: session-tracking, Property 4: Successful completion sets finish time and duration**
        **Validates: Requirements 2.1, 2.2, 2.3**

        For any session completed via complete_session(), the duration_seconds should
        be non-negative (since finish_time >= start_time).
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Complete the session
            completed_session = service.complete_session(session.id)

            # Property assertions
            assert completed_session is not None, "Session should be completed successfully"
            assert completed_session.duration_seconds is not None, "duration_seconds must be set"

            # Property: duration_seconds should be non-negative
            assert completed_session.duration_seconds >= 0, (
                f"duration_seconds ({completed_session.duration_seconds}) should be >= 0"
            )


class TestResetSessionPreservesMetrics:
    """
    **Feature: session-tracking, Property 5: Reset preserves metrics**
    **Validates: Requirements 3.1, 3.2, 3.3**

    Property 5: Reset preserves metrics
    *For any* session with recorded tokens and method, calling `reset_session()`:
    - SHALL change status to "unsuccessful"
    - SHALL set `finish_time`
    - SHALL NOT modify `input_tokens`, `output_tokens`, `tokens_total`
    - SHALL NOT modify `optimization_method` or `used_followup`
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        input_tokens=st.integers(min_value=0, max_value=100000),
        output_tokens=st.integers(min_value=0, max_value=100000),
        used_followup=st.booleans(),
    )
    @settings(max_examples=100)
    def test_reset_session_changes_status_to_unsuccessful(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        used_followup: bool,
    ):
        """
        **Feature: session-tracking, Property 5: Reset preserves metrics**
        **Validates: Requirements 3.1, 3.2, 3.3**

        For any session reset via reset_session(), the status should be
        "unsuccessful" as per Requirement 3.1.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add tokens and set followup if needed
            if input_tokens > 0 or output_tokens > 0:
                service.add_tokens(session.id, input_tokens, output_tokens)
            if used_followup:
                service.set_followup_used(session.id)

            # Reset the session
            reset_session = service.reset_session(session.id)

            # Property assertions
            assert reset_session is not None, "Session should be reset successfully"
            assert reset_session.status == SessionStatus.UNSUCCESSFUL.value, (
                f"Reset session status should be 'unsuccessful', got: {reset_session.status}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        input_tokens=st.integers(min_value=0, max_value=100000),
        output_tokens=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=100)
    def test_reset_session_sets_finish_time(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """
        **Feature: session-tracking, Property 5: Reset preserves metrics**
        **Validates: Requirements 3.1, 3.2, 3.3**

        For any session reset via reset_session(), the finish_time should be
        set to the current UTC timestamp as per Requirement 3.2.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add tokens
            if input_tokens > 0 or output_tokens > 0:
                service.add_tokens(session.id, input_tokens, output_tokens)

            # Reset the session
            before_reset = datetime.now(UTC)
            reset_session = service.reset_session(session.id)
            after_reset = datetime.now(UTC)

            # Property assertions
            assert reset_session is not None, "Session should be reset successfully"
            assert reset_session.finish_time is not None, "finish_time must be set"

            # Normalize timestamp for comparison (SQLite may strip timezone)
            finish_ts = _normalize_timestamp(reset_session.finish_time)

            # Property: finish_time should be within the test window
            assert before_reset <= finish_ts <= after_reset, (
                f"finish_time ({finish_ts}) should be between {before_reset} and {after_reset}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        input_tokens=st.integers(min_value=0, max_value=100000),
        output_tokens=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=100)
    def test_reset_session_preserves_input_tokens(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """
        **Feature: session-tracking, Property 5: Reset preserves metrics**
        **Validates: Requirements 3.1, 3.2, 3.3**

        For any session reset via reset_session(), the input_tokens should
        be preserved as per Requirement 3.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add tokens
            if input_tokens > 0 or output_tokens > 0:
                service.add_tokens(session.id, input_tokens, output_tokens)

            # Capture metrics before reset
            tokens_before = session.input_tokens

            # Reset the session
            reset_session = service.reset_session(session.id)

            # Property assertions
            assert reset_session is not None, "Session should be reset successfully"
            assert reset_session.input_tokens == tokens_before, (
                f"input_tokens should be preserved ({tokens_before}), "
                f"got: {reset_session.input_tokens}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        input_tokens=st.integers(min_value=0, max_value=100000),
        output_tokens=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=100)
    def test_reset_session_preserves_output_tokens(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """
        **Feature: session-tracking, Property 5: Reset preserves metrics**
        **Validates: Requirements 3.1, 3.2, 3.3**

        For any session reset via reset_session(), the output_tokens should
        be preserved as per Requirement 3.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add tokens
            if input_tokens > 0 or output_tokens > 0:
                service.add_tokens(session.id, input_tokens, output_tokens)

            # Capture metrics before reset
            tokens_before = session.output_tokens

            # Reset the session
            reset_session = service.reset_session(session.id)

            # Property assertions
            assert reset_session is not None, "Session should be reset successfully"
            assert reset_session.output_tokens == tokens_before, (
                f"output_tokens should be preserved ({tokens_before}), "
                f"got: {reset_session.output_tokens}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        input_tokens=st.integers(min_value=0, max_value=100000),
        output_tokens=st.integers(min_value=0, max_value=100000),
    )
    @settings(max_examples=100)
    def test_reset_session_preserves_tokens_total(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """
        **Feature: session-tracking, Property 5: Reset preserves metrics**
        **Validates: Requirements 3.1, 3.2, 3.3**

        For any session reset via reset_session(), the tokens_total should
        be preserved as per Requirement 3.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add tokens
            if input_tokens > 0 or output_tokens > 0:
                service.add_tokens(session.id, input_tokens, output_tokens)

            # Capture metrics before reset
            tokens_before = session.tokens_total

            # Reset the session
            reset_session = service.reset_session(session.id)

            # Property assertions
            assert reset_session is not None, "Session should be reset successfully"
            assert reset_session.tokens_total == tokens_before, (
                f"tokens_total should be preserved ({tokens_before}), "
                f"got: {reset_session.tokens_total}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_reset_session_preserves_optimization_method(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 5: Reset preserves metrics**
        **Validates: Requirements 3.1, 3.2, 3.3**

        For any session reset via reset_session(), the optimization_method should
        be preserved as per Requirement 3.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Capture method before reset
            method_before = session.optimization_method

            # Reset the session
            reset_session = service.reset_session(session.id)

            # Property assertions
            assert reset_session is not None, "Session should be reset successfully"
            assert reset_session.optimization_method == method_before, (
                f"optimization_method should be preserved ({method_before}), "
                f"got: {reset_session.optimization_method}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        used_followup=st.booleans(),
    )
    @settings(max_examples=100)
    def test_reset_session_preserves_used_followup(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        used_followup: bool,
    ):
        """
        **Feature: session-tracking, Property 5: Reset preserves metrics**
        **Validates: Requirements 3.1, 3.2, 3.3**

        For any session reset via reset_session(), the used_followup flag should
        be preserved as per Requirement 3.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Set followup if needed
            if used_followup:
                service.set_followup_used(session.id)

            # Capture followup before reset
            followup_before = session.used_followup

            # Reset the session
            reset_session = service.reset_session(session.id)

            # Property assertions
            assert reset_session is not None, "Session should be reset successfully"
            assert reset_session.used_followup == followup_before, (
                f"used_followup should be preserved ({followup_before}), "
                f"got: {reset_session.used_followup}"
            )


class TestTokenAccumulationIsAdditive:
    """
    **Feature: session-tracking, Property 3: Token accumulation is additive**
    **Validates: Requirements 5.2, 5.3, 5.4, 5.5**

    Property 3: Token accumulation is additive
    *For any* session and any sequence of `add_tokens(input, output)` calls:
    - The final `input_tokens` SHALL equal the sum of all input values
    - The final `output_tokens` SHALL equal the sum of all output values
    - The `tokens_total` SHALL equal `input_tokens + output_tokens`
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        token_calls=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=10000),
                st.integers(min_value=0, max_value=10000),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_token_accumulation_input_tokens_sum(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        token_calls: list[tuple[int, int]],
    ):
        """
        **Feature: session-tracking, Property 3: Token accumulation is additive**
        **Validates: Requirements 5.2, 5.3, 5.4, 5.5**

        For any sequence of add_tokens() calls, the final input_tokens should
        equal the sum of all input token values as per Requirement 5.2.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Apply all token calls
            expected_input_sum = 0
            for input_tokens, output_tokens in token_calls:
                result = service.add_tokens(session.id, input_tokens, output_tokens)
                assert result is not None, "add_tokens should succeed"
                expected_input_sum += input_tokens

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: input_tokens equals sum of all input values
            assert session.input_tokens == expected_input_sum, (
                f"input_tokens ({session.input_tokens}) should equal "
                f"sum of all input values ({expected_input_sum})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        token_calls=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=10000),
                st.integers(min_value=0, max_value=10000),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_token_accumulation_output_tokens_sum(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        token_calls: list[tuple[int, int]],
    ):
        """
        **Feature: session-tracking, Property 3: Token accumulation is additive**
        **Validates: Requirements 5.2, 5.3, 5.4, 5.5**

        For any sequence of add_tokens() calls, the final output_tokens should
        equal the sum of all output token values as per Requirement 5.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Apply all token calls
            expected_output_sum = 0
            for input_tokens, output_tokens in token_calls:
                result = service.add_tokens(session.id, input_tokens, output_tokens)
                assert result is not None, "add_tokens should succeed"
                expected_output_sum += output_tokens

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: output_tokens equals sum of all output values
            assert session.output_tokens == expected_output_sum, (
                f"output_tokens ({session.output_tokens}) should equal "
                f"sum of all output values ({expected_output_sum})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        token_calls=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=10000),
                st.integers(min_value=0, max_value=10000),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_token_accumulation_total_equals_sum(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        token_calls: list[tuple[int, int]],
    ):
        """
        **Feature: session-tracking, Property 3: Token accumulation is additive**
        **Validates: Requirements 5.2, 5.3, 5.4, 5.5**

        For any sequence of add_tokens() calls, the tokens_total should
        equal input_tokens + output_tokens as per Requirement 5.4.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Apply all token calls
            for input_tokens, output_tokens in token_calls:
                result = service.add_tokens(session.id, input_tokens, output_tokens)
                assert result is not None, "add_tokens should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: tokens_total equals input_tokens + output_tokens
            expected_total = session.input_tokens + session.output_tokens
            assert session.tokens_total == expected_total, (
                f"tokens_total ({session.tokens_total}) should equal "
                f"input_tokens + output_tokens ({expected_total})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        token_calls=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=10000),
                st.integers(min_value=0, max_value=10000),
            ),
            min_size=1,
            max_size=10,
        ),
    )
    @settings(max_examples=100)
    def test_token_accumulation_multiple_interactions(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        token_calls: list[tuple[int, int]],
    ):
        """
        **Feature: session-tracking, Property 3: Token accumulation is additive**
        **Validates: Requirements 5.2, 5.3, 5.4, 5.5**

        For any sequence of add_tokens() calls (simulating multiple LLM interactions),
        all token counts should accumulate correctly as per Requirement 5.5.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Apply all token calls and track expected sums
            expected_input_sum = 0
            expected_output_sum = 0
            for input_tokens, output_tokens in token_calls:
                result = service.add_tokens(session.id, input_tokens, output_tokens)
                assert result is not None, "add_tokens should succeed"
                expected_input_sum += input_tokens
                expected_output_sum += output_tokens

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertions: all accumulations are correct
            assert session.input_tokens == expected_input_sum, (
                f"input_tokens ({session.input_tokens}) should equal "
                f"sum of all input values ({expected_input_sum})"
            )
            assert session.output_tokens == expected_output_sum, (
                f"output_tokens ({session.output_tokens}) should equal "
                f"sum of all output values ({expected_output_sum})"
            )
            expected_total = expected_input_sum + expected_output_sum
            assert session.tokens_total == expected_total, (
                f"tokens_total ({session.tokens_total}) should equal "
                f"sum of all tokens ({expected_total})"
            )


class TestConversationHistoryPreservesOrder:
    """
    **Feature: session-tracking, Property 10: Conversation history preserves message order**
    **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

    Property 10: Conversation history preserves message order
    *For any* session, messages added via `add_message()` SHALL be appended to the
    `conversation_history` JSONB array in the order they were added, preserving
    chronological order of user-LLM exchanges.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        messages=st.lists(
            st.tuples(
                st.sampled_from(["user", "assistant"]),
                st.text(min_size=1, max_size=500),
            ),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_messages_appended_in_order(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        messages: list[tuple[str, str]],
    ):
        """
        **Feature: session-tracking, Property 10: Conversation history preserves message order**
        **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

        For any sequence of add_message() calls, the conversation_history should
        contain messages in the exact order they were added.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add all messages in order
            for role, content in messages:
                result = service.add_message(session.id, role, content)
                assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: messages are in the same order as added
            assert len(session.conversation_history) == len(messages), (
                f"conversation_history length ({len(session.conversation_history)}) "
                f"should equal number of messages added ({len(messages)})"
            )

            for i, (expected_role, expected_content) in enumerate(messages):
                actual_message = session.conversation_history[i]
                assert actual_message["role"] == expected_role, (
                    f"Message {i} role should be '{expected_role}', got: '{actual_message['role']}'"
                )
                assert actual_message["content"] == expected_content, (
                    f"Message {i} content should be '{expected_content}', "
                    f"got: '{actual_message['content']}'"
                )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        messages=st.lists(
            st.tuples(
                st.sampled_from(["user", "assistant"]),
                st.text(min_size=1, max_size=500),
            ),
            min_size=1,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_messages_have_timestamps(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        messages: list[tuple[str, str]],
    ):
        """
        **Feature: session-tracking, Property 10: Conversation history preserves message order**
        **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

        For any message added via add_message(), the message object should
        include a timestamp as per Requirement 10.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add all messages
            for role, content in messages:
                result = service.add_message(session.id, role, content)
                assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: all messages have timestamps
            for i, msg in enumerate(session.conversation_history):
                assert "timestamp" in msg, f"Message {i} should have a timestamp"
                assert msg["timestamp"] is not None, f"Message {i} timestamp should not be None"
                # Verify timestamp is a valid ISO8601 string
                assert isinstance(msg["timestamp"], str), (
                    f"Message {i} timestamp should be a string"
                )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        messages=st.lists(
            st.tuples(
                st.sampled_from(["user", "assistant"]),
                st.text(min_size=1, max_size=500),
            ),
            min_size=2,
            max_size=20,
        ),
    )
    @settings(max_examples=100)
    def test_timestamps_are_chronological(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        messages: list[tuple[str, str]],
    ):
        """
        **Feature: session-tracking, Property 10: Conversation history preserves message order**
        **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

        For any sequence of add_message() calls, the timestamps should be
        in chronological order (non-decreasing) as per Requirement 10.4.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add all messages
            for role, content in messages:
                result = service.add_message(session.id, role, content)
                assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: timestamps are in chronological order
            history = session.conversation_history
            for i in range(1, len(history)):
                prev_ts = history[i - 1]["timestamp"]
                curr_ts = history[i]["timestamp"]
                # ISO8601 strings can be compared lexicographically
                assert curr_ts >= prev_ts, (
                    f"Timestamp at index {i} ({curr_ts}) should be >= "
                    f"timestamp at index {i - 1} ({prev_ts})"
                )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_user_message_has_correct_role(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        content: str,
    ):
        """
        **Feature: session-tracking, Property 10: Conversation history preserves message order**
        **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

        For any user message added via add_message(), the role should be "user"
        as per Requirement 10.1.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add a user message
            result = service.add_message(session.id, "user", content)
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: message has role "user"
            assert len(session.conversation_history) == 1
            assert session.conversation_history[0]["role"] == "user", (
                f"User message role should be 'user', "
                f"got: '{session.conversation_history[0]['role']}'"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_assistant_message_has_correct_role(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        content: str,
    ):
        """
        **Feature: session-tracking, Property 10: Conversation history preserves message order**
        **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

        For any assistant message added via add_message(), the role should be
        "assistant" as per Requirement 10.2.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add an assistant message
            result = service.add_message(session.id, "assistant", content)
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: message has role "assistant"
            assert len(session.conversation_history) == 1
            assert session.conversation_history[0]["role"] == "assistant", (
                f"Assistant message role should be 'assistant', "
                f"got: '{session.conversation_history[0]['role']}'"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_message_content_preserved(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        content: str,
    ):
        """
        **Feature: session-tracking, Property 10: Conversation history preserves message order**
        **Validates: Requirements 10.1, 10.2, 10.3, 10.4**

        For any message added via add_message(), the content should be
        preserved exactly as provided.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add a message
            result = service.add_message(session.id, "user", content)
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: content is preserved exactly
            assert len(session.conversation_history) == 1
            assert session.conversation_history[0]["content"] == content, (
                "Message content should be preserved exactly"
            )


# Strategy for generating valid email addresses
email_strategy = st.emails()

# Strategy for generating valid delivery statuses
delivery_status_strategy = st.sampled_from(["sent", "failed"])


class TestEmailEventsLinkedToSessions:
    """
    **Feature: session-tracking, Property 6: Email events are linked to sessions**
    **Validates: Requirements 7.1, 7.3**

    Property 6: Email events are linked to sessions
    *For any* email event created via `log_email_sent(session_id, ...)`:
    - The event SHALL have a valid `session_id` reference
    - Querying the session SHALL include this event in `email_events`
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        recipient_email=email_strategy,
        delivery_status=delivery_status_strategy,
    )
    @settings(max_examples=100)
    def test_email_event_has_valid_session_reference(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        recipient_email: str,
        delivery_status: str,
    ):
        """
        **Feature: session-tracking, Property 6: Email events are linked to sessions**
        **Validates: Requirements 7.1, 7.3**

        For any email event created via log_email_sent(), the event should have
        a valid session_id reference as per Requirement 7.1.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Log an email event
            email_event = service.log_email_sent(session.id, recipient_email, delivery_status)

            # Property assertions
            assert email_event is not None, "Email event should be created successfully"
            assert email_event.session_id == session.id, (
                f"Email event session_id ({email_event.session_id}) should match "
                f"session id ({session.id})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        recipient_email=email_strategy,
        delivery_status=delivery_status_strategy,
    )
    @settings(max_examples=100)
    def test_session_includes_email_event_in_relationship(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        recipient_email: str,
        delivery_status: str,
    ):
        """
        **Feature: session-tracking, Property 6: Email events are linked to sessions**
        **Validates: Requirements 7.1, 7.3**

        For any email event created via log_email_sent(), querying the session
        should include this event in email_events as per Requirement 7.3.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Log an email event
            email_event = service.log_email_sent(session.id, recipient_email, delivery_status)
            assert email_event is not None, "Email event should be created successfully"

            # Refresh session to get updated relationships
            db_session.refresh(session)

            # Property assertion: session's email_events includes the created event
            assert len(session.email_events) == 1, (
                f"Session should have 1 email event, got: {len(session.email_events)}"
            )
            assert session.email_events[0].id == email_event.id, (
                f"Session's email event id ({session.email_events[0].id}) should match "
                f"created event id ({email_event.id})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        email_events_data=st.lists(
            st.tuples(email_strategy, delivery_status_strategy),
            min_size=1,
            max_size=5,
        ),
    )
    @settings(max_examples=100)
    def test_multiple_email_events_linked_to_session(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        email_events_data: list[tuple[str, str]],
    ):
        """
        **Feature: session-tracking, Property 6: Email events are linked to sessions**
        **Validates: Requirements 7.1, 7.3**

        For any sequence of email events created via log_email_sent(), all events
        should be accessible via the session's email_events relationship.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Log multiple email events
            created_event_ids = []
            for recipient_email, delivery_status in email_events_data:
                email_event = service.log_email_sent(session.id, recipient_email, delivery_status)
                assert email_event is not None, "Email event should be created successfully"
                created_event_ids.append(email_event.id)

            # Refresh session to get updated relationships
            db_session.refresh(session)

            # Property assertion: session's email_events includes all created events
            assert len(session.email_events) == len(email_events_data), (
                f"Session should have {len(email_events_data)} email events, "
                f"got: {len(session.email_events)}"
            )

            # Verify all created events are in the relationship
            session_event_ids = {event.id for event in session.email_events}
            for event_id in created_event_ids:
                assert event_id in session_event_ids, (
                    f"Email event {event_id} should be in session's email_events"
                )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        recipient_email=email_strategy,
        delivery_status=delivery_status_strategy,
    )
    @settings(max_examples=100)
    def test_email_event_stores_recipient_and_status(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        recipient_email: str,
        delivery_status: str,
    ):
        """
        **Feature: session-tracking, Property 6: Email events are linked to sessions**
        **Validates: Requirements 7.1, 7.3**

        For any email event created via log_email_sent(), the recipient_email
        and delivery_status should be stored correctly as per Requirement 7.2.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Log an email event
            email_event = service.log_email_sent(session.id, recipient_email, delivery_status)

            # Property assertions
            assert email_event is not None, "Email event should be created successfully"
            assert email_event.recipient_email == recipient_email, (
                f"Email event recipient_email ({email_event.recipient_email}) should match "
                f"input ({recipient_email})"
            )
            assert email_event.delivery_status == delivery_status, (
                f"Email event delivery_status ({email_event.delivery_status}) should match "
                f"input ({delivery_status})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        recipient_email=email_strategy,
        delivery_status=delivery_status_strategy,
    )
    @settings(max_examples=100)
    def test_email_event_has_sent_at_timestamp(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        recipient_email: str,
        delivery_status: str,
    ):
        """
        **Feature: session-tracking, Property 6: Email events are linked to sessions**
        **Validates: Requirements 7.1, 7.3**

        For any email event created via log_email_sent(), the sent_at timestamp
        should be set as per Requirement 7.2.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Log an email event
            before_log = datetime.now(UTC)
            email_event = service.log_email_sent(session.id, recipient_email, delivery_status)
            after_log = datetime.now(UTC)

            # Property assertions
            assert email_event is not None, "Email event should be created successfully"
            assert email_event.sent_at is not None, "sent_at timestamp must be set"

            # Normalize timestamp for comparison (SQLite may strip timezone)
            sent_ts = _normalize_timestamp(email_event.sent_at)

            # Property: sent_at should be within the test window
            # Note: SQLite may strip microseconds, so we compare at second-level precision
            # by allowing 1 second tolerance
            from datetime import timedelta

            assert (
                before_log - timedelta(seconds=1) <= sent_ts <= after_log + timedelta(seconds=1)
            ), (
                f"sent_at ({sent_ts}) should be within 1 second of test window "
                f"({before_log} to {after_log})"
            )


class TestOneActiveSessionPerUser:
    """
    **Feature: session-tracking, Property 9: One active session per user**
    **Validates: Requirements 1.1**

    Property 9: One active session per user
    *For any* user, there SHALL be at most one session with `status="in_progress"`
    at any time.

    Note: This property tests that the system correctly tracks active sessions
    and that get_user_current_session() returns the expected session. The
    enforcement of "at most one" is a design constraint that should be
    maintained by the application logic (completing/resetting previous sessions
    before starting new ones).
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_single_session_is_retrievable(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 9: One active session per user**
        **Validates: Requirements 1.1**

        For any user with a single in-progress session, get_user_current_session()
        should return that session.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Query for current session
            current_session = service.get_user_current_session(user.id)

            # Property assertion: the current session should be the one we created
            assert current_session is not None, "Current session should be found"
            assert current_session.id == session.id, (
                f"Current session id ({current_session.id}) should match "
                f"created session id ({session.id})"
            )
            assert current_session.status == SessionStatus.IN_PROGRESS.value, (
                f"Current session status should be 'in_progress', got: {current_session.status}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_completed_session_not_returned_as_current(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 9: One active session per user**
        **Validates: Requirements 1.1**

        For any user whose session has been completed, get_user_current_session()
        should return None (no active session).
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Complete the session
            completed = service.complete_session(session.id)
            assert completed is not None, "Session should be completed successfully"

            # Query for current session
            current_session = service.get_user_current_session(user.id)

            # Property assertion: no active session should be found
            assert current_session is None, "No current session should be found after completion"

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_reset_session_not_returned_as_current(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 9: One active session per user**
        **Validates: Requirements 1.1**

        For any user whose session has been reset, get_user_current_session()
        should return None (no active session).
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Reset the session
            reset = service.reset_session(session.id)
            assert reset is not None, "Session should be reset successfully"

            # Query for current session
            current_session = service.get_user_current_session(user.id)

            # Property assertion: no active session should be found
            assert current_session is None, "No current session should be found after reset"

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_user_with_no_sessions_returns_none(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 9: One active session per user**
        **Validates: Requirements 1.1**

        For any user with no sessions, get_user_current_session() should return None.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service but don't start any session
            service = _SQLiteSessionService(db_session)

            # Query for current session
            current_session = service.get_user_current_session(user.id)

            # Property assertion: no session should be found
            assert current_session is None, (
                "No current session should be found for user with no sessions"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        methods=st.lists(optimization_method_strategy, min_size=2, max_size=5),
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_only_latest_in_progress_session_is_current(
        self,
        telegram_id: int,
        methods: list[OptimizationMethod],
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 9: One active session per user**
        **Validates: Requirements 1.1**

        For any user with multiple sessions where all but the last are completed,
        get_user_current_session() should return only the in-progress session.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service
            service = _SQLiteSessionService(db_session)

            # Create multiple sessions, completing all but the last
            last_session = None
            for i, method in enumerate(methods):
                session = service.start_session(user.id, model_name, method)
                assert session is not None, f"Session {i} should be created successfully"

                if i < len(methods) - 1:
                    # Complete all sessions except the last one
                    completed = service.complete_session(session.id)
                    assert completed is not None, f"Session {i} should be completed"
                else:
                    # Keep the last session in progress
                    last_session = session

            # Query for current session
            current_session = service.get_user_current_session(user.id)

            # Property assertion: current session should be the last (in-progress) one
            assert current_session is not None, "Current session should be found"
            assert current_session.id == last_session.id, (
                f"Current session id ({current_session.id}) should match "
                f"last session id ({last_session.id})"
            )

    @given(
        telegram_ids=st.lists(
            st.integers(min_value=1, max_value=2**63 - 1),
            min_size=2,
            max_size=5,
            unique=True,
        ),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_different_users_have_independent_sessions(
        self,
        telegram_ids: list[int],
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 9: One active session per user**
        **Validates: Requirements 1.1**

        For any set of different users, each user's current session should be
        independent and correctly tracked.
        """
        with get_test_db_session() as db_session:
            # Create multiple users
            users = []
            for telegram_id in telegram_ids:
                user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
                db_session.add(user)
                users.append(user)
            db_session.commit()
            for user in users:
                db_session.refresh(user)

            # Create session service
            service = _SQLiteSessionService(db_session)

            # Start a session for each user
            user_sessions = {}
            for user in users:
                session = service.start_session(user.id, model_name, method)
                assert session is not None, f"Session for user {user.id} should be created"
                user_sessions[user.id] = session

            # Verify each user's current session is their own
            for user in users:
                current_session = service.get_user_current_session(user.id)
                assert current_session is not None, (
                    f"Current session for user {user.id} should be found"
                )
                assert current_session.id == user_sessions[user.id].id, (
                    f"User {user.id}'s current session id ({current_session.id}) "
                    f"should match their created session id ({user_sessions[user.id].id})"
                )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_count_in_progress_sessions_is_at_most_one(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 9: One active session per user**
        **Validates: Requirements 1.1**

        For any user, the count of sessions with status="in_progress" should be
        at most one at any time.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Count in-progress sessions for this user
            in_progress_count = (
                db_session.query(_SQLiteSession)
                .filter(
                    _SQLiteSession.user_id == user.id,
                    _SQLiteSession.status == SessionStatus.IN_PROGRESS.value,
                )
                .count()
            )

            # Property assertion: at most one in-progress session
            assert in_progress_count <= 1, (
                f"User should have at most 1 in-progress session, got: {in_progress_count}"
            )


class TestTimeoutMarksSessionsUnsuccessful:
    """
    **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
    **Validates: Requirements 4.1, 4.2**

    Property 8: Timeout marks sessions unsuccessful
    *For any* session with `status="in_progress"` and `start_time` older than
    the configured timeout (in seconds), calling `timeout_stale_sessions()`
    SHALL change its status to "unsuccessful" and set `finish_time`.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        timeout_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_stale_session_status_changes_to_unsuccessful(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        timeout_seconds: int,
    ):
        """
        **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
        **Validates: Requirements 4.1, 4.2**

        For any session with start_time older than timeout, calling
        timeout_stale_sessions() should change status to "unsuccessful"
        as per Requirement 4.1.
        """
        from datetime import timedelta

        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service
            service = _SQLiteSessionService(db_session)

            # Create a session with a start_time older than the timeout
            old_start_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds + 10)
            session = _SQLiteSession(
                user_id=user.id,
                optimization_method=method.value,
                model_name=model_name,
                status=SessionStatus.IN_PROGRESS.value,
                used_followup=False,
                input_tokens=0,
                output_tokens=0,
                tokens_total=0,
                conversation_history=[],
                start_time=old_start_time,
            )
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

            # Verify session is in_progress before timeout
            assert session.status == SessionStatus.IN_PROGRESS.value

            # Run timeout
            timed_out_count = service.timeout_stale_sessions(timeout_seconds)

            # Refresh session to get updated state
            db_session.refresh(session)

            # Property assertions
            assert timed_out_count == 1, f"Expected 1 session timed out, got {timed_out_count}"
            assert session.status == SessionStatus.UNSUCCESSFUL.value, (
                f"Timed out session status should be 'unsuccessful', got: {session.status}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        timeout_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_stale_session_finish_time_is_set(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        timeout_seconds: int,
    ):
        """
        **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
        **Validates: Requirements 4.1, 4.2**

        For any session with start_time older than timeout, calling
        timeout_stale_sessions() should set finish_time as per Requirement 4.2.
        """
        from datetime import timedelta

        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service
            service = _SQLiteSessionService(db_session)

            # Create a session with a start_time older than the timeout
            old_start_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds + 10)
            session = _SQLiteSession(
                user_id=user.id,
                optimization_method=method.value,
                model_name=model_name,
                status=SessionStatus.IN_PROGRESS.value,
                used_followup=False,
                input_tokens=0,
                output_tokens=0,
                tokens_total=0,
                conversation_history=[],
                start_time=old_start_time,
            )
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

            # Verify finish_time is None before timeout
            assert session.finish_time is None

            # Run timeout
            before_timeout = datetime.now(UTC)
            service.timeout_stale_sessions(timeout_seconds)
            after_timeout = datetime.now(UTC)

            # Refresh session to get updated state
            db_session.refresh(session)

            # Property assertions
            assert session.finish_time is not None, "finish_time must be set after timeout"

            # Normalize timestamp for comparison (SQLite may strip timezone)
            finish_ts = _normalize_timestamp(session.finish_time)

            # Property: finish_time should be within the test window
            assert before_timeout <= finish_ts <= after_timeout, (
                f"finish_time ({finish_ts}) should be between {before_timeout} and {after_timeout}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        timeout_seconds=st.integers(min_value=60, max_value=3600),
    )
    @settings(max_examples=100)
    def test_recent_session_not_timed_out(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        timeout_seconds: int,
    ):
        """
        **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
        **Validates: Requirements 4.1, 4.2**

        For any session with start_time within the timeout window,
        timeout_stale_sessions() should NOT change its status.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a fresh session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Run timeout with a timeout that's longer than the session age
            timed_out_count = service.timeout_stale_sessions(timeout_seconds)

            # Refresh session to get current state
            db_session.refresh(session)

            # Property assertions
            assert timed_out_count == 0, f"Expected 0 sessions timed out, got {timed_out_count}"
            assert session.status == SessionStatus.IN_PROGRESS.value, (
                f"Recent session status should remain 'in_progress', got: {session.status}"
            )
            assert session.finish_time is None, "Recent session finish_time should remain None"

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        timeout_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_already_completed_session_not_affected(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        timeout_seconds: int,
    ):
        """
        **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
        **Validates: Requirements 4.1, 4.2**

        For any session that is already completed (status != "in_progress"),
        timeout_stale_sessions() should NOT change its status.
        """
        from datetime import timedelta

        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service
            service = _SQLiteSessionService(db_session)

            # Create a session with old start_time but already completed
            old_start_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds + 10)
            session = _SQLiteSession(
                user_id=user.id,
                optimization_method=method.value,
                model_name=model_name,
                status=SessionStatus.SUCCESSFUL.value,  # Already completed
                used_followup=False,
                input_tokens=0,
                output_tokens=0,
                tokens_total=0,
                conversation_history=[],
                start_time=old_start_time,
                finish_time=datetime.now(UTC) - timedelta(seconds=timeout_seconds + 5),
            )
            db_session.add(session)
            db_session.commit()
            db_session.refresh(session)

            original_status = session.status
            original_finish_time = session.finish_time

            # Run timeout
            timed_out_count = service.timeout_stale_sessions(timeout_seconds)

            # Refresh session to get current state
            db_session.refresh(session)

            # Property assertions
            assert timed_out_count == 0, f"Expected 0 sessions timed out, got {timed_out_count}"
            assert session.status == original_status, (
                f"Completed session status should remain '{original_status}', got: {session.status}"
            )
            assert session.finish_time == original_finish_time, (
                "Completed session finish_time should not change"
            )

    @given(
        telegram_ids=st.lists(
            st.integers(min_value=1, max_value=2**63 - 1),
            min_size=2,
            max_size=5,
            unique=True,
        ),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        timeout_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_multiple_stale_sessions_all_timed_out(
        self,
        telegram_ids: list[int],
        method: OptimizationMethod,
        model_name: str,
        timeout_seconds: int,
    ):
        """
        **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
        **Validates: Requirements 4.1, 4.2**

        For any set of sessions with start_time older than timeout,
        timeout_stale_sessions() should mark ALL of them as unsuccessful.
        """
        from datetime import timedelta

        with get_test_db_session() as db_session:
            # Create multiple users
            users = []
            for telegram_id in telegram_ids:
                user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
                db_session.add(user)
                users.append(user)
            db_session.commit()
            for user in users:
                db_session.refresh(user)

            # Create session service
            service = _SQLiteSessionService(db_session)

            # Create stale sessions for each user
            sessions = []
            old_start_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds + 10)
            for user in users:
                session = _SQLiteSession(
                    user_id=user.id,
                    optimization_method=method.value,
                    model_name=model_name,
                    status=SessionStatus.IN_PROGRESS.value,
                    used_followup=False,
                    input_tokens=0,
                    output_tokens=0,
                    tokens_total=0,
                    conversation_history=[],
                    start_time=old_start_time,
                )
                db_session.add(session)
                sessions.append(session)
            db_session.commit()
            for session in sessions:
                db_session.refresh(session)

            # Run timeout
            timed_out_count = service.timeout_stale_sessions(timeout_seconds)

            # Refresh all sessions
            for session in sessions:
                db_session.refresh(session)

            # Property assertions
            assert timed_out_count == len(users), (
                f"Expected {len(users)} sessions timed out, got {timed_out_count}"
            )
            for i, session in enumerate(sessions):
                assert session.status == SessionStatus.UNSUCCESSFUL.value, (
                    f"Session {i} status should be 'unsuccessful', got: {session.status}"
                )
                assert session.finish_time is not None, f"Session {i} finish_time must be set"

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        timeout_seconds=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=100)
    def test_timeout_returns_correct_count(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        timeout_seconds: int,
    ):
        """
        **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
        **Validates: Requirements 4.1, 4.2**

        timeout_stale_sessions() should return the correct count of
        sessions that were timed out.
        """
        from datetime import timedelta

        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service
            service = _SQLiteSessionService(db_session)

            # Create one stale session
            old_start_time = datetime.now(UTC) - timedelta(seconds=timeout_seconds + 10)
            stale_session = _SQLiteSession(
                user_id=user.id,
                optimization_method=method.value,
                model_name=model_name,
                status=SessionStatus.IN_PROGRESS.value,
                used_followup=False,
                input_tokens=0,
                output_tokens=0,
                tokens_total=0,
                conversation_history=[],
                start_time=old_start_time,
            )
            db_session.add(stale_session)
            db_session.commit()

            # Create one fresh session
            fresh_session = service.start_session(user.id, model_name, method)
            assert fresh_session is not None

            # Run timeout
            timed_out_count = service.timeout_stale_sessions(timeout_seconds)

            # Property assertion: only the stale session should be timed out
            assert timed_out_count == 1, (
                f"Expected 1 session timed out (stale only), got {timed_out_count}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        timeout_seconds=st.integers(min_value=60, max_value=3600),
    )
    @settings(max_examples=100)
    def test_no_stale_sessions_returns_zero(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        timeout_seconds: int,
    ):
        """
        **Feature: session-tracking, Property 8: Timeout marks sessions unsuccessful**
        **Validates: Requirements 4.1, 4.2**

        When there are no stale sessions, timeout_stale_sessions() should
        return 0.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a fresh session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Run timeout
            timed_out_count = service.timeout_stale_sessions(timeout_seconds)

            # Property assertion
            assert timed_out_count == 0, (
                f"Expected 0 sessions timed out when no stale sessions exist, got {timed_out_count}"
            )


class TestSessionSerializationRoundTrip:
    """
    **Feature: session-tracking, Property 7: Session serialization round-trip**
    **Validates: Requirements 11.1, 11.2, 11.3**

    Property 7: Session serialization round-trip
    *For any* valid session object (including conversation history), serializing
    to JSON and parsing back SHALL produce an equivalent session object with all
    fields preserved.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
        input_tokens=st.integers(min_value=0, max_value=100000),
        output_tokens=st.integers(min_value=0, max_value=100000),
        used_followup=st.booleans(),
        status=st.sampled_from(["in_progress", "successful", "unsuccessful"]),
        duration_seconds=st.integers(min_value=0, max_value=86400) | st.none(),
        num_messages=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100)
    def test_serialization_round_trip_preserves_all_fields(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        used_followup: bool,
        status: str,
        duration_seconds: int | None,
        num_messages: int,
    ):
        """
        **Feature: session-tracking, Property 7: Session serialization round-trip**
        **Validates: Requirements 11.1, 11.2, 11.3**

        For any valid session object, serializing to dict (for JSON) and
        deserializing back should produce an equivalent session object.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Add tokens
            if input_tokens > 0 or output_tokens > 0:
                session = service.add_tokens(session.id, input_tokens, output_tokens)
                assert session is not None

            # Set followup if needed
            if used_followup:
                session = service.set_followup_used(session.id)
                assert session is not None

            # Add messages to conversation history
            for i in range(num_messages):
                role = "user" if i % 2 == 0 else "assistant"
                content = f"Test message {i} with some content"
                session = service.add_message(session.id, role, content)
                assert session is not None

            # Complete or reset session based on status
            if status == "successful":
                session = service.complete_session(session.id)
            elif status == "unsuccessful":
                session = service.reset_session(session.id)
            # else: keep as in_progress

            assert session is not None

            # Import the actual Session model for serialization
            from telegram_bot.data.database import Session

            # Create a Session object with the same data for serialization test
            # We need to test the to_dict/from_dict methods on the actual model
            test_session = Session(
                id=session.id,
                user_id=session.user_id,
                start_time=_normalize_timestamp(session.start_time),
                finish_time=_normalize_timestamp(session.finish_time)
                if session.finish_time
                else None,
                duration_seconds=session.duration_seconds,
                status=session.status,
                optimization_method=session.optimization_method,
                model_name=session.model_name,
                used_followup=session.used_followup,
                input_tokens=session.input_tokens,
                output_tokens=session.output_tokens,
                tokens_total=session.tokens_total,
                conversation_history=session.conversation_history or [],
            )

            # Serialize to dict
            serialized = test_session.to_dict()

            # Verify serialized is a valid dict (can be JSON serialized)
            import json

            json_str = json.dumps(serialized)
            assert json_str is not None, "Should produce valid JSON string"

            # Deserialize back
            deserialized = Session.from_dict(serialized)

            # Property assertions: all fields should be preserved
            assert deserialized.id == test_session.id, (
                f"id mismatch: {deserialized.id} != {test_session.id}"
            )
            assert deserialized.user_id == test_session.user_id, (
                f"user_id mismatch: {deserialized.user_id} != {test_session.user_id}"
            )
            assert deserialized.status == test_session.status, (
                f"status mismatch: {deserialized.status} != {test_session.status}"
            )
            assert deserialized.optimization_method == test_session.optimization_method, (
                f"optimization_method mismatch: {deserialized.optimization_method} "
                f"!= {test_session.optimization_method}"
            )
            assert deserialized.model_name == test_session.model_name, (
                f"model_name mismatch: {deserialized.model_name} != {test_session.model_name}"
            )
            assert deserialized.used_followup == test_session.used_followup, (
                f"used_followup mismatch: {deserialized.used_followup} "
                f"!= {test_session.used_followup}"
            )
            assert deserialized.input_tokens == test_session.input_tokens, (
                f"input_tokens mismatch: {deserialized.input_tokens} != {test_session.input_tokens}"
            )
            assert deserialized.output_tokens == test_session.output_tokens, (
                f"output_tokens mismatch: {deserialized.output_tokens} "
                f"!= {test_session.output_tokens}"
            )
            assert deserialized.tokens_total == test_session.tokens_total, (
                f"tokens_total mismatch: {deserialized.tokens_total} != {test_session.tokens_total}"
            )
            assert deserialized.duration_seconds == test_session.duration_seconds, (
                f"duration_seconds mismatch: {deserialized.duration_seconds} "
                f"!= {test_session.duration_seconds}"
            )
            assert deserialized.conversation_history == test_session.conversation_history, (
                f"conversation_history mismatch: {deserialized.conversation_history} "
                f"!= {test_session.conversation_history}"
            )

            # Verify datetime fields (with timezone handling)
            if test_session.start_time is not None:
                assert deserialized.start_time is not None, "start_time should be preserved"
                # Compare timestamps (allowing for timezone normalization)
                original_ts = test_session.start_time.replace(microsecond=0)
                deserialized_ts = deserialized.start_time.replace(microsecond=0)
                assert abs((original_ts - deserialized_ts).total_seconds()) < 1, (
                    f"start_time mismatch: {deserialized.start_time} != {test_session.start_time}"
                )

            if test_session.finish_time is not None:
                assert deserialized.finish_time is not None, "finish_time should be preserved"
                original_ts = test_session.finish_time.replace(microsecond=0)
                deserialized_ts = deserialized.finish_time.replace(microsecond=0)
                assert abs((original_ts - deserialized_ts).total_seconds()) < 1, (
                    f"finish_time mismatch: {deserialized.finish_time} != {test_session.finish_time}"
                )
            else:
                assert deserialized.finish_time is None, "finish_time should be None"

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_serialization_produces_valid_json(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 7: Session serialization round-trip**
        **Validates: Requirements 11.1, 11.2, 11.3**

        For any session, to_dict() should produce a dictionary that can be
        serialized to valid JSON (Requirement 11.1).
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Import the actual Session model for serialization test
            from telegram_bot.data.database import Session

            # Create a Session object with the same data
            test_session = Session(
                id=session.id,
                user_id=session.user_id,
                start_time=_normalize_timestamp(session.start_time),
                finish_time=None,
                duration_seconds=None,
                status=session.status,
                optimization_method=session.optimization_method,
                model_name=session.model_name,
                used_followup=session.used_followup,
                input_tokens=session.input_tokens,
                output_tokens=session.output_tokens,
                tokens_total=session.tokens_total,
                conversation_history=session.conversation_history or [],
            )

            # Serialize to dict
            serialized = test_session.to_dict()

            # Property assertion: should be a valid dict
            assert isinstance(serialized, dict), "to_dict() should return a dict"

            # Property assertion: should be JSON serializable
            import json

            try:
                json_str = json.dumps(serialized)
                assert isinstance(json_str, str), "Should produce a JSON string"
            except (TypeError, ValueError) as e:
                raise AssertionError(f"to_dict() result is not JSON serializable: {e}") from e

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        method=optimization_method_strategy,
        model_name=model_name_strategy,
    )
    @settings(max_examples=100)
    def test_serialization_uses_iso8601_for_datetimes(
        self,
        telegram_id: int,
        method: OptimizationMethod,
        model_name: str,
    ):
        """
        **Feature: session-tracking, Property 7: Session serialization round-trip**
        **Validates: Requirements 11.1, 11.2, 11.3**

        For any session, datetime fields should be serialized using ISO 8601
        format with timezone information (Requirement 11.3).
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, method)
            assert session is not None, "Session should be created successfully"

            # Complete the session to set finish_time
            session = service.complete_session(session.id)
            assert session is not None

            # Import the actual Session model for serialization test
            from telegram_bot.data.database import Session

            # Create a Session object with the same data
            test_session = Session(
                id=session.id,
                user_id=session.user_id,
                start_time=_normalize_timestamp(session.start_time),
                finish_time=_normalize_timestamp(session.finish_time),
                duration_seconds=session.duration_seconds,
                status=session.status,
                optimization_method=session.optimization_method,
                model_name=session.model_name,
                used_followup=session.used_followup,
                input_tokens=session.input_tokens,
                output_tokens=session.output_tokens,
                tokens_total=session.tokens_total,
                conversation_history=session.conversation_history or [],
            )

            # Serialize to dict
            serialized = test_session.to_dict()

            # Property assertion: start_time should be ISO 8601 format
            start_time_str = serialized.get("start_time")
            assert start_time_str is not None, "start_time should be serialized"
            assert isinstance(start_time_str, str), "start_time should be a string"

            # Verify it can be parsed back (ISO 8601 format)
            try:
                parsed_start = datetime.fromisoformat(start_time_str)
                assert parsed_start is not None
            except ValueError as e:
                raise AssertionError(f"start_time is not valid ISO 8601: {start_time_str}") from e

            # Property assertion: finish_time should be ISO 8601 format
            finish_time_str = serialized.get("finish_time")
            assert finish_time_str is not None, "finish_time should be serialized"
            assert isinstance(finish_time_str, str), "finish_time should be a string"

            # Verify it can be parsed back (ISO 8601 format)
            try:
                parsed_finish = datetime.fromisoformat(finish_time_str)
                assert parsed_finish is not None
            except ValueError as e:
                raise AssertionError(f"finish_time is not valid ISO 8601: {finish_time_str}") from e


class TestAddMessageMethodExtension:
    """
    Unit tests for add_message() method extension with optional method parameter.

    These tests verify the add_message() method correctly handles the optional
    `method` parameter for email flow attribution.

    **Validates: Requirements 3.1, 3.2, 3.3, 3.4**
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_add_message_with_method_adds_field_to_jsonb(
        self,
        telegram_id: int,
        model_name: str,
        content: str,
    ):
        """
        Test that add_message() with method parameter adds method field to JSONB.

        **Validates: Requirements 3.1, 3.2**

        WHEN an LLM response is added to conversation history during email flow
        THEN the System SHALL call an extended add_message() method that accepts
        an optional method parameter, and the method field SHALL be included in
        the message object.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Add message with method parameter
            result = service.add_message(session.id, "assistant", content, method="LYRA")
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(result)

            # Verify the message has the method field
            history = result.conversation_history
            assert len(history) == 1, "Should have exactly one message"
            assert history[0]["role"] == "assistant"
            assert history[0]["content"] == content
            assert "method" in history[0], "Message should have method field"
            assert history[0]["method"] == "LYRA", "Method should be LYRA"
            assert "timestamp" in history[0], "Message should have timestamp"

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_add_message_without_method_no_field_backward_compatible(
        self,
        telegram_id: int,
        model_name: str,
        content: str,
    ):
        """
        Test that add_message() without method parameter maintains backward compatibility.

        **Validates: Requirements 3.3, 3.4**

        WHEN storing user messages or system messages THEN the method field SHALL
        be omitted (backward compatible). WHEN querying conversation history THEN
        the System SHALL return all messages including those with and without
        method attribution.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.CRAFT)
            assert session is not None, "Session should be created successfully"

            # Add message WITHOUT method parameter (backward compatible)
            result = service.add_message(session.id, "user", content)
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(result)

            # Verify the message does NOT have the method field
            history = result.conversation_history
            assert len(history) == 1, "Should have exactly one message"
            assert history[0]["role"] == "user"
            assert history[0]["content"] == content
            assert "method" not in history[0], "Message should NOT have method field"
            assert "timestamp" in history[0], "Message should have timestamp"

    def test_add_message_method_values_lyra_craft_ggl(self):
        """
        Test that add_message() correctly stores LYRA, CRAFT, and GGL method values.

        **Validates: Requirements 3.1, 3.2**

        WHEN storing conversation messages with method attribution THEN the System
        SHALL use the format {"role": "assistant", "content": "...", "timestamp": "...",
        "method": "LYRA|CRAFT|GGL"}
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Add messages with each method value
            methods = ["LYRA", "CRAFT", "GGL"]
            for method in methods:
                result = service.add_message(
                    session.id, "assistant", f"Response from {method}", method=method
                )
                assert result is not None, f"add_message with method={method} should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Verify all messages have correct method values
            history = session.conversation_history
            assert len(history) == 3, "Should have exactly three messages"

            for i, method in enumerate(methods):
                assert history[i]["role"] == "assistant"
                assert history[i]["content"] == f"Response from {method}"
                assert history[i]["method"] == method, f"Method should be {method}"
                assert "timestamp" in history[i], "Message should have timestamp"

    def test_add_message_mixed_with_and_without_method(self):
        """
        Test that conversation history can contain messages with and without method.

        **Validates: Requirements 3.3, 3.4**

        WHEN querying conversation history THEN the System SHALL return all messages
        including those with and without method attribution.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Add user message (no method)
            result = service.add_message(session.id, "user", "Original prompt")
            assert result is not None

            # Add assistant messages with methods (email flow)
            result = service.add_message(session.id, "assistant", "LYRA response", method="LYRA")
            assert result is not None
            result = service.add_message(session.id, "assistant", "CRAFT response", method="CRAFT")
            assert result is not None
            result = service.add_message(session.id, "assistant", "GGL response", method="GGL")
            assert result is not None

            # Refresh session to get final state
            db_session.refresh(session)

            # Verify conversation history contains all messages
            history = session.conversation_history
            assert len(history) == 4, "Should have exactly four messages"

            # First message: user, no method
            assert history[0]["role"] == "user"
            assert history[0]["content"] == "Original prompt"
            assert "method" not in history[0], "User message should NOT have method"

            # Second message: assistant with LYRA
            assert history[1]["role"] == "assistant"
            assert history[1]["content"] == "LYRA response"
            assert history[1]["method"] == "LYRA"

            # Third message: assistant with CRAFT
            assert history[2]["role"] == "assistant"
            assert history[2]["content"] == "CRAFT response"
            assert history[2]["method"] == "CRAFT"

            # Fourth message: assistant with GGL
            assert history[3]["role"] == "assistant"
            assert history[3]["content"] == "GGL response"
            assert history[3]["method"] == "GGL"

    def test_add_message_with_none_method_no_field(self):
        """
        Test that add_message() with method=None does not add method field.

        **Validates: Requirements 3.3, 3.4**

        Explicitly passing method=None should behave the same as not passing
        the method parameter at all.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            assert session is not None, "Session should be created successfully"

            # Add message with method=None explicitly
            result = service.add_message(session.id, "assistant", "Response", method=None)
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(result)

            # Verify the message does NOT have the method field
            history = result.conversation_history
            assert len(history) == 1, "Should have exactly one message"
            assert "method" not in history[0], "Message should NOT have method field when None"


class TestEmailFlowTokenAccumulation:
    """
    **Feature: email-flow-session-tracking, Property 2: Token accumulation across all methods**
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

    Property 2: Token accumulation across all methods
    *For any* email flow session, the final `tokens_total` SHALL equal the sum of
    input and output tokens from all three optimization methods (LYRA + CRAFT + GGL).

    This test class verifies that when an email flow session runs all three
    optimization methods, the token counts are correctly accumulated.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_input=st.integers(min_value=0, max_value=10000),
        lyra_output=st.integers(min_value=0, max_value=10000),
        craft_input=st.integers(min_value=0, max_value=10000),
        craft_output=st.integers(min_value=0, max_value=10000),
        ggl_input=st.integers(min_value=0, max_value=10000),
        ggl_output=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_email_flow_tokens_total_equals_sum_of_all_methods(
        self,
        telegram_id: int,
        model_name: str,
        lyra_input: int,
        lyra_output: int,
        craft_input: int,
        craft_output: int,
        ggl_input: int,
        ggl_output: int,
    ):
        """
        **Feature: email-flow-session-tracking, Property 2: Token accumulation across all methods**
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

        For any email flow session with tokens from LYRA, CRAFT, and GGL optimizations,
        the final tokens_total SHALL equal the sum of all input and output tokens.

        This simulates the email flow where:
        1. Session is created with method="ALL"
        2. LYRA optimization adds tokens (Requirement 2.1)
        3. CRAFT optimization adds tokens (Requirement 2.2)
        4. GGL optimization adds tokens (Requirement 2.3)
        5. Final tokens_total equals sum of all (Requirement 2.4)
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"
            assert session.optimization_method == "ALL", "Email flow session should have method ALL"

            # Simulate LYRA optimization - add tokens (Requirement 2.1)
            result = service.add_tokens(session.id, lyra_input, lyra_output)
            assert result is not None, "add_tokens for LYRA should succeed"

            # Simulate CRAFT optimization - add tokens (Requirement 2.2)
            result = service.add_tokens(session.id, craft_input, craft_output)
            assert result is not None, "add_tokens for CRAFT should succeed"

            # Simulate GGL optimization - add tokens (Requirement 2.3)
            result = service.add_tokens(session.id, ggl_input, ggl_output)
            assert result is not None, "add_tokens for GGL should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Calculate expected totals
            expected_input = lyra_input + craft_input + ggl_input
            expected_output = lyra_output + craft_output + ggl_output
            expected_total = expected_input + expected_output

            # Property assertion: tokens_total equals sum of all tokens (Requirement 2.4)
            assert session.tokens_total == expected_total, (
                f"tokens_total ({session.tokens_total}) should equal "
                f"sum of all tokens ({expected_total})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_input=st.integers(min_value=0, max_value=10000),
        lyra_output=st.integers(min_value=0, max_value=10000),
        craft_input=st.integers(min_value=0, max_value=10000),
        craft_output=st.integers(min_value=0, max_value=10000),
        ggl_input=st.integers(min_value=0, max_value=10000),
        ggl_output=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_email_flow_input_tokens_equals_sum_of_all_methods(
        self,
        telegram_id: int,
        model_name: str,
        lyra_input: int,
        lyra_output: int,
        craft_input: int,
        craft_output: int,
        ggl_input: int,
        ggl_output: int,
    ):
        """
        **Feature: email-flow-session-tracking, Property 2: Token accumulation across all methods**
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

        For any email flow session, the final input_tokens SHALL equal the sum of
        input tokens from all three optimization methods.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Simulate all three optimizations
            service.add_tokens(session.id, lyra_input, lyra_output)
            service.add_tokens(session.id, craft_input, craft_output)
            service.add_tokens(session.id, ggl_input, ggl_output)

            # Refresh session to get final state
            db_session.refresh(session)

            # Calculate expected input total
            expected_input = lyra_input + craft_input + ggl_input

            # Property assertion: input_tokens equals sum of all input tokens
            assert session.input_tokens == expected_input, (
                f"input_tokens ({session.input_tokens}) should equal "
                f"sum of all input tokens ({expected_input})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_input=st.integers(min_value=0, max_value=10000),
        lyra_output=st.integers(min_value=0, max_value=10000),
        craft_input=st.integers(min_value=0, max_value=10000),
        craft_output=st.integers(min_value=0, max_value=10000),
        ggl_input=st.integers(min_value=0, max_value=10000),
        ggl_output=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_email_flow_output_tokens_equals_sum_of_all_methods(
        self,
        telegram_id: int,
        model_name: str,
        lyra_input: int,
        lyra_output: int,
        craft_input: int,
        craft_output: int,
        ggl_input: int,
        ggl_output: int,
    ):
        """
        **Feature: email-flow-session-tracking, Property 2: Token accumulation across all methods**
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

        For any email flow session, the final output_tokens SHALL equal the sum of
        output tokens from all three optimization methods.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Simulate all three optimizations
            service.add_tokens(session.id, lyra_input, lyra_output)
            service.add_tokens(session.id, craft_input, craft_output)
            service.add_tokens(session.id, ggl_input, ggl_output)

            # Refresh session to get final state
            db_session.refresh(session)

            # Calculate expected output total
            expected_output = lyra_output + craft_output + ggl_output

            # Property assertion: output_tokens equals sum of all output tokens
            assert session.output_tokens == expected_output, (
                f"output_tokens ({session.output_tokens}) should equal "
                f"sum of all output tokens ({expected_output})"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_input=st.integers(min_value=0, max_value=10000),
        lyra_output=st.integers(min_value=0, max_value=10000),
        craft_input=st.integers(min_value=0, max_value=10000),
        craft_output=st.integers(min_value=0, max_value=10000),
        ggl_input=st.integers(min_value=0, max_value=10000),
        ggl_output=st.integers(min_value=0, max_value=10000),
    )
    @settings(max_examples=100)
    def test_email_flow_tokens_total_equals_input_plus_output(
        self,
        telegram_id: int,
        model_name: str,
        lyra_input: int,
        lyra_output: int,
        craft_input: int,
        craft_output: int,
        ggl_input: int,
        ggl_output: int,
    ):
        """
        **Feature: email-flow-session-tracking, Property 2: Token accumulation across all methods**
        **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

        For any email flow session, tokens_total SHALL equal input_tokens + output_tokens.
        This is an invariant that must hold after all token additions.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Simulate all three optimizations
            service.add_tokens(session.id, lyra_input, lyra_output)
            service.add_tokens(session.id, craft_input, craft_output)
            service.add_tokens(session.id, ggl_input, ggl_output)

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: tokens_total equals input_tokens + output_tokens
            expected_total = session.input_tokens + session.output_tokens
            assert session.tokens_total == expected_total, (
                f"tokens_total ({session.tokens_total}) should equal "
                f"input_tokens + output_tokens ({expected_total})"
            )


class TestEmailFlowConversationHistoryMethodAttribution:
    """
    **Feature: email-flow-session-tracking, Property 3: Conversation history contains all method responses**
    **Validates: Requirements 3.1, 3.2**

    Property 3: Conversation history contains all method responses
    *For any* completed email flow session, the conversation history SHALL contain
    exactly 3 assistant messages with `method` field set to "LYRA", "CRAFT", and "GGL"
    respectively.

    This test class verifies that when an email flow session runs all three
    optimization methods, the conversation history correctly records each response
    with proper method attribution.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_response=st.text(min_size=1, max_size=500),
        craft_response=st.text(min_size=1, max_size=500),
        ggl_response=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_email_flow_conversation_history_has_exactly_three_method_attributed_messages(
        self,
        telegram_id: int,
        model_name: str,
        lyra_response: str,
        craft_response: str,
        ggl_response: str,
    ):
        """
        **Feature: email-flow-session-tracking, Property 3: Conversation history contains all method responses**
        **Validates: Requirements 3.1, 3.2**

        For any completed email flow session, the conversation history SHALL contain
        exactly 3 assistant messages with method attribution.

        This simulates the email flow where:
        1. Session is created with method="ALL"
        2. LYRA response is added with method="LYRA" (Requirement 3.1)
        3. CRAFT response is added with method="CRAFT" (Requirement 3.1)
        4. GGL response is added with method="GGL" (Requirement 3.1)
        5. All three methods are present in history (Requirement 3.2)
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"
            assert session.optimization_method == "ALL", "Email flow session should have method ALL"

            # Simulate LYRA optimization - add response with method attribution (Requirement 3.1)
            result = service.add_message(session.id, "assistant", lyra_response, method="LYRA")
            assert result is not None, "add_message for LYRA should succeed"

            # Simulate CRAFT optimization - add response with method attribution (Requirement 3.1)
            result = service.add_message(session.id, "assistant", craft_response, method="CRAFT")
            assert result is not None, "add_message for CRAFT should succeed"

            # Simulate GGL optimization - add response with method attribution (Requirement 3.1)
            result = service.add_message(session.id, "assistant", ggl_response, method="GGL")
            assert result is not None, "add_message for GGL should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Get assistant messages with method attribution
            assistant_messages = [
                msg
                for msg in session.conversation_history
                if msg.get("role") == "assistant" and "method" in msg
            ]

            # Property assertion: exactly 3 assistant messages with method attribution (Requirement 3.2)
            assert len(assistant_messages) == 3, (
                f"Should have exactly 3 assistant messages with method attribution, "
                f"got: {len(assistant_messages)}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_response=st.text(min_size=1, max_size=500),
        craft_response=st.text(min_size=1, max_size=500),
        ggl_response=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_email_flow_conversation_history_contains_all_three_methods(
        self,
        telegram_id: int,
        model_name: str,
        lyra_response: str,
        craft_response: str,
        ggl_response: str,
    ):
        """
        **Feature: email-flow-session-tracking, Property 3: Conversation history contains all method responses**
        **Validates: Requirements 3.1, 3.2**

        For any completed email flow session, the conversation history SHALL contain
        messages with method field set to "LYRA", "CRAFT", and "GGL".
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Simulate all three optimizations with method attribution
            service.add_message(session.id, "assistant", lyra_response, method="LYRA")
            service.add_message(session.id, "assistant", craft_response, method="CRAFT")
            service.add_message(session.id, "assistant", ggl_response, method="GGL")

            # Refresh session to get final state
            db_session.refresh(session)

            # Extract methods from conversation history
            methods_in_history = {
                msg.get("method")
                for msg in session.conversation_history
                if msg.get("role") == "assistant" and "method" in msg
            }

            # Property assertion: all three methods are present (Requirement 3.2)
            expected_methods = {"LYRA", "CRAFT", "GGL"}
            assert methods_in_history == expected_methods, (
                f"Conversation history should contain methods {expected_methods}, "
                f"got: {methods_in_history}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_response=st.text(min_size=1, max_size=500),
        craft_response=st.text(min_size=1, max_size=500),
        ggl_response=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_email_flow_conversation_history_preserves_response_content(
        self,
        telegram_id: int,
        model_name: str,
        lyra_response: str,
        craft_response: str,
        ggl_response: str,
    ):
        """
        **Feature: email-flow-session-tracking, Property 3: Conversation history contains all method responses**
        **Validates: Requirements 3.1, 3.2**

        For any completed email flow session, the conversation history SHALL preserve
        the original response content for each method.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Simulate all three optimizations with method attribution
            service.add_message(session.id, "assistant", lyra_response, method="LYRA")
            service.add_message(session.id, "assistant", craft_response, method="CRAFT")
            service.add_message(session.id, "assistant", ggl_response, method="GGL")

            # Refresh session to get final state
            db_session.refresh(session)

            # Build a map of method -> content from conversation history
            method_content_map = {
                msg.get("method"): msg.get("content")
                for msg in session.conversation_history
                if msg.get("role") == "assistant" and "method" in msg
            }

            # Property assertion: content is preserved for each method
            assert method_content_map.get("LYRA") == lyra_response, (
                f"LYRA response content should be preserved, "
                f"expected: {lyra_response!r}, got: {method_content_map.get('LYRA')!r}"
            )
            assert method_content_map.get("CRAFT") == craft_response, (
                f"CRAFT response content should be preserved, "
                f"expected: {craft_response!r}, got: {method_content_map.get('CRAFT')!r}"
            )
            assert method_content_map.get("GGL") == ggl_response, (
                f"GGL response content should be preserved, "
                f"expected: {ggl_response!r}, got: {method_content_map.get('GGL')!r}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        lyra_response=st.text(min_size=1, max_size=500),
        craft_response=st.text(min_size=1, max_size=500),
        ggl_response=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_email_flow_conversation_history_messages_have_timestamps(
        self,
        telegram_id: int,
        model_name: str,
        lyra_response: str,
        craft_response: str,
        ggl_response: str,
    ):
        """
        **Feature: email-flow-session-tracking, Property 3: Conversation history contains all method responses**
        **Validates: Requirements 3.1, 3.2**

        For any completed email flow session, each assistant message with method
        attribution SHALL have a timestamp field.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session with method="ALL" (email flow)
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.ALL)
            assert session is not None, "Session should be created successfully"

            # Simulate all three optimizations with method attribution
            service.add_message(session.id, "assistant", lyra_response, method="LYRA")
            service.add_message(session.id, "assistant", craft_response, method="CRAFT")
            service.add_message(session.id, "assistant", ggl_response, method="GGL")

            # Refresh session to get final state
            db_session.refresh(session)

            # Get assistant messages with method attribution
            assistant_messages = [
                msg
                for msg in session.conversation_history
                if msg.get("role") == "assistant" and "method" in msg
            ]

            # Property assertion: all messages have timestamps
            for msg in assistant_messages:
                assert "timestamp" in msg, (
                    f"Message with method {msg.get('method')} should have a timestamp"
                )
                # Verify timestamp is a valid ISO8601 string
                timestamp_str = msg.get("timestamp")
                assert timestamp_str is not None, "Timestamp should not be None"
                # Basic validation that it looks like an ISO8601 timestamp
                assert "T" in timestamp_str, (
                    f"Timestamp should be ISO8601 format, got: {timestamp_str}"
                )


class TestEmailFlowBackwardCompatibility:
    """
    **Feature: email-flow-session-tracking, Property 6: Backward compatibility of add_message**
    **Validates: Requirements 3.3, 3.4**

    Property 6: Backward compatibility of add_message
    *For any* call to `add_message()` without the `method` parameter, the resulting
    conversation history entry SHALL NOT contain a `method` field.

    This test class verifies that the add_message() method maintains backward
    compatibility when the optional `method` parameter is not provided.
    """

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        role=st.sampled_from(["user", "assistant", "system"]),
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_add_message_without_method_excludes_method_field(
        self,
        telegram_id: int,
        model_name: str,
        role: str,
        content: str,
    ):
        """
        **Feature: email-flow-session-tracking, Property 6: Backward compatibility of add_message**
        **Validates: Requirements 3.3, 3.4**

        For any call to add_message() without the method parameter, the resulting
        conversation history entry SHALL NOT contain a method field.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.CRAFT)
            assert session is not None, "Session should be created successfully"

            # Add message WITHOUT method parameter (backward compatible)
            result = service.add_message(session.id, role, content)
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(result)

            # Property assertion: message does NOT have the method field
            history = result.conversation_history
            assert len(history) == 1, "Should have exactly one message"
            assert history[0]["role"] == role, f"Role should be {role}"
            assert history[0]["content"] == content, "Content should match"
            assert "method" not in history[0], (
                f"Message should NOT have method field when add_message() is called "
                f"without method parameter, but found: {history[0]}"
            )
            assert "timestamp" in history[0], "Message should have timestamp"

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        content=st.text(min_size=1, max_size=500),
    )
    @settings(max_examples=100)
    def test_add_message_with_none_method_excludes_method_field(
        self,
        telegram_id: int,
        model_name: str,
        content: str,
    ):
        """
        **Feature: email-flow-session-tracking, Property 6: Backward compatibility of add_message**
        **Validates: Requirements 3.3, 3.4**

        For any call to add_message() with method=None explicitly, the resulting
        conversation history entry SHALL NOT contain a method field.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.CRAFT)
            assert session is not None, "Session should be created successfully"

            # Add message with method=None explicitly
            result = service.add_message(session.id, "user", content, method=None)
            assert result is not None, "add_message should succeed"

            # Refresh session to get final state
            db_session.refresh(result)

            # Property assertion: message does NOT have the method field
            history = result.conversation_history
            assert len(history) == 1, "Should have exactly one message"
            assert "method" not in history[0], (
                f"Message should NOT have method field when method=None, but found: {history[0]}"
            )

    @given(
        telegram_id=st.integers(min_value=1, max_value=2**63 - 1),
        model_name=model_name_strategy,
        num_messages=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=100)
    def test_multiple_messages_without_method_all_exclude_method_field(
        self,
        telegram_id: int,
        model_name: str,
        num_messages: int,
    ):
        """
        **Feature: email-flow-session-tracking, Property 6: Backward compatibility of add_message**
        **Validates: Requirements 3.3, 3.4**

        For any sequence of add_message() calls without the method parameter,
        ALL resulting conversation history entries SHALL NOT contain a method field.
        """
        with get_test_db_session() as db_session:
            # Create a user first (required for foreign key)
            user = _SQLiteUser(telegram_id=telegram_id, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and start a session
            service = _SQLiteSessionService(db_session)
            session = service.start_session(user.id, model_name, OptimizationMethod.CRAFT)
            assert session is not None, "Session should be created successfully"

            # Add multiple messages WITHOUT method parameter
            for i in range(num_messages):
                role = "user" if i % 2 == 0 else "assistant"
                result = service.add_message(session.id, role, f"Message {i}")
                assert result is not None, f"add_message {i} should succeed"

            # Refresh session to get final state
            db_session.refresh(session)

            # Property assertion: ALL messages do NOT have the method field
            history = session.conversation_history
            assert len(history) == num_messages, f"Should have {num_messages} messages"

            for i, msg in enumerate(history):
                assert "method" not in msg, (
                    f"Message {i} should NOT have method field when add_message() "
                    f"is called without method parameter, but found: {msg}"
                )
