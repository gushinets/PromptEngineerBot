"""Add session tracking tables

Revision ID: 004
Revises: 003
Create Date: 2025-12-16 10:00:00.000000

This migration adds session tracking tables for prompt optimization workflows.

Changes:
- Create sessions table with all fields including JSONB conversation_history
- Create session_email_events table for email delivery tracking
- Create indexes for efficient queries on user_id, status, start_time
- Create composite index for current session lookup (user_id + status)
- Create index on session_email_events.session_id

Requirements: 9.4 - Migration rollback removes session tables and indexes
"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sessions and session_email_events tables with indexes."""
    # Create sessions table
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        # Timing fields
        sa.Column(
            "start_time",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finish_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        # Status field
        sa.Column("status", sa.Text(), server_default="in_progress", nullable=False),
        # Optimization method and model
        sa.Column("optimization_method", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("used_followup", sa.Boolean(), server_default="false", nullable=False),
        # Token metrics (cumulative)
        sa.Column("input_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("output_tokens", sa.Integer(), server_default="0", nullable=False),
        sa.Column("tokens_total", sa.Integer(), server_default="0", nullable=False),
        # Conversation history as JSONB (PostgreSQL) or JSON (SQLite fallback)
        sa.Column("conversation_history", JSONB(), server_default="[]", nullable=False),
    )

    # Create session_email_events table
    op.create_table(
        "session_email_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("recipient_email", sa.Text(), nullable=False),
        sa.Column("delivery_status", sa.Text(), nullable=False),
    )

    # Create indexes for sessions table (Requirements 9.1, 9.2, 9.3)
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index("ix_sessions_status", "sessions", ["status"], unique=False)
    op.create_index("ix_sessions_start_time", "sessions", ["start_time"], unique=False)
    op.create_index("ix_sessions_user_status", "sessions", ["user_id", "status"], unique=False)

    # Create index for session_email_events table
    op.create_index(
        "ix_session_email_events_session_id",
        "session_email_events",
        ["session_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove session tables and their indexes (Requirement 9.4)."""
    # Drop indexes first
    op.drop_index("ix_session_email_events_session_id", table_name="session_email_events")
    op.drop_index("ix_sessions_user_status", table_name="sessions")
    op.drop_index("ix_sessions_start_time", table_name="sessions")
    op.drop_index("ix_sessions_status", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")

    # Drop tables (child table first due to foreign key constraint)
    op.drop_table("session_email_events")
    op.drop_table("sessions")
