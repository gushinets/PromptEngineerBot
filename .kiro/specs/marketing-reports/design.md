# Design Document: Marketing Reports

## Overview

This design describes the implementation of a daily marketing reports feature that generates and emails CSV reports containing user activity summaries, daily platform metrics, and session exports. The system leverages existing infrastructure (BackgroundTaskScheduler, EmailService, database models) to deliver reports at a configurable time each day, with support for historical report generation via CLI.

The implementation follows the Hybrid Approach (Approach 3) - using real-time queries with optimized SQL and proper indexing, without requiring new database tables or migrations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Marketing Reports System                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────┐         ┌─────────────────────────────────────┐ │
│  │  BackgroundTask    │         │          ReportService              │ │
│  │  Scheduler         │────────▶│                                     │ │
│  │  (daily_reports)   │         │  ┌─────────────────────────────┐   │ │
│  └────────────────────┘         │  │  ReportConfig               │   │ │
│                                 │  │  - generation_time          │   │ │
│  ┌────────────────────┐         │  │  - user_activity_days       │   │ │
│  │  CLI Module        │────────▶│  │  - recipient_emails         │   │ │
│  │  (reports.py)      │         │  └─────────────────────────────┘   │ │
│  └────────────────────┘         │                                     │ │
│                                 │  ┌─────────────────────────────┐   │ │
│                                 │  │  UserSummaryGenerator       │   │ │
│                                 │  └─────────────────────────────┘   │ │
│                                 │                                     │ │
│                                 │  ┌─────────────────────────────┐   │ │
│                                 │  │  DailyMetricsGenerator      │   │ │
│                                 │  └─────────────────────────────┘   │ │
│                                 │                                     │ │
│                                 │  ┌─────────────────────────────┐   │ │
│                                 │  │  SessionsExporter           │   │ │
│                                 │  └─────────────────────────────┘   │ │
│                                 │                                     │ │
│                                 │  ┌─────────────────────────────┐   │ │
│                                 │  │  CSVGenerator               │   │ │
│                                 │  └─────────────────────────────┘   │ │
│                                 └──────────────┬──────────────────────┘ │
│                                                │                        │
│                                                ▼                        │
│                                 ┌─────────────────────────────────────┐ │
│                                 │         EmailService               │ │
│                                 │  (existing, with retry logic)      │ │
│                                 └─────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### ReportConfig

Configuration dataclass for report generation settings.

```python
@dataclass
class ReportConfig:
    """Configuration for marketing report generation."""
    
    generation_time: str  # HH:MM format, default "01:00"
    user_activity_days: int  # 0 = all users, >0 = filter by days
    recipient_emails: list[str]  # List of email addresses
    
    @classmethod
    def from_env(cls) -> "ReportConfig":
        """Load configuration from environment variables."""
        pass
```

### ReportService

Main service orchestrating report generation and delivery.

```python
@dataclass
class QueryTiming:
    """Timing information for a database query."""
    
    query_name: str
    duration_ms: float
    row_count: int


@dataclass
class ReportResult:
    """Result of report generation including timing metrics."""
    
    success: bool
    user_summary_rows: int
    daily_metrics_generated: bool
    sessions_exported: int
    query_timings: list[QueryTiming]
    total_query_time_ms: float
    total_execution_time_ms: float
    error: str | None = None


class ReportService:
    """Service for generating and delivering marketing reports."""
    
    def __init__(
        self,
        db_session: DBSession,
        email_service: EmailService,
        config: ReportConfig,
    ) -> None:
        pass
    
    async def generate_and_send_reports(
        self,
        report_date: date,
        include_all_users: bool = False,
    ) -> ReportResult:
        """Generate all reports and send via email."""
        pass
    
    def generate_user_summary(
        self,
        report_date: date,
        include_all_users: bool = False,
    ) -> tuple[list[UserSummaryRow], QueryTiming]:
        """Generate user summary report data with timing."""
        pass
    
    def generate_daily_metrics(
        self,
        report_date: date,
    ) -> tuple[DailyMetricsRow, QueryTiming]:
        """Generate daily metrics report data with timing."""
        pass
    
    def export_sessions(
        self,
        report_date: date,
    ) -> tuple[list[SessionExportRow], QueryTiming]:
        """Export successful sessions for the report date with timing."""
        pass
    
    def _log_query_timing(self, timing: QueryTiming) -> None:
        """Log query timing in consistent format."""
        # Format: REPORT_QUERY_TIMING: {query_name} completed in {duration_ms}ms ({row_count} rows)
        pass
    
    def _log_performance_summary(
        self,
        query_timings: list[QueryTiming],
        total_execution_time_ms: float,
    ) -> None:
        """Log performance summary showing query time vs total time."""
        pass
```

