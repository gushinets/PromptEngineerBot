# Requirements Document

## Introduction

This document specifies the requirements for a daily marketing reports feature that generates and emails user activity summaries, daily metrics, and session data to marketing stakeholders. The system will leverage existing infrastructure (BackgroundTaskScheduler, EmailService) to deliver CSV reports at a configurable time each day, with support for historical report generation via CLI.

## Glossary

- **Report_Service**: The service responsible for generating marketing reports by aggregating data from users and sessions tables
- **User_Summary_Report**: CSV report containing per-user metrics including session counts, method usage, tokens, and success rates
- **Daily_Metrics_Report**: CSV report containing aggregate platform metrics for a specific date
- **Sessions_Export**: CSV export of successful sessions including conversation history
- **Background_Scheduler**: Existing BackgroundTaskScheduler that runs periodic tasks
- **Email_Service**: Existing EmailService with SMTP integration and retry logic
- **Active_User**: A user who has had at least one session within the configured activity window
- **Successful_Session**: A session with status="successful"
- **Activity_Window**: Configurable number of days (N) to filter active users, where 0 means all users

## Requirements

### Requirement 1: Report Configuration

**User Story:** As a system administrator, I want to configure report generation settings via environment variables, so that I can customize report timing and scope without code changes.

#### Acceptance Criteria

1. THE Report_Service SHALL read REPORT_GENERATION_TIME from environment with default value "01:00" (1 AM UTC)
2. THE Report_Service SHALL read REPORT_USER_ACTIVITY_DAYS from environment with default value 30
3. WHEN REPORT_USER_ACTIVITY_DAYS is set to 0, THE Report_Service SHALL include all users regardless of activity date
4. THE Report_Service SHALL read REPORT_RECIPIENT_EMAILS from environment as a comma-separated list of email addresses
5. IF REPORT_RECIPIENT_EMAILS is not configured or empty, THEN THE Report_Service SHALL log an error and skip report delivery

### Requirement 2: User Summary Report Generation

**User Story:** As a marketing analyst, I want to receive a daily user summary report, so that I can analyze individual user engagement and behavior patterns.

#### Acceptance Criteria

1. THE Report_Service SHALL generate a User_Summary_Report CSV with columns: UserID, Email, TotalSessions, TotalPrompts, CraftCount, LyraCount, GglCount, AvgTokens, SuccessRate, LastActivity, AvgDuration
2. WHEN REPORT_USER_ACTIVITY_DAYS is greater than 0, THE Report_Service SHALL include only users with last_interaction_at within the configured number of days
3. WHEN REPORT_USER_ACTIVITY_DAYS equals 0, THE Report_Service SHALL include all users in the database
4. THE Report_Service SHALL calculate TotalSessions as the count of all sessions for each user
5. THE Report_Service SHALL calculate TotalPrompts as equal to TotalSessions (one prompt per session)
6. THE Report_Service SHALL calculate CraftCount as the count of sessions where optimization_method equals "CRAFT"
7. THE Report_Service SHALL calculate LyraCount as the count of sessions where optimization_method equals "LYRA"
8. THE Report_Service SHALL calculate GglCount as the count of sessions where optimization_method equals "GGL"
9. THE Report_Service SHALL calculate AvgTokens as the average of tokens_total across all user sessions
10. THE Report_Service SHALL calculate SuccessRate as (successful sessions / total sessions) * 100 for each user
11. THE Report_Service SHALL set LastActivity to the user's last_interaction_at timestamp
12. THE Report_Service SHALL calculate AvgDuration as the average of duration_seconds across all user sessions

### Requirement 3: Daily Metrics Report Generation

**User Story:** As a marketing analyst, I want to receive a daily platform metrics report, so that I can track overall platform usage and trends.

#### Acceptance Criteria

1. THE Report_Service SHALL generate a Daily_Metrics_Report CSV with columns: Date, AllUsers, ActiveUsers, NewUsers, TotalPrompts, CraftUsed, LyraUsed, GglUsed, AvgTokens, TotalEmails
2. THE Report_Service SHALL calculate AllUsers as the total count of users in the database
3. THE Report_Service SHALL calculate ActiveUsers as the count of users with at least one session on the report date
4. THE Report_Service SHALL calculate NewUsers as the count of users with first_interaction_at on the report date
5. THE Report_Service SHALL calculate TotalPrompts as the count of successful sessions on the report date
6. THE Report_Service SHALL calculate CraftUsed as the count of successful sessions with optimization_method "CRAFT" on the report date
7. THE Report_Service SHALL calculate LyraUsed as the count of successful sessions with optimization_method "LYRA" on the report date
8. THE Report_Service SHALL calculate GglUsed as the count of successful sessions with optimization_method "GGL" on the report date
9. THE Report_Service SHALL calculate AvgTokens as the average tokens_total of successful sessions on the report date
10. THE Report_Service SHALL calculate TotalEmails as the count of session_email_events with delivery_status "sent" on the report date

