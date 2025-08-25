#!/usr/bin/env python3
"""
Google Sheets Logging Diagnostic Tool

This tool helps diagnose issues with Google Sheets logging configuration,
including header mismatches that cause empty cells.

Usage:
    python tools/diagnose_gsheets.py

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

    from gsheets_logging import build_google_sheets_handler_from_env
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print(
        "Make sure you're running this from the project root and have installed dependencies."
    )
    sys.exit(1)


def diagnose_gsheets():
    """Comprehensive Google Sheets logging diagnosis"""

    print("=" * 60)
    print("GOOGLE SHEETS LOGGING DIAGNOSTIC TOOL")
    print("=" * 60)

    # 1. Environment Check
    print("\n1. ENVIRONMENT CONFIGURATION")
    print("-" * 40)

    env_vars = {
        "GSHEETS_LOGGING_ENABLED": os.getenv("GSHEETS_LOGGING_ENABLED"),
        "GOOGLE_SERVICE_ACCOUNT_JSON": "***SET***"
        if os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        else None,
        "GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS"),
        "GSHEETS_SPREADSHEET_ID": os.getenv("GSHEETS_SPREADSHEET_ID"),
        "GSHEETS_SPREADSHEET_NAME": os.getenv("GSHEETS_SPREADSHEET_NAME"),
        "GSHEETS_WORKSHEET": os.getenv("GSHEETS_WORKSHEET", "Logs"),
        "GSHEETS_FIELDS": os.getenv("GSHEETS_FIELDS"),
        "GSHEETS_BATCH_SIZE": os.getenv("GSHEETS_BATCH_SIZE", "20"),
        "GSHEETS_FLUSH_INTERVAL_SECONDS": os.getenv(
            "GSHEETS_FLUSH_INTERVAL_SECONDS", "5.0"
        ),
    }

    for key, value in env_vars.items():
        status = "✓" if value else "✗"
        print(f"{status} {key}: {value or 'Not set'}")

    # Check if logging is enabled
    enabled = str(env_vars["GSHEETS_LOGGING_ENABLED"] or "").lower() in (
        "true",
        "1",
        "yes",
    )
    if not enabled:
        print(f"\n❌ GSHEETS_LOGGING_ENABLED is not set to 'true'")
        print("   Set GSHEETS_LOGGING_ENABLED=true to enable Google Sheets logging")
        return

    # 2. Credentials Check
    print(f"\n2. CREDENTIALS CHECK")
    print("-" * 40)

    try:
        if env_vars["GOOGLE_SERVICE_ACCOUNT_JSON"]:
            print("✓ Using GOOGLE_SERVICE_ACCOUNT_JSON")
            creds_data = json.loads(env_vars["GOOGLE_SERVICE_ACCOUNT_JSON"])
            print(
                f"  Service account email: {creds_data.get('client_email', 'Unknown')}"
            )
        elif env_vars["GOOGLE_APPLICATION_CREDENTIALS"]:
            print(
                f"✓ Using GOOGLE_APPLICATION_CREDENTIALS: {env_vars['GOOGLE_APPLICATION_CREDENTIALS']}"
            )
            if os.path.exists(env_vars["GOOGLE_APPLICATION_CREDENTIALS"]):
                print("  ✓ Credentials file exists")
                with open(env_vars["GOOGLE_APPLICATION_CREDENTIALS"]) as f:
                    creds_data = json.load(f)
                    print(
                        f"  Service account email: {creds_data.get('client_email', 'Unknown')}"
                    )
            else:
                print("  ❌ Credentials file not found")
                return
        else:
            print("❌ No credentials configured")
            print(
                "   Set either GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_APPLICATION_CREDENTIALS"
            )
            return
    except Exception as e:
        print(f"❌ Error reading credentials: {e}")
        return

    # 3. Spreadsheet Access Check
    print(f"\n3. SPREADSHEET ACCESS CHECK")
    print("-" * 40)

    try:
        # Create client
        if env_vars["GOOGLE_SERVICE_ACCOUNT_JSON"]:
            client = gspread.service_account_from_dict(
                json.loads(env_vars["GOOGLE_SERVICE_ACCOUNT_JSON"])
            )
        else:
            client = gspread.service_account(
                filename=env_vars["GOOGLE_APPLICATION_CREDENTIALS"]
            )

        # Open spreadsheet
        if env_vars["GSHEETS_SPREADSHEET_ID"]:
            print(f"Opening spreadsheet by ID: {env_vars['GSHEETS_SPREADSHEET_ID']}")
            spreadsheet = client.open_by_key(env_vars["GSHEETS_SPREADSHEET_ID"])
        elif env_vars["GSHEETS_SPREADSHEET_NAME"]:
            print(
                f"Opening spreadsheet by name: {env_vars['GSHEETS_SPREADSHEET_NAME']}"
            )
            spreadsheet = client.open(env_vars["GSHEETS_SPREADSHEET_NAME"])
        else:
            print("❌ No spreadsheet ID or name configured")
            return

        print(f"✓ Successfully opened spreadsheet: {spreadsheet.title}")
        print(f"  URL: {spreadsheet.url}")

    except Exception as e:
        print(f"❌ Error accessing spreadsheet: {e}")
        return

    # 4. Worksheet Check
    print(f"\n4. WORKSHEET CHECK")
    print("-" * 40)

    worksheet_title = env_vars["GSHEETS_WORKSHEET"]
    try:
        worksheet = spreadsheet.worksheet(worksheet_title)
        print(f"✓ Found worksheet: {worksheet_title}")
        print(f"  Rows: {worksheet.row_count}, Columns: {worksheet.col_count}")
    except Exception:
        print(f"❌ Worksheet '{worksheet_title}' not found")
        print("  The worksheet will be created automatically when logging starts")
        return

    # 5. Header Analysis
    print(f"\n5. HEADER ANALYSIS")
    print("-" * 40)

    # Get expected fields
    fields_env = env_vars["GSHEETS_FIELDS"]
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

    print(f"Expected fields ({len(expected_fields)}): {expected_fields}")

    # Get actual headers
    try:
        if worksheet.row_count > 0:
            actual_headers = worksheet.row_values(1)
            print(f"Actual headers ({len(actual_headers)}):   {actual_headers}")

            # Compare headers
            if actual_headers == expected_fields:
                print("✅ Headers match perfectly!")
            else:
                print("❌ Header mismatch detected!")

                # Detailed analysis
                if len(actual_headers) > len(expected_fields):
                    extra = len(actual_headers) - len(expected_fields)
                    print(f"   Sheet has {extra} extra columns")

                    # Check if expected headers are shifted
                    if (
                        actual_headers[extra : extra + len(expected_fields)]
                        == expected_fields
                    ):
                        print(
                            f"   ✓ Expected headers found starting at column {extra + 1}"
                        )
                        print(
                            f"   🔧 SOLUTION: Delete the first {extra} columns from your sheet"
                        )
                        print(
                            f"      OR set GSHEETS_FIELDS to: {','.join(['EmptyCol' + str(i + 1) for i in range(extra)] + expected_fields)}"
                        )

                elif len(actual_headers) < len(expected_fields):
                    missing = len(expected_fields) - len(actual_headers)
                    print(f"   Sheet is missing {missing} columns")

                # Show column-by-column comparison
                print(f"\n   Column-by-column comparison:")
                max_len = max(len(actual_headers), len(expected_fields))
                for i in range(max_len):
                    actual = actual_headers[i] if i < len(actual_headers) else "MISSING"
                    expected = (
                        expected_fields[i] if i < len(expected_fields) else "EXTRA"
                    )
                    match = "✓" if actual == expected else "✗"
                    print(f"   {match} Column {i + 1:2d}: '{actual}' vs '{expected}'")
        else:
            print("Sheet is empty (no headers)")
    except Exception as e:
        print(f"Error reading headers: {e}")

    # 6. Test Data Write (optional)
    print(f"\n6. TEST DATA WRITE")
    print("-" * 40)

    response = (
        input("Do you want to test writing a sample row? (y/N): ").strip().lower()
    )
    if response == "y":
        try:
            # Create sample data
            sample_data = []
            for field in expected_fields:
                if field == "DateTime":
                    sample_data.append("2025-08-24T13:14:40.796018+00:00")
                elif field == "BotID":
                    sample_data.append("diagnostic-test")
                elif field == "TelegramID":
                    sample_data.append("123456789")
                elif field == "LLM":
                    sample_data.append("TEST:diagnostic")
                elif field == "OptimizationModel":
                    sample_data.append("DIAGNOSTIC")
                elif field == "UserRequest":
                    sample_data.append("Test request from diagnostic tool")
                elif field == "Answer":
                    sample_data.append("Test response from diagnostic tool")
                elif "tokens" in field:
                    sample_data.append("0")
                else:
                    sample_data.append(f"test_{field}")

            print(f"Writing test data: {sample_data}")
            worksheet.append_row(sample_data, value_input_option="USER_ENTERED")
            print("✅ Test data written successfully!")
            print("   Check your Google Sheet to see where the data appeared")

        except Exception as e:
            print(f"❌ Error writing test data: {e}")

    print(f"\n" + "=" * 60)
    print("DIAGNOSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    diagnose_gsheets()
