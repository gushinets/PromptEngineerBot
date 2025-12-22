"""
Session service for managing prompt optimization session lifecycle.

This module provides the SessionService class that handles:
- Creating sessions when users submit prompts for optimization
- Tracking session status (in_progress, successful, unsuccessful)
- Accumulating token usage across LLM interactions
- Recording optimization method and model information
- Managing conversation history
- Logging email delivery events
- Handling session timeouts

The service follows graceful degradation principles - session tracking is
analytics/telemetry, not core business logic. Users should never be blocked
because session tracking failed.
"""

import logging
from datetime import UTC, datetime, timedelta
from enum import Enum

from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import joinedload

from telegram_bot.data.database import Session as SessionModel
from telegram_bot.data.database import SessionEmailEvent


logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """
    Session status enumeration.

    Represents the lifecycle state of a prompt optimization session.
    """

    IN_PROGRESS = "in_progress"
    """Session is currently active with optimization in progress."""

    SUCCESSFUL = "successful"
    """Session completed successfully with improved prompt delivered."""

    UNSUCCESSFUL = "unsuccessful"
    """Session terminated by user reset or automatic timeout."""


class OptimizationMethod(str, Enum):
    """
    Optimization method enumeration.

    Represents the prompt improvement technique selected by the user.
    """

    LYRA = "LYRA"
    """LYRA optimization method."""

    CRAFT = "CRAFT"
    """CRAFT optimization method."""

    GGL = "GGL"
    """GGL optimization method."""

    ALL = "ALL"
    """ALL optimization method - used for email flow with all 3 methods."""


