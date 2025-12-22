"""
Database models and connection management for email authentication and user profiling.

This module provides SQLAlchemy models for User and AuthEvent tables,
database connection factory, and session management.

User Profile Fields:
The User model includes Telegram profile fields that are automatically extracted
from update.effective_user during user interactions:

- first_name: User's first name from Telegram profile
- last_name: User's last name from Telegram profile
- is_bot: Boolean indicating if user is a bot account
- is_premium: Boolean indicating Telegram Premium subscription status
- language_code: User's language preference (ISO 639-1 code)

Profile Update Strategy:
- New users: All available profile data captured during registration
- Existing users: Selective updates only when meaningful changes detected
- Profile updates trigger updated_at timestamp for change tracking
- Graceful handling of missing or null profile data from Telegram API

Database Indexes:
Performance-optimized indexes are created for profile fields:
- ix_users_language_code: For language-based user queries
- ix_users_is_premium: For premium user filtering
- ix_users_bot_premium: Composite index for user type analytics
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    create_engine,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
    sessionmaker,
)
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import JSON, TypeDecorator


class JSONBCompatible(TypeDecorator):
    """
    A type that uses JSONB on PostgreSQL and JSON on other databases (like SQLite).

    This allows the Session model to work with both PostgreSQL (production) and
    SQLite (testing) without requiring separate model definitions.
    """

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""


class User(Base):
    """
    User model for storing authentication, email, and Telegram profile information.

    This model stores both authentication data (email, verification status) and
    Telegram profile information extracted from update.effective_user during user
    interactions. Profile data is captured automatically during user registration
    and updated selectively when meaningful changes are detected.

    Profile Update Strategy:
    - New users: All available profile data is captured during first interaction
    - Existing users: Profile data is updated only when meaningful changes are detected
      (name changes, premium status changes, language changes) to optimize performance
    - Updates trigger the updated_at timestamp to track when profile changes occurred
    """

    __tablename__ = "users"

    # Core identification and authentication fields
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    email: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    email_original: Mapped[str | None] = mapped_column(Text)
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_authenticated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Activity tracking fields
    first_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    """Timestamp of user's first interaction with the bot. Set once on user creation."""

    last_interaction_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    """Timestamp of user's most recent interaction with the bot. Updated on every interaction."""

    # Telegram profile fields extracted from update.effective_user
    # These fields are automatically populated during user interactions

    first_name: Mapped[str | None] = mapped_column(Text)
    """User's first name from Telegram (update.effective_user.first_name).
    Nullable as some users may not have a first name set in their Telegram profile."""

    last_name: Mapped[str | None] = mapped_column(Text)
    """User's last name from Telegram (update.effective_user.last_name).
    Nullable as most users don't set a last name in their Telegram profile."""

    is_bot: Mapped[bool] = mapped_column(Boolean, default=False)
    """Indicates if this user is a Telegram bot account (update.effective_user.is_bot).
    Defaults to False for regular user accounts. Used for analytics and bot detection."""

    is_premium: Mapped[bool | None] = mapped_column(Boolean)
    """Indicates if user has Telegram Premium subscription (update.effective_user.is_premium).
    Nullable as this field may not be available for all users or in all Telegram versions.
    Used for feature differentiation and user analytics."""

    language_code: Mapped[str | None] = mapped_column(Text)
    """User's language preference as ISO 639-1 code (update.effective_user.language_code).
    Examples: 'en', 'es', 'fr', 'de'. Nullable as not all users have language set.
    Used for localization and language-specific features."""

    # Relationship to sessions
    sessions: Mapped[list["Session"]] = relationship("Session", back_populates="user")

    def __repr__(self) -> str:
        name_part = f", name='{self.first_name}'" if self.first_name else ""
        email_part = f", email='{self.email[:3]}***'" if self.email else ""
        return f"<User(id={self.id}, telegram_id={self.telegram_id}{email_part}{name_part})>"


