"""Add followup tracking fields to sessions table

Revision ID: 005
Revises: 004
Create Date: 2025-12-18 10:00:00.000000

This migration adds followup conversation tracking fields to the sessions table.

Changes:
- Add followup_start_time: Timestamp when followup conversation starts
- Add followup_finish_time: Timestamp when followup conversation ends
- Add followup_duration_seconds: Calculated duration of followup conversation
- Add followup_input_tokens: Cumulative input tokens during followup phase
- Add followup_output_tokens: Cumulative output tokens during followup phase
- Add followup_tokens_total: Sum of followup input and output tokens
- Make optimization_method nullable (session created before method selection)

Requirements: 6a.1, 6a.2, 6a.3, 6a.4, 6a.5, 6a.6, 1.5
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add followup tracking fields and make optimization_method nullable."""
    # Add followup timing fields (Requirements 6a.1, 6a.2, 6a.3)
    op.add_column(
        "sessions",
        sa.Column("followup_start_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("followup_finish_time", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "sessions",
        sa.Column("followup_duration_seconds", sa.Integer(), nullable=True),
    )

    # Add followup token metrics (Requirements 6a.4, 6a.5, 6a.6)
    op.add_column(
        "sessions",
        sa.Column("followup_input_tokens", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "sessions",
        sa.Column("followup_output_tokens", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "sessions",
        sa.Column("followup_tokens_total", sa.Integer(), server_default="0", nullable=False),
    )

    # Make optimization_method nullable (Requirement 1.5)
    # Session is created before method selection, so method can be NULL initially
    op.alter_column(
        "sessions",
        "optimization_method",
        existing_type=sa.Text(),
        nullable=True,
    )


def downgrade() -> None:
    """Remove followup tracking fields and restore optimization_method as non-nullable."""
    # Restore optimization_method as non-nullable
    # First, update any NULL values to a default (required before making non-nullable)
    op.execute(
        "UPDATE sessions SET optimization_method = 'UNKNOWN' WHERE optimization_method IS NULL"
    )
    op.alter_column(
        "sessions",
        "optimization_method",
        existing_type=sa.Text(),
        nullable=False,
    )

    # Remove followup token metrics
    op.drop_column("sessions", "followup_tokens_total")
    op.drop_column("sessions", "followup_output_tokens")
    op.drop_column("sessions", "followup_input_tokens")

    # Remove followup timing fields
    op.drop_column("sessions", "followup_duration_seconds")
    op.drop_column("sessions", "followup_finish_time")
    op.drop_column("sessions", "followup_start_time")