class SessionService:
    """
    Service for managing prompt optimization sessions.

    This service handles the complete lifecycle of optimization sessions:
    - Session creation when user submits a prompt
    - Token accumulation across LLM interactions
    - Session completion on successful delivery
    - Session termination on user reset or timeout
    - Email event logging
    - Conversation history management

    Design Principle: Graceful Degradation
    Session tracking is analytics/telemetry, not core business logic.
    All operations return None on error and log the failure, allowing
    the bot to continue processing user requests normally.

    Attributes:
        db_session: SQLAlchemy database session for persistence operations
    """

    def __init__(self, db_session: DBSession) -> None:
        """
        Initialize the SessionService.

        Args:
            db_session: SQLAlchemy database session for persistence operations
        """
        self._db_session = db_session
        logger.debug("SessionService initialized")

    @property
    def db_session(self) -> DBSession:
        """Get the database session."""
        return self._db_session

    def start_session(
        self,
        user_id: int,
        model_name: str,
        method: OptimizationMethod | None = None,
    ) -> SessionModel | None:
        """
        Start a new optimization session.

        Creates a new session record with default values:
        - status: "in_progress"
        - used_followup: False
        - input_tokens: 0
        - output_tokens: 0
        - tokens_total: 0
        - conversation_history: []
        - start_time: current UTC timestamp
        - optimization_method: None (to be set when user selects method)

        Args:
            user_id: Foreign key to users.id
            model_name: LLM model identifier (e.g., "openai/gpt-4", "gpt-4o")
            method: Selected optimization method (LYRA, CRAFT, or GGL), optional.
                    Can be None initially and set later via set_optimization_method().

        Returns:
            Created Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if session creation fails,
            it logs the error and returns None, allowing the bot to continue
            processing the user's request normally.
        """
        try:
            session = SessionModel(
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
            method_str = method.value if method else "None"
            logger.info(
                f"Started session {session.id} for user {user_id} "
                f"with method {method_str} and model {model_name}"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to start session for user {user_id}: {e}")
            self._db_session.rollback()
            return None

    def set_optimization_method(
        self,
        session_id: int,
        method: OptimizationMethod,
    ) -> SessionModel | None:
        """
        Set the optimization method for a session.

        Called when user selects method after session is created.
        This allows session creation to happen before method selection.

        Args:
            session_id: ID of the session to update
            method: Selected optimization method (LYRA, CRAFT, or GGL)

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if setting the method fails,
            it logs the error and returns None. The user's optimization should
            continue regardless of session tracking status.
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for method update")
                return None

            session.optimization_method = method.value

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.info(f"Set optimization method for session {session_id}: {method.value}")
            return session
        except Exception as e:
            logger.error(f"Failed to set optimization method for session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def complete_session(self, session_id: int) -> SessionModel | None:
        """
        Mark session as successful when improved prompt is delivered.

        Sets status to SUCCESSFUL, finish_time to current UTC timestamp,
        and calculates duration_seconds as the difference between
        finish_time and start_time.

        Args:
            session_id: ID of the session to complete

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if completion fails,
            it logs the error and returns None. The user already received
            their improved prompt, so session tracking failure should not
            affect their experience.
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for completion")
                return None

            finish_time = datetime.now(UTC)
            session.status = SessionStatus.SUCCESSFUL.value
            session.finish_time = finish_time

            # Calculate duration in seconds
            if session.start_time is not None:
                duration = finish_time - session.start_time
                session.duration_seconds = int(duration.total_seconds())
            else:
                session.duration_seconds = 0
                logger.warning(f"Session {session_id} has no start_time, setting duration to 0")

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.info(
                f"Completed session {session_id} successfully "
                f"(duration: {session.duration_seconds}s)"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to complete session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def reset_session(self, session_id: int) -> SessionModel | None:
        """
        Mark session as unsuccessful when user resets dialog.

        Sets status to UNSUCCESSFUL and finish_time to current UTC timestamp.
        Preserves all collected metrics (tokens, method, conversation) for analysis.

        Args:
            session_id: ID of the session to reset

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if reset fails,
            it logs the error and returns None. The user's reset action
            should always work regardless of session tracking status.
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for reset")
                return None

            finish_time = datetime.now(UTC)
            session.status = SessionStatus.UNSUCCESSFUL.value
            session.finish_time = finish_time

            # Calculate duration in seconds
            if session.start_time is not None:
                duration = finish_time - session.start_time
                session.duration_seconds = int(duration.total_seconds())
            else:
                session.duration_seconds = 0
                logger.warning(f"Session {session_id} has no start_time, setting duration to 0")

            # Note: All metrics (input_tokens, output_tokens, tokens_total,
            # optimization_method, used_followup, conversation_history) are
            # preserved - we only update status, finish_time, and duration_seconds

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.info(
                f"Reset session {session_id} as unsuccessful "
                f"(duration: {session.duration_seconds}s, "
                f"tokens: {session.tokens_total})"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to reset session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def add_tokens(
        self,
        session_id: int,
        input_tokens: int,
        output_tokens: int,
    ) -> SessionModel | None:
        """
        Add token counts from an LLM interaction.

        Accumulates the provided token counts to the session's existing totals
        and recalculates the total token count.

        Args:
            session_id: ID of the session to update
            input_tokens: Number of input tokens from this LLM call
            output_tokens: Number of output tokens from this LLM response

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if token tracking fails,
            it logs the error and returns None. Token counting is analytics only,
            so the user's experience should not be affected.
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for token update")
                return None

            # Accumulate tokens
            session.input_tokens = (session.input_tokens or 0) + input_tokens
            session.output_tokens = (session.output_tokens or 0) + output_tokens
            session.tokens_total = session.input_tokens + session.output_tokens

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.debug(
                f"Added tokens to session {session_id}: "
                f"+{input_tokens} input, +{output_tokens} output "
                f"(total: {session.tokens_total})"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to add tokens to session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def add_message(
        self,
        session_id: int,
        role: str,
        content: str,
        method: str | None = None,
    ) -> SessionModel | None:
        """
        Add a message to the session's conversation history (JSONB).

        Appends a message object with role, content, and ISO8601 timestamp
        to the session's conversation_history JSONB field.

        Args:
            session_id: ID of the session to add message to
            role: Message role - "user" or "assistant"
            content: Message content text
            method: Optional optimization method that produced this response
                    (LYRA, CRAFT, GGL). Used for email flow attribution.

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if message logging fails,
            it logs the error and returns None. Conversation logging is analytics
            only, so the user's experience should not be affected.
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for message addition")
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
            # Need to create a new list to trigger SQLAlchemy change detection for JSONB
            current_history = session.conversation_history or []
            session.conversation_history = [*current_history, message]

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.debug(
                f"Added {role} message to session {session_id} "
                f"(history length: {len(session.conversation_history)})"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to add message to session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def set_followup_used(self, session_id: int) -> SessionModel | None:
        """
        Mark that FOLLOWUP optimization was used in this session.

        Sets the used_followup flag to True to indicate that the user
        opted for the secondary FOLLOWUP optimization phase where they
        answer clarifying questions to further improve an already-optimized prompt.

        Args:
            session_id: ID of the session to update

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if setting the flag fails,
            it logs the error and returns None. The FOLLOWUP flag is analytics only,
            so the user's experience should not be affected.

        Deprecated:
            Use start_followup() instead, which also sets followup_start_time.
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for followup flag update")
                return None

            session.used_followup = True

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.debug(f"Set used_followup=True for session {session_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to set followup used for session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def start_followup(self, session_id: int) -> SessionModel | None:
        """
        Start followup conversation tracking.

        Sets used_followup=True and followup_start_time to current UTC timestamp.
        This method should be called when a user opts for the FOLLOWUP optimization
        phase where they answer clarifying questions to further improve an
        already-optimized prompt.

        Args:
            session_id: ID of the session to update

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if starting followup fails,
            it logs the error and returns None. Followup tracking is analytics only,
            so the user's experience should not be affected.

        Requirements: 6a.1
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for followup start")
                return None

            session.used_followup = True
            session.followup_start_time = datetime.now(UTC)

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.info(
                f"Started followup for session {session_id} "
                f"at {session.followup_start_time.isoformat()}"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to start followup for session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def complete_followup(self, session_id: int) -> SessionModel | None:
        """
        Complete followup conversation tracking.

        Sets followup_finish_time to current UTC timestamp and calculates
        followup_duration_seconds as the difference between followup_finish_time
        and followup_start_time.

        Args:
            session_id: ID of the session to update

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if completing followup fails,
            it logs the error and returns None. Followup tracking is analytics only,
            so the user's experience should not be affected.

        Requirements: 6a.2, 6a.3
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for followup completion")
                return None

            finish_time = datetime.now(UTC)
            session.followup_finish_time = finish_time

            # Calculate followup duration in seconds
            if session.followup_start_time is not None:
                duration = finish_time - session.followup_start_time
                session.followup_duration_seconds = int(duration.total_seconds())
            else:
                session.followup_duration_seconds = 0
                logger.warning(
                    f"Session {session_id} has no followup_start_time, "
                    "setting followup_duration to 0"
                )

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.info(
                f"Completed followup for session {session_id} "
                f"(duration: {session.followup_duration_seconds}s)"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to complete followup for session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def add_followup_tokens(
        self,
        session_id: int,
        input_tokens: int,
        output_tokens: int,
    ) -> SessionModel | None:
        """
        Add token counts from an LLM interaction during followup phase.

        Accumulates the provided token counts to the session's followup token
        totals and recalculates the followup total token count.

        Args:
            session_id: ID of the session to update
            input_tokens: Number of input tokens from this followup LLM call
            output_tokens: Number of output tokens from this followup LLM response

        Returns:
            Updated Session instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if token tracking fails,
            it logs the error and returns None. Token counting is analytics only,
            so the user's experience should not be affected.

        Requirements: 6a.4, 6a.5, 6a.6
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for followup token update")
                return None

            # Accumulate followup tokens
            session.followup_input_tokens = (session.followup_input_tokens or 0) + input_tokens
            session.followup_output_tokens = (session.followup_output_tokens or 0) + output_tokens
            session.followup_tokens_total = (
                session.followup_input_tokens + session.followup_output_tokens
            )

            self._db_session.commit()
            self._db_session.refresh(session)
            logger.debug(
                f"Added followup tokens to session {session_id}: "
                f"+{input_tokens} input, +{output_tokens} output "
                f"(followup total: {session.followup_tokens_total})"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to add followup tokens to session {session_id}: {e}")
            self._db_session.rollback()
            return None

    def get_conversation_history(self, session_id: int) -> list[dict]:
        """
        Get all messages for a session in chronological order from JSONB field.

        Returns the complete conversation history stored in the session's
        conversation_history JSONB field. Messages are returned in the order
        they were added, preserving chronological order of user-LLM exchanges.

        Args:
            session_id: ID of the session to get conversation history for

        Returns:
            List of message dictionaries with role, content, and timestamp.
            Returns empty list if session not found or on error (logged).

        Note:
            This method follows graceful degradation - if retrieval fails,
            it logs the error and returns an empty list. Conversation history
            retrieval is analytics only, so the user's experience should not
            be affected.
        """
        try:
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for conversation history retrieval")
                return []

            # Return the conversation history as-is (already a list of dicts)
            # The JSONB field stores messages in chronological order
            history = session.conversation_history or []
            logger.debug(
                f"Retrieved conversation history for session {session_id} ({len(history)} messages)"
            )
            return history
        except Exception as e:
            logger.error(f"Failed to get conversation history for session {session_id}: {e}")
            return []

    def get_session_with_emails(self, session_id: int) -> SessionModel | None:
        """
        Get session with all associated email events loaded.

        Loads the session with its email_events relationship eagerly loaded
        to provide access to all email delivery records for the session.

        Args:
            session_id: ID of the session to retrieve

        Returns:
            Session instance with email_events loaded, or None if not found or on error (logged)

        Note:
            This method follows graceful degradation - if retrieval fails,
            it logs the error and returns None. Session data retrieval is
            analytics only, so the user's experience should not be affected.
        """
        try:
            session = (
                self._db_session.query(SessionModel)
                .options(joinedload(SessionModel.email_events))
                .filter(SessionModel.id == session_id)
                .first()
            )

            if session is None:
                logger.warning(f"Session {session_id} not found for retrieval with emails")
                return None

            logger.debug(
                f"Retrieved session {session_id} with {len(session.email_events)} email events"
            )
            return session
        except Exception as e:
            logger.error(f"Failed to get session {session_id} with emails: {e}")
            return None

    def get_user_current_session(self, user_id: int) -> SessionModel | None:
        """
        Get the current in-progress session for a user, if any.

        Queries for a session with the given user_id and status="in_progress".
        There should be at most one active session per user at any time.

        Args:
            user_id: ID of the user to get current session for

        Returns:
            Session instance with status="in_progress", or None if not found or on error (logged)

        Note:
            This method follows graceful degradation - if retrieval fails,
            it logs the error and returns None. The user can still use the bot
            even if we can't retrieve their current session.
        """
        try:
            session = (
                self._db_session.query(SessionModel)
                .filter(
                    SessionModel.user_id == user_id,
                    SessionModel.status == SessionStatus.IN_PROGRESS.value,
                )
                .first()
            )

            if session is None:
                logger.debug(f"No in-progress session found for user {user_id}")
                return None

            logger.debug(f"Found in-progress session {session.id} for user {user_id}")
            return session
        except Exception as e:
            logger.error(f"Failed to get current session for user {user_id}: {e}")
            return None

    def timeout_stale_sessions(self, timeout_seconds: int) -> int:
        """
        Mark all sessions inactive for longer than timeout as unsuccessful.

        Queries for sessions with status="in_progress" and start_time older
        than the configured timeout, then marks each as "unsuccessful" with
        finish_time set to the current timestamp.

        Processing is done in batches to avoid long transactions, and continues
        on individual failures to ensure maximum sessions are processed.

        Args:
            timeout_seconds: Inactivity threshold in seconds

        Returns:
            Number of sessions successfully timed out

        Note:
            This method follows graceful degradation - if individual session
            timeout fails, it logs the error and continues processing remaining
            sessions. The total count of successfully timed out sessions is returned.
        """
        timed_out_count = 0
        failed_count = 0

        try:
            # Calculate the cutoff time
            cutoff_time = datetime.now(UTC).replace(microsecond=0) - timedelta(
                seconds=timeout_seconds
            )

            # Query all stale sessions
            stale_sessions = (
                self._db_session.query(SessionModel)
                .filter(
                    SessionModel.status == SessionStatus.IN_PROGRESS.value,
                    SessionModel.start_time < cutoff_time,
                )
                .all()
            )

            if not stale_sessions:
                logger.debug(f"No stale sessions found (timeout: {timeout_seconds}s)")
                return 0

            logger.info(
                f"Found {len(stale_sessions)} stale sessions to timeout "
                f"(cutoff: {cutoff_time.isoformat()})"
            )

            # Process each session individually to continue on failures
            for session in stale_sessions:
                try:
                    finish_time = datetime.now(UTC)
                    session.status = SessionStatus.UNSUCCESSFUL.value
                    session.finish_time = finish_time

                    # Calculate duration in seconds
                    if session.start_time is not None:
                        duration = finish_time - session.start_time
                        session.duration_seconds = int(duration.total_seconds())
                    else:
                        session.duration_seconds = 0

                    self._db_session.commit()
                    timed_out_count += 1
                    logger.debug(
                        f"Timed out session {session.id} "
                        f"(started: {session.start_time}, duration: {session.duration_seconds}s)"
                    )
                except Exception as e:
                    logger.error(f"Failed to timeout session {session.id}: {e}")
                    self._db_session.rollback()
                    failed_count += 1

            logger.info(
                f"Session timeout complete: {timed_out_count} timed out, {failed_count} failed"
            )
            return timed_out_count

        except Exception as e:
            logger.error(f"Failed to query stale sessions: {e}")
            return timed_out_count

    def log_email_sent(
        self,
        session_id: int,
        recipient_email: str,
        delivery_status: str,
    ) -> SessionEmailEvent | None:
        """
        Log an email delivery event for the session.

        Creates a SessionEmailEvent record linked to the session to track
        email deliveries of optimized prompts. This method works on any session
        regardless of status (in_progress, successful, or unsuccessful), allowing
        email events to be recorded even after a session is marked as successful.

        Args:
            session_id: ID of the session to link the email event to
            recipient_email: Email address the optimized prompt was sent to
            delivery_status: Delivery status - "sent" or "failed"

        Returns:
            Created SessionEmailEvent instance, or None on error (logged)

        Note:
            This method follows graceful degradation - if email event logging fails,
            it logs the error and returns None. The email was already sent,
            so the user's experience should not be affected by tracking failures.

        Requirements: 7.4 - Email events can be recorded on any session regardless
            of session status (including "successful" sessions).
        """
        try:
            # Verify the session exists
            session = self._db_session.get(SessionModel, session_id)
            if session is None:
                logger.warning(f"Session {session_id} not found for email event logging")
                return None

            # Create the email event record
            email_event = SessionEmailEvent(
                session_id=session_id,
                recipient_email=recipient_email,
                delivery_status=delivery_status,
            )
            self._db_session.add(email_event)
            self._db_session.commit()
            self._db_session.refresh(email_event)

            logger.info(
                f"Logged email event for session {session_id}: "
                f"status={delivery_status}, recipient={recipient_email[:3]}***"
            )
            return email_event
        except Exception as e:
            logger.error(f"Failed to log email event for session {session_id}: {e}")
            self._db_session.rollback()
            return None


# Global session service instance
_session_service: SessionService | None = None


def init_session_service(db_session: DBSession) -> SessionService:
    """
    Initialize global session service.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        SessionService instance
    """
    global _session_service
    _session_service = SessionService(db_session)
    logger.info("Session service initialized")
    return _session_service


def get_session_service() -> SessionService:
    """
    Get the global session service instance.

    Returns:
        SessionService instance

    Raises:
        RuntimeError: If session service is not initialized
    """
    if _session_service is None:
        error_msg = "Session service not initialized. Call init_session_service() first."
        raise RuntimeError(error_msg)
    return _session_service
