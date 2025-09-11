"""Add user profile fields

Revision ID: 002
Revises: 001
Create Date: 2025-01-09 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add user profile fields to users table."""
    # Add new profile columns to users table
    op.add_column("users", sa.Column("first_name", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.Text(), nullable=True))
    op.add_column(
        "users", sa.Column("is_bot", sa.Boolean(), nullable=True, default=False)
    )
    # For SQLite compatibility, add is_premium as nullable first, then update with default
    op.add_column("users", sa.Column("is_premium", sa.Boolean(), nullable=True))
    op.add_column("users", sa.Column("language_code", sa.Text(), nullable=True))

    # Update existing rows to set default values for new columns
    op.execute("UPDATE users SET is_premium = FALSE WHERE is_premium IS NULL")
    op.execute("UPDATE users SET is_bot = FALSE WHERE is_bot IS NULL")

    # Create indexes for performance
    op.create_index("ix_users_language_code", "users", ["language_code"], unique=False)
    op.create_index("ix_users_is_premium", "users", ["is_premium"], unique=False)
    op.create_index(
        "ix_users_bot_premium", "users", ["is_bot", "is_premium"], unique=False
    )


def downgrade() -> None:
    """Remove user profile fields from users table."""
    # Drop indexes first
    op.drop_index("ix_users_bot_premium", table_name="users")
    op.drop_index("ix_users_is_premium", table_name="users")
    op.drop_index("ix_users_language_code", table_name="users")

    # Drop columns
    op.drop_column("users", "language_code")
    op.drop_column("users", "is_premium")
    op.drop_column("users", "is_bot")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")
