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
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool


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

    def __repr__(self) -> str:
        name_part = f", name='{self.first_name}'" if self.first_name else ""
        email_part = f", email='{self.email[:3]}***'" if self.email else ""
        return f"<User(id={self.id}, telegram_id={self.telegram_id}{email_part}{name_part})>"


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

    def get_session(self) -> Session:
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


def get_db_session() -> Session:
    """
    Get a new database session from the global database manager.

    Returns:
        Database session

    Raises:
        RuntimeError: If database manager is not initialized
    """
    return get_db_manager().get_session()
