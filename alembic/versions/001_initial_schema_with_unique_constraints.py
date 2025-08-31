"""Initial schema with unique constraints

Revision ID: 001
Revises:
Create Date: 2025-08-31 13:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema with unique constraints."""
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("email_original", sa.Text(), nullable=True),
        sa.Column("is_authenticated", sa.Boolean(), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_authenticated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create unique constraints
    op.create_unique_constraint("uq_users_telegram_id", "users", ["telegram_id"])
    op.create_unique_constraint("uq_users_email", "users", ["email"])

    # Create indexes for performance
    op.create_index("ix_users_telegram_id", "users", ["telegram_id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index(
        "ix_users_authenticated",
        "users",
        ["is_authenticated", "last_authenticated_at"],
        unique=False,
    )

    # Create auth_events table
    op.create_table(
        "auth_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for auth_events
    op.create_index(
        "ix_auth_events_telegram_time",
        "auth_events",
        ["telegram_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_auth_events_email_time",
        "auth_events",
        ["email", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_auth_events_type_time",
        "auth_events",
        ["event_type", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop all tables and constraints."""
    # Drop indexes first
    op.drop_index("ix_auth_events_type_time", table_name="auth_events")
    op.drop_index("ix_auth_events_email_time", table_name="auth_events")
    op.drop_index("ix_auth_events_telegram_time", table_name="auth_events")

    # Drop auth_events table
    op.drop_table("auth_events")

    # Drop indexes for users table
    op.drop_index("ix_users_authenticated", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_telegram_id", table_name="users")

    # Drop unique constraints
    op.drop_constraint("uq_users_email", "users", type_="unique")
    op.drop_constraint("uq_users_telegram_id", "users", type_="unique")

    # Drop users table
    op.drop_table("users")