### Requirement 4: Sessions Export

**User Story:** As a marketing analyst, I want to receive an export of successful sessions with conversation history, so that I can analyze user interactions and prompt quality.

#### Acceptance Criteria

1. THE Report_Service SHALL generate a Sessions_Export CSV containing all columns from the sessions table
2. THE Report_Service SHALL include only sessions with status "successful" in the export
3. THE Report_Service SHALL include only sessions with start_time on the report date
4. THE Report_Service SHALL serialize the conversation_history JSONB field as a raw JSON string in the CSV
5. THE Report_Service SHALL include columns: id, user_id, start_time, finish_time, duration_seconds, status, optimization_method, model_name, used_followup, input_tokens, output_tokens, tokens_total, followup_start_time, followup_finish_time, followup_duration_seconds, followup_input_tokens, followup_output_tokens, followup_tokens_total, conversation_history

### Requirement 5: Scheduled Report Delivery

**User Story:** As a marketing analyst, I want reports delivered automatically at a configured time each day, so that I receive fresh data without manual intervention.

#### Acceptance Criteria

1. THE Background_Scheduler SHALL execute the report generation task daily at the time specified by REPORT_GENERATION_TIME
2. WHEN the scheduled task runs, THE Report_Service SHALL generate reports for the previous day's data
3. THE Report_Service SHALL create three CSV attachments: user_summary_YYYY-MM-DD.csv, daily_metrics_YYYY-MM-DD.csv, sessions_YYYY-MM-DD.csv
4. THE Email_Service SHALL send the report email to all addresses in REPORT_RECIPIENT_EMAILS
5. THE Email_Service SHALL include all three CSV files as attachments in a single email

### Requirement 6: Report Delivery Retry Logic

**User Story:** As a system administrator, I want failed report deliveries to retry automatically, so that temporary failures don't result in missed reports.

#### Acceptance Criteria

1. IF report generation fails, THEN THE Report_Service SHALL retry up to 3 times
2. THE Report_Service SHALL use exponential backoff delays: 1 minute, 5 minutes, 15 minutes between retries
3. IF all retry attempts fail, THEN THE Report_Service SHALL log the error with full details
4. THE Report_Service SHALL not block other scheduled tasks during retry attempts

### Requirement 7: Historical Report Generation via CLI

**User Story:** As a system administrator, I want to generate reports for past dates via command line, so that I can retrieve historical data or regenerate failed reports.

#### Acceptance Criteria

1. THE CLI SHALL accept a --date parameter in YYYY-MM-DD format to generate reports for a specific date
2. THE CLI SHALL accept --from and --to parameters to generate reports for a date range
3. THE CLI SHALL accept an --all-users flag to override REPORT_USER_ACTIVITY_DAYS and include all users
4. WHEN --all-users is specified, THE Report_Service SHALL include all users regardless of the configured activity window
5. THE CLI SHALL output progress information to stdout during report generation
6. THE CLI SHALL exit with code 0 on success and non-zero on failure

### Requirement 8: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive logging of report generation, so that I can diagnose issues and monitor system health.

#### Acceptance Criteria

1. THE Report_Service SHALL log the start of report generation with timestamp and parameters
2. THE Report_Service SHALL log the completion of each report type (user summary, daily metrics, sessions)
3. THE Report_Service SHALL log the row count for each generated CSV
4. IF a database query fails, THEN THE Report_Service SHALL log the error and continue with remaining reports
5. THE Report_Service SHALL log email delivery success or failure for each recipient
6. THE Report_Service SHALL log total execution time for the complete report generation cycle

### Requirement 9: Query Performance Logging

**User Story:** As a system administrator, I want to see how long each database query takes, so that I can identify performance bottlenecks and optimize queries over time.

#### Acceptance Criteria

1. THE Report_Service SHALL measure and log the execution time of the user summary query in milliseconds
2. THE Report_Service SHALL measure and log the execution time of the daily metrics query in milliseconds
3. THE Report_Service SHALL measure and log the execution time of the sessions export query in milliseconds
4. THE Report_Service SHALL log query timing with a consistent format: "REPORT_QUERY_TIMING: {query_name} completed in {duration_ms}ms ({row_count} rows)"
5. THE Report_Service SHALL log a performance summary at the end of report generation showing total query time vs total execution time