class Session(Base):
    """
    Session model for tracking prompt optimization workflows.

    A session represents a complete prompt optimization workflow from initial
    prompt submission to final delivery or termination. Sessions capture:
    - Timing: start_time, finish_time, duration_seconds
    - Status: in_progress, successful, unsuccessful
    - Optimization method: LYRA, CRAFT, or GGL
    - Token metrics: cumulative input/output token counts
    - Conversation history: complete record of user-LLM exchanges (JSONB)
    - Email events: linked records of emails sent during the session
    """

    __tablename__ = "sessions"

    # Primary key
    id: Mapped[int] = mapped_column(primary_key=True)

    # Foreign key to users table
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)

    # Timing fields
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    """Session start timestamp. Set when session is created."""

    finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Session end timestamp. Set when session completes or is terminated."""

    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    """Calculated duration in seconds between start_time and finish_time."""

    # Status field
    status: Mapped[str] = mapped_column(Text, default="in_progress")
    """Session status: 'in_progress', 'successful', or 'unsuccessful'."""

    # Optimization method and model
    optimization_method: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Selected optimization method: LYRA, CRAFT, or GGL. Nullable until user selects method."""

    model_name: Mapped[str] = mapped_column(Text, nullable=False)
    """LLM model identifier used for optimization (e.g., 'openai/gpt-4', 'gpt-4o')."""

    used_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    """Whether FOLLOWUP optimization was used in this session."""

    # Token metrics (cumulative for initial optimization phase)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    """Cumulative count of all tokens sent to the LLM during initial optimization phase."""

    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    """Cumulative count of all tokens received from the LLM during initial optimization phase."""

    tokens_total: Mapped[int] = mapped_column(Integer, default=0)
    """Sum of input_tokens and output_tokens for initial optimization phase."""

    # Followup timing fields (Requirements 6a.1, 6a.2, 6a.3)
    followup_start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Timestamp when followup conversation starts. Set when user opts for followup."""

    followup_finish_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    """Timestamp when followup conversation ends."""

    followup_duration_seconds: Mapped[int | None] = mapped_column(Integer)
    """Calculated duration of followup conversation in seconds."""

    # Followup token metrics (Requirements 6a.4, 6a.5, 6a.6)
    followup_input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    """Cumulative count of all tokens sent to the LLM during followup phase."""

    followup_output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    """Cumulative count of all tokens received from the LLM during followup phase."""

    followup_tokens_total: Mapped[int] = mapped_column(Integer, default=0)
    """Sum of followup_input_tokens and followup_output_tokens."""

    # Conversation history as JSONB (PostgreSQL) or JSON (SQLite)
    # Format: [{"role": "user"|"assistant", "content": "...", "timestamp": "ISO8601"}, ...]
    conversation_history: Mapped[list] = mapped_column(JSONBCompatible, default=list)
    """Complete record of all messages exchanged between user and LLM during the session."""

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="sessions")
    email_events: Mapped[list["SessionEmailEvent"]] = relationship(
        "SessionEmailEvent", back_populates="session", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return (
            f"<Session(id={self.id}, user_id={self.user_id}, "
            f"status='{self.status}', method='{self.optimization_method}')>"
        )

    def to_dict(self) -> dict:
        """
        Serialize session to a dictionary for JSON output.

        Serializes all session fields including conversation_history and followup fields.
        Uses ISO 8601 format with timezone information for datetime fields.

        Returns:
            Dictionary containing all session fields suitable for JSON serialization.

        Requirements: 11.1, 11.3
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "finish_time": self.finish_time.isoformat() if self.finish_time else None,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "optimization_method": self.optimization_method,
            "model_name": self.model_name,
            "used_followup": self.used_followup,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "tokens_total": self.tokens_total,
            # Followup timing fields
            "followup_start_time": (
                self.followup_start_time.isoformat() if self.followup_start_time else None
            ),
            "followup_finish_time": (
                self.followup_finish_time.isoformat() if self.followup_finish_time else None
            ),
            "followup_duration_seconds": self.followup_duration_seconds,
            # Followup token metrics
            "followup_input_tokens": self.followup_input_tokens,
            "followup_output_tokens": self.followup_output_tokens,
            "followup_tokens_total": self.followup_tokens_total,
            "conversation_history": self.conversation_history or [],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """
        Deserialize a dictionary to a Session object.

        Parses ISO 8601 datetime strings back to datetime objects.
        Handles both main session fields and followup tracking fields.

        Args:
            data: Dictionary containing session fields (typically from JSON).

        Returns:
            Session object with all fields populated from the dictionary.

        Requirements: 11.2
        """

        def parse_datetime(value: str | None) -> datetime | None:
            """Parse ISO 8601 datetime string to datetime object."""
            if value is None:
                return None
            # Handle ISO 8601 format with timezone
            # Python's fromisoformat handles most ISO 8601 formats
            dt = datetime.fromisoformat(value)
            # Ensure timezone-aware (default to UTC if naive)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt

        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            start_time=parse_datetime(data.get("start_time")),
            finish_time=parse_datetime(data.get("finish_time")),
            duration_seconds=data.get("duration_seconds"),
            status=data.get("status", "in_progress"),
            optimization_method=data.get("optimization_method"),  # Now nullable
            model_name=data["model_name"],
            used_followup=data.get("used_followup", False),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            tokens_total=data.get("tokens_total", 0),
            # Followup timing fields
            followup_start_time=parse_datetime(data.get("followup_start_time")),
            followup_finish_time=parse_datetime(data.get("followup_finish_time")),
            followup_duration_seconds=data.get("followup_duration_seconds"),
            # Followup token metrics
            followup_input_tokens=data.get("followup_input_tokens", 0),
            followup_output_tokens=data.get("followup_output_tokens", 0),
            followup_tokens_total=data.get("followup_tokens_total", 0),
            conversation_history=data.get("conversation_history", []),
        )


