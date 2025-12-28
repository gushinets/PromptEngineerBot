#!/usr/bin/env python3
"""
CLI entry point for generating marketing reports.

This module provides a command-line interface for generating marketing reports
manually, supporting single date, date range, and all-users options.

Usage:
    python -m telegram_bot.reports --date 2024-01-15
    python -m telegram_bot.reports --from 2024-01-01 --to 2024-01-31
    python -m telegram_bot.reports --date 2024-01-15 --all-users

Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
"""

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta

from telegram_bot.data.database import get_db_session, init_database
from telegram_bot.services.email_service import get_email_service
from telegram_bot.services.report_config import ReportConfig
from telegram_bot.services.report_service import ReportService


# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


def parse_date(date_str: str) -> date:
    """
    Parse a date string in YYYY-MM-DD format.

    Args:
        date_str: Date string in YYYY-MM-DD format

    Returns:
        Parsed date object

    Raises:
        argparse.ArgumentTypeError: If date format is invalid

    Requirements: 7.1, 7.2
    """
    try:
        # Parse date components directly to avoid naive datetime warning
        parts = date_str.split("-")
        if len(parts) != 3:
            invalid_format_msg = "Invalid date format"
            raise ValueError(invalid_format_msg)
        year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
        return date(year, month, day)
    except (ValueError, IndexError) as e:
        error_msg = f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD format."
        raise argparse.ArgumentTypeError(error_msg) from e


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.

    Returns:
        Configured ArgumentParser instance

    Requirements: 7.1, 7.2, 7.3
    """
    parser = argparse.ArgumentParser(
        prog="reports",
        description="Generate marketing reports for specified date(s).",
        epilog="Examples:\n"
        "  python -m telegram_bot.reports --date 2024-01-15\n"
        "  python -m telegram_bot.reports --from 2024-01-01 --to 2024-01-31\n"
        "  python -m telegram_bot.reports --date 2024-01-15 --all-users",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Date selection options (mutually exclusive groups)
    date_group = parser.add_argument_group("Date Selection")

    # Requirement 7.1: Accept --date parameter in YYYY-MM-DD format
    date_group.add_argument(
        "--date",
        type=parse_date,
        metavar="YYYY-MM-DD",
        help="Generate reports for a specific date (YYYY-MM-DD format)",
    )

    # Requirement 7.2: Accept --from and --to parameters for date range
    date_group.add_argument(
        "--from",
        dest="from_date",
        type=parse_date,
        metavar="YYYY-MM-DD",
        help="Start date for date range (YYYY-MM-DD format)",
    )

    date_group.add_argument(
        "--to",
        dest="to_date",
        type=parse_date,
        metavar="YYYY-MM-DD",
        help="End date for date range (YYYY-MM-DD format)",
    )

    # Requirement 7.3: Accept --all-users flag
    parser.add_argument(
        "--all-users",
        action="store_true",
        help="Include all users regardless of activity window configuration",
    )

    return parser


def validate_args(args: argparse.Namespace) -> tuple[list[date], bool]:
    """
    Validate parsed arguments and return list of dates to process.

    Args:
        args: Parsed command-line arguments

    Returns:
        Tuple of (list of dates to process, all_users flag)

    Raises:
        SystemExit: If arguments are invalid

    Requirements: 7.1, 7.2, 7.3, 7.4
    """
    # Check for conflicting options
    has_single_date = args.date is not None
    has_from = args.from_date is not None
    has_to = args.to_date is not None

    if has_single_date and (has_from or has_to):
        print("Error: Cannot use --date with --from/--to. Choose one method.", file=sys.stderr)
        sys.exit(1)

    if (has_from and not has_to) or (has_to and not has_from):
        print("Error: Both --from and --to must be specified for date range.", file=sys.stderr)
        sys.exit(1)

    if not has_single_date and not has_from:
        print(
            "Error: Must specify either --date or --from/--to date range.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build list of dates
    dates: list[date] = []

    if has_single_date:
        dates = [args.date]
    else:
        # Date range
        if args.from_date > args.to_date:
            print(
                "Error: --from date must be before or equal to --to date.",
                file=sys.stderr,
            )
            sys.exit(1)

        current = args.from_date
        while current <= args.to_date:
            dates.append(current)
            current += timedelta(days=1)

    return dates, args.all_users


async def generate_reports_for_date(
    report_service: ReportService,
    report_date: date,
    include_all_users: bool,
) -> bool:
    """
    Generate reports for a single date.

    Args:
        report_service: ReportService instance
        report_date: Date to generate reports for
        include_all_users: Whether to include all users

    Returns:
        True if successful, False otherwise

    Requirements: 7.4, 7.5
    """
    # Requirement 7.5: Output progress to stdout
    print(f"Generating reports for {report_date}...")

    result = await report_service.generate_and_send_reports(
        report_date=report_date,
        include_all_users=include_all_users,
    )

    if result.success:
        print(f"  ✓ User summary: {result.user_summary_rows} rows")
        print(f"  ✓ Daily metrics: {'generated' if result.daily_metrics_generated else 'skipped'}")
        print(f"  ✓ Sessions exported: {result.sessions_exported}")
        print(f"  ✓ Total execution time: {result.total_execution_time_ms:.1f}ms")
        return True
    print(f"  ✗ Failed: {result.error}", file=sys.stderr)
    return False


async def generate_reports(
    dates: list[date],
    all_users: bool,
) -> int:
    """
    Generate reports for specified date(s).

    Args:
        dates: List of dates to generate reports for
        all_users: Whether to include all users

    Returns:
        Exit code (0 for success, non-zero for failure)

    Requirements: 7.4, 7.5, 7.6
    """
    # Initialize database
    print("Initializing database connection...")
    init_database()

    # Load configuration
    config = ReportConfig.from_env()

    # Requirement 7.4: When --all-users is specified, include all users
    if all_users:
        print("Note: --all-users flag set, including all users regardless of activity window")

    # Get dependencies
    db_session = get_db_session()
    email_service = get_email_service()

    # Initialize report service
    report_service = ReportService(
        db_session=db_session,
        email_service=email_service,
        config=config,
    )

    # Track results
    total_dates = len(dates)
    successful = 0
    failed = 0

    print(f"\nProcessing {total_dates} date(s)...\n")

    for report_date in dates:
        try:
            success = await generate_reports_for_date(
                report_service=report_service,
                report_date=report_date,
                include_all_users=all_users,
            )
            if success:
                successful += 1
            else:
                failed += 1
        except Exception as e:
            print(f"  ✗ Error generating reports for {report_date}: {e}", file=sys.stderr)
            failed += 1

    # Print summary
    print(f"\n{'=' * 50}")
    print("Report Generation Summary")
    print(f"{'=' * 50}")
    print(f"Total dates processed: {total_dates}")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")

    # Requirement 7.6: Exit with code 0 on success and non-zero on failure
    if failed > 0:
        return 1
    return 0


def main() -> int:
    """
    CLI entry point for report generation.

    Returns:
        Exit code (0 for success, non-zero for failure)

    Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6
    """
    parser = create_parser()
    args = parser.parse_args()

    try:
        dates, all_users = validate_args(args)
        return asyncio.run(generate_reports(dates, all_users))
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        logger.exception("Unexpected error during report generation")
        return 1


if __name__ == "__main__":
    sys.exit(main())
