# Implementation Plan: Marketing Reports

## Overview

This implementation plan breaks down the marketing reports feature into discrete coding tasks. The approach leverages existing infrastructure (BackgroundTaskScheduler, EmailService, database models) and follows the Hybrid Approach with real-time queries and proper timing instrumentation.

## Tasks

- [x] 1. Create report configuration module
  - [x] 1.1 Create ReportConfig dataclass in telegram_bot/services/report_config.py
    - Define dataclass with generation_time, user_activity_days, recipient_emails fields
    - Implement from_env() class method to load from environment variables
    - Handle defaults: "01:00" for time, 30 for days, empty list for emails
    - Parse comma-separated REPORT_RECIPIENT_EMAILS into list
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

  - [x] 1.2 Write property test for configuration parsing
    - **Property 1: Configuration Parsing Consistency**
    - **Validates: Requirements 1.1, 1.2, 1.4**

- [x] 2. Create report data models
  - [x] 2.1 Create report data structures in telegram_bot/services/report_models.py
    - Define UserSummaryRow dataclass with all 11 fields
    - Define DailyMetricsRow dataclass with all 10 fields
    - Define SessionExportRow dataclass with all 19 fields
    - Define QueryTiming dataclass with query_name, duration_ms, row_count
    - Define ReportResult dataclass with success, counts, timings, error
    - _Requirements: 2.1, 3.1, 4.5, 9.1, 9.2, 9.3_

- [x] 3. Implement CSV generator
  - [x] 3.1 Create CSVGenerator class in telegram_bot/services/csv_generator.py
    - Implement generate_user_summary_csv() with proper column headers
    - Implement generate_daily_metrics_csv() with proper column headers
    - Implement generate_sessions_csv() with JSON serialization for conversation_history
    - Use UTF-8 encoding and handle None values as empty strings
    - _Requirements: 2.1, 3.1, 4.1, 4.4, 4.5_

  - [x] 3.2 Write property test for CSV column completeness
    - **Property 9: CSV Column Completeness**
    - **Validates: Requirements 2.1**

  - [x] 3.3 Write property test for conversation history serialization
    - **Property 8: Conversation History Serialization Round-Trip**
    - **Validates: Requirements 4.4**

- [x] 4. Implement ReportService core
  - [x] 4.1 Create ReportService class in telegram_bot/services/report_service.py
    - Initialize with db_session, email_service, config
    - Implement _execute_timed_query() helper for timing measurement
    - Implement _log_query_timing() with consistent format
    - Implement _log_performance_summary() for end-of-generation summary
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 4.2 Implement generate_user_summary() method
    - Build SQL query with LEFT JOIN on users and sessions
    - Apply activity date filter when user_activity_days > 0
    - Calculate all metrics: TotalSessions, method counts, AvgTokens, SuccessRate, AvgDuration
    - Return list of UserSummaryRow with QueryTiming
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12_

  - [x] 4.3 Write property tests for user summary calculations
    - **Property 2: User Activity Filtering**
    - **Property 3: Method Count Accuracy**
    - **Property 4: Success Rate Calculation**
    - **Property 5: Average Calculations**
    - **Validates: Requirements 2.2, 2.3, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.12**

  - [x] 4.4 Implement generate_daily_metrics() method
    - Build SQL query for daily aggregate metrics
    - Calculate AllUsers, ActiveUsers, NewUsers from users table
    - Calculate TotalPrompts, method counts from successful sessions only
    - Calculate AvgTokens from successful sessions
    - Calculate TotalEmails from session_email_events
    - Return DailyMetricsRow with QueryTiming
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10_

  - [x] 4.5 Write property test for daily metrics method counts
    - **Property 6: Daily Metrics Method Counts**
    - **Validates: Requirements 3.5, 3.6, 3.7, 3.8**

  - [x] 4.6 Implement export_sessions() method
    - Build SQL query selecting all session columns
    - Filter by status='successful' and start_time on report_date
    - Serialize conversation_history as JSON string
    - Return list of SessionExportRow with QueryTiming
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 4.7 Write property test for sessions export filtering
    - **Property 7: Sessions Export Filtering**
    - **Validates: Requirements 4.2, 4.3**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement report generation and delivery
  - [x] 6.1 Implement generate_and_send_reports() method
    - Generate all three reports with timing
    - Create CSV files using CSVGenerator
    - Name files: user_summary_YYYY-MM-DD.csv, daily_metrics_YYYY-MM-DD.csv, sessions_YYYY-MM-DD.csv
    - Send email with all three attachments to all recipients
    - Log performance summary at end
    - Return ReportResult with all metrics
    - _Requirements: 5.3, 5.4, 5.5, 8.1, 8.2, 8.3, 9.5_

  - [x] 6.2 Implement retry logic with exponential backoff
    - Use tenacity library for retry decorator
    - Configure 3 retry attempts
    - Configure delays: 1 minute, 5 minutes, 15 minutes
    - Log error after all retries exhausted
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

  - [x] 6.3 Write property test for retry behavior
    - **Property 11: Retry Behavior**
    - **Validates: Requirements 6.1, 6.2**

- [x] 7. Implement email delivery for reports
  - [x] 7.1 Add send_report_email() method to EmailService
    - Accept list of CSV attachments (filename, content pairs)
    - Accept list of recipient emails
    - Create email with all attachments
    - Use existing retry logic from EmailService
    - Log delivery status for each recipient
    - _Requirements: 5.4, 5.5, 8.5_

- [x] 8. Integrate with BackgroundTaskScheduler
  - [x] 8.1 Create daily_reports_task() function in background_tasks.py
    - Load ReportConfig from environment
    - Calculate report_date as yesterday
    - Initialize ReportService with dependencies
    - Call generate_and_send_reports()
    - Return task result dict with success/failure info
    - _Requirements: 5.1, 5.2_

  - [x] 8.2 Register task in init_background_tasks()
    - Parse REPORT_GENERATION_TIME to get hour
    - Add task with appropriate interval
    - Configure to run at specified time
    - _Requirements: 5.1_

  - [x] 8.3 Write property test for report date calculation
    - **Property 10: Report Date Calculation**
    - **Validates: Requirements 5.2**

- [x] 9. Implement CLI module
  - [x] 9.1 Create CLI entry point in telegram_bot/reports.py
    - Use argparse for argument parsing
    - Accept --date parameter (YYYY-MM-DD format)
    - Accept --from and --to parameters for date range
    - Accept --all-users flag
    - Output progress to stdout
    - Exit with appropriate codes (0 success, non-zero failure)
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [x] 9.2 Write property test for CLI date parsing
    - **Property 12: CLI Date Parsing**
    - **Validates: Requirements 7.1, 7.2**

- [x] 10. Add environment variable documentation
  - [x] 10.1 Update .env.example with new variables
    - Add REPORT_GENERATION_TIME with default "01:00"
    - Add REPORT_USER_ACTIVITY_DAYS with default 30
    - Add REPORT_RECIPIENT_EMAILS as comma-separated list
    - Add comments explaining each variable
    - _Requirements: 1.1, 1.2, 1.4_

- [x] 11. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- All tasks including property tests are required
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The implementation reuses existing EmailService retry logic where possible
- Query timing uses time.perf_counter() for high-precision measurement
