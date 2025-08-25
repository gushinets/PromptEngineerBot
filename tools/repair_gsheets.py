#!/usr/bin/env python3
"""
Google Sheets Repair Tool

This tool can automatically fix common Google Sheets header issues,
including removing extra empty columns and setting correct headers.

Usage:
    python tools/repair_gsheets.py

Requirements:
    - GSHEETS_LOGGING_ENABLED=true
    - Valid Google Sheets credentials
    - Access to the target spreadsheet
"""

import json
import os
import sys
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    import gspread
except ImportError as e:
    print(f"Error importing gspread: {e}")
    print("Install with: pip install gspread")
    sys.exit(1)


def repair_gsheets():
    """Repair Google Sheets header issues"""

    print("=" * 60)
    print("GOOGLE SHEETS REPAIR TOOL")
    print("=" * 60)

    # Check environment
    enabled = str(os.getenv("GSHEETS_LOGGING_ENABLED", "")).lower() in (
        "true",
        "1",
        "yes",
    )
    if not enabled:
        print("❌ GSHEETS_LOGGING_ENABLED is not set to 'true'")
        return

    # Get expected fields
    fields_env = os.getenv("GSHEETS_FIELDS")
    if fields_env:
        expected_fields = [
            item.strip() for item in fields_env.split(",") if item.strip()
        ]
        print(f"Using custom fields from GSHEETS_FIELDS")
    else:
        expected_fields = [
            "DateTime",
            "BotID",
            "TelegramID",
            "LLM",
            "OptimizationModel",
            "UserRequest",
            "Answer",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
        ]
        print(f"Using default fields")

    print(f"Expected fields: {expected_fields}")

    try:
        # Create client
        if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"):
            client = gspread.service_account_from_dict(
                json.loads(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON"))
            )
        else:
            client = gspread.service_account(
                filename=os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            )

        # Open spreadsheet
        if os.getenv("GSHEETS_SPREADSHEET_ID"):
            spreadsheet = client.open_by_key(os.getenv("GSHEETS_SPREADSHEET_ID"))
        else:
            spreadsheet = client.open(os.getenv("GSHEETS_SPREADSHEET_NAME"))

        worksheet_title = os.getenv("GSHEETS_WORKSHEET", "Logs")
        worksheet = spreadsheet.worksheet(worksheet_title)

        print(f"✓ Opened worksheet: {worksheet_title}")

        # Get current headers
        if worksheet.row_count > 0:
            current_headers = worksheet.row_values(1)
            print(f"Current headers: {current_headers}")

            if current_headers == expected_fields:
                print("✅ Headers are already correct!")
                return

            # Analyze the issue
            if len(current_headers) > len(expected_fields):
                extra_columns = len(current_headers) - len(expected_fields)

                # Check if expected headers are just shifted
                if (
                    current_headers[
                        extra_columns : extra_columns + len(expected_fields)
                    ]
                    == expected_fields
                ):
                    print(
                        f"🔧 Detected {extra_columns} extra empty columns at the beginning"
                    )

                    response = (
                        input(f"Remove the first {extra_columns} columns? (y/N): ")
                        .strip()
                        .lower()
                    )
                    if response == "y":
                        # Delete extra columns
                        for i in range(extra_columns):
                            worksheet.delete_columns(1)  # Always delete column 1
                        print(f"✅ Removed {extra_columns} extra columns")

                        # Verify headers are now correct
                        new_headers = worksheet.row_values(1)
                        if new_headers == expected_fields:
                            print("✅ Headers are now correct!")
                        else:
                            print(f"⚠️  Headers after deletion: {new_headers}")
                    else:
                        print("Skipped column deletion")
                else:
                    print("❌ Headers don't match expected pattern")
                    print("Manual intervention required")

            else:
                # Different issue - replace headers
                response = (
                    input("Replace the header row with correct headers? (y/N): ")
                    .strip()
                    .lower()
                )
                if response == "y":
                    # Clear and set new headers
                    worksheet.update("1:1", [expected_fields])
                    print("✅ Headers updated!")
                else:
                    print("Skipped header replacement")

        else:
            # Empty sheet - add headers
            print("Sheet is empty, adding headers...")
            worksheet.append_row(expected_fields, value_input_option="USER_ENTERED")
            print("✅ Headers added!")

    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    repair_gsheets()