### UserSummaryRow

Data structure for user summary report rows.

```python
@dataclass
class UserSummaryRow:
    """Single row in user summary report."""
    
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
```

### DailyMetricsRow

Data structure for daily metrics report.

```python
@dataclass
class DailyMetricsRow:
    """Daily platform metrics."""
    
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
```

### SessionExportRow

Data structure for session export rows.

```python
@dataclass
class SessionExportRow:
    """Single row in sessions export."""
    
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
    conversation_history: str  # JSON string
```

### CSVGenerator

Utility for generating CSV content from report data.

```python
class CSVGenerator:
    """Generates CSV content from report data."""
    
    @staticmethod
    def generate_user_summary_csv(rows: list[UserSummaryRow]) -> str:
        """Generate CSV content for user summary report."""
        pass
    
    @staticmethod
    def generate_daily_metrics_csv(row: DailyMetricsRow) -> str:
        """Generate CSV content for daily metrics report."""
        pass
    
    @staticmethod
    def generate_sessions_csv(rows: list[SessionExportRow]) -> str:
        """Generate CSV content for sessions export."""
        pass
```

### CLI Module

Command-line interface for manual report generation.

```python
# telegram_bot/reports.py

def main():
    """CLI entry point for report generation."""
    pass

def generate_reports(
    date: date | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
    all_users: bool = False,
) -> int:
    """Generate reports for specified date(s)."""
    pass
```

## Data Models

No new database models are required. The implementation uses existing models:

- **User**: For user data and activity timestamps
- **Session**: For session metrics and conversation history
- **SessionEmailEvent**: For email delivery counts

### SQL Queries

#### User Summary Query

```sql
SELECT 
    u.id AS user_id,
    u.email,
    COUNT(s.id) AS total_sessions,
    COUNT(s.id) AS total_prompts,
    COUNT(CASE WHEN s.optimization_method = 'CRAFT' THEN 1 END) AS craft_count,
    COUNT(CASE WHEN s.optimization_method = 'LYRA' THEN 1 END) AS lyra_count,
    COUNT(CASE WHEN s.optimization_method = 'GGL' THEN 1 END) AS ggl_count,
    COALESCE(AVG(s.tokens_total), 0) AS avg_tokens,
    CASE 
        WHEN COUNT(s.id) > 0 
        THEN (COUNT(CASE WHEN s.status = 'successful' THEN 1 END) * 100.0 / COUNT(s.id))
        ELSE 0 
    END AS success_rate,
    u.last_interaction_at AS last_activity,
    COALESCE(AVG(s.duration_seconds), 0) AS avg_duration
FROM users u
LEFT JOIN sessions s ON u.id = s.user_id
WHERE u.last_interaction_at >= :activity_cutoff  -- omitted when include_all_users=True
GROUP BY u.id, u.email, u.last_interaction_at
ORDER BY u.id
```

#### Daily Metrics Query

