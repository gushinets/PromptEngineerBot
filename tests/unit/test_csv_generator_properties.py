"""Property-based tests for CSV Generator.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 9: CSV Column Completeness**
**Validates: Requirements 2.1**

**Feature: marketing-reports, Property 8: Conversation History Serialization Round-Trip**
**Validates: Requirements 4.4**
"""

import csv
import io
import json
from datetime import UTC, datetime
from typing import ClassVar

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from telegram_bot.services.csv_generator import CSVGenerator
from telegram_bot.services.report_models import SessionExportRow, UserSummaryRow


# Strategy for generating valid UserSummaryRow objects
user_summary_row_strategy = st.builds(
    UserSummaryRow,
    user_id=st.integers(min_value=1, max_value=1000000),
    email=st.one_of(st.none(), st.emails()),
    total_sessions=st.integers(min_value=0, max_value=10000),
    total_prompts=st.integers(min_value=0, max_value=10000),
    craft_count=st.integers(min_value=0, max_value=10000),
    lyra_count=st.integers(min_value=0, max_value=10000),
    ggl_count=st.integers(min_value=0, max_value=10000),
    avg_tokens=st.floats(min_value=0, max_value=100000, allow_nan=False, allow_infinity=False),
    success_rate=st.floats(min_value=0, max_value=100, allow_nan=False, allow_infinity=False),
    last_activity=st.datetimes(
        min_value=datetime(2020, 1, 1),
        max_value=datetime(2030, 12, 31),
        timezones=st.just(UTC),
    ),
    avg_duration=st.floats(min_value=0, max_value=86400, allow_nan=False, allow_infinity=False),
)


# Strategy for generating conversation history message objects
# Represents typical chat message structure with role and content
conversation_message_strategy = st.fixed_dictionaries(
    {
        "role": st.sampled_from(["user", "assistant", "system"]),
        "content": st.text(min_size=0, max_size=500),
    }
)

# Strategy for generating valid conversation history (list of messages)
conversation_history_strategy = st.lists(
    conversation_message_strategy,
    min_size=0,
    max_size=10,
)

# Strategy for generating datetime with timezone for SessionExportRow
session_datetime_strategy = st.datetimes(
    min_value=datetime(2020, 1, 1),
    max_value=datetime(2030, 12, 31),
    timezones=st.just(UTC),
)

# Strategy for generating valid SessionExportRow objects with conversation history
session_export_row_strategy = st.builds(
    SessionExportRow,
    id=st.integers(min_value=1, max_value=1000000),
    user_id=st.integers(min_value=1, max_value=1000000),
    start_time=session_datetime_strategy,
    finish_time=st.one_of(st.none(), session_datetime_strategy),
    duration_seconds=st.one_of(st.none(), st.integers(min_value=0, max_value=86400)),
    status=st.just("successful"),
    optimization_method=st.one_of(st.none(), st.sampled_from(["CRAFT", "LYRA", "GGL"])),
    model_name=st.sampled_from(["gpt-4", "gpt-3.5-turbo", "claude-3"]),
    used_followup=st.booleans(),
    input_tokens=st.integers(min_value=0, max_value=100000),
    output_tokens=st.integers(min_value=0, max_value=100000),
    tokens_total=st.integers(min_value=0, max_value=200000),
    followup_start_time=st.one_of(st.none(), session_datetime_strategy),
    followup_finish_time=st.one_of(st.none(), session_datetime_strategy),
    followup_duration_seconds=st.one_of(st.none(), st.integers(min_value=0, max_value=86400)),
    followup_input_tokens=st.integers(min_value=0, max_value=100000),
    followup_output_tokens=st.integers(min_value=0, max_value=100000),
    followup_tokens_total=st.integers(min_value=0, max_value=200000),
    # conversation_history is stored as JSON string in the dataclass
    conversation_history=st.builds(json.dumps, conversation_history_strategy),
)


