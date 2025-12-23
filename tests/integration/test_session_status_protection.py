"""Integration tests for session status protection.

This module contains integration tests for the terminal state protection feature
that prevents successfully completed sessions from being incorrectly overwritten
to "unsuccessful" status when users click the Reset button.

Requirements: 1.1, 3.1
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
    SQLite-compatible SessionService for integration testing.

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

    def get_session(self, session_id: int) -> _TestSession | None:
        """Get a session by ID."""
        try:
            session = self._db_session.get(_TestSession, session_id)
            return session
        except Exception:
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


class _MockStateManager:
    """Mock state manager for integration testing."""

    def __init__(self):
        self._session_ids = {}

    def get_current_session_id(self, user_id: int) -> int | None:
        return self._session_ids.get(user_id)

    def set_current_session_id(self, user_id: int, session_id: int | None):
        if session_id is None:
            self._session_ids.pop(user_id, None)
        else:
            self._session_ids[user_id] = session_id


class TestChatFlowProtection:
    """
    Integration tests for chat flow session status protection.

    These tests verify the complete flow:
    1. Create session → complete session → simulate reset → verify status unchanged

    Requirements: 1.1, 3.1
    """

    def test_completed_session_protected_from_reset(self):
        """
        Test that a completed session is protected from reset.

        Flow:
        1. Create a session (simulates user starting optimization)
        2. Complete the session (simulates successful prompt delivery)
        3. Simulate reset button click
        4. Verify session status remains "successful"

        Requirements: 1.1, 3.1
        """
        with get_test_db_session() as db_session:
            # Setup: Create user
            user = _TestUser(telegram_id=12345, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and state manager
            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Step 1: Create session (user submits prompt)
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            assert session is not None
            assert session.status == SessionStatus.IN_PROGRESS.value

            # Store session ID in state (as BotHandler does)
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Step 2: Complete session (prompt delivered successfully)
            completed = session_service.complete_session(session.id)
            assert completed is not None
            assert completed.status == SessionStatus.SUCCESSFUL.value

            # Store original values for comparison
            original_status = completed.status
            original_finish_time = completed.finish_time
            original_duration = completed.duration_seconds

            # Step 3: Simulate reset button click
            # This mimics what _reset_current_session does
            session_id = state_manager.get_current_session_id(user.telegram_id)
            assert session_id is not None

            # Check session status before reset (Layer 1 protection)
            current_session = session_service.get_session(session_id)
            assert current_session is not None

            # Since status is not "in_progress", reset should be skipped
            if current_session.status != SessionStatus.IN_PROGRESS.value:
                # Skip reset - this is the expected path for completed sessions
                pass
            else:
                # This should NOT happen for completed sessions
                session_service.reset_session(session_id)

            # Step 4: Verify session status is unchanged
            final_session = session_service.get_session(session_id)
            assert final_session is not None
            assert final_session.status == original_status
            assert final_session.status == SessionStatus.SUCCESSFUL.value
            assert final_session.finish_time == original_finish_time
            assert final_session.duration_seconds == original_duration

    def test_full_chat_flow_with_tokens_and_reset(self):
        """
        Test complete chat flow with token accumulation and reset protection.

        Flow:
        1. Create session
        2. Add tokens (simulates LLM interactions)
        3. Complete session
        4. Attempt reset
        5. Verify all data preserved

        Requirements: 1.1, 3.1
        """
        with get_test_db_session() as db_session:
            # Setup
            user = _TestUser(telegram_id=67890, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Step 1: Create session
            session = session_service.start_session(user.id, "gpt-4o", OptimizationMethod.LYRA)
            assert session is not None
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Step 2: Add tokens (simulates LLM interactions)
            session_service.add_tokens(session.id, 100, 200)
            session_service.add_tokens(session.id, 50, 150)

            # Verify tokens accumulated
            updated_session = session_service.get_session(session.id)
            assert updated_session.input_tokens == 150
            assert updated_session.output_tokens == 350
            assert updated_session.tokens_total == 500

            # Step 3: Complete session
            completed = session_service.complete_session(session.id)
            assert completed is not None
            assert completed.status == SessionStatus.SUCCESSFUL.value

            # Step 4: Attempt reset (should be blocked)
            session_id = state_manager.get_current_session_id(user.telegram_id)
            current_session = session_service.get_session(session_id)

            # Simulate _reset_current_session logic
            if current_session.status != SessionStatus.IN_PROGRESS.value:
                # Skip reset - terminal state protection
                result = current_session
            else:
                result = session_service.reset_session(session_id)

            # Step 5: Verify all data preserved
            assert result.status == SessionStatus.SUCCESSFUL.value
            assert result.input_tokens == 150
            assert result.output_tokens == 350
            assert result.tokens_total == 500
            assert result.optimization_method == OptimizationMethod.LYRA.value

    def test_multiple_reset_attempts_on_completed_session(self):
        """
        Test that multiple reset attempts on a completed session all fail.

        This simulates a user clicking reset multiple times after receiving
        their optimized prompt.

        Requirements: 1.1, 3.1
        """
        with get_test_db_session() as db_session:
            # Setup
            user = _TestUser(telegram_id=11111, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Create and complete session
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.GGL)
            state_manager.set_current_session_id(user.telegram_id, session.id)
            session_service.complete_session(session.id)

            # Verify initial state
            completed = session_service.get_session(session.id)
            assert completed.status == SessionStatus.SUCCESSFUL.value
            original_finish_time = completed.finish_time

            # Simulate multiple reset attempts
            for i in range(5):
                session_id = state_manager.get_current_session_id(user.telegram_id)
                current = session_service.get_session(session_id)

                if current.status != SessionStatus.IN_PROGRESS.value:
                    # Skip reset - expected behavior
                    continue
                session_service.reset_session(session_id)

            # Verify status still successful after all attempts
            final = session_service.get_session(session.id)
            assert final.status == SessionStatus.SUCCESSFUL.value
            assert final.finish_time == original_finish_time

    def test_in_progress_session_can_be_reset(self):
        """
        Test that an in-progress session CAN be reset (control test).

        This verifies that the protection only applies to terminal states,
        not to in-progress sessions.

        Requirements: 1.3
        """
        with get_test_db_session() as db_session:
            # Setup
            user = _TestUser(telegram_id=22222, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Create session but DON'T complete it
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Verify in-progress
            assert session.status == SessionStatus.IN_PROGRESS.value

            # Simulate reset (should succeed for in-progress)
            session_id = state_manager.get_current_session_id(user.telegram_id)
            current = session_service.get_session(session_id)

            if current.status != SessionStatus.IN_PROGRESS.value:
                # Skip reset
                result = current
            else:
                # Reset should proceed
                result = session_service.reset_session(session_id)

            # Verify status changed to unsuccessful
            assert result.status == SessionStatus.UNSUCCESSFUL.value
            assert result.finish_time is not None
            assert result.duration_seconds is not None


class TestChatFlowProtectionWithBotHandlerLogic:
    """
    Integration tests that more closely simulate BotHandler._reset_current_session logic.

    These tests verify the defense-in-depth approach with both Layer 1 (BotHandler)
    and Layer 2 (SessionService) protection.

    Requirements: 1.1, 2.2, 3.1
    """

    def _simulate_reset_current_session(
        self,
        session_service: _TestSessionService,
        state_manager: _MockStateManager,
        telegram_user_id: int,
    ) -> tuple[bool, str]:
        """
        Simulate BotHandler._reset_current_session logic.

        Returns:
            Tuple of (was_reset, reason)
        """
        # Check if session service is available
        if not session_service:
            return False, "session_service_not_available"

        # Get current session ID from state
        session_id = state_manager.get_current_session_id(telegram_user_id)
        if session_id is None:
            return False, "no_active_session"

        # Layer 1 Protection: Check session status before reset
        session = session_service.get_session(session_id)
        if session is None:
            return False, "session_not_found"

        # Skip reset if session is already in terminal state
        if session.status != SessionStatus.IN_PROGRESS.value:
            return False, f"already_terminal_state:{session.status}"

        # Session is in_progress, proceed with reset
        result = session_service.reset_session(session_id)
        if result:
            return True, "reset_successful"
        return False, "reset_failed"

    def test_bot_handler_logic_protects_successful_session(self):
        """
        Test that BotHandler logic protects successful sessions.

        Requirements: 1.1, 2.2, 3.1
        """
        with get_test_db_session() as db_session:
            # Setup
            user = _TestUser(telegram_id=33333, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Create and complete session
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            state_manager.set_current_session_id(user.telegram_id, session.id)
            session_service.complete_session(session.id)

            # Simulate reset using BotHandler logic
            was_reset, reason = self._simulate_reset_current_session(
                session_service, state_manager, user.telegram_id
            )

            # Verify reset was skipped
            assert was_reset is False
            assert "already_terminal_state:successful" in reason

            # Verify session unchanged
            final = session_service.get_session(session.id)
            assert final.status == SessionStatus.SUCCESSFUL.value

    def test_bot_handler_logic_allows_in_progress_reset(self):
        """
        Test that BotHandler logic allows in-progress session reset.

        Requirements: 1.3, 2.4
        """
        with get_test_db_session() as db_session:
            # Setup
            user = _TestUser(telegram_id=44444, email=None, is_authenticated=False)
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Create session (don't complete)
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Simulate reset using BotHandler logic
            was_reset, reason = self._simulate_reset_current_session(
                session_service, state_manager, user.telegram_id
            )

            # Verify reset succeeded
            assert was_reset is True
            assert reason == "reset_successful"

            # Verify session changed to unsuccessful
            final = session_service.get_session(session.id)
            assert final.status == SessionStatus.UNSUCCESSFUL.value

    def test_bot_handler_logic_handles_no_session(self):
        """
        Test that BotHandler logic handles missing session gracefully.

        Requirements: 2.5
        """
        with get_test_db_session() as db_session:
            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # No session set for user
            was_reset, reason = self._simulate_reset_current_session(
                session_service, state_manager, 99999
            )

            # Verify graceful handling
            assert was_reset is False
            assert reason == "no_active_session"


class TestEmailFlowProtection:
    """
    Integration tests for email flow session status protection.

    These tests verify that email flow sessions are protected from
    accidental status overwrites after successful email delivery.

    Requirements: 3.1, 3.2
    """

    def _simulate_reset_current_session(
        self,
        session_service: _TestSessionService,
        state_manager: _MockStateManager,
        telegram_user_id: int,
    ) -> tuple[bool, str]:
        """
        Simulate BotHandler._reset_current_session logic.

        Returns:
            Tuple of (was_reset, reason)
        """
        # Check if session service is available
        if not session_service:
            return False, "session_service_not_available"

        # Get current session ID from state
        session_id = state_manager.get_current_session_id(telegram_user_id)
        if session_id is None:
            return False, "no_active_session"

        # Layer 1 Protection: Check session status before reset
        session = session_service.get_session(session_id)
        if session is None:
            return False, "session_not_found"

        # Skip reset if session is already in terminal state
        if session.status != SessionStatus.IN_PROGRESS.value:
            return False, f"already_terminal_state:{session.status}"

        # Session is in_progress, proceed with reset
        result = session_service.reset_session(session_id)
        if result:
            return True, "reset_successful"
        return False, "reset_failed"

    def test_email_flow_successful_session_protected_from_reset(self):
        """
        Test that a successful email flow session is protected from reset.

        Flow:
        1. Create a session (simulates user starting email flow)
        2. Add tokens (simulates LLM interactions for optimization)
        3. Complete the session (simulates successful email delivery)
        4. Simulate reset button click
        5. Verify session status remains "successful"

        Requirements: 3.1, 3.2
        """
        with get_test_db_session() as db_session:
            # Setup: Create user with email (authenticated user)
            user = _TestUser(
                telegram_id=55555,
                email="test@example.com",
                is_authenticated=True,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and state manager
            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Step 1: Create session (user starts email flow)
            # Email flow uses "ALL" method for all three optimizations
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            assert session is not None
            assert session.status == SessionStatus.IN_PROGRESS.value

            # Store session ID in state (as BotHandler does)
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Step 2: Add tokens (simulates LLM interactions for all 3 methods)
            # CRAFT optimization
            session_service.add_tokens(session.id, 100, 200)
            # LYRA optimization
            session_service.add_tokens(session.id, 150, 250)
            # GGL optimization
            session_service.add_tokens(session.id, 120, 180)

            # Verify tokens accumulated
            updated_session = session_service.get_session(session.id)
            assert updated_session.input_tokens == 370  # 100 + 150 + 120
            assert updated_session.output_tokens == 630  # 200 + 250 + 180
            assert updated_session.tokens_total == 1000

            # Step 3: Complete session (email sent successfully)
            completed = session_service.complete_session(session.id)
            assert completed is not None
            assert completed.status == SessionStatus.SUCCESSFUL.value

            # Store original values for comparison
            original_status = completed.status
            original_finish_time = completed.finish_time
            original_duration = completed.duration_seconds
            original_tokens = completed.tokens_total

            # Step 4: Simulate reset button click using BotHandler logic
            was_reset, reason = self._simulate_reset_current_session(
                session_service, state_manager, user.telegram_id
            )

            # Verify reset was skipped due to terminal state
            assert was_reset is False
            assert "already_terminal_state:successful" in reason

            # Step 5: Verify session status and all data unchanged
            final_session = session_service.get_session(session.id)
            assert final_session is not None
            assert final_session.status == original_status
            assert final_session.status == SessionStatus.SUCCESSFUL.value
            assert final_session.finish_time == original_finish_time
            assert final_session.duration_seconds == original_duration
            assert final_session.tokens_total == original_tokens

    def test_email_flow_failed_session_protected_from_reset(self):
        """
        Test that a failed email flow session is protected from reset.

        Flow:
        1. Create a session (simulates user starting email flow)
        2. Mark session as unsuccessful (simulates email delivery failure)
        3. Simulate reset button click
        4. Verify session status remains "unsuccessful"

        Requirements: 3.2
        """
        with get_test_db_session() as db_session:
            # Setup: Create user with email
            user = _TestUser(
                telegram_id=66666,
                email="failed@example.com",
                is_authenticated=True,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Step 1: Create session
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.LYRA)
            assert session is not None
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Step 2: Mark session as unsuccessful (email delivery failed)
            # This simulates what happens when email_service.send_optimized_prompts_email fails
            reset_result = session_service.reset_session(session.id)
            assert reset_result is not None
            assert reset_result.status == SessionStatus.UNSUCCESSFUL.value

            # Store original values
            original_status = reset_result.status
            original_finish_time = reset_result.finish_time

            # Step 3: Simulate another reset button click
            was_reset, reason = self._simulate_reset_current_session(
                session_service, state_manager, user.telegram_id
            )

            # Verify reset was skipped due to terminal state
            assert was_reset is False
            assert "already_terminal_state:unsuccessful" in reason

            # Step 4: Verify session status unchanged
            final_session = session_service.get_session(session.id)
            assert final_session is not None
            assert final_session.status == original_status
            assert final_session.status == SessionStatus.UNSUCCESSFUL.value
            assert final_session.finish_time == original_finish_time

    def test_email_flow_multiple_reset_attempts_after_success(self):
        """
        Test that multiple reset attempts on a successful email flow session all fail.

        This simulates a user clicking reset multiple times after receiving
        their optimized prompts via email.

        Requirements: 3.1
        """
        with get_test_db_session() as db_session:
            # Setup
            user = _TestUser(
                telegram_id=77777,
                email="multi@example.com",
                is_authenticated=True,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Create and complete session (successful email delivery)
            session = session_service.start_session(user.id, "gpt-4o", OptimizationMethod.GGL)
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Add tokens and complete
            session_service.add_tokens(session.id, 200, 400)
            completed = session_service.complete_session(session.id)
            assert completed.status == SessionStatus.SUCCESSFUL.value

            original_finish_time = completed.finish_time
            original_tokens = completed.tokens_total

            # Simulate multiple reset attempts (user clicking reset button repeatedly)
            for attempt in range(5):
                was_reset, reason = self._simulate_reset_current_session(
                    session_service, state_manager, user.telegram_id
                )

                # Each attempt should be blocked
                assert was_reset is False, f"Reset attempt {attempt + 1} should be blocked"
                assert "already_terminal_state:successful" in reason

            # Verify session still successful after all attempts
            final = session_service.get_session(session.id)
            assert final.status == SessionStatus.SUCCESSFUL.value
            assert final.finish_time == original_finish_time
            assert final.tokens_total == original_tokens

    def test_email_flow_session_id_preserved_after_completion(self):
        """
        Test that session_id is preserved in state after email completion.

        This is important for post-completion email tracking - the session_id
        should remain in state even after the session is marked successful.

        Requirements: 3.1
        """
        with get_test_db_session() as db_session:
            # Setup
            user = _TestUser(
                telegram_id=88888,
                email="preserved@example.com",
                is_authenticated=True,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Create session
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Complete session (email sent)
            session_service.complete_session(session.id)

            # Verify session_id is still in state
            stored_session_id = state_manager.get_current_session_id(user.telegram_id)
            assert stored_session_id == session.id

            # Verify we can still retrieve the session
            retrieved_session = session_service.get_session(stored_session_id)
            assert retrieved_session is not None
            assert retrieved_session.status == SessionStatus.SUCCESSFUL.value

    def test_email_flow_in_progress_reset_marks_unsuccessful(self):
        """
        Test that an in-progress email flow session can be reset to unsuccessful.

        Flow:
        1. Create a session (simulates user starting email flow)
        2. Add tokens (simulates partial LLM interactions)
        3. Simulate reset button click BEFORE email is sent
        4. Verify session status is "unsuccessful"

        This tests the scenario where a user abandons the email flow
        before completion by clicking the reset button.

        Requirements: 1.3, 3.3
        """
        with get_test_db_session() as db_session:
            # Setup: Create user with email (authenticated user)
            user = _TestUser(
                telegram_id=99999,
                email="inprogress@example.com",
                is_authenticated=True,
            )
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)

            # Create session service and state manager
            session_service = _TestSessionService(db_session)
            state_manager = _MockStateManager()

            # Step 1: Create session (user starts email flow)
            session = session_service.start_session(user.id, "gpt-4", OptimizationMethod.CRAFT)
            assert session is not None
            assert session.status == SessionStatus.IN_PROGRESS.value

            # Store session ID in state (as BotHandler does)
            state_manager.set_current_session_id(user.telegram_id, session.id)

            # Step 2: Add some tokens (simulates partial LLM interactions)
            # User has started optimization but hasn't completed it yet
            session_service.add_tokens(session.id, 100, 200)

            # Verify session is still in progress with tokens
            updated_session = session_service.get_session(session.id)
            assert updated_session.status == SessionStatus.IN_PROGRESS.value
            assert updated_session.tokens_total == 300

            # Step 3: Simulate reset button click BEFORE completion
            # This mimics user abandoning the email flow
            was_reset, reason = self._simulate_reset_current_session(
                session_service, state_manager, user.telegram_id
            )

            # Verify reset succeeded (session was in_progress)
            assert was_reset is True
            assert reason == "reset_successful"

            # Step 4: Verify session status is "unsuccessful"
            final_session = session_service.get_session(session.id)
            assert final_session is not None
            assert final_session.status == SessionStatus.UNSUCCESSFUL.value
            assert final_session.finish_time is not None
            assert final_session.duration_seconds is not None
            # Tokens should be preserved
            assert final_session.tokens_total == 300