```sql
SELECT
    :report_date AS date,
    (SELECT COUNT(*) FROM users) AS all_users,
    (SELECT COUNT(DISTINCT user_id) FROM sessions 
     WHERE DATE(start_time) = :report_date) AS active_users,
    (SELECT COUNT(*) FROM users 
     WHERE DATE(first_interaction_at) = :report_date) AS new_users,
    COUNT(CASE WHEN s.status = 'successful' THEN 1 END) AS total_prompts,
    COUNT(CASE WHEN s.status = 'successful' AND s.optimization_method = 'CRAFT' THEN 1 END) AS craft_used,
    COUNT(CASE WHEN s.status = 'successful' AND s.optimization_method = 'LYRA' THEN 1 END) AS lyra_used,
    COUNT(CASE WHEN s.status = 'successful' AND s.optimization_method = 'GGL' THEN 1 END) AS ggl_used,
    COALESCE(AVG(CASE WHEN s.status = 'successful' THEN s.tokens_total END), 0) AS avg_tokens,
    (SELECT COUNT(*) FROM session_email_events 
     WHERE DATE(sent_at) = :report_date AND delivery_status = 'sent') AS total_emails
FROM sessions s
WHERE DATE(s.start_time) = :report_date
```

#### Sessions Export Query

```sql
SELECT 
    id, user_id, start_time, finish_time, duration_seconds,
    status, optimization_method, model_name, used_followup,
    input_tokens, output_tokens, tokens_total,
    followup_start_time, followup_finish_time, followup_duration_seconds,
    followup_input_tokens, followup_output_tokens, followup_tokens_total,
    conversation_history
FROM sessions
WHERE status = 'successful'
  AND DATE(start_time) = :report_date
ORDER BY id
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Configuration Parsing Consistency

*For any* valid environment configuration with REPORT_GENERATION_TIME, REPORT_USER_ACTIVITY_DAYS, and REPORT_RECIPIENT_EMAILS, parsing and then serializing the configuration should produce equivalent values.

**Validates: Requirements 1.1, 1.2, 1.4**

### Property 2: User Activity Filtering

*For any* set of users with various last_interaction_at timestamps and a positive activity_days value N, the User_Summary_Report should include exactly those users whose last_interaction_at is within N days of the report date.

**Validates: Requirements 2.2, 2.3**

### Property 3: Method Count Accuracy

*For any* user with sessions using different optimization methods (CRAFT, LYRA, GGL), the CraftCount, LyraCount, and GglCount in the User_Summary_Report should equal the actual count of sessions with each respective method.

**Validates: Requirements 2.6, 2.7, 2.8**

### Property 4: Success Rate Calculation

*For any* user with a mix of successful and unsuccessful sessions, the SuccessRate should equal (successful_count / total_count) * 100, and TotalPrompts should equal TotalSessions.

**Validates: Requirements 2.5, 2.10**

### Property 5: Average Calculations

*For any* user with sessions having various tokens_total and duration_seconds values, AvgTokens should equal the arithmetic mean of tokens_total, and AvgDuration should equal the arithmetic mean of duration_seconds.

**Validates: Requirements 2.9, 2.12**

### Property 6: Daily Metrics Method Counts

*For any* report date with sessions using different optimization methods, CraftUsed, LyraUsed, and GglUsed should count only successful sessions with the respective method on that date.

**Validates: Requirements 3.5, 3.6, 3.7, 3.8**

### Property 7: Sessions Export Filtering

*For any* set of sessions with various statuses and dates, the Sessions_Export should include exactly those sessions where status equals "successful" AND start_time falls on the report date.

**Validates: Requirements 4.2, 4.3**

### Property 8: Conversation History Serialization Round-Trip

*For any* valid conversation_history JSONB data, serializing to JSON string and parsing back should produce an equivalent data structure.

**Validates: Requirements 4.4**

### Property 9: CSV Column Completeness

*For any* generated User_Summary_Report CSV, the header row should contain exactly the columns: UserID, Email, TotalSessions, TotalPrompts, CraftCount, LyraCount, GglCount, AvgTokens, SuccessRate, LastActivity, AvgDuration.

**Validates: Requirements 2.1**

### Property 10: Report Date Calculation

*For any* scheduled report execution, the report_date parameter should equal the previous day's date (yesterday) relative to the execution time.

**Validates: Requirements 5.2**

### Property 11: Retry Behavior

*For any* report generation that fails, the system should retry exactly 3 times with delays of 1, 5, and 15 minutes before logging failure.

**Validates: Requirements 6.1, 6.2**

### Property 12: CLI Date Parsing

*For any* valid date string in YYYY-MM-DD format passed to --date parameter, the CLI should parse it correctly and generate reports for that exact date.

**Validates: Requirements 7.1, 7.2**

### Property 13: Query Timing Accuracy

*For any* query execution, the logged duration_ms should be a positive number representing actual elapsed time, and the row_count should match the actual number of rows returned.

**Validates: Requirements 9.1, 9.2, 9.3, 9.4**

## Error Handling

### Query Timing Implementation

Each database query is wrapped with timing measurement:

```python
import time