class TestCSVColumnCompleteness:
    """
    **Feature: marketing-reports, Property 9: CSV Column Completeness**
    **Validates: Requirements 2.1**

    Property 9: CSV Column Completeness
    *For any* generated User_Summary_Report CSV, the header row should contain
    exactly the columns: UserID, Email, TotalSessions, TotalPrompts, CraftCount,
    LyraCount, GglCount, AvgTokens, SuccessRate, LastActivity, AvgDuration.
    """

    # Expected columns as defined in Requirement 2.1
    EXPECTED_COLUMNS: ClassVar[list[str]] = [
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

    @given(rows=st.lists(user_summary_row_strategy, min_size=0, max_size=10))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_user_summary_csv_has_exact_columns(self, rows: list[UserSummaryRow]):
        """
        **Feature: marketing-reports, Property 9: CSV Column Completeness**
        **Validates: Requirements 2.1**

        For any list of UserSummaryRow objects (including empty list),
        the generated CSV should have exactly the required columns in the
        correct order.
        """
        # Generate CSV
        csv_content = CSVGenerator.generate_user_summary_csv(rows)

        # Parse the CSV to extract header
        reader = csv.reader(io.StringIO(csv_content))
        header = next(reader)

        # Property: Header should contain exactly the expected columns
        assert header == self.EXPECTED_COLUMNS, (
            f"CSV header should be {self.EXPECTED_COLUMNS}, got: {header}"
        )

    @given(rows=st.lists(user_summary_row_strategy, min_size=1, max_size=10))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_user_summary_csv_row_count_matches_input(self, rows: list[UserSummaryRow]):
        """
        **Feature: marketing-reports, Property 9: CSV Column Completeness**
        **Validates: Requirements 2.1**

        For any non-empty list of UserSummaryRow objects, the generated CSV
        should have exactly len(rows) + 1 lines (header + data rows).
        """
        # Generate CSV
        csv_content = CSVGenerator.generate_user_summary_csv(rows)

        # Parse the CSV to count rows
        reader = csv.reader(io.StringIO(csv_content))
        all_rows = list(reader)

        # Property: Should have header + data rows
        expected_row_count = len(rows) + 1  # +1 for header
        assert len(all_rows) == expected_row_count, (
            f"CSV should have {expected_row_count} rows (1 header + {len(rows)} data), "
            f"got: {len(all_rows)}"
        )

    @given(rows=st.lists(user_summary_row_strategy, min_size=1, max_size=10))
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_user_summary_csv_data_rows_have_correct_column_count(self, rows: list[UserSummaryRow]):
        """
        **Feature: marketing-reports, Property 9: CSV Column Completeness**
        **Validates: Requirements 2.1**

        For any list of UserSummaryRow objects, each data row in the generated
        CSV should have exactly 11 columns (matching the header).
        """
        # Generate CSV
        csv_content = CSVGenerator.generate_user_summary_csv(rows)

        # Parse the CSV
        reader = csv.reader(io.StringIO(csv_content))
        header = next(reader)
        expected_column_count = len(header)

        # Property: Each data row should have the same number of columns as header
        for i, data_row in enumerate(reader):
            assert len(data_row) == expected_column_count, (
                f"Data row {i} should have {expected_column_count} columns, got: {len(data_row)}"
            )


class TestConversationHistorySerializationRoundTrip:
    """
    **Feature: marketing-reports, Property 8: Conversation History Serialization Round-Trip**
    **Validates: Requirements 4.4**

    Property 8: Conversation History Serialization Round-Trip
    *For any* valid conversation_history JSONB data, serializing to JSON string
    and parsing back should produce an equivalent data structure.
    """

    @given(conversation_history=conversation_history_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_conversation_history_json_round_trip(
        self,
        conversation_history: list[dict],
    ):
        """
        **Feature: marketing-reports, Property 8: Conversation History Serialization Round-Trip**
        **Validates: Requirements 4.4**

        For any valid conversation history data structure, serializing to JSON
        and parsing back should produce an equivalent data structure.
        """
        # Serialize to JSON string
        json_string = json.dumps(conversation_history)

        # Parse back from JSON string
        parsed_history = json.loads(json_string)

        # Property: Round-trip should produce equivalent data
        assert parsed_history == conversation_history, (
            f"Round-trip should preserve conversation history.\n"
            f"Original: {conversation_history}\n"
            f"After round-trip: {parsed_history}"
        )

    @given(session_row=session_export_row_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_session_export_csv_preserves_conversation_history(
        self,
        session_row: SessionExportRow,
    ):
        """
        **Feature: marketing-reports, Property 8: Conversation History Serialization Round-Trip**
        **Validates: Requirements 4.4**

        For any SessionExportRow with conversation_history, generating CSV and
        extracting the conversation_history column should allow parsing back
        to the original data structure.
        """
        # Generate CSV with single session row
        csv_content = CSVGenerator.generate_sessions_csv([session_row])

        # Parse the CSV to extract conversation_history column
        reader = csv.reader(io.StringIO(csv_content))
        header = next(reader)
        data_row = next(reader)

        # Find the conversation_history column index
        history_index = header.index("conversation_history")
        csv_history_value = data_row[history_index]

        # Parse the original conversation_history from the session row
        original_history = json.loads(session_row.conversation_history)

        # Parse the conversation_history from CSV (if not empty)
        csv_parsed_history = json.loads(csv_history_value) if csv_history_value else []

        # Property: CSV round-trip should preserve conversation history
        assert csv_parsed_history == original_history, (
            f"CSV round-trip should preserve conversation history.\n"
            f"Original: {original_history}\n"
            f"From CSV: {csv_parsed_history}"
        )

    @given(
        conversation_history=st.lists(
            st.fixed_dictionaries(
                {
                    "role": st.sampled_from(["user", "assistant", "system"]),
                    "content": st.text(
                        alphabet=st.characters(
                            whitelist_categories=("L", "N", "P", "S", "Z"),
                            whitelist_characters='\n\t"\\/',
                        ),
                        min_size=0,
                        max_size=200,
                    ),
                }
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_conversation_history_with_special_characters_round_trip(
        self,
        conversation_history: list[dict],
    ):
        """
        **Feature: marketing-reports, Property 8: Conversation History Serialization Round-Trip**
        **Validates: Requirements 4.4**

        For any conversation history containing special characters (quotes,
        newlines, backslashes, etc.), serializing to JSON and parsing back
        should produce an equivalent data structure.
        """
        # Serialize to JSON string
        json_string = json.dumps(conversation_history)

        # Parse back from JSON string
        parsed_history = json.loads(json_string)

        # Property: Round-trip should preserve data even with special characters
        assert parsed_history == conversation_history, (
            f"Round-trip should preserve conversation history with special chars.\n"
            f"Original: {conversation_history}\n"
            f"After round-trip: {parsed_history}"
        )
