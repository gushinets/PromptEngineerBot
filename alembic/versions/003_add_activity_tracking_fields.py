"""Add activity tracking fields

Revision ID: 003
Revises: 002
Create Date: 2025-01-10 12:00:00.000000

This migration adds user activity tracking fields and modifies the email column
to allow null values for unauthenticated users.

Changes:
- Add first_interaction_at column (timestamp of first bot interaction)
- Add last_interaction_at column (timestamp of most recent bot interaction)
- Backfill existing records with created_at value
- Create indexes for activity tracking columns
- Modify email column to allow null values
- Handle unique constraint on email for null values
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add activity tracking fields and modify email column."""
    # Add activity tracking columns (nullable initially for existing data)
    op.add_column(
        "users",
        sa.Column("first_interaction_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("last_interaction_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Backfill existing records with created_at value
    # This ensures existing users have valid activity timestamps
    op.execute(
        "UPDATE users SET first_interaction_at = created_at WHERE first_interaction_at IS NULL"
    )
    op.execute(
        "UPDATE users SET last_interaction_at = created_at WHERE last_interaction_at IS NULL"
    )

    # Create indexes for activity tracking columns
    op.create_index(
        "ix_users_first_interaction_at", "users", ["first_interaction_at"], unique=False
    )
    op.create_index("ix_users_last_interaction_at", "users", ["last_interaction_at"], unique=False)

    # Modify email column to allow null values
    # This is needed for unauthenticated users who haven't verified their email yet
    #
    # Using batch_alter_table for cross-database compatibility
    # SQLite requires table recreation for ALTER COLUMN operations
    # batch_alter_table handles this automatically
    #
    # Note: In SQL standard, NULL values are not considered equal in unique constraints,
    # so multiple NULL values are allowed. Both SQLite and PostgreSQL follow this behavior.
    with op.batch_alter_table("users", recreate="always") as batch_op:
        # Alter email column to be nullable while preserving the unique constraint
        batch_op.alter_column(
            "email",
            existing_type=sa.Text(),
            nullable=True,
            existing_nullable=False,
        )


def downgrade() -> None:
    """Remove activity tracking fields and restore email column constraints."""
    # Drop indexes first
    op.drop_index("ix_users_last_interaction_at", table_name="users")
    op.drop_index("ix_users_first_interaction_at", table_name="users")

    # Drop activity tracking columns
    op.drop_column("users", "last_interaction_at")
    op.drop_column("users", "first_interaction_at")

    # Restore email column to non-nullable
    # Note: This will fail if there are any NULL email values in the database
    # In production, you would need to handle this case (e.g., delete or update those records)
    with op.batch_alter_table("users", recreate="always") as batch_op:
        # Alter email column to be non-nullable
        # This requires all existing records to have non-null email values
        batch_op.alter_column(
            "email",
            existing_type=sa.Text(),
            nullable=False,
            existing_nullable=True,
        )