def _execute_timed_query(self, query_name: str, query_func: Callable) -> tuple[Any, QueryTiming]:
    """Execute a query and measure its execution time."""
    start_time = time.perf_counter()
    result = query_func()
    duration_ms = (time.perf_counter() - start_time) * 1000
    
    row_count = len(result) if isinstance(result, list) else 1
    timing = QueryTiming(
        query_name=query_name,
        duration_ms=duration_ms,
        row_count=row_count,
    )
    
    self._log_query_timing(timing)
    return result, timing
```

Log output format:
```
REPORT_QUERY_TIMING: user_summary completed in 245.32ms (1523 rows)
REPORT_QUERY_TIMING: daily_metrics completed in 12.45ms (1 rows)
REPORT_QUERY_TIMING: sessions_export completed in 89.21ms (342 rows)
REPORT_PERFORMANCE_SUMMARY: Total query time: 347.0ms, Total execution time: 1523.4ms, Query overhead: 22.8%
```

### Database Errors

- If a query fails, log the error with full stack trace
- Continue generating remaining reports (graceful degradation)
- Include partial results in email with error note

### Email Delivery Errors

- Use existing EmailService retry logic (3 attempts, exponential backoff)
- After all retries exhausted, log error and continue
- Do not block scheduler for other tasks

### Configuration Errors

- If REPORT_RECIPIENT_EMAILS is empty/missing, log error and skip delivery
- If REPORT_GENERATION_TIME is invalid, use default "01:00"
- If REPORT_USER_ACTIVITY_DAYS is invalid, use default 30

### CSV Generation Errors

- Handle None/null values gracefully (empty string in CSV)
- Escape special characters in conversation_history JSON
- Use UTF-8 encoding for all CSV files

## Testing Strategy

### Unit Tests

- Test ReportConfig.from_env() with various environment configurations
- Test CSVGenerator methods with sample data
- Test date filtering logic in isolation
- Test SQL query result mapping to dataclasses

### Property-Based Tests

Using Hypothesis library for Python:

- **Property 1**: Generate random config values, verify round-trip parsing
- **Property 2**: Generate users with random activity dates, verify filtering
- **Property 3-5**: Generate sessions with random methods/tokens/durations, verify calculations
- **Property 6**: Generate daily sessions, verify method counts
- **Property 7**: Generate sessions with various statuses/dates, verify export filtering
- **Property 8**: Generate random conversation history, verify JSON round-trip
- **Property 9**: Generate reports, verify CSV headers
- **Property 10**: Generate execution times, verify report date is yesterday
- **Property 11**: Simulate failures, verify retry count and delays
- **Property 12**: Generate valid date strings, verify parsing
- **Property 13**: Execute queries, verify timing is positive and row counts match

### Integration Tests

- Test full report generation with test database
- Test email delivery with mock SMTP server
- Test CLI commands with various arguments
- Test scheduler integration with BackgroundTaskScheduler
