"""
Report data models for marketing reports.

This module defines the data structures used for generating marketing reports,
including user summaries, daily metrics, session exports, and timing information.
"""

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class UserSummaryRow:
    """
    Single row in user summary report.

    Contains per-user metrics including session counts, method usage,
    token statistics, and success rates.

    Attributes:
        user_id: Unique identifier for the user
        email: User's email address (may be None)
        total_sessions: Count of all sessions for this user
        total_prompts: Count of prompts (equal to total_sessions)
        craft_count: Count of sessions using CRAFT optimization method
        lyra_count: Count of sessions using LYRA optimization method
        ggl_count: Count of sessions using GGL optimization method
        avg_tokens: Average tokens_total across all user sessions
        success_rate: Percentage of successful sessions (0-100)
        last_activity: User's last_interaction_at timestamp
        avg_duration: Average duration_seconds across all user sessions
    """

    user_id: int
    email: str | None
    total_sessions: int
    total_prompts: int
    craft_count: int
    lyra_count: int
    ggl_count: int
    avg_tokens: float
    success_rate: float
    last_activity: datetime
    avg_duration: float


@dataclass
class DailyMetricsRow:
    """
    Daily platform metrics.

    Contains aggregate metrics for a specific date including user counts,
    prompt statistics, and method usage.

    Attributes:
        date: The report date
        all_users: Total count of users in the database
        active_users: Count of users with at least one session on the report date
        new_users: Count of users with first_interaction_at on the report date
        total_prompts: Count of successful sessions on the report date
        craft_used: Count of successful sessions with CRAFT method on the report date
        lyra_used: Count of successful sessions with LYRA method on the report date
        ggl_used: Count of successful sessions with GGL method on the report date
        avg_tokens: Average tokens_total of successful sessions on the report date
        total_emails: Count of sent emails on the report date
    """

    date: date
    all_users: int
    active_users: int
    new_users: int
    total_prompts: int
    craft_used: int
    lyra_used: int
    ggl_used: int
    avg_tokens: float
    total_emails: int


@dataclass
class SessionExportRow:
    """
    Single row in sessions export.

    Contains all session data including conversation history for successful sessions.

    Attributes:
        id: Session unique identifier
        user_id: User who owns this session
        start_time: When the session started
        finish_time: When the session finished (may be None)
        duration_seconds: Session duration in seconds (may be None)
        status: Session status (e.g., "successful")
        optimization_method: Method used (CRAFT, LYRA, GGL, or None)
        model_name: Name of the LLM model used
        used_followup: Whether follow-up was used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        tokens_total: Total tokens (input + output)
        followup_start_time: When follow-up started (may be None)
        followup_finish_time: When follow-up finished (may be None)
        followup_duration_seconds: Follow-up duration in seconds (may be None)
        followup_input_tokens: Follow-up input tokens
        followup_output_tokens: Follow-up output tokens
        followup_tokens_total: Follow-up total tokens
        conversation_history: JSON string of conversation history
    """

    id: int
    user_id: int
    start_time: datetime
    finish_time: datetime | None
    duration_seconds: int | None
    status: str
    optimization_method: str | None
    model_name: str
    used_followup: bool
    input_tokens: int
    output_tokens: int
    tokens_total: int
    followup_start_time: datetime | None
    followup_finish_time: datetime | None
    followup_duration_seconds: int | None
    followup_input_tokens: int
    followup_output_tokens: int
    followup_tokens_total: int
    conversation_history: str


@dataclass
class QueryTiming:
    """
    Timing information for a database query.

    Used to track and log query performance metrics.

    Attributes:
        query_name: Name/identifier of the query
        duration_ms: Query execution time in milliseconds
        row_count: Number of rows returned by the query
    """

    query_name: str
    duration_ms: float
    row_count: int


@dataclass
class ReportResult:
    """
    Result of report generation including timing metrics.

    Contains success status, row counts for each report type,
    and detailed timing information.

    Attributes:
        success: Whether report generation completed successfully
        user_summary_rows: Number of rows in user summary report
        daily_metrics_generated: Whether daily metrics were generated
        sessions_exported: Number of sessions exported
        query_timings: List of timing information for each query
        total_query_time_ms: Sum of all query execution times
        total_execution_time_ms: Total time for complete report generation
        error: Error message if generation failed (None on success)
    """

    success: bool
    user_summary_rows: int
    daily_metrics_generated: bool
    sessions_exported: int
    query_timings: list[QueryTiming] = field(default_factory=list)
    total_query_time_ms: float = 0.0
    total_execution_time_ms: float = 0.0
    error: str | None = None
