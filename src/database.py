"""
Database models and connection management for email authentication feature.

This module provides SQLAlchemy models for User and AuthEvent tables,
database connection factory, and session management.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Text, create_engine, func
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class User(Base):
    """User model for storing authentication and email information."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    email_original: Mapped[Optional[str]] = mapped_column(Text)
    is_authenticated: Mapped[bool] = mapped_column(Boolean, default=False)
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    last_authenticated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, email='{self.email[:3]}***')>"


class AuthEvent(Base):
    """AuthEvent model for audit logging of authentication events."""

    __tablename__ = "auth_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    def __repr__(self) -> str:
        return f"<AuthEvent(id={self.id}, event_type='{self.event_type}', success={self.success})>"


# Essential Indexes for User Model
Index("ix_users_telegram_id", User.telegram_id)
Index("ix_users_email", User.email)
Index(
    "ix_users_authenticated", User.is_authenticated, User.last_authenticated_at.desc()
)

# Essential Indexes for AuthEvents Model
Index(
    "ix_auth_events_telegram_time", AuthEvent.telegram_id, AuthEvent.created_at.desc()
)
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
            self._session_factory = sessionmaker(
                bind=self.get_engine(), expire_on_commit=False
            )
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
    masked_local = local[:1] + "***" if len(local) > 1 else "***"

    if "." in domain:
        domain_parts = domain.split(".")
        masked_domain = domain_parts[0][:1] + "***." + domain_parts[-1]
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
db_manager: Optional[DatabaseManager] = None


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
        raise RuntimeError(
            "Database manager not initialized. Call init_database() first."
        )
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
