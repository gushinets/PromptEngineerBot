"""Property-based tests for CLI date parsing.

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document for the marketing
reports feature.

**Feature: marketing-reports, Property 12: CLI Date Parsing**
**Validates: Requirements 7.1, 7.2**
"""

import argparse
from datetime import date, timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from telegram_bot.reports import create_parser, parse_date, validate_args


# Strategy for generating valid dates
# We use a reasonable range of dates for testing
valid_date_strategy = st.dates(
    min_value=date(2000, 1, 1),
    max_value=date(2099, 12, 31),
)


class TestCLIDateParsing:
    """
    **Feature: marketing-reports, Property 12: CLI Date Parsing**
    **Validates: Requirements 7.1, 7.2**

    Property 12: CLI Date Parsing
    *For any* valid date string in YYYY-MM-DD format passed to --date parameter,
    the CLI should parse it correctly and generate reports for that exact date.
    """

    @given(test_date=valid_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_parse_date_preserves_date_value(self, test_date: date):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.1**

        For any valid date, formatting it as YYYY-MM-DD and parsing it
        should produce the exact same date object.
        """
        # Format date as YYYY-MM-DD string
        date_str = test_date.strftime("%Y-%m-%d")

        # Parse the string back to a date
        parsed_date = parse_date(date_str)

        # Property: parsed date should equal original date
        assert parsed_date == test_date, (
            f"parse_date('{date_str}') should return {test_date}, but got {parsed_date}"
        )

    @given(test_date=valid_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_parse_date_preserves_year_month_day(self, test_date: date):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.1**

        For any valid date, parsing should preserve the exact year,
        month, and day components.
        """
        date_str = test_date.strftime("%Y-%m-%d")
        parsed_date = parse_date(date_str)

        # Property: all date components should match
        assert parsed_date.year == test_date.year, (
            f"Year mismatch: expected {test_date.year}, got {parsed_date.year}"
        )
        assert parsed_date.month == test_date.month, (
            f"Month mismatch: expected {test_date.month}, got {parsed_date.month}"
        )
        assert parsed_date.day == test_date.day, (
            f"Day mismatch: expected {test_date.day}, got {parsed_date.day}"
        )

    @given(test_date=valid_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_cli_parser_with_date_argument(self, test_date: date):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.1**

        For any valid date passed via --date argument, the CLI parser
        should correctly parse it to the exact date object.
        """
        date_str = test_date.strftime("%Y-%m-%d")
        parser = create_parser()

        # Parse the --date argument
        args = parser.parse_args(["--date", date_str])

        # Property: parsed date should equal original date
        assert args.date == test_date, (
            f"Parser with --date {date_str} should produce {test_date}, but got {args.date}"
        )

    @given(
        from_date=valid_date_strategy,
        days_offset=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_cli_parser_with_date_range(self, from_date: date, days_offset: int):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.2**

        For any valid date range passed via --from and --to arguments,
        the CLI parser should correctly parse both dates.
        """
        to_date = from_date + timedelta(days=days_offset)

        # Ensure to_date is within valid range
        to_date = min(to_date, date(2099, 12, 31))

        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")

        parser = create_parser()
        args = parser.parse_args(["--from", from_str, "--to", to_str])

        # Property: both dates should be parsed correctly
        assert args.from_date == from_date, (
            f"Parser with --from {from_str} should produce {from_date}, but got {args.from_date}"
        )
        assert args.to_date == to_date, (
            f"Parser with --to {to_str} should produce {to_date}, but got {args.to_date}"
        )

    @given(
        from_date=valid_date_strategy,
        days_offset=st.integers(min_value=0, max_value=30),
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_args_generates_correct_date_list(self, from_date: date, days_offset: int):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.2**

        For any valid date range, validate_args should generate a list
        containing all dates from from_date to to_date inclusive.
        """
        to_date = from_date + timedelta(days=days_offset)

        # Ensure to_date is within valid range
        if to_date > date(2099, 12, 31):
            to_date = date(2099, 12, 31)
            days_offset = (to_date - from_date).days

        from_str = from_date.strftime("%Y-%m-%d")
        to_str = to_date.strftime("%Y-%m-%d")

        parser = create_parser()
        args = parser.parse_args(["--from", from_str, "--to", to_str])

        dates, _ = validate_args(args)

        # Property: date list should have correct length
        expected_length = days_offset + 1
        assert len(dates) == expected_length, (
            f"Date range from {from_date} to {to_date} should produce "
            f"{expected_length} dates, but got {len(dates)}"
        )

        # Property: first date should be from_date
        assert dates[0] == from_date, f"First date should be {from_date}, but got {dates[0]}"

        # Property: last date should be to_date
        assert dates[-1] == to_date, f"Last date should be {to_date}, but got {dates[-1]}"

        # Property: dates should be consecutive
        for i in range(1, len(dates)):
            expected = dates[i - 1] + timedelta(days=1)
            assert dates[i] == expected, (
                f"Date at index {i} should be {expected}, but got {dates[i]}"
            )

    @given(test_date=valid_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_validate_args_single_date_produces_single_item_list(self, test_date: date):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.1**

        For any single date passed via --date, validate_args should
        produce a list containing exactly that one date.
        """
        date_str = test_date.strftime("%Y-%m-%d")
        parser = create_parser()
        args = parser.parse_args(["--date", date_str])

        dates, _ = validate_args(args)

        # Property: list should contain exactly one date
        assert len(dates) == 1, f"Single date should produce list of length 1, got {len(dates)}"

        # Property: the date should be the exact input date
        assert dates[0] == test_date, f"Date in list should be {test_date}, but got {dates[0]}"

    @pytest.mark.parametrize(
        "invalid_date_str",
        [
            "2024-13-01",  # Invalid month
            "2024-00-15",  # Invalid month (zero)
            "2024-01-32",  # Invalid day
            "2024-01-00",  # Invalid day (zero)
            "2023-02-29",  # Invalid leap year date
            "not-a-date",  # Non-date string
            "2024/01/15",  # Wrong separator
            "01-15-2024",  # Wrong order
            "",  # Empty string
        ],
    )
    def test_parse_date_rejects_invalid_formats(self, invalid_date_str: str):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.1**

        For any invalid date string, parse_date should raise
        argparse.ArgumentTypeError.
        """
        with pytest.raises(argparse.ArgumentTypeError):
            parse_date(invalid_date_str)

    @given(test_date=valid_date_strategy)
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_date_parsing_round_trip(self, test_date: date):
        """
        **Feature: marketing-reports, Property 12: CLI Date Parsing**
        **Validates: Requirements 7.1, 7.2**

        For any valid date, the round-trip of formatting to string
        and parsing back should be idempotent.
        """
        # First round trip
        date_str_1 = test_date.strftime("%Y-%m-%d")
        parsed_1 = parse_date(date_str_1)

        # Second round trip
        date_str_2 = parsed_1.strftime("%Y-%m-%d")
        parsed_2 = parse_date(date_str_2)

        # Property: round-trip should be idempotent
        assert parsed_1 == parsed_2, f"Round-trip should be idempotent: {parsed_1} != {parsed_2}"
        assert date_str_1 == date_str_2, (
            f"String representation should be stable: '{date_str_1}' != '{date_str_2}'"
        )
