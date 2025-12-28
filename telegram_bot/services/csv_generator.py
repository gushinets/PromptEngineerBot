"""
CSV Generator for marketing reports.

This module provides utilities for generating CSV content from report data
structures, handling proper encoding and None value conversion.
"""

import csv
import io
import json
from typing import Any, ClassVar

from telegram_bot.services.report_models import (
    DailyMetricsRow,
    SessionExportRow,
    UserSummaryRow,
)


class CSVGenerator:
    """
    Generates CSV content from report data.

    Provides static methods to convert report data structures into
    properly formatted CSV strings with UTF-8 encoding.
    """

    # Column headers for User Summary Report (Requirement 2.1)
    USER_SUMMARY_COLUMNS: ClassVar[list[str]] = [
        "UserID",
        "Email",
        "TotalSessions",
        "TotalPrompts",
        "CraftCount",
        "LyraCount",
        "GglCount",
        "AvgTokens",
        "SuccessRate",
        "LastActivity",
        "AvgDuration",
    ]

    # Column headers for Daily Metrics Report (Requirement 3.1)
    DAILY_METRICS_COLUMNS: ClassVar[list[str]] = [
        "Date",
        "AllUsers",
        "ActiveUsers",
        "NewUsers",
        "TotalPrompts",
        "CraftUsed",
        "LyraUsed",
        "GglUsed",
        "AvgTokens",
        "TotalEmails",
    ]

    # Column headers for Sessions Export (Requirement 4.5)
    SESSIONS_COLUMNS: ClassVar[list[str]] = [
        "id",
        "user_id",
        "start_time",
        "finish_time",
        "duration_seconds",
        "status",
        "optimization_method",
        "model_name",
        "used_followup",
        "input_tokens",
        "output_tokens",
        "tokens_total",
        "followup_start_time",
        "followup_finish_time",
        "followup_duration_seconds",
        "followup_input_tokens",
        "followup_output_tokens",
        "followup_tokens_total",
        "conversation_history",
    ]

    @staticmethod
    def _format_value(value: Any) -> str:
        """
        Format a value for CSV output.

        Handles None values by converting to empty string,
        and formats other types appropriately.

        Args:
            value: The value to format

        Returns:
            String representation suitable for CSV
        """
        if value is None:
            return ""
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, float):
            return f"{value:.2f}"
        return str(value)

    @staticmethod
    def generate_user_summary_csv(rows: list[UserSummaryRow]) -> str:
        """
        Generate CSV content for user summary report.

        Creates a CSV with columns: UserID, Email, TotalSessions, TotalPrompts,
        CraftCount, LyraCount, GglCount, AvgTokens, SuccessRate, LastActivity,
        AvgDuration.

        Args:
            rows: List of UserSummaryRow objects to convert

        Returns:
            UTF-8 encoded CSV string with header row and data rows
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write header row
        writer.writerow(CSVGenerator.USER_SUMMARY_COLUMNS)

        # Write data rows
        for row in rows:
            writer.writerow(
                [
                    CSVGenerator._format_value(row.user_id),
                    CSVGenerator._format_value(row.email),
                    CSVGenerator._format_value(row.total_sessions),
                    CSVGenerator._format_value(row.total_prompts),
                    CSVGenerator._format_value(row.craft_count),
                    CSVGenerator._format_value(row.lyra_count),
                    CSVGenerator._format_value(row.ggl_count),
                    CSVGenerator._format_value(row.avg_tokens),
                    CSVGenerator._format_value(row.success_rate),
                    CSVGenerator._format_value(row.last_activity),
                    CSVGenerator._format_value(row.avg_duration),
                ]
            )

        return output.getvalue()

    @staticmethod
    def generate_daily_metrics_csv(row: DailyMetricsRow) -> str:
        """
        Generate CSV content for daily metrics report.

        Creates a CSV with columns: Date, AllUsers, ActiveUsers, NewUsers,
        TotalPrompts, CraftUsed, LyraUsed, GglUsed, AvgTokens, TotalEmails.

        Args:
            row: DailyMetricsRow object to convert

        Returns:
            UTF-8 encoded CSV string with header row and single data row
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write header row
        writer.writerow(CSVGenerator.DAILY_METRICS_COLUMNS)

        # Write data row
        writer.writerow(
            [
                CSVGenerator._format_value(row.date),
                CSVGenerator._format_value(row.all_users),
                CSVGenerator._format_value(row.active_users),
                CSVGenerator._format_value(row.new_users),
                CSVGenerator._format_value(row.total_prompts),
                CSVGenerator._format_value(row.craft_used),
                CSVGenerator._format_value(row.lyra_used),
                CSVGenerator._format_value(row.ggl_used),
                CSVGenerator._format_value(row.avg_tokens),
                CSVGenerator._format_value(row.total_emails),
            ]
        )

        return output.getvalue()

    @staticmethod
    def generate_sessions_csv(rows: list[SessionExportRow]) -> str:
        """
        Generate CSV content for sessions export.

        Creates a CSV with all session columns including conversation_history
        serialized as a JSON string.

        Args:
            rows: List of SessionExportRow objects to convert

        Returns:
            UTF-8 encoded CSV string with header row and data rows
        """
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

        # Write header row
        writer.writerow(CSVGenerator.SESSIONS_COLUMNS)

        # Write data rows
        for row in rows:
            # conversation_history is already a JSON string from the dataclass
            # but we ensure it's properly formatted
            conversation_history = row.conversation_history
            if conversation_history and not isinstance(conversation_history, str):
                conversation_history = json.dumps(conversation_history)

            writer.writerow(
                [
                    CSVGenerator._format_value(row.id),
                    CSVGenerator._format_value(row.user_id),
                    CSVGenerator._format_value(row.start_time),
                    CSVGenerator._format_value(row.finish_time),
                    CSVGenerator._format_value(row.duration_seconds),
                    CSVGenerator._format_value(row.status),
                    CSVGenerator._format_value(row.optimization_method),
                    CSVGenerator._format_value(row.model_name),
                    CSVGenerator._format_value(row.used_followup),
                    CSVGenerator._format_value(row.input_tokens),
                    CSVGenerator._format_value(row.output_tokens),
                    CSVGenerator._format_value(row.tokens_total),
                    CSVGenerator._format_value(row.followup_start_time),
                    CSVGenerator._format_value(row.followup_finish_time),
                    CSVGenerator._format_value(row.followup_duration_seconds),
                    CSVGenerator._format_value(row.followup_input_tokens),
                    CSVGenerator._format_value(row.followup_output_tokens),
                    CSVGenerator._format_value(row.followup_tokens_total),
                    conversation_history if conversation_history else "",
                ]
            )

        return output.getvalue()