class SessionEmailEvent(Base):
    """
    SessionEmailEvent model for tracking email deliveries per session.

    Records each email sent containing an optimized prompt, linked to the
    session that generated it.
    """

    __tablename__ = "session_email_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), nullable=False)

    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    """Timestamp when the email was sent."""

    recipient_email: Mapped[str] = mapped_column(Text, nullable=False)
    """Email address the optimized prompt was sent to."""

    delivery_status: Mapped[str] = mapped_column(Text, nullable=False)
    """Delivery status: 'sent' or 'failed'."""

    # Relationship
    session: Mapped["Session"] = relationship("Session", back_populates="email_events")

    def __repr__(self) -> str:
        return (
            f"<SessionEmailEvent(id={self.id}, session_id={self.session_id}, "
            f"status='{self.delivery_status}')>"
        )


class AuthEvent(Base):
    """AuthEvent model for audit logging of authentication events."""

    __tablename__ = "auth_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    email: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())

    def __repr__(self) -> str:
        return f"<AuthEvent(id={self.id}, event_type='{self.event_type}', success={self.success})>"


# Essential Indexes for User Model
Index("ix_users_telegram_id", User.telegram_id)
Index("ix_users_email", User.email)
Index("ix_users_authenticated", User.is_authenticated, User.last_authenticated_at.desc())

# Profile field indexes for efficient queries on Telegram user data
Index("ix_users_language_code", User.language_code)  # Language-based user segmentation
Index("ix_users_is_premium", User.is_premium)  # Premium user filtering and analytics
Index("ix_users_bot_premium", User.is_bot, User.is_premium)  # Composite index for user type queries

# Activity tracking indexes for efficient queries on user interaction timestamps
Index("ix_users_first_interaction_at", User.first_interaction_at)  # First interaction queries
Index("ix_users_last_interaction_at", User.last_interaction_at)  # Last interaction queries

# Essential Indexes for AuthEvents Model
Index("ix_auth_events_telegram_time", AuthEvent.telegram_id, AuthEvent.created_at.desc())
Index("ix_auth_events_email_time", AuthEvent.email, AuthEvent.created_at.desc())
Index("ix_auth_events_type_time", AuthEvent.event_type, AuthEvent.created_at.desc())

# Session indexes for efficient queries (Requirements 9.1, 9.2, 9.3)
Index("ix_sessions_user_id", Session.user_id)  # User-based session queries
Index("ix_sessions_status", Session.status)  # Status-based filtering
Index("ix_sessions_start_time", Session.start_time)  # Time-range queries
Index(
    "ix_sessions_user_status", Session.user_id, Session.status
)  # Composite for current session lookup

# SessionEmailEvent indexes
Index(
    "ix_session_email_events_session_id", SessionEmailEvent.session_id
)  # Session-based email queries


class DatabaseManager:
    """Database connection and session management."""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_pre_ping: bool = True,
    ):
        """Initialize database manager with connection URL and pool settings."""
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.pool_pre_ping = pool_pre_ping
        self._engine = None
        self._session_factory = None

    def get_engine(self):
        """Get or create database engine."""
        if self._engine is None:
            if self.database_url.startswith("sqlite"):
                # SQLite configuration for development
                self._engine = create_engine(
                    self.database_url,
                    poolclass=StaticPool,
                    connect_args={"check_same_thread": False},
                    echo=False,
                )
            else:
                # PostgreSQL configuration for production
                self._engine = create_engine(
                    self.database_url,
                    pool_size=self.pool_size,
                    max_overflow=self.max_overflow,
                    pool_pre_ping=self.pool_pre_ping,
                    echo=False,
                )
        return self._engine

    def get_session_factory(self):
        """Get or create session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(bind=self.get_engine(), expire_on_commit=False)
        return self._session_factory

    def create_tables(self):
        """Create all database tables."""
        try:
            Base.metadata.create_all(self.get_engine())
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create database tables: {e}")
            raise

    def get_session(self) -> DBSession:
        """Get a new database session."""
        session_factory = self.get_session_factory()
        return session_factory()

    def health_check(self) -> bool:
        """Check database connectivity."""
        try:
            with self.get_session() as session:
                session.execute(func.now())
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


def normalize_email(email: str) -> str:
    """
    Normalize email address for storage and uniqueness checks.

    Args:
        email: Raw email address from user input

    Returns:
        Normalized email address (lowercase, plus-tag removed)
    """
    if not email or "@" not in email:
        return email.lower() if email else ""

    local, domain = email.split("@", 1)

    # Remove plus-tags from local part
    if "+" in local:
        local = local.split("+")[0]

    # Convert to lowercase
    normalized = f"{local}@{domain}".lower()

    return normalized


def mask_email(email: str) -> str:
    """
    Mask email for logging purposes.

    Args:
        email: Email address to mask

    Returns:
        Masked email (e.g., u***@e***.com)
    """
    if not email or "@" not in email:
        return email[:1] + "***" if email else "***"

    local, domain = email.split("@", 1)
    # For single character local parts, mask completely for security
    if len(local) == 1:
        masked_local = "***"
    else:
        masked_local = local[:1] + "***" if len(local) >= 1 else "***"

    if "." in domain:
        domain_parts = domain.split(".")
        # Handle international domains and IDN domains
        first_part = domain_parts[0]
        if len(first_part) > 0:
            masked_first = first_part[:1] + "***"
        else:
            masked_first = "***"
        masked_domain = masked_first + "." + domain_parts[-1]
    else:
        masked_domain = "***"

    return f"{masked_local}@{masked_domain}"


def mask_telegram_id(tg_id: int) -> str:
    """
    Mask telegram ID for logging purposes.

    Args:
        tg_id: Telegram ID to mask

    Returns:
        Masked telegram ID (e.g., 123***789)
    """
    tg_str = str(tg_id)
    if len(tg_str) <= 6:
        return tg_str[:2] + "***"
    return tg_str[:3] + "***" + tg_str[-3:]


# Global database manager instance
db_manager: DatabaseManager | None = None


def init_database(
    database_url: str,
    pool_size: int = 10,
    max_overflow: int = 20,
    pool_pre_ping: bool = True,
) -> DatabaseManager:
    """
    Initialize global database manager.

    Args:
        database_url: Database connection URL
        pool_size: Connection pool size
        max_overflow: Maximum overflow connections
        pool_pre_ping: Enable connection pre-ping

    Returns:
        DatabaseManager instance
    """
    global db_manager
    db_manager = DatabaseManager(database_url, pool_size, max_overflow, pool_pre_ping)
    return db_manager


def init_database_from_config(config) -> DatabaseManager:
    """
    Initialize global database manager from BotConfig.

    Args:
        config: BotConfig instance with database settings

    Returns:
        DatabaseManager instance
    """
    return init_database(
        database_url=config.database_url,
        pool_size=config.database_pool_size,
        max_overflow=config.database_max_overflow,
        pool_pre_ping=config.database_pool_pre_ping,
    )


def get_db_manager() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager instance

    Raises:
        RuntimeError: If database manager is not initialized
    """
    if db_manager is None:
        raise RuntimeError("Database manager not initialized. Call init_database() first.")
    return db_manager


def get_db_session() -> DBSession:
    """
    Get a new database session from the global database manager.

    Returns:
        Database session

    Raises:
        RuntimeError: If database manager is not initialized
    """
    return get_db_manager().get_session()
